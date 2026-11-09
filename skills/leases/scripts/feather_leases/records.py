"""Lease records and the short critical section that changes them.

A lease is `<key>.json` in the lease location; its critical section is `<key>.lock` beside it, created exclusively
for the few file and Git worktree lock operations of one acquire, release or re-locking, as the handoff history lock
is. A critical section already held is reported at once with its holder and age; it is never waited on and never
broken. The location ignores itself with its own `.gitignore` holding `*`, written before any lease or lock."""
from dataclasses import replace
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import secrets
import socket
import stat
import time

from feather_handoff.storage import (HandoffError, Snapshot, _check_lock_path, _listed, _mark_denied, check_path,
                                     create_file, read_file, require_current)

from .checkouts import Checkout, LeaseError, Repository, Unknown
from . import locks

SCHEMA_VERSION = 1
IGNORE = b"*\n"
TEXT_FIELDS = ("lease_id", "session", "host", "runtime", "started", "purpose", "last_activity")
# Windows refuses to delete a file another process holds open (ERROR_SHARING_VIOLATION, ERROR_LOCK_VIOLATION), as a
# concurrent listing, acquire or busy report does for the moment it reads a lease or a lock.
HELD_OPEN = frozenset({32, 33})
REMOVAL_PATIENCE = 1.0


def now() -> datetime:
    return datetime.now().astimezone()


def stamp() -> str:
    return now().isoformat(timespec="seconds")


def age(moment: str) -> int | None:
    try:
        return int((now() - datetime.fromisoformat(moment)).total_seconds())
    except (TypeError, ValueError):
        return None


def lease_path(repository: Repository, key: str) -> Path:
    path = repository.directory / f"{key}.json"
    check_path(path)
    return path


def lock_path(repository: Repository, key: str) -> Path:
    return repository.directory / f"{key}.lock"


def remove_own(path: Path) -> None:
    """Delete a file this operation owns, the lease inside its critical section or the section's own lock.

    A reader holding it open only delays the deletion: it is retried for a bounded moment, so a concurrent reader
    never leaves the file behind. This waits for no other operation's critical section and breaks none."""
    deadline = time.monotonic() + REMOVAL_PATIENCE
    while True:
        try:
            path.unlink()
            return
        except PermissionError as error:
            if getattr(error, "winerror", None) not in HELD_OPEN or time.monotonic() >= deadline:
                raise
        time.sleep(0.02)


def _valid(value: object, key: str) -> str | None:
    """Why value is not a lease of this tool's schema for key, or None."""
    if not isinstance(value, dict):
        return "the lease is not a JSON object"
    if value.get("schema_version") != SCHEMA_VERSION:
        return f"the lease has schema version {value.get('schema_version')!r}, not {SCHEMA_VERSION}"
    checkout = value.get("checkout")
    if not isinstance(checkout, dict) or checkout.get("key") != key or not isinstance(checkout.get("path"), str):
        return "the lease does not name this checkout's key and path"
    for field in TEXT_FIELDS:
        if not isinstance(value.get(field), str):
            return f"the lease has no text field {field}"
    for field in ("started", "last_activity"):
        try:
            if datetime.fromisoformat(value[field]).utcoffset() is None:
                return f"the lease's {field} has no time zone"
        except ValueError:
            return f"the lease's {field} is not a time"
    if "accepted_lock" in value and not isinstance(value["accepted_lock"], str):
        return "the lease's accepted_lock is not text"
    return None


