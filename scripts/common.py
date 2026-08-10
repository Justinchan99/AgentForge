"""Shared filesystem and configuration helpers for AgentForge."""

from __future__ import annotations

import json
import os
import shutil
import stat
import tempfile
from pathlib import Path
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_ROOT = PROJECT_ROOT / "templates"
WORKFLOW_BEGIN = "<!-- AGENTFORGE:BEGIN -->"
WORKFLOW_END = "<!-- AGENTFORGE:END -->"
LEGACY_WORKFLOW_MARKER = "<!-- agentforge-workflow:v1 -->"


def command_path(*names: str) -> str | None:
    """Return the first command found on PATH."""
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    return None


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def deep_add_missing(
    current: dict[str, Any],
    defaults: dict[str, Any],
    conflicts: list[str] | None = None,
    prefix: str = "",
) -> bool:
    """Add missing keys recursively without replacing any user value."""
    changed = False
    for key, value in defaults.items():
        if key not in current:
            current[key] = value
            changed = True
        elif isinstance(current[key], dict) and isinstance(value, dict):
            changed = deep_add_missing(current[key], value, conflicts, f"{prefix}{key}.") or changed
        elif current[key] != value and conflicts is not None:
            conflicts.append(f"{prefix}{key}")
    return changed


def atomic_write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
        if path.exists():
            os.chmod(temporary, stat.S_IMODE(path.stat().st_mode))
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def atomic_write_text(path: Path, content: str) -> None:
    atomic_write_bytes(path, content.encode("utf-8"))


def write_if_absent(path: Path, content: str, dry_run: bool = False) -> str:
    if path.exists():
        return "preserved"
    if not dry_run:
        atomic_write_text(path, content)
    return "created"


def ensure_text_block(path: Path, block: str, marker: str, dry_run: bool = False) -> str:
    """Append one owned text block while preserving all existing bytes."""
    encoded = block.rstrip().encode("utf-8") + b"\n"
    if not path.exists():
        if not dry_run:
            atomic_write_bytes(path, encoded)
        return "created"
    try:
        existing = path.read_bytes()
        decoded = existing.decode("utf-8-sig")
    except (OSError, UnicodeError):
        return "preserved"
    if marker in decoded:
        return "unchanged"
    separator = b"" if not existing or existing.endswith((b"\n", b"\r")) else b"\n"
    if not dry_run:
        atomic_write_bytes(path, existing + separator + b"\n" + encoded)
    return "appended"


def template_text(name: str) -> str:
    return (TEMPLATE_ROOT / name).read_text(encoding="utf-8")


def render_template(name: str, replacements: dict[str, str] | None = None) -> str:
    content = template_text(name)
    for key, value in (replacements or {}).items():
        content = content.replace("{{" + key + "}}", value)
    return content


def merge_json_file(
    destination: Path,
    defaults: dict[str, Any],
    dry_run: bool = False,
) -> tuple[str, str | None]:
    """Safely create or merge a JSON object, preserving all existing values."""
    if not destination.exists():
        if not dry_run:
            atomic_write_text(destination, json.dumps(defaults, indent=2) + "\n")
        return "created", None

    try:
        current = load_json(destination)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return "preserved", f"Could not merge {destination}: {exc}"

    conflicts: list[str] = []
    changed = deep_add_missing(current, defaults, conflicts)
    backup_created = False
    if conflicts:
        backup = destination.with_name(destination.name + ".agentforge.bak")
        if not backup.exists() and not dry_run:
            atomic_write_bytes(backup, destination.read_bytes())
            backup_created = True
    if not changed:
        if backup_created:
            return "preserved+backup", None
        return "unchanged", None
    if not dry_run:
        atomic_write_text(destination, json.dumps(current, indent=2) + "\n")
    return "merged+backup" if backup_created else "merged", None


def format_changes(changes: Iterable[tuple[Path, str]]) -> list[str]:
    return [f"{status:>9}  {path}" for path, status in changes]
