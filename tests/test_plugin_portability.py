"""Exercise the bundled runtime after relocation and across Feather hosts."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PluginPortabilityTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.skill = self.base / "plugin cache with spaces" / "skills" / "handoff"
        shutil.copytree(ROOT / "skills/handoff", self.skill)
        self.tool = self.skill / "scripts/handoff.py"
        self.project = self.base / "使用者專案"
        self.project.mkdir()
        self.source = self.project / "source.txt"
        self.source.write_text("original", encoding="utf-8")

    def run_tool(self, tool, *args, payload=None):
        result = subprocess.run(
            [sys.executable, "-B", str(tool), "--project", str(self.project), *args],
            cwd=self.base,
            input=None if payload is None else json.dumps(payload, ensure_ascii=False),
            text=True, encoding="utf-8", capture_output=True, timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def workflow(self, first, second):
        before = {p.relative_to(self.skill): p.read_bytes()
                  for p in self.skill.rglob("*") if p.is_file()}
        snapshot = self.run_tool(first, "snapshot", payload={"paths": ["source.txt"]})["snapshot"]
        created = self.run_tool(first, "create", "--work", "interop.md", payload={
            "title": "跨工具交接", "fields": {
                "goal": "維持相容", "progress": "已記錄", "next": "另一工具接續",
            }, "snapshot": snapshot,
        })
        read = self.run_tool(second, "read", "--work", "interop.md")
        self.assertEqual(read["content"], created["content"])
        compared = self.run_tool(second, "compare", "--work", "interop.md")
        self.assertEqual(compared["files"][0]["comparison"], "unchanged")
        updated = self.run_tool(second, "update", "--work", "interop.md", payload={
            "version": read["version"], "fields": {"progress": "另一工具已接續"},
        })
        self.assertEqual(self.run_tool(first, "read", "--work", "interop.md")["version"], updated["version"])
        self.run_tool(first, "update", "--work", "interop.md", payload={
            "version": updated["version"], "fields": {
                "status": "完成", "progress": "跨工具驗證完成", "next": "無",
            },
        })
        entries = self.run_tool(second, "history")["entries"]
        self.assertEqual(len(entries), 1)
        self.assertIn("## 檔案基準", entries[0]["body"])
        self.assertFalse((self.project / ".feather/handoffs/interop.md").exists())
        self.run_tool(second, "seal", payload={
            "version": entries[0]["document_version"], "ids": [entries[0]["id"]],
            "destination": "interop-batch.md",
        })
        self.assertEqual(self.run_tool(first, "history")["entries"], [])
        sealed = self.run_tool(first, "history", "--include-sealed")["entries"]
        self.assertEqual([entry["id"] for entry in sealed], [entries[0]["id"]])
        self.run_tool(first, "clear", payload={
            "source": sealed[0]["source"], "version": sealed[0]["document_version"],
            "ids": [sealed[0]["id"]],
        })
        self.assertEqual(self.run_tool(second, "history", "--include-sealed")["entries"], [])
        self.assertEqual(before, {p.relative_to(self.skill): p.read_bytes()
                                 for p in self.skill.rglob("*") if p.is_file()})
        self.assertEqual(self.source.read_text(encoding="utf-8"), "original")

    def test_relocated_plugin_has_no_checkout_dependency(self):
        self.workflow(self.tool, self.tool)

    @unittest.skipUnless(os.environ.get("CODEX_FEATHER_ROOT"), "Set CODEX_FEATHER_ROOT for live cross-runtime compatibility")
    def test_codex_and_claude_alternate_on_the_same_records(self):
        upstream = Path(os.environ["CODEX_FEATHER_ROOT"]) / "skills/feather-handoff/scripts/handoff.py"
        self.assertTrue(upstream.is_file(), str(upstream))
        self.workflow(upstream, self.tool)


class SetupPortabilityTest(unittest.TestCase):
    """The setup tool finds its templates from a relocated copy, as in a plugin cache."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.package = self.base / "plugin cache with spaces"
        shutil.copytree(ROOT / "templates", self.package / "templates")
        (self.package / "scripts").mkdir()
        shutil.copy2(ROOT / "scripts/feather_config.py", self.package / "scripts")
        self.tool = self.package / "scripts/feather_config.py"
        self.project = self.base / "使用者專案"
        self.project.mkdir()
        self.claude_home = self.base / "claude home"
        self.claude_home.mkdir()
        # The user home stays inside the temporary directory too, so nothing reads or writes the real one.
        self.user_home = self.base / "user home"
        self.user_home.mkdir()

    def run_setup(self, *args):
        environment = {key: value for key, value in os.environ.items() if key != "CLAUDE_CONFIG_DIR"}
        environment.update(HOME=str(self.user_home), USERPROFILE=str(self.user_home))
        result = subprocess.run(
            [sys.executable, "-B", str(self.tool), *args, "--project", str(self.project),
             "--claude-home", str(self.claude_home)],
            cwd=self.base, env=environment, text=True, encoding="utf-8", capture_output=True, timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def apply(self, *args):
        preview = self.run_setup(*args)
        self.assertEqual(preview["status"], "preview")
        applied = self.run_setup(*args, "--apply", "--expected-plan", preview["plan_id"])
        self.assertEqual(applied["status"], "applied")

    def test_relocated_setup_checks_installs_and_removes(self):
        before = {p.relative_to(self.package): p.read_bytes() for p in self.package.rglob("*") if p.is_file()}
        self.assertEqual(self.run_setup("check", "--scope", "project")["status"], "ok")
        self.apply("install", "--scope", "project", "--component", "both")
        shown = self.run_setup("check", "--scope", "project")
        self.assertEqual((shown["status"], shown["installed"]), ("ok", True), shown)
        self.assertTrue((self.project / ".claude/agents/scout.md").is_file())
        self.assertIn("<!-- cc-feather:handoff:begin -->", (self.project / "CLAUDE.md").read_text(encoding="utf-8"))
        self.apply("remove", "--scope", "project", "--component", "both")
        shown = self.run_setup("check", "--scope", "project")
        self.assertEqual((shown["status"], shown["installed"]), ("ok", False), shown)
        self.assertFalse((self.project / "CLAUDE.md").exists())
        self.assertEqual(list((self.project / ".claude/agents").glob("*.md")), [])
        self.assertEqual(list(self.claude_home.iterdir()), [])
        self.assertEqual(list(self.user_home.iterdir()), [])
        self.assertEqual(before, {p.relative_to(self.package): p.read_bytes()
                                  for p in self.package.rglob("*") if p.is_file()})


if __name__ == "__main__":
    unittest.main()
