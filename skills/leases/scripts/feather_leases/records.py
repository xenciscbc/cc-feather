"""Lease records and the short critical section that changes them.

A lease is `<key>.json` in the lease location; its critical section is `<key>.lock` beside it, created exclusively
for the few file operations of one acquire or release, as the handoff history lock is. A critical section already
held is reported at once with its holder and age; it is never waited on and never broken. The location ignores
itself with its own `.gitignore` holding `*`, written before any lease or lock."""
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

from .checkouts import Checkout, LeaseError, Repository

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


def new_lease(checkout: Checkout, session: str, purpose: str, runtime: str) -> dict:
    moment = stamp()
    return {"schema_version": SCHEMA_VERSION, "checkout": {"key": checkout.key, "path": checkout.path},
            "lease_id": secrets.token_hex(16), "session": session, "host": socket.gethostname(),
            "runtime": runtime, "started": moment, "purpose": purpose, "last_activity": moment,
            # The tool is a short-lived subprocess: this PID never shows that the holder is still running.
            "diagnostic_pid": os.getpid()}


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


def acquire(repository: Repository, checkout: Checkout, session: str, purpose: str, runtime: str) -> dict:
    """An exclusive create inside the lease's critical section; a held or unreadable lease acquires nothing."""
    repository.require_location()
    state, _ = read_lease(repository, checkout)
    if state["state"] == "unknown":
        return {"status": "unknown", "acquired": False, "reason": state["reason"]}
    ensure_location(repository)
    section = _section(repository, checkout, "acquire")
    result = None
    try:
        with section:
            state, _ = read_lease(repository, checkout)
            if state["state"] == "absent":
                lease = new_lease(checkout, session, purpose, runtime)
                try:
                    saved = create_file(lease_path(repository, checkout.key), encode(lease))
                except HandoffError as error:
                    if error.code != "exists":
                        raise
                    state, _ = read_lease(repository, checkout)
                else:
                    result = {"status": "ok", "acquired": True, "lease": lease, "version": saved.version}
    except Busy as busy:
        return {"status": "busy", "acquired": False, "critical_section": busy.section}
    if result is not None:
        return _with_left(result, section)
    if state["state"] == "absent":
        # The exclusive create found a lease that was gone again when reread: report it rather than guess.
        return _with_left({"status": "unknown", "acquired": False,
                           "reason": "A lease appeared and disappeared while it was being acquired."}, section)
    if state["state"] == "unknown":
        return _with_left({"status": "unknown", "acquired": False, "reason": state["reason"]}, section)
    held = {key: state[key] for key in ("lease", "version", "age_seconds", "activity_age_seconds")}
    return _with_left({"status": "held", "acquired": False, **held,
                       "message": "The checkout's lease is held; nothing was acquired."}, section)


def release(repository: Repository, checkout: Checkout, lease_id: str) -> dict:
    """Remove the lease inside its critical section only when it carries the caller's lease_id."""
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
                path = lease_path(repository, checkout.key)
                remove_own(path)
                if os.path.lexists(path):
                    raise LeaseError("changed", f"The lease still exists after removal: {path}")
                result = {"status": "ok", "released": True, "lease": state["lease"]}
            elif state["state"] == "unknown":
                result = {"status": "unknown", "released": False, "reason": state["reason"]}
            else:
                result = {"status": "changed-hands", "released": False, "lease": state.get("lease"),
                          "message": "The lease changed hands: it does not carry this lease_id. Nothing was changed."}
    except Busy as busy:
        return {"status": "busy", "released": False, "critical_section": busy.section}
    return _with_left(result, section)


def listing(repository: Repository) -> dict:
    checkouts = []
    for checkout in repository.checkouts():
        state, _ = read_lease(repository, checkout)
        checkouts.append({**checkout.view(), "lease": state})
    complete = all(item["lease"]["state"] != "unknown" for item in checkouts)
    return {"status": "ok", "complete": complete, "checkouts": checkouts}
