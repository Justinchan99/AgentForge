#!/usr/bin/env python3
"""Build the Linux deployment branch as one self-contained Python script."""

from __future__ import annotations

import argparse
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MODULE_ORDER = (
    "common",
    "project_detection",
    "detect_env",
    "configure_agents",
    "configure_lsp",
    "adapt_project",
    "install_dependencies",
    "verify",
    "agentforge",
)
TEMPLATE_NAMES = (
    "agentforge_gitignore",
    "agents.md",
    "deepseek-worker-free.md",
    "deepseek-worker.md",
    "gitignore_secrets",
    "legacy_agents_existing_header_v1.md",
    "legacy_agents_v1.md",
    "legacy_architect_v1.md",
    "legacy_developer_v1.md",
    "legacy_reviewer_v1.md",
    "main-agent.md",
    "opencode.json",
    "vscode_extensions.json",
    "vscode_settings.json",
)


STANDALONE_INSTALL_DEPENDENCIES = r'''"""Linux dependency installation and single-file deployment."""

from __future__ import annotations

import argparse
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

from common import atomic_write_bytes, command_path, format_changes
from configure_lsp import migrate_legacy_global_lsp
from detect_env import Environment, detect_environment, print_report
from project_detection import ProjectInfo, detect_project


APT_PACKAGES = {
    "git": "git",
    "node": "nodejs",
    "npm": "npm",
    "cmake": "cmake",
    "ninja": "ninja-build",
    "clangd": "clangd",
}
DNF_PACKAGES = {
    "git": "git",
    "node": "nodejs",
    "npm": "npm",
    "cmake": "cmake",
    "ninja": "ninja-build",
    "clangd": "clang-tools-extra",
}


def required_tools(project: ProjectInfo) -> tuple[str, ...]:
    names = ["git", "node", "npm", "opencode"]
    if "cpp" in project.languages:
        names.append("clangd")
    if "python" in project.languages:
        names.append("pyright")
    if project.cmake:
        names.extend(("cmake", "ninja"))
    if project.ros2:
        names.append("colcon")
    return tuple(dict.fromkeys(names))


def missing_tools(environment: Environment, project: ProjectInfo) -> list[str]:
    return [name for name in required_tools(project) if not environment.tools.get(name)]


def _privilege_prefix() -> list[str] | None:
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        return []
    sudo = command_path("sudo")
    return [sudo] if sudo else None


def _run_system(command: list[str]) -> bool:
    prefix = _privilege_prefix()
    if prefix is None:
        print("Administrator privileges are required; install sudo or run as root.", file=sys.stderr)
        return False
    return subprocess.run(prefix + command, check=False).returncode == 0


def _install_system_packages(missing: list[str]) -> bool:
    apt = command_path("apt-get")
    dnf = command_path("dnf")
    mapping = APT_PACKAGES if apt else DNF_PACKAGES
    packages = list(dict.fromkeys(mapping[name] for name in missing if name in mapping))
    if not packages:
        return True
    if apt:
        return _run_system([apt, "update"]) and _run_system([apt, "install", "-y", *packages])
    if dnf:
        return _run_system([dnf, "install", "-y", *packages])
    print("No supported package manager found; install required tools manually.", file=sys.stderr)
    return False


def _install_npm_packages(missing: list[str]) -> bool:
    packages: list[str] = []
    if "opencode" in missing:
        packages.append("opencode-ai")
    if "pyright" in missing:
        packages.append("pyright")
    if not packages:
        return True
    npm = command_path("npm")
    if not npm:
        print("npm is required to install " + ", ".join(packages), file=sys.stderr)
        return False
    command = [npm, "install", "--global", *packages]
    completed = subprocess.run(command, check=False)
    if completed.returncode == 0:
        return True
    prefix = _privilege_prefix()
    if not prefix:
        return False
    return subprocess.run(prefix + command, check=False).returncode == 0


def install_missing(project: Path, assume_yes: bool, interactive: bool = True) -> tuple[bool, list[str]]:
    environment = detect_environment()
    info = detect_project(project)
    missing = missing_tools(environment, info)
    installable = [name for name in missing if name != "colcon"]
    if not installable:
        return True, missing
    if not assume_yes:
        if not interactive or not sys.stdin.isatty():
            return False, missing
        answer = input("Install missing dependencies (" + ", ".join(installable) + ")? [y/N] ")
        if answer.lower() not in {"y", "yes"}:
            return False, missing
    if os.name == "nt":
        print("This deployment artifact supports Linux only.", file=sys.stderr)
        return False, missing
    if not _install_system_packages(installable):
        return False, missing
    if not _install_npm_packages(installable):
        return False, missing
    remaining = missing_tools(detect_environment(), info)
    return not any(name != "colcon" for name in remaining), missing


def _clean_legacy_runtime() -> None:
    data_root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")).expanduser().resolve()
    legacy = data_root / "agentforge"
    if legacy.parent != data_root or legacy.name != "agentforge":
        raise RuntimeError(f"Unsafe legacy runtime path: {legacy}")
    if legacy.is_symlink():
        print(f"Preserved symbolic link at legacy runtime path: {legacy}", file=sys.stderr)
        return
    if not legacy.exists():
        return
    known_runtime = (
        legacy.is_dir()
        and (legacy / "scripts/agentforge.py").is_file()
        and (legacy / "templates/agents.md").is_file()
    )
    if not known_runtime:
        print(f"Preserved unrecognized legacy runtime path: {legacy}", file=sys.stderr)
        return
    shutil.rmtree(legacy)
    print(f"Removed recognized legacy AgentForge runtime: {legacy}")


def _install_artifact(source: Path) -> Path:
    bin_root = Path.home() / ".local/bin"
    bin_root.mkdir(parents=True, exist_ok=True)
    target = bin_root / "agentforge"
    atomic_write_bytes(target, source.read_bytes())
    target.chmod(stat.S_IMODE(target.stat().st_mode) | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return target


def install_command(argv: list[str], source: Path) -> int:
    parser = argparse.ArgumentParser(prog="agentforge install", description="Install the self-contained AgentForge CLI for the current Linux user")
    parser.add_argument("--yes", "-y", action="store_true")
    parser.add_argument("--skip-tools", action="store_true")
    parser.add_argument("--project", default=".")
    parser.add_argument("--init", nargs="?", const=".")
    args = parser.parse_args(argv)
    if os.name == "nt":
        print("ERROR: the deploy branch supports Linux only.", file=sys.stderr)
        return 2
    project = Path(args.project).resolve()
    if not project.is_dir():
        print(f"ERROR: project directory does not exist: {project}", file=sys.stderr)
        return 2

    environment = detect_environment()
    info = detect_project(project)
    print_report(environment)
    print(f"\nProject:     {project}")
    print(f"Languages:   {', '.join(info.languages) if info.languages else 'none detected'}")
    missing = missing_tools(environment, info)
    if missing and not args.skip_tools:
        installed, _ = install_missing(project, args.yes)
        if not installed:
            print("Dependencies were not installed; AgentForge itself will still be installed.", file=sys.stderr)

    target = _install_artifact(source.resolve())
    _clean_legacy_runtime()
    changes, warnings = migrate_legacy_global_lsp()
    print("\nGlobal migration:")
    print("\n".join(format_changes(changes)))
    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    print(f"\nAgentForge CLI installed: {target}")
    if str(target.parent) not in os.environ.get("PATH", "").split(os.pathsep):
        print(f'Add {target.parent} to PATH: export PATH="$HOME/.local/bin:$PATH"')

    if args.init is not None:
        init_project = Path(args.init).resolve()
        completed = subprocess.run([sys.executable, str(target), "init", str(init_project)], check=False)
        return completed.returncode
    return 0
'''


