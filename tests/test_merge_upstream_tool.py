"""The merge-upstream fact tool at its command line (merge-upstream ticket 01).

The tool runs as a subprocess with --project and one JSON object on stdin, and only its JSON result, its exit status
and the repositories' unchanged state are asserted. Disposable repositories are built under a unique directory made
with mkdtemp under FEATHER_LINK_TEST_DIR when it is set, otherwise the system temporary directory, always outside the
project directory, with an isolated Git environment (GIT_CONFIG_NOSYSTEM, an empty GIT_CONFIG_GLOBAL, HOME and
XDG_CONFIG_HOME inside the base, inherited GIT_* removed), synthetic data only, bare remotes reached only through
file:// URLs (protocol.file.allow=always for the submodule, uploadpack.allowFilter for the partial clone), and the
base removed on cleanup.

The shared fixture: a bare remote whose main branch an "upstream" clone moves after the work clone branched; the work
clone holds two Claims' commits and one commit no Claim owns, then merges the fetched remote tip with --no-ff,
resolving a conflict in a Claim's file and one in a file no Claim owns, and changing one more file in the merge
itself. Upstream's commit renames, deletes, changes a mode, turns a file into a symbolic link, bumps a submodule,
changes test support and build configuration, and changes a Claim's file cleanly. The merge commit is pushed only to
a second remote. Cases that change configuration work on a copy."""
import hashlib
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
TOOL = ROOT / "skills/merge-upstream/scripts/merge_upstream.py"
TIMEOUT = 120
COMMIT_ENV = {"GIT_AUTHOR_NAME": "Fixture", "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
              "GIT_COMMITTER_NAME": "Fixture", "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
              "GIT_AUTHOR_DATE": "2026-11-19T10:00:00+08:00", "GIT_COMMITTER_DATE": "2026-11-19T10:00:00+08:00"}
NO_LAZY_FETCH_FROM = (2, 45, 0)
# Git commands that would fetch, push, merge or write a ref, the index or an object; none may run under the tool.
WRITING_COMMANDS = {"fetch", "fetch-pack", "pull", "push", "send-pack", "upload-pack", "receive-pack", "index-pack",
                    "unpack-objects", "merge", "merge-tree", "merge-recursive", "update-ref", "update-index",
                    "write-tree", "commit-tree", "hash-object", "gc", "maintenance", "repack", "commit-graph",
                    "pack-refs", "prune", "reset", "checkout", "switch", "read-tree", "stash", "commit", "rebase",
                    "remote-http", "remote-https", "remote-ext", "remote-fd"}


def remove_tree(base: Path) -> None:
    """Remove the tree, clearing the read-only attribute Git gives its object files on Windows."""
    def writable(function, path, *_):
        os.chmod(path, stat.S_IREAD | stat.S_IWRITE)
        function(path)
    if sys.version_info >= (3, 12):
        shutil.rmtree(base, onexc=writable)
    else:
        shutil.rmtree(base, onerror=writable)


def snapshot(path: Path) -> dict:
    """Every directory and file under path, files with size, modification time and content hash."""
    found = {}
    for current, directories, files in os.walk(path):
        directories.sort()
        for name in directories:
            found[os.path.relpath(os.path.join(current, name), path)] = "directory"
        for name in sorted(files):
            full = os.path.join(current, name)
            info = os.lstat(full)
            with open(full, "rb") as handle:
                digest = hashlib.sha256(handle.read()).hexdigest()
            found[os.path.relpath(full, path)] = (info.st_size, info.st_mtime_ns, digest)
    return found


