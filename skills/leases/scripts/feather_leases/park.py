"""Parking: detach a returned linked worktree's HEAD so that its merged branch can be deleted and the worktree reused.

Parking runs inside the releasing lease's critical section, after the lease_id was matched and before the lease's own
lock is removed. It applies only to a linked worktree on a branch that is clean (no uncommitted or untracked
changes) and whose branch commit the local default branch contains, or else the branch of the checkout the work
continues in when the caller names one; the tool checks the containment itself with `git merge-base --is-ancestor`.
It detaches at the local default branch's commit, otherwise at the continuing branch's commit. Every failed condition
leaves the worktree as it is and is reported with its reason. Parking never deletes a branch or a worktree, never
resets or cleans files and never overwrites an ignored file (`--no-overwrite-ignore`), and never applies to the main
worktree."""
import os
import subprocess

from feather_handoff.storage import (GIT_COMMAND, _considered, _fully_qualified, git_environment, git_search_path,
                                     resolve_git, run_git)

from .checkouts import Checkout, Repository
from . import leftover

# Switching the worktree's files can take longer than a query: run_git's short timeout would kill a checkout midway.
DETACH_TIMEOUT = 300


def skipped(condition: str, reason: str) -> dict:
    return {"parked": False, "condition": condition, "reason": f"{reason} The worktree was left as it is."}


def _plural(count: int, word: str) -> str:
    return f"{count} {word}" + ("" if count == 1 else "s")


def _contains(repository: Repository, guard: bool, commit: str, tip: str) -> bool:
    """Whether tip contains commit; OSError when Git cannot tell."""
    try:
        result = run_git(repository.main, "merge-base", "--is-ancestor", commit, tip, errors="replace",
                         no_lazy_fetch=guard)
    except subprocess.TimeoutExpired as error:
        raise OSError(f"git merge-base timed out: {error}") from None
    if result.returncode in (0, 1):
        return result.returncode == 0
    raise OSError("git merge-base --is-ancestor failed: " + (result.stderr.strip() or f"exit {result.returncode}"))


