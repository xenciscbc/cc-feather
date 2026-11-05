"""The Working checkout and the Handoff store are separate locations in the handoff tool (worktree store ticket 01).

Trust boundary: the project's files, its Git metadata and the paths supplied to --project against the handoff tool's
process. The tool reads sources and Git state from the Working checkout and keeps records, history and archives in
the Handoff store directory; today both are the same directory, so every result reports `shared: false`. Each store
root is pinned once it was resolved strictly, the root guard covers both locations, and each group of Git commands
runs the lazy-fetch guard in its own -C directory.

Tests run under a unique directory made with mkdtemp under FEATHER_LINK_TEST_DIR when it is set, otherwise the system
temporary directory, with an isolated Git environment and synthetic data only. A store apart from the checkout is
simulated by replacing the store selection with a strictly resolved sibling repository, the seam later tickets fill
with the main worktree; the operations themselves are driven through the CLI entry point or a mutation's public
operation."""
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
TOOL_REFERENCE = ROOT / "skills/handoff/references/tool.md"
sys.path.insert(0, str(SCRIPTS))

from feather_handoff import cli, storage  # noqa: E402
from feather_handoff.archiving import archive_work  # noqa: E402
from feather_handoff.history_mutations import clear_history, seal_history  # noqa: E402
from feather_handoff.writing import create_work, update_work  # noqa: E402
from tests import feather_support  # noqa: E402

FIELDS = {"goal": "g", "progress": "p", "next": "n", "updated": "2026-11-05T10:00:00+08:00"}
COMMIT_ENV = {"GIT_AUTHOR_NAME": "Fixture", "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
              "GIT_COMMITTER_NAME": "Fixture", "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
              "GIT_AUTHOR_DATE": "2026-11-05T10:00:00+08:00", "GIT_COMMITTER_DATE": "2026-11-05T10:00:00+08:00"}
# Commands of the tool that can read objects, which only run after the lazy-fetch guard in their directory.
OBJECT_READS = {"ls-files", "check-ignore", "show-ref"}
STRICT_REALPATH = "strict realpath unsupported on this volume; set FEATHER_LINK_TEST_DIR to a volume that supports it"


def remove_base(base: Path) -> None:
    """Unlink every directory link first so removal never reaches through one, then remove the tree, clearing the
    read-only attribute Git gives its object files on Windows."""
    for current, directories, _ in os.walk(base):
        for name in list(directories):
            info = (Path(current) / name).lstat()
            if stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & 0x400):
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


class StoreBase(unittest.TestCase):
    requires_strict_realpath = True

    def setUp(self):
        configured = os.environ.get("FEATHER_LINK_TEST_DIR")
        if configured:
            os.makedirs(configured, exist_ok=True)
        base = tempfile.mkdtemp(dir=configured or None)
        self.addCleanup(remove_base, Path(base))
        try:
            self.base = Path(os.path.realpath(base, strict=True))
        except OSError:
            if self.requires_strict_realpath:
                self.skipTest(STRICT_REALPATH)
            self.base = Path(os.path.realpath(base))
        self.outside = self.base / "outside"
        self.outside.mkdir()
        (self.base / "home").mkdir()
        empty = self.base / "gitconfig"
        empty.write_bytes(b"")
        # Isolated from the user's global and system Git configuration; no inherited GIT_* variable reaches Git.
        environment = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
        environment.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": str(empty),
                            "HOME": str(self.base / "home"), "XDG_CONFIG_HOME": str(self.base / "home")})
        self.enterContext(mock.patch.dict(os.environ, environment, clear=True))
        self.addCleanup(storage.reset_roots)

    def git(self, cwd: Path, *args: str) -> str:
        try:
            result = subprocess.run(["git", *args], cwd=cwd, env={**os.environ, **COMMIT_ENV},
                                    stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired) as error:
            self.skipTest(f"Git cannot be run: {error}")
        self.assertEqual(result.returncode, 0, (args, result.stderr))
        return result.stdout.strip()

    def repository(self, name: str, source: bytes = b"a\n") -> Path:
        """A repository with one commit holding a.txt."""
        path = self.base / name
        path.mkdir(parents=True)
        self.git(path, "-c", "core.fsmonitor=", "init", "--quiet", "--initial-branch=main", ".")
        self.git(path, "config", "core.autocrlf", "false")
        (path / "a.txt").write_bytes(source)
        self.git(path, "-c", "core.fsmonitor=", "add", "--", "a.txt")
        self.git(path, "-c", "core.fsmonitor=", "-c", "commit.gpgSign=false", "commit", "--quiet", "--no-verify",
                 "-m", "fixture")
        return path

    def git_version(self) -> tuple[int, ...]:
        match = re.match(r"git version (\d+)\.(\d+)\.(\d+)", self.git(self.base, "version"))
        if not match:
            self.skipTest("the installed Git version could not be read")
        return tuple(map(int, match.groups()))

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
        result = {}
        for directory, _, files in os.walk(path or self.base):
            for name in files:
                item = Path(directory, name)
                result[item.relative_to(path or self.base).as_posix()] = item.read_bytes()
        return result

    def changed(self, before: dict, after: dict) -> set[str]:
        return {name for name in before.keys() | after.keys() if before.get(name) != after.get(name)}


