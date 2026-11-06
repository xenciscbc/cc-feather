"""`list` reports records in other stores (worktree store ticket 05).

A user upgrading from 0.30.0, or switching tracking, learns about records outside the store the current run uses
before they are lost with a worktree: `list` reports `other_stores` for every other checkout of the repository that
holds `.feather/handoffs/`, plus the shared store when the run keeps a checkout-local store, with work names qualified
by checkout and their status. A checkout that cannot be read or no longer exists makes the result incomplete. Other
stores are read only: the work file names, each one's status line and whether history.md or archive/ holds anything;
their paths pass the existing link checks, and nothing is written in another checkout.

The fixture and its isolated Git environment are those of tests/test_handoff_shared_store.py: a unique directory made
with mkdtemp under FEATHER_LINK_TEST_DIR when it is set, synthetic data only, removed on cleanup. The tool runs as a
subprocess with --project; the in-process cases drive only the CLI entry point. The 0.30.0-style records of the
upgrade case are written directly into a linked worktree's own `.feather/handoffs/`. The unreadable-store case denies
listing the store directory with a denying ACL entry on Windows and permission bits on POSIX, and is skipped with the
reason when the platform or user can still list it; the link case is skipped where no directory link can be made."""
import os
from pathlib import Path
import stat
import subprocess
import unittest
from unittest import mock

from tests import feather_support
from tests.test_handoff_shared_store import (FIELDS, HOST_TOOLS, MARKER, SKILL, TOOL_REFERENCE, SharedBase,
                                             assert_sentences, git_call, normalized, remove_base)

WINDOWS = os.name == "nt"
NOT_DENIED = ("this platform and user can still list a directory denied read access (for example running as root, "
              "or a volume that ignores permission bits or ACLs)")


def old_record(title: str, status: str = "進行中", body: str = "") -> str:
    """A record as 0.30.0 wrote it in a linked worktree's own store."""
    return (f"# {title}\n更新：2026-10-01T10:00:00+08:00\n狀態：{status}\n目標：g\n進度：p\n下一步：n\n\n"
            f"## 詳細紀錄\n{body}")


class OtherStoresBase(SharedBase):
    def write_store(self, checkout: Path, records: dict[str, str], history: str | None = None,
                    archive: dict[str, str] | None = None) -> Path:
        store = checkout / ".feather" / "handoffs"
        store.mkdir(parents=True, exist_ok=True)
        for name, text in records.items():
            (store / name).write_bytes(text.encode("utf-8"))
        if history is not None:
            (store / "history.md").write_bytes(history.encode("utf-8"))
        for name, text in (archive or {}).items():
            (store / "archive").mkdir(exist_ok=True)
            (store / "archive" / name).write_bytes(text.encode("utf-8"))
        return store

    def entries(self, listed: dict) -> dict[Path, dict]:
        return {Path(entry["checkout"]): entry for entry in listed["other_stores"]}

    def works(self, entry: dict) -> list[tuple[str, str | None]]:
        return [(work["work"], work["status"]) for work in entry["works"]]


