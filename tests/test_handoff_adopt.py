"""`adopt` moves leftover records into the current store (worktree store ticket 06).

Trust boundary: the source checkout path in adopt's input, the files of that checkout's `.feather/handoffs/` and the
repository's Git metadata, against the handoff tool's process, which deletes files in the source store. The source
comes only from the input and is validated on every run (S06-2): it resolves strictly to a non-bare checkout listed by
`git worktree list --porcelain -z` from the Working checkout, of the same repository, and is pinned as a root so the
path check covers every path adopt touches there. The stores are distinct (S06-1), every target is created
exclusively and read back before its source is checked and removed (S06-3, S06-4), history is merged under the locks
(S06-5), the target gets create's default tracking (S06-6), and nothing outside the two stores and the target
checkout's ignore rules is written (S06-7).

The fixture and its isolated Git environment are those of tests/test_handoff_shared_store.py: a unique directory made
with mkdtemp under FEATHER_LINK_TEST_DIR when it is set, otherwise the system temporary directory, synthetic data
only, removed on cleanup; GIT_CONFIG_NOSYSTEM, an empty GIT_CONFIG_GLOBAL, HOME and XDG_CONFIG_HOME inside the base and
inherited GIT_* removed. The base holds main/ with one commit, linked worktrees wt1 and wt2 added from it, an empty
outside/ sentinel, and 0.30.0-style records, history and one sealed archive written directly into
wt1/.feather/handoffs/ and, with different names, into wt2/.feather/handoffs/. The tool runs as a subprocess with
--project; the in-process cases drive the CLI entry point while wrapping a storage primitive or a Git start, never
calling the resolver, lock or path helpers directly. A case whose link, short name or denial cannot be made is skipped
with the reason."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest
from unittest import mock

from tests import feather_support
from tests.test_handoff_shared_store import (FIELDS, HOST_TOOLS, SKILL, TOOL_REFERENCE, SharedBase, assert_sentences,
                                             git_call, normalized)
from tests.test_handoff_other_stores import old_record
from tests.test_handoff_unwritable_store import DenyMixin
from feather_handoff import adopt, storage

WINDOWS = os.name == "nt"
LOCK = ".history.lock"
HEADER = "# 交接歷史\n\n"


def entry(title: str, completed: str, body: str = "") -> str:
    return f"## {title} · 完成：{completed}\n更新：{completed}\n狀態：完成\n目標：{title} goal\n{body}\n"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class AdoptBase(DenyMixin, SharedBase):
    def setUp(self):
        super().setUp()
        self.leftovers = {
            self.wt1: {"works": {"a1.md": old_record("a1"), "b1.md": old_record("b1", "受阻")},
                       "history": HEADER + entry("h1a", "2026-09-01T10:00:00+08:00")
                       + entry("h1b", "2026-09-02T10:00:00+08:00"),
                       "archive": {"2026-08-wt1.md": HEADER + entry("s1", "2026-08-01T10:00:00+08:00")}},
            self.wt2: {"works": {"a2.md": old_record("a2"), "b2.md": old_record("b2", "完成")},
                       "history": HEADER + entry("h2a", "2026-09-03T10:00:00+08:00")
                       + entry("h2b", "2026-09-04T10:00:00+08:00"),
                       "archive": {"2026-08-wt2.md": HEADER + entry("s2", "2026-08-02T10:00:00+08:00")}},
        }
        for checkout, records in self.leftovers.items():
            store = checkout / ".feather" / "handoffs"
            (store / "archive").mkdir(parents=True)
            for name, text in records["works"].items():
                (store / name).write_bytes(text.encode("utf-8"))
            (store / "history.md").write_bytes(records["history"].encode("utf-8"))
            for name, text in records["archive"].items():
                (store / "archive" / name).write_bytes(text.encode("utf-8"))

    def source_store(self, checkout: Path) -> Path:
        return checkout / ".feather" / "handoffs"

    def request(self, checkout: Path, works=(), history=None, archives=(), source: str | None = None) -> dict:
        """The input main builds from read-only runs against the source checkout as an explicit root."""
        payload = {"source": source or str(checkout)}
        if works:
            payload["works"] = {name: self.run_tool(checkout, "read", "--work", name, exact=True)["version"]
                                for name in works}
        if history is not None:
            listed = self.run_tool(checkout, "history", exact=True)
            ids = [item["id"] for item in listed["entries"] if history == "all" or item["title"] in history]
            payload["history"] = {"version": listed["documents"][0]["version"], "ids": ids}
        if archives:
            sealed = self.run_tool(checkout, "history", "--include-sealed", exact=True)
            versions = {document["source"]: document["version"] for document in sealed["documents"]}
            payload["archives"] = {name: versions[f"archive/{name}"] for name in archives}
        return payload

    def everything(self, checkout: Path, source: str | None = None) -> dict:
        records = self.leftovers[checkout]
        return self.request(checkout, works=list(records["works"]), history="all", archives=list(records["archive"]),
                            source=source)

    def adopt(self, project: Path, payload: dict, expected: int = 0) -> dict:
        return self.run_tool(project, "adopt", payload=payload, expected=expected)

    def assert_refused(self, result: dict, code: str, before: dict, text: str | None = None):
        self.assertEqual((result["status"], result["complete"], result["code"]), ("error", False, code), result)
        if text is not None:
            self.assertIn(text, result["message"])
        self.assertEqual(self.changed(before, self.tree()), set())

    def locks(self) -> list[Path]:
        return [path for path in (self.store / LOCK, *(self.source_store(c) / LOCK for c in (self.wt1, self.wt2)))
                if os.path.lexists(path)]

    def write_lock(self, directory: Path) -> bytes:
        data = (json.dumps({"created": "2026-11-06T10:00:00.000000+08:00", "host": "fixture-host", "pid": 4242})
                + "\n").encode("utf-8")
        (directory / LOCK).write_bytes(data)
        return data


class MoveTest(AdoptBase):
    """The ticket's cases: adopting a Working checkout's own leftover records and another checkout's, each changing
    only the source store, the target store and the target checkout's ignore rules (S06-6, S06-7)."""

    def test_adopting_the_working_checkouts_own_leftover_records_changes_it_only_under_its_store(self):
        payload = self.everything(self.wt1)
        before = self.tree()
        acquired = []
        real_acquire = adopt.acquire_history_lock

        def recorded(store):
            lock = real_acquire(store)
            acquired.append((str(lock.path), lock.path.exists()))
            return lock
        with mock.patch.object(adopt, "acquire_history_lock", recorded):
            code, result = self.invoke(self.wt1, "adopt", payload=payload)
        self.assertEqual((code, result["status"], result["complete"]), (0, "ok", True), result)
        self.assertEqual(result["root"], self.shared_root(self.wt1), result)
        self.assertEqual((result["source"], result["target"]),
                         ({"checkout": str(self.wt1), "store": str(self.source_store(self.wt1))}, str(self.store)))
        self.assertEqual([(item["work"], item["moved"]) for item in result["works"]], [("a1.md", True), ("b1.md", True)])
        self.assertEqual([(item["archive"], item["moved"]) for item in result["archives"]], [("2026-08-wt1.md", True)])
        self.assertEqual((len(result["history"]["added"]), result["history"]["skipped"],
                          result["history"]["conflicts"]), (2, [], []), result)
        # S06-6: the same default tracking as create.
        self.assertEqual(result["tracking"], "ignored")
        self.assertEqual((self.main / ".gitignore").read_text(encoding="utf-8"), "/.feather/handoffs/\n")
        source = "wt1/.feather/handoffs/"
        self.assertEqual(self.changed(before, self.tree()), {
            source + "a1.md", source + "b1.md", source + "archive/2026-08-wt1.md", source + "history.md",
            "main/.feather/handoffs/a1.md", "main/.feather/handoffs/b1.md", "main/.feather/handoffs/history.md",
            "main/.feather/handoffs/archive/2026-08-wt1.md", "main/.gitignore"})
        records = self.leftovers[self.wt1]
        for name, text in records["works"].items():
            self.assertEqual((self.store / name).read_bytes(), text.encode("utf-8"))
            self.assertFalse((self.source_store(self.wt1) / name).exists())
        self.assertEqual((self.store / "archive" / "2026-08-wt1.md").read_bytes(),
                         records["archive"]["2026-08-wt1.md"].encode("utf-8"))
        self.assertEqual((self.store / "history.md").read_bytes(), records["history"].encode("utf-8"))
        # history.md is rewritten, never removed.
        self.assertEqual((self.source_store(self.wt1) / "history.md").read_bytes(), HEADER.encode("utf-8"))
        # Both locks were created and removed again.
        self.assertEqual(acquired, [(str(self.store / LOCK), True), (str(self.source_store(self.wt1) / LOCK), True)])
        self.assertEqual(self.locks(), [])
        listed = self.run_tool(self.wt1, "list")
        self.assertEqual([item["work"] for item in listed["items"]], ["a1.md", "b1.md"], listed)

    def test_adopting_another_checkouts_records_leaves_the_working_checkout_byte_identical(self):
        payload = self.everything(self.wt2)
        before, wt1 = self.tree(), self.tree(self.wt1)
        result = self.adopt(self.wt1, payload)
        self.assertEqual((result["status"], result["complete"]), ("ok", True), result)
        self.assertEqual(self.tree(self.wt1), wt1)
        changed = self.changed(before, self.tree())
        self.assertEqual({name for name in changed if name.startswith("wt2/")},
                         {"wt2/.feather/handoffs/a2.md", "wt2/.feather/handoffs/b2.md", "wt2/.feather/handoffs/history.md",
                          "wt2/.feather/handoffs/archive/2026-08-wt2.md"})
        self.assertEqual({name for name in changed if not name.startswith("wt2/.feather/handoffs/")},
                         {"main/.feather/handoffs/a2.md", "main/.feather/handoffs/b2.md",
                          "main/.feather/handoffs/history.md", "main/.feather/handoffs/archive/2026-08-wt2.md",
                          "main/.gitignore"})
        titles = [item["title"] for item in self.run_tool(self.main, "history")["entries"]]
        self.assertEqual(titles, ["h2a", "h2b"])

    def test_a_checkout_local_target_store_receives_another_checkouts_records(self):
        """From the main worktree, whose store is its own, a linked worktree's leftover work moves in."""
        payload = self.request(self.wt1, works=["a1.md"])
        before = self.tree()
        result = self.adopt(self.main, payload)
        self.assertEqual((result["status"], result["root"]["shared"], result["tracking"]), ("ok", False, "ignored"),
                         result)
        self.assertEqual(self.changed(before, self.tree()), {"wt1/.feather/handoffs/a1.md",
                                                             "main/.feather/handoffs/a1.md", "main/.gitignore"})
        self.assertEqual(self.locks(), [])

    def test_works_only_take_no_source_lock_and_leave_its_history_alone(self):
        data = self.write_lock(self.source_store(self.wt2))
        result = self.adopt(self.wt1, self.request(self.wt2, works=["a2.md"]))
        self.assertEqual((result["status"], result["history"], result["archives"]), ("ok", None, []), result)
        self.assertEqual((self.source_store(self.wt2) / LOCK).read_bytes(), data)
        self.assertEqual((self.source_store(self.wt2) / "history.md").read_bytes(),
                         self.leftovers[self.wt2]["history"].encode("utf-8"))