def read_lease(repository: Repository, checkout: Checkout) -> tuple[dict, Snapshot | None]:
    """(the lease state as reported, the lease file's snapshot when held).

    The state is held with the lease and its ages, absent ("no registered use"), or unknown with the reason when the
    checkout's key, the location or the lease cannot be read."""
    if checkout.key is None:
        return {"state": "unknown", "reason": checkout.key_reason}, None
    if repository.location_problem is not None:
        return {"state": "unknown", "reason": repository.location_problem}, None
    try:
        snapshot = read_file(lease_path(repository, checkout.key))
    except FileNotFoundError:
        return {"state": "absent", "description": "no registered use"}, None
    except (OSError, HandoffError) as error:
        return {"state": "unknown", "reason": f"The lease could not be read: {error}"}, None
    try:
        value = json.loads(snapshot.data.decode("utf-8"))
    except (UnicodeError, ValueError, RecursionError) as error:
        return {"state": "unknown", "reason": f"The lease is not valid UTF-8 JSON: {type(error).__name__}"}, None
    problem = _valid(value, checkout.key)
    if problem is not None:
        return {"state": "unknown", "reason": f"The lease could not be read: {problem}"}, None
    return {"state": "held", "lease": value, "version": snapshot.version, "age_seconds": age(value["started"]),
            "activity_age_seconds": age(value["last_activity"])}, snapshot


def new_lease(checkout: Checkout, session: str, purpose: str, runtime: str, accepted_lock: str | None) -> dict:
    """A new lease; accepted_lock is the Claude Code session lock it accepted in place of its own lock."""
    moment = stamp()
    accepted = {} if accepted_lock is None else {"accepted_lock": accepted_lock}
    return {"schema_version": SCHEMA_VERSION, "checkout": {"key": checkout.key, "path": checkout.path},
            "lease_id": secrets.token_hex(16), "session": session, "host": socket.gethostname(),
            "runtime": runtime, "started": moment, "purpose": purpose, "last_activity": moment,
            # The tool is a short-lived subprocess: this PID never shows that the holder is still running.
            "diagnostic_pid": os.getpid(), **accepted}


def encode(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def ensure_location(repository: Repository) -> None:
    """Create the lease location and its own `.gitignore` before anything else is written there."""
    repository.require_location()
    try:
        repository.directory.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        _mark_denied(error)
        raise
    ignore = repository.directory / ".gitignore"
    try:
        create_file(ignore, IGNORE)
    except HandoffError as error:
        if error.code != "exists":
            raise


class Busy(Exception):
    def __init__(self, section: dict):
        super().__init__(section.get("message"))
        self.section = section


def _describe(path: Path) -> dict:
    """The critical section's lock as observed now: its creation time, holder and age."""
    base = {"path": str(path), "readable": False, "created": None, "holder": None, "age_seconds": None}
    try:
        if _check_lock_path(path):
            return {**base, "message": "The critical section is held by a lock file pending deletion"}
        snapshot = read_file(path)
        info = path.lstat()
    except (OSError, HandoffError) as error:
        return {**base, "message": f"The critical section is held by a lock that could not be read: {error}"}
    created = holder = None
    try:
        value = json.loads(snapshot.data.decode("utf-8"))
        created = datetime.fromisoformat(value["created"])
        holder = {"host": value["host"], "pid": value["pid"], "operation": value["operation"]}
        if created.utcoffset() is None:
            created = None
    except (UnicodeError, ValueError, TypeError, KeyError):
        created = holder = None
    if created is None:
        created = datetime.fromtimestamp(info.st_mtime, timezone.utc).astimezone()
    seconds = int((now() - created).total_seconds())
    who = (f"{holder['operation']} by process {holder['pid']} on {holder['host']}" if holder
           else "an unrecognized holder")
    return {**base, "readable": True, "created": created.isoformat(), "holder": holder, "age_seconds": seconds,
            "message": (f"The lease's critical section is held by {who} since {created.isoformat()} ({seconds} s "
                        f"ago): {path}. It is never waited on or broken; nothing was changed. Retry once the holder "
                        "finishes, or show the holder and age to the user when it was left by a crash.")}


class CriticalSection:
    """One exclusive lock file for the duration of a lease change."""

    def __init__(self, path: Path, operation: str, key: str):
        self.path = path
        self.data = (json.dumps({"created": now().isoformat(timespec="microseconds"), "host": socket.gethostname(),
                                 "pid": os.getpid(), "operation": operation, "checkout": key},
                                ensure_ascii=False) + "\n").encode("utf-8")
        self.identity = (0, 0)

    def __enter__(self):
        if _check_lock_path(self.path):
            raise Busy(_describe(self.path))
        try:
            descriptor = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o644)
        except FileExistsError:
            raise Busy(_describe(self.path)) from None
        except OSError as error:
            # Windows reports EACCES for a lock file pending deletion as for a denied directory.
            if os.path.lexists(self.path) or _listed(self.path):
                raise Busy(_describe(self.path)) from None
            _mark_denied(error)
            raise
        try:
            with os.fdopen(descriptor, "wb") as handle:
                opened = os.fstat(handle.fileno())
                self.identity = (opened.st_dev, opened.st_ino)
                handle.write(self.data)
                handle.flush()
                os.fsync(handle.fileno())
            check_path(self.path)
        except BaseException:
            self._remove()
            raise
        return self

    def _remove(self) -> str | None:
        try:
            check_path(self.path)
            info = self.path.lstat()
            if not stat.S_ISREG(info.st_mode) or (self.identity[1] and (info.st_dev, info.st_ino) != self.identity):
                return f"The critical section's lock was replaced and was left in place: {self.path}"
            remove_own(self.path)
        except (OSError, HandoffError) as error:
            return f"The critical section's lock could not be removed: {error}"
        return None

    def __exit__(self, kind, error, trace):
        # An interruption that is not an Exception leaves the lock in place, as a crash does; it is then reported.
        if kind is None or issubclass(kind, Exception):
            self.left = self._remove()
        return False