class RootFieldsTest(StoreBase):
    """Acceptance 3: every result's root reports checkout, store and shared; path stays the store's directory."""

    def assert_root(self, result: dict, requested: Path, path: Path, state: str):
        expected = {"requested": str(requested), "path": str(path), "state": state,
                    "checkout": str(path), "store": str(path), "shared": False}
        self.assertEqual({key: value for key, value in result["root"].items() if key != "reason"}, expected, result)

    def test_git_project(self):
        repo = self.repository("repo")
        self.assert_root(self.run_tool(repo, "list"), repo, repo, "git")
        created = self.run_tool(repo, "create", "--work", "w.md", payload={"title": "w", "fields": FIELDS})
        self.assert_root(created, repo, repo, "git")
        self.assertTrue((repo / ".feather/handoffs/w.md").is_file())

    def test_git_subdirectory(self):
        repo = self.repository("repo")
        nested = repo / "a" / "b"
        nested.mkdir(parents=True)
        self.assert_root(self.run_tool(nested, "list"), nested, repo, "git")
        created = self.run_tool(nested, "create", "--work", "w.md", payload={"title": "w", "fields": FIELDS})
        self.assert_root(created, nested, repo, "git")
        self.assertTrue((repo / ".feather/handoffs/w.md").is_file())
        self.assertFalse((nested / ".feather").exists())

    def test_non_git_project(self):
        project = self.base / "plain"
        project.mkdir()
        self.assert_root(self.run_tool(project, "list"), project, project, "non-git")
        created = self.run_tool(project, "create", "--work", "w.md", payload={"title": "w", "fields": FIELDS})
        self.assert_root(created, project, project, "non-git")

    def test_exact_root(self):
        repo = self.repository("repo")
        nested = repo / "nested"
        nested.mkdir()
        self.assert_root(self.run_tool(nested, "list", exact=True), nested, nested, "explicit")
        created = self.run_tool(nested, "create", "--work", "w.md", payload={"title": "w", "fields": FIELDS},
                                exact=True)
        self.assert_root(created, nested, nested, "explicit")
        self.assertTrue((nested / ".feather/handoffs/w.md").is_file())

    def test_uncertain_root_reports_the_same_location_twice(self):
        repo = self.repository("repo")
        (repo / "target").mkdir()
        feather_support.make_directory_link(repo / "alias", repo / "target")
        listed = self.run_tool(repo / "alias", "list", expected=2)
        self.assert_root(listed, repo / "alias", repo / "target", "uncertain")
        self.assertEqual(listed["status"], "partial")


