#!/usr/bin/env python3
"""Configure the hierarchical AgentForge workflow and OpenCode workers."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

from common import (
    LEGACY_WORKFLOW_MARKER,
    WORKFLOW_BEGIN,
    WORKFLOW_END,
    atomic_write_bytes,
    command_path,
    ensure_text_block,
    format_changes,
    template_text,
    write_if_absent,
)


ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")


def deepseek_auth_source() -> str | None:
    if os.environ.get("DEEPSEEK_API_KEY", "").strip():
        return "DEEPSEEK_API_KEY"
    opencode = command_path("opencode", "opencode.cmd", "opencode.exe")
    if not opencode:
        return None
    try:
        completed = subprocess.run(
            [opencode, "auth", "list"],
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    output = ANSI_ESCAPE.sub("", (completed.stdout + completed.stderr).decode("utf-8", errors="replace"))
    return "OpenCode auth" if completed.returncode == 0 and re.search(r"\bDeepSeek\b", output, re.I) else None


def _replace_owned_workflow(existing: bytes, block: bytes) -> tuple[bytes, str, str | None]:
    bom = b"\xef\xbb\xbf" if existing.startswith(b"\xef\xbb\xbf") else b""
    body = existing[len(bom) :]
    begin = WORKFLOW_BEGIN.encode("ascii")
    end = WORKFLOW_END.encode("ascii")
    start = body.find(begin)
    if start >= 0:
        finish = body.find(end, start + len(begin))
        if finish < 0:
            return existing, "preserved", "AGENTS.md contains AGENTFORGE:BEGIN without AGENTFORGE:END"
        finish += len(end)
        replacement = body[:start] + block + body[finish:]
        status = "unchanged" if replacement == body else "updated"
        return bom + replacement, status, None

    legacy_full = template_text("legacy_agents_v1.md").encode("utf-8")
    legacy_header = template_text("legacy_agents_existing_header_v1.md").rstrip().encode("utf-8")
    normalized_body = body.decode("utf-8").replace("\r\n", "\n")
    normalized_legacy = legacy_full.decode("utf-8").replace("\r\n", "\n")
    if normalized_body == normalized_legacy:
        return bom + block + b"\n", "migrated", None
    if body.startswith(legacy_header):
        remainder = body[len(legacy_header) :].lstrip(b"\r\n")
        return bom + block + b"\n\n" + remainder, "migrated", None
    if LEGACY_WORKFLOW_MARKER.encode("ascii") in body:
        return bom + block + b"\n\n" + body, "prepended", "Unrecognized legacy AgentForge block was preserved"
    return bom + block + b"\n\n" + body, "prepended", None


def _retire_legacy_agents(project: Path, dry_run: bool) -> list[tuple[Path, str]]:
    changes: list[tuple[Path, str]] = []
    for role in ("architect", "developer", "reviewer"):
        destination = project / ".opencode/agents" / f"{role}.md"
        if not destination.is_file():
            continue
        try:
            current = destination.read_text(encoding="utf-8").replace("\r\n", "\n")
        except (OSError, UnicodeError):
            changes.append((destination, "preserved-legacy"))
            continue
        legacy = template_text(f"legacy_{role}_v1.md").replace("\r\n", "\n")
        retired = legacy.replace("mode: primary\n", "mode: primary\ndisable: true\n", 1)
        retired = retired.replace("mode: subagent\n", "mode: subagent\ndisable: true\n", 1)
        if current == retired:
            changes.append((destination, "retired-legacy"))
            continue
        if current != legacy:
            changes.append((destination, "preserved-legacy"))
            continue
        if not dry_run:
            atomic_write_bytes(destination, retired.encode("utf-8"))
        changes.append((destination, "retired-legacy"))
    return changes


def _configure_api_worker(path: Path, auth_source: str | None, dry_run: bool) -> str:
    enabled = template_text("deepseek-worker.md")
    disabled = enabled.replace("mode: subagent\n", "mode: subagent\ndisable: true\n", 1)
    if not path.exists():
        if not auth_source:
            return "optional-unavailable"
        return write_if_absent(path, enabled, dry_run)
    try:
        current = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    except (OSError, UnicodeError):
        return "preserved-unavailable" if not auth_source else "preserved"
    enabled_normalized = enabled.replace("\r\n", "\n")
    disabled_normalized = disabled.replace("\r\n", "\n")
    if auth_source and current == disabled_normalized:
        if not dry_run:
            atomic_write_bytes(path, enabled.encode("utf-8"))
        return "enabled"
    if not auth_source and current == enabled_normalized:
        if not dry_run:
            atomic_write_bytes(path, disabled.encode("utf-8"))
        return "disabled-unavailable"
    if not auth_source and current == disabled_normalized:
        return "optional-unavailable"
    return "preserved" if auth_source else "preserved-unavailable"


def configure_agents(
    project: Path,
    dry_run: bool = False,
    deepseek_configured: bool | None = None,
) -> tuple[list[tuple[Path, str]], list[str], str | None]:
    project = project.resolve()
    changes: list[tuple[Path, str]] = []
    warnings: list[str] = []

    agents_path = project / "AGENTS.md"
    full_block = template_text("agents.md")
    existing_block = full_block.rstrip().encode("utf-8")
    if not agents_path.exists():
        status = write_if_absent(agents_path, full_block, dry_run)
    else:
        try:
            existing = agents_path.read_bytes()
            existing.decode("utf-8-sig")
        except (OSError, UnicodeError) as exc:
            status = "preserved"
            warnings.append(f"Could not safely update {agents_path}: {exc}")
        else:
            updated, status, warning = _replace_owned_workflow(existing, existing_block)
            if warning:
                warnings.append(warning)
            if updated != existing and not dry_run:
                atomic_write_bytes(agents_path, updated)
    changes.append((agents_path, status))

    portable_roles = ("main-agent.md", "deepseek-worker-free.md", "deepseek-worker.md")
    for role in portable_roles:
        destination = project / ".agentforge" / role
        changes.append((destination, write_if_absent(destination, template_text(role), dry_run)))

    free_worker = project / ".opencode/agents/deepseek-worker-free.md"
    changes.append((free_worker, write_if_absent(free_worker, template_text("deepseek-worker-free.md"), dry_run)))

    auth_source = deepseek_auth_source() if deepseek_configured is None else ("test" if deepseek_configured else None)
    api_worker = project / ".opencode/agents/deepseek-worker.md"
    changes.append((api_worker, _configure_api_worker(api_worker, auth_source, dry_run)))

    managed_ignore = project / ".agentforge/.gitignore"
    changes.append((managed_ignore, write_if_absent(managed_ignore, template_text("agentforge_gitignore"), dry_run)))
    root_ignore = project / ".gitignore"
    ignore_status = ensure_text_block(root_ignore, template_text("gitignore_secrets"), "# AGENTFORGE:BEGIN SECRETS", dry_run)
    changes.append((root_ignore, ignore_status))
    changes.extend(_retire_legacy_agents(project, dry_run))
    return changes, warnings, auth_source


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", nargs="?", default=".")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    changes, warnings, auth_source = configure_agents(Path(args.project), args.dry_run)
    print("\n".join(format_changes(changes)))
    print(f"DeepSeek API worker: {'configured via ' + auth_source if auth_source else 'optional / not configured'}")
    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    return 1 if warnings else 0


if __name__ == "__main__":
    sys.exit(main())
