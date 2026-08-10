"""Project type and source-language detection."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path


CPP_SUFFIXES = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx"}
PYTHON_SUFFIXES = {".py", ".pyi"}
SKIP_DIRECTORIES = {
    ".git",
    ".agentforge",
    ".opencode",
    ".venv",
    ".vscode",
    "__pycache__",
    "build",
    "dist",
    "install",
    "log",
    "node_modules",
    "vendor",
}


@dataclass(frozen=True)
class ProjectInfo:
    root: str
    languages: tuple[str, ...]
    cmake: bool
    ros2: bool
    git: bool

    def to_dict(self) -> dict:
        return asdict(self)


def detect_project(project: Path) -> ProjectInfo:
    project = project.resolve()
    languages: set[str] = set()
    cmake = (project / "CMakeLists.txt").is_file()
    ros2 = (project / "package.xml").is_file()

    for root, directories, files in os.walk(project):
        directories[:] = [name for name in directories if name not in SKIP_DIRECTORIES]
        if "CMakeLists.txt" in files:
            cmake = True
        if "package.xml" in files:
            ros2 = True
        for name in files:
            suffix = Path(name).suffix.lower()
            if suffix in CPP_SUFFIXES:
                languages.add("cpp")
            elif suffix in PYTHON_SUFFIXES:
                languages.add("python")
        if languages == {"cpp", "python"} and cmake and ros2:
            break

    return ProjectInfo(
        root=str(project),
        languages=tuple(sorted(languages)),
        cmake=cmake,
        ros2=ros2,
        git=(project / ".git").exists(),
    )
