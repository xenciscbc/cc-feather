"""Linked worktrees share the main worktree's Handoff store (worktree store ticket 02).

Trust boundary: the project's files, its Git metadata (worktree list, Git and common directories, configuration,
index) and the paths supplied to --project against the handoff tool's process. From an untracked linked worktree the
tool writes records outside the Working checkout, in a store under the repository's main worktree that it derives
from Git metadata; the main worktree is accepted only after strict checks of Git's output and of filesystem
identities, the store is pinned to the main worktree's strict real path and passes the existing link, reparse-point
and hard-link checks, and any failure leaves the root uncertain: reads are partial, every mutation is refused, and
nothing is written in the linked worktree in the store's place.

Tests run under a unique directory made with mkdtemp under FEATHER_LINK_TEST_DIR when it is set, otherwise the system
temporary directory, with an isolated Git environment (GIT_CONFIG_NOSYSTEM, an empty GIT_CONFIG_GLOBAL, HOME and
XDG_CONFIG_HOME inside the base, inherited GIT_* removed) and synthetic data only. The base holds main/ with one
commit, linked worktrees wt1 and wt2 added from it and an empty outside/ sentinel, and is removed on cleanup. The
tool runs as a subprocess with --project; in-process cases drive the CLI entry point or a mutation's public operation,
never the resolver or path helpers."""
import contextlib
import errno
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/handoff/scripts"
TOOL = SCRIPTS / "handoff.py"
SKILL = ROOT / "skills/handoff/SKILL.md"
TOOL_REFERENCE = ROOT / "skills/handoff/references/tool.md"
sys.path.insert(0, str(SCRIPTS))

from feather_handoff import cli, storage  # noqa: E402
from feather_handoff.writing import create_work  # noqa: E402
from tests import feather_support  # noqa: E402

FIELDS = {"goal": "g", "progress": "p", "next": "n", "updated": "2026-11-05T10:00:00+08:00"}
COMMIT_ENV = {"GIT_AUTHOR_NAME": "Fixture", "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
              "GIT_COMMITTER_NAME": "Fixture", "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
              "GIT_AUTHOR_DATE": "2026-11-05T10:00:00+08:00", "GIT_COMMITTER_DATE": "2026-11-05T10:00:00+08:00"}
# Commands of the tool that can read objects, which only run after the lazy-fetch guard in their directory.
OBJECT_READS = {"ls-files", "check-ignore", "show-ref"}
MARKER = "# cc-feather: track /.feather/handoffs/"
STRICT_REALPATH = "strict realpath unsupported on this volume; set FEATHER_LINK_TEST_DIR to a volume that supports it"
DISCOVERY_FAILED = "Handoff store discovery failed"


def is_directory_link(path: Path) -> bool:
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & 0x400)


def remove_base(base: Path) -> None:
    """Unlink every directory link first so removal never reaches through one, then remove the tree, clearing the
    read-only attribute Git gives its object files on Windows."""
    for current, directories, _ in os.walk(base):
        for name in list(directories):
            if is_directory_link(Path(current) / name):
                feather_support.remove_directory_link(Path(current) / name)
                directories.remove(name)

    def writable(function, path, *_):
        os.chmod(path, stat.S_IREAD | stat.S_IWRITE)
        function(path)
    if sys.version_info >= (3, 12):
        shutil.rmtree(base, onexc=writable)
    else:
        shutil.rmtree(base, onerror=writable)


def git_call(args: list[str]) -> tuple[str, list[str], bool]:
    """(the -C directory, the Git command after it, whether --no-lazy-fetch was passed) of one recorded start."""
    index = args.index("-C")
    return args[index + 1], args[index + 2:], "--no-lazy-fetch" in args[:index]