class SourceValidationTest(AdoptBase):
    """Acceptance line 1 and S06-2: a source that is not a listed checkout of this repository, or fails the store link
    checks, is refused with nothing changed; the source is validated on every run."""

    def test_a_source_that_is_not_a_listed_worktree_is_refused(self):
        other = self.repository("other")
        store = other / ".feather" / "handoffs"
        store.mkdir(parents=True)
        (store / "a2.md").write_bytes(old_record("x").encode("utf-8"))
        plain = self.outside / "plain"
        (plain / ".feather" / "handoffs").mkdir(parents=True)
        (plain / ".feather" / "handoffs" / "a2.md").write_bytes(old_record("x").encode("utf-8"))
        versions = {"a2.md": sha(old_record("x").encode("utf-8"))}
        for label, source in (("another repository", other), ("a plain directory", plain),
                              ("a store directory", self.source_store(self.wt2)),
                              ("a missing directory", self.base / "missing")):
            with self.subTest(case=label):
                before = self.tree()
                result = self.adopt(self.wt1, {"source": str(source), "works": versions}, expected=2)
                self.assert_refused(result, "scope", before, "Nothing was changed")

    def test_a_directory_with_a_copied_git_file_is_refused(self):
        copy = self.base / "copy"
        shutil.copytree(self.source_store(self.wt2), copy / ".feather" / "handoffs")
        shutil.copy2(self.wt2 / ".git", copy / ".git")
        # The copy's .git file points at wt2's Git directory; only the listed checkout's identity tells them apart.
        payload = {**self.request(self.wt2, works=["a2.md"]), "source": str(copy)}
        before = self.tree()
        result = self.adopt(self.wt1, payload, expected=2)
        self.assert_refused(result, "scope", before, "is not a checkout that git worktree list reports")

    def test_a_relative_source_is_an_input_error(self):
        before = self.tree()
        result = self.adopt(self.wt1, {"source": "wt2", "works": {"a2.md": "x"}}, expected=2)
        self.assert_refused(result, "input", before)

    def test_a_source_store_reached_through_a_link_is_refused(self):
        moved = self.outside / "store"
        shutil.move(str(self.wt2 / ".feather"), str(moved))
        feather_support.make_directory_link(self.wt2 / ".feather", moved)
        payload = {"source": str(self.wt2), "works": {"a2.md": sha(self.leftovers[self.wt2]["works"]["a2.md"]
                                                                       .encode("utf-8"))}}
        before = self.tree()
        result = self.adopt(self.wt1, payload, expected=2)
        self.assert_refused(result, "unsafe-path", before, "Link/reparse path is not supported")

    def test_the_source_is_validated_again_on_every_run(self):
        first = self.adopt(self.wt1, self.request(self.wt2, works=["a2.md"]))
        self.assertEqual(first["status"], "ok", first)
        payload = self.request(self.wt2, works=["b2.md"])
        # Git forgets wt2 while its directory and records stay; the same input is no longer accepted.
        shutil.rmtree(self.main / ".git" / "worktrees" / "wt2")
        self.assertNotIn(str(self.wt2), self.git(self.main, "worktree", "list", "--porcelain"))
        before = self.tree()
        result = self.adopt(self.wt1, payload, expected=2)
        self.assert_refused(result, "scope", before)

    def test_a_non_git_or_explicit_root_is_refused(self):
        plain = self.base / "plain"
        plain.mkdir()
        payload = self.request(self.wt2, works=["a2.md"])
        for label, project, exact in (("non-git", plain, False), ("explicit root", self.wt1, True)):
            with self.subTest(case=label):
                before = self.tree()
                result = self.run_tool(project, "adopt", payload=payload, expected=2, exact=exact)
                self.assert_refused(result, "scope", before, "has no other checkout to adopt from")