def unknown_parts(value, where="result"):
    """Every (location, part) whose state is unknown, anywhere in a result."""
    found = []
    if isinstance(value, dict):
        if value.get("state") == "unknown":
            found.append((where, value))
        for key, item in value.items():
            found.extend(unknown_parts(item, f"{where}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(unknown_parts(item, f"{where}[{index}]"))
    return found


def paths(part: dict) -> list[str]:
    return [change["path"] for change in part["changes"]]


def by_path(part: dict) -> dict:
    return {change["path"]: change for change in part["changes"]}


class MergeUpstreamBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        configured = os.environ.get("FEATHER_LINK_TEST_DIR")
        if configured:
            os.makedirs(configured, exist_ok=True)
        base = Path(os.path.realpath(tempfile.mkdtemp(dir=configured or None)))
        cls.addClassCleanup(remove_tree, base)
        if os.path.normcase(str(base)).startswith(os.path.normcase(str(ROOT)) + os.sep):
            raise unittest.SkipTest(f"the test directory {base} is inside the project; set FEATHER_LINK_TEST_DIR")
        cls.base = base
        (base / "home").mkdir()
        empty = base / "gitconfig"
        empty.write_bytes(b"")
        environment = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
        environment.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": str(empty), "HOME": str(base / "home"),
                            "XDG_CONFIG_HOME": str(base / "home")})
        cls.enterClassContext(mock.patch.dict(os.environ, environment, clear=True))
        cls.git_version = cls.installed_git_version()
        cls.build()

    @staticmethod
    def installed_git_version() -> tuple:
        try:
            reported = subprocess.run(["git", "version"], capture_output=True, text=True, timeout=60).stdout
        except (OSError, subprocess.TimeoutExpired) as error:
            raise unittest.SkipTest(f"Git cannot be run: {error}")
        match = re.match(r"git version (\d+)\.(\d+)\.(\d+)", reported.strip())
        if not match:
            raise unittest.SkipTest(f"the Git version cannot be read: {reported!r}")
        return tuple(map(int, match.groups()))

    @classmethod
    def git(cls, cwd: Path, *args: str, check: bool = True, input: str | None = None) -> str:
        result = subprocess.run(["git", "-c", "core.fsmonitor=", *args], cwd=cwd, env={**os.environ, **COMMIT_ENV},
                                input=input, stdin=None if input is not None else subprocess.DEVNULL,
                                capture_output=True, text=True, encoding="utf-8", timeout=60)
        if check and result.returncode:
            raise AssertionError(f"git {args} failed in {cwd}: {result.stderr}")
        return result.stdout.strip()

    @classmethod
    def write(cls, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))

    @classmethod
    def commit(cls, cwd: Path, *files: str, message: str = "fixture") -> str:
        if files:
            cls.git(cwd, "add", "--", *files)
        cls.git(cwd, "-c", "commit.gpgSign=false", "commit", "--quiet", "--no-verify", "-m", message)
        return cls.git(cwd, "rev-parse", "HEAD")

    @classmethod
    def clone(cls, url: str, path: Path, *options: str) -> Path:
        cls.git(cls.base, "clone", "--quiet", *options, url, str(path))
        cls.git(path, "config", "core.autocrlf", "false")
        return path

    @classmethod
    def build(cls):
        base = cls.base
        # The submodule's own repository, reached through a bare remote.
        sub_source = base / "sub-source"
        sub_source.mkdir()
        cls.git(sub_source, "init", "--quiet", "--initial-branch=main", ".")
        cls.write(sub_source / "lib.txt", "lib 1\n")
        cls.commit(sub_source, "lib.txt")
        cls.git(base, "clone", "--quiet", "--bare", str(sub_source), "sub.git")
        cls.sub_url = (base / "sub.git").as_uri()

        cls.remote = base / "remote.git"
        cls.git(base, "init", "--quiet", "--bare", "--initial-branch=main", str(cls.remote))
        cls.remote_url = cls.remote.as_uri()

        upstream = cls.clone(cls.remote_url, base / "upstream")
        cls.git(upstream, "switch", "--quiet", "-c", "main")
        files = {"src/a.py": "a1\n", "src/b.py": "".join(f"b{n}\n" for n in range(1, 11)), "src/c.py": "c1\nc2\n",
                 "docs/free.txt": "free\n", "rename_me.txt": "rename\n", "delete_me.txt": "delete\n",
                 "script.sh": "echo\n", "kind.txt": "target\n", "tests/test_x.py": "x = 1\n",
                 "pyproject.toml": "[project]\n"}
        for name, text in files.items():
            cls.write(upstream / name, text)
        cls.git(upstream, "-c", "protocol.file.allow=always", "submodule", "add", "--quiet", cls.sub_url, "sub")
        cls.git(upstream / "sub", "config", "core.autocrlf", "false")
        cls.start = cls.commit(upstream, *files, ".gitmodules", "sub", message="start")
        cls.git(upstream, "push", "--quiet", "origin", "main")

        cls.work = cls.clone(cls.remote_url, base / "work")
        cls.git(cls.work, "config", "--replace-all", "remote.origin.fetch", "+refs/heads/main:refs/remotes/origin/main")
        cls.git(cls.work, "switch", "--quiet", "-c", "work")
        cls.write(cls.work / "src/b.py", "".join(f"b{n}\n" for n in range(1, 11)).replace("b1\n", "B1\n", 1))
        cls.write(cls.work / "src/only_claim.py", "only\n")
        cls.claim1 = cls.commit(cls.work, "src/b.py", "src/only_claim.py", message="claim 1")
        cls.write(cls.work / "src/c.py", "work c1\nc2\n")
        cls.claim2 = cls.commit(cls.work, "src/c.py", message="claim 2")
        cls.write(cls.work / "docs/free.txt", "work free\n")
        cls.tip_before = cls.commit(cls.work, "docs/free.txt", message="no claim")

        cls.write(upstream / "src/b.py", "".join(f"b{n}\n" for n in range(1, 11)).replace("b10\n", "B10\n"))
        cls.write(upstream / "src/c.py", "upstream c1\nc2\n")
        cls.write(upstream / "docs/free.txt", "upstream free\n")
        cls.write(upstream / "tests/test_x.py", "x = 2\n")
        cls.write(upstream / "pyproject.toml", "[project]\nname = \"x\"\n")
        cls.git(upstream, "add", "--", "src/b.py", "src/c.py", "docs/free.txt", "tests/test_x.py", "pyproject.toml")
        cls.git(upstream, "mv", "rename_me.txt", "renamed.txt")
        cls.git(upstream, "rm", "--quiet", "delete_me.txt")
        cls.git(upstream, "update-index", "--chmod=+x", "script.sh")
        link = cls.git(upstream, "hash-object", "-w", "--stdin", input="link-target")
        cls.git(upstream, "update-index", "--cacheinfo", f"120000,{link},kind.txt")
        cls.write(upstream / "sub/lib.txt", "lib 2\n")
        cls.commit(upstream / "sub", "lib.txt", message="lib 2")
        cls.git(upstream, "add", "sub")
        cls.remote_tip = cls.commit(upstream, message="upstream")
        cls.git(upstream, "push", "--quiet", "origin", "main")

        cls.git(cls.work, "fetch", "--quiet", "origin")
        cls.git(cls.work, "-c", "commit.gpgSign=false", "merge", "--no-ff", "--no-commit", cls.remote_tip,
                check=False)
        cls.write(cls.work / "src/c.py", "resolved c1\nc2\n")
        cls.write(cls.work / "docs/free.txt", "upstream free\n")
        cls.write(cls.work / "src/a.py", "a1 merged\n")
        cls.merge = cls.commit(cls.work, "src/c.py", "docs/free.txt", "src/a.py", message="merge upstream")

        cls.second = base / "second.git"
        cls.git(base, "init", "--quiet", "--bare", str(cls.second))
        cls.git(cls.work, "remote", "add", "second", cls.second.as_uri())
        cls.git(cls.work, "push", "--quiet", "second", "HEAD:refs/heads/integration")
        cls.git(cls.work, "remote", "add", "empty", (base / "never-fetched.git").as_uri())

    # Running the tool -----------------------------------------------------------------------------------------------

    def payload(self, **changes) -> dict:
        claims = [
            {"id": "01", "base": self.start, "judged": [self.claim1]},
            {"id": "02", "base": self.claim1, "judged": [self.claim2]},
            {"id": "fix-1", "kind": "fix", "base": None, "judged": []},
            {"id": "03", "kind": "cancelled", "base": self.claim1, "judged": ["f" * 40]},
        ]
        return {"remote": "origin", "default_branch": "main", "remote_tip": self.remote_tip,
                "tip_before": self.tip_before, "merge_commit": self.merge, "claims": claims, **changes}

    def run_tool(self, project: Path, payload=None, *, raw: str | None = None, expected: int = 0,
                 env: dict | None = None) -> dict:
        text = raw if raw is not None else json.dumps(payload if payload is not None else self.payload())
        result = subprocess.run([sys.executable, "-B", str(TOOL), "--project", str(project)], input=text,
                                capture_output=True, text=True, encoding="utf-8", timeout=TIMEOUT,
                                env={**os.environ, **(env or {})})
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        output = json.loads(result.stdout)
        self.assertIsInstance(output, dict)
        for where, part in unknown_parts(output):
            self.assertTrue(part.get("reason"), f"{where} is unknown without a reason: {part}")
            self.assertFalse({"changes", "paths", "remotes", "ranges"} & part.keys(),
                             f"{where} is unknown but carries a list: {part}")
        return output

    def copy_work(self, name: str) -> Path:
        target = self.base / name
        shutil.copytree(self.work, target, symlinks=True)
        self.addCleanup(remove_tree, target)
        return target


