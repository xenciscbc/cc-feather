"""Left-behind work in the Checkout lease listing, and orphan leases (checkout leases ticket 04).

The lease tool runs as a subprocess against temporary real Git repositories with real linked worktrees, and only its
JSON result and exit status are asserted, with the fixture of tests/test_leases_tool.py: a base made with mkdtemp
under FEATHER_LINK_TEST_DIR when set, holding main/ with one commit and linked worktrees wt1 and wt2 beside it,
synthetic data only, removed on cleanup. Handoff records are written with the handoff tool itself, or as synthetic
files where a record must be unreadable. A remote default branch is a synthetic `refs/remotes/origin/*` ref with a
symbolic `refs/remotes/origin/HEAD`; no remote is contacted. Orphan leases come from `git worktree remove --force` and
`git worktree prune` after the lease's own lock is removed; a held critical section is a synthetic lock file.

A failed enumeration of the other checkouts (`other_stores_issues`) and an uncertain root cannot be produced from a
real repository the lease tool lists, since the lease tool itself refuses a root it cannot establish: those cases
feed such a handoff `list` result to the pure judging function `leftover.judge_records` (JudgeRecordsTest)."""
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import unittest

from tests.test_handoff_shared_store import FIELDS, MARKER, ROOT, remove_base
from tests.test_leases_tool import HANDOFF_TOOL, MAIN_KEY, TIMEOUT, LeaseBase

sys.path.insert(0, str(ROOT / "skills/leases/scripts"))
from feather_leases import leftover  # noqa: E402
from feather_leases.checkouts import Checkout  # noqa: E402

WINDOWS = os.name == "nt"


class ListingBase(LeaseBase):
    def handoff(self, project: Path, *args, payload=None, exact=False) -> dict:
        result = subprocess.run([sys.executable, "-B", str(HANDOFF_TOOL), "--project", str(project),
                                 *(["--exact-root"] if exact else []), *args],
                                input=json.dumps(payload, ensure_ascii=False) if payload is not None else None,
                                capture_output=True, text=True, encoding="utf-8", timeout=TIMEOUT)
        return json.loads(result.stdout)

    def record(self, project: Path, work: str, environment: str) -> dict:
        created = self.handoff(project, "create", "--work", work,
                               payload={"title": work, "fields": {**FIELDS, "environment": environment}})
        self.assertEqual(created["status"], "ok", created)
        return created

    def records(self, listed: dict, checkout: Path) -> list[str]:
        part = self.entry(listed, checkout)["handoff_records"]
        self.assertEqual(part["state"], "known", part)
        return sorted(record["work"] for record in part["records"])

    def unknown(self, listed: dict, checkout: Path, part: str) -> str:
        value = self.entry(listed, checkout)[part]
        self.assertEqual(value["state"], "unknown", value)
        self.assertTrue(value["reason"], value)
        return value["reason"]

    def remove_worktree(self, checkout: Path):
        self.git(self.main, "worktree", "unlock", str(checkout))
        self.git(self.main, "worktree", "remove", "--force", str(checkout))