class UpgradeTest(OtherStoresBase):
    """0.30.0-style records in a linked worktree's own store are reported from that worktree and from the main
    worktree, qualified by that worktree, and nothing is written anywhere."""

    def test_records_a_linked_worktree_wrote_itself_are_reported_from_every_checkout(self):
        self.write_store(self.wt1, {"a.md": old_record("a"), "b.md": old_record("b", "受阻")},
                         history="## old · 完成：2026-09-01T10:00:00+08:00\n\nbody\n",
                         archive={"2026-09.md": "sealed\n"})
        before = self.tree()
        for project in (self.wt1, self.main, self.wt2):
            with self.subTest(project=project.name):
                listed = self.run_tool(project, "list")
                self.assertEqual((listed["status"], listed["complete"], listed["items"]), ("missing", True, []),
                                 listed)
                self.assertEqual((listed["other_stores_complete"], listed["other_stores_issues"]), (True, []))
                self.assertEqual(list(self.entries(listed)), [self.wt1], listed)
                entry = listed["other_stores"][0]
                self.assertEqual(self.works(entry), [("a.md", "進行中"), ("b.md", "受阻")])
                self.assertEqual((entry["checkout"], entry["store"], entry["main_worktree"], entry["complete"],
                                  entry["history"], entry["archive"], entry["issues"]),
                                 (str(self.wt1), str(self.wt1 / ".feather" / "handoffs"), False, True, True, True,
                                  []), entry)
                for work in entry["works"]:
                    self.assertEqual((work["checkout"], work["path"]),
                                     (str(self.wt1), str(self.wt1 / ".feather" / "handoffs" / work["work"])))
        # Nothing is written anywhere, in the reported checkout or in the shared store.
        self.assertEqual(self.tree(), before)

    def test_an_empty_history_and_archive_hold_nothing_and_the_lock_is_no_record(self):
        store = self.write_store(self.wt1, {"a.md": old_record("a")}, history="")
        (store / "archive").mkdir()
        (store / ".history.lock").write_text("{}", encoding="utf-8")
        entry = self.run_tool(self.main, "list")["other_stores"][0]
        self.assertEqual((self.works(entry), entry["history"], entry["archive"]), ([("a.md", "進行中")], False, False))

    def test_a_checkout_without_a_store_is_not_reported(self):
        (self.wt1 / ".feather").mkdir()
        listed = self.run_tool(self.main, "list")
        self.assertEqual((listed["other_stores"], listed["other_stores_complete"]), ([], True), listed)


class QualificationTest(OtherStoresBase):
    def test_equal_work_names_in_different_stores_stay_distinct(self):
        self.run_tool(self.main, "create", "--work", "a.md", payload={"title": "main a", "fields": FIELDS})
        self.write_store(self.wt1, {"a.md": old_record("wt1 a")})
        self.write_store(self.wt2, {"a.md": old_record("wt2 a", "完成")})
        listed = self.run_tool(self.main, "list")
        self.assertEqual([item["work"] for item in listed["items"]], ["a.md"], listed)
        entries = self.entries(listed)
        self.assertEqual(set(entries), {self.wt1, self.wt2}, listed)
        qualified = {(work["checkout"], work["work"]) for entry in entries.values() for work in entry["works"]}
        self.assertEqual(qualified, {(str(self.wt1), "a.md"), (str(self.wt2), "a.md")})
        paths = {work["path"] for entry in entries.values() for work in entry["works"]}
        self.assertEqual(len(paths), 2)
        self.assertEqual(self.works(entries[self.wt2]), [("a.md", "完成")])


class TrackedCheckoutTest(OtherStoresBase):
    def test_a_tracked_checkout_reports_the_shared_store(self):
        self.run_tool(self.wt2, "create", "--work", "shared.md", payload={"title": "shared", "fields": FIELDS})
        (self.wt1 / ".gitignore").write_text(MARKER + "\n", encoding="utf-8")
        self.run_tool(self.wt1, "create", "--work", "own.md", payload={"title": "own", "fields": FIELDS})
        listed = self.run_tool(self.wt1, "list")
        self.assertEqual((listed["root"]["tracking"], listed["root"]["shared"]), ("tracked", False), listed)
        self.assertEqual([item["work"] for item in listed["items"]], ["own.md"], listed)
        self.assertEqual(list(self.entries(listed)), [self.main], listed)
        entry = listed["other_stores"][0]
        self.assertEqual((entry["main_worktree"], self.works(entry), entry["complete"]),
                         (True, [("shared.md", "進行中")], True), entry)
        # The shared run from the other linked worktree reports the tracked checkout's store in turn.
        shared = self.run_tool(self.wt2, "list")
        self.assertEqual([item["work"] for item in shared["items"]], ["shared.md"], shared)
        self.assertEqual([(path, self.works(entry)) for path, entry in self.entries(shared).items()],
                         [(self.wt1, [("own.md", "進行中")])], shared)


