"""Local handoff fixes that are not part of the inherited upstream tests."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/handoff/scripts"
TOOL = SCRIPTS / "handoff.py"
sys.path.insert(0, str(SCRIPTS))

from feather_handoff import cli, history, observations, storage  # noqa: E402

COMPLETED = "2026-09-11T10:00:00+08:00"
FAKE = "## Bar · 完成：2020-01-01T00:00:00+00:00"


def record(title="Foo", status="完成", updated=COMPLETED, details="證據。", eol="\n", heading=None):
    text = (f"# {heading or title}\n更新：{updated}\n狀態：{status}\n目標：g\n進度：p\n下一步：n\n"
            f"\n## 詳細紀錄\n{details}\n")
    return text.replace("\n", eol).encode("utf-8")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class LocalFixesBase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name)
        self.directory = self.project / ".feather/handoffs"
        self.directory.mkdir(parents=True)
        self.history = self.directory / "history.md"

    def run_tool(self, *args, payload=None, raw=None, expected=0) -> dict:
        data = raw if raw is not None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        result = subprocess.run([sys.executable, "-B", str(TOOL), "--project", str(self.project), *args],
                                input=data, capture_output=True, timeout=30)
        stdout = result.stdout.decode("utf-8")
        self.assertEqual(result.returncode, expected, stdout + result.stderr.decode("utf-8", "replace"))
        return json.loads(stdout)

    def put(self, name: str, data: bytes) -> Path:
        path = self.directory / name
        path.write_bytes(data)
        return path

    def archive(self, name: str, data: bytes | None = None, expected=0) -> dict:
        data = self.put(name, data).read_bytes() if data is not None else (self.directory / name).read_bytes()
        return self.run_tool("archive", "--work", name, payload={"version": sha(data)}, expected=expected)


class CompletedBodyTest(LocalFixesBase):
    def test_create_completed_with_fake_history_heading_writes_nothing(self):
        payload = {"title": "Foo", "fields": {"updated": COMPLETED, "status": "完成", "goal": "g",
                                              "progress": "p", "next": "n"},
                   "details": f"x\n{FAKE}\ny"}
        result = self.run_tool("create", "--work", "a.md", payload=payload, expected=2)
        self.assertEqual(result["code"], "format")
        self.assertFalse((self.directory / "a.md").exists())
        self.assertFalse(self.history.exists())

    def test_active_work_with_fake_heading_saves_but_cannot_become_completed(self):
        payload = {"title": "Foo", "fields": {"updated": COMPLETED, "goal": "g", "progress": "p", "next": "n"},
                   "details": f"x\n{FAKE}\ny"}
        self.run_tool("create", "--work", "a.md", payload=payload)
        path = self.directory / "a.md"
        before = path.read_bytes()
        result = self.run_tool("update", "--work", "a.md", expected=2,
                               payload={"version": sha(before), "fields": {"status": "完成"}})
        self.assertEqual(result["code"], "format")
        self.assertEqual(path.read_bytes(), before)
        self.assertIn("狀態：進行中", before.decode("utf-8"))
        self.assertFalse(self.history.exists())

    def test_title_line_whitespace_archives_with_the_stripped_title(self):
        for name, heading in (("a.md", "Foo  "), ("b.md", " Bar")):
            self.put(name, record(title=heading.strip(), heading=heading, updated=COMPLETED if name == "a.md"
                                  else "2026-09-12T10:00:00+08:00"))
            result = self.archive(name)
            self.assertEqual(result["title"], heading.strip())
            self.assertFalse((self.directory / name).exists())
        text = self.history.read_text(encoding="utf-8")
        self.assertIn(f"## Foo · 完成：{COMPLETED}\n", text)
        entries = self.run_tool("history")["entries"]
        self.assertEqual({entry["title"] for entry in entries}, {"Foo", "Bar"})

    def test_stuck_completed_work_reports_replacement_path_and_can_be_repaired(self):
        stuck = record(details=f"x\n{FAKE}\ny")
        path = self.put("a.md", stuck)
        result = self.archive("a.md", expected=2)
        self.assertEqual(result["code"], "format")
        self.assertIn("replacement", result["message"])
        self.assertIn(FAKE, result["message"])
        self.assertFalse(self.history.exists())
        self.assertEqual(path.read_bytes(), stuck)

        fixed = record(details="x\nBar reworded\ny")
        report = self.run_tool("update", "--work", "a.md",
                               payload={"version": sha(stuck), "replacement": fixed.decode("utf-8")})
        self.assertTrue(report["archived"])
        self.assertFalse(path.exists())
        self.assertIn(b"Bar reworded", self.history.read_bytes())

    def test_replacement_of_completed_work_must_keep_identity_and_status(self):
        original = record()
        path = self.put("a.md", original)
        refused = {
            "updated": record(updated="2026-09-12T10:00:00+08:00"),
            "title": record(title="Other"),
            "status": record(status="進行中"),
        }
        for label, replacement in refused.items():
            with self.subTest(label):
                result = self.run_tool("update", "--work", "a.md", expected=2,
                                       payload={"version": sha(original), "replacement": replacement.decode("utf-8")})
                self.assertEqual(result["code"], "completed")
                self.assertEqual(path.read_bytes(), original)
        result = self.run_tool("update", "--work", "a.md", expected=2,
                               payload={"version": sha(original), "fields": {"progress": "q"}})
        self.assertEqual(result["code"], "completed")
        self.assertEqual(path.read_bytes(), original)
        self.assertFalse(self.history.exists())

    def test_replacement_is_refused_when_history_already_holds_the_identity(self):
        stuck = record(details=f"x\n{FAKE}\ny")
        path = self.put("a.md", stuck)
        self.history.write_bytes(f"# 交接歷史\n\n## Foo · 完成：{COMPLETED}\nbody\n".encode("utf-8"))
        history_before = self.history.read_bytes()
        result = self.run_tool("update", "--work", "a.md", expected=2,
                               payload={"version": sha(stuck), "replacement": record().decode("utf-8")})
        self.assertEqual(result["code"], "completed")
        self.assertEqual(path.read_bytes(), stuck)
        self.assertEqual(self.history.read_bytes(), history_before)


class CliContractTest(LocalFixesBase):
    def test_invalid_stdin_is_an_input_error(self):
        for label, raw in (("bracket", b"["), ("deep", b"[" * 100000), ("not-utf8", b"\xff\xfe\x00{")):
            with self.subTest(label):
                result = self.run_tool("clear", raw=raw, expected=2)
                self.assertEqual(result["status"], "error")
                self.assertEqual(result["code"], "input")

    def test_unexpected_exception_becomes_internal_json_error(self):
        out = io.StringIO()
        with mock.patch.object(sys, "argv", ["handoff", "--project", str(self.project), "list"]), \
                mock.patch.object(cli, "list_work", side_effect=RuntimeError("boom")), \
                contextlib.redirect_stdout(out):
            code = cli.main()
        result = json.loads(out.getvalue())
        self.assertEqual(code, 2)
        self.assertEqual((result["status"], result["code"]), ("error", "internal"))
        self.assertEqual(result["message"], "RuntimeError: boom")


class LineEndingTest(LocalFixesBase):
    def test_update_details_follow_the_file_newline(self):
        data = record(status="進行中", eol="\r\n")
        path = self.put("a.md", data)
        self.run_tool("update", "--work", "a.md", payload={"version": sha(data), "details": "a\nb\r\nc\rd"})
        saved = path.read_bytes()
        self.assertIsNone(re.search(rb"(?<!\r)\n", saved))
        self.assertIn(b"a\r\nb\r\nc\r\nd\r\n", saved)

    def test_crlf_history_gets_crlf_marker_and_round_trips(self):
        previous = "# 交接歷史\r\n\r\n## old · 完成：2026-09-10T00:00:00+00:00\r\nold\r\n".encode("utf-8")
        self.history.write_bytes(previous)
        work = record(eol="\r\n")
        result = self.archive("a.md", work)
        self.assertEqual(self.history.read_bytes(),
                         previous + f"## Foo · 完成：{COMPLETED}\r\n".encode("utf-8") + work.split(b"\r\n", 1)[1])
        entries = self.run_tool("history")["entries"]
        self.assertEqual([entry["title"] for entry in entries], ["old", "Foo"])
        self.assertEqual(entries[1]["id"], result["id"])

    def test_new_history_stays_lf(self):
        self.archive("a.md", record(eol="\r\n"))
        self.assertTrue(self.history.read_bytes().startswith("# 交接歷史\n\n".encode("utf-8")))
        self.assertIn(f"## Foo · 完成：{COMPLETED}\n".encode("utf-8"), self.history.read_bytes())

    def test_crlf_separator_after_unterminated_body_is_accepted_on_retry(self):
        self.history.write_bytes("# 交接歷史\r\n\r\n".encode("utf-8"))
        first = record(title="A", eol="\n").rstrip(b"\n")
        self.archive("a.md", first)
        self.archive("b.md", record(title="B", updated="2026-09-12T10:00:00+08:00"))
        saved = self.history.read_bytes()
        self.assertIn(first.split(b"\n", 1)[1] + b"\r\n## B", saved)
        retry = self.archive("a.md", first)
        self.assertFalse(retry["history_appended"])
        self.assertFalse((self.directory / "a.md").exists())
        self.assertEqual(self.history.read_bytes(), saved)


class SmallFixesTest(LocalFixesBase):
    def test_clear_defers_with_pending_archive_for_identical_body(self):
        work = record()
        body = work.split(b"\n", 1)[1]
        self.history.write_bytes(f"# 交接歷史\n\n## Foo · 完成：{COMPLETED}\n".encode("utf-8") + body)
        before = self.history.read_bytes()
        self.put("a.md", work)
        entry = self.run_tool("history")["entries"][0]
        result = self.run_tool("clear", expected=2,
                               payload={"version": entry["document_version"], "ids": [entry["id"]]})
        self.assertEqual(result["code"], "pending-archive")
        self.assertEqual(self.history.read_bytes(), before)
        (self.directory / "a.md").unlink()
        cleared = self.run_tool("clear", payload={"version": entry["document_version"], "ids": [entry["id"]]})
        self.assertEqual(cleared["status"], "ok")

    def test_superscript_com_and_lpt_names_are_reserved(self):
        for name in ("COM¹.md", "com².md", "LPT³", "COM1.md"):
            with self.subTest(name), self.assertRaises(storage.HandoffError) as raised:
                storage.legal_name(name)
            self.assertEqual(raised.exception.code, "unsafe-name")
        storage.legal_name("COM10.md")

    def test_unavailable_inode_does_not_flag_distinct_sources_as_duplicates(self):
        (self.project / "a.txt").write_text("a", encoding="utf-8")
        (self.project / "b.txt").write_text("b", encoding="utf-8")
        zero_inode = lambda info: (info.st_dev, 0, info.st_mode, info.st_nlink, info.st_size, info.st_mtime_ns)
        with mock.patch.object(observations, "signature", zero_inode), \
                mock.patch.object(observations, "git_observation", return_value={"state": "not-repository"}):
            result = observations.capture(storage.Store(str(self.project), exact_root=True),
                                          {"paths": ["a.txt", "b.txt"]})
        self.assertNotIn("duplicate-source", json.dumps(result))
        self.assertEqual([item["state"] for item in result["snapshot"]["files"]], ["present", "present"])

    def test_history_byte_offsets_match_prefix_encoding_with_bom_and_multibyte_text(self):
        text = ("# 交接歷史\n\n## 一 · 完成：2026-09-01T00:00:00+00:00\n內容 😀 é\n"
                "## two · 完成：2026-09-02T00:00:00+00:00\r\nbody\r\n"
                "## 三 · 完成：2026-09-03T00:00:00+00:00\n結尾")
        for bom in (b"", b"\xef\xbb\xbf"):
            data = bom + text.encode("utf-8")
            document = history.parse_history(storage.Snapshot(self.directory / "history.md", data))
            self.assertEqual(len(document.entries), 3)
            for entry in document.entries:
                for offset, expected in ((entry.start, entry.byte_start), (entry.body_start, entry.byte_body_start),
                                         (entry.end, entry.byte_end)):
                    self.assertEqual(expected, len(bom) + len(text[:offset].encode("utf-8")))
                self.assertEqual(entry.content_bytes.decode("utf-8"), entry.content)
                self.assertEqual(entry.body_bytes.decode("utf-8"), entry.body)


if __name__ == "__main__":
    unittest.main()
