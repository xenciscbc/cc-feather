"""Protect a held Checkout lease with a Git worktree lock (checkout leases ticket 02).

The lease tool runs as a subprocess against temporary real Git repositories with real linked worktrees, and only its
JSON result and exit status are asserted, with the fixture of tests/test_leases_tool.py. Locks are set and read with
`git worktree lock --reason` and `git worktree list --porcelain -z`, using Claude Code's observed reason formats
(`claude session <name> (pid N)`, `claude agent <id> (pid N)`); Claude Code itself is not driven. One case denies the
current user write access to one worktree's administration directory for the duration of one acquire (icacls on
Windows, chmod elsewhere) and restores it on cleanup. Critical-section locks left by a crashed operation are synthetic
files written by the tests. Synthetic data only, removed on cleanup."""
import os
from pathlib import Path
import shutil
import subprocess
import unittest
import uuid

from tests.test_leases_tool import LeaseBase

SESSION = "claude session feature-x (pid 4242)"
AGENT = "claude agent a1b2c3d4 (pid 777)"


class LockBase(LeaseBase):
    def lock(self, checkout: Path, reason: str | None):
        self.git(self.main, "worktree", "lock", *(["--reason", reason] if reason is not None else []), str(checkout))

    def unlock(self, checkout: Path):
        self.git(self.main, "worktree", "unlock", str(checkout))

    def locked(self, checkout: Path) -> str | None:
        """The checkout's lock reason as `git worktree list --porcelain -z` reports it, or None when unlocked."""
        output = subprocess.run(["git", "-C", str(self.main), "worktree", "list", "--porcelain", "-z"],
                                capture_output=True, text=True, encoding="utf-8", timeout=60).stdout
        for record in output.split("\0\0"):
            fields = [field for field in record.split("\0") if field]
            if fields and os.path.normcase(os.path.normpath(fields[0][len("worktree "):])) == \
                    os.path.normcase(str(checkout)):
                for field in fields[1:]:
                    if field == "locked" or field.startswith("locked "):
                        return field[len("locked "):] if " " in field else ""
                return None
        self.fail(f"{checkout} is not registered")

    def registered(self, checkout: Path) -> bool:
        listed = self.git(self.main, "worktree", "list", "--porcelain")
        return any(os.path.normcase(os.path.normpath(line[len("worktree "):])) == os.path.normcase(str(checkout))
                   for line in listed.splitlines() if line.startswith("worktree "))

    def remove_tree(self, path: Path):
        shutil.rmtree(path)
        self.assertFalse(path.exists())

    def own(self, lease_id: str) -> str:
        return f"cc-feather lease {lease_id}"

    def acquire_attested(self, checkout: Path, attested: str, *, expected=0) -> dict:
        return self.lease(self.main, "acquire", "--checkout", str(checkout), "--session", "s", "--purpose", "p",
                          "--accept-session-lock", attested, expected=expected)