class IncompleteTest(OtherStoresBase):
    """A worktree directory deleted behind Git's back, an unreadable store and a store reached through a link are
    listed with a reason and make the result incomplete; the current store keeps its items."""

    def assert_incomplete(self, listed: dict, checkout: Path, code: str) -> dict:
        self.assertEqual((listed["status"], listed["complete"], listed["other_stores_complete"]),
                         ("partial", False, False), listed)
        self.assertEqual([item["work"] for item in listed["items"]], ["here.md"], listed)
        self.assertEqual(listed["issues"], [], listed)
        entry = self.entries(listed)[checkout]
        self.assertEqual((entry["complete"], [issue["code"] for issue in entry["issues"]]), (False, [code]), entry)
        self.assertIn(str(checkout.name), entry["issues"][0]["message"])
        return entry

    def test_a_worktree_deleted_behind_gits_back_is_missing(self):
        self.run_tool(self.main, "create", "--work", "here.md", payload={"title": "here", "fields": FIELDS})
        remove_base(self.wt2)
        listed = self.run_tool(self.main, "list", expected=2)
        entry = self.assert_incomplete(listed, self.wt2, "missing")
        self.assertEqual((entry["works"], entry["history"], entry["archive"]), ([], None, None), entry)
        self.assertFalse(self.wt2.exists())

    def deny_listing(self, directory: Path):
        if WINDOWS:
            user = os.environ.get("USERNAME")
            if not user:
                self.skipTest("no USERNAME to deny listing the directory to")
            denied = subprocess.run(["icacls", str(directory), "/deny", f"{user}:(RD)"], capture_output=True)
            self.addCleanup(subprocess.run, ["icacls", str(directory), "/remove:d", user], capture_output=True)
            if denied.returncode:
                self.skipTest(f"icacls could not deny listing {directory} (exit {denied.returncode})")
        else:
            mode = stat.S_IMODE(directory.stat().st_mode)
            directory.chmod(0o000)
            self.addCleanup(directory.chmod, mode)
        try:
            with os.scandir(directory) as entries:
                list(entries)
        except PermissionError:
            return
        self.skipTest(NOT_DENIED)

    def test_an_unreadable_store_is_listed_with_its_reason(self):
        self.run_tool(self.main, "create", "--work", "here.md", payload={"title": "here", "fields": FIELDS})
        store = self.write_store(self.wt1, {"a.md": old_record("a")})
        self.deny_listing(store)
        listed = self.run_tool(self.main, "list", expected=2)
        self.assert_incomplete(listed, self.wt1, "unreadable")

    def test_a_store_reached_through_a_link_is_refused_and_not_followed(self):
        self.run_tool(self.main, "create", "--work", "here.md", payload={"title": "here", "fields": FIELDS})
        self.write_store(self.outside, {"a.md": old_record("a")})
        feather_support.make_directory_link(self.wt1 / ".feather", self.outside / ".feather")
        before = self.tree(self.outside)
        listed = self.run_tool(self.main, "list", expected=2)
        entry = self.assert_incomplete(listed, self.wt1, "unsafe-path")
        self.assertIn("Link/reparse path is not supported", entry["issues"][0]["message"])
        self.assertEqual(entry["works"], [], entry)
        self.assertEqual(self.tree(self.outside), before)

    def test_a_hard_linked_work_file_is_reported_not_read(self):
        self.run_tool(self.main, "create", "--work", "here.md", payload={"title": "here", "fields": FIELDS})
        store = self.write_store(self.wt1, {"a.md": old_record("a")})
        try:
            os.link(store / "a.md", self.outside / "alias.md")
        except OSError as error:
            self.skipTest(f"hard links are unavailable here: {error}")
        listed = self.run_tool(self.main, "list", expected=2)
        entry = self.assert_incomplete(listed, self.wt1, "unsafe-path")
        self.assertEqual(self.works(entry), [("a.md", None)], entry)
        self.assertEqual(entry["issues"][0]["work"], "a.md")