class SharedBase(unittest.TestCase):
    def setUp(self):
        configured = os.environ.get("FEATHER_LINK_TEST_DIR")
        if configured:
            os.makedirs(configured, exist_ok=True)
        base = tempfile.mkdtemp(dir=configured or None)
        self.addCleanup(remove_base, Path(base))
        try:
            self.base = Path(os.path.realpath(base, strict=True))
        except OSError:
            self.skipTest(STRICT_REALPATH)
        self.outside = self.base / "outside"
        self.outside.mkdir()
        (self.base / "home").mkdir()
        empty = self.base / "gitconfig"
        empty.write_bytes(b"")
        environment = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
        environment.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": str(empty),
                            "HOME": str(self.base / "home"), "XDG_CONFIG_HOME": str(self.base / "home")})
        self.enterContext(mock.patch.dict(os.environ, environment, clear=True))
        self.addCleanup(storage.reset_roots)
        self.main = self.repository("main", b"main\n")
        self.wt1, self.wt2 = self.base / "wt1", self.base / "wt2"
        self.git(self.main, "worktree", "add", "--quiet", str(self.wt1))
        self.git(self.main, "worktree", "add", "--quiet", str(self.wt2))
        self.store = self.main / ".feather" / "handoffs"

    def git(self, cwd: Path, *args: str) -> str:
        try:
            result = subprocess.run(["git", "-c", "core.fsmonitor=", *args], cwd=cwd, env={**os.environ, **COMMIT_ENV},
                                    stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired) as error:
            self.skipTest(f"Git cannot be run: {error}")
        self.assertEqual(result.returncode, 0, (args, result.stderr))
        return result.stdout.strip()

    def repository(self, name: str, source: bytes = b"a\n", path: Path | None = None) -> Path:
        """A repository with one commit holding a.txt."""
        path = path or self.base / name
        path.mkdir(parents=True, exist_ok=True)
        self.git(path, "init", "--quiet", "--initial-branch=main", ".")
        self.git(path, "config", "core.autocrlf", "false")
        (path / "a.txt").write_bytes(source)
        self.commit(path)
        return path

    def commit(self, path: Path, message: str = "fixture"):
        self.git(path, "add", "--all")
        self.git(path, "-c", "commit.gpgSign=false", "commit", "--quiet", "--no-verify", "-m", message)

    def run_tool(self, project: Path, *args, payload=None, expected=0, exact=False) -> dict:
        result = subprocess.run(
            [sys.executable, "-B", str(TOOL), "--project", str(project), *(["--exact-root"] if exact else []), *args],
            input=json.dumps(payload, ensure_ascii=False) if payload is not None else None,
            capture_output=True, text=True, encoding="utf-8", timeout=60)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def invoke(self, project: Path, *args, payload=None) -> tuple[int, dict]:
        """The CLI entry point in this process, starting like a fresh tool process with no registered root."""
        storage.reset_roots()
        output = io.StringIO()
        with mock.patch.object(sys, "argv", ["handoff", "--project", str(project), *args]), \
                mock.patch.object(cli, "input_payload", return_value=payload), contextlib.redirect_stdout(output):
            code = cli.main()
        return code, json.loads(output.getvalue())

    def tree(self, path: Path | None = None) -> dict:
        """Every file below path (default: the whole base, Git directories included), not following directory links."""
        top = path or self.base
        result = {}
        for directory, directories, files in os.walk(top):
            directories[:] = [name for name in directories if not is_directory_link(Path(directory, name))]
            for name in files:
                item = Path(directory, name)
                result[item.relative_to(top).as_posix()] = item.read_bytes()
        return result

    def changed(self, before: dict, after: dict) -> set[str]:
        return {name for name in before.keys() | after.keys() if before.get(name) != after.get(name)}

    def shared_root(self, requested: Path, checkout: Path | None = None) -> dict:
        checkout = checkout or requested
        return {"requested": str(requested), "path": str(self.main), "state": "git", "tracking": "untracked",
                "checkout": str(checkout), "store": str(self.main), "shared": True}

    @contextlib.contextmanager
    def git_as(self, version: str | None = None, override=None):
        """Record the tool's Git starts and pass them to the real Git, as the existing fake Git records them.

        version answers `git version` with a chosen release; --no-lazy-fetch is then recorded and removed before the
        real Git runs, so an older installed Git can stand in for a newer one. override(directory, command) may
        return (exit code, stdout, stderr) to replace one command's answer, or raise to simulate a failed start."""
        calls: list[list[str]] = []
        real = subprocess.run

        def run(args, **kwargs):
            args = list(args)
            calls.append(args)
            directory, command, flagged = git_call(args)
            answer = override(directory, command) if override else None
            if answer is not None:
                return subprocess.CompletedProcess(args, *answer)
            if version is not None:
                if command == ["version"]:
                    return subprocess.CompletedProcess(args, 0, version + "\n", "")
                if flagged:
                    return real([item for item in args if item != "--no-lazy-fetch"], **kwargs)
            return real(args, **kwargs)
        with mock.patch.object(storage.subprocess, "run", side_effect=run):
            yield calls

    def assert_guarded(self, calls: list[list[str]]):
        """S02-4: an object-reading command runs only after the lazy-fetch guard ran in its own -C directory."""
        guarded = set()
        for args in calls:
            directory, command, _ = git_call(args)
            if command[:2] == ["config", "--list"]:
                guarded.add(directory)
            elif command[0] in OBJECT_READS:
                self.assertIn(directory, guarded, f"{command} ran in {directory} before its lazy-fetch guard")

    def assert_uncertain(self, project: Path, reason: str, *, subprocess_run=True, context=None) -> dict:
        """The root is uncertain with a reason naming what failed; the read is partial over the Working checkout's
        own records, and every mutation is refused before anything is written."""
        before = self.tree()
        with context or contextlib.nullcontext():
            if subprocess_run:
                listed = self.run_tool(project, "list", expected=2)
                refused = self.run_tool(project, "create", "--work", "w.md", payload={"title": "w", "fields": FIELDS},
                                        expected=2)
            else:
                _, listed = self.invoke(project, "list")
                _, refused = self.invoke(project, "create", "--work", "w.md",
                                         payload={"title": "w", "fields": FIELDS})
        self.assertEqual((listed["status"], listed["complete"]), ("partial", False), listed)
        root = listed["root"]
        self.assertEqual(root["state"], "uncertain", root)
        self.assertIn(DISCOVERY_FAILED, root["reason"])
        self.assertIn(reason, root["reason"])
        self.assertEqual((root["path"], root["store"], root["shared"]), (root["checkout"], root["checkout"], False))
        self.assertEqual(refused["code"], "project-root-uncertain", refused)
        self.assertEqual(self.tree(), before)
        return listed


