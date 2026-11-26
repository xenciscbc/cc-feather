"""The Speed-up record script of /cc-feather:test-speedup (docs/specs/test-speedup-record.md, ticket 01).

The script runs against the shared fixture of tests/test_handoff_shared_store.py, imported unchanged: a base made with
mkdtemp under FEATHER_LINK_TEST_DIR when set, holding main/ with one commit and linked worktrees wt1 and wt2, with an
isolated Git environment and synthetic data only, removed on cleanup; plus a non-Git directory plain/ in the same base.
Single calls run in the test process through the entry point, `feather_speedup.cli.main()`, given the argument list a
subprocess gets and its JSON input on standard input, with only the JSON result, the exit code and the files left on
disk asserted; the launcher, the unsupported-Python error and the environment the script sees run as subprocesses.
Bounds: each test uses a handful of files and items; the top-ten check uses twelve tests each way; no test generates a
large record. Two writes at the same instant are a residual risk the spec accepts and are not tested."""
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock

from tests.test_handoff_shared_store import ROOT, SharedBase

SPEEDUP_SCRIPTS = ROOT / "skills/test-speedup/scripts"
HANDOFF_SCRIPTS = ROOT / "skills/handoff/scripts"
for _path in (SPEEDUP_SCRIPTS, HANDOFF_SCRIPTS):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from feather_handoff import storage  # noqa: E402
from feather_speedup import cli  # noqa: E402

TOOL = SPEEDUP_SCRIPTS / "speedup.py"
TIMEOUT = 60
D1, D2, D3, D4 = ("2026-11-01T10:00:00+08:00", "2026-11-02T10:00:00+08:00", "2026-11-03T10:00:00+08:00",
                  "2026-11-04T10:00:00+08:00")
KEY = {"command": "pytest", "selected": ["tests"], "concurrency": 1, "override": None, "runner": None,
       "left_out": []}


def item(file, tests=None, setting=None, section="speed-up", description="make it faster"):
    value = {"section": section, "file": file, "description": description, "location": f"{file}:1",
             "expected_gain": "1s", "correctness": "same assertions", "risk": "low"}
    if tests is not None:
        value["tests"] = tests
    else:
        value["setting"] = setting
    return value


class SpeedupBase(SharedBase):
    def setUp(self):
        super().setUp()
        self.record_dir = self.main / ".feather" / "test-speedup"
        self.plain = self.base / "plain"
        self.plain.mkdir()

    def command(self, project: Path, *args) -> list[str]:
        return [sys.executable, "-B", str(TOOL), "--project", str(project), *args]

    def tool(self, project: Path, *args, payload=None, expected=0, env=None, process=False, raw=None) -> dict:
        """The script's JSON result, its exit code asserted. Given an env, or asked for a process, it runs as a
        subprocess; otherwise its entry point runs in this process with a fresh process's registered roots."""
        data = raw if raw is not None else (b"" if payload is None else json.dumps(payload).encode("utf-8"))
        if env is not None or process:
            result = subprocess.run(self.command(project, *args), input=data, capture_output=True, timeout=TIMEOUT,
                                    env=env)
            output = result.stdout.decode("utf-8")
            self.assertEqual(result.returncode, expected, output + result.stderr.decode("utf-8", "replace"))
            return json.loads(output)
        stdout = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
        stdin = io.TextIOWrapper(io.BytesIO(data), encoding="utf-8")
        storage.reset_roots()
        try:
            with mock.patch.object(sys, "argv", self.command(project, *args)[2:]), \
                    mock.patch.object(sys, "stdout", stdout), mock.patch.object(sys, "stdin", stdin), \
                    mock.patch.object(sys, "stderr", io.StringIO()):
                code = cli.main()
            stdout.flush()
        finally:
            storage.reset_roots()
        output = stdout.buffer.getvalue().decode("utf-8")
        self.assertEqual(code, expected, output)
        return json.loads(output)

    def write(self, project: Path, path: str, text: str) -> None:
        target = project / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(text.encode("utf-8"))

    def version(self, project: Path) -> str:
        return self.tool(project, "read")["version"]

    def record(self, project: Path) -> dict:
        return self.tool(project, "read")["record"]

    def run_record(self, project: Path, files=(), items=(), *, shared=(), scope=(".",), deleted=(), date=D1,
                   version=None, expected=0, versions=None) -> dict:
        payload = {"scope": list(scope), "commit": None, "full": False, "date": date,
                   "files": [{"path": path, "shared": list(shared)} for path in files], "deleted": list(deleted),
                   "items": list(items)}
        if versions is not None:
            payload["versions"] = versions
        return self.tool(project, "record-run", "--version", version or self.version(project), payload=payload,
                         expected=expected)

    def changes(self, project: Path, files=(), *, shared=(), scope=(".",), versions=None) -> dict:
        payload = {"scope": list(scope), "files": [{"path": path, "shared": list(shared)} for path in files]}
        if versions is not None:
            payload["versions"] = versions
        return self.tool(project, "changes", payload=payload)

    def states(self, result: dict) -> dict:
        return {entry["path"]: entry["state"] for entry in result["files"]}

    def entry(self, result: dict, path: str) -> dict:
        return next(entry for entry in result["files"] if entry["path"] == path)

    def classify(self, project: Path, entries, expected=0) -> dict:
        return self.tool(project, "classify", "--version", self.version(project), payload={"items": entries},
                         expected=expected)

    def decide(self, project: Path, entries, expected=0) -> dict:
        return self.tool(project, "decide", "--version", self.version(project), payload={"items": entries},
                         expected=expected)

    def measure(self, project: Path, tests, *, date=D1, key=KEY, succeeded=True, total=None, version=None) -> dict:
        payload = {"commit": None, "date": date, "key": key, "succeeded": succeeded,
                   "total_seconds": sum(tests.values()) if total is None else total, "tests": tests}
        return self.tool(project, "measure", "--version", version or self.version(project), payload=payload)


