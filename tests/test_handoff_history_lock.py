"""History mutations take a lock; a stale lock is cleared only on the user's decision (worktree store ticket 04).

Every operation that changes history.md or archive/ (the archive step of a completed save, archive, clear and seal)
holds .feather/handoffs/.history.lock in the Handoff store from its history read until its last history write and
source removal are verified. A held lock makes the operation change nothing and return history-locked with the lock's
creation time, holder, age and version; a completed save that meets it is kept as deferred. unlock removes a lock only
when it is stale and unchanged since the user saw it.

The fixture and its isolated Git environment are those of tests/test_handoff_shared_store.py: a base made with
mkdtemp under FEATHER_LINK_TEST_DIR when set, synthetic data only, removed on cleanup. Pre-created locks are synthetic
JSON lines written by the tests. The tool runs as a subprocess with --project; the in-process cases drive the CLI
entry point while patching internals, as the existing in-process tests do, never the lock helpers directly. The case
of a lock file pending deletion is built on Windows with SetFileInformationByHandle and skipped elsewhere, because a
POSIX unlink removes the name at once and leaves no file pending deletion."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import socket
import unittest
from unittest import mock

from tests import feather_support
from tests.test_handoff_shared_store import FIELDS, SKILL, TOOL_REFERENCE, SharedBase, assert_sentences, normalized
from tests.test_handoff_unwritable_store import DONE, StoreFixture
from feather_handoff import archiving, history_mutations

WINDOWS = os.name == "nt"
LOCK = ".history.lock"
NO_PENDING_DELETE = ("a POSIX unlink removes the name at once, so no lock file pending deletion can exist; the "
                     "pending-deletion case exists only on Windows")


class LockFixture(StoreFixture):
    def lock_path(self) -> Path:
        return self.store / LOCK

    def write_lock(self, age: timedelta = timedelta(seconds=5), pid: int = 4242, host: str = "fixture-host") -> bytes:
        created = (datetime.now(timezone.utc) - age).astimezone().isoformat(timespec="microseconds")
        data = (json.dumps({"created": created, "host": host, "pid": pid}) + "\n").encode("utf-8")
        self.lock_path().write_bytes(data)
        return data

    def version_of(self) -> str:
        return hashlib.sha256(self.lock_path().read_bytes()).hexdigest()

    def assert_locked(self, result: dict, data: bytes, *, stale: bool = False, code: str = "history-locked"):
        self.assertEqual((result["status"], result["complete"], result["code"]), ("error", False, code), result)
        lock = result["lock"]
        written = json.loads(data)
        self.assertEqual((lock["path"], lock["readable"], lock["format_valid"]),
                         (str(self.lock_path()), True, True), lock)
        self.assertEqual(datetime.fromisoformat(lock["created"]), datetime.fromisoformat(written["created"]))
        self.assertEqual(lock["holder"], {"pid": written["pid"], "host": written["host"]})
        self.assertEqual(lock["version"], hashlib.sha256(data).hexdigest())
        self.assertIs(lock["stale"], stale)
        self.assertGreaterEqual(lock["age_seconds"], 600 if stale else 0)
        if not stale:
            self.assertLess(lock["age_seconds"], 600)

    def history_mutations_of(self, versions: dict) -> dict:
        mutations = self.mutations(versions)
        return {name: mutations[name] for name in ("archive", "clear", "seal")}


class HeldLockTest(LockFixture, SharedBase):
    """Acceptance 7 and the ticket's second and third lines: a pre-created lock makes every history mutation return
    history-locked and leaves every file byte-identical; a completed save under it is deferred, and a later archive
    without the lock archives it."""

    def test_every_history_mutation_returns_history_locked_and_changes_nothing(self):
        versions = self.prepare()
        for project in (self.wt1, self.main):
            with self.subTest(project=project.name):
                data = self.write_lock()
                before = self.tree()
                for name, (command, option, work, payload) in self.history_mutations_of(versions).items():
                    with self.subTest(operation=name):
                        arguments = (command, option, work) if option else (command,)
                        result = self.run_tool(project, *arguments, payload=payload, expected=2)
                        self.assert_locked(result, data)
                        self.assertIn("Nothing was changed", result["message"])
                        self.assertEqual(self.changed(before, self.tree()), set())
                self.lock_path().unlink()

    def test_a_stale_lock_is_reported_stale(self):
        versions = self.prepare()
        data = self.write_lock(age=timedelta(minutes=11))
        before = self.tree()
        command, option, work, payload = self.mutations(versions)["archive"]
        result = self.run_mutation(command, option, work, payload, expected=2)
        self.assert_locked(result, data, stale=True)
        self.assertIn("only on their decision run unlock", result["message"])
        self.assertEqual(self.changed(before, self.tree()), set())

    def test_a_completed_save_under_the_lock_is_deferred_and_archived_later(self):
        versions = self.prepare()
        data = self.write_lock()
        before = self.tree()
        saved = self.run_tool(self.wt1, "create", "--work", "d.md", payload={"title": "d", "fields": DONE},
                              expected=2)
        self.assertEqual((saved["status"], saved["complete"], saved["code"], saved["cause_code"],
                          saved["defer_history"], saved["recovery"]),
                         ("partial", False, "deferred", "history-locked", True, "retry-archive"), saved)
        self.assertEqual(saved["lock"]["version"], hashlib.sha256(data).hexdigest())
        # Only the completed work was written; history, archives and the lock are as they were.
        self.assertEqual(self.changed(before, self.tree()), {"main/.feather/handoffs/d.md"})
        self.lock_path().unlink()
        archived = self.run_tool(self.wt1, "archive", "--work", "d.md", payload={"version": saved["version"]})
        self.assertEqual((archived["status"], archived["archived"]), ("ok", True), archived)
        retried = self.run_tool(self.wt1, "archive", "--work", "b.md", payload={"version": versions["b"]})
        self.assertEqual(retried["archived"], True, retried)
        titles = [entry["title"] for entry in self.run_tool(self.wt1, "history")["entries"]]
        self.assertEqual(sorted(titles), ["b", "d", "h"])
        self.assertFalse(self.lock_path().exists())

    def test_a_lock_the_tool_did_not_write_reports_its_file_time(self):
        self.prepare()
        self.lock_path().write_bytes(b"")
        old = (datetime.now(timezone.utc) - timedelta(minutes=20)).timestamp()
        os.utime(self.lock_path(), (old, old))
        result = self.run_tool(self.wt1, "seal", expected=2, payload={"version": "x", "ids": ["x"],
                                                                      "destination": "batch.md"})
        lock = result["lock"]
        self.assertEqual((result["code"], lock["format_valid"], lock["holder"], lock["stale"]),
                         ("history-locked", False, None, True), result)
        self.assertEqual(lock["version"], hashlib.sha256(b"").hexdigest())
        removed = self.run_tool(self.wt1, "unlock", payload={"version": lock["version"]})
        self.assertEqual((removed["status"], removed["removed"]), ("ok", True), removed)
        self.assertFalse(self.lock_path().exists())


class LockLifetimeTest(LockFixture, SharedBase):
    """The ticket's first and sixth lines: each mutation removes the lock afterwards, including on handled errors,
    and the lock is written and flushed, with its holder, before the history read it guards."""

    def test_no_lock_is_left_after_success_or_a_handled_error(self):
        versions = self.prepare()
        mutations = self.history_mutations_of(versions)
        for name in ("clear", "seal"):
            command, _, _, payload = mutations[name]
            with self.subTest(handled=name):
                before = self.tree()
                result = self.run_tool(self.wt1, command, payload={**payload, "version": "0" * 64}, expected=2)
                self.assertEqual(result["code"], "conflict", result)
                self.assertFalse(os.path.lexists(self.lock_path()))
                self.assertEqual(self.changed(before, self.tree()), set())
        archived = self.run_tool(self.wt1, "archive", "--work", "b.md", payload={"version": versions["b"]})
        self.assertEqual(archived["archived"], True, archived)
        history = self.run_tool(self.wt1, "history")
        for name, payload in (("seal", {"destination": "batch.md"}), ("clear", {"source": "archive/batch.md"})):
            with self.subTest(succeeded=name):
                version = next(document["version"] for document in self.run_tool(
                    self.wt1, "history", "--include-sealed")["documents"]
                    if document["source"] == ("history.md" if name == "seal" else "archive/batch.md"))
                result = self.run_tool(self.wt1, name, payload={**payload, "version": version,
                                                                "ids": [history["entries"][0]["id"]]})
                self.assertEqual(result["status"], "ok", result)
                self.assertNotIn("lock_left", result)
                self.assertFalse(os.path.lexists(self.lock_path()))

    def test_an_interrupted_operation_leaves_the_lock_it_wrote_before_reading_history(self):
        versions = self.prepare()
        before = self.tree()
        real, seen = archiving.read_file, {}

        def read_file(path):
            if Path(path) == self.store / "history.md":
                # The history read: the lock already holds this process's holder on disk.
                seen["data"] = self.lock_path().read_bytes()
                raise KeyboardInterrupt
            return real(path)
        with mock.patch.object(archiving, "read_file", side_effect=read_file), self.assertRaises(KeyboardInterrupt):
            self.invoke(self.wt1, "archive", "--work", "b.md", payload={"version": versions["b"]})
        written = json.loads(seen["data"])
        self.assertEqual(set(written), {"created", "host", "pid"})
        self.assertEqual((written["pid"], written["host"]), (os.getpid(), socket.gethostname()))
        self.assertEqual(self.changed(before, self.tree()), {"main/.feather/handoffs/" + LOCK})
        for project in (self.wt2, self.main):
            with self.subTest(project=project.name):
                result = self.run_tool(project, "clear", expected=2, payload={
                    "source": "history.md", "version": versions["history"], "ids": [versions["id"]]})
                self.assert_locked(result, seen["data"])
        self.assertEqual(self.lock_path().read_bytes(), seen["data"])


class UnlockTest(LockFixture, SharedBase):
    """Acceptance 8 and the ticket's fourth line: unlock refuses a fresh or changed lock and removes a stale,
    unchanged one."""

    def test_a_fresh_lock_is_not_stale(self):
        self.prepare()
        data = self.write_lock()
        before = self.tree()
        result = self.run_tool(self.wt1, "unlock", payload={"version": self.version_of()}, expected=2)
        self.assert_locked(result, data, code="not-stale")
        self.assertEqual(self.changed(before, self.tree()), set())

    def test_a_changed_lock_is_a_conflict(self):
        self.prepare()
        self.write_lock(age=timedelta(minutes=30))
        seen = self.version_of()
        data = self.write_lock(age=timedelta(minutes=30), pid=5151)
        before = self.tree()
        result = self.run_tool(self.wt1, "unlock", payload={"version": seen}, expected=2)
        self.assert_locked(result, data, stale=True, code="conflict")
        self.assertEqual(self.changed(before, self.tree()), set())

    def test_a_missing_lock_is_a_conflict(self):
        self.prepare()
        before = self.tree()
        result = self.run_tool(self.wt1, "unlock", payload={"version": "0" * 64}, expected=2)
        self.assertEqual((result["code"], result["lock"]), ("conflict", {"path": str(self.lock_path()),
                                                                         "present": False}), result)
        self.assertEqual(self.changed(before, self.tree()), set())

    def test_a_stale_unchanged_lock_is_removed(self):
        versions = self.prepare()
        data = self.write_lock(age=timedelta(minutes=11))
        before = self.tree()
        result = self.run_tool(self.wt1, "unlock", payload={"version": self.version_of()})
        self.assertEqual((result["status"], result["complete"], result["removed"]), ("ok", True, True), result)
        self.assertEqual(result["lock"]["version"], hashlib.sha256(data).hexdigest())
        self.assertEqual(self.changed(before, self.tree()), {"main/.feather/handoffs/" + LOCK})
        archived = self.run_tool(self.wt1, "archive", "--work", "b.md", payload={"version": versions["b"]})
        self.assertEqual(archived["archived"], True, archived)

    def test_unlock_input_names_only_the_version(self):
        self.prepare()
        self.write_lock(age=timedelta(minutes=11))
        before = self.tree()
        for payload in ({}, {"version": 1}, {"version": self.version_of(), "force": True}):
            with self.subTest(payload=payload):
                result = self.run_tool(self.wt1, "unlock", payload=payload, expected=2)
                self.assertEqual(result["code"], "input", result)
                self.assertEqual(self.changed(before, self.tree()), set())


class UncertainRootTest(LockFixture, SharedBase):
    """The ticket's seventh line: under an uncertain root, unlock and every operation that takes the lock are refused
    before any write, the lock included."""

    def test_unlock_and_every_locking_operation_are_refused(self):
        versions = self.prepare()
        self.write_lock(age=timedelta(minutes=11))
        before = self.tree()

        def override(directory, command):
            return (1, "", "fixture: worktree list failed") if command[:2] == ["worktree", "list"] else None
        operations = {**{name: (command, option, work, payload) for name, (command, option, work, payload)
                         in self.history_mutations_of(versions).items()},
                      "completed save": ("create", "--work", "d.md", {"title": "d", "fields": DONE}),
                      "unlock": ("unlock", None, None, {"version": self.version_of()})}
        with self.git_as(override=override):
            for name, (command, option, work, payload) in operations.items():
                with self.subTest(operation=name):
                    arguments = (command, option, work) if option else (command,)
                    _, result = self.invoke(self.wt1, *arguments, payload=payload)
                    self.assertEqual(result["root"]["state"], "uncertain", result)
                    self.assertEqual(result["code"], "project-root-uncertain", result)
                    self.assertEqual(self.changed(before, self.tree()), set())
        self.assertFalse((self.wt1 / ".feather").exists())


class LockPathTest(LockFixture, SharedBase):
    """The ticket's eighth line: the lock's creation and removal, and unlock's removal, go through the existing path
    check, so a lock path reached through a link or hard link is refused."""

    def assert_refused(self, versions: dict):
        before = self.tree()
        for name, (command, option, work, payload) in {
                **self.history_mutations_of(versions),
                "unlock": ("unlock", None, None, {"version": "0" * 64})}.items():
            with self.subTest(operation=name):
                arguments = (command, option, work) if option else (command,)
                result = self.run_tool(self.wt1, *arguments, payload=payload, expected=2)
                self.assertEqual(result["code"], "unsafe-path", result)
                self.assertEqual(self.changed(before, self.tree()), set())

    def test_a_hard_linked_lock_is_refused(self):
        versions = self.prepare()
        other = self.outside / "lock-copy"
        self.write_lock(age=timedelta(minutes=11))
        try:
            os.link(self.lock_path(), other)
        except OSError as error:
            self.skipTest(f"hard links unavailable on this volume: {error}")
        self.assert_refused(versions)
        self.assertTrue(self.lock_path().exists())

    def test_a_linked_lock_path_is_refused(self):
        versions = self.prepare()
        feather_support.make_directory_link(self.lock_path(), self.outside)
        self.assert_refused(versions)
        self.assertEqual(os.listdir(self.outside), [])

    def test_the_lock_is_removed_only_through_the_path_check(self):
        versions = self.prepare()
        probe, other = self.store / "probe", self.outside / "lock-copy"
        probe.write_bytes(b"")
        try:
            os.link(probe, self.outside / "probe-copy")
        except OSError as error:
            self.skipTest(f"hard links unavailable on this volume: {error}")
        probe.unlink()
        (self.outside / "probe-copy").unlink()
        real = archiving.read_file

        def read_file(path):
            if Path(path) == self.store / "history.md" and not other.exists():
                # While the archive holds the lock, a hard link to it appears.
                os.link(self.lock_path(), other)
            return real(path)
        with mock.patch.object(archiving, "read_file", side_effect=read_file):
            code, result = self.invoke(self.wt1, "archive", "--work", "b.md", payload={"version": versions["b"]})
        self.assertEqual((code, result["status"], result["archived"]), (0, "ok", True), result)
        self.assertEqual(result["lock_left"]["path"], str(self.lock_path()), result)
        self.assertIn("Hard-linked file is not supported", result["lock_left"]["message"])
        self.assertTrue(self.lock_path().exists())


class NotARecordTest(LockFixture, SharedBase):
    """The ticket's fifth line: list, the pending-unknown checks and Handoff tidy, which reads records through list,
    never treat the lock file as a record."""

    def test_list_does_not_report_the_lock(self):
        self.prepare()
        listed = self.run_tool(self.wt1, "list")
        self.write_lock()
        with_lock = self.run_tool(self.wt1, "list")
        self.assertEqual((with_lock["status"], with_lock["complete"], with_lock["issues"]), ("ok", True, []), with_lock)
        self.assertEqual(with_lock["items"], listed["items"])
        self.assertNotIn(LOCK, [item["work"] for item in with_lock["items"]])

    def test_the_pending_checks_run_while_the_lock_exists_and_ignore_it(self):
        versions = self.prepare()
        real, seen = history_mutations.check_pending, []

        def check_pending(*args):
            seen.append(self.lock_path().is_file())
            return real(*args)
        with mock.patch.object(history_mutations, "check_pending", side_effect=check_pending):
            code, result = self.invoke(self.wt1, "clear", payload={
                "source": "history.md", "version": versions["history"], "ids": [versions["id"]]})
        self.assertEqual((code, result["status"]), (0, "ok"), result)
        self.assertNotIn("warnings", result)
        self.assertEqual(seen, [True])
        self.assertFalse(self.lock_path().exists())


class UnwritableLockTest(LockFixture, SharedBase):
    """The ticket's ninth line: creating the lock in a store the session cannot write is store-unwritable, while a
    lock file pending deletion on Windows is a held lock."""

    def test_a_denied_lock_creation_is_store_unwritable(self):
        versions = self.prepare()
        self.deny(self.store)
        before = self.tree()
        for name, (command, option, work, payload) in self.history_mutations_of(versions).items():
            with self.subTest(operation=name):
                result = self.run_mutation(command, option, work, payload, expected=2)
                self.assert_unwritable(result)
                self.assertNotIn("lock", result)
                self.assertEqual(self.changed(before, self.tree()), set())
        self.assertFalse(os.path.lexists(self.lock_path()))

    def pending_deletion(self):
        """Leave a lock file pending deletion until cleanup: a handle with classic delete-on-close disposition."""
        if not WINDOWS:
            self.skipTest(NO_PENDING_DELETE)
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateFileW.restype = wintypes.HANDLE
        kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
                                       wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        kernel.SetFileInformationByHandle.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self.write_lock()
        # DELETE access, every share mode, OPEN_EXISTING; FileDispositionInfo (4) with DeleteFile set.
        handle = kernel.CreateFileW(str(self.lock_path()), 0x10000, 7, None, 3, 0, None)
        if handle in (None, wintypes.HANDLE(-1).value):
            self.skipTest(f"the lock file could not be opened for deletion: {ctypes.get_last_error()}")
        self.addCleanup(kernel.CloseHandle, handle)
        flag = ctypes.c_ubyte(1)
        if not kernel.SetFileInformationByHandle(handle, 4, ctypes.byref(flag), 1):
            self.skipTest(f"the lock file could not be marked for deletion: {ctypes.get_last_error()}")
        try:
            self.lock_path().read_bytes()
        except PermissionError:
            return
        self.skipTest("the volume removed the name at once instead of leaving the file pending deletion")

    def tree_without_lock(self) -> dict:
        tree = {}
        for directory, directories, files in os.walk(self.base):
            for name in files:
                item = Path(directory, name)
                if item != self.lock_path():
                    tree[item.relative_to(self.base).as_posix()] = item.read_bytes()
        return tree

    def assert_pending_held(self, versions: dict, invoke: bool = False):
        before = self.tree_without_lock()
        for name, (command, option, work, payload) in self.history_mutations_of(versions).items():
            with self.subTest(operation=name):
                arguments = (command, option, work) if option else (command,)
                if invoke:
                    _, result = self.invoke(self.wt1, *arguments, payload=payload)
                else:
                    result = self.run_tool(self.wt1, *arguments, payload=payload, expected=2)
                self.assertEqual((result["status"], result["code"]), ("error", "history-locked"), result)
                self.assertEqual((result["lock"]["readable"], result["lock"]["version"]), (False, None), result)
                self.assertNotIn("store", result)
                self.assertEqual(self.tree_without_lock(), before)

    def test_a_lock_pending_deletion_is_held(self):
        versions = self.prepare()
        self.pending_deletion()
        self.assert_pending_held(versions)

    def test_a_lock_pending_deletion_is_held_when_its_stat_fails(self):
        versions = self.prepare()
        self.pending_deletion()
        real = Path.lstat
        for failure in (FileNotFoundError, PermissionError):
            def lstat(path, *args, **kwargs):
                if path == self.lock_path():
                    raise failure(2 if failure is FileNotFoundError else 13, "fixture: stat failed", str(path))
                return real(path, *args, **kwargs)
            with self.subTest(failure=failure.__name__), mock.patch.object(Path, "lstat", lstat):
                self.assert_pending_held(versions, invoke=True)


class HistoryLockDocumentationTest(unittest.TestCase):
    """Acceptance 12's skill and tool-reference share for items 7 and 8, and the ticket's tenth line."""

    SKILL_SENTENCES = (
        "History mutations, the archive step of a completed save, `archive`, `clear` and `seal`, take the tool's "
        "history lock, `.feather/handoffs/.history.lock` in the Handoff store, so sessions sharing that store cannot "
        "lose each other's completions.",
        "If the tool returns `history-locked`, another operation holds history and nothing was changed: report the "
        "lock's holder and age, and retry once it finishes; independent active work may continue.",
        "A completed save that meets the lock is kept as `deferred`; retry it with `archive`.",
        "Run `unlock` only on the user's explicit decision after showing the lock's holder and age, with the version "
        "that `history-locked` result reported; never run it automatically.",
        "`unlock` removes only a stale lock, older than ten minutes, whose content is unchanged.",
    )
    TOOL_SENTENCES = (
        "Work-file writes take no lock: keep one writer for a work item, and rely on the content version check, which "
        "does not close the gap between checking and writing, to detect conflicts there.",
        "History mutations take the history lock described in [History lock](#history-lock).",
        "A completed save that meets the [history lock](#history-lock) keeps the saved work and returns "
        "`status: partial`, `code: deferred` with `cause_code: history-locked`, `defer_history: true`, the `lock` "
        "object and `recovery: retry-archive`, leaving history unchanged.",
        "`defer_history: true` in the save's input also keeps the completed work without touching history.",
        "Every operation that changes `history.md` or `archive/`, namely the archive step of a completed save, "
        "`archive`, `clear` and `seal`, holds the history lock `.feather/handoffs/.history.lock` in the Handoff store "
        "from the history read it acts on until its last history write and source removal are verified, and removes "
        "it afterwards, including when it returns an error it handled.",
        "The lock is created with an exclusive create and holds one JSON line with the creating process ID `pid`, the "
        "host name `host` and the zoned creation time `created`, written and flushed before the history read it "
        "guards.",
        "Its creation and removal, and `unlock`'s removal, pass the same link, reparse-point and hard-link checks as "
        "records, so a lock path reached through a link or hard link is refused with `unsafe-path`.",
        "Under an uncertain root these operations and `unlock` fail with `project-root-uncertain` before writing "
        "anything, the lock included.",
        "The lock is not a work file: `list` and the `pending-unknown` checks never treat it as a record, so nothing "
        "that reads records through `list` does.",
        "When the lock already exists, the operation changes nothing and returns `status: error`, "
        "`code: history-locked` and a `lock` object with `path`, `created`, `holder` (`pid` and `host`), "
        "`age_seconds`, `version`, the SHA-256 of the lock's content, and `stale`, which is `true` when the lock is "
        "older than ten minutes.",
        "A lock that exists but cannot be read, such as a lock file pending deletion on Windows, is still held: it "
        "reports `readable: false` and no `version`; retry shortly.",
        "When creating the lock is denied, the result is that of a denied history write: `store-unwritable` in a "
        "shared run, and the previous `partial` results in a checkout-local store.",
        "A crash or an interrupted run leaves the lock in place; the tool reports it and never breaks it.",
        "`unlock` with `{ \"version\": \"<lock version from history-locked>\" }` removes the lock only when it is stale "
        "and its content is unchanged since that result.",
        "A fresh lock returns `not-stale`, and a changed or missing lock returns `conflict`, both with "
        "`status: error`, the current `lock` and nothing changed; a removal returns `status: ok` and `removed: true`.",
        "Run `unlock` only on the user's explicit decision after showing the lock's holder and age.",
        "The lock serializes this tool's history mutations on one Handoff store across the sessions and checkouts "
        "that share it.",
        "It does not cover work-file writes, which keep one writer per work item, edits of history or archives made "
        "outside the tool, the checkout-local store of another checkout, which has its own lock, or a run of an older "
        "tool that takes no lock.",
        "In tracked mode the lock is a temporary file inside the tracked `.feather/handoffs/` directory that is never "
        "committed: the tool stages and commits nothing, so leave it out of a commit, and clear a lock left by a "
        "crash with `unlock` instead of committing it.",
    )

    def test_the_skill_states_the_lock_rules(self):
        assert_sentences(self, SKILL, self.SKILL_SENTENCES)

    def test_the_tool_reference_documents_the_lock(self):
        assert_sentences(self, TOOL_REFERENCE, self.TOOL_SENTENCES)

    def test_the_external_serialization_statements_are_gone(self):
        for path, sentence in (
                (TOOL_REFERENCE, "The tool is not a lock or a cross-session transaction system."),
                (TOOL_REFERENCE, "serialize all shared-history operations externally"),
                (TOOL_REFERENCE, "If another session is known to be writing shared history, use `defer_history: true`"),
                (SKILL, "Concurrent sessions must arrange a single history writer externally."),
                (SKILL, "provides no cross-session lock")):
            with self.subTest(sentence=sentence):
                self.assertNotIn(sentence, normalized(path))


if __name__ == "__main__":
    unittest.main()
