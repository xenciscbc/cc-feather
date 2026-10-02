"""Linked project ancestors resolve once; links inside the project stay refused (local, not upstream)."""
import contextlib
import errno
import io
import json
import os
from pathlib import Path
import shutil
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
from feather_handoff.writing import create_work  # noqa: E402

FIELDS = {"fields": {"goal": "g", "progress": "p", "next": "n"}}
CROSSES = "the path crosses a link below the repository root; confirm with --exact-root"


def make_link(test: unittest.TestCase, link: Path, target: Path) -> None:
    """Directory junction on Windows, symlink elsewhere; skip only when neither can be created."""
    errors = []
    if os.name == "nt":
        try:
            import _winapi
            _winapi.CreateJunction(str(target), str(link))
            return
        except OSError as error:
            errors.append(error)
    try:
        os.symlink(target, link, target_is_directory=True)
        return
    except OSError as error:
        errors.append(error)
    test.skipTest(f"Directory links unavailable: {errors}")


class LinkBase(unittest.TestCase):
    """Tests run under FEATHER_LINK_TEST_DIR when set; volumes without strict realpath are skipped."""

    # False for tests that mock strict realpath themselves; they run on every volume.
    requires_strict_realpath = True

    def setUp(self):
        configured = os.environ.get("FEATHER_LINK_TEST_DIR")
        if configured:
            os.makedirs(configured, exist_ok=True)
            base = tempfile.mkdtemp(dir=configured)
            self.addCleanup(shutil.rmtree, base, True)
        else:
            temporary = tempfile.TemporaryDirectory()
            self.addCleanup(temporary.cleanup)
            base = temporary.name
        try:
            self.base = Path(os.path.realpath(base, strict=True))
        except OSError:
            if self.requires_strict_realpath:
                self.skipTest("strict realpath unsupported")
            self.base = Path(os.path.realpath(base))
        self.addCleanup(storage.reset_roots)

    def run_tool(self, project, *args, payload=None, expected=0, exact=False):
        result = subprocess.run(
            [sys.executable, "-B", str(TOOL), "--project", str(project), *(["--exact-root"] if exact else []), *args],
            input=json.dumps(payload, ensure_ascii=False) if payload is not None else None,
            capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def git_init(self, path: Path) -> None:
        subprocess.run(["git", "init", "--quiet", str(path)], check=True, capture_output=True)

    def tree(self, path: Path) -> dict:
        result = {}
        for directory, names, files in os.walk(path):
            names[:] = [name for name in names if name != ".git"]
            for name in files:
                item = Path(directory, name)
                result[item.relative_to(path).as_posix()] = item.read_bytes()
        return result


class LinkedAncestorTest(LinkBase):
    def test_linked_ancestor_is_resolved_once_and_writes_land_in_the_real_project(self):
        real = self.base / "real"
        (real / "project").mkdir(parents=True)
        make_link(self, self.base / "link", real)
        requested = self.base / "link" / "project"
        listed = self.run_tool(requested, "list")
        self.assertEqual(listed["root"], {"requested": str(requested), "path": str(real / "project"), "state": "non-git"})
        created = self.run_tool(requested, "create", "--work", "w.md", payload=FIELDS)
        self.assertEqual(created["root"]["path"], str(real / "project"))
        self.assertTrue((real / "project/.feather/handoffs/w.md").is_file())
        self.assertEqual(self.run_tool(requested, "read", "--work", "w.md")["version"], created["version"])

    def test_project_that_is_itself_a_link_is_resolved(self):
        (self.base / "real").mkdir()
        make_link(self, self.base / "alias", self.base / "real")
        created = self.run_tool(self.base / "alias", "create", "--work", "w.md", payload=FIELDS)
        self.assertEqual((created["root"]["requested"], created["root"]["path"]),
                         (str(self.base / "alias"), str(self.base / "real")))
        self.assertTrue((self.base / "real/.feather/handoffs/w.md").is_file())

    def test_link_inside_the_project_is_refused(self):
        project, outside = self.base / "project", self.base / "outside"
        project.mkdir()
        outside.mkdir()
        make_link(self, project / ".feather", outside)
        for args, payload in ((("list",), None), (("create", "--work", "w.md"), FIELDS)):
            with self.subTest(args=args):
                result = self.run_tool(project, *args, payload=payload, expected=2)
                self.assertEqual((result["status"], result["code"]), ("error", "unsafe-path"))
        self.assertEqual(self.tree(outside), {})

    def test_root_that_resolves_elsewhere_after_init_is_refused(self):
        project, other = self.base / "project", self.base / "other"
        project.mkdir()
        other.mkdir()
        store = storage.Store(str(project))
        real = os.path.realpath

        def moved(path, *args, **kwargs):
            return str(other) if os.path.normcase(str(path)) == os.path.normcase(str(project)) else real(path, *args, **kwargs)
        with mock.patch.object(storage.os.path, "realpath", side_effect=moved), \
                self.assertRaises(storage.HandoffError) as raised:
            create_work(store, "w.md", FIELDS)
        self.assertEqual(raised.exception.code, "unsafe-path")
        self.assertIn("Project root changed after it was resolved", str(raised.exception))
        self.assertEqual(self.tree(project), {})
        self.assertEqual(self.tree(other), {})

    def test_repointed_ancestor_does_not_redirect_writes(self):
        for name in ("one", "two"):
            (self.base / name / "project").mkdir(parents=True)
        link = self.base / "link"
        make_link(self, link, self.base / "one")
        store = storage.Store(str(link / "project"))
        self.assertEqual(store.project, self.base / "one" / "project")
        os.unlink(link)
        make_link(self, link, self.base / "two")
        try:
            create_work(store, "w.md", FIELDS)
        except storage.HandoffError as error:
            self.assertIn("Project root changed after it was resolved", str(error))
        else:
            self.assertTrue((self.base / "one/project/.feather/handoffs/w.md").is_file())
        self.assertEqual(self.tree(self.base / "two"), {})
        # Replacing the resolved root itself is detected before any write.
        before = self.tree(self.base / "one")
        os.rename(self.base / "one" / "project", self.base / "one" / "moved")
        make_link(self, self.base / "one" / "project", self.base / "two" / "project")
        with self.assertRaises(storage.HandoffError) as raised:
            create_work(store, "x.md", FIELDS)
        self.assertIn("Project root changed after it was resolved", str(raised.exception))
        self.assertEqual(self.tree(self.base / "two"), {})
        self.assertEqual(self.tree(self.base / "one" / "moved"), {k.removeprefix("project/"): v for k, v in before.items()})


class UnsupportedStrictRealpathTest(LinkBase):
    """Strict realpath is mocked away, so these run even where the volume cannot resolve it."""

    requires_strict_realpath = False

    def test_volume_without_strict_realpath_keeps_full_link_checks(self):
        real = self.base / "real"
        (real / "project").mkdir(parents=True)
        make_link(self, self.base / "link", real)
        original = os.path.realpath

        def unsupported(path, *args, strict=False, **kwargs):
            if strict:
                raise OSError(errno.EINVAL, "Incorrect function", str(path), 1)
            return original(path, *args, **kwargs)
        with mock.patch.object(storage.os.path, "realpath", side_effect=unsupported):
            with self.assertRaises(storage.HandoffError) as raised:
                storage.Store(str(self.base / "link" / "project"))
            self.assertEqual(raised.exception.code, "unsafe-path")
            self.assertIn("Link/reparse path is not supported", str(raised.exception))
            store = storage.Store(str(real / "project"))
        self.assertEqual(store.root["state"], "non-git")
        self.assertNotIn(os.path.normcase(str(store.project)), storage._ROOTS)


class GitTopLevelOutputTest(LinkBase):
    """HF2: Git succeeding without an absolute top level never selects the working directory as root."""

    requires_strict_realpath = False

    def invoke(self, project: Path, *args, payload=None) -> tuple[int, dict]:
        out = io.StringIO()
        with mock.patch.object(sys, "argv", ["handoff", "--project", str(project), *args]), \
                mock.patch.object(cli, "input_payload", return_value=payload), contextlib.redirect_stdout(out):
            code = cli.main()
        return code, json.loads(out.getvalue())

    def test_empty_top_level_output_is_uncertain_and_create_writes_nothing(self):
        def empty_top_level(args, **kwargs):
            if args[-1] != "--show-toplevel":
                raise AssertionError(f"Unexpected Git call: {args}")
            return subprocess.CompletedProcess(args, 0, "\n", "")
        original = os.path.realpath

        def unsupported(path, *args, strict=False, **kwargs):
            if strict:
                raise OSError(errno.EINVAL, "Incorrect function", str(path), 1)
            return original(path, *args, **kwargs)
        self.addCleanup(os.chdir, os.getcwd())
        for label in ("strict realpath", "strict realpath unsupported"):
            with self.subTest(label):
                if label == "strict realpath":
                    try:
                        os.path.realpath(self.base, strict=True)
                    except OSError:
                        self.skipTest("strict realpath unsupported")
                project = self.base / label.replace(" ", "-")
                project.mkdir()
                (project / "source.txt").write_bytes(b"kept")
                before = self.tree(project)
                # An empty answer must not fall back to the process working directory.
                os.chdir(project)
                with contextlib.ExitStack() as stack:
                    stack.enter_context(mock.patch.object(storage.subprocess, "run", side_effect=empty_top_level))
                    if label != "strict realpath":
                        stack.enter_context(mock.patch.object(storage.os.path, "realpath", side_effect=unsupported))
                    code, result = self.invoke(project, "create", "--work", "w.md", payload=FIELDS)
                self.assertEqual((code, result["status"], result["code"]), (2, "error", "project-root-uncertain"))
                self.assertEqual(result["root"]["state"], "uncertain")
                self.assertEqual(result["root"]["reason"], storage.NO_TOP_LEVEL)
                self.assertEqual(self.tree(project), before)
                self.assertFalse((project / ".feather").exists())


class GitRootTest(LinkBase):
    def test_plain_subdirectory_selects_the_repository_root(self):
        repo = self.base / "repo"
        (repo / "a" / "b").mkdir(parents=True)
        self.git_init(repo)
        listed = self.run_tool(repo / "a" / "b", "list")
        self.assertEqual((listed["root"]["state"], listed["root"]["path"]), ("git", str(repo)))
        self.run_tool(repo / "a" / "b", "create", "--work", "w.md", payload=FIELDS)
        self.assertTrue((repo / ".feather/handoffs/w.md").is_file())

    def test_linked_ancestor_above_the_repository_is_resolved(self):
        repo = self.base / "real" / "repo"
        (repo / "sub").mkdir(parents=True)
        self.git_init(repo)
        make_link(self, self.base / "link", self.base / "real")
        requested = self.base / "link" / "repo" / "sub"
        created = self.run_tool(requested, "create", "--work", "w.md", payload=FIELDS)
        self.assertEqual(created["root"], {"requested": str(requested), "path": str(repo), "state": "git"})
        self.assertTrue((repo / ".feather/handoffs/w.md").is_file())

    def test_link_below_the_repository_root_is_uncertain(self):
        repo = self.base / "repo"
        (repo / "target").mkdir(parents=True)
        self.git_init(repo)
        make_link(self, repo / "alias", repo / "target")
        listed = self.run_tool(repo / "alias", "list", expected=2)
        self.assertEqual(listed["root"]["state"], "uncertain")
        self.assertEqual(listed["root"]["reason"], CROSSES)
        self.assertEqual(listed["root"]["path"], str(repo / "target"))
        before = self.tree(repo)
        refused = self.run_tool(repo / "alias", "create", "--work", "w.md", payload=FIELDS, expected=2)
        self.assertEqual(refused["code"], "project-root-uncertain")
        self.assertEqual(self.tree(repo), before)
        created = self.run_tool(repo / "target", "create", "--work", "w.md", payload=FIELDS, exact=True)
        self.assertEqual((created["root"]["state"], created["root"]["path"]), ("explicit", str(repo / "target")))
        self.assertTrue((repo / "target/.feather/handoffs/w.md").is_file())


if __name__ == "__main__":
    unittest.main()