class StoreSelectionTest(SharedBase):
    """Acceptance 1 and 3, item 6: store selection for the main worktree, an untracked linked worktree, a non-Git
    project, --exact-root and tracked mode; root reports checkout, store, shared and the linked worktree's tracking."""

    def test_an_untracked_linked_worktree_uses_the_main_worktrees_store(self):
        before = self.tree()
        listed = self.run_tool(self.wt1, "list")
        self.assertEqual((listed["status"], listed["root"]), ("missing", self.shared_root(self.wt1)), listed)
        created = self.run_tool(self.wt1, "create", "--work", "w.md", payload={"title": "w", "fields": FIELDS})
        self.assertEqual((created["status"], created["tracking"], created["root"]),
                         ("ok", "ignored", self.shared_root(self.wt1)), created)
        # S02-5: the store and the main worktree's .gitignore are the only paths written.
        self.assertEqual(self.changed(before, self.tree()), {"main/.feather/handoffs/w.md", "main/.gitignore"})
        self.assertEqual((self.main / ".gitignore").read_text(encoding="utf-8"), "/.feather/handoffs/\n")
        for project in (self.wt2, self.main):
            with self.subTest(project=project.name):
                listed = self.run_tool(project, "list")
                self.assertEqual([item["work"] for item in listed["items"]], ["w.md"], listed)
        self.assertFalse((self.wt1 / ".feather").exists())
        self.assertFalse((self.wt1 / ".gitignore").exists())

    def test_a_subdirectory_of_a_linked_worktree_uses_the_main_worktrees_store(self):
        nested = self.wt1 / "a" / "b"
        nested.mkdir(parents=True)
        created = self.run_tool(nested, "create", "--work", "w.md", payload={"title": "w", "fields": FIELDS})
        self.assertEqual(created["root"], self.shared_root(nested, self.wt1), created)
        self.assertTrue((self.store / "w.md").is_file())

    def test_the_main_worktree_keeps_its_own_store(self):
        created = self.run_tool(self.main, "create", "--work", "w.md", payload={"title": "w", "fields": FIELDS})
        self.assertEqual(created["root"], {"requested": str(self.main), "path": str(self.main), "state": "git",
                                           "checkout": str(self.main), "store": str(self.main), "shared": False})
        self.assertTrue((self.store / "w.md").is_file())

    def test_a_non_git_project_keeps_its_own_store(self):
        project = self.base / "plain"
        project.mkdir()
        created = self.run_tool(project, "create", "--work", "w.md", payload={"title": "w", "fields": FIELDS})
        self.assertEqual({key: created["root"][key] for key in ("state", "path", "store", "shared")},
                         {"state": "non-git", "path": str(project), "store": str(project), "shared": False})
        self.assertTrue((project / ".feather/handoffs/w.md").is_file())

    def test_an_exact_root_in_a_linked_worktree_is_used_literally(self):
        before = self.tree(self.main)
        created = self.run_tool(self.wt1, "create", "--work", "w.md", payload={"title": "w", "fields": FIELDS},
                                exact=True)
        self.assertEqual(created["root"], {"requested": str(self.wt1), "path": str(self.wt1), "state": "explicit",
                                           "checkout": str(self.wt1), "store": str(self.wt1), "shared": False})
        self.assertTrue((self.wt1 / ".feather/handoffs/w.md").is_file())
        self.assertEqual(self.tree(self.main), before)

    def assert_checkout_local(self, project: Path):
        before = self.tree(self.main)
        created = self.run_tool(project, "create", "--work", "w.md", payload={"title": "w", "fields": FIELDS})
        self.assertEqual(created["root"], {"requested": str(project), "path": str(project), "state": "git",
                                           "tracking": "tracked", "checkout": str(project), "store": str(project),
                                           "shared": False}, created)
        self.assertTrue((project / ".feather/handoffs/w.md").is_file())
        self.assertEqual(self.tree(self.main), before)

    def test_the_track_marker_in_the_linked_worktree_keeps_its_store_local(self):
        (self.wt1 / ".gitignore").write_text(MARKER + "\n", encoding="utf-8")
        self.assert_checkout_local(self.wt1)

    def test_tracked_records_in_the_linked_worktrees_index_keep_its_store_local(self):
        (self.wt1 / ".feather/handoffs").mkdir(parents=True)
        (self.wt1 / ".feather/handoffs/old.md").write_text("# old\n", encoding="utf-8")
        self.git(self.wt1, "add", "--force", "--", ".feather/handoffs/old.md")
        self.assert_checkout_local(self.wt1)

    def test_tracking_is_detected_in_the_working_checkout_not_in_the_store(self):
        # The main worktree tracks its records; that is no tracking state of the linked worktree.
        (self.main / ".gitignore").write_text(MARKER + "\n", encoding="utf-8")
        listed = self.run_tool(self.wt1, "list")
        self.assertEqual(listed["root"], self.shared_root(self.wt1), listed)
        created = self.run_tool(self.wt1, "create", "--work", "w.md", payload={"title": "w", "fields": FIELDS})
        self.assertEqual((created["tracking"], created["root"]["shared"]), ("existing-rule", True), created)
        self.assertEqual((self.main / ".gitignore").read_text(encoding="utf-8"), MARKER + "\n")


