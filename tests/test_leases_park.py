"""Park a merged worktree when its Checkout lease is returned (checkout leases ticket 05).

The lease tool runs as a subprocess against temporary real Git repositories with real linked worktrees, and only its
JSON result and exit status are asserted, with the fixture of tests/test_leases_tool.py: a base made with mkdtemp
under FEATHER_LINK_TEST_DIR when set, holding main/ with one commit and linked worktrees wt1 and wt2 (on branches wt1
and wt2) beside it, synthetic data only, removed on cleanup. Merges are made with `git merge --no-ff` in the fixture's
own checkouts. A remote default branch is a synthetic `refs/remotes/origin/*` ref with a symbolic
`refs/remotes/origin/HEAD`; no remote is contacted. A held critical section is a synthetic lock file."""
from datetime import timedelta
from pathlib import Path
import subprocess
import unittest

from tests.test_leases_locks import LockBase
from tests.test_leases_tool import CriticalSectionTest


class ParkBase(LockBase):
    def park(self, checkout: Path, lease_id: str, *, continue_in: Path | None = None, expected=0) -> dict:
        return self.lease(self.main, "release", "--checkout", str(checkout), "--lease-id", lease_id, "--park",
                          *(["--continue-in", str(continue_in)] if continue_in is not None else []),
                          expected=expected)

    def head(self, checkout: Path) -> tuple[str, str]:
        """(the symbolic name HEAD gives, "HEAD" when detached; the commit HEAD names)."""
        return (self.git(checkout, "rev-parse", "--abbrev-ref", "HEAD"), self.git(checkout, "rev-parse", "HEAD"))

    def tip(self, branch: str) -> str:
        return self.git(self.main, "rev-parse", f"refs/heads/{branch}")

    def branches(self) -> list[str]:
        return sorted(self.git(self.main, "for-each-ref", "--format=%(refname:short)", "refs/heads/").splitlines())

    def work(self, checkout: Path, name: str):
        (checkout / name).write_bytes(f"{name}\n".encode())
        self.commit(checkout, name)

    def merge(self, into: Path, branch: str):
        self.git(into, "-c", "commit.gpgSign=false", "merge", "--quiet", "--no-ff", "--no-edit", branch)

    def assert_released(self, result: dict, checkout: Path):
        self.assertEqual((result["status"], result["released"]), ("ok", True), result)
        self.assertEqual(self.entry(self.listing(self.main), checkout)["lease"]["state"], "absent")
        self.assertIsNone(self.locked(checkout))

    def assert_not_parked(self, result: dict, condition: str, before: tuple[str, str], checkout: Path) -> str:
        park = result["park"]
        self.assertEqual((park["parked"], park["condition"]), (False, condition), result)
        self.assertTrue(park["reason"], result)
        self.assertEqual(self.head(checkout), before)
        return park["reason"]