INSTALL_SH = r'''#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
assume_yes=0
skip_tools=0
for argument in "$@"; do
    case "$argument" in
        --yes|-y) assume_yes=1 ;;
        --skip-tools) skip_tools=1 ;;
    esac
done

python_ok=0
if command -v python3 >/dev/null 2>&1; then
    if python3 -c 'import sys; raise SystemExit(sys.version_info < (3, 9))'; then
        python_ok=1
    fi
fi

if [ "$python_ok" -eq 0 ]; then
    if [ "$skip_tools" -eq 1 ]; then
        echo "Python 3.9 or newer is required; --skip-tools prevents installation." >&2
        exit 1
    fi
    if [ "$assume_yes" -eq 0 ]; then
        if [ ! -t 0 ]; then
            echo "Python 3.9 or newer is required; rerun with --yes to install it." >&2
            exit 1
        fi
        printf 'Install Python 3.9 or newer? [y/N] '
        read -r answer
        case "$answer" in y|Y|yes|YES) ;; *) exit 1 ;; esac
    fi
    privilege=""
    if [ "$(id -u)" -ne 0 ]; then
        command -v sudo >/dev/null 2>&1 || { echo "sudo is required to install Python." >&2; exit 1; }
        privilege="sudo"
    fi
    if command -v apt-get >/dev/null 2>&1; then
        $privilege apt-get update
        $privilege apt-get install -y python3
    elif command -v dnf >/dev/null 2>&1; then
        $privilege dnf install -y python3
    else
        echo "No supported package manager found; install Python 3.9+ manually." >&2
        exit 1
    fi
fi

if ! command -v python3 >/dev/null 2>&1 || ! python3 -c 'import sys; raise SystemExit(sys.version_info < (3, 9))'; then
    echo "The available python3 is older than 3.9; install Python 3.9+ manually." >&2
    exit 1
fi

exec python3 "$SCRIPT_DIR/agentforge" install "$@"
'''