def _section(repository: Repository, checkout: Checkout, operation: str) -> CriticalSection:
    return CriticalSection(lock_path(repository, checkout.key), operation, checkout.key)


def _with_left(result: dict, section: CriticalSection) -> dict:
    left = getattr(section, "left", None)
    return {**result, "critical_section_left": left} if left else result


def _relock(repository: Repository, checkout: Checkout, lease_id: str) -> tuple[dict, Checkout]:
    """Inside the lease's critical section, lock a lockless held lease's worktree again with its own reason.

    Only when the lease still carries lease_id, the worktree still has no lock at all and Git can lock it. Returns
    (what happened, the checkout as found)."""
    current = repository.current(checkout)
    state, _ = read_lease(repository, current)
    if state["state"] != "held" or state["lease"]["lease_id"] != lease_id or current.locked is not None:
        return {"relocked": False, "reason": "The lease or the lock changed before it could be locked again."}, current
    blocked = locks.cannot_lock(current)
    if blocked is not None:
        return {"relocked": False, "reason": blocked[1]}, current
    failure = locks.lock(repository, current, lease_id)
    if failure is not None:
        return {"relocked": False, "reason": failure}, repository.current(current)
    return {"relocked": True}, repository.current(current)


def relock(repository: Repository, checkout: Checkout, lease_id: str) -> tuple[dict, Checkout]:
    """_relock inside its own critical section; one already held is reported at once, never waited on."""
    section = _section(repository, checkout, "relock")
    try:
        with section:
            outcome, current = _relock(repository, checkout, lease_id)
    except Busy as busy:
        return {"relocked": False, "status": "busy", "critical_section": busy.section}, checkout
    return _with_left(outcome, section), current


def _lock_view(checkout: Checkout, state: dict, outcome: dict | None = None) -> dict:
    """The checkout's lock as described for its lease state, with what a re-locking attempt did."""
    lease = state.get("lease")
    view = locks.describe(checkout, lease, state["state"] != "unknown" or lease is not None)
    if outcome is not None:
        if outcome.get("relocked"):
            view["relocked"] = True
        else:
            view["relock"] = {key: value for key, value in outcome.items() if key != "relocked"}
    return view


def _locked(checkout: Checkout, outcome: str) -> dict:
    """A lock other than the lease's own blocks acquisition; the checkout is known to have no lease here."""
    view = locks.describe(checkout, None, True)
    return {"status": "locked", "acquired": False, "lock": view,
            "message": f"The worktree carries a Git worktree lock that is not this lease's, with the reason "
                       f"{view['reason']!r}. It is handled like a held lease. {outcome}"}


def _refused(blocked: tuple[str, str]) -> dict:
    return {"status": "refused", "acquired": False, "code": blocked[0],
            "reason": f"{blocked[1]}; it is not acquired. Nothing was changed."}