class ParkTest(ParkBase):
    def test_a_clean_worktree_merged_into_the_default_branch_is_detached_there_and_released(self):
        self.work(self.wt1, "one.txt")
        self.merge(self.main, "wt1")
        main_tip = self.tip("main")
        self.assertNotEqual(main_tip, self.tip("wt1"))
        branches = self.branches()
        lease_id = self.acquire(self.main, self.wt1)["lease"]["lease_id"]
        parked = self.park(self.wt1, lease_id)
        self.assertEqual(parked["park"], {"parked": True, "branch": "wt1", "detached_at": main_tip,
                                          "contained_in": "refs/heads/main", "target": "default-branch"}, parked)
        self.assertEqual(self.head(self.wt1), ("HEAD", main_tip))
        self.assert_released(parked, self.wt1)
        self.assertEqual(parked["lock"]["removed"], True, parked)
        self.assertEqual(self.branches(), branches)
        self.assertTrue(self.registered(self.wt1))
        self.assertEqual(self.status(self.wt1), "")
        self.git(self.main, "branch", "-d", "wt1")

    def test_a_worktree_merged_into_a_named_continuing_checkout_is_detached_at_that_branch(self):
        # Parallel Claims in wt1 and wt2: wt2's branch is merged into wt1's, and work continues in wt1.
        self.work(self.wt2, "two.txt")
        self.merge(self.wt1, "wt2")
        continuing = self.acquire(self.main, self.wt1)
        lease_id = self.acquire(self.main, self.wt2)["lease"]["lease_id"]
        parked = self.park(self.wt2, lease_id, continue_in=self.wt1)
        self.assertEqual(parked["park"], {"parked": True, "branch": "wt2", "detached_at": self.tip("wt1"),
                                          "contained_in": "refs/heads/wt1", "target": "continuing-checkout"}, parked)
        self.assertEqual(self.head(self.wt2), ("HEAD", self.tip("wt1")))
        self.assert_released(parked, self.wt2)
        kept = self.entry(self.listing(self.main), self.wt1)
        self.assertEqual(kept["lease"]["lease"]["lease_id"], continuing["lease"]["lease_id"], kept)
        self.assertEqual(self.locked(self.wt1), self.own(continuing["lease"]["lease_id"]))
        self.assertEqual(self.head(self.wt1)[0], "wt1")
        self.assertIn("wt2", self.branches())

    def test_the_default_branch_is_preferred_when_it_contains_the_branch(self):
        self.work(self.wt2, "two.txt")
        self.merge(self.main, "wt2")
        self.merge(self.wt1, "wt2")
        lease_id = self.acquire(self.main, self.wt2)["lease"]["lease_id"]
        parked = self.park(self.wt2, lease_id, continue_in=self.wt1)
        self.assertEqual((parked["park"]["target"], parked["park"]["detached_at"]),
                         ("default-branch", self.tip("main")), parked)

    def test_a_named_checkout_whose_branch_does_not_contain_it_is_a_failed_condition(self):
        self.work(self.wt2, "two.txt")
        before = self.head(self.wt2)
        lease_id = self.acquire(self.main, self.wt2)["lease"]["lease_id"]
        result = self.park(self.wt2, lease_id, continue_in=self.wt1)
        reason = self.assert_not_parked(result, "not-contained", before, self.wt2)
        self.assertIn("wt1", reason)
        self.assert_released(result, self.wt2)

    def test_a_branch_neither_contains_is_left_and_the_lease_returned(self):
        self.work(self.wt1, "one.txt")
        before = self.head(self.wt1)
        lease_id = self.acquire(self.main, self.wt1)["lease"]["lease_id"]
        result = self.park(self.wt1, lease_id)
        self.assertIn("refs/heads/main", self.assert_not_parked(result, "not-contained", before, self.wt1))
        self.assert_released(result, self.wt1)

    def test_a_dirty_worktree_is_left_as_it_is_and_the_lease_returned(self):
        for name, change in (("uncommitted", lambda: (self.wt1 / "a.txt").write_bytes(b"changed\n")),
                             ("untracked", lambda: (self.wt1 / "new.txt").write_bytes(b"new\n"))):
            with self.subTest(name):
                change()
                status = self.status(self.wt1)
                before = self.head(self.wt1)
                lease_id = self.acquire(self.main, self.wt1)["lease"]["lease_id"]
                result = self.park(self.wt1, lease_id)
                self.assertIn(name, self.assert_not_parked(result, "dirty", before, self.wt1))
                self.assert_released(result, self.wt1)
                self.assertEqual(self.status(self.wt1), status)
                self.git(self.wt1, "checkout", "--quiet", "--", "a.txt")
                (self.wt1 / "new.txt").unlink(missing_ok=True)

    def test_the_main_worktree_is_never_parked(self):
        before = self.head(self.main)
        lease_id = self.acquire(self.wt1, self.main)["lease"]["lease_id"]
        result = self.park(self.main, lease_id, continue_in=self.wt1)
        self.assert_not_parked(result, "main-worktree", before, self.main)
        self.assertEqual((result["status"], result["released"]), ("ok", True), result)
        self.assertEqual(self.entry(self.listing(self.main), self.main)["lease"]["state"], "absent")

    def test_a_detached_worktree_has_no_branch_to_park(self):
        self.git(self.wt1, "checkout", "--quiet", "--detach")
        before = self.head(self.wt1)
        lease_id = self.acquire(self.main, self.wt1)["lease"]["lease_id"]
        result = self.park(self.wt1, lease_id)
        self.assert_not_parked(result, "no-branch", before, self.wt1)
        self.assert_released(result, self.wt1)

    def test_naming_the_returned_checkout_itself_or_a_detached_one_is_a_failed_condition(self):
        self.work(self.wt2, "two.txt")
        before = self.head(self.wt2)
        lease_id = self.acquire(self.main, self.wt2)["lease"]["lease_id"]
        result = self.park(self.wt2, lease_id, continue_in=self.wt2)
        self.assert_not_parked(result, "continuing-checkout", before, self.wt2)
        self.assert_released(result, self.wt2)
        self.git(self.wt1, "checkout", "--quiet", "--detach")
        lease_id = self.acquire(self.main, self.wt2)["lease"]["lease_id"]
        result = self.park(self.wt2, lease_id, continue_in=self.wt1)
        self.assert_not_parked(result, "continuing-checkout", before, self.wt2)

    def test_parking_never_overwrites_an_ignored_file_and_then_leaves_the_worktree(self):
        # The default branch tracks a file the worktree holds ignored: switching there would overwrite it.
        (self.main / ".gitignore").write_bytes(b"gen.txt\n")
        self.commit(self.main, "ignore gen.txt")
        self.git(self.wt1, "merge", "--quiet", "--ff-only", "main")
        (self.wt1 / "gen.txt").write_bytes(b"local\n")
        (self.main / "gen.txt").write_bytes(b"tracked\n")
        self.git(self.main, "add", "--force", "gen.txt")
        self.git(self.main, "-c", "commit.gpgSign=false", "commit", "--quiet", "--no-verify", "-m", "track gen")
        before = self.head(self.wt1)
        lease_id = self.acquire(self.main, self.wt1)["lease"]["lease_id"]
        result = self.park(self.wt1, lease_id)
        self.assert_not_parked(result, "detach-failed", before, self.wt1)
        self.assertEqual((self.wt1 / "gen.txt").read_bytes(), b"local\n")
        self.assertEqual(self.status(self.wt1), "")
        self.assert_released(result, self.wt1)

    def test_an_ignored_file_that_is_not_overwritten_stays_when_parked(self):
        (self.main / ".gitignore").write_bytes(b"*.log\n")
        self.commit(self.main, "ignore logs")
        self.git(self.wt1, "merge", "--quiet", "--ff-only", "main")
        (self.wt1 / "build.log").write_bytes(b"log\n")
        lease_id = self.acquire(self.main, self.wt1)["lease"]["lease_id"]
        self.assertTrue(self.park(self.wt1, lease_id)["park"]["parked"])
        self.assertEqual((self.wt1 / "build.log").read_bytes(), b"log\n")