class ListsTest(MergeUpstreamBase):
    def setUp(self):
        self.result = self.run_tool(self.work)
        self.assertEqual(self.result["status"], "ok", self.result)

    def test_commits_parents_and_merge_base_are_checked(self):
        result = self.result
        for name in ("remote_tip", "tip_before", "merge_commit"):
            self.assertEqual(result["commits"][name]["state"], "known", result["commits"])
        self.assertEqual(result["merge_parents"]["parents"], [self.tip_before, self.remote_tip])
        self.assertTrue(result["merge_parents"]["as_expected"])
        self.assertEqual(result["merge_base"], {"state": "known", "commit": self.start})

    def test_upstream_lists_every_change_with_status_modes_and_submodule(self):
        upstream = self.result["upstream"]
        self.assertEqual((upstream["state"], upstream["from"], upstream["to"]), ("known", self.start, self.remote_tip))
        changes = by_path(upstream)
        self.assertEqual(sorted(changes), ["delete_me.txt", "docs/free.txt", "kind.txt", "pyproject.toml",
                                           "rename_me.txt", "renamed.txt", "script.sh", "src/b.py", "src/c.py",
                                           "sub", "tests/test_x.py"])
        # Both sides of the rename, renames not detected.
        self.assertEqual((changes["rename_me.txt"]["status"], changes["renamed.txt"]["status"]),
                         ("deleted", "added"))
        self.assertEqual((changes["delete_me.txt"]["status"], changes["delete_me.txt"]["new_mode"]),
                         ("deleted", None))
        mode = changes["script.sh"]
        self.assertEqual((mode["status"], mode["old_mode"], mode["new_mode"], mode["mode_changed"]),
                         ("modified", "100644", "100755", True))
        kind = changes["kind.txt"]
        self.assertEqual((kind["status"], kind["old_kind"], kind["new_kind"]), ("type-changed", "file", "symlink"))
        sub = changes["sub"]
        self.assertEqual((sub["status"], sub["old_mode"], sub["new_mode"], sub["new_kind"]),
                         ("modified", "160000", "160000", "submodule"))
        self.assertNotEqual(sub["old_object"], sub["new_object"])
        self.assertNotIn("src/a.py", changes)
        self.assertNotIn("src/only_claim.py", changes)

    def test_merge_result_is_taken_from_the_tip_before_the_merge(self):
        merge_result = self.result["merge_result"]
        self.assertEqual((merge_result["state"], merge_result["from"], merge_result["to"]),
                         ("known", self.tip_before, self.merge))
        changes = by_path(merge_result)
        # The change the merge itself made, which upstream never made, and the conflict resolutions.
        self.assertIn("src/a.py", changes)
        self.assertNotIn("src/a.py", paths(self.result["upstream"]))
        self.assertIn("src/c.py", changes)
        self.assertIn("docs/free.txt", changes)
        # Upstream's changes reach the work branch through the merge; the work branch's own commits do not appear.
        for name in ("rename_me.txt", "renamed.txt", "delete_me.txt", "script.sh", "kind.txt", "sub", "src/b.py"):
            self.assertIn(name, changes)
        self.assertNotIn("src/only_claim.py", changes)

    def test_resolution_paths_are_those_both_sides_changed(self):
        resolution = self.result["resolution"]
        self.assertEqual(resolution["state"], "known")
        found = {entry["path"]: entry for entry in resolution["paths"]}
        self.assertEqual(sorted(found), ["docs/free.txt", "src/b.py", "src/c.py"])
        flags = {path: (entry["merge_differs_from_tip_before"], entry["merge_differs_from_remote_tip"])
                 for path, entry in found.items()}
        self.assertEqual(flags, {"src/b.py": (True, True), "src/c.py": (True, True),
                                 "docs/free.txt": (True, False)})

    def test_every_claim_appears(self):
        claims = {claim["id"]: claim for claim in self.result["claims"]}
        self.assertEqual(list(claims), ["01", "02", "fix-1", "03"])
        first = claims["01"]
        self.assertEqual(first["state"], "known")
        self.assertEqual(first["paths"], ["src/b.py", "src/only_claim.py"])
        self.assertEqual(first["overlap"]["upstream"], {"state": "known", "paths": ["src/b.py"]})
        self.assertEqual(first["overlap"]["merge_result"], {"state": "known", "paths": ["src/b.py"]})
        self.assertEqual([(entry["from"], entry["to"]) for entry in first["ranges"]], [(self.start, self.claim1)])
        second = claims["02"]
        self.assertEqual(second["paths"], ["src/c.py"])
        self.assertEqual(second["overlap"]["upstream"]["paths"], ["src/c.py"])
        self.assertEqual(second["overlap"]["merge_result"]["paths"], ["src/c.py"])
        self.assertEqual((claims["fix-1"]["state"], claims["fix-1"]["kind"]), ("not-implemented", "fix"))
        self.assertEqual(claims["03"]["state"], "unknown")
        self.assertIn("f" * 40, claims["03"]["reason"])

    def test_test_support_and_build_configuration_are_classed_as_advice(self):
        classification = self.result["classification"]
        self.assertIs(classification["advice"], True)
        self.assertTrue(classification["rule"])
        classed = {entry["path"]: entry["classes"] for entry in classification["upstream"]["paths"]}
        self.assertIn("test-support", classed["tests/test_x.py"])
        self.assertIn("build-configuration", classed["pyproject.toml"])
        self.assertNotIn("src/b.py", classed)
        self.assertIn("tests/test_x.py", {entry["path"] for entry in classification["merge_result"]["paths"]})

    def test_each_remote_says_whether_the_merge_commit_is_on_its_tracking_refs(self):
        tracking = self.result["remote_tracking"]
        self.assertEqual(tracking["state"], "known")
        remotes = {entry["remote"]: entry for entry in tracking["remotes"]}
        self.assertEqual(sorted(remotes), ["empty", "origin", "second"])
        self.assertEqual((remotes["origin"]["state"], remotes["origin"]["contains_merge_commit"]), ("known", False))
        self.assertEqual((remotes["second"]["state"], remotes["second"]["contains_merge_commit"]), ("known", True))
        self.assertEqual(remotes["second"]["containing"], ["refs/remotes/second/integration"])
        self.assertEqual(remotes["empty"]["state"], "unknown")
        default = self.result["default_branch_ref"]
        self.assertEqual((default["state"], default["ref"], default["commit"], default["is_remote_tip"]),
                         ("known", "refs/remotes/origin/main", self.remote_tip, True))