class LocationTest(SpeedupBase):
    def test_the_main_worktree_holds_the_record(self):
        self.write(self.main, "tests/test_a.py", "a\n")
        result = self.run_record(self.main, ["tests/test_a.py"])
        self.assertEqual(result["status"], "ok", result)
        self.assertEqual(os.path.normcase(result["location"]), os.path.normcase(str(self.record_dir)))
        self.assertTrue((self.record_dir / "record.json").is_file())
        self.assertIn("tests/test_a.py", self.record(self.main)["files"])

    def test_a_linked_worktree_uses_the_main_worktrees_record(self):
        self.write(self.wt1, "tests/test_a.py", "a\n")
        result = self.run_record(self.wt1, ["tests/test_a.py"])
        self.assertEqual(os.path.normcase(result["location"]), os.path.normcase(str(self.record_dir)))
        self.assertEqual(os.path.normcase(result["project"]), os.path.normcase(str(self.wt1)))
        self.assertFalse((self.wt1 / ".feather").exists())
        self.assertIn("tests/test_a.py", self.record(self.wt2)["files"])
        self.assertTrue((self.record_dir / "record.json").is_file())

    def test_a_non_git_project_keeps_the_record_in_its_directory(self):
        self.write(self.plain, "t.py", "a\n")
        result = self.run_record(self.plain, ["t.py"])
        self.assertEqual(os.path.normcase(result["location"]),
                         os.path.normcase(str(self.plain / ".feather" / "test-speedup")))
        self.assertIsNone(result["main_worktree"])
        self.assertEqual((self.plain / ".feather" / "test-speedup" / ".gitignore").read_bytes(), b"*\n")

    def test_a_bare_repository_is_an_error_and_nothing_is_written(self):
        bare = self.base / "bare.git"
        self.git(self.base, "init", "--quiet", "--bare", str(bare))
        before = self.tree()
        failed = self.tool(bare, "record-run", "--version", "absent", expected=2,
                           payload={"scope": ["."], "commit": None, "full": False})
        self.assertEqual((failed["status"], failed["code"]), ("error", "bare-repository"), failed)
        self.assertEqual(self.changed(before, self.tree()), set())

    def test_an_unusable_location_is_an_error_and_nothing_is_written_elsewhere(self):
        (self.main / ".feather").mkdir()
        (self.main / ".feather" / "test-speedup").write_text("not a directory", encoding="utf-8")
        self.write(self.wt1, "t.py", "a\n")
        before = self.tree()
        failed = self.run_record(self.wt1, ["t.py"], version="absent", expected=2)
        self.assertEqual((failed["status"], failed["code"]), ("error", "location"), failed)
        self.assertEqual(self.changed(before, self.tree()), set())

    def test_an_unwritable_directory_is_an_error_and_nothing_is_written(self):
        self.write(self.wt1, "t.py", "a\n")
        before = self.tree()
        denied = PermissionError(13, "Access is denied")
        with mock.patch.object(Path, "mkdir", side_effect=denied):
            failed = self.run_record(self.wt1, ["t.py"], version="absent", expected=2)
        self.assertEqual((failed["status"], failed["code"]), ("error", "location-unwritable"), failed)
        self.assertEqual(self.changed(before, self.tree()), set())

    def test_an_unresolvable_main_worktree_is_an_error_and_nothing_is_written(self):
        self.write(self.wt1, "t.py", "a\n")
        # Git then lists the repository's first worktree as bare, so no main worktree can hold the record.
        self.git(self.main, "config", "core.bare", "true")
        before = self.tree()
        failed = self.run_record(self.wt1, ["t.py"], version="absent", expected=2)
        self.assertEqual((failed["status"], failed["code"]), ("error", "main-worktree"), failed)
        self.assertEqual(self.changed(before, self.tree()), set())

    def test_the_directory_ignores_itself_and_the_project_gitignore_is_untouched(self):
        self.write(self.main, ".gitignore", "*.log\n")
        self.commit(self.main, "ignore logs")
        self.write(self.main, "t.py", "a\n")
        self.commit(self.main, "test")
        self.run_record(self.main, ["t.py"])
        self.measure(self.main, {"t::a": 1.0})
        self.assertEqual((self.record_dir / ".gitignore").read_bytes(), b"*\n")
        self.assertEqual((self.main / ".gitignore").read_bytes(), b"*.log\n")
        self.assertEqual(self.git(self.main, "status", "--porcelain", "--untracked-files=all"), "")


