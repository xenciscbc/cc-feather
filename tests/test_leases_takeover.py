"""Renew a Checkout lease and take one over (checkout leases ticket 03).

The lease tool runs as a subprocess against temporary real Git repositories with real linked worktrees, and only its
JSON result and exit status are asserted, with the fixture of tests/test_leases_tool.py and the lock helpers of
tests/test_leases_locks.py. Locks are set and read with `git worktree lock --reason` and `git worktree list
--porcelain -z`, using Claude Code's observed reason formats; Claude Code itself is not driven. Old activity times and
critical-section locks left by a crashed operation are synthetic edits and files written by the tests. The
concurrent-reader case, on Windows only, holds a lease open from the test process for a fraction of a second.
Synthetic data only, removed on cleanup."""
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import subprocess
import time
import unittest

from tests.test_leases_locks import AGENT, SESSION, CriticalSectionLock, LockBase
from tests.test_leases_tool import HOLD, MAIN_KEY, TIMEOUT


class TakeOverBase(LockBase):
    def renew(self, checkout: Path, lease_id: str, *extra: str, expected=0) -> dict:
        return self.lease(self.main, "renew", "--checkout", str(checkout), "--lease-id", lease_id, *extra,
                          expected=expected)

    def take_over(self, checkout: Path, version: str, *, session="session-b", purpose="take over", expected=0,
                  project: Path | None = None) -> dict:
        return self.lease(project or self.main, "take-over", "--checkout", str(checkout), "--version", version,
                          "--session", session, "--purpose", purpose, expected=expected)

    def lease_file(self, checkout: Path) -> Path:
        return self.leases / ("wt1.json" if checkout == self.wt1 else
                              "wt2.json" if checkout == self.wt2 else f"{MAIN_KEY}.json")

    def age_lease(self, checkout: Path, delta: timedelta) -> dict:
        """Move the lease's start and last reported activity back by delta, as an old lease has them."""
        path = self.lease_file(checkout)
        value = json.loads(path.read_text(encoding="utf-8"))
        for field in ("started", "last_activity"):
            value[field] = (datetime.fromisoformat(value[field]) - delta).isoformat(timespec="seconds")
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        return value

    def shown(self, checkout: Path) -> dict:
        """The lease state the listing shows the user for checkout."""
        state = self.entry(self.listing(self.main), checkout)["lease"]
        self.assertEqual(state["state"], "held", state)
        return state