class SeparateStoreBase(StoreBase):
    """A checkout repository and a sibling repository standing in for a store selected elsewhere."""

    def setUp(self):
        super().setUp()
        self.checkout = self.repository("repo", b"checkout\n")
        self.main = self.repository("main", b"main\n")
        self.store = self.main / ".feather" / "handoffs"

    def separate(self, reason: str | None = None):
        """The store selection names the sibling repository, resolved strictly, as later store selection will."""
        selected = Path(os.path.realpath(self.main, strict=True))
        return mock.patch.object(storage, "_select_store", return_value=(selected, True, reason))

    @contextlib.contextmanager
    def recorded(self):
        calls: list[list[str]] = []
        real = subprocess.run

        def run(args, **kwargs):
            calls.append(list(args))
            return real(args, **kwargs)
        with mock.patch.object(storage.subprocess, "run", side_effect=run):
            yield calls

    def assert_guarded(self, calls: list[list[str]]):
        """S01-4: an object-reading command runs only after the lazy-fetch guard ran in its own -C directory."""
        guarded = set()
        for args in calls:
            directory, command, _ = git_call(args)
            if command[:2] == ["config", "--list"]:
                guarded.add(directory)
            elif command[0] in OBJECT_READS:
                self.assertIn(directory, guarded, f"{command} ran in {directory} before its lazy-fetch guard")


class SeparateLocationsTest(SeparateStoreBase):
    """S01-3, S01-4 and S01-5: records, history, archives and ignore rules use the store; sources, Git state and
    their containment use the Working checkout, whatever the store holds."""

    def test_records_and_ignore_rules_use_the_store_and_observations_use_the_checkout(self):
        before = self.tree()
        with self.separate():
            with self.recorded() as calls:
                code, snapshot = self.invoke(self.checkout, "snapshot", payload={"paths": ["a.txt"]})
            self.assertEqual(code, 0, snapshot)
            self.assertEqual(snapshot["root"], {"requested": str(self.checkout), "path": str(self.main),
                                                "state": "git", "checkout": str(self.checkout),
                                                "store": str(self.main), "shared": True})
            self.assertEqual(snapshot["snapshot"]["files"][0]["sha256"], hashlib.sha256(b"checkout\n").hexdigest())
            for args in calls:
                self.assertEqual(git_call(args)[0], str(self.checkout), args)

            with self.recorded() as calls:
                code, created = self.invoke(self.checkout, "create", "--work", "w.md",
                                            payload={"title": "w", "fields": FIELDS,
                                                     "snapshot": snapshot["snapshot"]})
            # The save-time check of the baseline read the checkout's a.txt, not the store's.
            self.assertEqual((code, created["status"], created["tracking"]), (0, "ok", "ignored"), created)
            self.assertEqual(created["root"]["path"], str(self.main))
            self.assert_guarded(calls)
            ignore_rules = [git_call(args) for args in calls if git_call(args)[1][0] in {"ls-files", "check-ignore"}]
            self.assertTrue(ignore_rules)
            for directory, command, _ in ignore_rules:
                self.assertEqual(directory, str(self.main), command)
                pathspec = command[command.index("--") + 1]
                self.assertTrue(pathspec.startswith(".feather/handoffs/"), command)
            for args in calls:
                directory, command, _ = git_call(args)
                if command[0] in {"symbolic-ref", "show-ref"} or command[:2] == ["rev-parse", "--verify"]:
                    self.assertEqual(directory, str(self.checkout), command)

            code, listed = self.invoke(self.checkout, "list")
            self.assertEqual([item["work"] for item in listed["items"]], ["w.md"], listed)
            code, read = self.invoke(self.checkout, "read", "--work", "w.md")
            self.assertEqual((code, read["version"]), (0, created["version"]), read)
            # A change in the store's checkout is no change to the Working checkout's sources.
            (self.main / "a.txt").write_bytes(b"main changed\n")
            code, compared = self.invoke(self.checkout, "compare", "--work", "w.md")
            self.assertEqual((code, [item["comparison"] for item in compared["files"]]), (0, ["unchanged"]), compared)
            self.assertEqual(compared["git"]["comparison"], "unchanged", compared)

            code, done = self.invoke(self.checkout, "update", "--work", "w.md",
                                     payload={"version": created["version"], "fields": {"status": "完成"}})
            self.assertEqual((code, done["archived"]), (0, True), done)
            code, history = self.invoke(self.checkout, "history")
            self.assertEqual([entry["title"] for entry in history["entries"]], ["w"], history)
            code, sealed = self.invoke(self.checkout, "seal", payload={
                "version": history["documents"][0]["version"], "ids": [history["entries"][0]["id"]],
                "destination": "batch.md"})
            self.assertEqual((code, sealed["status"]), (0, "ok"), sealed)
        self.assertEqual(Path(done["history_path"]), self.store / "history.md")
        self.assertEqual(Path(done["work_path"]), self.store / "w.md")
        self.assertEqual(Path(sealed["destination"]), self.store / "archive" / "batch.md")
        self.assertEqual(self.changed(before, self.tree()),
                         {"main/a.txt", "main/.gitignore", "main/.feather/handoffs/history.md",
                          "main/.feather/handoffs/archive/batch.md"})
        self.assertEqual(self.tree(self.outside), {})

    def test_archival_keeps_history_and_the_removed_work_file_in_one_store(self):
        with self.separate():
            code, saved = self.invoke(self.checkout, "create", "--work", "done.md",
                                      payload={"title": "done", "fields": {**FIELDS, "status": "完成"},
                                               "defer_history": True})
            self.assertEqual((code, saved["code"]), (2, "deferred"), saved)
            self.assertTrue((self.store / "done.md").is_file())
            before = self.tree()
            code, archived = self.invoke(self.checkout, "archive", "--work", "done.md",
                                         payload={"version": saved["version"]})
        self.assertEqual((code, archived["archived"], archived["tracking"]), (0, True, "existing-rule"), archived)
        self.assertEqual(Path(archived["work_path"]).parent, Path(archived["history_path"]).parent)
        self.assertEqual(Path(archived["history_path"]), self.store / "history.md")
        self.assertEqual(self.changed(before, self.tree()),
                         {"main/.feather/handoffs/done.md", "main/.feather/handoffs/history.md"})
        self.assertFalse((self.checkout / ".feather").exists())

    def test_a_source_reaching_the_store_through_a_link_is_refused(self):
        feather_support.make_directory_link(self.checkout / "linked", self.main)
        with self.separate():
            code, result = self.invoke(self.checkout, "snapshot", payload={"paths": ["linked/a.txt", "a.txt"]})
        self.assertEqual((code, result["status"]), (2, "partial"), result)
        files = {item["path"]: item for item in result["snapshot"]["files"]}
        self.assertEqual(files["linked/a.txt"], {"path": "linked/a.txt", "state": "unknown", "reason": "unsafe-path"})
        self.assertEqual(files["a.txt"]["sha256"], hashlib.sha256(b"checkout\n").hexdigest())