class ChangesTest(SpeedupBase):
    def test_files_are_new_changed_unchanged_or_deleted_by_content_hash(self):
        for name in ("same.py", "edited.py", "gone.py"):
            self.write(self.plain, name, f"{name}\n")
        self.run_record(self.plain, ["same.py", "edited.py", "gone.py"])
        self.write(self.plain, "edited.py", "edited again\n")
        os.utime(self.plain / "same.py")
        (self.plain / "gone.py").unlink()
        self.write(self.plain, "fresh.py", "fresh\n")
        result = self.changes(self.plain, ["same.py", "edited.py", "fresh.py"])
        self.assertEqual(self.states(result), {"same.py": "unchanged", "edited.py": "changed", "fresh.py": "new",
                                               "gone.py": "deleted"})

    def test_uncommitted_content_analysed_then_restored_is_changed(self):
        original = (self.wt1 / "a.txt").read_bytes()
        self.write(self.wt1, "a.txt", "uncommitted\n")
        self.run_record(self.wt1, ["a.txt"])
        self.git(self.wt1, "checkout", "--", "a.txt")
        self.assertEqual((self.wt1 / "a.txt").read_bytes(), original)
        self.assertEqual(self.states(self.changes(self.wt1, ["a.txt"])), {"a.txt": "changed"})

    def test_a_shared_file_changed_added_or_removed_changes_the_shared_set_hash(self):
        self.write(self.plain, "t.py", "t\n")
        self.write(self.plain, "conftest.py", "c\n")
        self.write(self.plain, "setup.cfg", "s\n")
        self.run_record(self.plain, ["t.py"], shared=["conftest.py"])
        self.assertFalse(self.entry(self.changes(self.plain, ["t.py"], shared=["conftest.py"]), "t.py")
                         ["shared_set_changed"])
        added = self.entry(self.changes(self.plain, ["t.py"], shared=["conftest.py", "setup.cfg"]), "t.py")
        self.assertEqual((added["state"], added["shared_set_changed"], added["shared_changes"]),
                         ("unchanged", True, [{"path": "setup.cfg", "change": "added"}]))
        removed = self.entry(self.changes(self.plain, ["t.py"], shared=[]), "t.py")
        self.assertEqual((removed["shared_set_changed"], removed["shared_changes"]),
                         (True, [{"path": "conftest.py", "change": "removed"}]))
        self.write(self.plain, "conftest.py", "c2\n")
        changed = self.entry(self.changes(self.plain, ["t.py"], shared=["conftest.py"]), "t.py")
        self.assertEqual((changed["shared_set_changed"], changed["shared_changes"]),
                         (True, [{"path": "conftest.py", "change": "changed"}]))

    def test_a_shared_set_change_stays_reported_for_a_file_not_analysed_again(self):
        for name in ("t1.py", "t2.py", "conftest.py"):
            self.write(self.plain, name, f"{name}\n")
        self.run_record(self.plain, ["t1.py", "t2.py"], shared=["conftest.py"])
        self.write(self.plain, "conftest.py", "changed\n")
        seen = self.changes(self.plain, ["t1.py", "t2.py"], shared=["conftest.py"])
        self.assertEqual([self.entry(seen, name)["shared_set_changed"] for name in ("t1.py", "t2.py")], [True, True])
        self.run_record(self.plain, ["t1.py"], shared=["conftest.py"], date=D2)
        later = self.changes(self.plain, ["t1.py", "t2.py"], shared=["conftest.py"])
        self.assertEqual([self.entry(later, name)["shared_set_changed"] for name in ("t1.py", "t2.py")], [False, True])

    def test_a_deletion_is_reported_only_inside_the_scope(self):
        self.write(self.plain, "a/t.py", "a\n")
        self.write(self.plain, "b/t.py", "b\n")
        self.run_record(self.plain, ["a/t.py", "b/t.py"])
        (self.plain / "a" / "t.py").unlink()
        (self.plain / "b" / "t.py").unlink()
        self.assertEqual(self.states(self.changes(self.plain, [], scope=["a"])), {"a/t.py": "deleted"})

    def test_a_partial_run_leaves_other_files_entries_alone(self):
        self.write(self.plain, "t1.py", "1\n")
        self.write(self.plain, "t2.py", "2\n")
        self.run_record(self.plain, ["t1.py", "t2.py"])
        before = self.record(self.plain)["files"]["t2.py"]
        self.write(self.plain, "t1.py", "1 changed\n")
        self.write(self.plain, "t2.py", "2 changed\n")
        self.run_record(self.plain, ["t1.py"], date=D2)
        files = self.record(self.plain)["files"]
        self.assertEqual(files["t2.py"], before)
        self.assertEqual(files["t1.py"]["analysed"], D2)
        self.assertEqual(self.states(self.changes(self.plain, ["t1.py", "t2.py"])),
                         {"t1.py": "unchanged", "t2.py": "changed"})

    def test_a_listed_file_that_does_not_exist_is_an_input_error(self):
        failed = self.tool(self.plain, "changes", payload={"scope": ["."], "files": [{"path": "nope.py"}]},
                           expected=2)
        self.assertEqual(failed["code"], "input", failed)