class LinkedOperationsTest(SharedBase):
    """Acceptance 1 and 6, S02-5 and S02-6: list, read, create, update, archive, clear and seal from linked worktrees
    land in one store under the main worktree, and nothing is written in a Working checkout."""

    def test_every_operation_lands_in_the_main_worktrees_store(self):
        before = self.tree()
        created = self.run_tool(self.wt1, "create", "--work", "a.md", payload={"title": "a", "fields": FIELDS})
        read = self.run_tool(self.wt2, "read", "--work", "a.md")
        self.assertEqual(read["version"], created["version"])
        updated = self.run_tool(self.wt2, "update", "--work", "a.md",
                                payload={"version": read["version"], "fields": {"next": "m"}})
        done = self.run_tool(self.wt1, "update", "--work", "a.md", payload={
            "version": updated["version"], "fields": {"status": "完成", "updated": "2026-11-05T11:00:00+08:00"}})
        self.assertEqual((done["archived"], done["root"]["shared"]), (True, True), done)
        deferred = self.run_tool(self.wt2, "create", "--work", "b.md", expected=2, payload={
            "title": "b", "fields": {**FIELDS, "status": "完成"}, "defer_history": True})
        self.assertEqual(deferred["code"], "deferred", deferred)
        archived = self.run_tool(self.wt1, "archive", "--work", "b.md", payload={"version": deferred["version"]})
        self.assertEqual(archived["archived"], True, archived)
        for result in (done, archived):
            # S02-6: history.md and the work file are direct descendants of the one store directory.
            self.assertEqual((Path(result["history_path"]), Path(result["work_path"]).parent),
                             (self.store / "history.md", self.store), result)
        history = self.run_tool(self.wt2, "history")
        entries = {entry["title"]: entry for entry in history["entries"]}
        self.assertEqual(set(entries), {"a", "b"}, history)
        cleared = self.run_tool(self.wt1, "clear", payload={
            "source": "history.md", "version": history["documents"][0]["version"], "ids": [entries["b"]["id"]]})
        self.assertEqual(cleared["status"], "ok", cleared)
        history = self.run_tool(self.wt1, "history")
        self.assertEqual([entry["title"] for entry in history["entries"]], ["a"], history)
        sealed = self.run_tool(self.wt2, "seal", payload={
            "version": history["documents"][0]["version"], "ids": [history["entries"][0]["id"]],
            "destination": "batch.md"})
        self.assertEqual(Path(sealed["destination"]), self.store / "archive" / "batch.md", sealed)
        listed = self.run_tool(self.main, "list")
        self.assertEqual(listed["items"], [], listed)
        self.assertEqual(self.changed(before, self.tree()),
                         {"main/.gitignore", "main/.feather/handoffs/history.md",
                          "main/.feather/handoffs/archive/batch.md"})
        self.assertIn(b"## a", (self.store / "archive/batch.md").read_bytes())

    def test_a_missing_work_in_the_shared_store_is_not_found(self):
        missing = self.run_tool(self.wt1, "read", "--work", "absent.md", expected=2)
        self.assertEqual((missing["status"], missing["code"]), ("error", "not-found"), missing)
        self.assertTrue(missing["root"]["shared"])
        self.run_tool(self.wt1, "create", "--work", "w.md", payload={"title": "w", "fields": FIELDS})
        missing = self.run_tool(self.wt1, "archive", "--work", "absent.md", payload={"version": "0" * 64}, expected=2)
        self.assertEqual(missing["code"], "not-found", missing)

    def test_a_track_choice_in_a_shared_run_is_refused_without_writing(self):
        created = self.run_tool(self.wt1, "create", "--work", "w.md", payload={"title": "w", "fields": FIELDS})
        done = self.run_tool(self.wt1, "create", "--work", "d.md", expected=2, payload={
            "title": "d", "fields": {**FIELDS, "status": "完成"}, "defer_history": True})
        before = self.tree()
        attempts = {
            "create": ("create", "--work", "t.md", {"title": "t", "fields": FIELDS, "tracking": "track"}),
            "update": ("update", "--work", "w.md", {"version": created["version"], "tracking": "track",
                                                    "fields": {"next": "m"}}),
            "archive": ("archive", "--work", "d.md", {"version": done["version"], "tracking": "track"}),
        }
        for name, (*args, payload) in attempts.items():
            with self.subTest(operation=name):
                refused = self.run_tool(self.wt1, *args, payload=payload, expected=2)
                self.assertEqual((refused["status"], refused["code"]), ("error", "input"), refused)
                self.assertIn("tracking is chosen from the checkout whose records it should track",
                              refused["message"])
        self.assertEqual(self.tree(), before)
        # The same choice from the main worktree, whose records it tracks, is applied as before.
        tracked = self.run_tool(self.main, "update", "--work", "w.md",
                                payload={"version": created["version"], "tracking": "track"})
        self.assertEqual(tracked["tracking"], "track", tracked)


class ObservationsTest(SharedBase):
    """Acceptance 4 and S02-6: snapshot, compare and the save-time baseline check read the linked worktree's sources
    and Git state, whatever the main worktree holds."""

    def test_baselines_describe_the_linked_worktree_while_the_main_worktree_changes(self):
        (self.wt1 / "a.txt").write_bytes(b"wt1 change\n")
        snapshot = self.run_tool(self.wt1, "snapshot", payload={"paths": ["a.txt"]})
        self.assertEqual(snapshot["snapshot"]["files"][0]["sha256"], hashlib.sha256(b"wt1 change\n").hexdigest())
        self.assertEqual(snapshot["snapshot"]["git"]["branch"], "wt1")
        created = self.run_tool(self.wt1, "create", "--work", "w.md",
                                payload={"title": "w", "fields": FIELDS, "snapshot": snapshot["snapshot"]})
        self.assertEqual((created["status"], created["root"]["shared"]), ("ok", True), created)
        # Unrelated changes in the main worktree: its sources, a new file and a new commit on its branch.
        (self.main / "a.txt").write_bytes(b"main changed\n")
        (self.main / "new.txt").write_bytes(b"new\n")
        self.git(self.main, "add", "--", "a.txt", "new.txt")
        self.git(self.main, "-c", "commit.gpgSign=false", "commit", "--quiet", "--no-verify", "-m", "main moves")
        compared = self.run_tool(self.wt1, "compare", "--work", "w.md")
        self.assertEqual((compared["status"], [item["comparison"] for item in compared["files"]],
                          compared["git"]["comparison"]), ("ok", ["unchanged"], "unchanged"), compared)
        # The save-time check still reads the linked worktree.
        updated = self.run_tool(self.wt1, "update", "--work", "w.md", payload={
            "version": created["version"], "snapshot": snapshot["snapshot"], "fields": {"next": "m"}})
        self.assertEqual(updated["status"], "ok", updated)
        # A change in the linked worktree itself is reported.
        (self.wt1 / "a.txt").write_bytes(b"wt1 again\n")
        compared = self.run_tool(self.wt1, "compare", "--work", "w.md", expected=0)
        self.assertEqual([item["comparison"] for item in compared["files"]], ["changed"], compared)
        self.assertFalse((self.wt1 / ".feather").exists())


