#!/usr/bin/env python3
"""Safely configure OpenCode and VS Code language intelligence."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from common import atomic_write_bytes, atomic_write_text, format_changes, load_json, merge_json_file, render_template
from project_detection import detect_project


def _render_json(name: str, replacements: dict[str, str] | None = None) -> dict:
    value = json.loads(render_template(name, replacements))
    if not isinstance(value, dict):
        raise ValueError(f"Template {name} must contain a JSON object")
    return value


def _merge_or_migrate(
    destination: Path,
    defaults: dict,
    legacy: dict,
    dry_run: bool,
) -> tuple[str, str | None]:
    if destination.exists():
        try:
            current = load_json(destination)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
            pass
        else:
            if current == legacy and current != defaults:
                backup = destination.with_name(destination.name + ".agentforge.bak")
                if not dry_run:
                    if not backup.exists():
                        atomic_write_bytes(backup, destination.read_bytes())
                    atomic_write_text(destination, json.dumps(defaults, indent=2) + "\n")
                return "migrated", None
    return merge_json_file(destination, defaults, dry_run)


def configure_lsp(
    project: Path,
    dry_run: bool = False,
    languages: tuple[str, ...] | None = None,
) -> tuple[list[tuple[Path, str]], list[str]]:
    project = project.resolve()
    languages = languages if languages is not None else detect_project(project).languages
    clangd = "clangd.exe" if os.name == "nt" else "clangd"
    pyright = "pyright-langserver.cmd" if os.name == "nt" else "pyright-langserver"
    compile_dir = "." if (project / "compile_commands.json").is_file() else ".agentforge"
    replacements = {"CLANGD": clangd, "PYRIGHT": pyright, "COMPILE_COMMANDS_DIR": compile_dir}
    opencode = _render_json("opencode.json", replacements)
    settings = _render_json("vscode_settings.json", replacements)
    extensions = _render_json("vscode_extensions.json")
    legacy_opencode = json.loads(json.dumps(opencode))
    legacy_settings = json.loads(json.dumps(settings))
    legacy_extensions = json.loads(json.dumps(extensions))

    if "cpp" not in languages:
        opencode["lsp"].pop("clangd", None)
        settings.pop("C_Cpp.intelliSenseEngine", None)
        settings.pop("clangd.arguments", None)
        extensions["recommendations"] = [
            item for item in extensions["recommendations"] if item not in {"llvm-vs-code-extensions.vscode-clangd", "ms-vscode.cmake-tools"}
        ]
    if "python" not in languages:
        opencode["lsp"].pop("pyright", None)
        settings.pop("python.analysis.typeCheckingMode", None)
        settings.pop("python.analysis.autoImportCompletions", None)
        extensions["recommendations"] = [
            item for item in extensions["recommendations"] if item not in {"ms-python.python", "ms-python.vscode-pylance"}
        ]
    if not opencode["lsp"]:
        opencode.pop("lsp")

    changes: list[tuple[Path, str]] = []
    warnings: list[str] = []
    for destination, defaults, legacy in (
        (project / ".opencode/opencode.json", opencode, legacy_opencode),
        (project / ".vscode/settings.json", settings, legacy_settings),
        (project / ".vscode/extensions.json", extensions, legacy_extensions),
    ):
        status, warning = _merge_or_migrate(destination, defaults, legacy, dry_run)
        changes.append((destination, status))
        if warning:
            warnings.append(warning)
    return changes, warnings


def migrate_legacy_global_lsp(dry_run: bool = False) -> tuple[list[tuple[Path, str]], list[str]]:
    clangd = "clangd.exe" if os.name == "nt" else "clangd"
    pyright = "pyright-langserver.cmd" if os.name == "nt" else "pyright-langserver"
    legacy = _render_json(
        "opencode.json",
        {"CLANGD": clangd, "PYRIGHT": pyright, "COMPILE_COMMANDS_DIR": ".agentforge"},
    )
    config_root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    destination = config_root / "opencode/opencode.json"
    if not destination.is_file():
        return [(destination, "not-applicable")], []
    try:
        current = load_json(destination)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return [(destination, "preserved")], [f"Could not inspect legacy global config: {exc}"]
    if current == {"$schema": "https://opencode.ai/config.json"}:
        return [(destination, "already-migrated")], []
    if current != legacy:
        return [(destination, "preserved-user-config")], []
    backup = destination.with_name(destination.name + ".agentforge.bak")
    if not dry_run:
        if not backup.exists():
            atomic_write_bytes(backup, destination.read_bytes())
        atomic_write_text(destination, json.dumps({"$schema": "https://opencode.ai/config.json"}, indent=2) + "\n")
    return [(destination, "migrated-legacy")], []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", nargs="?", default=".")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--migrate-global", action="store_true", help="retire only the exact legacy AgentForge global LSP config")
    args = parser.parse_args(argv)
    if args.migrate_global:
        changes, warnings = migrate_legacy_global_lsp(args.dry_run)
    else:
        changes, warnings = configure_lsp(Path(args.project), args.dry_run)
    print("\n".join(format_changes(changes)))
    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    return 1 if warnings else 0


if __name__ == "__main__":
    sys.exit(main())