class LazyFetchGuardTest(SeparateStoreBase):
    """S01-4: the ignore rules' Git commands follow the guard of the store's checkout, never the Working checkout's."""

    def create(self) -> tuple[int, dict, list[list[str]]]:
        with self.separate(), self.recorded() as calls:
            code, result = self.invoke(self.checkout, "create", "--work", "w.md",
                                       payload={"title": "w", "fields": FIELDS})
        return code, result, calls

    def test_a_promisor_remote_in_the_store_checkout_governs_the_ignore_rules(self):
        self.git(self.main, "config", "remote.origin.promisor", "true")
        before = self.tree()
        code, result, calls = self.create()
        self.assert_guarded(calls)
        reads = [git_call(args) for args in calls if git_call(args)[1][0] in OBJECT_READS]
        if self.git_version() >= storage.NO_LAZY_FETCH_FROM:
            self.assertEqual((code, result["tracking"]), (0, "ignored"), result)
            self.assertTrue(reads)
            for directory, command, lazy in reads:
                self.assertTrue(lazy, (directory, command))
        else:
            self.assertEqual((code, result["code"], result["cause_code"]), (2, "tracking-failed", "promisor-remote"),
                             result)
            self.assertEqual([read for read in reads if read[0] == str(self.main)], [])
            self.assertEqual(self.changed(before, self.tree()), {"main/.feather/handoffs/w.md"})

    def test_a_promisor_remote_in_the_checkout_alone_does_not_govern_the_store(self):
        self.git(self.checkout, "config", "remote.origin.promisor", "true")
        code, result, calls = self.create()
        self.assertEqual((code, result["tracking"]), (0, "ignored"), result)
        self.assert_guarded(calls)
        reads = [git_call(args) for args in calls if git_call(args)[1][0] in {"ls-files", "check-ignore"}]
        self.assertTrue(reads)
        for directory, command, lazy in reads:
            self.assertEqual((directory, lazy), (str(self.main), False), command)
        self.assertTrue((self.main / ".gitignore").is_file())
        self.assertFalse((self.checkout / ".gitignore").exists())