class ChangesTest(ListingBase):
    def test_uncommitted_untracked_and_unmerged_work_is_listed(self):
        (self.wt1 / "a.txt").write_bytes(b"changed\n")
        (self.wt1 / "new.txt").write_bytes(b"new\n")
        (self.wt1 / "dir").mkdir()
        (self.wt1 / "dir" / "deep.txt").write_bytes(b"deep\n")
        (self.wt2 / "b.txt").write_bytes(b"b\n")
        self.commit(self.wt2, "unmerged")
        listed = self.listing(self.main)
        first = self.entry(listed, self.wt1)
        self.assertEqual(first["changes"], {"state": "known", "uncommitted": [{"status": " M", "path": "a.txt"}],
                                            "untracked": ["dir/deep.txt", "new.txt"], "uncommitted_count": 1,
                                            "untracked_count": 2, "truncated": False}, first)
        self.assertEqual((first["commits"]["ahead"], first["commits"]["behind"]), (0, 0), first)
        second = self.entry(listed, self.wt2)
        self.assertEqual((second["changes"]["uncommitted"], second["changes"]["untracked"]), ([], []), second)
        self.assertEqual(second["commits"], {"state": "known", "compared_with": "refs/heads/main", "kind": "local",
                                             "ahead": 1, "behind": 0}, second)
        main = self.entry(listed, self.main)
        self.assertEqual((main["changes"]["state"], main["changes"]["uncommitted"]), ("known", []), main)
        self.assertTrue(listed["complete"], listed)

    def test_a_rename_in_the_worktree_is_one_change(self):
        # Porcelain v1 reports a worktree rename in its Y column (an intent-to-add target), followed by the source.
        (self.wt1 / "a.txt").rename(self.wt1 / "renamed.txt")
        self.git(self.wt1, "add", "-N", "renamed.txt")
        changes = self.entry(self.listing(self.main), self.wt1)["changes"]
        self.assertEqual((changes["uncommitted"], changes["uncommitted_count"]),
                         ([{"status": " R", "path": "renamed.txt"}], 1), changes)

    def test_the_leases_themselves_are_no_change(self):
        self.acquire(self.wt1, self.main)
        self.acquire(self.wt1, self.wt1)
        listed = self.listing(self.wt1)
        for checkout in (self.main, self.wt1):
            changes = self.entry(listed, checkout)["changes"]
            self.assertEqual((changes["uncommitted"], changes["untracked"]), ([], []), changes)

    def test_a_missing_directory_makes_its_changes_unknown(self):
        remove_base(self.wt2)
        listed = self.listing(self.main)
        self.assertFalse(self.entry(listed, self.wt2)["directory_exists"])
        self.unknown(listed, self.wt2, "changes")
        self.unknown(listed, self.wt2, "handoff_records")
        self.assertEqual(self.entry(listed, self.wt1)["changes"]["state"], "known", listed)
        self.assertFalse(listed["complete"], listed)

    def test_a_prunable_worktree_has_unknown_changes(self):
        (self.wt1 / ".git").unlink()
        listed = self.listing(self.main)
        self.assertTrue(self.entry(listed, self.wt1)["prunable"], listed)
        self.unknown(listed, self.wt1, "changes")