class ItemsTest(SpeedupBase):
    def setUp(self):
        super().setUp()
        self.write(self.plain, "t.py", "t\n")
        self.write(self.plain, "u.py", "u\n")

    def key(self, result: dict, index=0) -> str:
        return result["found"][index]["key"]

    def test_the_key_orders_test_ids_and_matches_across_runs(self):
        first = self.run_record(self.plain, ["t.py"], [item("t.py", ["b", "a", "b"])])
        self.assertEqual(self.key(first), '["speed-up","t.py","tests",["a","b"]]')
        self.assertEqual(first["found"][0]["outcome"], "new")
        self.assertEqual(self.record(self.plain)["items"][self.key(first)]["state"], "undecided")
        self.decide(self.plain, [{"key": self.key(first), "state": "picked", "reason": "user picked it"}])
        again = self.run_record(self.plain, ["t.py"], [item("t.py", ["a", "b"]), item("t.py", setting="workers")],
                                date=D2)
        self.assertEqual([(entry["outcome"], entry["state"]) for entry in again["found"]],
                         [("matched", "picked"), ("new", "undecided")])
        self.assertEqual(self.key(again, 1), '["speed-up","t.py","setting","workers"]')

    def test_two_found_items_sharing_a_key_are_refused(self):
        version = self.version(self.plain)
        failed = self.run_record(self.plain, ["t.py"], [item("t.py", ["a", "b"]), item("t.py", ["b", "a"])],
                                 version=version, expected=2)
        self.assertEqual(failed["code"], "duplicate-key", failed)
        self.assertIn('["speed-up","t.py","tests",["a","b"]]', failed["message"])
        self.assertEqual(self.version(self.plain), version)

    def test_a_landed_or_obsolete_item_found_again_is_reopened_with_its_earlier_state(self):
        found = self.run_record(self.plain, ["t.py"], [item("t.py", ["a"]), item("t.py", ["b"])])
        landed, obsolete = self.key(found, 0), self.key(found, 1)
        self.classify(self.plain, [{"key": landed, "state": "landed", "evidence": "the fixture is shared", "date": D2},
                                   {"key": obsolete, "state": "obsolete", "evidence": "test b is gone",
                                    "date": D2}])
        again = self.run_record(self.plain, ["t.py"], [item("t.py", ["a"]), item("t.py", ["b"])], date=D3)
        self.assertEqual([(entry["outcome"], entry["state"]) for entry in again["found"]],
                         [("reopened", "undecided"), ("reopened", "undecided")])
        items = self.record(self.plain)["items"]
        self.assertEqual(items[landed]["history"][-1],
                         {"state": "landed", "date": D2, "reason": "the fixture is shared"})
        self.assertEqual(items[obsolete]["history"][-1], {"state": "obsolete", "date": D2, "reason": "test b is gone"})

    def test_a_deleted_files_items_become_obsolete(self):
        found = self.run_record(self.plain, ["t.py", "u.py"], [item("u.py", ["x"]), item("t.py", ["y"])])
        (self.plain / "u.py").unlink()
        self.assertEqual(self.states(self.changes(self.plain, ["t.py"]))["u.py"], "deleted")
        result = self.run_record(self.plain, ["t.py"], [item("t.py", ["y"])], deleted=["u.py"], date=D2)
        self.assertEqual(result["obsoleted"], [self.key(found, 0)])
        record = self.record(self.plain)
        self.assertNotIn("u.py", record["files"])
        gone = record["items"][self.key(found, 0)]
        self.assertEqual((gone["state"], gone["obsolete"]["evidence"]), ("obsolete", "u.py was deleted"))

    def test_unmatched_items_are_returned_then_classified(self):
        found = self.run_record(self.plain, ["t.py", "u.py"],
                                [item("t.py", ["a"]), item("t.py", ["b"]), item("u.py", ["c"]),
                                 item("cfg.ini", setting="workers", section="run-configuration-resource-risk")])
        keys = [entry["key"] for entry in found["found"]]
        self.decide(self.plain, [{"key": keys[1], "state": "declined", "reason": "not now"}])
        again = self.run_record(self.plain, ["t.py"], [item("t.py", ["a"])], date=D2)
        self.assertEqual({entry["file"]: [(i["key"], i["state"]) for i in entry["items"]]
                          for entry in again["not_found"]},
                         {"t.py": [(keys[1], "declined")], "cfg.ini": [(keys[3], "undecided")]})
        classified = self.classify(self.plain, [
            {"key": keys[1], "state": "landed", "evidence": "the change is in t.py", "date": D3},
            {"key": keys[3], "state": "unchanged"}])
        self.assertEqual(classified["items"], [{"key": keys[1], "state": "landed"},
                                               {"key": keys[3], "state": "undecided"}])
        items = self.record(self.plain)["items"]
        self.assertEqual(items[keys[1]]["landed"], {"date": D3, "evidence": "the change is in t.py"})
        self.assertEqual(items[keys[2]]["state"], "undecided")

    def test_decide_sets_state_date_reason_and_content_hash(self):
        found = self.run_record(self.plain, ["t.py"], [item("t.py", ["a"]), item("t.py", ["b"])])
        decided = self.decide(self.plain, [
            {"key": self.key(found, 0), "state": "picked", "reason": "worth it", "date": D2},
            {"key": self.key(found, 1), "state": "declined", "reason": "too risky", "date": D2}])
        content = self.changes(self.plain, ["t.py"])["files"][0]["content_hash"]
        self.assertEqual([(entry["state"], entry["decision"]) for entry in decided["items"]],
                         [("picked", {"date": D2, "reason": "worth it", "content_hash": content}),
                          ("declined", {"date": D2, "reason": "too risky", "content_hash": content})])
        self.write(self.plain, "t.py", "t changed\n")
        again = self.run_record(self.plain, ["t.py"], [item("t.py", ["b"])], date=D3)
        self.assertEqual((again["found"][0]["state"], again["found"][0]["decided_file_changed"]), ("declined", True))

    def test_an_unknown_key_is_refused_and_nothing_written(self):
        self.run_record(self.plain, ["t.py"], [item("t.py", ["a"])])
        version = self.version(self.plain)
        failed = self.decide(self.plain, [{"key": "nope", "state": "picked", "reason": "r"}], expected=2)
        self.assertEqual(failed["code"], "unknown-item", failed)
        self.assertEqual(self.version(self.plain), version)