class StoreRootPinTest(SeparateStoreBase):
    """S01-1: the store root is pinned on its own; replacing it after resolution redirects nothing."""

    def test_a_store_root_replaced_after_resolution_is_refused(self):
        decoy = self.base / "decoy"
        decoy.mkdir()
        with self.separate():
            store = storage.Store(str(self.checkout))
        before = self.tree(self.checkout)
        os.rename(self.main, self.base / "moved")
        feather_support.make_directory_link(self.main, decoy)
        with self.assertRaises(storage.HandoffError) as raised:
            create_work(store, "w.md", {"title": "w", "fields": FIELDS})
        self.assertEqual(raised.exception.code, "unsafe-path")
        self.assertIn("Project root changed after it was resolved", str(raised.exception))
        self.assertEqual(self.tree(decoy), {})
        self.assertFalse((self.base / "moved" / ".feather").exists())
        self.assertEqual(self.tree(self.checkout), before)
        self.assertEqual(self.tree(self.outside), {})


class UnresolvedVolumeTest(StoreBase):
    """S01-1: where strict real paths cannot be resolved, a checkout-local store keeps the documented fallback: it
    is not registered, and links anywhere in the supplied path are refused."""

    requires_strict_realpath = False

    def test_checkout_local_store_is_not_registered_and_links_are_refused(self):
        real = self.base / "real"
        (real / "project").mkdir(parents=True)
        feather_support.make_directory_link(self.base / "link", real)
        original = os.path.realpath

        def unsupported(path, *args, strict=False, **kwargs):
            if strict:
                raise OSError(errno.EINVAL, "Incorrect function", str(path), 1)
            return original(path, *args, **kwargs)
        with mock.patch.object(storage.os.path, "realpath", side_effect=unsupported):
            code, refused = self.invoke(self.base / "link" / "project", "create", "--work", "w.md",
                                        payload={"title": "w", "fields": FIELDS})
            self.assertEqual((code, refused["code"]), (2, "unsafe-path"), refused)
            self.assertIn("Link/reparse path is not supported", refused["message"])
            self.assertEqual(self.tree(real), {})
            code, created = self.invoke(real / "project", "create", "--work", "w.md",
                                        payload={"title": "w", "fields": FIELDS})
        self.assertEqual((code, created["status"]), (0, "ok"), created)
        resolved = str((real / "project").resolve())
        self.assertEqual({key: created["root"][key] for key in ("path", "checkout", "store", "shared")},
                         {"path": resolved, "checkout": resolved, "store": resolved, "shared": False})
        self.assertEqual(storage._ROOTS, set())
        self.assertTrue((real / "project/.feather/handoffs/w.md").is_file())