class DistinctStoresTest(AdoptBase):
    """S06-1: a source whose store is the target store, however it is spelled, is refused before the first read."""

    def assert_same_store_refused(self, project: Path, source: str):
        payload = {"source": source, "works": {"a1.md": "0" * 64}}
        before = self.tree()
        result = self.adopt(project, payload, expected=2)
        self.assert_refused(result, "scope", before, "holds the current Handoff store")

    def test_the_target_stores_checkout_is_refused_as_spelled(self):
        self.run_tool(self.wt1, "create", "--work", "a1.md", payload={"title": "a1", "fields": FIELDS})
        self.assert_same_store_refused(self.wt1, str(self.main))
        self.assert_same_store_refused(self.main, str(self.main))

    def test_a_junction_to_the_target_stores_checkout_is_refused(self):
        alias = self.base / "alias"
        feather_support.make_directory_link(alias, self.main)
        self.assert_same_store_refused(self.wt1, str(alias))

    def test_a_case_variant_of_the_target_stores_checkout_is_refused(self):
        variant = str(self.main.parent / self.main.name.upper())
        if not os.path.isdir(variant):
            self.skipTest("this volume is case-sensitive, so a case variant names no directory")
        self.assert_same_store_refused(self.wt1, variant)

    def test_a_short_name_of_the_target_stores_checkout_is_refused(self):
        if not WINDOWS:
            self.skipTest("8.3 short names exist only on Windows")
        import ctypes
        buffer = ctypes.create_unicode_buffer(1024)
        length = ctypes.windll.kernel32.GetShortPathNameW(str(self.main), buffer, len(buffer))
        if not length or os.path.normcase(buffer.value) == os.path.normcase(str(self.main)):
            self.skipTest("8.3 short names are not generated on this volume")
        self.assert_same_store_refused(self.wt1, buffer.value)

    def test_a_source_store_linked_to_the_target_store_is_refused(self):
        self.run_tool(self.wt1, "create", "--work", "x.md", payload={"title": "x", "fields": FIELDS})
        shutil.rmtree(self.wt2 / ".feather")
        feather_support.make_directory_link(self.wt2 / ".feather", self.main / ".feather")
        before = self.tree()
        result = self.adopt(self.wt1, {"source": str(self.wt2), "works": {"x.md": "0" * 64}}, expected=2)
        self.assert_refused(result, "scope", before, "are the same directory or one contains the other")
        self.assertTrue((self.store / "x.md").is_file())