class SettingsTest(MergeUpstreamBase):
    def test_diff_settings_and_the_directory_change_no_list(self):
        def facts(result: dict) -> dict:
            return {key: value for key, value in result.items() if key != "project"}
        baseline = self.run_tool(self.work)
        copy = self.copy_work("settings")
        for key, value in (("diff.relative", "true"), ("diff.renames", "copies"), ("diff.ignoreSubmodules", "all"),
                           ("submodule.sub.ignore", "all"), ("pull.rebase", "true"), ("diff.noprefix", "true"),
                           ("diff.external", "false"), ("status.relativePaths", "true")):
            self.git(copy, "config", key, value)
        (copy / ".gitmodules").write_text((copy / ".gitmodules").read_text() + "\tignore = all\n")
        (copy / ".gitattributes").write_text("*.py diff=shout\n")
        self.git(copy, "config", "diff.shout.textconv", "false")
        moved = self.run_tool(copy / "src")
        self.assertEqual(moved["project"], str(copy))
        self.assertEqual(facts(moved), facts(baseline))


class ChecksTest(MergeUpstreamBase):
    def test_wrong_parent_order_makes_the_dependent_lists_unknown(self):
        result = self.run_tool(self.work, self.payload(tip_before=self.remote_tip, remote_tip=self.tip_before))
        self.assertFalse(result["merge_parents"]["as_expected"])
        for name in ("upstream", "merge_result", "resolution"):
            self.assertEqual(result[name]["state"], "unknown", result[name])
            self.assertIn("parents", result[name]["reason"])
        claim = result["claims"][0]
        self.assertEqual((claim["state"], claim["paths"]), ("known", ["src/b.py", "src/only_claim.py"]))
        self.assertEqual(claim["overlap"]["upstream"]["state"], "unknown")
        self.assertEqual(result["classification"]["upstream"]["state"], "unknown")

    def test_a_commit_that_is_not_a_merge_makes_the_dependent_lists_unknown(self):
        result = self.run_tool(self.work, self.payload(merge_commit=self.claim2))
        self.assertEqual(result["merge_parents"]["parents"], [self.claim1])
        for name in ("upstream", "merge_result", "resolution"):
            self.assertEqual(result[name]["state"], "unknown", result[name])

    def test_an_unknown_commit_is_unknown_with_the_reason(self):
        missing = "e" * 40
        result = self.run_tool(self.work, self.payload(merge_commit=missing))
        self.assertEqual(result["commits"]["merge_commit"]["state"], "unknown")
        self.assertIn(missing, result["commits"]["merge_commit"]["reason"])
        for name in ("merge_parents", "upstream", "merge_result", "resolution", "remote_tracking"):
            self.assertEqual(result[name]["state"], "unknown", result[name])
        self.assertEqual(len(result["claims"]), 4)
        result = self.run_tool(self.work, self.payload(remote_tip=missing))
        self.assertEqual(result["merge_base"]["state"], "unknown")
        self.assertEqual(result["upstream"]["state"], "unknown")

    def test_a_missing_remote_ref_is_unknown(self):
        result = self.run_tool(self.work, self.payload(default_branch="nosuch", remote="other"))
        self.assertEqual(result["default_branch_ref"]["state"], "unknown")
        self.assertIn("refs/remotes/other/nosuch", result["default_branch_ref"]["reason"])
        remotes = {entry["remote"]: entry for entry in result["remote_tracking"]["remotes"]}
        self.assertEqual(remotes["other"]["state"], "unknown")

    def tracking(self, project: Path) -> dict:
        result = self.run_tool(project)
        self.assertEqual(result["remote_tracking"]["state"], "known", result["remote_tracking"])
        return {entry["remote"]: entry for entry in result["remote_tracking"]["remotes"]}

    def own_origin(self, project: Path, name: str) -> None:
        origin = self.base / f"{name}.git"
        self.git(self.base, "clone", "--quiet", "--bare", str(self.remote), str(origin))
        self.addCleanup(remove_tree, origin)
        self.git(project, "remote", "set-url", "origin", origin.as_uri())

    def test_a_tracking_ref_is_the_remotes_by_its_fetch_refspec_not_its_name(self):
        copy = self.copy_work("refspec-origin")
        self.own_origin(copy, "refspec-origin")
        self.git(copy, "config", "--add", "remote.origin.fetch", "+refs/heads/*:refs/remotes/origin-all/*")
        self.git(copy, "push", "--quiet", "origin", f"{self.merge}:refs/heads/work")
        self.git(copy, "fetch", "--quiet", "origin")
        self.assertIn("origin-all/work", self.git(copy, "branch", "-r", "--contains", self.merge))
        remotes = self.tracking(copy)
        self.assertEqual((remotes["origin"]["state"], remotes["origin"]["contains_merge_commit"]), ("known", True))
        self.assertEqual(remotes["origin"]["containing"], ["refs/remotes/origin-all/work"])
        self.assertIn("refs/remotes/origin/main", remotes["origin"]["refs"])

    def test_a_refspec_can_map_a_remote_under_another_remotes_name(self):
        copy = self.copy_work("refspec-second")
        self.git(copy, "update-ref", "-d", "refs/remotes/second/integration")
        self.git(copy, "update-ref", "refs/remotes/stray/old", self.start)
        self.git(copy, "config", "--replace-all", "remote.second.fetch",
                 "+refs/heads/*:refs/remotes/origin/from-second/*")
        self.git(copy, "config", "--add", "remote.second.fetch", "^refs/heads/nothing")
        self.git(copy, "fetch", "--quiet", "second")
        remotes = self.tracking(copy)
        self.assertEqual((remotes["origin"]["state"], remotes["origin"]["contains_merge_commit"]), ("known", False))
        self.assertEqual(remotes["origin"]["refs"], ["refs/remotes/origin/main"])
        self.assertEqual((remotes["second"]["state"], remotes["second"]["contains_merge_commit"]), ("known", True))
        self.assertEqual(remotes["second"]["containing"], ["refs/remotes/origin/from-second/integration"])
        self.assertEqual(remotes["empty"]["state"], "unknown")

    def test_an_unattributed_tracking_ref_holding_the_merge_makes_every_remote_unknown(self):
        copy = self.copy_work("refspec-stray")
        self.git(copy, "update-ref", "refs/remotes/stray/x", self.merge)
        result = self.run_tool(copy)
        self.assertEqual(result["remote_tracking"]["state"], "known", result["remote_tracking"])
        remotes = {entry["remote"]: entry for entry in result["remote_tracking"]["remotes"]}
        self.assertEqual(sorted(remotes), ["empty", "origin", "second"])
        for name, entry in remotes.items():
            self.assertEqual(entry["state"], "unknown", entry)
            self.assertIn("refs/remotes/stray/x", entry["reason"])
            self.assertIn(name, entry["reason"])

    def test_a_claim_whose_base_is_not_an_ancestor_is_unknown(self):
        payload = self.payload(claims=[{"id": "x", "base": self.remote_tip, "judged": [self.claim1]},
                                       {"id": "y", "base": None, "judged": [self.claim1]}])
        result = self.run_tool(self.work, payload)
        self.assertEqual([claim["state"] for claim in result["claims"]], ["unknown", "unknown"])
        self.assertIn("not an ancestor", result["claims"][0]["reason"])

    def test_a_claim_over_several_judged_commits_unites_its_ranges(self):
        payload = self.payload(claims=[{"id": "both", "base": self.start, "judged": [self.claim1, self.claim2]}])
        claim = self.run_tool(self.work, payload)["claims"][0]
        self.assertEqual(claim["paths"], ["src/b.py", "src/c.py", "src/only_claim.py"])
        self.assertEqual(len(claim["ranges"]), 2)

    def test_more_than_one_merge_base_is_unknown(self):
        repository = self.base / "criss-cross"
        repository.mkdir()
        self.addCleanup(remove_tree, repository)
        self.git(repository, "init", "--quiet", "--initial-branch=main", ".")
        self.write(repository / "f.txt", "root\n")
        self.commit(repository, "f.txt")
        self.git(repository, "branch", "other")
        self.write(repository / "a.txt", "a\n")
        first = self.commit(repository, "a.txt")
        self.git(repository, "switch", "--quiet", "other")
        self.write(repository / "b.txt", "b\n")
        second = self.commit(repository, "b.txt")
        self.git(repository, "merge", "--quiet", "--no-ff", "--no-edit", first)
        other_tip = self.git(repository, "rev-parse", "HEAD")
        self.git(repository, "switch", "--quiet", "main")
        self.git(repository, "merge", "--quiet", "--no-ff", "--no-edit", second)
        main_tip = self.git(repository, "rev-parse", "HEAD")
        self.git(repository, "merge", "--quiet", "--no-ff", "--no-edit", other_tip)
        merge = self.git(repository, "rev-parse", "HEAD")
        payload = {"remote": "origin", "default_branch": "main", "remote_tip": other_tip, "tip_before": main_tip,
                   "merge_commit": merge, "claims": [{"id": "01", "base": None, "judged": []}]}
        result = self.run_tool(repository, payload)
        self.assertTrue(result["merge_parents"]["as_expected"])
        self.assertEqual(result["merge_base"]["state"], "unknown")
        self.assertIn("2 merge bases", result["merge_base"]["reason"])
        self.assertEqual(result["upstream"]["state"], "unknown")
        self.assertEqual(result["merge_result"]["state"], "known")
        self.assertEqual(result["claims"], [{"id": "01", "state": "not-implemented",
                                             "reason": "The input names no judged commit for this Claim"}])