def _withdraw(repository: Repository, checkout: Checkout) -> str | None:
    """Remove the lease this acquire just created; why that failed, or None."""
    try:
        remove_own(lease_path(repository, checkout.key))
    except (OSError, HandoffError) as error:
        return f"The new lease could not be withdrawn and is left in place: {error}"
    return None


def _take(repository: Repository, checkout: Checkout, session: str, purpose: str, runtime: str,
          attested: str | None) -> dict:
    """Inside the critical section of a checkout without a lease: create the lease and protect it with a lock."""
    accepted = None
    if not checkout.main:
        blocked = locks.cannot_lock(checkout)
        if blocked is not None:
            return _refused(blocked)
        if checkout.locked is not None:
            if attested is None or checkout.locked != attested or not locks.is_session_lock(checkout.locked):
                return _locked(checkout, "Nothing was acquired.")
            accepted = checkout.locked
    lease = new_lease(checkout, session, purpose, runtime, accepted)
    try:
        saved = create_file(lease_path(repository, checkout.key), encode(lease))
    except HandoffError as error:
        if error.code != "exists":
            raise
        return {"status": "unknown", "acquired": False,
                "reason": "A lease appeared while it was being acquired; nothing was acquired."}
    result = {"status": "ok", "acquired": True, "lease": lease, "version": saved.version}
    held = {"state": "held", "lease": lease}
    if checkout.main or accepted is not None:
        return {**result, "lock": _lock_view(checkout, held)}
    failure = locks.lock(repository, checkout, lease["lease_id"])
    if failure is None:
        try:
            current = repository.current(checkout)
        except Unknown:
            current = replace(checkout, locked=locks.own_reason(lease["lease_id"]))
        return {**result, "lock": _lock_view(current, held)}
    left = _withdraw(repository, checkout)
    try:
        current = repository.current(checkout)
    except Unknown:
        current = checkout
    if current.locked is not None and left is None:
        # Another holder locked the worktree first: handled like any other lock.
        return _locked(current, "The new lease was withdrawn; nothing was acquired.")
    return {"status": "error", "code": "lock-failed", "acquired": False, "withdrawn": left is None,
            "message": f"The worktree could not be locked: {failure}. "
                       + ("The new lease was withdrawn; nothing was acquired." if left is None else left)}


def acquire(repository: Repository, checkout: Checkout, session: str, purpose: str, runtime: str,
            attested: str | None = None) -> dict:
    """An exclusive create inside the lease's critical section; a held or unreadable lease acquires nothing.

    On a linked worktree the new lease is then locked with its own reason, or accepts the Claude Code session lock
    whose exact reason the caller attested; any other lock blocks it. A held lease found with no lock is locked
    again. A worktree whose directory is missing or that Git marks prunable is not acquired."""
    repository.require_location()
    state, _ = read_lease(repository, checkout)
    if state["state"] == "unknown":
        return {"status": "unknown", "acquired": False, "reason": state["reason"]}
    blocked = None if checkout.main else locks.cannot_lock(checkout)
    if blocked is not None and state["state"] == "absent":
        return _refused(blocked)
    ensure_location(repository)
    section = _section(repository, checkout, "acquire")
    try:
        with section:
            current = checkout if checkout.main else repository.current(checkout)
            state, _ = read_lease(repository, current)
            if state["state"] == "absent":
                result = _take(repository, current, session, purpose, runtime, attested)
            elif state["state"] == "unknown":
                result = {"status": "unknown", "acquired": False, "reason": state["reason"]}
            else:
                outcome = None
                if not current.main and current.locked is None:
                    outcome, current = _relock(repository, current, state["lease"]["lease_id"])
                held = {key: state[key] for key in ("lease", "version", "age_seconds", "activity_age_seconds")}
                result = {"status": "held", "acquired": False, **held, "lock": _lock_view(current, state, outcome),
                          "message": "The checkout's lease is held; nothing was acquired."}
    except Busy as busy:
        return {"status": "busy", "acquired": False, "critical_section": busy.section}
    return _with_left(result, section)