class NamesTest(AdoptBase):
    """S06-3 names and S06-4: names equal after case folding are refused; illegal names are reported, not moved."""

    def test_names_equal_after_case_folding_are_refused(self):
        version = sha(self.leftovers[self.wt2]["works"]["a2.md"].encode("utf-8"))
        for key in ("works", "archives"):
            with self.subTest(key=key):
                before = self.tree()
                result = self.adopt(self.wt1, {"source": str(self.wt2), key: {"W.md": version, "w.md": version}},
                                    expected=2)
                self.assert_refused(result, "input", before, "equal after case folding")

    def test_illegal_names_are_reported_and_nothing_is_moved_for_them(self):
        payload = {"source": str(self.wt2), "works": {"../wt2.md": "0" * 64, "history.md": "0" * 64,
                                                       LOCK: "0" * 64, "a2.md": self.request(self.wt2, works=["a2.md"])
                                                       ["works"]["a2.md"]},
                   "archives": {"notes.txt": "0" * 64}}
        before = self.tree()
        result = self.adopt(self.wt1, payload, expected=2)
        self.assertEqual((result["status"], result["complete"]), ("partial", False), result)
        codes = {item["work"]: item.get("code") for item in result["works"]}
        self.assertEqual(codes, {"../wt2.md": "unsafe-name", "history.md": "unsafe-name", LOCK: "unsafe-name",
                                 "a2.md": None}, result)
        self.assertEqual([(item["archive"], item["moved"], item["code"]) for item in result["archives"]],
                         [("notes.txt", False, "unsafe-name")])
        self.assertEqual(self.changed(before, self.tree()), {"wt2/.feather/handoffs/a2.md",
                                                             "main/.feather/handoffs/a2.md", "main/.gitignore"})


class ConflictTest(AdoptBase):
    """Acceptance lines 2, 4 and 5, S06-4: a conflict is per file and per history entry, is decided by the exclusive
    create, and leaves both copies; other files still move, and every lock is removed afterwards."""

    def test_a_work_name_in_the_target_conflicts_and_other_files_still_move(self):
        self.run_tool(self.wt1, "create", "--work", "a2.md", payload={"title": "main a2", "fields": FIELDS})
        held = (self.store / "a2.md").read_bytes()
        payload = self.request(self.wt2, works=["a2.md", "b2.md"], history="all")
        before = self.tree()
        result = self.adopt(self.wt1, payload, expected=2)
        self.assertEqual((result["status"], result["complete"]), ("partial", False), result)
        first, second = result["works"]
        self.assertEqual((first["work"], first["moved"], first["code"]), ("a2.md", False, "conflict"), first)
        self.assertEqual((second["work"], second["moved"]), ("b2.md", True), second)
        self.assertEqual((self.store / "a2.md").read_bytes(), held)
        self.assertEqual((self.source_store(self.wt2) / "a2.md").read_bytes(),
                         before["wt2/.feather/handoffs/a2.md"])
        self.assertEqual(self.locks(), [])

    def test_a_single_conflicting_file_changes_neither_store(self):
        (self.store).mkdir(parents=True)
        (self.store / "a2.md").write_bytes(b"other\n")
        (self.store / "archive").mkdir()
        (self.store / "archive" / "2026-08-wt2.md").write_bytes(b"other sealed\n")
        for label, payload in (("work", self.request(self.wt2, works=["a2.md"])),
                               ("archive", self.request(self.wt2, archives=["2026-08-wt2.md"]))):
            with self.subTest(case=label):
                before = self.tree()
                result = self.adopt(self.wt1, payload, expected=2)
                items = result["works"] + result["archives"]
                self.assertEqual([(item["moved"], item["code"]) for item in items], [(False, "conflict")], result)
                self.assertEqual(self.changed(before, self.tree()), set())
                self.assertEqual(self.locks(), [])

    def test_a_name_differing_only_in_case_conflicts_where_names_ignore_case(self):
        self.store.mkdir(parents=True)
        (self.store / "A2.md").write_bytes(b"other\n")
        if not (self.store / "a2.md").exists():
            self.skipTest("this volume is case-sensitive, so A2.md and a2.md are different files")
        before = self.tree()
        result = self.adopt(self.wt1, self.request(self.wt2, works=["a2.md"]), expected=2)
        self.assertEqual(result["works"][0]["code"], "conflict", result)
        self.assertEqual(self.changed(before, self.tree()), set())

    def test_the_conflict_is_decided_by_the_exclusive_create(self):
        """Another writer creates the target just before adopt's create: the create alone refuses it."""
        payload = self.request(self.wt2, works=["a2.md"])
        real_create = storage.create_file
        target = self.store / "a2.md"

        def raced(path, data):
            if path == target:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"other writer\n")
            return real_create(path, data)
        with mock.patch.object(adopt, "create_file", raced):
            code, result = self.invoke(self.wt1, "adopt", payload=payload)
        self.assertEqual((code, result["works"][0]["code"]), (2, "conflict"), result)
        self.assertEqual(target.read_bytes(), b"other writer\n")
        self.assertEqual((self.source_store(self.wt2) / "a2.md").read_bytes(),
                         self.leftovers[self.wt2]["works"]["a2.md"].encode("utf-8"))

    def test_a_history_body_conflict_keeps_both_entries_and_other_entries_move(self):
        self.store.mkdir(parents=True)
        (self.store / "history.md").write_bytes(
            (HEADER + entry("h2a", "2026-09-03T10:00:00+08:00", "different\n")).encode("utf-8"))
        payload = self.request(self.wt2, history="all")
        conflicting, added = payload["history"]["ids"]
        result = self.adopt(self.wt1, payload, expected=2)
        history = result["history"]
        self.assertEqual((result["status"], history["added"], history["skipped"]), ("partial", [added], []), result)
        self.assertEqual([(item["id"], item["code"]) for item in history["conflicts"]], [(conflicting, "conflict")])
        source = self.run_tool(self.wt2, "history", exact=True)
        self.assertEqual([item["id"] for item in source["entries"]], [conflicting])
        target = self.run_tool(self.wt1, "history")
        self.assertEqual([item["title"] for item in target["entries"]], ["h2a", "h2b"])
        self.assertIn("different", target["entries"][0]["body"])
        self.assertEqual(self.locks(), [])

    def test_a_single_conflicting_history_entry_changes_neither_store(self):
        self.store.mkdir(parents=True)
        (self.store / "history.md").write_bytes(
            (HEADER + entry("h2a", "2026-09-03T10:00:00+08:00", "different\n")).encode("utf-8"))
        payload = self.request(self.wt2, history=["h2a"])
        before = self.tree()
        result = self.adopt(self.wt1, payload, expected=2)
        self.assertEqual(len(result["history"]["conflicts"]), 1, result)
        self.assertEqual(self.changed(before, self.tree()), set())

    def test_a_changed_source_history_is_a_conflict_and_every_lock_is_removed(self):
        payload = self.request(self.wt2, history="all")
        path = self.source_store(self.wt2) / "history.md"
        path.write_bytes(path.read_bytes() + entry("late", "2026-09-05T10:00:00+08:00").encode("utf-8"))
        before = self.tree()
        result = self.adopt(self.wt1, payload, expected=2)
        self.assertEqual((result["status"], result["history"]["code"]), ("partial", "conflict"), result)
        self.assertEqual(self.changed(before, self.tree()), set())
        self.assertEqual(self.locks(), [])


