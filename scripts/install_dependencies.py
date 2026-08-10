"""Dispatch missing dependency installation to the platform installer."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from common import PROJECT_ROOT
from detect_env import Environment
from project_detection import ProjectInfo


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


def install_missing(project: Path, assume_yes: bool, interactive: bool = True) -> tuple[bool, list[str]]:
    from detect_env import detect_environment
    from project_detection import detect_project

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
        command = [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(PROJECT_ROOT / "scripts/install_windows.ps1"),
            "-SourceRoot",
            str(PROJECT_ROOT),
            "-Yes",
            "-Project",
            str(project),
        ]
    else:
        command = [
            "sh",
            str(PROJECT_ROOT / "scripts/install_linux.sh"),
            "--source",
            str(PROJECT_ROOT),
            "--yes",
            "--project",
            str(project),
        ]
    completed = subprocess.run(command, check=False)
    return completed.returncode == 0, missing