class DefaultBranchTest(ListingBase):
    def test_without_a_remote_the_lone_main_branch_is_the_default(self):
        listed = self.listing(self.wt1)
        self.assertEqual(listed["default_branch"], {"state": "known", "name": "main", "source": "main-or-master",
                                                    "local": "refs/heads/main", "remote": None}, listed)
        self.assertEqual(self.entry(listed, self.wt1)["commits"]["compared_with"], "refs/heads/main")

    def test_a_lone_master_branch_is_the_default(self):
        self.git(self.main, "branch", "-m", "main", "master")
        listed = self.listing(self.wt1)
        self.assertEqual((listed["default_branch"]["name"], listed["default_branch"]["local"]),
                         ("master", "refs/heads/master"), listed)

    def test_origin_head_names_the_default_branch_and_the_remote_one_is_used_without_a_local_one(self):
        (self.wt1 / "c.txt").write_bytes(b"c\n")
        self.commit(self.wt1, "ahead")
        self.git(self.main, "update-ref", "refs/remotes/origin/trunk", "HEAD")
        self.git(self.main, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/trunk")
        listed = self.listing(self.main)
        self.assertEqual(listed["default_branch"], {"state": "known", "name": "trunk", "source": "origin/HEAD",
                                                    "local": None, "remote": "refs/remotes/origin/trunk"}, listed)
        self.assertEqual(self.entry(listed, self.wt1)["commits"],
                         {"state": "known", "compared_with": "refs/remotes/origin/trunk", "kind": "remote",
                          "ahead": 1, "behind": 0})
        self.git(self.main, "branch", "trunk", "wt1")
        listed = self.listing(self.main)
        self.assertEqual(listed["default_branch"]["local"], "refs/heads/trunk", listed)
        self.assertEqual(self.entry(listed, self.wt1)["commits"],
                         {"state": "known", "compared_with": "refs/heads/trunk", "kind": "local", "ahead": 0,
                          "behind": 0})
        self.assertEqual(self.entry(listed, self.main)["commits"]["behind"], 1, listed)

    def test_the_default_branch_cannot_be_determined_with_both_main_and_master(self):
        self.git(self.main, "branch", "master")
        listed = self.listing(self.main)
        self.assertEqual(listed["default_branch"]["state"], "unknown", listed)
        self.assertTrue(listed["default_branch"]["reason"])
        for checkout in (self.main, self.wt1, self.wt2):
            self.assertIn("default branch", self.unknown(listed, checkout, "commits"))
        self.assertFalse(listed["complete"], listed)

    def test_the_default_branch_cannot_be_determined_without_main_or_master(self):
        self.git(self.main, "branch", "-m", "main", "trunk")
        listed = self.listing(self.main)
        self.assertEqual(listed["default_branch"]["state"], "unknown", listed)
        self.unknown(listed, self.wt1, "commits")


class HandoffRecordsTest(ListingBase):
    def test_a_record_naming_a_checkout_is_listed_for_it_alone(self):
        self.record(self.main, "one.md", f"worktree {self.wt1}；Windows")
        self.record(self.main, "two.md", f"working in {self.wt2}")
        self.record(self.main, "here.md", f"{self.main}")
        self.record(self.main, "none.md", f"{self.wt1}0 and {self.base / 'elsewhere'}")
        if WINDOWS:
            self.record(self.main, "case.md", str(self.wt1).upper().replace("\\", "/") + "/sub")
        listed = self.listing(self.wt2)
        self.assertEqual(self.records(listed, self.wt1), ["case.md", "one.md"] if WINDOWS else ["one.md"])
        self.assertEqual(self.records(listed, self.wt2), ["two.md"])
        self.assertEqual(self.records(listed, self.main), ["here.md"])
        record = next(item for item in self.entry(listed, self.wt2)["handoff_records"]["records"])
        self.assertEqual((record["title"], record["status"]), ("two.md", "進行中"), record)
        self.assertEqual(os.path.normcase(record["store"]), os.path.normcase(str(self.main / ".feather/handoffs")))

    def test_a_record_naming_a_linked_worktree_inside_the_main_worktree_does_not_name_the_main_worktree(self):
        inside = self.main / ".claude" / "worktrees" / "agent"
        self.git(self.main, "worktree", "add", "--quiet", "-b", "agent", str(inside))
        self.record(self.main, "agent.md", f"in {inside}")
        listed = self.listing(self.main)
        self.assertEqual(self.records(listed, inside), ["agent.md"])
        self.assertEqual(self.records(listed, self.main), [])

    def test_an_unreadable_main_store_makes_the_part_unknown_for_every_checkout(self):
        self.record(self.main, "one.md", f"{self.wt1}")
        (self.main / ".feather" / "handoffs" / "bad.md").write_bytes(b"# bad\n\xff\xfe\n")
        listed = self.listing(self.main)
        for checkout in (self.main, self.wt1, self.wt2):
            self.unknown(listed, checkout, "handoff_records")
        self.assertFalse(listed["complete"], listed)

    def test_a_tracked_linked_worktrees_record_naming_itself_is_listed_the_same_from_every_checkout(self):
        (self.wt1 / ".gitignore").write_text(MARKER + "\n", encoding="utf-8")
        created = self.record(self.wt1, "own.md", f"{self.wt1}")
        self.assertEqual(created["root"]["tracking"], "tracked", created)
        self.assertTrue((self.wt1 / ".feather" / "handoffs" / "own.md").is_file())
        views = [self.listing(project) for project in (self.main, self.wt1, self.wt2)]
        for view in views:
            with self.subTest(project=view["project"]):
                self.assertEqual(self.records(view, self.wt1), ["own.md"])
                self.assertEqual(self.records(view, self.main), [])
                stores = [record["store"] for record in self.entry(view, self.wt1)["handoff_records"]["records"]]
                self.assertEqual([os.path.normcase(store) for store in stores],
                                 [os.path.normcase(str(self.wt1 / ".feather" / "handoffs"))])
        self.assertEqual(views[0]["checkouts"], views[1]["checkouts"])

    def test_a_deleted_worktree_leaves_the_main_stores_records_for_other_checkouts(self):
        self.record(self.main, "one.md", f"{self.wt1}")
        self.record(self.main, "two.md", f"{self.wt2}")
        remove_base(self.wt2)
        listed = self.listing(self.main)
        self.assertEqual(self.records(listed, self.wt1), ["one.md"])
        self.assertEqual(self.records(listed, self.main), [])
        self.assertIn("missing", self.unknown(listed, self.wt2, "handoff_records"))

    def test_an_unreadable_other_store_makes_only_that_checkout_unknown(self):
        self.record(self.main, "one.md", f"{self.wt2}")
        self.record(self.main, "main.md", f"{self.main}")
        (self.wt1 / ".gitignore").write_text(MARKER + "\n", encoding="utf-8")
        self.record(self.wt1, "own.md", f"{self.wt1}")
        (self.wt1 / ".feather" / "handoffs" / "bad.md").write_bytes(b"# bad\n\xff\xfe\n")
        listed = self.listing(self.wt2)
        self.unknown(listed, self.wt1, "handoff_records")
        self.assertEqual(self.records(listed, self.wt2), ["one.md"])
        self.assertEqual(self.records(listed, self.main), ["main.md"])


class OrphanTest(ListingBase):
    def test_listing_removes_a_lease_whose_checkout_git_no_longer_registers_and_reports_it(self):
        acquired = self.acquire(self.main, self.wt2)
        kept = self.acquire(self.main, self.wt1)
        self.remove_worktree(self.wt2)
        listed = self.listing(self.main)
        self.assertEqual(listed["orphans"]["state"], "known", listed)
        self.assertEqual([(item["key"], item["removed"], item["lease"]) for item in listed["orphans"]["leases"]],
                         [("wt2", True, acquired["lease"])], listed)
        self.assertFalse((self.leases / "wt2.json").exists())
        self.assertFalse((self.leases / "wt2.lock").exists())
        self.assertEqual(self.entry(listed, self.wt1)["lease"]["lease"], kept["lease"])
        self.assertEqual(len(listed["checkouts"]), 2, listed)
        again = self.listing(self.main)
        self.assertEqual(again["orphans"], {"state": "known", "leases": []}, again)

    def test_acquire_removes_an_orphan_lease_and_names_it(self):
        acquired = self.acquire(self.main, self.wt2)
        self.remove_worktree(self.wt2)
        self.git(self.main, "worktree", "prune")
        taken = self.acquire(self.main, self.wt1)
        self.assertEqual(taken["status"], "ok", taken)
        self.assertEqual([(item["key"], item["removed"], item["lease"]["lease_id"])
                          for item in taken["orphans"]["leases"]],
                         [("wt2", True, acquired["lease"]["lease_id"])], taken)
        self.assertFalse((self.leases / "wt2.json").exists())

    def test_an_orphan_whose_critical_section_is_held_is_kept_and_reported(self):
        self.acquire(self.main, self.wt2)
        self.remove_worktree(self.wt2)
        created = (datetime.now(timezone.utc) - timedelta(minutes=5)).astimezone().isoformat()
        lock = self.leases / "wt2.lock"
        lock.write_text(json.dumps({"created": created, "host": "fixture-host", "pid": 4242, "operation": "acquire",
                                    "checkout": "wt2"}) + "\n", encoding="utf-8")
        listed = self.listing(self.main)
        [orphan] = listed["orphans"]["leases"]
        self.assertEqual((orphan["key"], orphan["removed"], orphan["status"]), ("wt2", False, "busy"), orphan)
        self.assertTrue((self.leases / "wt2.json").exists())
        self.assertTrue(lock.exists())
        self.assertFalse(listed["complete"], listed)

    def test_an_unreadable_orphan_is_reported_and_kept(self):
        self.acquire(self.main, self.wt2)
        self.remove_worktree(self.wt2)
        (self.leases / "wt2.json").write_text("{not json", encoding="utf-8")
        listed = self.listing(self.main)
        [orphan] = listed["orphans"]["leases"]
        self.assertEqual((orphan["key"], orphan["removed"]), ("wt2", False), orphan)
        self.assertTrue(orphan["reason"], orphan)
        self.assertEqual((self.leases / "wt2.json").read_text(encoding="utf-8"), "{not json")

    def test_a_prunable_or_missing_worktrees_lease_is_kept_and_listed_unknown(self):
        first = self.acquire(self.main, self.wt1)
        second = self.acquire(self.main, self.wt2)
        self.git(self.main, "worktree", "unlock", str(self.wt1))
        (self.wt1 / ".git").unlink()
        remove_base(self.wt2)
        listed = self.listing(self.main)
        self.assertEqual(listed["orphans"], {"state": "known", "leases": []}, listed)
        for checkout, acquired in ((self.wt1, first), (self.wt2, second)):
            with self.subTest(checkout=checkout.name):
                lease = self.entry(listed, checkout)["lease"]
                self.assertEqual((lease["state"], lease["lease"]), ("unknown", acquired["lease"]), lease)
                self.assertTrue((self.leases / f"{checkout.name}.json").exists())

    def test_acquiring_a_held_worktree_whose_directory_is_missing_is_refused_and_keeps_the_lease(self):
        acquired = self.acquire(self.main, self.wt1)
        data = (self.leases / "wt1.json").read_bytes()
        remove_base(self.wt1)
        refused = self.acquire(self.main, self.wt1, session="beta")
        self.assertEqual((refused["status"], refused["code"], refused["acquired"]),
                         ("refused", "directory-missing", False), refused)
        self.assertEqual((refused["lease"], refused["version"]), (acquired["lease"], acquired["version"]), refused)
        self.assertIn("kept", refused["reason"])
        self.assertEqual((self.leases / "wt1.json").read_bytes(), data)

    def test_an_unknown_checkout_key_leaves_every_lease(self):
        self.acquire(self.main, self.wt2)
        self.remove_worktree(self.wt2)
        # A second administration directory naming wt1 leaves wt1's key unknown.
        admin = self.main / ".git" / "worktrees"
        shutil.copytree(admin / "wt1", admin / "wt1-copy")
        listed = self.listing(self.main)
        unkeyed = [item for item in listed["checkouts"] if item["key"] is None]
        self.assertTrue(unkeyed, listed)
        self.assertEqual(listed["orphans"]["state"], "unknown", listed)
        self.assertTrue((self.leases / "wt2.json").exists())


class FactsOnlyTest(ListingBase):
    def test_the_listing_never_calls_a_checkout_usable(self):
        self.acquire(self.main, self.wt1)
        listed = self.listing(self.main)
        self.assertEqual(self.entry(listed, self.wt2)["lease"], {"state": "absent", "description": "no registered use"})
        text = json.dumps(listed, ensure_ascii=False).lower()
        for word in ("usable", "reusable", "free", "available", "idle"):
            self.assertIsNone(re.search(rf"\b{word}\b", text), word)


def checkout(path: str, *, main: bool = False, exists: bool = True) -> Checkout:
    return Checkout(path=path, main=main, head=None, branch=None, detached=False, key=None, exists=exists)


class JudgeRecordsTest(unittest.TestCase):
    """Handoff `list` results a real repository the lease tool lists cannot produce are fed to the pure judging
    function: an uncertain root and a failed enumeration of the other checkouts."""

    MAIN, LINKED = "/repo/main", "/repo/wt1"

    def item(self, work: str, environment: str) -> dict:
        return {"work": work, "title": work, "status": "進行中", "record_status": "進行中",
                "updated": "2026-11-09T10:00:00+08:00", "environment": environment}

    def result(self, **overrides) -> dict:
        return {"status": "ok", "complete": True, "items": [self.item("m.md", self.MAIN + " here"),
                                                            self.item("l.md", self.LINKED)],
                "issues": [], "other_stores": [], "other_stores_complete": True, "other_stores_issues": [],
                "root": {"state": "git", "path": self.MAIN, "store": self.MAIN}, **overrides}

    def judge(self, main: dict, others: dict | None = None) -> list[dict]:
        return leftover.judge_records([checkout(self.MAIN, main=True), checkout(self.LINKED)], main, others or {})

    def test_a_readable_store_gives_each_checkout_its_records(self):
        parts = self.judge(self.result())
        self.assertEqual([[record["work"] for record in part["records"]] for part in parts], [["m.md"], ["l.md"]])

    def test_a_failed_enumeration_of_the_other_checkouts_is_unknown_for_every_linked_worktree(self):
        failed = [{"code": "git", "message": "The repository's checkouts could not be listed: broken"}]
        parts = self.judge(self.result(status="partial", complete=False, other_stores_complete=False,
                                       other_stores_issues=failed))
        self.assertEqual([record["work"] for record in parts[0]["records"]], ["m.md"])
        self.assertEqual(parts[1]["state"], "unknown", parts)
        self.assertIn("broken", parts[1]["reason"])

    def test_an_uncertain_root_is_unknown_for_every_checkout(self):
        uncertain = [{"code": "project-root-uncertain", "message": "Other checkouts were not searched"}]
        for main in (self.result(root={"state": "uncertain", "reason": "discovery failed", "path": self.MAIN}),
                     self.result(other_stores_issues=uncertain)):
            with self.subTest(root=main["root"]["state"]):
                self.assertEqual([part["state"] for part in self.judge(main)], ["unknown", "unknown"])

    def test_the_overall_status_alone_does_not_make_the_main_store_unreadable(self):
        entry = {"checkout": self.LINKED, "main_worktree": False, "complete": False, "works": [],
                 "issues": [{"code": "unreadable", "message": "denied"}]}
        others = {self.LINKED: {"status": "error", "code": "io", "message": "denied"}}
        parts = self.judge(self.result(status="partial", complete=False, other_stores=[entry],
                                       other_stores_complete=False), others)
        self.assertEqual([record["work"] for record in parts[0]["records"]], ["m.md"])
        self.assertEqual(parts[1]["state"], "unknown", parts)

    def test_an_other_store_is_matched_by_its_listed_path(self):
        entry = {"checkout": "/real/wt1", "listed": self.LINKED, "main_worktree": False, "complete": True,
                 "works": [{"work": "own.md"}], "issues": []}
        own = {"status": "ok", "complete": True, "items": [self.item("own.md", self.LINKED)], "issues": [],
               "root": {"state": "explicit", "path": "/real/wt1", "store": "/real/wt1"}}
        parts = self.judge(self.result(other_stores=[entry]), {"/real/wt1": own})
        self.assertEqual(sorted(record["work"] for record in parts[1]["records"]), ["l.md", "own.md"])
        unreadable = {**own, "status": "partial", "complete": False, "issues": [{"code": "io", "message": "x"}]}
        parts = self.judge(self.result(other_stores=[entry]), {"/real/wt1": unreadable})
        self.assertEqual((parts[0]["state"], parts[1]["state"]), ("known", "unknown"), parts)

    def test_the_longest_whole_path_names_the_record(self):
        # The spec bounds a whole path only on its right; whatever precedes it, such as text written without a space
        # before the path, does not stop it naming the checkout.
        cases = {"/repo/main/x": 0, "/repo/main": 0, "/repo/main,": 0, "/repo/mainline": None, "/x/repo/main": 0,
                 "/repo/wt1/src": 1, "(/repo/wt1)": 1, "/repo/wt10": None, "工作樹/repo/main（main）": 0,
                 "位於/repo/wt1，分支 x": 1, "file:///repo/main": 0}
        for environment, expected in cases.items():
            with self.subTest(environment=environment):
                self.assertEqual(leftover.named_checkout(environment, [self.MAIN, self.LINKED]), expected)
        nested = ["/repo/main", "/repo/main/.claude/worktrees/a"]
        self.assertEqual(leftover.named_checkout("at /repo/main/.claude/worktrees/a now", nested), 1)
        if WINDOWS:
            self.assertEqual(leftover.named_checkout(r"D:\Repo\WT1\x", ["d:/repo/wt1"]), 0)


if __name__ == "__main__":
    unittest.main()