class StaleVersionTest(SpeedupBase):
    def test_every_writing_command_returns_changed_on_a_stale_version(self):
        self.write(self.plain, "t.py", "t\n")
        found = self.run_record(self.plain, ["t.py"], [item("t.py", ["a"])])
        key = found["found"][0]["key"]
        stale = self.version(self.plain)
        added = self.measure(self.plain, {"t::a": 1.0}, version=stale)
        current = added["version"]
        self.assertNotEqual(current, stale)
        record_before = (self.plain / ".feather" / "test-speedup" / "record.json").read_bytes()
        writes = {
            "record-run": ({"scope": ["."], "commit": None, "full": False, "files": [{"path": "t.py"}]}, ()),
            "classify": ({"items": [{"key": key, "state": "obsolete", "evidence": "e"}]}, ()),
            "decide": ({"items": [{"key": key, "state": "picked", "reason": "r"}]}, ()),
            "measure": ({"commit": None, "key": KEY, "succeeded": True, "total_seconds": 1, "tests": {}}, ()),
            "prune": (None, ("--obsolete",)),
        }
        for command, (payload, extra) in writes.items():
            with self.subTest(command=command, after="a measurement was added"):
                result = self.tool(self.plain, command, *extra, "--version", stale, payload=payload)
                self.assertEqual((result["status"], result["version"]), ("changed", current), result)
        self.assertEqual((self.plain / ".feather" / "test-speedup" / "record.json").read_bytes(), record_before)
        self.assertEqual(len(self.tool(self.plain, "read")["measurements"]), 1)
        removed = self.tool(self.plain, "prune", "--keep-measurements", "0", "--version", current)
        self.assertEqual(removed["removed"]["measurements"], [added["measurement"]])
        for command, (payload, extra) in writes.items():
            with self.subTest(command=command, after="a measurement was removed"):
                result = self.tool(self.plain, command, *extra, "--version", current, payload=payload)
                self.assertEqual((result["status"], result["version"]), ("changed", removed["version"]), result)


