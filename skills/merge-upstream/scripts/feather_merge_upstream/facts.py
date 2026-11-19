"""The facts of one Upstream merge, each known or unknown with the reason.

Every Git command goes through the handoff tool's run_git, so it starts the Git found by the handoff tool's PATH
discovery with --no-pager, --no-optional-locks, an empty core.fsmonitor, GIT_OPTIONAL_LOCKS=0 and a timeout, and with
--no-lazy-fetch whenever lazy_fetch_guard found a promisor remote that the installed Git can guard; when it cannot,
no command that reads objects runs and every fact is unknown. The commands used only read: cat-file, merge-base,
diff-tree, remote, config --get-all and for-each-ref. None fetches, merges, pushes or writes a ref, the index, an object
or the working tree."""
from pathlib import Path
import subprocess

from feather_handoff.storage import HandoffError, lazy_fetch_guard, run_git

from . import classify

# Global options placed after -C: a replacement ref never changes what a named commit is.
SCOPE = ("--no-replace-objects",)
# Every list is a tree-to-tree diff of two named commits: paths from the top level whatever diff.relative or the
# directory says, no rename or copy detection (both sides of a rename are listed), submodule entries whatever
# diff.ignoreSubmodules or a submodule's ignore setting says, full object names, no external diff or text conversion.
DIFF = ("diff-tree", "-r", "-z", "--raw", "--no-abbrev", "--no-renames", "--no-relative", "--ignore-submodules=none",
        "--no-ext-diff", "--no-textconv", "--no-commit-id")
KIND = {"100644": "file", "100755": "executable", "120000": "symlink", "160000": "submodule", "040000": "tree"}
STATUS = {"A": "added", "D": "deleted", "M": "modified", "T": "type-changed"}
COMMITS = ("remote_tip", "tip_before", "merge_commit")
LISTS = ("upstream", "merge_result")


class Unknown(Exception):
    """A fact that could not be established; reported as unknown with the reason, never guessed or left empty."""


def unknown(reason: str) -> dict:
    return {"state": "unknown", "reason": reason}


def claim_view(item: dict) -> dict:
    view = {"id": item["id"]}
    if "kind" in item:
        view["kind"] = item["kind"]
    return view


def not_implemented(item: dict) -> dict | None:
    if item["judged"]:
        return None
    return {**claim_view(item), "state": "not-implemented",
            "reason": "The input names no judged commit for this Claim"}


def all_unknown(request: dict, reason: str) -> dict:
    """The full result shape with every fact unknown for one reason; every Claim of the input is still listed."""
    part = unknown(reason)
    claims = [not_implemented(item) or {**claim_view(item), **part} for item in request["claims"]]
    return {"commits": {name: dict(part) for name in COMMITS}, "merge_parents": dict(part),
            "merge_base": dict(part), "upstream": dict(part), "merge_result": dict(part), "resolution": dict(part),
            "claims": claims,
            "classification": {"advice": True, "rule": classify.RULE, "upstream": dict(part),
                               "merge_result": dict(part)},
            "remote_tracking": dict(part), "default_branch_ref": dict(part)}


def destinations(refspecs: list[str]) -> list[str]:
    """The destinations of a remote's fetch refspecs, the right-hand sides that name its remote-tracking refs.

    A leading `+` is dropped. A negative refspec (`^...`) only excludes sources and a refspec without a destination
    stores nothing, so neither names a remote-tracking ref."""
    found = []
    for refspec in refspecs:
        refspec = refspec.strip()
        if refspec.startswith("+"):
            refspec = refspec[1:]
        if refspec.startswith("^"):
            continue
        _, separator, destination = refspec.partition(":")
        if separator and destination:
            found.append(destination)
    return found


def names_ref(destination: str, ref: str) -> bool:
    """Whether a fetch refspec destination names the ref: an exact name, or a pattern with a single `*` matched as Git
    matches it (the ref starts with the part before the `*` and ends with the part after it). A destination with more
    than one `*` is not a valid refspec and names nothing."""
    stars = destination.count("*")
    if stars == 0:
        return ref == destination
    if stars > 1:
        return False
    prefix, suffix = destination.split("*")
    return len(ref) >= len(prefix) + len(suffix) and ref.startswith(prefix) and ref.endswith(suffix)


