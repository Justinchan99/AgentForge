#!/usr/bin/env python3
"""AgentForge command-line interface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from adapt_project import adapt_project
from common import format_changes
from configure_agents import configure_agents
from configure_lsp import configure_lsp
from detect_env import detect_environment, print_report
from install_dependencies import install_missing, missing_tools, required_tools
from project_detection import detect_project
from verify import print_report as print_verify_report
from verify import ready, verify_project


def command_init(args: argparse.Namespace) -> int:
    project = Path(args.project).resolve()
    if not project.is_dir():
        print(f"ERROR: project directory does not exist: {project}", file=sys.stderr)
        return 2

    environment = detect_environment()
    project_info = detect_project(project)
    print("AgentForge")
    print(f"Environment: {environment.mode} / {environment.architecture}")
    print(f"Project:     {project}")
    print(f"Languages:   {', '.join(project_info.languages) if project_info.languages else 'none detected'}")
    print("\nTools:")
    for name in required_tools(project_info):
        found = environment.tools.get(name)
        print(f"  {'[OK]' if found else '[--]'} {name:<10} {found or 'missing'}")
    missing = missing_tools(environment, project_info)
    if missing:
        print("Missing:     " + ", ".join(missing))
        if args.dry_run:
            print("Dry run: dependencies will not be installed.")
        elif not args.skip_install:
            installed, _ = install_missing(project, args.yes)
            if not installed:
                print("Dependencies were not installed; configuration will continue.")

    agent_changes, agent_warnings, auth_source = configure_agents(project, args.dry_run)
    lsp_changes, lsp_warnings = configure_lsp(project, args.dry_run, project_info.languages)
    print("\nConfiguration:")
    print("\n".join(format_changes(agent_changes + lsp_changes)))
    print("\nAgents:")
    print("  [OK] Main Agent             current conversation model")
    print("  [OK] deepseek-worker-free   opencode/deepseek-v4-flash-free")
    if auth_source:
        print(f"  [OK] deepseek-worker        deepseek/deepseek-v4-pro ({auth_source})")
    else:
        print("  [--] deepseek-worker        optional / DeepSeek authentication not configured")

    if (project_info.cmake or project_info.ros2) and not (project / "compile_commands.json").is_file():
        print("\nProject preparation is available; run: agentforge prepare")

    warnings = agent_warnings + lsp_warnings
    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    if args.dry_run:
        print("\nDry run complete; no files were written.")
    elif not warnings:
        print("\nAgentForge initialization complete.")
    return 1 if warnings else 0


def command_prepare(args: argparse.Namespace) -> int:
    project = Path(args.project).resolve()
    if not project.is_dir():
        print(f"ERROR: project directory does not exist: {project}", file=sys.stderr)
        return 2
    result = adapt_project(project, args.dry_run)
    print(f"Project type: {result.kind}")
    print(f"Status:       {result.status}")
    if result.command:
        print("Command:      " + " ".join(result.command))
    if result.message:
        print(f"Message:      {result.message}")
    return 1 if result.status == "failed" else 0


def command_verify(args: argparse.Namespace) -> int:
    checks = verify_project(Path(args.project))
    print_verify_report(checks)
    return 0 if ready(checks) else 1


def command_doctor(args: argparse.Namespace) -> int:
    print_report(detect_environment())
    project = Path(args.project).resolve()
    if project.is_dir():
        info = detect_project(project)
        print("\nProject:")
        print(f"  Root:      {info.root}")
        print(f"  Languages: {', '.join(info.languages) if info.languages else 'none detected'}")
        print(f"  CMake:     {'yes' if info.cmake else 'no'}")
        print(f"  ROS 2:     {'yes' if info.ros2 else 'no'}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agentforge", description="OpenCode hierarchical multi-agent workflow initializer")
    parser.add_argument("--version", action="version", version="AgentForge 0.2.0")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="initialize project configuration without building")
    init_parser.add_argument("project", nargs="?", default=".")
    init_parser.add_argument("--dry-run", action="store_true")
    init_parser.add_argument("--yes", "-y", action="store_true", help="install missing dependencies without prompting")
    init_parser.add_argument("--skip-install", action="store_true", help="do not offer dependency installation")
    init_parser.add_argument("--skip-build", action="store_true", help=argparse.SUPPRESS)
    init_parser.set_defaults(handler=command_init)

    prepare_parser = subparsers.add_parser("prepare", help="generate compile database and index inputs")
    prepare_parser.add_argument("project", nargs="?", default=".")
    prepare_parser.add_argument("--dry-run", action="store_true")
    prepare_parser.set_defaults(handler=command_prepare)

    verify_parser = subparsers.add_parser("verify", help="verify workflow, workers, LSP, and tools")
    verify_parser.add_argument("project", nargs="?", default=".")
    verify_parser.set_defaults(handler=command_verify)

    doctor_parser = subparsers.add_parser("doctor", help="report host and project environment")
    doctor_parser.add_argument("project", nargs="?", default=".")
    doctor_parser.set_defaults(handler=command_doctor)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
