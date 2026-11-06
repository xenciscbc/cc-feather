"""An unwritable Handoff store fails visibly (worktree store ticket 03).

When the operating system or the session sandbox denies creating files in the shared store (root.shared true),
create, update, archive, clear and seal return `error` with code `store-unwritable`, naming the store and the write
access the session needs. Nothing is written in the Working checkout in the store's place, and every record already
in the store stays readable and can be retried once access is granted. Every other result keeps its code from the
claim base (f0fad3a): a checkout-local store's denied writes, a seal denied after writing its destination
(`seal-failed`), a completed save whose history write is denied (`history-save-failed`) and a denied ignore-rule
write after a saved record (`tracking-failed`); the two partials add `cause_code: store-unwritable` in a shared run.
A read-only work file keeps its `read-only` code and an unrelated I/O error stays `io`.

The write is denied on Windows with a denying ACL entry for the current user (`icacls /deny`), because Windows ignores
the read-only attribute on directories, and on POSIX with permission bits. Each case first probes that the denial
holds and is skipped with the reason when the platform or user can still create files there, for example when
running as root or on a volume that ignores permission bits. Every ACL or mode change is restored before the base is
removed. The fixture and its isolated Git environment are those of tests/test_handoff_shared_store.py; the tool runs
as a subprocess with --project, and the in-process cases drive only the CLI entry point."""
import errno
import hashlib
import os
from pathlib import Path
import stat
import subprocess
import unittest
from unittest import mock

from tests.test_handoff_shared_store import FIELDS, SKILL, TOOL_REFERENCE, SharedBase, assert_sentences
from feather_handoff import storage

WINDOWS = os.name == "nt"
NOT_DENIED = ("this platform and user can still create files in a directory denied write access (for example "
              "running as root, or a volume that ignores permission bits or ACLs)")
DONE = {**FIELDS, "status": "完成"}