class HistoryTest(AdoptBase):
    """S06-1 and S06-3 for history: a skipped identical entry stays in the source history, and added entries leave it
    only after the target's reread confirms them."""

    def test_a_skipped_identical_entry_stays_in_the_source_history(self):
        self.store.mkdir(parents=True)
        identical = HEADER + entry("h2a", "2026-09-03T10:00:00+08:00")
        (self.store / "history.md").write_bytes(identical.encode("utf-8"))
        payload = self.request(self.wt2, history="all")
        skipped, added = payload["history"]["ids"]
        result = self.adopt(self.wt1, payload)
        self.assertEqual((result["status"], result["history"]["added"], result["history"]["skipped"]),
                         ("ok", [added], [skipped]), result)
        self.assertEqual([item["id"] for item in self.run_tool(self.wt2, "history", exact=True)["entries"]], [skipped])
        self.assertEqual([item["id"] for item in self.run_tool(self.wt1, "history")["entries"]], [skipped, added])
        self.assertEqual(result["history"]["source_version"],
                         sha((self.source_store(self.wt2) / "history.md").read_bytes()))

    def test_an_unverified_target_history_leaves_the_source_history_unchanged(self):
        payload = self.request(self.wt2, history="all")
        real_create = storage.create_file

        def corrupted(path, data):
            saved = real_create(path, data)
            if path.name == "history.md":
                path.write_bytes(data.replace(b"h2b", b"h2x"))
            return saved
        source = (self.source_store(self.wt2) / "history.md").read_bytes()
        with mock.patch.object(adopt, "create_file", corrupted):
            code, result = self.invoke(self.wt1, "adopt", payload=payload)
        history = result["history"]
        self.assertEqual((code, history["code"], history["added"], history["target_present"]),
                         (2, "partial", [], True), result)
        self.assertEqual((self.source_store(self.wt2) / "history.md").read_bytes(), source)
        self.assertEqual(self.locks(), [])

    def test_a_source_history_changed_before_its_rewrite_is_kept(self):
        payload = self.request(self.wt2, history="all")
        path = self.source_store(self.wt2) / "history.md"
        real_create = storage.create_file

        def changed(target, data):
            saved = real_create(target, data)
            path.write_bytes(path.read_bytes() + b"\n")
            return saved
        with mock.patch.object(adopt, "create_file", changed):
            code, result = self.invoke(self.wt1, "adopt", payload=payload)
        history = result["history"]
        self.assertEqual((code, history["code"], history["cause_code"]), (2, "partial", "conflict"), result)
        self.assertEqual(path.read_bytes(), (self.leftovers[self.wt2]["history"] + "\n").encode("utf-8"))
        # The verified target holds the entries, which the source also kept.
        self.assertEqual(history["added"], payload["history"]["ids"], result)
        self.assertEqual([item["id"] for item in self.run_tool(self.wt1, "history")["entries"]],
                         payload["history"]["ids"])