class MeasureTest(SpeedupBase):
    def test_equal_keys_are_compared(self):
        self.measure(self.plain, {"a": 1.0, "b": 2.0, "old": 1.0}, date=D1)
        result = self.measure(self.plain, {"a": 3.0, "b": 1.0, "new": 1.0}, date=D2)
        comparison = result["comparison"]
        self.assertTrue(comparison["available"], comparison)
        self.assertEqual(comparison["total"], {"before": 4.0, "after": 5.0, "seconds": 1.0, "factor": 1.25})
        self.assertEqual(comparison["rose"], [{"test": "a", "before": 1.0, "after": 3.0, "seconds": 2.0,
                                               "factor": 3.0}])
        self.assertEqual(comparison["fell"], [{"test": "b", "before": 2.0, "after": 1.0, "seconds": -1.0,
                                               "factor": 0.5}])
        self.assertEqual((comparison["only_before"], comparison["only_after"]), (["old"], ["new"]))

    def test_unequal_keys_or_a_failed_run_are_not_compared(self):
        first = self.measure(self.plain, {"a": 1.0}, date=D1)
        self.assertFalse(first["comparison"]["available"])
        other = self.measure(self.plain, {"a": 2.0}, date=D2, key={**KEY, "concurrency": 4})
        self.assertFalse(other["comparison"]["available"], other)
        failed = self.measure(self.plain, {"a": 2.0}, date=D3, succeeded=False)
        self.assertFalse(failed["comparison"]["available"], failed)
        after_failure = self.measure(self.plain, {"a": 2.0}, date=D4)
        self.assertEqual(after_failure["comparison"]["against"]["measurement"], first["measurement"])

    def test_the_top_ten_each_way_with_ties_and_a_zero_earlier_time(self):
        rising = {f"r{n:02}": 1.0 for n in range(12)}
        falling = {f"f{n:02}": 10.0 for n in range(12)}
        before = {**rising, **falling, "zero": 0.0}
        after = {**{name: 1.0 + n for n, name in enumerate(sorted(rising))},
                 **{name: 10.0 - n * 0.5 for n, name in enumerate(sorted(falling))}, "zero": 30.0}
        after["r00"] = after["r11"]  # r00 ties with r11; the tie goes to the lower test id
        self.measure(self.plain, before, date=D1)
        comparison = self.measure(self.plain, after, date=D2)["comparison"]
        self.assertEqual([entry["test"] for entry in comparison["rose"]],
                         ["zero", "r00", "r11", "r10", "r09", "r08", "r07", "r06", "r05", "r04"])
        self.assertIsNone(comparison["rose"][0]["factor"])
        self.assertEqual([entry["test"] for entry in comparison["fell"]],
                         ["f11", "f10", "f09", "f08", "f07", "f06", "f05", "f04", "f03", "f02"])

    def test_a_landed_items_times_before_and_after_its_landing(self):
        self.write(self.plain, "t.py", "t\n")
        found = self.run_record(self.plain, ["t.py"], [item("t.py", ["t::a"]), item("t.py", ["t::b"])])
        early, late = found["found"][0]["key"], found["found"][1]["key"]
        before = self.measure(self.plain, {"t::a": 5.0, "t::b": 5.0}, date=D1)
        self.classify(self.plain, [{"key": early, "state": "landed", "evidence": "e", "date": D2},
                                   {"key": late, "state": "landed", "evidence": "e", "date": D4}])
        after = self.measure(self.plain, {"t::a": 1.0, "t::b": 5.0}, date=D3)
        landed = {entry["key"]: entry for entry in after["landed"]}
        self.assertEqual(landed[early]["before"], {"state": "available", "measurement": before["measurement"],
                                                   "date": D1, "times": {"t::a": 5.0}})
        self.assertEqual(landed[early]["after"], {"state": "available", "measurement": after["measurement"],
                                                  "date": D3, "times": {"t::a": 1.0}})
        self.assertEqual(landed[late]["after"], {"state": "unavailable"})
        self.assertEqual(landed[late]["before"]["measurement"], after["measurement"])
        # A measurement dated at the landing date itself is the first one after it.
        at = self.measure(self.plain, {"t::a": 1.0, "t::b": 2.0}, date=D4)
        late_entry = {entry["key"]: entry for entry in at["landed"]}[late]
        self.assertEqual((late_entry["before"]["measurement"], late_entry["after"]["measurement"]),
                         (after["measurement"], at["measurement"]))


class VersionsTest(SpeedupBase):
    def test_versions_are_read_from_each_kind_of_source_or_unknown(self):
        self.write(self.plain, "node_modules/vitest/package.json", json.dumps({"name": "vitest", "version": "2.1.8"}))
        self.write(self.plain, "venv/lib/pytest-8.3.4.dist-info/METADATA",
                   "Metadata-Version: 2.1\nName: pytest\nVersion: 8.3.4\n\nbody\n")
        self.write(self.plain, "venv/lib/xdist.dist-info/METADATA", "Name: pytest-xdist\nVersion: 3.6.1\n")
        self.write(self.plain, "go.mod", "module x\n\ngo 1.22.1 // declared\n\ntoolchain go1.23.0\n")
        self.write(self.plain, ".python-version", "# pinned\n3.12.7\n")
        self.write(self.plain, "venv/pyvenv.cfg", "home = /usr/bin\nversion = 3.11.9\n")
        self.write(self.plain, "uv/pyvenv.cfg", "home = /usr/bin\nversion_info = 3.13.0\n")
        self.write(self.plain, "jest/package.json", json.dumps({"name": "jest"}))
        sources = [{"name": "vitest", "source": "node_modules/vitest/package.json"},
                   {"name": "pytest", "source": "venv/lib/pytest-8.3.4.dist-info"},
                   {"name": "pytest-xdist", "source": "venv/lib/xdist.dist-info/METADATA"},
                   {"name": "go", "source": "go.mod"},
                   {"name": "go toolchain", "source": "go.mod", "line": "toolchain"},
                   {"name": "python", "source": ".python-version"},
                   {"name": "venv", "source": str(self.plain / "venv" / "pyvenv.cfg")},
                   {"name": "uv", "source": "uv/pyvenv.cfg"},
                   {"name": "jest", "source": "jest/package.json"},
                   {"name": "mocha", "source": "node_modules/mocha/package.json"},
                   {"name": "other", "source": "setup.cfg"},
                   {"name": "none", "source": None}]
        result = self.changes(self.plain, [], versions=sources)["versions"]["now"]
        self.assertEqual([(entry["name"], entry["state"], entry["version"]) for entry in result],
                         [("vitest", "read", "2.1.8"), ("pytest", "read", "8.3.4"), ("pytest-xdist", "read", "3.6.1"),
                          ("go", "read", "1.22.1"), ("go toolchain", "read", "go1.23.0"),
                          ("python", "read", "3.12.7"), ("venv", "read", "3.11.9"), ("uv", "read", "3.13.0"),
                          ("jest", "unknown", None), ("mocha", "unknown", None), ("other", "unknown", None),
                          ("none", "unknown", None)])
        self.assertTrue(all(entry["reason"] for entry in result if entry["state"] == "unknown"))

    def test_the_versions_read_now_are_reported_beside_the_last_runs(self):
        self.write(self.plain, "go.mod", "module x\ngo 1.22\n")
        source = [{"name": "go", "source": "go.mod"}]
        self.run_record(self.plain, versions=source)
        self.assertEqual(self.record(self.plain)["runs"][0]["versions"][0]["version"], "1.22")
        self.write(self.plain, "go.mod", "module x\ngo 1.23\n")
        versions = self.changes(self.plain, [], versions=source)["versions"]
        self.assertEqual(versions["changed"], [{"name": "go", "last_run": "1.22", "now": "1.23"}])