class AcquireLockTest(LockBase):
    def test_acquiring_a_free_linked_worktree_locks_it_with_the_leases_reason(self):
        acquired = self.acquire(self.main, self.wt1)
        self.assertEqual((acquired["status"], acquired["acquired"]), ("ok", True), acquired)
        reason = self.own(acquired["lease"]["lease_id"])
        self.assertEqual(self.locked(self.wt1), reason)
        self.assertIn("cc-feather", reason)
        self.assertEqual(acquired["lock"], {"state": "locked", "reason": reason, "pid": None, "holder": "lease"})
        self.assertIsNone(self.locked(self.wt2))

    def test_the_main_worktree_gets_the_lease_and_no_lock(self):
        acquired = self.acquire(self.wt1, self.main)
        self.assertEqual(acquired["status"], "ok", acquired)
        self.assertEqual(acquired["lock"]["state"], "not-lockable", acquired)
        self.assertIsNone(self.locked(self.main))
        listed = self.entry(self.listing(self.wt1), self.main)
        self.assertEqual((listed["lease"]["state"], listed["lock"]["state"]), ("held", "not-lockable"), listed)

    def test_when_locking_fails_the_lease_is_withdrawn_and_the_acquire_fails(self):
        admin = self.main / ".git" / "worktrees" / "wt1"
        if os.name == "nt":
            user = os.environ.get("USERNAME") or self.skipTest("USERNAME is not set")
            subprocess.run(["icacls", str(admin), "/deny", f"{user}:(AD,WD)"], check=True, capture_output=True)
            self.addCleanup(subprocess.run, ["icacls", str(admin), "/remove:d", user], capture_output=True)
        else:
            if os.geteuid() == 0:
                self.skipTest("root ignores directory permissions")
            admin.chmod(0o555)
            self.addCleanup(admin.chmod, 0o755)
        failed = self.acquire(self.main, self.wt1, expected=2)
        self.assertEqual((failed["status"], failed["code"], failed["acquired"]), ("error", "lock-failed", False),
                         failed)
        self.assertTrue(failed["withdrawn"], failed)
        self.assertIn("withdrawn", failed["message"])
        self.assertIsNone(self.locked(self.wt1))
        self.assertFalse((self.leases / "wt1.json").exists())
        self.assertFalse((self.leases / "wt1.lock").exists())
        self.assertEqual(self.entry(self.listing(self.main), self.wt1)["lease"]["state"], "absent")

    def test_a_worktree_whose_directory_is_missing_is_not_acquired(self):
        self.remove_tree(self.wt1)
        listed = self.entry(self.listing(self.main), self.wt1)
        self.assertFalse(listed["directory_exists"], listed)
        refused = self.lease(self.main, "acquire", "--checkout", str(self.wt1), "--session", "s", "--purpose", "p")
        self.assertEqual((refused["status"], refused["acquired"]), ("refused", False), refused)
        self.assertEqual(refused["code"], "directory-missing", refused)
        self.assertFalse((self.leases / "wt1.json").exists())
        self.assertIsNone(self.locked(self.wt1))

    def test_a_worktree_git_marks_prunable_is_not_acquired(self):
        (self.wt1 / ".git").unlink()
        self.assertTrue(self.wt1.is_dir())
        listed = self.entry(self.listing(self.main), self.wt1)
        self.assertTrue(listed["prunable"], listed)
        refused = self.lease(self.main, "acquire", "--checkout", str(self.wt1), "--session", "s", "--purpose", "p")
        self.assertEqual((refused["status"], refused["code"]), ("refused", "prunable"), refused)
        self.assertFalse((self.leases / "wt1.json").exists())
        self.assertIsNone(self.locked(self.wt1))

class SessionLockTest(LockBase):
    def test_an_attested_session_lock_is_accepted_and_never_changed(self):
        self.lock(self.wt1, SESSION)
        acquired = self.acquire_attested(self.wt1, SESSION)
        self.assertEqual((acquired["status"], acquired["acquired"]), ("ok", True), acquired)
        self.assertEqual(acquired["lease"]["accepted_lock"], SESSION)
        self.assertEqual(acquired["lock"], {"state": "locked", "reason": SESSION, "pid": 4242,
                                            "holder": "accepted-session"})
        self.assertEqual(self.locked(self.wt1), SESSION)
        listed = self.entry(self.listing(self.wt2), self.wt1)
        self.assertEqual(listed["lock"]["holder"], "accepted-session", listed)
        self.assertEqual(self.locked(self.wt1), SESSION)

    def test_an_unattested_session_lock_blocks_acquisition(self):
        self.lock(self.wt1, SESSION)
        blocked = self.acquire(self.main, self.wt1)
        self.assert_blocked(blocked, self.wt1, SESSION, 4242)

    def test_a_session_lock_whose_reason_differs_from_the_attested_one_blocks_acquisition(self):
        self.lock(self.wt1, SESSION)
        for attested in ("claude session feature-x (pid 4243)", "claude session feature-y (pid 4242)"):
            with self.subTest(attested=attested):
                self.assert_blocked(self.acquire_attested(self.wt1, attested), self.wt1, SESSION, 4242)

    def test_an_attested_reason_that_is_not_a_session_lock_is_refused(self):
        self.lock(self.wt1, AGENT)
        refused = self.acquire_attested(self.wt1, AGENT, expected=2)
        self.assertEqual((refused["status"], refused["code"]), ("error", "input"), refused)
        self.assertEqual(self.locked(self.wt1), AGENT)
        self.assertFalse((self.leases / "wt1.json").exists())

    def test_every_other_lock_blocks_acquisition_and_its_reason_is_returned(self):
        cases = [(AGENT, 777), ("in use by backup-tool", None), ("", None), ("my own lock (pid 12)", 12)]
        for reason, pid in cases:
            with self.subTest(reason=reason):
                self.lock(self.wt1, reason if reason else None)
                self.assert_blocked(self.acquire(self.main, self.wt1), self.wt1, reason, pid)
                self.assert_blocked(self.acquire_attested(self.wt1, SESSION), self.wt1, reason, pid)
                self.unlock(self.wt1)

    def assert_blocked(self, blocked: dict, checkout: Path, reason: str, pid: int | None):
        self.assertEqual((blocked["status"], blocked["acquired"]), ("locked", False), blocked)
        self.assertEqual(blocked["lock"], {"state": "locked", "reason": reason, "pid": pid, "holder": "other"})
        self.assertIn("lock", blocked["message"])
        self.assertEqual(self.locked(checkout), reason)
        self.assertFalse((self.leases / f"{checkout.name}.json").exists())
        self.assertEqual(self.entry(self.listing(self.main), checkout)["lease"]["state"], "absent")