class DiscoveryFailureTest(SharedBase):
    """Acceptance 2, S02-1 and S02-2: a main worktree that cannot be accepted leaves the root uncertain with a
    reason, reads partial and every mutation refused, and nothing written anywhere."""

    def test_a_bare_first_entry_is_uncertain(self):
        bare = self.base / "bare.git"
        self.git(self.base, "clone", "--quiet", "--bare", str(self.main), str(bare))
        worktree = self.base / "bare-wt"
        self.git(bare, "worktree", "add", "--quiet", str(worktree), "main")
        self.assert_uncertain(worktree, "is bare")
        self.assertEqual([path.name for path in bare.rglob(".feather")], [])

    def test_a_separate_git_directory_is_uncertain_and_its_main_checkout_keeps_its_store(self):
        gitdir, checkout = self.base / "separate.git", self.base / "separate"
        self.git(self.base, "init", "--quiet", "--initial-branch=main", "--separate-git-dir", str(gitdir),
                 str(checkout))
        (checkout / "a.txt").write_bytes(b"a\n")
        self.commit(checkout)
        linked = self.base / "separate-wt"
        self.git(checkout, "worktree", "add", "--quiet", str(linked))
        self.assert_uncertain(linked, "is the repository's Git directory or inside it")
        self.assertEqual(list(gitdir.rglob(".feather")), [])
        # S02-1: the main checkout's Git directory is the common directory, so it is not linked and keeps its store.
        created = self.run_tool(checkout, "create", "--work", "w.md", payload={"title": "w", "fields": FIELDS})
        self.assertEqual(created["root"], {"requested": str(checkout), "path": str(checkout), "state": "git",
                                           "checkout": str(checkout), "store": str(checkout), "shared": False})
        self.assertTrue((checkout / ".feather/handoffs/w.md").is_file())
        self.assertEqual(list(gitdir.rglob(".feather")), [])

    def test_a_submodules_linked_worktree_is_uncertain(self):
        superproject = self.repository("super")
        self.git(superproject, "-c", "protocol.file.allow=always", "submodule", "add", "--quiet", str(self.main), "sub")
        self.commit(superproject, "submodule")
        linked = self.base / "sub-wt"
        self.git(superproject / "sub", "worktree", "add", "--quiet", str(linked))
        self.assert_uncertain(linked, "is the repository's Git directory or inside it")
        self.assertEqual(list((superproject / ".git" / "modules").rglob(".feather")), [])

    def assert_broken_linked_worktree(self):
        """A moved or deleted main worktree breaks the linked worktree itself: the Working checkout's own root
        discovery fails with Git's error as the reason, before any store discovery; reads are partial, mutations
        are refused and the old main worktree path is not recreated."""
        listed = self.run_tool(self.wt1, "list", expected=2)
        root = listed["root"]
        self.assertEqual((listed["status"], root["state"], root["store"], root["shared"]),
                         ("partial", "uncertain", str(self.wt1), False), listed)
        self.assertIn("not a git repository", root["reason"].lower(), root)
        self.assertNotIn(DISCOVERY_FAILED, root["reason"], root)
        refused = self.run_tool(self.wt1, "create", "--work", "w.md", payload={"title": "w", "fields": FIELDS},
                                expected=2)
        self.assertEqual((refused["code"], refused["root"]["reason"]), ("project-root-uncertain", root["reason"]),
                         refused)
        self.assertFalse(self.main.exists())
        self.assertEqual(list(self.base.rglob(".feather")), [])

    def test_a_moved_main_worktree_is_uncertain_and_not_recreated(self):
        os.rename(self.main, self.base / "moved")
        self.assert_broken_linked_worktree()

    def test_a_deleted_main_worktree_is_uncertain_and_not_recreated(self):
        remove_base(self.main)
        self.assert_broken_linked_worktree()

    def test_a_store_reached_through_a_directory_link_is_uncertain(self):
        feather_support.make_directory_link(self.main / ".feather", self.outside)
        self.assert_uncertain(self.wt1, "Link/reparse path is not supported")
        self.assertEqual(self.tree(self.outside), {})

    def test_strict_git_output_is_required(self):
        """S02-2: a non-zero exit, a missing field or an unrecognised format makes the root uncertain."""
        common = ["rev-parse", "--path-format=absolute", "--git-common-dir"]
        cases = {
            "older Git echoing --path-format": (common, (0, "--path-format=absolute\n.git\n", ""), "exactly one"),
            "relative common directory": (common, (0, ".git\n", ""), "exactly one absolute path"),
            "missing common directory": (common, (0, str(self.base / "absent") + "\n", ""), "not an existing"),
            "failed Git directory query": (["rev-parse", "--absolute-git-dir"], (128, "", "fatal: broken\n"),
                                           "fatal: broken"),
            "older Git without worktree list -z": (["worktree", "list", "--porcelain", "-z"],
                                                   (129, "", "error: unknown switch `z'\n"), "unknown switch"),
            "newline-delimited worktree list": (["worktree", "list", "--porcelain", "-z"],
                                                (0, f"worktree {self.main}\nHEAD 0\n\n", ""), "NUL-terminated"),
            "first record without a worktree path": (["worktree", "list", "--porcelain", "-z"],
                                                     (0, "HEAD 0\0branch refs/heads/main\0\0", ""),
                                                     "does not start with a worktree path"),
            "relative worktree path": (["worktree", "list", "--porcelain", "-z"],
                                       (0, "worktree main\0HEAD 0\0\0", ""), "has no absolute path"),
            "bare first record": (["worktree", "list", "--porcelain", "-z"],
                                  (0, f"worktree {self.main}\0bare\0\0", ""), "is bare"),
        }
        for label, (command, answer, reason) in cases.items():
            with self.subTest(case=label):
                def override(directory, seen, command=command, answer=answer):
                    return answer if directory == str(self.wt1) and seen == command else None
                self.assert_uncertain(self.wt1, reason, subprocess_run=False, context=self.git_as(override=override))

    def test_the_main_candidate_must_be_the_repositorys_main_worktree(self):
        """S02-1: the first entry is accepted only when it is neither the common directory nor inside it, is its own
        top level, holds .git and has the common directory as its Git directory."""
        other = self.repository("other")
        (self.main / "sub").mkdir()
        common = Path(self.git(self.wt1, "rev-parse", "--path-format=absolute", "--git-common-dir"))
        cases = {
            "the common directory": (self.main / ".git", {}, "Git directory or inside it"),
            "inside the common directory": (self.main / ".git" / "refs", {}, "Git directory or inside it"),
            "a missing directory": (self.base / "absent", {}, "does not exist"),
            "a subdirectory of the main worktree": (self.main / "sub", {}, "not its own Git top level"),
            "another repository": (other, {}, "not the repository's common directory"),
            "a directory without .git": (self.outside, {
                ("rev-parse", "--show-toplevel"): (0, f"{self.outside}\n", ""),
                ("rev-parse", "--absolute-git-dir"): (0, f"{common}\n", "")}, "holds no .git entry"),
        }
        for label, (candidate, answers, reason) in cases.items():
            with self.subTest(candidate=label):
                listing = f"worktree {candidate.as_posix()}\0HEAD 0\0branch refs/heads/main\0\0"

                def override(directory, command, candidate=candidate, answers=answers, listing=listing):
                    if directory == str(self.wt1) and command[:2] == ["worktree", "list"]:
                        return 0, listing, ""
                    if os.path.normcase(directory) == os.path.normcase(str(candidate)):
                        return answers.get(tuple(command))
                    return None
                self.assert_uncertain(self.wt1, reason, subprocess_run=False, context=self.git_as(override=override))

    def test_the_linked_decision_precedes_the_worktree_list(self):
        """S02-1: a main checkout runs no worktree list; a linked one reads its Git and common directories first."""
        with self.git_as() as calls:
            code, listed = self.invoke(self.main, "list")
        self.assertEqual((code, listed["root"]["shared"]), (0, False), listed)
        self.assertNotIn(["worktree", "list", "--porcelain", "-z"], [git_call(args)[1] for args in calls])
        with self.git_as() as calls:
            code, listed = self.invoke(self.wt1, "list")
        self.assertEqual((code, listed["root"]["shared"]), (0, True), listed)
        commands = [git_call(args)[1] for args in calls]
        listing = commands.index(["worktree", "list", "--porcelain", "-z"])
        self.assertLess(commands.index(["rev-parse", "--absolute-git-dir"]), listing)
        self.assertLess(commands.index(["rev-parse", "--path-format=absolute", "--git-common-dir"]), listing)


