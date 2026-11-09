"""Git worktree locks that protect held leases on linked worktrees.

A lease's own lock has the reason `cc-feather lease <lease_id>`. A Claude Code session lock (`claude session <name>
(pid N)`) is accepted in its place only when the caller attests that exact reason. The tool locks, unlocks and
re-locks only inside the lease's critical section, and never removes or changes a lock whose reason is not one of
its own leases' reasons. A process ID parsed from a reason is shown only; whether that process exists is never probed.
Git cannot lock the main worktree, so its lease has no lock."""
import re
import subprocess

from feather_handoff.storage import run_git

from .checkouts import Checkout, Repository

OWN = re.compile(r"cc-feather lease ([0-9a-f]{32})")
SESSION = re.compile(r"claude session .+ \(pid [0-9]+\)")
PID = re.compile(r"\(pid ([0-9]+)\)\s*$")


def own_reason(lease_id: str) -> str:
    return f"cc-feather lease {lease_id}"


def named_lease(reason: str) -> str | None:
    """The lease_id a cc-feather lock's reason names, or None for any other reason."""
    match = OWN.fullmatch(reason)
    return match.group(1) if match else None


def is_session_lock(reason: str) -> bool:
    return SESSION.fullmatch(reason) is not None


def cannot_lock(checkout: Checkout) -> tuple[str, str] | None:
    """(code, reason) when Git cannot or must not lock this linked worktree now, or None.

    Git can lock a worktree whose directory is gone, and the lock then hides that it is prunable, so such a worktree is
    never locked."""
    if not checkout.exists:
        return "directory-missing", f"The worktree's directory {checkout.path} is missing"
    if checkout.prunable is not None:
        return "prunable", f"Git marks the worktree {checkout.path} prunable: {checkout.prunable}"
    return None


def _git(repository: Repository, *arguments: str) -> str | None:
    """Run one worktree lock command; why it failed, or None."""
    try:
        result = run_git(repository.main, "worktree", *arguments, errors="replace")
    except (OSError, subprocess.TimeoutExpired) as error:
        return f"git worktree {arguments[0]} could not be run: {error}"
    if result.returncode:
        return f"git worktree {arguments[0]} failed: " + (result.stderr.strip() or f"exit {result.returncode}")
    return None


def lock(repository: Repository, checkout: Checkout, lease_id: str) -> str | None:
    """Lock the worktree with the lease's own reason; Git refuses when it is already locked."""
    return _git(repository, "lock", "--reason", own_reason(lease_id), checkout.path)


def unlock(repository: Repository, checkout: Checkout) -> str | None:
    """Unlock the worktree; only called when its current lock is the releasing lease's own."""
    return _git(repository, "unlock", checkout.path)


def describe(checkout: Checkout, lease: dict | None, lease_known: bool) -> dict:
    """The checkout's lock as found: its reason as written, its parsed process ID and whose it is.

    holder is `lease` for the lease's own lock, `accepted-session` for the Claude Code session lock the lease
    accepted, `cc-feather` for a cc-feather lock that does not name the lease (a mismatch when the lease is known),
    and `other` for every other lock."""
    if checkout.main:
        return {"state": "not-lockable", "reason": "Git cannot lock the main worktree; its lease alone records use"}
    reason = checkout.locked
    if reason is None:
        return {"state": "unlocked"}
    match = PID.search(reason)
    view = {"state": "locked", "reason": reason, "pid": int(match.group(1)) if match else None}
    named = named_lease(reason)
    if named is not None:
        if lease is not None and lease.get("lease_id") == named:
            return {**view, "holder": "lease"}
        view["holder"] = "cc-feather"
        if lease_known:
            view["mismatch"] = (f"The cc-feather lock names lease {named}, but "
                                + ("the checkout has no lease" if lease is None
                                   else f"the checkout's lease is {lease.get('lease_id')}"))
        return view
    if lease is not None and lease.get("accepted_lock") == reason:
        return {**view, "holder": "accepted-session"}
    return {**view, "holder": "other"}