class ReadOnlyTest(OtherStoresBase):
    def test_only_the_header_up_to_the_status_line_is_read(self):
        header = "# a\n更新：2026-10-01T10:00:00+08:00\n狀態：受阻\n"
        self.write_store(self.wt1, {"a.md": header + "目標：g\n進度：p\n下一步：n\n\n## 詳細紀錄\n狀態：完成\n" + "x" * 100000})
        target = os.path.normcase(str(self.wt1 / ".feather" / "handoffs" / "a.md"))
        returned = []
        real_open = Path.open

        class Counted:
            def __init__(self, handle):
                self.handle = handle

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return self.handle.__exit__(*exc)

            def fileno(self):
                return self.handle.fileno()

            def readline(self, *args):
                line = self.handle.readline(*args)
                returned.append(line)
                return line

            def read(self, *args):
                data = self.handle.read(*args)
                returned.append(data)
                return data

        def counted(path, *args, **kwargs):
            handle = real_open(path, *args, **kwargs)
            return Counted(handle) if os.path.normcase(str(path)) == target else handle
        with mock.patch.object(Path, "open", counted):
            code, listed = self.invoke(self.main, "list")
        self.assertEqual(code, 0, listed)
        self.assertEqual(self.works(listed["other_stores"][0]), [("a.md", "受阻")], listed)
        self.assertEqual(b"".join(returned), header.encode("utf-8"))

    def test_a_status_after_the_first_heading_is_not_a_header_status(self):
        self.write_store(self.wt1, {"a.md": "# a\n更新：2026-10-01T10:00:00+08:00\n\n## 詳細紀錄\n狀態：完成\n"})
        entry = self.run_tool(self.main, "list")["other_stores"][0]
        self.assertEqual((self.works(entry), entry["complete"]), ([("a.md", None)], True), entry)

    def test_the_worktree_list_runs_after_the_lazy_fetch_guard_in_the_working_checkout(self):
        with self.git_as() as calls:
            code, listed = self.invoke(self.main, "list")
        self.assertEqual(code, 0, listed)
        started = [git_call(args)[:2] for args in calls]
        listing = started.index((str(self.main), ["worktree", "list", "--porcelain", "-z"]))
        self.assertIn((str(self.main), ["config", "--list", "--includes", "-z"]), started[:listing])
        # Other checkouts are read from the filesystem only; no Git command runs there.
        self.assertFalse([item for item in started if item[0] in {str(self.wt1), str(self.wt2)}], started)


class RootScopeTest(OtherStoresBase):
    def test_an_uncertain_root_searches_no_other_checkout(self):
        self.write_store(self.wt2, {"a.md": old_record("a")})
        feather_support.make_directory_link(self.main / ".feather", self.outside)
        listed = self.run_tool(self.wt1, "list", expected=2)
        self.assertEqual((listed["status"], listed["complete"], listed["operation_status"]),
                         ("partial", False, "missing"), listed)
        self.assertEqual((listed["other_stores"], listed["other_stores_complete"]), ([], False), listed)
        self.assertEqual([issue["code"] for issue in listed["other_stores_issues"]], ["project-root-uncertain"])
        self.assertIn("Handoff store discovery failed", listed["other_stores_issues"][0]["message"])

    def test_a_non_git_project_and_an_exact_root_search_no_other_checkout(self):
        self.write_store(self.wt2, {"a.md": old_record("a")})
        plain = self.base / "plain"
        plain.mkdir()
        for label, project, exact in (("non-git", plain, False), ("exact root", self.wt1, True)):
            with self.subTest(case=label):
                listed = self.run_tool(project, "list", exact=exact)
                self.assertEqual((listed["status"], listed["other_stores"], listed["other_stores_complete"]),
                                 ("missing", [], True), listed)

    def test_a_failed_worktree_list_makes_the_result_incomplete(self):
        def fails(directory, command):
            if directory == str(self.main) and command[:2] == ["worktree", "list"]:
                return 128, "", "fatal: broken\n"
            return None
        with self.git_as(override=fails):
            code, listed = self.invoke(self.main, "list")
        self.assertEqual((code, listed["status"], listed["complete"], listed["other_stores_complete"]),
                         (2, "partial", False, False), listed)
        self.assertEqual([issue["code"] for issue in listed["other_stores_issues"]], ["git"], listed)
        self.assertIn("fatal: broken", listed["other_stores_issues"][0]["message"])