class ShowTest(SpeedupBase):
    def test_show_without_a_record_lists_the_forms_and_creates_nothing(self):
        for form in ((), ("items",), ("runs",)):
            with self.subTest(form=form):
                result = self.tool(self.main, "show", *form)
                self.assertEqual((result["present"], result["version"]), (False, "absent"), result)
                self.assertIn("show runs", result["forms"])
        self.assertFalse((self.main / ".feather").exists())

    def test_show_summarises_lists_items_and_runs_and_changes_nothing(self):
        self.write(self.plain, "t.py", "t\n")
        self.write(self.plain, "u.py", "u\n")
        found = self.run_record(self.plain, ["t.py", "u.py"], [item("t.py", ["a"]), item("t.py", ["b"])], date=D1)
        self.decide(self.plain, [{"key": found["found"][1]["key"], "state": "declined", "reason": "no"}])
        measured = self.measure(self.plain, {"a": 1.0}, date=D2)
        self.write(self.plain, "u.py", "u changed\n")
        before = self.tree(self.plain)
        summary = self.tool(self.plain, "show")
        self.assertEqual(summary["last_analysis"], {"date": D1, "commit": None})
        self.assertEqual(summary["items_by_state"],
                         {"undecided": 1, "picked": 0, "declined": 1, "landed": 0, "obsolete": 0})
        self.assertEqual((summary["last_measurement"]["measurement"], summary["last_measurement"]["total_seconds"],
                          summary["last_measurement"]["key"]), (measured["measurement"], 1.0, KEY))
        self.assertEqual(summary["files_changed"], 1)
        self.assertIn("show items [undecided|picked|declined|landed|obsolete]", summary["forms"])
        declined = self.tool(self.plain, "show", "items", "declined")["items"]
        self.assertEqual([entry["key"] for entry in declined], [found["found"][1]["key"]])
        self.assertEqual(len(self.tool(self.plain, "show", "items")["items"]), 2)
        runs = self.tool(self.plain, "show", "runs")
        self.assertEqual(([run["date"] for run in runs["runs"]], [m["measurement"] for m in runs["measurements"]]),
                         ([D1], [measured["measurement"]]))
        self.assertEqual(self.tool(self.plain, "show", "items", "nope", expected=2)["code"], "usage")
        self.assertEqual(self.tree(self.plain), before)


