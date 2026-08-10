from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from build_deploy import build_agentforge, build_install_sh  # noqa: E402


class DeployArtifactTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.artifact = self.root / "agentforge"
        self.installer = self.root / "install.sh"
        build_agentforge(self.artifact)
        build_install_sh(self.installer)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_artifact(self, *arguments: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-I", str(self.artifact), *arguments],
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
        )

    def test_generated_artifact_is_self_contained(self) -> None:
        result = self.run_artifact("--version", cwd=self.root)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("AgentForge 0.2.0", result.stdout.strip())
        self.assertNotIn("scripts/", self.artifact.read_text(encoding="utf-8").splitlines()[1])

    def test_generated_artifact_is_reproducible(self) -> None:
        second = self.root / "second-agentforge"
        build_agentforge(second)
        self.assertEqual(self.artifact.read_bytes(), second.read_bytes())

    def test_generated_artifact_initializes_without_external_modules_or_templates(self) -> None:
        project = self.root / "project"
        project.mkdir()
        (project / "app.py").write_text("print('ok')\n", encoding="utf-8")
        result = self.run_artifact("init", str(project), "--skip-install")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertTrue((project / "AGENTS.md").is_file())
        self.assertTrue((project / ".opencode/agents/deepseek-worker-free.md").is_file())
        self.assertFalse((project / ".opencode/agents/deepseek-worker.md").exists())
        config = (project / ".opencode/opencode.json").read_text(encoding="utf-8")
        self.assertIn("pyright", config)
        self.assertNotIn("clangd", config)

    def test_generated_artifact_dry_run_writes_nothing(self) -> None:
        project = self.root / "dry-run"
        project.mkdir()
        before = set(project.iterdir())
        result = self.run_artifact("init", str(project), "--dry-run", "--skip-install")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(before, set(project.iterdir()))

    @unittest.skipUnless(os.name != "nt" and Path("/bin/sh").is_file(), "requires POSIX sh")
    def test_generated_installer_has_valid_shell_syntax(self) -> None:
        subprocess.run(["/bin/sh", "-n", str(self.installer)], check=True)

    @unittest.skipUnless(os.name != "nt" and Path("/bin/sh").is_file(), "requires POSIX sh")
    def test_install_removes_only_recognized_legacy_runtime(self) -> None:
        home = self.root / "home with spaces"
        legacy = home / ".local/share/agentforge"
        (legacy / "scripts").mkdir(parents=True)
        (legacy / "templates").mkdir()
        (legacy / "scripts/agentforge.py").write_text("legacy\n", encoding="utf-8")
        (legacy / "templates/agents.md").write_text("legacy\n", encoding="utf-8")
        environment = os.environ.copy()
        environment["HOME"] = str(home)
        environment["PATH"] = os.environ.get("PATH", "")

        installed = subprocess.run(
            ["/bin/sh", str(self.installer), "--skip-tools", "--project", str(self.root)],
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, installed.returncode, installed.stderr)
        self.assertFalse(legacy.exists())
        self.assertTrue((home / ".local/bin/agentforge").is_file())

        victim = self.root / "unrelated-data"
        victim.mkdir()
        (victim / "keep.txt").write_text("keep\n", encoding="utf-8")
        legacy.parent.mkdir(parents=True, exist_ok=True)
        legacy.symlink_to(victim, target_is_directory=True)
        repeated = subprocess.run(
            ["/bin/sh", str(self.installer), "--skip-tools", "--project", str(self.root)],
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, repeated.returncode, repeated.stderr)
        self.assertTrue(legacy.is_symlink())
        self.assertEqual("keep\n", (victim / "keep.txt").read_text(encoding="utf-8"))
        self.assertIn("Preserved symbolic link", repeated.stderr)


if __name__ == "__main__":
    unittest.main()