class DenyMixin:
    def deny(self, directory: Path, inherit: bool = True):
        """Deny creating files and directories in directory (and, with inherit, below it) and restore it on cleanup.

        Skips the test when a probe file can still be created there."""
        if WINDOWS:
            user = os.environ.get("USERNAME")
            if not user:
                self.skipTest("no USERNAME to deny writing the directory to")
            rights = "(OI)(CI)(WD,AD)" if inherit else "(WD,AD)"
            denied = subprocess.run(["icacls", str(directory), "/deny", f"{user}:{rights}"], capture_output=True)
            self.addCleanup(subprocess.run, ["icacls", str(directory), "/remove:d", user], capture_output=True)
            if denied.returncode:
                self.skipTest(f"icacls could not deny writing {directory} (exit {denied.returncode})")
        else:
            changed = [directory] + ([path for path in directory.rglob("*") if path.is_dir()] if inherit else [])
            for path in changed:
                mode = stat.S_IMODE(path.stat().st_mode)
                path.chmod(0o555)
                self.addCleanup(path.chmod, mode)
        probe = directory / ".probe"
        try:
            descriptor = os.open(probe, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
        except PermissionError:
            return
        os.close(descriptor)
        probe.unlink()
        self.skipTest(NOT_DENIED)

    def assert_unwritable(self, result: dict):
        self.assertEqual((result["status"], result["complete"], result["code"]), ("error", False, "store-unwritable"),
                         result)
        self.assertEqual((result["store"], result["access"]), (str(self.store), "write"), result)
        self.assertIn(f"The Handoff store {self.store} is not writable", result["message"])
        self.assertIn(f"The session needs write access to {self.store}; nothing was written in the Working checkout "
                      "in its place.", result["message"])
        self.assertEqual((result["root"]["store"], result["root"]["shared"]), (str(self.main), True), result)


class StoreFixture(DenyMixin):
    """Records prepared through the tool from working(), then the five store mutations on them."""

    def working(self) -> Path:
        return self.wt1

    def prepare(self) -> dict:
        """From the Working checkout: an active a.md, a deferred completed b.md, and history holding the completed h.md."""
        active = self.run_tool(self.working(), "create", "--work", "a.md", payload={"title": "a", "fields": FIELDS})
        deferred = self.run_tool(self.working(), "create", "--work", "b.md", expected=2,
                                 payload={"title": "b", "fields": DONE, "defer_history": True})
        self.assertEqual(deferred["code"], "deferred", deferred)
        done = self.run_tool(self.working(), "create", "--work", "h.md", payload={"title": "h", "fields": DONE})
        self.assertEqual(done["archived"], True, done)
        (self.store / "archive").mkdir()
        history = self.run_tool(self.working(), "history")
        return {"a": active["version"], "b": deferred["version"], "history": history["documents"][0]["version"],
                "id": history["entries"][0]["id"]}

    def mutations(self, versions: dict) -> dict:
        return {
            "create": ("create", "--work", "c.md", {"title": "c", "fields": FIELDS}),
            "update": ("update", "--work", "a.md", {"version": versions["a"], "fields": {"next": "m"}}),
            "archive": ("archive", "--work", "b.md", {"version": versions["b"]}),
            "clear": ("clear", None, None, {"source": "history.md", "version": versions["history"],
                                            "ids": [versions["id"]]}),
            "seal": ("seal", None, None, {"version": versions["history"], "ids": [versions["id"]],
                                          "destination": "batch.md"}),
        }

    def run_mutation(self, command, option, work, payload, expected):
        arguments = (command, option, work) if option else (command,)
        return self.run_tool(self.working(), *arguments, payload=payload, expected=expected)

    def deny_check_inherited(self):
        """The denial also reaches archive/, so seal is refused at its first write too."""
        probe = self.store / "archive" / ".probe"
        try:
            os.close(os.open(probe, os.O_WRONLY | os.O_CREAT | os.O_EXCL))
        except PermissionError:
            return
        probe.unlink()
        self.skipTest(NOT_DENIED)

    def grant_access(self):
        """Grant write access to the store again before the test ends; the cleanups registered by deny repeat it."""
        if WINDOWS:
            restored = subprocess.run(["icacls", str(self.store), "/remove:d", os.environ["USERNAME"]],
                                      capture_output=True)
            self.assertEqual(restored.returncode, 0, restored)
        else:
            for path in [self.store, *(path for path in self.store.rglob("*") if path.is_dir())]:
                path.chmod(0o755)


class UnwritableStoreTest(StoreFixture, SharedBase):
    """Acceptance 5 and the ticket's first and third lines: every store mutation from a linked worktree returns
    store-unwritable, the whole base stays byte-identical, and the records already written stay recoverable."""

    def test_every_store_mutation_fails_visibly_and_writes_nothing(self):
        versions = self.prepare()
        listed = self.run_tool(self.wt1, "list")
        self.deny(self.store)
        self.deny_check_inherited()
        before = self.tree()
        for name, (command, option, work, payload) in self.mutations(versions).items():
            with self.subTest(operation=name):
                self.assert_unwritable(self.run_mutation(command, option, work, payload, expected=2))
                # No file anywhere in the base changed: not the store, the main worktree or the Working checkout.
                self.assertEqual(self.changed(before, self.tree()), set())
        self.assertFalse((self.wt1 / ".feather").exists())
        # Records already written stay readable with their versions while access is denied.
        self.assertEqual(self.run_tool(self.wt1, "list")["items"], listed["items"])
        self.assertEqual(self.run_tool(self.wt2, "read", "--work", "a.md")["version"], versions["a"])

    def test_records_are_recoverable_once_access_is_granted(self):
        versions = self.prepare()
        self.deny(self.store)
        for name in ("update", "archive"):
            command, option, work, payload = self.mutations(versions)[name]
            self.assert_unwritable(self.run_mutation(command, option, work, payload, expected=2))
        self.grant_access()
        updated = self.run_tool(self.wt1, "update", "--work", "a.md",
                                payload={"version": versions["a"], "fields": {"next": "m"}})
        self.assertEqual(updated["status"], "ok", updated)
        archived = self.run_tool(self.wt1, "archive", "--work", "b.md", payload={"version": versions["b"]})
        self.assertEqual(archived["archived"], True, archived)
        self.assertFalse((self.wt1 / ".feather").exists())

    def test_a_seal_denied_after_writing_its_destination_keeps_it_for_the_retry(self):
        versions = self.prepare()
        # Only the store directory itself is denied; archive/ keeps accepting the destination.
        self.deny(self.store, inherit=False)
        before = self.tree()
        command, option, work, payload = self.mutations(versions)["seal"]
        sealed = self.run_mutation(command, option, work, payload, expected=2)
        # The partial result and its retry are those of the claim base; the shared run adds the cause.
        self.assertEqual((sealed["status"], sealed["code"], sealed["cause_code"]),
                         ("partial", "seal-failed", "store-unwritable"), sealed)
        destination = self.store / "archive" / "batch.md"
        self.assertEqual(self.changed(before, self.tree()), {"main/.feather/handoffs/archive/batch.md"})
        self.assertEqual(sealed["destination_version"], hashlib.sha256(destination.read_bytes()).hexdigest())
        self.grant_access()
        retried = self.run_tool(self.wt1, "seal", payload={**payload, "destination_version": sealed["destination_version"]})
        self.assertEqual((retried["status"], Path(retried["destination"])), ("ok", destination), retried)
        self.assertFalse((self.wt1 / ".feather").exists())

    def test_a_missing_store_under_an_unwritable_main_worktree_is_not_created_elsewhere(self):
        self.deny(self.main, inherit=False)
        before = self.tree()
        result = self.run_tool(self.wt1, "create", "--work", "c.md", payload={"title": "c", "fields": FIELDS},
                               expected=2)
        self.assert_unwritable(result)
        self.assertEqual(self.changed(before, self.tree()), set())
        self.assertFalse((self.wt1 / ".feather").exists())


class CheckoutLocalStoreTest(StoreFixture, SharedBase):
    """Main's scope decision: store-unwritable is a shared-store result. A checkout-local store whose writes are
    denied keeps each operation's result exactly as at the claim base (f0fad3a)."""

    def working(self) -> Path:
        return self.main

    EXPECTED = {"create": ("error", "io"), "update": ("error", "io"), "archive": ("partial", "history-save-failed"),
                "clear": ("partial", "clear-failed"), "seal": ("partial", "seal-failed")}

    def test_a_denied_checkout_local_store_keeps_its_previous_results(self):
        versions = self.prepare()
        self.deny(self.store)
        self.deny_check_inherited()
        before = self.tree()
        for name, (command, option, work, payload) in self.mutations(versions).items():
            with self.subTest(operation=name):
                result = self.run_mutation(command, option, work, payload, expected=2)
                self.assertEqual((result["status"], result["code"]), self.EXPECTED[name], result)
                self.assertNotIn("cause_code", result)
                self.assertNotIn("store", result)
                self.assertFalse(result["root"]["shared"], result)
                self.assertEqual(self.changed(before, self.tree()), set())


class CompletedSaveTest(SharedBase):
    """Main's decision: a completed save whose history write is denied keeps its partial history-save-failed result
    and retry-archive recovery as at the claim base; only a shared run adds cause_code store-unwritable. Only the
    history's temporary file can be denied while the work's own replacement in the same directory succeeds, so the
    denial is injected at the second temporary-file creation through the CLI entry point."""

    def complete(self, project: Path) -> dict:
        created = self.run_tool(project, "create", "--work", "a.md", payload={"title": "a", "fields": FIELDS})
        self.run_tool(project, "create", "--work", "h.md", payload={"title": "h", "fields": DONE})
        before = self.tree()
        real, calls = os.open, []

        def open_(path, *args, **kwargs):
            calls.append(path)
            if len(calls) > 1:
                raise PermissionError(errno.EACCES, os.strerror(errno.EACCES), str(path))
            return real(path, *args, **kwargs)
        with mock.patch.object(storage.os, "open", side_effect=open_):
            code, result = self.invoke(project, "update", "--work", "a.md", payload={
                "version": created["version"], "fields": {"status": "完成", "updated": "2026-11-05T11:00:00+08:00"}})
        self.assertEqual(code, 2)
        self.assertEqual((result["status"], result["code"], result["recovery"], result["work_present"]),
                         ("partial", "history-save-failed", "retry-archive", True), result)
        # Only the completed work changed; history is as it was.
        self.assertEqual({name.rsplit("/", 1)[-1] for name in self.changed(before, self.tree())}, {"a.md"})
        return result

    def test_a_shared_run_adds_the_cause(self):
        self.assertEqual(self.complete(self.wt1)["cause_code"], "store-unwritable")

    def test_a_checkout_local_run_is_unchanged(self):
        self.assertNotIn("cause_code", self.complete(self.main))


class TrackingAfterSaveTest(DenyMixin, SharedBase):
    """The ticket's second line: a denied ignore-rule write after the record was saved is still tracking-failed."""

    def test_a_denied_gitignore_after_a_saved_record_is_tracking_failed(self):
        self.store.mkdir(parents=True)
        self.deny(self.main, inherit=False)
        before = self.tree()
        result = self.run_tool(self.wt1, "create", "--work", "a.md", payload={"title": "a", "fields": FIELDS},
                               expected=2)
        self.assertEqual((result["status"], result["code"], result["cause_code"], result["state"]),
                         ("partial", "tracking-failed", "io", "saved"), result)
        self.assertEqual(result["version"], result["saved_version"])
        self.assertEqual(self.changed(before, self.tree()), {"main/.feather/handoffs/a.md"})
        self.assertFalse((self.main / ".gitignore").exists())


class OtherFailuresKeepTheirCodesTest(SharedBase):
    """A read-only work file stays read-only and an unrelated I/O error stays io; neither is store-unwritable."""

    def test_a_read_only_work_file_stays_read_only(self):
        if not WINDOWS:
            self.skipTest("POSIX rename replaces a read-only file in a writable directory, so there is no refusal")
        created = self.run_tool(self.wt1, "create", "--work", "a.md", payload={"title": "a", "fields": FIELDS})
        path = self.store / "a.md"
        os.chmod(path, stat.S_IREAD)
        self.addCleanup(os.chmod, path, stat.S_IREAD | stat.S_IWRITE)
        before = self.tree()
        result = self.run_tool(self.wt1, "update", "--work", "a.md", expected=2,
                               payload={"version": created["version"], "fields": {"next": "m"}})
        self.assertEqual((result["status"], result["code"]), ("error", "read-only"), result)
        self.assertEqual(self.changed(before, self.tree()), set())

    def test_an_unrelated_io_error_stays_io(self):
        created = self.run_tool(self.wt1, "create", "--work", "a.md", payload={"title": "a", "fields": FIELDS})
        before = self.tree()
        failure = OSError(errno.ENOSPC, os.strerror(errno.ENOSPC))
        with mock.patch.object(storage.os, "open", side_effect=failure):
            code, result = self.invoke(self.wt1, "update", "--work", "a.md",
                                       payload={"version": created["version"], "fields": {"next": "m"}})
        self.assertEqual((code, result["status"], result["code"]), (2, "error", "io"), result)
        self.assertEqual(self.changed(before, self.tree()), set())

    def test_a_target_held_open_is_not_reported_as_an_unwritable_store(self):
        if not WINDOWS:
            self.skipTest("POSIX rename replaces a file another process holds open, so there is no failure")
        created = self.run_tool(self.wt1, "create", "--work", "a.md", payload={"title": "a", "fields": FIELDS})
        before = self.tree()
        # Python opens without FILE_SHARE_DELETE, so replacing the held file fails although the store is writable.
        with (self.store / "a.md").open("rb"):
            result = self.run_tool(self.wt1, "update", "--work", "a.md", expected=2,
                                   payload={"version": created["version"], "fields": {"next": "m"}})
        self.assertEqual((result["status"], result["code"]), ("error", "io"), result)
        self.assertEqual(self.changed(before, self.tree()), set())

    def test_a_directory_named_like_the_work_file_is_not_an_unwritable_store(self):
        # Windows reports EACCES for an exclusive create over a directory; POSIX reports EEXIST.
        (self.store / "c.md").mkdir(parents=True)
        before = self.tree()
        result = self.run_tool(self.wt1, "create", "--work", "c.md", expected=2,
                               payload={"title": "c", "fields": FIELDS})
        self.assertEqual((result["status"], result["code"]), ("error", "io" if WINDOWS else "exists"), result)
        self.assertNotIn("store", result)
        self.assertNotIn("access", result)
        self.assertEqual(self.changed(before, self.tree()), set())


class UnwritableStoreDocumentationTest(unittest.TestCase):
    """Acceptance 12's skill and tool-reference share for item 5."""

    SKILL_SENTENCES = (
        "If the tool returns `store-unwritable`, the session cannot write the shared Handoff store: report the store path "
        "and that the session needs write access to it, and never recreate the records inside the Working checkout "
        "or the linked worktree in its place.",
    )
    TOOL_SENTENCES = (
        "When the operating system or the session sandbox denies creating a file or directory in the shared Handoff "
        "store, that is, when `root.shared` is true, create, update, archive, clear and seal return `status: error`, "
        "`code: store-unwritable`, `store` with the store directory and `access: write`, and the `message` names the "
        "store and says that the session needs write access to it.",
        "The tool writes nothing in the Working checkout in its place; records already in the store stay as they "
        "were, so retry the same operation once access is granted.",
        "A seal that already wrote its destination before the denial keeps its `partial` `seal-failed` result with "
        "the `destination_version` to retry with, and a completed save whose history write is denied keeps its "
        "`partial` `history-save-failed` result with `recovery: retry-archive`; in a shared run both add "
        "`cause_code: store-unwritable`.",
        "A denied ignore-rule write after the record was saved stays `tracking-failed`.",
        "A checkout-local store keeps its previous results for a denied write, such as `io`, a read-only work file is "
        "still `read-only`, and other I/O failures, such as a full disk or a file another process holds open, are "
        "still `io`.",
    )

    def test_the_skill_says_to_report_and_never_recreate(self):
        assert_sentences(self, SKILL, self.SKILL_SENTENCES)

    def test_the_tool_reference_documents_store_unwritable(self):
        assert_sentences(self, TOOL_REFERENCE, self.TOOL_SENTENCES)


if __name__ == "__main__":
    unittest.main()