def _raw_literal(value: str) -> str:
    value = value.replace("\r\n", "\n")
    if "'''" in value:
        raise ValueError("embedded source contains an unsupported triple-single-quote sequence")
    return "r'''" + value + "'''"


def _mapping_literal(values: dict[str, str]) -> str:
    rows = ["{"]
    for name, value in values.items():
        rows.append(f"    {name!r}: {_raw_literal(value)},")
    rows.append("}")
    return "\n".join(rows)


def _module_sources() -> dict[str, str]:
    sources: dict[str, str] = {}
    for name in MODULE_ORDER:
        if name == "install_dependencies":
            sources[name] = STANDALONE_INSTALL_DEPENDENCIES
            continue
        source = (ROOT / "scripts" / f"{name}.py").read_text(encoding="utf-8")
        if name == "common":
            old = 'return (TEMPLATE_ROOT / name).read_text(encoding="utf-8")'
            if old not in source:
                raise ValueError("common.template_text implementation changed; update the deployment builder")
            source = source.replace(old, "return _EMBEDDED_TEMPLATES[name]", 1)
        sources[name] = source
    return sources


def _templates() -> dict[str, str]:
    return {name: (ROOT / "templates" / name).read_text(encoding="utf-8") for name in TEMPLATE_NAMES}


def build_agentforge(output: Path) -> None:
    header = '''#!/usr/bin/env python3
"""Self-contained AgentForge Linux deployment artifact. Generated; do not edit."""

from __future__ import annotations

import sys
import types
from pathlib import Path

'''
    runtime = r'''

def _load_embedded_module(name: str) -> None:
    module = types.ModuleType(name)
    module.__file__ = f"{Path(__file__).resolve()}::{name}.py"
    module.__package__ = ""
    if name == "common":
        module.__dict__["_EMBEDDED_TEMPLATES"] = EMBEDDED_TEMPLATES
    sys.modules[name] = module
    exec(compile(EMBEDDED_MODULES[name], module.__file__, "exec"), module.__dict__)


for _module_name in EMBEDDED_MODULES:
    _load_embedded_module(_module_name)


def _main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "install":
        from install_dependencies import install_command

        return install_command(sys.argv[2:], Path(__file__))
    from agentforge import main

    return main()


if __name__ == "__main__":
    raise SystemExit(_main())
'''
    content = (
        header
        + "EMBEDDED_TEMPLATES = "
        + _mapping_literal(_templates())
        + "\n\nEMBEDDED_MODULES = "
        + _mapping_literal(_module_sources())
        + runtime
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8", newline="\n")
    output.chmod(output.stat().st_mode | 0o111)


def build_install_sh(output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(INSTALL_SH, encoding="utf-8", newline="\n")
    output.chmod(output.stat().st_mode | 0o111)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="deployment output directory")
    args = parser.parse_args()
    build_agentforge(args.output / "agentforge")
    build_install_sh(args.output / "install.sh")
    print(args.output / "agentforge")
    print(args.output / "install.sh")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