class RenewTest(TakeOverBase):
    def test_renew_with_the_holders_lease_id_updates_the_last_reported_activity(self):
        acquired = self.acquire(self.main, self.wt1, purpose="ticket 01")
        old = self.age_lease(self.wt1, timedelta(hours=2))
        before = datetime.now().astimezone()
        renewed = self.renew(self.wt1, acquired["lease"]["lease_id"])
        self.assertEqual((renewed["status"], renewed["renewed"]), ("ok", True), renewed)
        lease = renewed["lease"]
        self.assertGreaterEqual(datetime.fromisoformat(lease["last_activity"]), before - timedelta(seconds=5))
        self.assertEqual(lease["started"], old["started"])
        for field in ("lease_id", "session", "purpose", "host", "runtime", "checkout"):
            self.assertEqual(lease[field], acquired["lease"][field], field)
        shown = self.shown(self.wt1)
        self.assertEqual((shown["lease"], shown["version"]), (lease, renewed["version"]))
        self.assertLess(shown["activity_age_seconds"], 3600)
        self.assertGreaterEqual(shown["age_seconds"], 2 * 3600 - 5)
        self.assertEqual(self.locked(self.wt1), self.own(lease["lease_id"]))

    def test_renew_changes_the_purpose_when_given(self):
        acquired = self.acquire(self.main, self.wt1, purpose="ticket 01")
        renewed = self.renew(self.wt1, acquired["lease"]["lease_id"], "--purpose", "ticket 02")
        self.assertEqual((renewed["status"], renewed["lease"]["purpose"]), ("ok", "ticket 02"), renewed)
        self.assertEqual(self.shown(self.wt1)["lease"]["purpose"], "ticket 02")
        main = self.acquire(self.wt1, self.main)
        renewed = self.renew(self.main, main["lease"]["lease_id"], "--purpose", "merge")
        self.assertEqual((renewed["status"], renewed["lease"]["purpose"]), ("ok", "merge"), renewed)
        self.assertEqual(renewed["lock"]["state"], "not-lockable", renewed)

    def test_renew_with_another_lease_id_reports_changed_hands_and_changes_nothing(self):
        acquired = self.acquire(self.main, self.wt1)
        data = self.lease_file(self.wt1).read_bytes()
        refused = self.renew(self.wt1, "0" * 32, "--purpose", "stolen")
        self.assertEqual((refused["status"], refused["renewed"]), ("changed-hands", False), refused)
        self.assertEqual(refused["lease"], acquired["lease"])
        self.assertEqual(self.lease_file(self.wt1).read_bytes(), data)
        self.assertEqual(self.locked(self.wt1), self.own(acquired["lease"]["lease_id"]))

    def test_renew_never_acquires(self):
        refused = self.renew(self.wt1, "0" * 32)
        self.assertEqual((refused["status"], refused["renewed"], refused["lease"]), ("changed-hands", False, None),
                         refused)
        acquired = self.acquire(self.main, self.wt1)
        self.release(self.main, self.wt1, acquired["lease"]["lease_id"])
        again = self.renew(self.wt1, acquired["lease"]["lease_id"])
        self.assertEqual((again["status"], again["lease"]), ("changed-hands", None), again)
        self.assertFalse(self.lease_file(self.wt1).exists())
        self.assertIsNone(self.locked(self.wt1))
        self.assertEqual(self.entry(self.listing(self.main), self.wt1)["lease"]["state"], "absent")

    def test_renew_meets_a_held_critical_section_and_changes_nothing(self):
        acquired = self.acquire(self.main, self.wt1)
        data = self.lease_file(self.wt1).read_bytes()
        section = CriticalSectionLock(self.leases / "wt1.lock")
        busy = self.renew(self.wt1, acquired["lease"]["lease_id"], "--purpose", "later")
        self.assertEqual((busy["status"], busy["renewed"]), ("busy", False), busy)
        self.assertEqual(busy["critical_section"]["holder"]["operation"], "acquire", busy)
        self.assertEqual(self.lease_file(self.wt1).read_bytes(), data)
        self.assertEqual(section.read(), section.data)

    def test_an_unreadable_lease_is_unknown_and_not_renewed(self):
        self.leases.mkdir(parents=True)
        (self.leases / ".gitignore").write_text("*\n", encoding="utf-8")
        self.lease_file(self.wt1).write_text("{not json", encoding="utf-8")
        unknown = self.renew(self.wt1, "0" * 32)
        self.assertEqual((unknown["status"], unknown["renewed"]), ("unknown", False), unknown)
        self.assertEqual(self.lease_file(self.wt1).read_text(encoding="utf-8"), "{not json")

    def test_an_empty_purpose_is_an_input_error(self):
        acquired = self.acquire(self.main, self.wt1)
        refused = self.renew(self.wt1, acquired["lease"]["lease_id"], "--purpose", " ", expected=2)
        self.assertEqual((refused["status"], refused["code"]), ("error", "input"), refused)

    @unittest.skipUnless(os.name == "nt", "only Windows refuses to replace a file another process holds open")
    def test_a_concurrent_reader_delays_a_renew_but_does_not_fail_it(self):
        acquired = self.acquire(self.main, self.wt1)
        lock = self.leases / "wt1.lock"
        reader = open(self.lease_file(self.wt1), "rb")
        process = subprocess.Popen(self.command(self.main, "renew", "--checkout", str(self.wt1), "--lease-id",
                                                acquired["lease"]["lease_id"], "--purpose", "while read"),
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
        try:
            deadline = time.monotonic() + TIMEOUT / 2
            while not lock.exists() and process.poll() is None and time.monotonic() < deadline:
                pass
            time.sleep(HOLD)
        finally:
            reader.close()
        out, err = process.communicate(timeout=TIMEOUT)
        self.assertEqual(process.returncode, 0, out + err)
        renewed = json.loads(out)
        self.assertEqual((renewed["status"], renewed["lease"]["purpose"]), ("ok", "while read"), renewed)
        self.assertFalse(lock.exists())
        self.assertEqual(self.shown(self.wt1)["lease"]["purpose"], "while read")
        self.assertEqual([path.name for path in self.leases.iterdir() if path.suffix == ".tmp"], [])


class TakeOverTest(TakeOverBase):
    def test_a_takeover_with_the_shown_version_writes_a_new_lease_and_moves_the_lock(self):
        acquired = self.acquire(self.main, self.wt1, session="alpha", purpose="old work")
        self.age_lease(self.wt1, timedelta(days=3))
        shown = self.shown(self.wt1)
        before = datetime.now().astimezone()
        taken = self.take_over(self.wt1, shown["version"], session="beta", purpose="new work", project=self.wt2)
        self.assertEqual((taken["status"], taken["taken_over"]), ("ok", True), taken)
        lease = taken["lease"]
        self.assertRegex(lease["lease_id"], r"^[0-9a-f]{32}$")
        self.assertNotEqual(lease["lease_id"], acquired["lease"]["lease_id"])
        self.assertEqual((lease["session"], lease["purpose"], lease["checkout"]["key"]), ("beta", "new work", "wt1"))
        for field in ("started", "last_activity"):
            self.assertGreaterEqual(datetime.fromisoformat(lease[field]), before - timedelta(seconds=5))
        self.assertEqual(taken["previous"], shown["lease"])
        old, new = self.own(acquired["lease"]["lease_id"]), self.own(lease["lease_id"])
        self.assertEqual(taken["lock"], {"state": "locked", "reason": new, "pid": None, "holder": "lease",
                                         "replaced": old})
        self.assertEqual(self.locked(self.wt1), new)
        listed = self.entry(self.listing(self.main), self.wt1)
        self.assertEqual((listed["lease"]["lease"], listed["lease"]["version"]), (lease, taken["version"]))
        self.assertEqual(listed["lock"]["holder"], "lease", listed)

    def test_the_version_a_refused_acquire_returns_takes_the_lease_over(self):
        self.acquire(self.main, self.wt1, session="alpha")
        refused = self.acquire(self.main, self.wt1, session="beta")
        self.assertEqual(refused["status"], "held", refused)
        taken = self.take_over(self.wt1, refused["version"], session="beta")
        self.assertEqual((taken["status"], taken["lease"]["session"]), ("ok", "beta"), taken)
        self.assertEqual(self.locked(self.wt1), self.own(taken["lease"]["lease_id"]))

    def test_a_takeover_with_a_stale_version_refuses_and_returns_the_current_lease(self):
        acquired = self.acquire(self.main, self.wt1)
        stale = self.shown(self.wt1)["version"]
        renewed = self.renew(self.wt1, acquired["lease"]["lease_id"], "--purpose", "still here")
        data = self.lease_file(self.wt1).read_bytes()
        refused = self.take_over(self.wt1, stale)
        self.assertEqual((refused["status"], refused["taken_over"]), ("changed", False), refused)
        self.assertEqual((refused["lease"], refused["version"]), (renewed["lease"], renewed["version"]))
        self.assertIn("activity_age_seconds", refused)
        self.assertEqual(self.lease_file(self.wt1).read_bytes(), data)
        self.assertEqual(self.locked(self.wt1), self.own(acquired["lease"]["lease_id"]))

    def test_a_takeover_of_an_absent_lease_refuses_and_acquires_nothing(self):
        acquired = self.acquire(self.main, self.wt1)
        version = self.shown(self.wt1)["version"]
        self.release(self.main, self.wt1, acquired["lease"]["lease_id"])
        refused = self.take_over(self.wt1, version)
        self.assertEqual((refused["status"], refused["taken_over"], refused["lease"]), ("changed", False, None),
                         refused)
        self.assertFalse(self.lease_file(self.wt1).exists())
        self.assertIsNone(self.locked(self.wt1))

    def test_an_accepted_session_lock_stays_and_the_result_says_so(self):
        self.lock(self.wt1, SESSION)
        acquired = self.acquire_attested(self.wt1, SESSION)
        taken = self.take_over(self.wt1, acquired["version"])
        self.assertEqual(taken["status"], "ok", taken)
        self.assertNotIn("accepted_lock", taken["lease"])
        lock = taken["lock"]
        self.assertEqual((lock["state"], lock["reason"], lock["pid"], lock["holder"]),
                         ("locked", SESSION, 4242, "other"), lock)
        self.assertEqual((lock["kept"], lock["previous_holder"]), (True, "accepted-session"), lock)
        self.assertIn("stays", lock["message"])
        self.assertEqual(self.locked(self.wt1), SESSION)
        self.assertEqual(self.entry(self.listing(self.main), self.wt1)["lock"]["holder"], "other")
        released = self.release(self.main, self.wt1, taken["lease"]["lease_id"])
        self.assertEqual((released["status"], released["lock"]["removed"]), ("ok", False), released)
        self.assertEqual(self.locked(self.wt1), SESSION)

    def test_every_other_lock_stays_and_the_result_says_so(self):
        for reason in (AGENT, self.own("f" * 32), "in use by backup-tool"):
            with self.subTest(reason=reason):
                acquired = self.acquire(self.main, self.wt1)
                self.unlock(self.wt1)
                self.lock(self.wt1, reason)
                taken = self.take_over(self.wt1, acquired["version"])
                self.assertEqual(taken["status"], "ok", taken)
                self.assertEqual((taken["lock"]["reason"], taken["lock"]["kept"]), (reason, True), taken)
                self.assertNotIn("replaced", taken["lock"])
                self.assertEqual(self.locked(self.wt1), reason)
                self.release(self.main, self.wt1, taken["lease"]["lease_id"])
                self.assertEqual(self.locked(self.wt1), reason)
                self.unlock(self.wt1)

    def test_a_takeover_of_a_lockless_lease_locks_the_worktree_for_the_new_lease(self):
        acquired = self.acquire(self.main, self.wt1)
        self.unlock(self.wt1)
        taken = self.take_over(self.wt1, acquired["version"])
        self.assertEqual(taken["status"], "ok", taken)
        new = self.own(taken["lease"]["lease_id"])
        self.assertEqual(taken["lock"], {"state": "locked", "reason": new, "pid": None, "holder": "lease",
                                         "relocked": True})
        self.assertEqual(self.locked(self.wt1), new)

    def test_the_main_worktree_is_taken_over_without_a_lock(self):
        acquired = self.acquire(self.wt1, self.main)
        taken = self.take_over(self.main, acquired["version"], project=self.wt2)
        self.assertEqual((taken["status"], taken["lease"]["checkout"]["key"]), ("ok", MAIN_KEY), taken)
        self.assertEqual(taken["lock"]["state"], "not-lockable", taken)
        self.assertIsNone(self.locked(self.main))

    def test_a_worktree_whose_directory_is_missing_is_not_taken_over(self):
        acquired = self.acquire(self.main, self.wt1)
        data = self.lease_file(self.wt1).read_bytes()
        self.remove_tree(self.wt1)
        refused = self.take_over(self.wt1, acquired["version"])
        self.assertEqual((refused["status"], refused["code"], refused["taken_over"]),
                         ("refused", "directory-missing", False), refused)
        self.assertEqual(self.lease_file(self.wt1).read_bytes(), data)
        self.assertEqual(self.locked(self.wt1), self.own(acquired["lease"]["lease_id"]))

    def test_a_takeover_meets_a_held_critical_section_and_changes_nothing(self):
        acquired = self.acquire(self.main, self.wt1)
        data = self.lease_file(self.wt1).read_bytes()
        section = CriticalSectionLock(self.leases / "wt1.lock")
        busy = self.take_over(self.wt1, acquired["version"])
        self.assertEqual((busy["status"], busy["taken_over"]), ("busy", False), busy)
        self.assertEqual(self.lease_file(self.wt1).read_bytes(), data)
        self.assertEqual(self.locked(self.wt1), self.own(acquired["lease"]["lease_id"]))
        self.assertEqual(section.read(), section.data)

    def test_a_takeover_needs_a_version_and_valid_input(self):
        acquired = self.acquire(self.main, self.wt1)
        missing = self.lease(self.main, "take-over", "--checkout", str(self.wt1), "--session", "s", "--purpose", "p",
                             expected=2)
        self.assertEqual((missing["status"], missing["code"]), ("error", "usage"), missing)
        for version, session, purpose in (("not-a-version", "s", "p"), (acquired["version"], " ", "p"),
                                          (acquired["version"], "s", "")):
            with self.subTest(version=version, session=session, purpose=purpose):
                refused = self.take_over(self.wt1, version, session=session, purpose=purpose, expected=2)
                self.assertEqual((refused["status"], refused["code"]), ("error", "input"), refused)
        self.assertEqual(self.shown(self.wt1)["lease"], acquired["lease"])


class OldHolderTest(TakeOverBase):
    def test_after_a_takeover_the_old_holder_finds_the_lease_changed_hands(self):
        old = self.acquire(self.main, self.wt1, session="alpha")
        taken = self.take_over(self.wt1, old["version"], session="beta")
        new_reason = self.own(taken["lease"]["lease_id"])
        data = self.lease_file(self.wt1).read_bytes()

        renewed = self.renew(self.wt1, old["lease"]["lease_id"], "--purpose", "old work")
        self.assertEqual((renewed["status"], renewed["renewed"]), ("changed-hands", False), renewed)
        self.assertEqual(renewed["lease"], taken["lease"])
        released = self.release(self.main, self.wt1, old["lease"]["lease_id"])
        self.assertEqual((released["status"], released["released"]), ("changed-hands", False), released)
        again = self.take_over(self.wt1, old["version"], session="alpha")
        self.assertEqual((again["status"], again["lease"]), ("changed", taken["lease"]), again)
        self.assertEqual(self.lease_file(self.wt1).read_bytes(), data)
        self.assertEqual(self.locked(self.wt1), new_reason)

        renewed = self.renew(self.wt1, taken["lease"]["lease_id"])
        self.assertEqual(renewed["status"], "ok", renewed)
        released = self.release(self.main, self.wt1, taken["lease"]["lease_id"])
        self.assertEqual(released["lock"], {"removed": True, "reason": new_reason}, released)
        self.assertIsNone(self.locked(self.wt1))


class NoReclaimTest(TakeOverBase):
    def test_no_age_reclaims_a_lease_and_nothing_takes_one_over_automatically(self):
        acquired = self.acquire(self.main, self.wt1, session="alpha")
        old = self.age_lease(self.wt1, timedelta(days=400))
        blocked = self.acquire(self.main, self.wt1, session="beta")
        self.assertEqual((blocked["status"], blocked["acquired"], blocked["lease"]), ("held", False, old), blocked)
        self.assertGreaterEqual(blocked["activity_age_seconds"], 399 * 86400)
        listed = self.shown(self.wt1)
        self.assertEqual(listed["lease"], old)
        renewed = self.renew(self.wt1, "0" * 32)
        self.assertEqual(renewed["status"], "changed-hands", renewed)
        self.assertEqual(self.shown(self.wt1)["lease"], old)
        self.assertEqual(self.locked(self.wt1), self.own(acquired["lease"]["lease_id"]))


if __name__ == "__main__":
    unittest.main()
