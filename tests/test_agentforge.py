from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from adapt_project import adapt_project, collect_compile_commands, project_kind  # noqa: E402
from common import WORKFLOW_BEGIN, WORKFLOW_END, template_text  # noqa: E402
from configure_agents import configure_agents  # noqa: E402
from configure_lsp import configure_lsp, migrate_legacy_global_lsp  # noqa: E402
from detect_env import Environment  # noqa: E402
from project_detection import detect_project  # noqa: E402
from verify import FREE_MODEL, ready, verify_project  # noqa: E402


class AgentForgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def configure(self, api: bool = False) -> None:
        configure_agents(self.project, deepseek_configured=api)
        configure_lsp(self.project)

    def test_new_project_creates_main_and_free_worker_without_api_worker(self) -> None:
        changes, warnings, auth = configure_agents(self.project, deepseek_configured=False)
        lsp_changes, lsp_warnings = configure_lsp(self.project)

        self.assertFalse(warnings + lsp_warnings)
        self.assertIsNone(auth)
        self.assertIn((self.project / ".opencode/agents/deepseek-worker.md", "optional-unavailable"), changes)
        self.assertTrue((self.project / ".agentforge/main-agent.md").is_file())
        free = (self.project / ".opencode/agents/deepseek-worker-free.md").read_text(encoding="utf-8")
        self.assertIn("mode: subagent", free)
        self.assertIn("model: opencode/deepseek-v4-flash-free", free)
        self.assertFalse((self.project / ".opencode/agents/deepseek-worker.md").exists())
        workflow = (self.project / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn(WORKFLOW_BEGIN, workflow)
        self.assertIn(WORKFLOW_END, workflow)
        self.assertIn("*.agentforge.bak", (self.project / ".gitignore").read_text(encoding="utf-8"))
        config = json.loads((self.project / ".opencode/opencode.json").read_text(encoding="utf-8"))
        self.assertNotIn("lsp", config)
        self.assertTrue(all(status == "created" for _, status in lsp_changes))

    def test_api_worker_is_registered_without_storing_key(self) -> None:
        configure_agents(self.project, deepseek_configured=True)
        worker = (self.project / ".opencode/agents/deepseek-worker.md").read_text(encoding="utf-8")
        self.assertIn("model: deepseek/deepseek-v4-pro", worker)
        self.assertNotIn("apiKey", worker)
        self.assertNotIn("sk-", worker)

    def test_environment_api_key_enables_worker_without_persisting_value(self) -> None:
        secret = "test-only-secret-value"
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": secret}):
            _, warnings, source = configure_agents(self.project)
        self.assertFalse(warnings)
        self.assertEqual("DEEPSEEK_API_KEY", source)
        worker = (self.project / ".opencode/agents/deepseek-worker.md").read_text(encoding="utf-8")
        self.assertNotIn(secret, worker)

    def test_api_worker_is_disabled_when_auth_disappears_and_reenabled(self) -> None:
        configure_agents(self.project, deepseek_configured=True)
        changes, _, _ = configure_agents(self.project, deepseek_configured=False)
        worker = self.project / ".opencode/agents/deepseek-worker.md"
        self.assertIn((worker, "disabled-unavailable"), changes)
        self.assertIn("disable: true", worker.read_text(encoding="utf-8"))
        changes, _, _ = configure_agents(self.project, deepseek_configured=True)
        self.assertIn((worker, "enabled"), changes)
        self.assertNotIn("disable: true", worker.read_text(encoding="utf-8"))

    def test_language_detection_and_selective_lsp(self) -> None:
        (self.project / "src").mkdir()
        (self.project / "src/main.cpp").write_text("int main() {}\n", encoding="utf-8")
        (self.project / "tool.py").write_text("print('ok')\n", encoding="utf-8")
        (self.project / "node_modules").mkdir()
        (self.project / "node_modules/ignored.c").write_text("ignored", encoding="utf-8")
        info = detect_project(self.project)
        self.assertEqual(("cpp", "python"), info.languages)
        configure_lsp(self.project, languages=info.languages)
        config = json.loads((self.project / ".opencode/opencode.json").read_text(encoding="utf-8"))
        self.assertEqual({"clangd", "pyright"}, set(config["lsp"]))

    def test_python_only_does_not_configure_clangd(self) -> None:
        (self.project / "main.py").write_text("pass\n", encoding="utf-8")
        configure_lsp(self.project)
        config = json.loads((self.project / ".opencode/opencode.json").read_text(encoding="utf-8"))
        self.assertEqual({"pyright"}, set(config["lsp"]))

    def test_unmodified_legacy_full_lsp_config_is_migrated_selectively(self) -> None:
        (self.project / "main.py").write_text("pass\n", encoding="utf-8")
        configure_lsp(self.project, languages=("cpp", "python"))
        changes, warnings = configure_lsp(self.project)
        self.assertFalse(warnings)
        self.assertEqual("migrated", changes[0][1])
        config = json.loads((self.project / ".opencode/opencode.json").read_text(encoding="utf-8"))
        self.assertEqual({"pyright"}, set(config["lsp"]))
        self.assertTrue((self.project / ".opencode/opencode.json.agentforge.bak").is_file())

    def test_exact_legacy_global_lsp_is_backed_up_and_retired(self) -> None:
        previous = os.environ.get("XDG_CONFIG_HOME")
        config_root = self.project / "global-config"
        os.environ["XDG_CONFIG_HOME"] = str(config_root)
        try:
            global_config = config_root / "opencode/opencode.json"
            global_config.parent.mkdir(parents=True)
            configure_lsp(self.project, languages=("cpp", "python"))
            global_config.write_bytes((self.project / ".opencode/opencode.json").read_bytes())
            changes, warnings = migrate_legacy_global_lsp()
        finally:
            if previous is None:
                os.environ.pop("XDG_CONFIG_HOME", None)
            else:
                os.environ["XDG_CONFIG_HOME"] = previous
        self.assertFalse(warnings)
        self.assertEqual("migrated-legacy", changes[0][1])
        self.assertEqual({"$schema": "https://opencode.ai/config.json"}, json.loads(global_config.read_text(encoding="utf-8")))
        self.assertTrue(global_config.with_name("opencode.json.agentforge.bak").is_file())

    def test_existing_agents_is_prepended_once_and_body_is_preserved(self) -> None:
        original = b"# Existing rules\r\n\r\nKeep this exact body.\r\n"
        (self.project / "AGENTS.md").write_bytes(original)
        first, warnings, _ = configure_agents(self.project, deepseek_configured=False)
        after_first = (self.project / "AGENTS.md").read_bytes()
        second, second_warnings, _ = configure_agents(self.project, deepseek_configured=False)
        after_second = (self.project / "AGENTS.md").read_bytes()
        self.assertFalse(warnings + second_warnings)
        self.assertEqual("prepended", first[0][1])
        self.assertEqual("unchanged", second[0][1])
        self.assertTrue(after_first.endswith(original))
        self.assertEqual(after_first, after_second)

    def test_owned_agents_block_is_updated_without_touching_user_body(self) -> None:
        path = self.project / "AGENTS.md"
        path.write_text(f"{WORKFLOW_BEGIN}\nold block\n{WORKFLOW_END}\n\n# User rule\nkeep\n", encoding="utf-8")
        changes, warnings, _ = configure_agents(self.project, deepseek_configured=False)
        updated = path.read_text(encoding="utf-8")
        self.assertFalse(warnings)
        self.assertEqual("updated", changes[0][1])
        self.assertIn("# User rule\nkeep\n", updated)
        self.assertNotIn("old block", updated)

    def test_legacy_generated_agents_is_migrated(self) -> None:
        (self.project / "AGENTS.md").write_text(template_text("legacy_agents_v1.md"), encoding="utf-8")
        changes, warnings, _ = configure_agents(self.project, deepseek_configured=False)
        migrated = (self.project / "AGENTS.md").read_text(encoding="utf-8")
        self.assertFalse(warnings)
        self.assertEqual("migrated", changes[0][1])
        self.assertIn(WORKFLOW_BEGIN, migrated)
        self.assertNotIn("Architect Agent", migrated)

    def test_unmodified_legacy_opencode_agent_is_disabled_not_deleted(self) -> None:
        legacy = self.project / ".opencode/agents/developer.md"
        legacy.parent.mkdir(parents=True)
        legacy.write_text(template_text("legacy_developer_v1.md"), encoding="utf-8")
        changes, warnings, _ = configure_agents(self.project, deepseek_configured=False)
        self.assertFalse(warnings)
        self.assertIn((legacy, "retired-legacy"), changes)
        self.assertTrue(legacy.is_file())
        self.assertIn("disable: true", legacy.read_text(encoding="utf-8"))

    def test_modified_legacy_opencode_agent_is_preserved(self) -> None:
        legacy = self.project / ".opencode/agents/developer.md"
        legacy.parent.mkdir(parents=True)
        customized = template_text("legacy_developer_v1.md") + "\nCustom user rule.\n"
        legacy.write_text(customized, encoding="utf-8")
        changes, _, _ = configure_agents(self.project, deepseek_configured=False)
        self.assertIn((legacy, "preserved-legacy"), changes)
        self.assertEqual(customized, legacy.read_text(encoding="utf-8"))

    def test_existing_agents_preserves_bom(self) -> None:
        path = self.project / "AGENTS.md"
        original = b"\xef\xbb\xbf# Existing\r\n"
        path.write_bytes(original)
        configure_agents(self.project, deepseek_configured=False)
        updated = path.read_bytes()
        self.assertTrue(updated.startswith(b"\xef\xbb\xbf"))
        self.assertTrue(updated.endswith(original[3:]))

    def test_json_conflicts_are_backed_up_and_user_values_win(self) -> None:
        (self.project / "main.py").write_text("pass\n", encoding="utf-8")
        path = self.project / ".opencode/opencode.json"
        path.parent.mkdir(parents=True)
        custom = {"$schema": "custom-schema", "permission": {"edit": "ask"}}
        original = json.dumps(custom).encode("utf-8")
        path.write_bytes(original)
        changes, warnings = configure_lsp(self.project)
        merged = json.loads(path.read_text(encoding="utf-8"))
        self.assertFalse(warnings)
        self.assertEqual("merged+backup", changes[0][1])
        self.assertEqual(original, path.with_name("opencode.json.agentforge.bak").read_bytes())
        self.assertEqual("custom-schema", merged["$schema"])
        self.assertEqual("ask", merged["permission"]["edit"])
        self.assertIn("pyright", merged["lsp"])

    def test_invalid_existing_json_is_left_byte_for_byte(self) -> None:
        path = self.project / ".opencode/opencode.json"
        path.parent.mkdir(parents=True)
        invalid = b"{ user: 'jsonc' }\n"
        path.write_bytes(invalid)
        changes, warnings = configure_lsp(self.project)
        self.assertEqual("preserved", changes[0][1])
        self.assertTrue(warnings)
        self.assertEqual(invalid, path.read_bytes())

    def test_dry_run_writes_nothing(self) -> None:
        configure_agents(self.project, dry_run=True, deepseek_configured=False)
        configure_lsp(self.project, dry_run=True)
        self.assertEqual([], list(self.project.iterdir()))

    def test_full_configuration_is_idempotent(self) -> None:
        self.configure()
        first = {path.relative_to(self.project): path.read_bytes() for path in self.project.rglob("*") if path.is_file()}
        self.configure()
        second = {path.relative_to(self.project): path.read_bytes() for path in self.project.rglob("*") if path.is_file()}
        self.assertEqual(first, second)

    def test_project_detection_and_managed_prepare_path(self) -> None:
        (self.project / "CMakeLists.txt").write_text("project(example)\n", encoding="utf-8")
        self.assertEqual("cmake", project_kind(self.project))
        result = adapt_project(self.project, dry_run=True)
        if result.status == "planned":
            self.assertIn(str(self.project / ".agentforge/cmake-build"), " ".join(result.command))
        else:
            self.assertEqual("skipped", result.status)

    def test_init_does_not_run_cmake(self) -> None:
        (self.project / "CMakeLists.txt").write_text("cmake_minimum_required(VERSION 3.16)\nproject(no_build NONE)\n", encoding="utf-8")
        completed = subprocess.run(
            [sys.executable, str(SCRIPTS / "agentforge.py"), "init", str(self.project), "--skip-install"],
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, completed.returncode, completed.stderr.decode("utf-8", errors="replace"))
        self.assertFalse((self.project / ".agentforge/cmake-build").exists())

    def test_prepare_preserves_existing_root_compile_database(self) -> None:
        (self.project / "CMakeLists.txt").write_text("project(existing)\n", encoding="utf-8")
        database = self.project / "compile_commands.json"
        original = b"[]\n"
        database.write_bytes(original)
        result = adapt_project(self.project)
        self.assertEqual("ready", result.status)
        self.assertEqual(original, database.read_bytes())

    @unittest.skipUnless(shutil.which("cmake"), "cmake is not installed")
    def test_cmake_prepare_configures_without_building(self) -> None:
        (self.project / "CMakeLists.txt").write_text(
            "cmake_minimum_required(VERSION 3.16)\nproject(agentforge_smoke NONE)\n",
            encoding="utf-8",
        )
        result = adapt_project(self.project)
        self.assertEqual("configured", result.status)
        self.assertTrue((self.project / ".agentforge/cmake-build/CMakeCache.txt").is_file())

    def test_ros_compile_databases_are_combined(self) -> None:
        first = self.project / ".agentforge/ros-build/one/compile_commands.json"
        second = self.project / ".agentforge/ros-build/two/compile_commands.json"
        first.parent.mkdir(parents=True)
        second.parent.mkdir(parents=True)
        first.write_text(json.dumps([{"file": "one.c"}]), encoding="utf-8")
        second.write_text(json.dumps([{"file": "two.c"}]), encoding="utf-8")
        self.assertEqual(2, collect_compile_commands(self.project, "ros2"))

    def test_verify_allows_missing_optional_api_worker(self) -> None:
        (self.project / "main.py").write_text("pass\n", encoding="utf-8")
        self.configure()
        tools = {name: f"/{name}" for name in ("git", "node", "npm", "opencode", "pyright")}
        tools.update({name: None for name in ("cmake", "ninja", "clangd", "vscode", "colcon")})
        environment = Environment("Linux", "test", "x86_64", "Linux Local Development", False, tools)
        checks = verify_project(
            self.project,
            environment=environment,
            auth_source=None,
            model_catalog={FREE_MODEL},
        )
        self.assertTrue(ready(checks))
        optional = next(check for check in checks if check.name == "deepseek-worker")
        self.assertFalse(optional.required)

    @unittest.skipUnless(os.name != "nt" and shutil.which("sh"), "requires a POSIX shell")
    def test_linux_installer_is_repeatable_from_installed_copy(self) -> None:
        profile = self.project / "profile"
        profile.mkdir()
        environment = os.environ.copy()
        environment["HOME"] = str(profile)
        environment["XDG_DATA_HOME"] = str(profile / "data")
        root_installer = SCRIPTS.parent / "install.sh"
        command = ["sh", str(root_installer), "--skip-tools", "--project", str(self.project)]
        subprocess.run(command, env=environment, check=True, capture_output=True)
        installed = profile / "data/agentforge/install.sh"
        subprocess.run(["sh", str(installed), "--skip-tools", "--project", str(self.project)], env=environment, check=True, capture_output=True)
        self.assertTrue((profile / ".local/bin/agentforge").is_file())

    @unittest.skipUnless(os.name == "nt" and shutil.which("cmd.exe"), "requires Windows cmd.exe")
    def test_windows_checkout_launcher_runs_with_python_launcher(self) -> None:
        launcher = SCRIPTS.parent / "agentforge.cmd"
        result = subprocess.run(
            ["cmd.exe", "/d", "/c", str(launcher), "doctor", str(self.project)],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("AgentForge Environment Check", result.stdout)


if __name__ == "__main__":
    unittest.main()
