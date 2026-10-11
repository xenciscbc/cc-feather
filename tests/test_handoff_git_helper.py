"""Repository safety C4: the handoff tool runs every Git command through one hardened helper.

Trust boundary: a project repository's tracked content and local Git metadata against the handoff tool's process. The
repository's own configuration must not choose a program the tool's Git commands run, and reading must not write the
index; the user's global and system configuration and environment stay trusted."""
import ast
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/handoff/scripts"
TOOL = SCRIPTS / "handoff.py"
sys.path.insert(0, str(SCRIPTS))

from feather_handoff import cli, storage  # noqa: E402

PREFIX = ["git", "--no-pager", "--no-optional-locks", "-c", "core.fsmonitor="]
FIELDS = {"goal": "g", "progress": "p", "next": "n", "updated": "2026-10-11T10:00:00+08:00"}
UPDATED = "2026-10-11T11:00:00+08:00"
CAPTURED = "2026-10-11T10:00:00+08:00"
# Fixed identity and dates make the plain and the configured repository's commits identical.
COMMIT_ENV = {"GIT_AUTHOR_NAME": "Fixture", "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
              "GIT_COMMITTER_NAME": "Fixture", "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
              "GIT_AUTHOR_DATE": "2026-10-11T10:00:00+08:00", "GIT_COMMITTER_DATE": "2026-10-11T10:00:00+08:00"}