class PruneTest(SpeedupBase):
    def setUp(self):
        super().setUp()
        self.write(self.plain, "t.py", "t\n")
        found = self.run_record(self.plain, ["t.py"], [item("t.py", [name]) for name in "abcdef"])
        self.keys = dict(zip("abcdef", (entry["key"] for entry in found["found"])))
        k = self.keys
        self.classify(self.plain, [{"key": k["a"], "state": "landed", "evidence": "e", "date": D1},
                                   {"key": k["b"], "state": "landed", "evidence": "e", "date": D3},
                                   {"key": k["c"], "state": "obsolete", "evidence": "e", "date": D1},
                                   {"key": k["f"], "state": "landed", "evidence": "e", "date": D1}])
        self.decide(self.plain, [{"key": k["d"], "state": "picked", "reason": "r"},
                                 {"key": k["e"], "state": "declined", "reason": "r"}])
        self.run_record(self.plain, ["t.py"], [item("t.py", ["f"])], date=D2)  # f reopened: undecided again
        self.measurements = [self.measure(self.plain, {"x": 1.0}, date=date)["measurement"] for date in (D1, D2, D3)]

    def test_the_dry_run_lists_and_the_removal_removes_exactly_that(self):
        dry = self.tool(self.plain, "prune", "--obsolete", "--landed-before", D2, "--measurements-before", D2)
        self.assertTrue(dry["dry_run"])
        self.assertEqual(dry["remove"], {"items": sorted([self.keys["a"], self.keys["c"]]),
                                         "measurements": [self.measurements[0]]})
        self.assertEqual(self.version(self.plain), dry["version"])
        removed = self.tool(self.plain, "prune", "--obsolete", "--landed-before", D2, "--measurements-before", D2,
                            "--version", dry["version"])
        self.assertEqual(removed["removed"], dry["remove"])
        read = self.tool(self.plain, "read")
        self.assertEqual(sorted(read["record"]["items"]), sorted(self.keys[name] for name in "bdef"))
        self.assertEqual(read["measurements"], sorted(self.measurements[1:]))

    def test_all_but_the_last_measurements_by_date(self):
        dry = self.tool(self.plain, "prune", "--keep-measurements", "1")
        self.assertEqual(dry["remove"], {"items": [], "measurements": sorted(self.measurements[:2])})

    def test_undecided_picked_and_declined_items_are_never_selected(self):
        dry = self.tool(self.plain, "prune", "--obsolete", "--landed-before", "2099-01-01")
        self.assertEqual(dry["remove"]["items"], sorted([self.keys["a"], self.keys["b"], self.keys["c"]]))
        self.assertEqual(self.tool(self.plain, "prune", expected=2)["code"], "usage")

    def test_a_concurrent_write_makes_the_removal_return_changed(self):
        dry = self.tool(self.plain, "prune", "--obsolete")
        self.decide(self.plain, [{"key": self.keys["f"], "state": "declined", "reason": "later"}])
        result = self.tool(self.plain, "prune", "--obsolete", "--version", dry["version"])
        self.assertEqual(result["status"], "changed", result)
        self.assertIn(self.keys["c"], self.record(self.plain)["items"])


class InputTest(SpeedupBase):
    def test_malformed_input_is_a_json_error_with_exit_code_two(self):
        cases = {
            "not JSON": (("changes",), b"{not json"),
            "a duplicate JSON key": (("changes",), b'{"scope": ["."], "scope": ["a"]}'),
            "not an object": (("changes",), b"[1]"),
            "no scope": (("changes",), b'{"files": []}'),
            "a path leaving the project": (("changes",), b'{"scope": [".."], "files": []}'),
            "a bad section": (("record-run", "--version", "absent"),
                              b'{"scope": ["."], "full": false, "items": [{"section": "x", "file": "t.py", '
                              b'"tests": ["a"], "description": "d"}]}'),
            "a bad version token": (("decide", "--version", "nope"), b'{"items": []}'),
            "an unknown command": (("reset",), b""),
            "a missing --version": (("measure",), b"{}"),
        }
        for name, (args, raw) in cases.items():
            with self.subTest(case=name):
                result = self.tool(self.plain, *args, raw=raw, expected=2)
                self.assertEqual(result["status"], "error", result)
                self.assertIn(result["code"], ("input", "usage"), result)
        self.assertFalse((self.plain / ".feather").exists())


class LauncherTest(SpeedupBase):
    def test_the_launcher_runs_the_entry_point(self):
        result = self.tool(self.main, "read", process=True)
        self.assertEqual((result["status"], result["version"]), ("ok", "absent"), result)

    def test_an_unsupported_python_is_a_json_error(self):
        code = ("import runpy, sys; sys.version_info = (3, 10, 0); sys.argv = [sys.argv[1], 'read']; "
                "runpy.run_path(sys.argv[0], run_name='__main__')")
        result = subprocess.run([sys.executable, "-B", "-c", code, str(TOOL)], capture_output=True, timeout=TIMEOUT)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(json.loads(result.stdout.decode("utf-8"))["code"], "python-version")

    def test_the_environment_cannot_redirect_or_misplace_the_record(self):
        self.write(self.wt1, "t.py", "t\n")
        payload = {"scope": ["."], "commit": None, "full": False, "files": [{"path": "t.py"}]}
        redirected = {**os.environ, "GIT_DIR": str(self.wt2 / ".git"), "GIT_WORK_TREE": str(self.outside)}
        result = self.tool(self.wt1, "record-run", "--version", "absent", payload=payload, env=redirected)
        self.assertEqual(os.path.normcase(result["location"]), os.path.normcase(str(self.record_dir)), result)
        self.assertEqual(os.path.normcase(result["project"]), os.path.normcase(str(self.wt1)))
        no_git = {**os.environ, "PATH": str(self.outside)}
        before = self.tree()
        failed = self.tool(self.wt1, "record-run", "--version", result["version"], payload=payload, env=no_git,
                           expected=2)
        self.assertEqual(failed["status"], "error", failed)
        self.assertEqual(self.changed(before, self.tree()), set())


if __name__ == "__main__":
    unittest.main()
