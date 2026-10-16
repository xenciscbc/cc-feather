"""Handoff tidy ticket 01: the bundled handoff tool, unchanged, carries both merge shapes through its public command.

A partial move writes the target (create for a new record, update for an existing one) and reads it back before the
moved items leave the source; a full merge then completes the source, which the tool archives into history; a gate
note restricting moved and remaining items is copied word for word and stays in the active source (spec Acceptance
item 9, Testing Decisions)."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "skills/handoff/scripts/handoff.py"

ITEM_A = "- 項目A：核對 readiness 端點的 timeout。"
ITEM_B = "- 項目B：補上 port 設定的說明。"
ITEM_C = "- 項目C：清理舊的 log 設定。"
EVIDENCE = "### 證據\nport=7319 已於 2026-09-11 核對。"
GATE_NOTE = "pending acceptance: claim X（項目A 與 項目B 尚待驗收，未經 code review）"
SIBLING = "## 詳細紀錄補充\n人工補充保留。\n"


def source_record(items: list[str], gate_note: str | None = None) -> str:
    details = "### 待辦項目\n" + "\n".join(items) + "\n\n" + EVIDENCE + "\n"
    if gate_note:
        details += "\n" + gate_note + "\n"
    return ("# config-audit\n更新：2026-09-11T10:00:00+08:00\n狀態：進行中\n\n"
            "目標：核對設定\n進度：port=7319；readiness 待確認。\n下一步：核對 readiness\n"
            "注意：timeout 等待使用者決定。\n\n## 詳細紀錄\n" + details + "\n" + SIBLING)


def remaining_details(items: list[str], gate_note: str | None = None) -> str:
    details = "### 待辦項目\n" + "\n".join(items) + "\n\n" + EVIDENCE + "\n"
    if gate_note:
        details += "\n" + gate_note + "\n"
    return details


class HandoffTidyMergeTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.project = Path(os.path.realpath(self.temporary.name))
        self.directory = self.project / ".feather/handoffs"
        self.directory.mkdir(parents=True)
        self.source = self.directory / "config-audit.md"

    def run_tool(self, *args, payload=None, expected=0) -> dict:
        # --exact-root keeps every operation inside the temporary project, never the repository's own .feather/.
        result = subprocess.run(
            [sys.executable, "-B", str(TOOL), "--project", str(self.project), "--exact-root", *args],
            input=json.dumps(payload, ensure_ascii=False) if payload is not None else None,
            capture_output=True, text=True, encoding="utf-8", timeout=15,
        )
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def read(self, work: str) -> dict:
        return self.run_tool("read", "--work", work)

    def write_source(self, content: str) -> bytes:
        data = content.encode("utf-8")
        self.source.write_bytes(data)
        return data

    def create_existing_target(self) -> None:
        self.run_tool("create", "--work", "readiness.md", payload={
            "title": "readiness", "fields": {"goal": "整理 readiness 檢查", "progress": "已列出既有檢查。",
                                             "next": "補齊 timeout 檢查"},
            "details": "### 待辦項目\n- 既有項目：列出 readiness 檢查。\n"})

    def remove_moved_items_from_source(self, remaining: list[str], gate_note: str | None = None) -> dict:
        current = self.read(self.source.name)
        return self.run_tool("update", "--work", self.source.name, payload={
            "version": current["version"], "details": remaining_details(remaining, gate_note)})

    def assert_source_keeps_only(self, remaining: list[str], moved: list[str]) -> dict:
        read = self.read(self.source.name)
        content = read["content"]
        for item in remaining:
            self.assertIn(item, content)
        for item in moved:
            self.assertNotIn(item, content)
        # The source's other fields and sections are intact.
        self.assertEqual(read["goal"], "核對設定")
        self.assertEqual(read["progress"], "port=7319；readiness 待確認。")
        self.assertEqual(read["next"], "核對 readiness")
        self.assertEqual(read["notes"], "timeout 等待使用者決定。")
        self.assertIn(EVIDENCE, content)
        self.assertTrue(content.endswith(SIBLING), content)
        self.assertEqual(read["record_status"], "進行中")
        return read

    def test_partial_move_into_a_new_target_writes_and_reads_it_back_before_the_source(self):
        original = self.write_source(source_record([ITEM_A, ITEM_B, ITEM_C]))
        created = self.run_tool("create", "--work", "readiness.md", payload={
            "title": "readiness", "fields": {"goal": "整理 readiness 檢查", "progress": "自 config-audit 移入。",
                                             "next": "核對 timeout"},
            "details": "### 待辦項目\n" + ITEM_A + "\n"})
        self.assertEqual(created["status"], "ok")
        target = self.read("readiness.md")
        self.assertIn(ITEM_A, target["content"])
        self.assertEqual(target["version"], created["version"])
        self.assertEqual(self.source.read_bytes(), original, "the source changes only after the target is read back")

        updated = self.remove_moved_items_from_source([ITEM_B, ITEM_C])
        self.assertEqual(updated["status"], "ok")
        self.assert_source_keeps_only([ITEM_B, ITEM_C], [ITEM_A])
        self.assertIn(ITEM_A, self.read("readiness.md")["content"])

    def test_partial_move_into_an_existing_target_updates_and_reads_it_back_before_the_source(self):
        self.create_existing_target()
        original = self.write_source(source_record([ITEM_A, ITEM_B, ITEM_C]))
        before = self.read("readiness.md")
        moved = self.run_tool("update", "--work", "readiness.md", payload={
            "version": before["version"],
            "details": "### 待辦項目\n- 既有項目：列出 readiness 檢查。\n" + ITEM_A + "\n"})
        self.assertEqual(moved["status"], "ok")
        target = self.read("readiness.md")
        self.assertIn(ITEM_A, target["content"])
        self.assertIn("- 既有項目：列出 readiness 檢查。", target["content"])
        self.assertEqual(target["goal"], "整理 readiness 檢查")
        self.assertEqual(self.source.read_bytes(), original, "the source changes only after the target is read back")

        self.remove_moved_items_from_source([ITEM_B, ITEM_C])
        self.assert_source_keeps_only([ITEM_B, ITEM_C], [ITEM_A])

    def test_full_merge_completes_and_archives_the_source_into_history(self):
        self.create_existing_target()
        original = self.write_source(source_record([ITEM_A, ITEM_B, ITEM_C]))
        before = self.read("readiness.md")
        self.run_tool("update", "--work", "readiness.md", payload={
            "version": before["version"],
            "details": "### 待辦項目\n- 既有項目：列出 readiness 檢查。\n" + "\n".join([ITEM_A, ITEM_B, ITEM_C]) + "\n"})
        target = self.read("readiness.md")
        for item in (ITEM_A, ITEM_B, ITEM_C):
            self.assertIn(item, target["content"])
        self.assertEqual(self.source.read_bytes(), original, "the source changes only after the target is read back")

        progress = "已全部併入 readiness.md，本紀錄無剩餘工作。"
        current = self.read(self.source.name)
        completed = self.run_tool("update", "--work", self.source.name, payload={
            "version": current["version"],
            "fields": {"status": "完成", "progress": progress, "next": "無"},
            "details": "### 已移出項目\n項目A、項目B、項目C 已移至 readiness.md。\n\n" + EVIDENCE + "\n"})
        self.assertEqual(completed["status"], "ok", completed)
        self.assertTrue(completed["archived"])
        self.assertTrue(completed["history_appended"])
        self.assertFalse(self.source.exists())

        listed = self.run_tool("list")
        self.assertTrue(listed["complete"])
        self.assertEqual([item["work"] for item in listed["items"]], ["readiness.md"])

        history = self.run_tool("history", "--work", "config-audit")
        self.assertTrue(history["complete"])
        self.assertEqual(len(history["entries"]), 1)
        entry = history["entries"][0]
        self.assertEqual(entry["title"], "config-audit")
        self.assertIn("狀態：完成", entry["body"])
        self.assertIn("進度：" + progress, entry["body"])
        self.assertIn("readiness.md", entry["body"])

    def test_gate_note_is_copied_word_for_word_and_the_source_stays_active(self):
        self.write_source(source_record([ITEM_A, ITEM_B, ITEM_C], GATE_NOTE))
        original = self.source.read_bytes()
        self.run_tool("create", "--work", "readiness.md", payload={
            "title": "readiness", "fields": {"goal": "整理 readiness 檢查", "progress": "自 config-audit 移入。",
                                             "next": "核對 timeout"},
            "details": "### 待辦項目\n" + ITEM_A + "\n\n" + GATE_NOTE + "\n"})
        target = self.read("readiness.md")
        self.assertIn(ITEM_A, target["content"])
        self.assertIn("\n" + GATE_NOTE + "\n", target["content"])
        self.assertEqual(self.source.read_bytes(), original, "the source changes only after the target is read back")

        # Item B, which the note restricts, remains, so the note stays in the source.
        self.remove_moved_items_from_source([ITEM_B, ITEM_C], GATE_NOTE)
        source = self.assert_source_keeps_only([ITEM_B, ITEM_C], [ITEM_A])
        self.assertIn("\n" + GATE_NOTE + "\n", source["content"])
        self.assertIn("\n狀態：進行中\n", source["content"])

        listed = self.run_tool("list")
        self.assertEqual({item["work"]: item["record_status"] for item in listed["items"]},
                         {"config-audit.md": "進行中", "readiness.md": "進行中"})
        self.assertEqual(self.run_tool("history")["status"], "missing")
        self.assertFalse((self.directory / "history.md").exists())


if __name__ == "__main__":
    unittest.main()
