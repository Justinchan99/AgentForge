#!/usr/bin/env python3
"""Generate compilation databases for CMake and ROS 2 projects."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from common import atomic_write_text, command_path


@dataclass(frozen=True)
class AdaptResult:
    kind: str
    status: str
    command: tuple[str, ...] = ()
    message: str = ""


def project_kind(project: Path) -> str:
    if (project / "package.xml").is_file():
        return "ros2"
    if (project / "CMakeLists.txt").is_file():
        return "cmake"
    return "none"


def build_command(project: Path) -> tuple[str, ...] | None:
    kind = project_kind(project)
    if kind == "ros2":
        if not command_path("colcon"):
            return None
        managed = project / ".agentforge"
        return (
            "colcon",
            "--log-base",
            str(managed / "ros-log"),
            "build",
            "--build-base",
            str(managed / "ros-build"),
            "--install-base",
            str(managed / "ros-install"),
            "--cmake-args",
            "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON",
        )
    if kind == "cmake":
        if not command_path("cmake"):
            return None
        return (
            "cmake",
            "-S",
            str(project),
            "-B",
            str(project / ".agentforge/cmake-build"),
            "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON",
        )
    return ()


def collect_compile_commands(project: Path, kind: str) -> int:
    """Create one clangd-visible database from managed CMake/colcon outputs."""
    managed = project / ".agentforge"
    if kind == "cmake":
        sources = [managed / "cmake-build/compile_commands.json"]
    elif kind == "ros2":
        sources = sorted((managed / "ros-build").glob("*/compile_commands.json"))
    else:
        return 0

    entries: list[dict] = []
    for source in sources:
        if not source.is_file():
            continue
        try:
            value = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if isinstance(value, list):
            entries.extend(item for item in value if isinstance(item, dict))
    if entries:
        atomic_write_text(managed / "compile_commands.json", json.dumps(entries, indent=2) + "\n")
    return len(entries)


def adapt_project(project: Path, dry_run: bool = False) -> AdaptResult:
    project = project.resolve()
    kind = project_kind(project)
    if (project / "compile_commands.json").is_file():
        return AdaptResult(kind, "ready", message="project compile_commands.json already exists")
    command = build_command(project)
    if command == ():
        return AdaptResult(kind, "not-applicable", message="No CMakeLists.txt or package.xml found")
    if command is None:
        tool = "colcon" if kind == "ros2" else "cmake"
        return AdaptResult(kind, "skipped", message=f"{tool} is not available")
    if dry_run:
        return AdaptResult(kind, "planned", command)

    environment = os.environ.copy()
    cache = project / ".agentforge/cmake-build/CMakeCache.txt"
    if kind == "cmake" and command_path("ninja") and not cache.exists():
        command = command + ("-G", "Ninja")
    completed = subprocess.run(command, cwd=project, env=environment, check=False)
    if completed.returncode:
        return AdaptResult(kind, "failed", command, f"build configuration exited with {completed.returncode}")
    entries = collect_compile_commands(project, kind)
    message = f"wrote {entries} compile command entries" if entries else "no compile commands were produced"
    return AdaptResult(kind, "configured", command, message)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", nargs="?", default=".")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    result = adapt_project(Path(args.project), args.dry_run)
    print(f"Project type: {result.kind}")
    print(f"Status:       {result.status}")
    if result.command:
        print("Command:      " + " ".join(result.command))
    if result.message:
        print(f"Message:      {result.message}")
    return 1 if result.status == "failed" else 0


if __name__ == "__main__":
    sys.exit(main())