def _unlock_own(repository: Repository, checkout: Checkout, state: dict, lease_id: str) -> dict | None:
    """Inside the release's critical section: remove the worktree's lock only when its reason names this lease."""
    if checkout.main:
        return None
    current = repository.current(checkout)
    if current.locked is None:
        return {"removed": False, "kept": None}
    if locks.named_lease(current.locked) != lease_id:
        return {"removed": False, "kept": _lock_view(current, state),
                "message": "The worktree's lock does not name this lease and stays."}
    failure = locks.unlock(repository, current)
    if failure is not None:
        raise LeaseError("unlock-failed", f"The lease's own lock could not be removed: {failure}. The lease and its "
                         "lock stay; nothing was released.")
    return {"removed": True, "reason": current.locked}


def release(repository: Repository, checkout: Checkout, lease_id: str) -> dict:
    """Inside its critical section, and only when the lease carries the caller's lease_id: remove the worktree's
    lock when its reason names this lease, then remove the lease. Every other lock stays."""
    repository.require_location()
    state, _ = read_lease(repository, checkout)
    if state["state"] == "unknown":
        return {"status": "unknown", "released": False, "reason": state["reason"]}
    if state["state"] == "absent":
        return {"status": "changed-hands", "released": False, "lease": None,
                "message": "The checkout has no lease; it changed hands or was returned. Nothing was changed."}
    section = _section(repository, checkout, "release")
    try:
        with section:
            state, snapshot = read_lease(repository, checkout)
            if state["state"] == "held" and state["lease"]["lease_id"] == lease_id:
                require_current(snapshot)
                lock = _unlock_own(repository, checkout, state, lease_id)
                path = lease_path(repository, checkout.key)
                remove_own(path)
                if os.path.lexists(path):
                    raise LeaseError("changed", f"The lease still exists after removal: {path}")
                result = {"status": "ok", "released": True, "lease": state["lease"]}
                if lock is not None:
                    result["lock"] = lock
            elif state["state"] == "unknown":
                result = {"status": "unknown", "released": False, "reason": state["reason"]}
            else:
                result = {"status": "changed-hands", "released": False, "lease": state.get("lease"),
                          "message": "The lease changed hands: it does not carry this lease_id. Nothing was changed."}
    except Busy as busy:
        return {"status": "busy", "released": False, "critical_section": busy.section}
    return _with_left(result, section)


def _listed_checkout(repository: Repository, checkout: Checkout) -> dict:
    state, _ = read_lease(repository, checkout)
    outcome = None
    if not checkout.main and state["state"] == "held":
        if checkout.locked is None and locks.cannot_lock(checkout) is None:
            try:
                outcome, checkout = relock(repository, checkout, state["lease"]["lease_id"])
            except (Unknown, OSError, HandoffError) as error:
                outcome = {"relocked": False, "reason": f"The lease could not be locked again: {error}"}
            state, _ = read_lease(repository, checkout)
        blocked = locks.cannot_lock(checkout)
        if blocked is not None and state["state"] == "held":
            # Git can lock such a worktree and the lock would hide that it is gone, so the lease stays unknown.
            state = {"state": "unknown", "lease": state["lease"],
                     "reason": f"{blocked[1]}; the lease is kept and the worktree is not locked again."}
    lock = _lock_view(checkout, state, outcome)
    if lock["state"] == "unlocked" and state.get("lease") is not None:
        lock["unprotected"] = ("The held lease has no Git worktree lock and could not be locked again: "
                               + (lock.get("relock", {}).get("reason") or state.get("reason")
                                  or "its critical section is held"))
    return {**checkout.view(), "lease": state, "lock": lock}


def listing(repository: Repository) -> dict:
    """Every registered checkout with its lease and its lock. A held lease on a linked worktree with no lock at all is
    locked again inside its critical section and reported; one Git cannot lock again (its directory missing or
    prunable) stays unknown and is shown with no lock."""
    checkouts = [_listed_checkout(repository, checkout) for checkout in repository.checkouts()]
    complete = all(item["lease"]["state"] != "unknown" for item in checkouts)
    return {"status": "ok", "complete": complete, "checkouts": checkouts}