class StorePinTest(SharedBase):
    """S02-3 and S02-6: the store root is the main worktree's strict real path, pinned and checked like any root."""

    def test_a_worktree_reached_through_a_link_above_it_reports_the_real_store(self):
        feather_support.make_directory_link(self.base / "alias", self.base)
        requested = self.base / "alias" / "wt1"
        created = self.run_tool(requested, "create", "--work", "w.md", payload={"title": "w", "fields": FIELDS})
        self.assertEqual(created["root"], self.shared_root(requested, self.wt1), created)
        self.assertTrue((self.store / "w.md").is_file())

    def test_a_store_root_replaced_after_resolution_is_refused(self):
        decoy = self.base / "decoy"
        decoy.mkdir()
        storage.reset_roots()
        store = storage.Store(str(self.wt1))
        self.assertTrue(store.root["shared"], store.root)
        moved = self.base / "moved"
        os.rename(self.main, moved)
        feather_support.make_directory_link(self.main, decoy)
        with self.assertRaises(storage.HandoffError) as raised:
            create_work(store, "w.md", {"title": "w", "fields": FIELDS})
        self.assertEqual(raised.exception.code, "unsafe-path")
        self.assertIn("Project root changed after it was resolved", str(raised.exception))
        self.assertEqual(self.tree(decoy), {})
        self.assertFalse((moved / ".feather").exists())
        self.assertFalse((self.wt1 / ".feather").exists())
        self.assertEqual(self.tree(self.outside), {})

    def test_a_hard_linked_work_file_in_the_shared_store_is_refused(self):
        created = self.run_tool(self.wt1, "create", "--work", "w.md", payload={"title": "w", "fields": FIELDS})
        work = self.store / "w.md"
        data = work.read_bytes()
        outside = self.outside / "w.md"
        outside.write_bytes(data)
        work.unlink()
        try:
            os.link(outside, work)
        except (OSError, NotImplementedError) as error:
            self.skipTest(f"hard link creation unavailable: {error}")
        refused = self.run_tool(self.wt1, "update", "--work", "w.md", expected=2,
                                payload={"version": created["version"], "fields": {"next": "m"}})
        self.assertEqual(refused["code"], "unsafe-path", refused)
        self.assertIn("Hard-linked file is not supported", refused["message"])
        self.assertEqual((work.read_bytes(), outside.read_bytes()), (data, data))

    def strict_realpath_fails(self, under: Path | None):
        original = os.path.realpath

        def realpath(path, *args, strict=False, **kwargs):
            if strict and (under is None or os.path.normcase(os.path.abspath(path)).startswith(
                    os.path.normcase(str(under)))):
                raise OSError(errno.EINVAL, "Incorrect function", str(path), 1)
            return original(path, *args, **kwargs)
        return mock.patch.object(storage.os.path, "realpath", side_effect=realpath)

    def test_a_main_worktree_without_a_strict_real_path_is_uncertain(self):
        listed = self.assert_uncertain(self.wt1, "could not be resolved to a strict real path", subprocess_run=False,
                                       context=self.strict_realpath_fails(self.main))
        self.assertEqual(listed["root"]["checkout"], str(self.wt1))
        self.assertFalse((self.main / ".feather").exists())

    def test_a_volume_without_strict_real_paths_never_uses_an_unpinned_shared_store(self):
        self.assert_uncertain(self.wt1, "could not be resolved to a strict real path", subprocess_run=False,
                              context=self.strict_realpath_fails(None))
        self.assertEqual(list(self.base.rglob(".feather")), [])
        self.assertEqual(storage._ROOTS, set())