class GitProcessStartTest(unittest.TestCase):
    """C4 item 2: no place in the handoff tool's package other than the helper starts a Git process."""

    SUBPROCESS = {"run", "Popen", "call", "check_call", "check_output", "getoutput", "getstatusoutput"}
    OS = {"system", "popen", "startfile", "fork", "forkpty"}
    OS_PREFIXES = ("exec", "spawn", "posix_spawn")
    # Standard modules that can start a process without naming subprocess or os, or import one by a computed name.
    FORBIDDEN_MODULES = {"asyncio", "multiprocessing", "concurrent", "pty", "ctypes", "importlib", "runpy",
                         "_posixsubprocess", "_winapi"}

    def starts(self, module: str, name: str) -> bool:
        if module == "subprocess":
            return name in self.SUBPROCESS
        return module == "os" and (name in self.OS or name.startswith(self.OS_PREFIXES))

    def scan(self, path: Path) -> list[tuple[str, str]]:
        """(enclosing function, reference) for every process start; also fails on imports that would hide one."""
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        found, scope = [], {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for child in ast.walk(node):
                    scope.setdefault(id(child), node.name)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    self.assertNotIn(top, self.FORBIDDEN_MODULES, f"{path.name} imports {alias.name}")
                    if top in {"subprocess", "os"}:
                        self.assertIn(alias.asname, {None, top}, f"{path.name} renames {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                top = (node.module or "").split(".")[0]
                self.assertNotIn(top, self.FORBIDDEN_MODULES, f"{path.name} imports from {node.module}")
                for alias in node.names:
                    self.assertFalse(alias.name == "*" and top in {"subprocess", "os"}, f"{path.name}: star import")
                    self.assertFalse(self.starts(top, alias.name), f"{path.name} imports {top}.{alias.name}")
            elif isinstance(node, ast.Name) and node.id in {"__import__", "exec", "eval", "compile"}:
                self.fail(f"{path.name} uses {node.id}")
            elif (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
                  and self.starts(node.value.id, node.attr)):
                found.append((scope.get(id(node), "<module>"), f"{node.value.id}.{node.attr}"))
        return found

    def test_only_the_helper_starts_a_process(self):
        sources = sorted(SCRIPTS.rglob("*.py"))
        self.assertIn(SCRIPTS / "feather_handoff" / "storage.py", sources)
        starts = {(path.relative_to(SCRIPTS).as_posix(), *start) for path in sources for start in self.scan(path)}
        self.assertEqual(starts, {("feather_handoff/storage.py", "run_git", "subprocess.run")})

    def test_the_scan_finds_a_process_start(self):
        # Abuse check for the scan itself: a second Git start, written several ways, would be caught.
        with tempfile.TemporaryDirectory() as temp:
            for source in ("import subprocess\ndef f():\n    subprocess.check_output(['git'])\n",
                           "import os\ndef f():\n    os.system('git status')\n",
                           "from subprocess import Popen\n",
                           "import subprocess as s\n",
                           "import asyncio\n"):
                with self.subTest(source=source):
                    path = Path(temp, "probe.py")
                    path.write_text(source, encoding="utf-8")
                    try:
                        found = self.scan(path)
                    except AssertionError:
                        continue  # refused at the import
                    self.assertTrue(found, "the scan missed a process start")


class GitHelperCallTest(unittest.TestCase):
    """C4 item 1: the helper's argument list, environment and error handling, with and without a Store."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.project = Path(os.path.realpath(temporary.name))
        self.addCleanup(storage.reset_roots)

    def test_helper_prefixes_every_command_and_keeps_the_environment_protections(self):
        completed = subprocess.CompletedProcess([], 0, "out\n", "")
        with mock.patch.object(storage.subprocess, "run", return_value=completed) as run, \
                mock.patch.dict(os.environ, {"GIT_DIR": "elsewhere", "GIT_INDEX_FILE": "elsewhere"}):
            # No Store exists yet: discovery calls the helper with a plain path.
            self.assertIs(storage.run_git(self.project, "rev-parse", "--show-toplevel", errors="replace"), completed)
            storage.run_git(self.project, "ls-files", "--", ".feather/handoffs/")
        first, second = run.call_args_list
        self.assertEqual(first.args[0], [*PREFIX, "-C", str(self.project), "rev-parse", "--show-toplevel"])
        self.assertEqual(second.args[0], [*PREFIX, "-C", str(self.project), "ls-files", "--", ".feather/handoffs/"])
        self.assertEqual({key: first.kwargs[key] for key in ("capture_output", "text", "encoding", "errors", "timeout")},
                         {"capture_output": True, "text": True, "encoding": "utf-8", "errors": "replace", "timeout": 5})
        self.assertEqual(second.kwargs["errors"], "strict")
        for call in (first, second):
            environment = call.kwargs["env"]
            self.assertNotIn("GIT_DIR", environment)
            self.assertNotIn("GIT_INDEX_FILE", environment)
            self.assertEqual((environment["GIT_OPTIONAL_LOCKS"], environment["LC_ALL"]), ("0", "C"))

    def test_helper_raises_what_the_process_start_raises(self):
        # Each caller keeps its own handling of a missing Git and a timeout.
        for error in (FileNotFoundError("git"), subprocess.TimeoutExpired(["git"], 5)):
            with self.subTest(error=type(error).__name__), \
                    mock.patch.object(storage.subprocess, "run", side_effect=error), self.assertRaises(type(error)):
                storage.run_git(self.project, "rev-parse", "--is-inside-work-tree")

    def test_discovery_tracking_and_observations_all_use_the_helper(self):
        try:
            subprocess.run(["git", "init", "--quiet", str(self.project)], check=True, capture_output=True, timeout=60)
        except (OSError, subprocess.SubprocessError) as error:
            self.skipTest(f"Git cannot set up the repository: {error}")
        (self.project / "a.txt").write_bytes(b"a\n")
        real, calls = subprocess.run, []

        def recorded(args, **kwargs):
            calls.append(list(args))
            return real(args, **kwargs)

        def invoke(*args, payload=None):
            out = io.StringIO()
            with mock.patch.object(sys, "argv", ["handoff", "--project", str(self.project), *args]), \
                    mock.patch.object(cli, "input_payload", return_value=payload), contextlib.redirect_stdout(out):
                cli.main()
            return json.loads(out.getvalue())
        with mock.patch.object(storage.subprocess, "run", side_effect=recorded):
            snapshot = invoke("snapshot", payload={"paths": ["a.txt"]})["snapshot"]
            created = invoke("create", "--work", "w.md", payload={"fields": FIELDS, "snapshot": snapshot})
            invoke("update", "--work", "w.md", payload={"version": created["version"], "tracking": "track"})
            invoke("compare", "--work", "w.md")
        self.assertEqual(created["status"], "ok", created)
        commands = {tuple(call[len(PREFIX) + 2:]) for call in calls}
        # Discovery, the tracking probe and rules, and the observation each ran through the helper.
        for expected in (("rev-parse", "--show-toplevel"), ("rev-parse", "--is-inside-work-tree"),
                         ("ls-files", "--", ".feather/handoffs/"), ("check-ignore", "-v", "--", ".feather/handoffs/w.md"),
                         ("check-ignore", "-q", "--", ".feather/handoffs/w.md"), ("symbolic-ref", "--quiet", "HEAD"),
                         ("rev-parse", "--verify", "--quiet", "HEAD")):
            self.assertIn(expected, commands)
        for call in calls:
            self.assertEqual(call[:len(PREFIX) + 2], [*PREFIX, "-C", str(self.project)], call)


class RepositoryChosenProgramTest(unittest.TestCase):
    """C4 item 3 (B6), regression and abuse check: a repository whose local configuration names an fsmonitor program
    and a clean filter, each leaving a marker outside the repository when run. The tool's list, read, create, update,
    snapshot and compare operations, through its command line, run neither, write no index, and return what they
    return in the same repository without that configuration."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(temporary.cleanup)
        self.root = Path(os.path.realpath(temporary.name))
        self.marker = self.root / "marker"
        (self.root / "home").mkdir()
        empty = self.root / "gitconfig"
        empty.write_bytes(b"")
        # Isolated from the user's global and system Git configuration; no inherited GIT_* variable reaches Git.
        self.env = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
        self.env.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": str(empty), "HOME": str(self.root / "home"),
                         "XDG_CONFIG_HOME": str(self.root / "home")})
        self.scripts = {}
        for name, body in (("monitor", "exit 1"), ("filter", "cat")):
            script = self.root / f"{name}.sh"
            script.write_text(f'#!/bin/sh\necho {name} >> "{self.marker.as_posix()}"\n{body}\n', encoding="utf-8",
                              newline="\n")
            script.chmod(0o755)
            self.scripts[name] = script.as_posix()

    def git(self, repo: Path, *args, check=True) -> subprocess.CompletedProcess:
        try:
            result = subprocess.run(["git", *args], cwd=repo, env={**self.env, **COMMIT_ENV}, stdin=subprocess.DEVNULL,
                                    capture_output=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired) as error:
            self.skipTest(f"Git cannot be run: {error}")
        if check:
            self.assertEqual(result.returncode, 0, (args, result.stderr))
        return result

    def repository(self, name: str) -> Path:
        repo = self.root / name
        repo.mkdir()
        # Setup runs with fsmonitor disabled and before the marker configuration exists.
        self.git(repo, "-c", "core.fsmonitor=", "init", "--quiet", "--initial-branch=main", ".")
        self.git(repo, "config", "core.autocrlf", "false")
        (repo / ".gitattributes").write_bytes(b"tracked.txt filter=marker\n")
        (repo / "tracked.txt").write_bytes(b"tracked\n")
        (repo / "other.txt").write_bytes(b"other\n")
        self.git(repo, "-c", "core.fsmonitor=", "add", "--", ".gitattributes", "tracked.txt", "other.txt")
        self.git(repo, "-c", "core.fsmonitor=", "-c", "commit.gpgSign=false", "commit", "--quiet", "--no-verify",
                 "-m", "fixture")
        return repo

    def ran(self) -> set[str]:
        found = set(self.marker.read_text(encoding="utf-8").split()) if self.marker.exists() else set()
        self.marker.unlink(missing_ok=True)
        return found

    def run_tool(self, repo: Path, *args, payload=None) -> dict:
        result = subprocess.run([sys.executable, "-B", str(TOOL), "--project", str(repo), *args],
                                input=json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload else b"",
                                capture_output=True, timeout=60, env=self.env)
        stdout = result.stdout.decode("utf-8")
        self.assertEqual(result.returncode, 0, stdout + result.stderr.decode("utf-8", "replace"))
        return json.loads(stdout)

    def normalized(self, repo: Path, value):
        """The result with the repository's own path and the capture time made comparable across repositories."""
        if isinstance(value, dict):
            return {key: CAPTURED if key == "captured_at" else self.normalized(repo, item) for key, item in value.items()}
        if isinstance(value, list):
            return [self.normalized(repo, item) for item in value]
        if isinstance(value, str):
            return value.replace(str(repo), "<repo>")
        return value

    def test_no_repository_chosen_program_runs_and_results_are_unchanged(self):
        plain, configured = self.repository("plain"), self.repository("configured")
        self.git(configured, "config", "core.fsmonitor", self.scripts["monitor"])
        self.git(configured, "config", "filter.marker.clean", self.scripts["filter"])
        self.assertEqual(self.ran(), set())
        # Positive control: an index-reading command the tool runs, without the helper's prefix, runs the monitor.
        self.git(configured, "ls-files", "--", ".feather/handoffs/", check=False)
        controls = self.ran()
        if "monitor" not in controls:
            self.skipTest("this Git ran no configured fsmonitor program for an index read")
        # The clean filter is a regression guard: none of the tool's current commands runs filters. Its control shows
        # that the configured filter does run when Git applies it, so its absence below means something.
        self.git(configured, "-c", "core.fsmonitor=", "hash-object", "--", "tracked.txt")
        self.assertEqual(self.ran(), {"filter"}, "the configured clean filter did not run in its control")
        indexes = {repo: (repo / ".git/index").read_bytes() for repo in (plain, configured)}

        results = {plain: {}, configured: {}}

        def step(label: str, *args, payload=None, status="ok") -> dict:
            """One operation in both repositories; returns the plain repository's result."""
            outcome = {}
            for repo in (plain, configured):
                result = self.run_tool(repo, *args, payload=payload(results[repo]) if callable(payload) else payload)
                results[repo][label] = result
                outcome[repo] = self.normalized(repo, result)
                self.assertEqual(self.ran(), set(), f"{label} ran a program the repository configured")
            self.assertEqual(outcome[configured], outcome[plain], label)
            self.assertEqual(outcome[plain]["status"], status, outcome[plain])
            return results[plain][label]

        # Before any work exists, list reports the handoff directory as missing.
        step("list-empty", "list", status="missing")
        snapshot = step("snapshot", "snapshot", payload={"paths": ["tracked.txt", "other.txt", "missing.txt"]})
        self.assertEqual(snapshot["snapshot"]["git"]["state"], "available")
        # One baseline for both repositories, so the saved records and their versions are comparable.
        value = {**snapshot["snapshot"], "captured_at": CAPTURED}
        created = step("create", "create", "--work", "w.md", payload={"title": "w", "fields": FIELDS, "snapshot": value})
        self.assertEqual(created["tracking"], "ignored")
        step("read", "read", "--work", "w.md")
        updated = step("update", "update", "--work", "w.md", payload=lambda previous: {
            "version": previous["create"]["version"], "tracking": "track", "fields": {"next": "m", "updated": UPDATED}})
        self.assertEqual(updated["tracking"], "track")
        compared = step("compare", "compare", "--work", "w.md")
        self.assertEqual(compared["git"]["comparison"], "unchanged")
        self.assertEqual([item["comparison"] for item in compared["files"]], ["unchanged"] * 3)
        step("list", "list")
        for repo, index in indexes.items():
            self.assertEqual((repo / ".git/index").read_bytes(), index, f"{repo.name}: the tool wrote Git's index")


if __name__ == "__main__":
    unittest.main()
