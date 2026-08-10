#!/usr/bin/env python3
"""Verify the AgentForge workflow, workers, LSP, and relevant build tools."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from common import WORKFLOW_BEGIN, WORKFLOW_END, load_json
from configure_agents import deepseek_auth_source
from detect_env import Environment, detect_environment
from project_detection import ProjectInfo, detect_project


FREE_MODEL = "opencode/deepseek-v4-flash-free"
API_MODEL = "deepseek/deepseek-v4-pro"


@dataclass(frozen=True)
class Check:
    group: str
    name: str
    ok: bool
    detail: str
    required: bool = True


def ready(checks: list[Check]) -> bool:
    return all(check.ok or not check.required for check in checks)


def _agent_has_model(path: Path, model: str) -> bool:
    try:
        return f"model: {model}" in path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return False


def _model_catalog(environment: Environment) -> set[str]:
    if not environment.tools["opencode"]:
        return set()
    try:
        completed = subprocess.run(
            [environment.tools["opencode"], "models"],
            capture_output=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return set()
    output = completed.stdout.decode("utf-8", errors="replace")
    return {line.strip() for line in output.splitlines() if "/" in line}


def verify_project(
    project: Path,
    environment: Environment | None = None,
    project_info: ProjectInfo | None = None,
    auth_source: str | None | object = ...,
    model_catalog: set[str] | None = None,
) -> list[Check]:
    project = project.resolve()
    environment = environment or detect_environment()
    project_info = project_info or detect_project(project)
    auth = deepseek_auth_source() if auth_source is ... else auth_source
    models = _model_catalog(environment) if model_catalog is None else model_catalog
    checks: list[Check] = []

    opencode = environment.tools["opencode"]
    checks.append(Check("Runtime", "opencode", bool(opencode), opencode or "not found on PATH"))
    for name in ("node", "npm", "git"):
        found = environment.tools[name]
        checks.append(Check("Runtime", name, bool(found), found or "not found on PATH"))

    agents_md = project / "AGENTS.md"
    try:
        workflow = agents_md.read_text(encoding="utf-8-sig")
        workflow_ok = WORKFLOW_BEGIN in workflow and WORKFLOW_END in workflow
    except (OSError, UnicodeError):
        workflow_ok = False
    checks.append(Check("Agents", "Main Agent", workflow_ok, "inherits current conversation model" if workflow_ok else "workflow block missing"))

    main_doc = project / ".agentforge/main-agent.md"
    checks.append(Check("Agents", "main-agent policy", main_doc.is_file(), str(main_doc) if main_doc.is_file() else "missing"))
    free_worker = project / ".opencode/agents/deepseek-worker-free.md"
    free_ok = _agent_has_model(free_worker, FREE_MODEL) and FREE_MODEL in models
    free_detail = FREE_MODEL if free_ok else "agent or model unavailable"
    checks.append(Check("Agents", "deepseek-worker-free", free_ok, free_detail))

    api_worker = project / ".opencode/agents/deepseek-worker.md"
    if auth:
        api_ok = _agent_has_model(api_worker, API_MODEL) and API_MODEL in models
        checks.append(Check("Agents", "deepseek-worker", api_ok, f"configured via {auth}" if api_ok else "authenticated but agent/model unavailable"))
    else:
        checks.append(Check("Agents", "deepseek-worker", False, "optional / DeepSeek authentication not configured", required=False))

    config = project / ".opencode/opencode.json"
    try:
        data = load_json(config)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        data = {}
        checks.append(Check("Config", ".opencode/opencode.json", False, str(exc)))
    else:
        checks.append(Check("Config", ".opencode/opencode.json", True, str(config)))

    lsp = data.get("lsp", {}) if isinstance(data.get("lsp", {}), dict) else {}
    if "cpp" in project_info.languages:
        found = environment.tools["clangd"]
        checks.append(Check("LSP", "clangd", bool(found) and "clangd" in lsp, found or "tool/config missing"))
    if "python" in project_info.languages:
        found = environment.tools["pyright"]
        checks.append(Check("LSP", "pyright", bool(found) and "pyright" in lsp, found or "tool/config missing"))
    if not project_info.languages:
        checks.append(Check("LSP", "language detection", True, "no C/C++ or Python sources detected"))

    if project_info.cmake:
        for name in ("cmake", "ninja"):
            found = environment.tools[name]
            checks.append(Check("Build", name, bool(found), found or "not found on PATH"))
    if project_info.ros2:
        found = environment.tools["colcon"]
        checks.append(Check("Build", "colcon", bool(found), found or "not found on PATH"))
    return checks


def print_report(checks: list[Check]) -> None:
    current_group = None
    for check in checks:
        if check.group != current_group:
            current_group = check.group
            print(f"\n{current_group}:")
        mark = "[OK]" if check.ok else ("[--]" if not check.required else "[!!]")
        print(f"  {mark} {check.name:<32} {check.detail}")
    print("\nREADY" if ready(checks) else "\nNOT READY")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", nargs="?", default=".")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    checks = verify_project(Path(args.project))
    if args.json:
        print(json.dumps({"ready": ready(checks), "checks": [asdict(c) for c in checks]}, indent=2))
    else:
        print_report(checks)
    return 0 if ready(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