class RemovalTest(AdoptBase):
    """Acceptance line 3 and S06-3: the order create, reread, check, remove, confirm; a failure before removal removes
    nothing and returns partial naming both paths; a root replaced after resolution and a hard-linked source are
    refused."""

    def test_the_removal_order_is_create_reread_check_remove_confirm(self):
        payload = self.request(self.wt2, works=["a2.md"])
        source, target = self.source_store(self.wt2) / "a2.md", self.store / "a2.md"
        events = []
        real_read, real_create, real_unlink, real_lexists = adopt.read_file, adopt.create_file, Path.unlink, \
            os.path.lexists

        def read(path):
            if path in (source, target):
                events.append(("read", path))
            return real_read(path)

        def create(path, data):
            events.append(("create", path))
            return real_create(path, data)

        def unlink(path, *args, **kwargs):
            if path == source:
                events.append(("unlink", path))
            return real_unlink(path, *args, **kwargs)

        def lexists(path):
            if os.path.normcase(os.fspath(path)) == os.path.normcase(str(source)):
                events.append(("lexists", source))
            return real_lexists(path)
        with mock.patch.object(adopt, "read_file", read), mock.patch.object(adopt, "create_file", create), \
                mock.patch.object(Path, "unlink", unlink), mock.patch.object(os.path, "lexists", lexists):
            code, result = self.invoke(self.wt1, "adopt", payload=payload)
        self.assertEqual((code, result["works"][0]["moved"]), (0, True), result)
        self.assertEqual(events, [("read", source), ("create", target), ("read", target), ("read", source),
                                  ("unlink", source), ("lexists", source)])

    def test_a_target_reread_that_differs_leaves_the_source_untouched(self):
        payload = self.request(self.wt2, works=["a2.md"])
        real_create = storage.create_file

        def altered(path, data):
            saved = real_create(path, data)
            path.write_bytes(data + b"altered\n")
            return saved
        with mock.patch.object(adopt, "create_file", altered):
            code, result = self.invoke(self.wt1, "adopt", payload=payload)
        item = result["works"][0]
        self.assertEqual((code, item["moved"], item["code"], item["source_present"], item["target_present"]),
                         (2, False, "partial", True, True), result)
        self.assertEqual((item["source_path"], item["target_path"]),
                         (str(self.source_store(self.wt2) / "a2.md"), str(self.store / "a2.md")))
        self.assertEqual((self.source_store(self.wt2) / "a2.md").read_bytes(),
                         self.leftovers[self.wt2]["works"]["a2.md"].encode("utf-8"))

    def test_a_source_changed_between_reread_and_removal_is_kept(self):
        payload = self.request(self.wt2, works=["a2.md"])
        source = self.source_store(self.wt2) / "a2.md"
        real_create = storage.create_file

        def changed(path, data):
            saved = real_create(path, data)
            source.write_bytes(data + b"later\n")
            return saved
        with mock.patch.object(adopt, "create_file", changed):
            code, result = self.invoke(self.wt1, "adopt", payload=payload)
        item = result["works"][0]
        self.assertEqual((code, item["code"], item["source_present"], item["target_present"]),
                         (2, "partial", True, True), result)
        self.assertIn("changed after it was read", item["message"])
        self.assertTrue(source.read_bytes().endswith(b"later\n"))

    def test_a_source_root_replaced_by_a_junction_after_resolution_is_refused(self):
        payload = self.request(self.wt2, works=["a2.md"], history="all")
        moved = self.base / "wt2-moved"
        real_run = subprocess.run

        def run(args, **kwargs):
            result = real_run(args, **kwargs)
            directory, command, _ = git_call(list(args))
            if directory == str(self.wt2) and command == ["rev-parse", "--path-format=absolute", "--git-common-dir"]:
                os.rename(self.wt2, moved)
                feather_support.make_directory_link(self.wt2, moved)
            return result
        before = self.tree(self.base / "wt2")
        with mock.patch.object(storage.subprocess, "run", side_effect=run):
            code, result = self.invoke(self.wt1, "adopt", payload=payload)
        self.assertEqual((code, result["status"], result["code"]), (2, "error", "unsafe-path"), result)
        self.assertIn("Project root changed after it was resolved", result["message"])
        self.assertEqual(self.tree(moved), before)
        self.assertFalse(self.store.exists() and any(self.store.iterdir()))

    def test_a_hard_linked_source_file_is_refused_with_both_files_unchanged(self):
        payload = self.request(self.wt2, works=["a2.md", "b2.md"])
        source = self.source_store(self.wt2) / "a2.md"
        alias = self.outside / "alias.md"
        try:
            os.link(source, alias)
        except OSError as error:
            self.skipTest(f"hard links are unavailable here: {error}")
        data = source.read_bytes()
        result = self.adopt(self.wt1, payload, expected=2)
        first, second = result["works"]
        self.assertEqual((first["moved"], first["code"]), (False, "unsafe-path"), result)
        self.assertIn("Hard-linked file is not supported", first["message"])
        self.assertEqual(second["moved"], True, result)
        self.assertEqual((source.read_bytes(), alias.read_bytes()), (data, data))
        self.assertFalse((self.store / "a2.md").exists())

    def test_a_target_the_session_cannot_write_is_store_unwritable_with_nothing_removed(self):
        self.store.mkdir(parents=True)
        (self.store / "archive").mkdir()
        self.deny(self.store / "archive")
        payload = self.request(self.wt2, works=["a2.md"], archives=["2026-08-wt2.md"])
        result = self.adopt(self.wt1, payload, expected=2)
        archive = result["archives"][0]
        self.assertEqual((archive["moved"], archive["code"], archive["store"]),
                         (False, "store-unwritable", str(self.store)), result)
        self.assertTrue((self.source_store(self.wt2) / "archive" / "2026-08-wt2.md").is_file())
        self.assertEqual(result["works"][0]["moved"], True, result)
        self.assertEqual(self.locks(), [])

    def test_a_target_store_the_session_cannot_write_refuses_the_whole_run(self):
        self.store.mkdir(parents=True)
        self.deny(self.store)
        payload = self.request(self.wt2, works=["a2.md"])
        before = self.tree()
        result = self.adopt(self.wt1, payload, expected=2)
        self.assert_refused(result, "store-unwritable", before)
        self.assertEqual(result["store"], str(self.store), result)


