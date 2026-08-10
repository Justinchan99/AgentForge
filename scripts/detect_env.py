#!/usr/bin/env python3
"""Detect the host mode, architecture, privileges, and development tools."""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import platform
import sys
from dataclasses import asdict, dataclass

from common import command_path


TOOL_COMMANDS: dict[str, tuple[str, ...]] = {
    "git": ("git",),
    "node": ("node",),
    "npm": ("npm", "npm.cmd"),
    "cmake": ("cmake",),
    "ninja": ("ninja",),
    "clangd": ("clangd", "clangd.exe"),
    "pyright": ("pyright-langserver", "pyright-langserver.cmd", "pyright", "pyright.cmd"),
    "opencode": ("opencode", "opencode.exe", "opencode.cmd"),
    "vscode": ("code", "code.cmd"),
    "colcon": ("colcon",),
}


@dataclass(frozen=True)
class Environment:
    os: str
    os_version: str
    architecture: str
    mode: str
    elevated: bool
    tools: dict[str, str | None]


def is_elevated() -> bool:
    if os.name == "nt":
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except (AttributeError, OSError):
            return False
    return hasattr(os, "geteuid") and os.geteuid() == 0


def detect_mode() -> str:
    if platform.system() == "Windows":
        return "Windows Local Development"
    if os.environ.get("SSH_CONNECTION") or os.environ.get("SSH_CLIENT"):
        return "Windows + SSH Remote Linux"
    return "Linux Local Development"


def detect_environment() -> Environment:
    system = platform.system() or "Unknown"
    return Environment(
        os=system,
        os_version=platform.platform(),
        architecture=platform.machine() or "unknown",
        mode=detect_mode(),
        elevated=is_elevated(),
        tools={name: command_path(*commands) for name, commands in TOOL_COMMANDS.items()},
    )


def print_report(environment: Environment) -> None:
    print("AgentForge Environment Check")
    print(f"OS:           {environment.os_version}")
    print(f"Architecture: {environment.architecture}")
    print(f"Mode:         {environment.mode}")
    print(f"Elevated:     {'yes' if environment.elevated else 'no'}")
    print("\nInstalled:")
    for name, path in environment.tools.items():
        if path:
            print(f"  [OK] {name:<10} {path}")
    print("\nMissing:")
    missing = [name for name, path in environment.tools.items() if not path]
    if missing:
        for name in missing:
            print(f"  [--] {name}")
    else:
        print("  none")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    args = parser.parse_args(argv)
    environment = detect_environment()
    if args.json:
        print(json.dumps(asdict(environment), indent=2))
    else:
        print_report(environment)
    return 0


if __name__ == "__main__":
    sys.exit(main())