class DefaultBranchParkTest(ParkBase):
    def test_parking_is_skipped_when_the_default_branch_is_unknown(self):
        self.git(self.main, "branch", "master")
        before = self.head(self.wt1)
        lease_id = self.acquire(self.main, self.wt1)["lease"]["lease_id"]
        result = self.park(self.wt1, lease_id)
        self.assertIn("default branch", self.assert_not_parked(result, "default-branch-unknown", before, self.wt1))
        self.assert_released(result, self.wt1)

    def test_a_default_branch_only_on_the_remote_is_a_failed_condition(self):
        self.git(self.main, "update-ref", "refs/remotes/origin/trunk", "HEAD")
        self.git(self.main, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/trunk")
        before = self.head(self.wt1)
        lease_id = self.acquire(self.main, self.wt1)["lease"]["lease_id"]
        result = self.park(self.wt1, lease_id)
        reason = self.assert_not_parked(result, "local-default-branch", before, self.wt1)
        self.assertIn("may need creating or updating", reason)
        self.assert_released(result, self.wt1)

    def test_a_branch_contained_only_in_the_remote_default_branch_is_a_failed_condition(self):
        self.work(self.wt1, "one.txt")
        self.git(self.main, "update-ref", "refs/remotes/origin/main", "wt1")
        self.git(self.main, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
        before = self.head(self.wt1)
        lease_id = self.acquire(self.main, self.wt1)["lease"]["lease_id"]
        result = self.park(self.wt1, lease_id)
        reason = self.assert_not_parked(result, "local-default-branch", before, self.wt1)
        self.assertIn("may need creating or updating", reason)
        self.assert_released(result, self.wt1)

    def test_a_named_checkout_still_parks_when_the_default_branch_is_only_on_the_remote(self):
        self.git(self.main, "branch", "-m", "main", "local-work")
        self.git(self.main, "update-ref", "refs/remotes/origin/trunk", "HEAD")
        self.git(self.main, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/trunk")
        self.work(self.wt2, "two.txt")
        self.merge(self.wt1, "wt2")
        lease_id = self.acquire(self.main, self.wt2)["lease"]["lease_id"]
        parked = self.park(self.wt2, lease_id, continue_in=self.wt1)
        self.assertEqual((parked["park"]["parked"], parked["park"]["target"]), (True, "continuing-checkout"), parked)


class ParkLeaseTest(ParkBase):
    def test_parking_with_another_lease_id_changes_nothing(self):
        self.work(self.wt1, "one.txt")
        self.merge(self.main, "wt1")
        before = self.head(self.wt1)
        acquired = self.acquire(self.main, self.wt1)
        result = self.park(self.wt1, "0" * 32)
        self.assertEqual((result["status"], result["released"]), ("changed-hands", False), result)
        self.assertEqual((result["park"]["parked"], result["park"]["condition"]), (False, "not-released"), result)
        self.assertEqual(self.head(self.wt1), before)
        self.assertEqual(self.locked(self.wt1), self.own(acquired["lease"]["lease_id"]))
        self.assertEqual(self.entry(self.listing(self.main), self.wt1)["lease"]["lease"], acquired["lease"])

    def test_a_held_critical_section_is_reported_at_once_and_nothing_is_parked(self):
        self.work(self.wt1, "one.txt")
        self.merge(self.main, "wt1")
        before = self.head(self.wt1)
        acquired = self.acquire(self.main, self.wt1)
        data = CriticalSectionTest.write_lock(self, "wt1", timedelta(seconds=30))
        result = self.park(self.wt1, acquired["lease"]["lease_id"])
        self.assertEqual((result["status"], result["released"], result["park"]["parked"]), ("busy", False, False),
                         result)
        self.assertEqual(self.head(self.wt1), before)
        self.assertEqual((self.leases / "wt1.lock").read_bytes(), data)
        self.assertEqual(self.locked(self.wt1), self.own(acquired["lease"]["lease_id"]))

    def test_continue_in_needs_park_and_a_registered_checkout(self):
        lease_id = self.acquire(self.main, self.wt1)["lease"]["lease_id"]
        refused = self.lease(self.main, "release", "--checkout", str(self.wt1), "--lease-id", lease_id,
                             "--continue-in", str(self.wt2), expected=2)
        self.assertEqual(refused["status"], "error", refused)
        refused = self.park(self.wt1, lease_id, continue_in=self.outside, expected=2)
        self.assertEqual(refused["code"], "not-a-checkout", refused)
        self.assertEqual(self.entry(self.listing(self.main), self.wt1)["lease"]["state"], "held")

    def test_release_without_park_never_parks(self):
        self.work(self.wt1, "one.txt")
        self.merge(self.main, "wt1")
        lease_id = self.acquire(self.main, self.wt1)["lease"]["lease_id"]
        released = self.release(self.main, self.wt1, lease_id)
        self.assertNotIn("park", released)
        self.assertEqual(self.head(self.wt1)[0], "wt1")


if __name__ == "__main__":
    unittest.main()