class ReleaseLockTest(LockBase):
    def test_release_removes_its_own_lock_and_then_the_lease(self):
        acquired = self.acquire(self.main, self.wt1)
        released = self.release(self.wt2, self.wt1, acquired["lease"]["lease_id"])
        self.assertEqual((released["status"], released["released"]), ("ok", True), released)
        self.assertEqual(released["lock"], {"removed": True, "reason": self.own(acquired["lease"]["lease_id"])})
        self.assertIsNone(self.locked(self.wt1))
        self.assertEqual(self.entry(self.listing(self.main), self.wt1)["lease"]["state"], "absent")

    def test_release_leaves_an_accepted_session_lock(self):
        self.lock(self.wt1, SESSION)
        acquired = self.acquire_attested(self.wt1, SESSION)
        released = self.release(self.main, self.wt1, acquired["lease"]["lease_id"])
        self.assertEqual(released["status"], "ok", released)
        self.assertFalse(released["lock"]["removed"], released)
        self.assertEqual(released["lock"]["kept"]["reason"], SESSION)
        self.assertEqual(self.locked(self.wt1), SESSION)
        self.assertFalse((self.leases / "wt1.json").exists())

    def test_release_leaves_a_foreign_lock_that_replaced_its_own(self):
        acquired = self.acquire(self.main, self.wt1)
        self.unlock(self.wt1)
        self.lock(self.wt1, AGENT)
        released = self.release(self.main, self.wt1, acquired["lease"]["lease_id"])
        self.assertEqual(released["status"], "ok", released)
        self.assertEqual((released["lock"]["removed"], released["lock"]["kept"]["reason"]), (False, AGENT))
        self.assertEqual(self.locked(self.wt1), AGENT)

    def test_release_leaves_a_cc_feather_lock_naming_another_lease(self):
        acquired = self.acquire(self.main, self.wt1)
        other = self.own(uuid.uuid4().hex)
        self.unlock(self.wt1)
        self.lock(self.wt1, other)
        released = self.release(self.main, self.wt1, acquired["lease"]["lease_id"])
        self.assertEqual((released["status"], released["lock"]["removed"]), ("ok", False), released)
        self.assertEqual(self.locked(self.wt1), other)

    def test_release_with_another_lease_id_keeps_the_lock(self):
        acquired = self.acquire(self.main, self.wt1)
        refused = self.release(self.main, self.wt1, "0" * 32)
        self.assertEqual(refused["status"], "changed-hands", refused)
        self.assertEqual(self.locked(self.wt1), self.own(acquired["lease"]["lease_id"]))