class GuardTest(SharedBase):
    """S02-4: tracking detection runs in the Working checkout after its own lazy-fetch guard, before the store is
    chosen; the ignore rules run in the main worktree after the main worktree's guard; a detection failure makes the
    root uncertain."""

    def test_each_git_directory_is_guarded(self):
        with self.git_as() as calls:
            code, created = self.invoke(self.wt1, "create", "--work", "w.md", payload={"title": "w", "fields": FIELDS})
        self.assertEqual((code, created["tracking"], created["root"]["shared"]), (0, "ignored", True), created)
        self.assert_guarded(calls)
        recorded = [git_call(args) for args in calls]
        commands = [command for _, command, _ in recorded]
        detection = recorded.index((str(self.wt1), ["ls-files", "--", ".feather/handoffs/"], False))
        self.assertLess(detection, commands.index(["worktree", "list", "--porcelain", "-z"]))
        ignore_rules = [(directory, command) for directory, command, _ in recorded[detection + 1:]
                        if command[0] in {"ls-files", "check-ignore"}]
        self.assertTrue(ignore_rules)
        for directory, command in ignore_rules:
            self.assertEqual(directory, str(self.main), command)
            self.assertTrue(command[command.index("--") + 1].startswith(".feather/handoffs/"), command)

    def per_worktree_promisor(self):
        self.git(self.main, "config", "extensions.worktreeConfig", "true")
        self.git(self.wt1, "config", "--worktree", "remote.origin.promisor", "true")

    def test_a_per_worktree_promisor_governs_only_the_linked_worktrees_reads(self):
        self.per_worktree_promisor()
        with self.git_as(version="git version 2.45.0") as calls:
            code, created = self.invoke(self.wt1, "create", "--work", "w.md", payload={"title": "w", "fields": FIELDS})
        self.assertEqual((code, created["tracking"], created["root"]["shared"]), (0, "ignored", True), created)
        self.assert_guarded(calls)
        reads = [git_call(args) for args in calls if git_call(args)[1][0] in OBJECT_READS]
        self.assertIn((str(self.wt1), ["ls-files", "--", ".feather/handoffs/"], True), reads)
        for directory, command, flagged in reads:
            # The guard of each directory decides the flag of the reads there.
            self.assertEqual(flagged, directory == str(self.wt1), (directory, command))
        self.assertTrue(any(directory == str(self.main) for directory, _, _ in reads), reads)

    def test_a_promisor_the_installed_git_cannot_guard_makes_the_root_uncertain(self):
        self.per_worktree_promisor()
        with self.git_as(version="git version 2.44.0") as calls:
            self.assert_uncertain(self.wt1, "promisor-remote", subprocess_run=False)
        for directory, command, _ in map(git_call, calls):
            self.assertFalse(directory == str(self.wt1) and command[0] in OBJECT_READS, command)
            self.assertNotEqual(command[:2], ["worktree", "list"], "the store was chosen without a tracking state")

    def test_a_failed_detection_makes_the_root_uncertain(self):
        def index_fails(directory, command):
            if directory == str(self.wt1) and command[0] == "ls-files":
                return 128, "", "fatal: index file corrupt\n"
            return None

        def git_unavailable(directory, command):
            if directory == str(self.wt1) and command[:2] == ["config", "--list"]:
                raise FileNotFoundError(errno.ENOENT, "git vanished", "git")
            return None
        for label, override, reason in (("index read fails", index_fails, "index file corrupt"),
                                        ("Git cannot be run", git_unavailable, "git vanished")):
            with self.subTest(case=label):
                self.assert_uncertain(self.wt1, reason, subprocess_run=False, context=self.git_as(override=override))