class InvalidInputTest(MergeUpstreamBase):
    def test_invalid_input_is_an_error_and_touches_nothing(self):
        before = snapshot(self.work)
        cases = {
            "not json": "{",
            "not an object": "[]",
            "missing key": json.dumps({key: value for key, value in self.payload().items() if key != "merge_commit"}),
            "unknown key": json.dumps(self.payload(extra=1)),
            "short sha": json.dumps(self.payload(remote_tip=self.remote_tip[:12])),
            "ref syntax": json.dumps(self.payload(remote_tip="HEAD")),
            "claims not a list": json.dumps(self.payload(claims={})),
            "duplicate claim": json.dumps(self.payload(claims=[{"id": "a", "base": None, "judged": []}] * 2)),
            "claim without judged": json.dumps(self.payload(claims=[{"id": "a", "base": None}])),
            "bad judged": json.dumps(self.payload(claims=[{"id": "a", "base": None, "judged": ["main"]}])),
            "bad ref name": json.dumps(self.payload(default_branch="ma..in")),
        }
        for name, raw in cases.items():
            with self.subTest(name):
                result = self.run_tool(self.work, raw=raw, expected=2)
                self.assertEqual(result["status"], "error", result)
                self.assertTrue(result["code"] and result["message"], result)
        self.assertEqual(snapshot(self.work), before)