class RelockTest(LockBase):
    def test_listing_locks_a_lockless_held_lease_again_and_reports_it(self):
        acquired = self.acquire(self.main, self.wt1)
        self.unlock(self.wt1)
        listed = self.entry(self.listing(self.wt2), self.wt1)
        reason = self.own(acquired["lease"]["lease_id"])
        self.assertEqual(listed["lock"], {"state": "locked", "reason": reason, "pid": None, "holder": "lease",
                                          "relocked": True})
        self.assertEqual(self.locked(self.wt1), reason)
        again = self.entry(self.listing(self.wt2), self.wt1)
        self.assertNotIn("relocked", again["lock"])

    def test_a_lease_whose_accepted_session_lock_was_released_is_locked_again_with_its_own_reason(self):
        self.lock(self.wt1, SESSION)
        acquired = self.acquire_attested(self.wt1, SESSION)
        self.unlock(self.wt1)
        listed = self.entry(self.listing(self.main), self.wt1)
        self.assertEqual((listed["lock"]["holder"], listed["lock"].get("relocked")), ("lease", True), listed)
        self.assertEqual(self.locked(self.wt1), self.own(acquired["lease"]["lease_id"]))

    def test_acquire_locks_a_lockless_held_lease_again(self):
        first = self.acquire(self.main, self.wt1, session="alpha")
        self.unlock(self.wt1)
        second = self.acquire(self.main, self.wt1, session="beta")
        self.assertEqual((second["status"], second["lease"]), ("held", first["lease"]), second)
        self.assertEqual((second["lock"]["holder"], second["lock"].get("relocked")), ("lease", True), second)
        self.assertEqual(self.locked(self.wt1), self.own(first["lease"]["lease_id"]))

    def test_a_held_lease_whose_directory_is_missing_is_not_locked_again_and_stays_unknown(self):
        acquired = self.acquire(self.main, self.wt1)
        self.unlock(self.wt1)
        self.remove_tree(self.wt1)
        listed = self.entry(self.listing(self.main), self.wt1)
        self.assertEqual(listed["lease"]["state"], "unknown", listed)
        self.assertEqual(listed["lease"]["lease"], acquired["lease"])
        self.assertEqual(listed["lock"]["state"], "unlocked", listed)
        self.assertTrue(listed["lock"]["unprotected"], listed)
        self.assertIsNone(self.locked(self.wt1))
        blocked = self.acquire(self.main, self.wt1)
        self.assertEqual(blocked["acquired"], False, blocked)
        self.assertIsNone(self.locked(self.wt1))

    def test_a_held_lease_git_marks_prunable_is_not_locked_again(self):
        self.acquire(self.main, self.wt1)
        self.unlock(self.wt1)
        (self.wt1 / ".git").unlink()
        listed = self.entry(self.listing(self.main), self.wt1)
        self.assertEqual((listed["lease"]["state"], listed["lock"]["state"]), ("unknown", "unlocked"), listed)
        self.assertTrue(listed["lock"]["unprotected"], listed)
        self.assertIsNone(self.locked(self.wt1))

    def test_relocking_waits_for_no_held_critical_section(self):
        acquired = self.acquire(self.main, self.wt1)
        self.unlock(self.wt1)
        section = CriticalSectionLock(self.leases / "wt1.lock")
        listed = self.entry(self.listing(self.main), self.wt1)
        self.assertEqual(listed["lock"]["state"], "unlocked", listed)
        self.assertNotIn("relocked", listed["lock"])
        self.assertEqual(listed["lock"]["relock"]["status"], "busy", listed)
        self.assertIsNone(self.locked(self.wt1))
        self.assertEqual(section.read(), section.data)
        section.remove()
        listed = self.entry(self.listing(self.main), self.wt1)
        self.assertTrue(listed["lock"]["relocked"], listed)
        self.assertEqual(self.locked(self.wt1), self.own(acquired["lease"]["lease_id"]))

    def test_release_meets_a_held_critical_section_and_keeps_the_lock(self):
        acquired = self.acquire(self.main, self.wt1)
        CriticalSectionLock(self.leases / "wt1.lock")
        busy = self.release(self.main, self.wt1, acquired["lease"]["lease_id"])
        self.assertEqual(busy["status"], "busy", busy)
        self.assertEqual(self.locked(self.wt1), self.own(acquired["lease"]["lease_id"]))


class CriticalSectionLock:
    """A synthetic critical-section lock of the lease tool, as a crashed operation leaves it."""

    def __init__(self, path: Path):
        self.path = path
        self.data = b'{"created": "2026-11-09T10:00:00+00:00", "host": "fixture-host", "pid": 4242, ' \
                    b'"operation": "acquire", "checkout": "wt1"}\n'
        path.write_bytes(self.data)

    def read(self) -> bytes:
        return self.path.read_bytes()

    def remove(self):
        self.path.unlink()