class SkillOtherStoresTest(unittest.TestCase):
    """Acceptance 12's skill share for item 9."""

    SENTENCES = (
        "A list result's `other_stores` reports records left in the stores of other checkouts of the repository, "
        "such as a linked worktree's records from before the shared store or a store left behind by a tracking "
        "switch.",
        "Report `other_stores` with every list and resume result: name each checkout with its work files and their "
        "status, and say whether its history or archive holds anything.",
        "When `other_stores_complete` is false, a checkout could not be read or no longer exists: report its reason, "
        "and never treat the result as showing that no pending work exists elsewhere.",
        "Records under `other_stores` belong to their checkout; they are not items of the current store, and they "
        "are not moved or changed without the user's decision.",
    )

    def test_the_skill_states_the_other_stores_rules(self):
        assert_sentences(self, SKILL, self.SENTENCES)

    def test_the_rules_name_no_hosts_tools(self):
        for sentence in self.SENTENCES:
            with self.subTest(sentence=sentence[:60]):
                self.assertNotRegex(sentence, HOST_TOOLS)


class ToolReferenceOtherStoresTest(unittest.TestCase):
    """Acceptance 12's tool-reference share for item 9: the `other_stores` field."""

    SENTENCES = (
        "`list` also reports `other_stores`: one entry for each other checkout that `git worktree list --porcelain "
        "-z`, run from the Working checkout after its lazy-fetch guard, reports with a `.feather/handoffs/` "
        "directory, other than the checkout that holds the current store, so a run with a checkout-local store also "
        "reports the main worktree's shared store.",
        "`git worktree list` reads no objects, so it also runs when the guard finds a promisor remote that the "
        "installed Git cannot guard.",
        "Each entry gives `checkout`, the checkout's real path (`listed` adds Git's spelling when it differs), "
        "`main_worktree`, `store`, `works` with each work file's `work`, `checkout`, `path` and `status`, the value "
        "of its first header status line or `null`, and `history` and `archive`, whether `history.md` is nonempty "
        "and whether `archive/` holds any entry.",
        "Work names are qualified by `checkout` and `path`, so equal names in different stores stay distinct.",
        "The tool reads no record body beyond the header's status line and writes nothing in another checkout.",
        "That checkout's `.feather/handoffs/`, work files, `history.md` and `archive/` pass the link checks above, "
        "and a link, junction or hard link there is reported as an issue rather than followed.",
        "An entry whose checkout no longer exists has an issue with `code: missing`; an entry whose store or files "
        "cannot be read or are refused has an issue with the failure's code.",
        "Such an entry has `complete: false` and its `issues`, each with `code` and `message`, and it makes "
        "`other_stores_complete` false and the list `partial` with `complete: false`; a failure to list the "
        "checkouts does the same and is reported in `other_stores_issues`.",
        "An incomplete `other_stores` never establishes that no pending work exists elsewhere.",
        "Under an uncertain root no other checkout is searched: `other_stores` is empty, `other_stores_complete` is "
        "false and `other_stores_issues` gives the reason, while `operation_status` still describes the current "
        "store.",
        "In a non-Git project and with `--exact-root` no other checkout is searched and `other_stores` is empty.",
        "`items` and `issues` still describe only the current store.",
    )

    def test_the_tool_reference_documents_other_stores(self):
        assert_sentences(self, TOOL_REFERENCE, self.SENTENCES)

    def test_no_new_text_uses_the_forbidden_word(self):
        for sentence in (*self.SENTENCES, *SkillOtherStoresTest.SENTENCES):
            with self.subTest(sentence=sentence[:60]):
                self.assertNotIn("tidy", sentence.lower())
        self.assertIn("other_stores", normalized(TOOL_REFERENCE))


if __name__ == "__main__":
    unittest.main()