class ReadOnlyTest(MergeUpstreamBase):
    def traced(self, project: Path, name: str) -> tuple[dict, list[str], list[dict]]:
        trace = self.base / f"{name}.trace"
        events = self.base / f"{name}.events"
        self.addCleanup(lambda: [path.unlink() for path in (trace, events) if path.exists()])
        result = self.run_tool(project, env={"GIT_TRACE": str(trace), "GIT_TRACE2_EVENT": str(events),
                                             "GIT_TRACE2_ENV_VARS": "GIT_TERMINAL_PROMPT,GIT_OPTIONAL_LOCKS"})
        lines = trace.read_text(encoding="utf-8", errors="replace").splitlines() if trace.exists() else []
        records = ([json.loads(line) for line in events.read_text(encoding="utf-8").splitlines() if line.strip()]
                   if events.exists() else [])
        return result, lines, records

    def assert_no_network_or_write(self, lines: list[str], records: list[dict]) -> None:
        self.assertTrue(lines, "Git wrote no trace, so the commands run cannot be checked")
        for line in lines:
            self.assertNotRegex(line, r"trace: (run_command|exec|start_command):", line)
            match = re.search(r"trace: built-in: git (.*)$", line)
            if match:
                words = [word for word in match.group(1).split() if not word.startswith("-")
                         and not word.startswith("'-")]
                command = words[0].strip("'") if words else ""
                self.assertNotIn(command, WRITING_COMMANDS, line)
        processes = {record["sid"] for record in records if record.get("event") == "start"}
        self.assertTrue(processes, "Git wrote no trace2 events")
        for sid in processes:
            settings = {record["param"]: record["value"] for record in records
                        if record.get("sid") == sid and record.get("event") == "def_param"}
            self.assertEqual(settings.get("GIT_TERMINAL_PROMPT"), "0", sid)
            self.assertEqual(settings.get("GIT_OPTIONAL_LOCKS"), "0", sid)

    def test_a_run_changes_nothing_and_reaches_no_remote(self):
        watched = [self.work, self.remote, self.second, self.base / "sub.git"]
        before = [snapshot(path) for path in watched]
        result, lines, records = self.traced(self.work, "work")
        self.assertEqual(result["upstream"]["state"], "known")
        self.assertEqual([snapshot(path) for path in watched], before)
        self.assertFalse((self.work / ".git" / "index.lock").exists())
        self.assert_no_network_or_write(lines, records)

    def test_a_partial_clone_fetches_nothing(self):
        source = self.base / "partial-source.git"
        self.git(self.base, "clone", "--quiet", "--bare", str(self.work), str(source))
        self.addCleanup(remove_tree, source)
        self.git(source, "config", "uploadpack.allowFilter", "true")
        partial = self.base / "partial"
        self.git(self.base, "clone", "--quiet", "--no-checkout", "--filter=blob:none", "--branch", "work",
                 source.as_uri(), str(partial))
        self.addCleanup(remove_tree, partial)
        self.assertTrue(self.git(partial, "config", "--get", "remote.origin.promisor"))
        before = [snapshot(partial), snapshot(source)]
        result, lines, records = self.traced(partial, "partial")
        self.assertEqual([snapshot(partial), snapshot(source)], before)
        self.assertEqual(len(result["claims"]), 4)
        if self.git_version < NO_LAZY_FETCH_FROM:
            for name in ("commits", "merge_parents", "merge_base", "upstream", "merge_result", "resolution",
                         "remote_tracking"):
                part = result[name] if name != "commits" else result[name]["merge_commit"]
                self.assertEqual(part["state"], "unknown", (name, part))
                self.assertIn("promisor", part["reason"])
            self.assertEqual({claim["state"] for claim in result["claims"]}, {"unknown", "not-implemented"})
        else:
            self.assertEqual(result["upstream"]["state"], "known")
            self.assertIn("src/c.py", paths(result["upstream"]))
        self.assert_no_network_or_write(lines, records)


if __name__ == "__main__":
    unittest.main()