class LockTest(AdoptBase):
    """Acceptance line 7 and S06-5: a held target lock, or with history or archives a held source lock, returns
    history-locked with every file of both stores byte-identical; adopt removes every lock it took."""

    def test_a_held_target_lock_returns_history_locked_and_changes_nothing(self):
        self.store.mkdir(parents=True)
        data = self.write_lock(self.store)
        for label, payload in (("works", self.request(self.wt2, works=["a2.md"])),
                               ("everything", self.everything(self.wt2))):
            with self.subTest(case=label):
                before = self.tree()
                result = self.adopt(self.wt1, payload, expected=2)
                self.assert_refused(result, "history-locked", before, "Nothing was changed")
                self.assertEqual((result["lock"]["path"], result["lock"]["version"]),
                                 (str(self.store / LOCK), sha(data)), result)

    def test_a_held_source_lock_returns_history_locked_and_changes_nothing(self):
        data = self.write_lock(self.source_store(self.wt2))
        for label, payload in (("history", self.request(self.wt2, works=["a2.md"], history="all")),
                               ("archives", self.request(self.wt2, archives=["2026-08-wt2.md"]))):
            with self.subTest(case=label):
                before = self.tree()
                result = self.adopt(self.wt1, payload, expected=2)
                self.assertEqual((result["status"], result["code"], result["lock"]["path"]),
                                 ("error", "history-locked", str(self.source_store(self.wt2) / LOCK)), result)
                # The target store directory may be created for its lock; no file of either store changes.
                self.assertEqual(self.changed(before, self.tree()), set())
                self.assertEqual(self.locks(), [self.source_store(self.wt2) / LOCK])
                self.assertEqual((self.source_store(self.wt2) / LOCK).read_bytes(), data)

    def test_a_source_lock_left_in_place_is_reported_apart_from_the_target_lock(self):
        payload = self.request(self.wt2, history="all")
        source_lock = self.source_store(self.wt2) / LOCK
        real_release = storage.HistoryLock.release

        def release(lock):
            return "kept for the test" if lock.path == source_lock else real_release(lock)
        with mock.patch.object(storage.HistoryLock, "release", release):
            code, result = self.invoke(self.wt1, "adopt", payload=payload)
        self.assertEqual((code, result["status"]), (0, "ok"), result)
        self.assertEqual(result["source_lock_left"], {"path": str(source_lock), "message": "kept for the test"})
        self.assertNotIn("lock_left", result)
        self.assertEqual(self.locks(), [source_lock])

    def test_every_lock_is_removed_after_a_handled_error(self):
        (self.source_store(self.wt2) / "history.md").write_bytes(b"unrecognized\n")
        payload = {"source": str(self.wt2), "history": {"version": sha(b"unrecognized\n"), "ids": ["x"]}}
        result = self.adopt(self.wt1, payload, expected=2)
        self.assertEqual(result["history"]["code"], "format", result)
        self.assertEqual(self.locks(), [])


class UncertainRootTest(AdoptBase):
    """Acceptance line 8: under an uncertain root adopt is refused before any write."""

    def test_an_uncertain_root_refuses_adopt_before_any_write(self):
        payload = self.everything(self.wt2)
        feather_support.make_directory_link(self.main / ".feather", self.outside)
        before = self.tree()
        result = self.adopt(self.wt1, payload, expected=2)
        self.assert_refused(result, "project-root-uncertain", before, "No writes made")


class GuardTest(AdoptBase):
    """S06-7's last sentence: each group of Git commands runs the lazy-fetch guard in its own -C directory first, and
    no Git command runs in a checkout other than the Working checkout, the source and the target store's checkout."""

    def test_each_git_group_runs_after_its_lazy_fetch_guard(self):
        payload = self.everything(self.wt2)
        with self.git_as() as calls:
            code, result = self.invoke(self.wt1, "adopt", payload=payload)
        self.assertEqual((code, result["status"]), (0, "ok"), result)
        self.assert_guarded(calls)
        started = [git_call(args)[:2] for args in calls]
        self.assertTrue({str(self.wt2), str(self.wt1), str(self.main)} >= {item[0] for item in started}, started)
        # The source's own group starts with its guard; only these commands, none of which reads objects, run there.
        source = [command for place, command in started if place == str(self.wt2)]
        self.assertEqual(source[0], ["config", "--list", "--includes", "-z"], source)
        self.assertEqual([command for command in source if command[0] != "config" and command != ["version"]],
                         [["rev-parse", "--absolute-git-dir"],
                          ["rev-parse", "--path-format=absolute", "--git-common-dir"]], source)
        listing = started.index((str(self.wt1), ["worktree", "list", "--porcelain", "-z"]))
        self.assertIn((str(self.wt1), ["config", "--list", "--includes", "-z"]), started[:listing])