class ListingLockTest(LockBase):
    def test_the_listing_shows_each_lock_as_written_with_its_process_id_and_holder(self):
        third = self.base / "wt3"
        self.git(self.main, "worktree", "add", "--quiet", str(third))
        own = self.acquire(self.main, self.wt1)
        self.lock(self.wt2, SESSION)
        self.lock(third, AGENT)
        listed = self.listing(self.main)
        self.assertEqual(self.entry(listed, self.wt1)["lock"],
                         {"state": "locked", "reason": self.own(own["lease"]["lease_id"]), "pid": None,
                          "holder": "lease"})
        self.assertEqual(self.entry(listed, self.wt2)["lock"],
                         {"state": "locked", "reason": SESSION, "pid": 4242, "holder": "other"})
        self.assertEqual(self.entry(listed, third)["lock"],
                         {"state": "locked", "reason": AGENT, "pid": 777, "holder": "other"})
        self.assertEqual(self.entry(listed, self.main)["lock"]["state"], "not-lockable")
        for checkout in (self.main, self.wt1, self.wt2, third):
            self.assertTrue(self.entry(listed, checkout)["directory_exists"])

    def test_an_unlocked_worktree_without_a_lease_shows_no_lock(self):
        listed = self.entry(self.listing(self.main), self.wt1)
        self.assertEqual(listed["lock"], {"state": "unlocked"})

    def test_a_cc_feather_lock_without_its_lease_is_a_mismatch(self):
        stray = self.own(uuid.uuid4().hex)
        self.lock(self.wt1, stray)
        entry = self.entry(self.listing(self.main), self.wt1)
        self.assertEqual((entry["lock"]["holder"], entry["lock"]["reason"]), ("cc-feather", stray), entry)
        self.assertTrue(entry["lock"]["mismatch"], entry)
        self.assertEqual(entry["lease"]["state"], "absent")
        blocked = self.acquire(self.main, self.wt1)
        self.assertEqual((blocked["status"], blocked["lock"]["holder"]), ("locked", "cc-feather"), blocked)
        self.assertTrue(blocked["lock"]["mismatch"], blocked)
        held = self.acquire(self.main, self.wt2)
        self.unlock(self.wt2)
        self.lock(self.wt2, stray)
        entry = self.entry(self.listing(self.main), self.wt2)
        self.assertEqual((entry["lock"]["holder"], entry["lease"]["lease"]), ("cc-feather", held["lease"]), entry)
        self.assertTrue(entry["lock"]["mismatch"], entry)
        self.assertEqual(self.locked(self.wt1), stray)
        self.assertEqual(self.locked(self.wt2), stray)

    def test_the_listing_never_changes_a_foreign_lock(self):
        self.acquire(self.main, self.wt1)
        self.unlock(self.wt1)
        self.lock(self.wt1, AGENT)
        entry = self.entry(self.listing(self.main), self.wt1)
        self.assertEqual((entry["lock"]["holder"], entry["lock"].get("relocked")), ("other", None), entry)
        self.assertEqual(self.locked(self.wt1), AGENT)


class CleanupTest(LockBase):
    def test_prune_and_a_plain_remove_leave_a_leased_worktree(self):
        acquired = self.acquire(self.main, self.wt1)
        self.assertEqual(acquired["status"], "ok", acquired)
        self.git(self.main, "worktree", "prune")
        self.assertTrue(self.registered(self.wt1))
        removed = subprocess.run(["git", "-C", str(self.main), "worktree", "remove", str(self.wt1)],
                                 capture_output=True, text=True, timeout=60)
        self.assertNotEqual(removed.returncode, 0, removed.stdout)
        self.assertIn("locked", removed.stderr)
        self.assertTrue(self.registered(self.wt1))
        self.assertTrue((self.wt1 / "a.txt").exists())
        self.remove_tree(self.wt1)
        self.git(self.main, "worktree", "prune")
        self.assertTrue(self.registered(self.wt1))
        self.assertEqual(self.locked(self.wt1), self.own(acquired["lease"]["lease_id"]))

    def test_an_accepted_session_lock_also_keeps_the_worktree(self):
        self.lock(self.wt1, SESSION)
        self.acquire_attested(self.wt1, SESSION)
        removed = subprocess.run(["git", "-C", str(self.main), "worktree", "remove", str(self.wt1)],
                                 capture_output=True, text=True, timeout=60)
        self.assertNotEqual(removed.returncode, 0)
        self.git(self.main, "worktree", "prune")
        self.assertTrue(self.registered(self.wt1))


if __name__ == "__main__":
    unittest.main()