def normalized(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def assert_sentences(test: unittest.TestCase, path: Path, sentences: tuple[str, ...]):
    text = normalized(path)
    for sentence in sentences:
        with test.subTest(sentence=sentence[:60]):
            test.assertRegex(text, rf"(?:^|(?<=\s)){re.escape(sentence)}(?=\s|$)")


# Words that would name a host's own tools rather than state a rule codex-feather can adopt unchanged.
HOST_TOOLS = re.compile(r"\b(?:Bash|PowerShell|Edit|Write|Read|Grep|Glob|apply_patch|Claude Code|Codex)\b")


class SkillDocumentationTest(unittest.TestCase):
    """Acceptance 11 and 12's skill share for items 1, 6 and 11: the root rule names the Handoff store, the old
    worktree statement is gone, and the rules name no host's tools."""

    SENTENCES = (
        "**Root:** resolve the project root, including when working in a subdirectory, and its Handoff store, the "
        "`.feather/handoffs/` directory that holds the records.",
        "In an untracked linked worktree of a Git repository the Handoff store is the main worktree's, shared by every "
        "checkout of that repository; in the main worktree, a non-Git project, an explicit root and a checkout that "
        "tracks its records, it stays under the project root.",
        "Sources, baselines and the record's environment still describe the Working checkout, the checkout the session "
        "works in, never the store's checkout.",
        "When the main worktree cannot be established, the tool reports the root as uncertain and writes nothing; "
        "never write records inside the linked worktree in its place.",
        "Checkouts of one repository share records only through the Handoff store; cross-project synchronization is "
        "outside this skill.",
        "Tracking is decided from the Working checkout: its track marker or already tracked records keep a linked "
        "worktree's records in its own store.",
        "Ignore rules go to the `.gitignore` of the checkout that holds the store, and a linked worktree that uses the "
        "shared store writes no other file outside it.",
        "Choose tracking from the checkout whose records it should track; the tool refuses a `track` choice from a "
        "linked worktree that uses the shared store.",
        "When the tool reports `root.shared: true`, record the Working checkout's path, branch and commit in `環境：` "
        "on create and on each update that changes them.",
        "A record whose `環境：` names another checkout belongs to that checkout: name that checkout in the four-part "
        "resume summary, do not switch branches or checkouts to match it, and let work that needs that checkout's "
        "files wait for the user.",
        "`環境：` is provenance, not evidence that uncommitted work in that checkout still exists.",
    )

    def test_the_skill_states_the_shared_store_rules(self):
        assert_sentences(self, SKILL, self.SENTENCES)

    def test_the_old_worktree_statement_is_gone(self):
        self.assertNotIn("Cross-project/worktree synchronization is outside this skill.", normalized(SKILL))

    def test_the_new_rules_name_no_hosts_tools(self):
        for sentence in self.SENTENCES:
            with self.subTest(sentence=sentence[:60]):
                self.assertNotRegex(sentence, HOST_TOOLS)


class ToolReferenceSharedStoreTest(unittest.TestCase):
    """Acceptance 12's tool-reference share for items 1, 2, 3, 4 and 6: store selection, the root fields from a
    linked worktree, root.tracking and the new uncertain reasons."""

    SENTENCES = (
        "The Working checkout is a linked worktree only when its `git rev-parse --absolute-git-dir` and "
        "`git rev-parse --path-format=absolute --git-common-dir` name different directories, so a main checkout with "
        "a separate Git directory keeps its own store.",
        "For a linked worktree, `root.tracking` reports `tracked` when the checkout's own `.gitignore` holds the track "
        "marker or its index already tracks a file under `.feather/handoffs/`, and `untracked` otherwise; that "
        "detection runs in the Working checkout after its lazy-fetch guard, and a tracked checkout keeps its records "
        "in its own store.",
        "The main worktree is the first record of `git worktree list --porcelain -z`, accepted only when it is not "
        "marked bare, resolves to an existing directory that is neither the repository's Git directory nor inside it, "
        "is its own top level, holds a `.git` entry and has the repository's common directory as its Git directory; "
        "paths are compared by filesystem identity, and the store under it passes the link checks below.",
        "When the tracking state or the main worktree cannot be established, such as a bare repository, a separate "
        "Git directory or submodule whose first entry is the Git directory itself, "
        "`.feather` reached through a link, a main worktree without a strict real path, a promisor remote the "
        "installed Git cannot guard, or a Git too old for `--path-format` or `worktree list -z`, the root is "
        "`uncertain` with a `reason` that starts \"Handoff store discovery failed\" and names what failed, `path` and "
        "`store` stay the Working checkout, reads return its own records as `partial`, and mutations fail with "
        "`project-root-uncertain` until a root is confirmed with `--exact-root`.",
        "A moved or deleted main worktree breaks the linked worktree itself, so its root is `uncertain` with Git's own "
        "discovery error as the `reason`, reads are `partial` and mutations fail with `project-root-uncertain`.",
        "Records are never written inside the linked worktree in place of the shared store.",
        "Writing in a Git project needs Git 2.31 or later, for `--path-format`, and a shared store needs Git 2.36 or "
        "later, for `worktree list -z`; on older Git the root is `uncertain` and `--exact-root` is the recovery.",
        "`snapshot`, `compare` and the save-time baseline check read sources and Git state from the Working checkout, "
        "never from the store's directory.",
        "Ignore rules are applied in the checkout that holds the store, with its own lazy-fetch guard, so a run that "
        "uses the shared store writes only the main worktree's `.gitignore` outside the store and nothing in the "
        "Working checkout.",
        "A `track` choice in such a run returns `input` and writes nothing, because tracking is chosen from the "
        "checkout whose records it should track.",
    )

    def test_the_tool_reference_documents_the_shared_store(self):
        assert_sentences(self, TOOL_REFERENCE, self.SENTENCES)

    def test_the_store_is_no_longer_said_to_be_always_under_the_working_checkout(self):
        self.assertNotIn("The store is currently always under the Working checkout", normalized(TOOL_REFERENCE))


if __name__ == "__main__":
    unittest.main()