class SkillAdoptTest(unittest.TestCase):
    """Acceptance 12's skill share for item 10."""

    SENTENCES = (
        "On the user's request, the tool's `adopt` moves named work files, and optionally selected history entries "
        "and sealed archives, of one other checkout's store reported under `other_stores` into the current Handoff "
        "store, so that removing that checkout no longer threatens them.",
        "Run `adopt` only after the user confirms the exact source checkout, work files, history entries and "
        "archives; never move records automatically, including when a list or resume reports `other_stores`.",
        "Take the versions and history identities from read-only `read` and `history` runs against the source "
        "checkout as an explicit root, and pass only what the user confirmed.",
        "A `conflict` for a work file or archive means the current store already holds that name, and for a history "
        "entry that the current history holds its completion identity with a different body; nothing is moved for "
        "it, so report both paths and ask.",
        "An identical history entry is skipped and stays in the source history.",
        "On `partial`, the target copy may exist while its source was kept: report both paths and the reason, and "
        "compare them with the user before any retry.",
        "`adopt` takes the current store's history lock, and the source store's as well when it moves history or "
        "archives; handle `history-locked` as for other history mutations.",
    )

    def test_the_skill_runs_adopt_only_on_the_users_confirmation(self):
        assert_sentences(self, SKILL, self.SENTENCES)

    def test_the_rules_name_no_hosts_tools(self):
        for sentence in self.SENTENCES:
            with self.subTest(sentence=sentence[:60]):
                self.assertNotRegex(sentence, HOST_TOOLS)


class ToolReferenceAdoptTest(unittest.TestCase):
    """Acceptance 12's tool-reference share for item 10: the command, its input and its results."""

    SENTENCES = (
        "`adopt` takes this lock too, as [Adopt](#adopt) describes.",
        "`adopt` moves records the user confirmed from the store of one other checkout of the repository into the "
        "current Handoff store.",
        "Its input is `{ \"source\": \"<checkout path>\", \"works\": { \"<work>.md\": \"<version>\" }, \"history\": "
        "{ \"version\": \"<source history version>\", \"ids\": [\"<id>\"] }, \"archives\": { \"<batch>.md\": "
        "\"<version>\" } }`, with at least one of `works`, `history` and `archives`; each version is the one read "
        "from that source file.",
        "Read those versions and identities without writing anything with `read --work <work>.md`, `history` and "
        "`history --include-sealed` run with `--project <source checkout> --exact-root`.",
        "The source must be an absolute path that resolves strictly to a non-bare checkout that `git worktree list "
        "--porcelain -z`, run from the Working checkout, reports; its Git directory must be the repository's common "
        "directory or lie under its `worktrees/`, and its common directory must be the current one.",
        "The source path comes only from the input and is validated on every run, never taken from `other_stores`.",
        "Its strict real path is pinned like a project root, so its `.feather/handoffs/`, every file `adopt` reads, "
        "replaces or removes there and its history lock pass the link, reparse-point and hard-link checks, and a "
        "source root replaced after resolution is refused with `unsafe-path`.",
        "The source store and the current store must differ in filesystem identity and neither may contain the "
        "other, checked before the first read and again before each removal; a source that holds the current store, "
        "however it is spelled, is refused.",
        "A refused source returns `status: error` with `code: scope`, or `unsafe-path` for a link check, and nothing "
        "changed; so does a run whose root is not a Git root discovered from `--project`.",
        "Under an uncertain root `adopt` fails with `project-root-uncertain` before writing anything.",
        "Two names in `works` or in `archives` that are equal after case folding are refused with `input`.",
        "For each work file and archive, the tool creates the target exclusively, so an existing name returns "
        "`conflict` for that file and moves nothing for it, rereads the target and matches the source bytes, checks "
        "the source against the given version, removes it and confirms it is gone; other named files still move.",
        "A work name must be a legal `<name>.md` other than `history.md`, and an archive name a legal name ending in "
        "`.md`; another name is reported with `unsafe-name` and not moved.",
        "A failure after the target was written and before the source was removed removes nothing and reports "
        "`code: partial` with `cause_code`, `source_path`, `target_path`, `source_present` and `target_present`; a "
        "target the session cannot write reports `store-unwritable` with nothing removed.",
        "History entries are added by completion identity, work title plus completion time: an identity already "
        "present with the same body is listed in `skipped` and stays in the source history, one present with a "
        "different body is listed in `conflicts`, and the rest are appended to the current history and listed in "
        "`added`.",
        "Only after the current history's reread confirms every added identity and body does a version-checked "
        "replace remove exactly the added entries from the source history; `history.md` itself is never removed.",
        "When that replace fails, the history result is `partial` and `added` lists the entries the current history "
        "was confirmed to hold, which the source history also kept.",
        "A source history whose version differs from the input returns `conflict` and changes neither history.",
        "`adopt` holds the current store's history lock, and, when it includes history or archives, the source "
        "store's as well; when either already exists it returns `history-locked` and changes nothing, and it removes "
        "every lock it took afterwards, including after `conflict` or another handled error.",
        "A source lock that cannot be removed afterwards is reported as `source_lock_left`, as `lock_left` reports "
        "the current store's.",
        "The result has `source` (`checkout` and `store`), `target`, `works` and `archives` with one item per name, "
        "each with `moved`, `source_path`, `target_path` and, when not moved, `code` and `message`, and `history` "
        "with `added`, `skipped` and `conflicts` or `null`.",
        "It is `status: ok` only when every named file moved and no history entry conflicted or failed, and "
        "otherwise `partial` with `complete: false`.",
        "When `adopt` creates records in the current store it applies the default tracking of `create` and reports "
        "it as `tracking`.",
        "Besides the current store and that ignore rule, `adopt` writes only, inside the source store, the files it "
        "removes, the `history.md` it rewrites and the lock it creates and removes.",
    )

    def test_the_tool_reference_documents_adopt(self):
        assert_sentences(self, TOOL_REFERENCE, self.SENTENCES)
        self.assertIn("handoff.py --project <project> adopt", normalized(TOOL_REFERENCE))

    def test_no_new_text_uses_the_forbidden_word(self):
        for sentence in (*self.SENTENCES, *SkillAdoptTest.SENTENCES):
            with self.subTest(sentence=sentence[:60]):
                self.assertNotIn("tidy", sentence.lower())


if __name__ == "__main__":
    unittest.main()