class RootGuardTest(SeparateStoreBase):
    """S01-2: when either location is uncertain, every mutation is refused before its first write and reads are
    partial."""

    def setUp(self):
        super().setUp()
        self.addCleanup(storage.reset_roots)
        storage.reset_roots()
        with self.separate():
            store = storage.Store(str(self.checkout))
            create_work(store, "active.md", {"title": "active", "fields": FIELDS})
            create_work(store, "done.md", {"title": "done", "fields": {**FIELDS, "status": "完成"}})
            code, self.history = self.invoke(self.checkout, "history")
        self.assertEqual(len(self.history["entries"]), 1, self.history)
        self.active = (self.store / "active.md").read_bytes()

    def denied(self):
        return mock.patch.object(storage.subprocess, "run", return_value=subprocess.CompletedProcess(
            [], 128, "", "fatal: detected dubious ownership in repository"))

    def mutations(self, store: storage.Store):
        version = hashlib.sha256(self.active).hexdigest()
        ids = [self.history["entries"][0]["id"]]
        history_version = self.history["documents"][0]["version"]
        return {"create": lambda: create_work(store, "new.md", {"title": "new", "fields": FIELDS}),
                "update": lambda: update_work(store, "active.md", {"version": version, "fields": {"next": "m"}}),
                "archive": lambda: archive_work(store, "active.md", {"version": version}),
                "clear": lambda: clear_history(store, {"source": "history.md", "version": history_version,
                                                       "ids": ids}),
                "seal": lambda: seal_history(store, {"version": history_version, "ids": ids,
                                                     "destination": "batch.md"})}

    def assert_refused(self, store: storage.Store):
        before = self.tree()
        for name, mutation in self.mutations(store).items():
            with self.subTest(mutation=name), self.assertRaises(storage.HandoffError) as raised:
                mutation()
            self.assertEqual(raised.exception.code, "project-root-uncertain", name)
        self.assertEqual(self.tree(), before)

    def test_an_uncertain_root_refuses_every_mutation(self):
        with self.denied():
            store = storage.Store(str(self.checkout))
        self.assertEqual(store.root["state"], "uncertain")
        self.assert_refused(store)

    def test_an_uncertain_checkout_with_a_certain_store_refuses_every_mutation(self):
        with self.separate(), self.denied():
            store = storage.Store(str(self.checkout))
            code, listed = self.invoke(self.checkout, "list")
        self.assertEqual((code, listed["status"], listed["operation_status"]), (2, "partial", "ok"), listed)
        self.assertEqual(listed["root"]["store"], str(self.main))
        self.assert_refused(store)

    def test_an_uncertain_store_with_a_certain_checkout_refuses_every_mutation(self):
        with self.separate("the store could not be established"):
            store = storage.Store(str(self.checkout))
            code, listed = self.invoke(self.checkout, "list")
            self.assertEqual((code, listed["status"], listed["operation_status"]), (2, "partial", "ok"), listed)
            self.assertEqual(listed["root"]["state"], "git")
            before = self.tree()
            code, refused = self.invoke(self.checkout, "create", "--work", "new.md",
                                        payload={"title": "new", "fields": FIELDS})
            self.assertEqual((code, refused["code"]), (2, "project-root-uncertain"), refused)
            self.assertEqual(self.tree(), before)
        self.assert_refused(store)


class ToolReferenceRootFieldsTest(unittest.TestCase):
    """Acceptance 12's tool-reference share for item 3: the reference documents the new root fields."""

    SENTENCES = (
        "Every `root` also reports `checkout`, the Working checkout whose sources and Git state the tool reads, "
        "`store`, the directory that holds `.feather/handoffs/`, and `shared`, which is true when the two differ; "
        "`path` stays the store's directory, so a caller that reads only `path` still finds the records.",
        "From an untracked linked worktree the store is the repository's main worktree, so `shared` is true and "
        "`path` and `store` name the main worktree's directory; in every other case, the main worktree itself, a "
        "non-Git project, `--exact-root` and tracked mode, the store is under the Working checkout, so `checkout` and "
        "`store` name the same directory and `shared` is false.",
    )

    def test_root_fields_are_documented(self):
        text = " ".join(TOOL_REFERENCE.read_text(encoding="utf-8").split())
        for sentence in self.SENTENCES:
            with self.subTest(sentence=sentence[:60]):
                self.assertRegex(text, rf"(?:^|(?<=\s)){re.escape(sentence)}(?=\s|$)")


if __name__ == "__main__":
    unittest.main()
