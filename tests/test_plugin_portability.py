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


if __name__ == "__main__":
    unittest.main()
