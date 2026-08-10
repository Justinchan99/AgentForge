#!/usr/bin/env python3
"""Combined host and project detection entry point."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from detect_env import detect_environment
from project_detection import detect_project


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=".")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--has-language", choices=("cpp", "python"))
    args = parser.parse_args(argv)
    project = detect_project(Path(args.project))
    if args.has_language:
        return 0 if args.has_language in project.languages else 1
    payload = {"environment": asdict(detect_environment()), "project": project.to_dict()}
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"OS: {payload['environment']['os_version']}")
        print(f"Mode: {payload['environment']['mode']}")
        print(f"Architecture: {payload['environment']['architecture']}")
        print(f"Languages: {', '.join(project.languages) if project.languages else 'none detected'}")
        print(f"CMake: {'yes' if project.cmake else 'no'}")
        print(f"ROS 2: {'yes' if project.ros2 else 'no'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