class Git:
    def __init__(self, root: Path, guard: bool):
        self.root = root
        self.guard = guard

    def run(self, *arguments: str) -> subprocess.CompletedProcess:
        try:
            return run_git(self.root, *SCOPE, *arguments, errors="surrogateescape", no_lazy_fetch=self.guard)
        except subprocess.TimeoutExpired:
            raise Unknown(f"git {arguments[0]} did not finish within the tool's timeout") from None
        except OSError as error:
            raise Unknown(f"Git could not be run: {error}") from None

    def output(self, *arguments: str, what: str) -> str:
        result = self.run(*arguments)
        if result.returncode:
            raise Unknown(f"{what}: {result.stderr.strip() or f'git {arguments[0]} exited with {result.returncode}'}")
        return result.stdout


class Facts:
    def __init__(self, git: Git, request: dict):
        self.git = git
        self.request = request
        self.checked: dict[str, str | None] = {}

    # Commits -------------------------------------------------------------------------------------------------------

    def require_commit(self, sha: str, label: str) -> None:
        if sha not in self.checked:
            result = self.git.run("cat-file", "-t", sha)
            kind = result.stdout.strip()
            if result.returncode:
                self.checked[sha] = f"{sha} is not an object in this repository"
            elif kind != "commit":
                self.checked[sha] = f"{sha} is a {kind}, not a commit"
            else:
                self.checked[sha] = None
        if self.checked[sha] is not None:
            raise Unknown(f"The {label} is unknown: {self.checked[sha]}")

    def parents(self, sha: str) -> list[str]:
        text = self.git.output("cat-file", "commit", sha, what=f"The commit {sha} could not be read")
        found = []
        for line in text.split("\n"):
            if not line:
                break
            if line.startswith("parent "):
                found.append(line[len("parent "):].strip())
        return found

    def merge_bases(self, first: str, second: str) -> list[str]:
        result = self.git.run("merge-base", "--all", first, second)
        if result.returncode == 1 and not result.stdout.strip():
            return []
        if result.returncode:
            raise Unknown(f"The merge base could not be computed: {result.stderr.strip() or result.returncode}")
        return result.stdout.split()

    def is_ancestor(self, first: str, second: str) -> bool:
        result = self.git.run("merge-base", "--is-ancestor", first, second)
        if result.returncode in (0, 1):
            return result.returncode == 0
        raise Unknown(f"Whether {first} is an ancestor of {second} could not be established: "
                      f"{result.stderr.strip() or result.returncode}")

    def diff(self, first: str, second: str) -> list[dict]:
        text = self.git.output(*DIFF, first, second, what=f"The range {first}..{second} could not be read")
        fields = text.split("\0")
        if fields and fields[-1] == "":
            fields.pop()
        if len(fields) % 2:
            raise Unknown(f"The range {first}..{second} gave output the tool cannot read")
        changes = []
        for index in range(0, len(fields), 2):
            meta, path = fields[index], fields[index + 1]
            parts = meta.lstrip(":").split(" ")
            if not meta.startswith(":") or len(parts) != 5:
                raise Unknown(f"The range {first}..{second} gave output the tool cannot read")
            old_mode, new_mode, old_object, new_object, status = parts
            old_absent, new_absent = set(old_mode) == {"0"}, set(new_mode) == {"0"}
            changes.append({
                "path": path, "status": STATUS.get(status[:1], status),
                "old_mode": None if old_absent else old_mode, "new_mode": None if new_absent else new_mode,
                "old_kind": None if old_absent else KIND.get(old_mode, old_mode),
                "new_kind": None if new_absent else KIND.get(new_mode, new_mode),
                "old_object": None if old_absent else old_object, "new_object": None if new_absent else new_object,
                "mode_changed": not old_absent and not new_absent and old_mode != new_mode})
        return sorted(changes, key=lambda change: change["path"])

    # Parts ---------------------------------------------------------------------------------------------------------

    @staticmethod
    def attempt(action) -> dict:
        try:
            return action()
        except Unknown as error:
            return unknown(str(error))

    def commit_part(self, name: str) -> dict:
        def action():
            self.require_commit(self.request[name], name.replace("_", " "))
            return {"state": "known", "commit": self.request[name]}
        return self.attempt(action)

    def merge_parents_part(self) -> dict:
        request = self.request

        def action():
            self.require_commit(request["merge_commit"], "merge commit")
            parents = self.parents(request["merge_commit"])
            expected = [request["tip_before"], request["remote_tip"]]
            return {"state": "known", "parents": parents, "expected": expected, "as_expected": parents == expected}
        return self.attempt(action)

    def merge_problem(self, parents: dict) -> str | None:
        """Why the lists that depend on the merge commit's parents cannot be taken, or None."""
        if parents["state"] != "known":
            return f"The merge commit's parents are unknown: {parents['reason']}"
        if not parents["as_expected"]:
            return ("The merge commit's parents are " + (", ".join(parents["parents"]) or "none")
                    + "; the list needs exactly two, the tip before the merge first and the remote tip second")
        return None

    def merge_base_part(self) -> dict:
        request = self.request

        def action():
            self.require_commit(request["tip_before"], "tip before the merge")
            self.require_commit(request["remote_tip"], "remote tip")
            bases = self.merge_bases(request["tip_before"], request["remote_tip"])
            if len(bases) != 1:
                raise Unknown(f"Git computes {len(bases)} merge bases of the tip before the merge and the remote tip"
                              + (f" ({', '.join(bases)})" if bases else "") + "; the lists need exactly one")
            return {"state": "known", "commit": bases[0]}
        return self.attempt(action)

    def build(self) -> dict:
        request = self.request
        commits = {name: self.commit_part(name) for name in COMMITS}
        parents = self.merge_parents_part()
        base = self.merge_base_part()
        problem = self.merge_problem(parents)

        def upstream():
            if problem:
                raise Unknown(problem)
            if base["state"] != "known":
                raise Unknown(f"The merge base is unknown: {base['reason']}")
            return {"state": "known", "from": base["commit"], "to": request["remote_tip"],
                    "changes": self.diff(base["commit"], request["remote_tip"])}

        def merge_result():
            if problem:
                raise Unknown(problem)
            return {"state": "known", "from": request["tip_before"], "to": request["merge_commit"],
                    "changes": self.diff(request["tip_before"], request["merge_commit"])}

        lists = {"upstream": self.attempt(upstream), "merge_result": self.attempt(merge_result)}

        def resolution():
            for name in LISTS:
                if lists[name]["state"] != "known":
                    raise Unknown(f"The {name} list is unknown: {lists[name]['reason']}")
            ours = {change["path"]: change for change in self.diff(base["commit"], request["tip_before"])}
            theirs = {change["path"]: change for change in lists["upstream"]["changes"]}
            from_first = {change["path"] for change in lists["merge_result"]["changes"]}
            from_second = {change["path"]
                           for change in self.diff(request["remote_tip"], request["merge_commit"])}
            return {"state": "known", "paths": [
                {"path": path, "tip_before_status": ours[path]["status"], "remote_tip_status": theirs[path]["status"],
                 "merge_differs_from_tip_before": path in from_first,
                 "merge_differs_from_remote_tip": path in from_second}
                for path in sorted(ours.keys() & theirs.keys())]}

        result = {"commits": commits, "merge_parents": parents, "merge_base": base, **lists,
                  "resolution": self.attempt(resolution)}
        result["claims"] = [self.claim(item, lists) for item in request["claims"]]
        result["classification"] = {"advice": True, "rule": classify.RULE}
        for name in LISTS:
            if lists[name]["state"] == "known":
                classed = [{"path": change["path"], "classes": classify.classes(change["path"])}
                           for change in lists[name]["changes"]]
                result["classification"][name] = {"state": "known",
                                                  "paths": [entry for entry in classed if entry["classes"]]}
            else:
                result["classification"][name] = unknown(f"The {name} list is unknown: {lists[name]['reason']}")
        result["remote_tracking"], result["default_branch_ref"] = self.remote_parts(commits)
        return result

    def claim(self, item: dict, lists: dict) -> dict:
        empty = not_implemented(item)
        if empty:
            return empty
        view = claim_view(item)
        if item["base"] is None:
            return {**view, **unknown("The input names judged commits but no base revision for this Claim")}
        base = item["base"]
        try:
            self.require_commit(base, "Claim's base revision")
            ranges = []
            for judged in dict.fromkeys(item["judged"]):
                self.require_commit(judged, "Claim's judged commit")
                if not self.is_ancestor(base, judged):
                    raise Unknown(f"The base revision {base} is not an ancestor of the judged commit {judged}, so "
                                  "the Claim's range cannot be read")
                ranges.append({"from": base, "to": judged, "changes": self.diff(base, judged)})
        except Unknown as error:
            return {**view, **unknown(str(error))}
        paths = sorted({change["path"] for entry in ranges for change in entry["changes"]})
        overlap = {}
        for name in LISTS:
            if lists[name]["state"] == "known":
                listed = {change["path"] for change in lists[name]["changes"]}
                overlap[name] = {"state": "known", "paths": [path for path in paths if path in listed]}
            else:
                overlap[name] = unknown(f"The {name} list is unknown: {lists[name]['reason']}")
        return {**view, "state": "known", "ranges": ranges, "paths": paths, "overlap": overlap}

    def remote_parts(self, commits: dict) -> tuple[dict, dict]:
        request = self.request
        try:
            names = [name for name in self.git.output("remote", what="The remotes could not be listed").split("\n")
                     if name]
            listing = self.git.output("for-each-ref", "--format=%(refname)%00%(objectname)", "refs/remotes/",
                                      what="The remote-tracking refs could not be listed")
        except Unknown as error:
            return unknown(str(error)), unknown(str(error))
        refs = {}
        for line in listing.split("\n"):
            name, separator, objectname = line.partition("\0")
            if separator:
                refs[name] = objectname
        wanted = f"refs/remotes/{request['remote']}/{request['default_branch']}"
        if wanted in refs:
            default = {"state": "known", "ref": wanted, "commit": refs[wanted],
                       "is_remote_tip": refs[wanted] == request["remote_tip"]}
        else:
            default = {"ref": wanted, **unknown(f"There is no remote-tracking ref {wanted}")}

        def tracking():
            if commits["merge_commit"]["state"] != "known":
                raise Unknown(f"The merge commit is unknown: {commits['merge_commit']['reason']}")
            containing = set(self.git.output(
                "for-each-ref", "--format=%(refname)", f"--contains={request['merge_commit']}", "refs/remotes/",
                what="The remote-tracking refs that contain the merge commit could not be listed").split("\n"))
            # A ref is a remote's remote-tracking ref when one of the remote's fetch refspec destinations names it,
            # whatever its name says; a ref several remotes' destinations name counts for each of them.
            mapped: dict[str, list[str]] = {}
            unreadable: dict[str, str] = {}
            for name in names:
                result = self.git.run("config", "--null", "--get-all", f"remote.{name}.fetch")
                if result.returncode == 1 and not result.stdout:
                    mapped[name] = []
                elif result.returncode:
                    unreadable[name] = (f"The fetch refspecs of the remote {name} could not be read: "
                                        f"{result.stderr.strip() or f'git config exited with {result.returncode}'}")
                else:
                    mapped[name] = destinations([value for value in result.stdout.split("\0") if value])
            owned: dict[str, list[str]] = {name: [] for name in mapped}
            unclaimed = []
            for ref in sorted(refs):
                owners = [name for name, targets in mapped.items() if any(names_ref(target, ref) for target in targets)]
                for name in owners:
                    owned[name].append(ref)
                if not owners and ref in containing:
                    unclaimed.append(ref)
            remotes = []
            for name in names:
                if name in unreadable:
                    remotes.append({"remote": name, **unknown(unreadable[name])})
                    continue
                if unclaimed:
                    remotes.append({"remote": name, **unknown(
                        "The merge commit is on " + ", ".join(unclaimed) + ", which no readable fetch refspec of any "
                        f"remote names, so it may be a remote-tracking ref of any remote, {name} included")})
                    continue
                if not owned[name]:
                    remotes.append({"remote": name, **unknown(
                        f"The remote {name} has no remote-tracking refs, so whether the merge commit reached it "
                        "cannot be established")})
                    continue
                holding = [ref for ref in owned[name] if ref in containing]
                remotes.append({"remote": name, "state": "known", "refs": owned[name], "containing": holding,
                                "contains_merge_commit": bool(holding)})
            if request["remote"] not in names:
                remotes.append({"remote": request["remote"],
                                **unknown(f"{request['remote']} is not a configured remote")})
            return {"state": "known", "remotes": remotes}
        return self.attempt(tracking), default


def report(root: Path, request: dict) -> dict:
    try:
        guard = lazy_fetch_guard(root)
    except HandoffError as error:
        return all_unknown(request, f"{error} ({error.code})")
    except (OSError, subprocess.TimeoutExpired) as error:
        return all_unknown(request, f"Git could not be run or did not respond: {error}")
    return Facts(Git(root, guard), request).build()