def _detach(repository: Repository, checkout: Checkout, guard: bool, commit: str) -> str | None:
    """Detach the worktree's HEAD at commit with its own Git directory and work tree named; why that failed, or None.

    Git is found and started as run_git does it, with a timeout long enough for switching the worktree's files."""
    value = os.environ.get("PATH")
    executable = resolve_git(value)
    environment = git_environment()
    environment["PATH"] = os.pathsep.join(git_search_path(value))
    exec_path = environment.get("GIT_EXEC_PATH")
    if exec_path is not None and (os.pathsep in exec_path or not _considered(exec_path)):
        del environment["GIT_EXEC_PATH"]
    target = checkout.path if _fully_qualified(checkout.path) else os.path.abspath(checkout.path)
    options = (*GIT_COMMAND, "--no-lazy-fetch") if guard else GIT_COMMAND
    git_directory = repository.common / "worktrees" / checkout.key
    command = [executable, *options, "-C", target, f"--git-dir={git_directory}", f"--work-tree={target}",
               "checkout", "--quiet", "--no-overwrite-ignore", "--detach", commit, "--"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace",
                                timeout=DETACH_TIMEOUT, env=environment, cwd=os.path.dirname(executable),
                                stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return (f"git checkout --detach did not finish within {DETACH_TIMEOUT} s and was stopped; the worktree may "
                "be partly switched, so check it before using it")
    except OSError as error:
        return f"git checkout --detach could not be run: {error}"
    if result.returncode:
        return "git checkout --detach failed: " + (result.stderr.strip() or f"exit {result.returncode}")
    return None


def _default_target(repository: Repository, guard: bool, base: dict, branch: str, head: str) -> tuple:
    """(commit, ref) of the local default branch when it contains head, otherwise (None, condition, reason)."""
    if base["local"] is None:
        return None, "local-default-branch", (
            f"The default branch {base['name']} exists only on the remote as {base['remote']}; the local default "
            "branch may need creating or updating.")
    local = leftover._commit(repository, guard, base["local"])
    if local is not None and _contains(repository, guard, head, local):
        return local, base["local"]
    if base["remote"] is not None:
        remote = leftover._commit(repository, guard, base["remote"])
        if remote is not None and _contains(repository, guard, head, remote):
            return None, "local-default-branch", (
                f"The branch {branch} is contained only in the remote default branch {base['remote']}, not in "
                f"{base['local']}; the local default branch may need creating or updating.")
    return None, "not-contained", f"The branch {branch} is not fully contained in {base['local']}."


def _continuing_target(repository: Repository, guard: bool, checkout: Checkout, continuing: Checkout, branch: str,
                       head: str) -> tuple:
    """(commit, ref) of the continuing checkout's branch when it contains head, otherwise (None, condition, reason)."""
    if continuing.key is not None and continuing.key == checkout.key:
        return None, "continuing-checkout", "The named continuing checkout is the checkout being returned."
    if continuing.detached or not continuing.branch:
        return None, "continuing-checkout", f"The named continuing checkout {continuing.path} is not on a branch."
    ref = f"refs/heads/{continuing.branch}"
    tip = leftover._commit(repository, guard, ref)
    if tip is None:
        return None, "continuing-checkout", f"The named continuing checkout's branch {ref} names no commit."
    if _contains(repository, guard, head, tip):
        return tip, ref
    return None, "not-contained", (f"The branch {branch} is not fully contained in {ref}, the branch of the named "
                                   f"continuing checkout {continuing.path}.")


def park(repository: Repository, checkout: Checkout, continuing: Checkout | None) -> dict:
    """Inside the releasing lease's critical section, with checkout as Git registers it now: detach its HEAD when
    every condition holds, otherwise leave it as it is; the result says which, and why."""
    if checkout.main:
        return skipped("main-worktree", "The main worktree is never parked.")
    if checkout.detached or not checkout.branch:
        return skipped("no-branch", "The worktree's HEAD is already detached; there is no branch to park.")
    branch, head = checkout.branch, checkout.head
    guard = leftover.object_guard(repository)
    if isinstance(guard, str):
        return skipped("state-unknown", guard)
    changes = leftover.changes(repository, checkout, guard)
    if changes["state"] != "known":
        return skipped("state-unknown", f"Whether the worktree is clean could not be established: {changes['reason']}")
    if changes["uncommitted_count"] or changes["untracked_count"]:
        parts = [_plural(changes[f"{kind}_count"], f"{kind} path") for kind in ("uncommitted", "untracked")
                 if changes[f"{kind}_count"]]
        return {**skipped("dirty", f"The worktree is not clean: it has {' and '.join(parts)}."), "branch": branch}
    base = leftover.default_branch(repository, guard)
    if base["state"] != "known":
        return {**skipped("default-branch-unknown", f"The default branch is unknown, so parking is skipped: "
                                                    f"{base['reason']}"), "branch": branch}
    try:
        found = _default_target(repository, guard, base, branch, head)
        if found[0] is None and continuing is not None:
            other = _continuing_target(repository, guard, checkout, continuing, branch, head)
            found = other if other[0] is not None else (None, other[1], f"{found[2]} {other[2]}")
    except OSError as error:
        return {**skipped("state-unknown", f"The containment could not be established: {error}"), "branch": branch}
    if found[0] is None:
        return {**skipped(found[1], found[2]), "branch": branch}
    commit, ref = found
    failure = _detach(repository, checkout, guard, commit)
    if failure is not None:
        return {"parked": False, "condition": "detach-failed", "branch": branch, "reason": failure}
    return {"parked": True, "branch": branch, "detached_at": commit, "contained_in": ref,
            "target": "default-branch" if ref == base["local"] else "continuing-checkout"}
