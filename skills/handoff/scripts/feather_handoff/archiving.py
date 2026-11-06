"""Save a completed work body to shared history before removing its source."""
from pathlib import Path
import subprocess

from .history import HEADING, MODERN, HistoryDocument, HistoryEntry, parse_history
from .records import summary
from .storage import (HandoffError, Snapshot, Store, acquire_history_lock, create_file, creation_denied, read_file,
                      replace_file, require_current, with_history_lock)
from .tracking import ensure_tracking, require_track_choice


HISTORY_HEADER = b"# \xe4\xba\xa4\xe6\x8e\xa5\xe6\xad\xb7\xe5\x8f\xb2\n\n"


def _input(raw: object) -> tuple[str, str]:
    if (not isinstance(raw, dict) or "version" not in raw or set(raw) - {"version", "tracking"}
            or not isinstance(raw["version"], str)):
        raise HandoffError("input", "Archive input must be a JSON object containing version and optional tracking")
    tracking = raw.get("tracking", "default")
    if not isinstance(tracking, str) or tracking not in {"default", "track"}:
        raise HandoffError("input", "tracking must be default or track")
    return raw["version"], tracking


def work_body(snapshot: Snapshot, title: str) -> bytes:
    start = 3 if snapshot.data.startswith(b"\xef\xbb\xbf") else 0
    line_end = snapshot.data.find(b"\n", start)
    if line_end < 0:
        raise HandoffError("format", "Completed work must have a title line followed by its body")
    try:
        title_line = snapshot.data[start:line_end].decode("utf-8").removesuffix("\r")
    except UnicodeError as error:
        raise HandoffError("format", f"Invalid UTF-8 title: {error}") from error
    if not title_line.startswith("# ") or title_line[1:].strip() != title:
        raise HandoffError("format", "The first line must be the work title")
    return snapshot.data[line_end + 1:]


def _matching(document: HistoryDocument, title: str, completed: str) -> list[HistoryEntry]:
    return [entry for entry in document.entries
            if entry.title == title and entry.completed == completed]


def same_body(entry: HistoryEntry, body: bytes, document: HistoryDocument) -> bool:
    """Compare an archived body, allowing only a newline that frames a following entry."""
    if entry.body_bytes == body:
        return True
    if body.endswith(b"\n") or entry.body_bytes not in (body + b"\n", body + b"\r\n"):
        return False
    return any(candidate.byte_start == entry.byte_end for candidate in document.entries
               if candidate is not entry)


def check_archivable(snapshot: Snapshot) -> None:
    """Refuse a completed work whose body would not archive as exactly one history entry."""
    item = summary(snapshot)
    if item["problems"]:
        raise HandoffError("format", "; ".join(item["problems"]))
    title, completed = item["title"], item["updated"]
    body = work_body(snapshot, title)
    candidate = HISTORY_HEADER + f"## {title} · 完成：{completed}\n".encode("utf-8") + body
    document = parse_history(Snapshot(Path("history.md"), candidate), "history.md")
    intended = _matching(document, title, completed)
    if (len(document.entries) == 1 and len(intended) == 1 and not document.issues
            and intended[0].boundary_known and intended[0].body_bytes == body):
        return
    line = next((h.group().strip() for h in HEADING.finditer(body.decode("utf-8", "replace"))
                 if MODERN.fullmatch(h.group(1).strip())), None)
    cause = (f"line {line!r} looks like a history entry marker" if line
             else "its body would not parse as a single history entry")
    raise HandoffError("format", f"Completed work cannot be archived exactly: {cause}; reword it")


def _validated_document(snapshot: Snapshot) -> HistoryDocument:
    document = parse_history(snapshot, "history.md")
    if document.issues:
        raise HandoffError("history-format", "History has ambiguous or invalid entry boundaries; existing data was preserved")
    return document


def _blank(existing: Snapshot | None) -> bool:
    """A missing, empty or whitespace-only history is framed like a new one."""
    return existing is None or not existing.data.strip()


def _newline(existing: Snapshot | None) -> bytes:
    """Line terminator of an existing history's first line, so appended framing matches it."""
    end = -1 if _blank(existing) else existing.data.find(b"\n")
    return b"\r\n" if end > 0 and existing.data[end - 1:end] == b"\r" else b"\n"


def _candidate(existing: Snapshot | None, entry_data: bytes) -> bytes:
    if _blank(existing):
        return HISTORY_HEADER + entry_data
    separator = b"" if existing.data.endswith(b"\n") else _newline(existing)
    return existing.data + separator + entry_data


def _pending(work: Snapshot, history_path: Path, code: str, message: str,
             identity: str, title: str, completed: str, history: Snapshot | None,
             appended: bool | None = None) -> dict:
    return {"status": "partial", "complete": False, "archived": False, "code": code,
            "message": message, "recovery": "retry-archive", "id": identity,
            "title": title, "completed": completed, "work_version": work.version,
            "history_version": history.version if history is not None else None,
            "history_appended": appended,
            "work_path": str(work.path), "history_path": str(history_path),
            "work_present": work.path.exists(), "history_present": history_path.exists(),
            "pending": [str(work.path)] if work.path.exists() else []}


def _identity(title: str, completed: str, body: bytes) -> str:
    """The completion identity an archival of this work appends, as check_archivable's candidate history parses it."""
    candidate = HISTORY_HEADER + f"## {title} · 完成：{completed}\n".encode("utf-8") + body
    return _matching(parse_history(Snapshot(Path("history.md"), candidate), "history.md"), title, completed)[0].identity


def _observed(history_path: Path) -> Snapshot | None:
    try:
        return read_file(history_path)
    except (OSError, ValueError):
        return None


def _denied_cause(store: Store, error: BaseException, result: dict) -> dict:
    """A partial result keeps its code; in a shared run a denied store write adds it as cause_code."""
    return {**result, "cause_code": "store-unwritable"} if store.unwritable(error) else result


def _archive_locked(store: Store, work: Snapshot, title: str, completed: str, body: bytes,
                    denied_as_error: bool) -> dict:
    """The history read, append, verification and source removal of one archival, run while holding the lock."""
    history_path = store.history
    existing = None
    try:
        existing = read_file(history_path)
    except FileNotFoundError:
        pass
    marker = f"## {title} · 完成：{completed}".encode("utf-8") + _newline(existing)
    entry_data = marker + body
    if existing is not None:
        document = _validated_document(existing)
        matches = _matching(document, title, completed)
        if len(matches) > 1:
            raise HandoffError("conflict", f"Duplicate completion identity in {history_path}; all data was preserved")
        if matches:
            if not same_body(matches[0], body, document):
                raise HandoffError("conflict", f"Completion identity has a different body in {history_path}; all data was preserved")
            saved = existing
            appended = False
            identity = matches[0].identity
        else:
            candidate = _candidate(existing, entry_data)
            preview = _validated_document(Snapshot(history_path, candidate))
            intended = _matching(preview, title, completed)
            if (len(preview.entries) != len(document.entries) + 1 or len(intended) != 1
                    or intended[0].body_bytes != body or not intended[0].boundary_known):
                raise HandoffError("history-format", "Generated entry cannot be separated exactly; existing data was preserved")
            identity = intended[0].identity
            try:
                saved = replace_file(existing, candidate)
            except (OSError, ValueError) as error:
                if denied_as_error and store.unwritable(error):
                    raise  # Nothing was written: the work and history are as they were.
                observed = None
                try:
                    observed = read_file(history_path)
                except (OSError, ValueError):
                    pass
                return _denied_cause(store, error, _pending(work, history_path, "history-save-failed", str(error),
                                                            identity, title, completed, observed))
            appended = True
    else:
        candidate = _candidate(None, entry_data)
        preview = _validated_document(Snapshot(history_path, candidate))
        intended = _matching(preview, title, completed)
        if (len(preview.entries) != 1 or len(intended) != 1
                or intended[0].body_bytes != body or not intended[0].boundary_known):
            raise HandoffError("history-format", "Generated entry cannot be separated exactly; no history was created")
        identity = intended[0].identity
        try:
            saved = create_file(history_path, candidate)
        except (OSError, ValueError) as error:
            if denied_as_error and store.unwritable(error):
                raise  # Nothing was written: the work is as it was and no history was created.
            observed = None
            try:
                observed = read_file(history_path)
            except (OSError, ValueError):
                pass
            return _denied_cause(store, error, _pending(work, history_path, "history-save-failed", str(error),
                                                        identity, title, completed, observed))
        appended = True

    try:
        verified = _validated_document(read_file(history_path))
    except (OSError, ValueError) as error:
        return _pending(work, history_path, "history-verify-failed", str(error), identity,
                        title, completed, saved, appended)
    matches = _matching(verified, title, completed)
    if len(matches) != 1 or not same_body(matches[0], body, verified):
        return _pending(work, history_path, "history-verify-failed",
                        "Saved history did not contain exactly the completed body", identity,
                        title, completed, verified.snapshot, appended)
    try:
        require_current(work)
        work.path.unlink()
        if work.path.exists():
            raise OSError(f"Completed work still exists after removal: {work.path}")
    except (OSError, ValueError) as error:
        return _pending(work, history_path, "pending-removal", str(error), identity,
                        title, completed, verified.snapshot, appended)
    return {"status": "ok", "complete": True, "archived": True, "id": identity,
            "title": title, "completed": completed, "work_version": work.version,
            "history_version": verified.snapshot.version, "history_appended": appended,
            "work_path": str(work.path), "history_path": str(history_path),
            "work_present": False, "history_present": True, "pending": []}


def archive_work(store: Store, name: str, raw: object, *, apply_tracking: bool = True,
                 denied_as_error: bool = True) -> dict:
    """apply_tracking is False only when a save already applied tracking before archiving. denied_as_error is False
    for the archival a completed save runs, which keeps its partial history-save-failed result when the shared store
    denies the history write; an explicit archive returns that denial as the store-unwritable error. The history
    read, append, verification and source removal run while holding the history lock; a held lock raises LockError
    history-locked before anything is written, and a denied lock creation is handled as a denied history write."""
    store.require_write_root()
    expected, tracking = _input(raw)
    require_track_choice(store, tracking)
    work = read_file(store.work_path(name))
    if expected != work.version:
        raise HandoffError("conflict", "Source changed or version missing; read the completed work again")
    item = summary(work)
    if item["problems"]:
        raise HandoffError("format", "; ".join(item["problems"]))
    if item["status"] != "完成":
        raise HandoffError("completed", "Only a completed work can be archived")
    try:
        check_archivable(work)
    except HandoffError as error:
        raise HandoffError(error.code, f"{error}. Reword it with update {{version, replacement}} "
                           "keeping the same title, 更新 and 狀態：完成") from None
    title, completed = item["title"], item["updated"]
    body = work_body(work, title)
    history_path = store.history
    try:
        lock = acquire_history_lock(store)
    except OSError as error:
        if not creation_denied(error) or (denied_as_error and store.unwritable(error)):
            raise  # Nothing was written: the work and history are as they were.
        # The store denied the lock as it would deny the history write: the same partial result as that denial.
        return _denied_cause(store, error, _pending(work, history_path, "history-save-failed", str(error),
                                                    _identity(title, completed, body), title, completed,
                                                    _observed(history_path)))
    result = with_history_lock(lock, lambda: _archive_locked(store, work, title, completed, body, denied_as_error))
    if result["status"] != "ok":
        return result
    if not apply_tracking:
        return result
    try:
        result["tracking"] = ensure_tracking(store, name, tracking)
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        cause = getattr(error, "code", "io")
        resolve = ("Resolve the Git rules" if cause not in {"promisor-remote", "promisor-unknown"} else
                   "No Git command that could read objects was run because of a promisor remote; report it, and "
                   "upgrade Git to 2.45.0 or later or have the user remove the promisor configuration "
                   "(promisor-unknown: first have the user make the configuration and Git readable)")
        return {**result, "status": "partial", "complete": False, "code": "tracking-failed",
                "cause_code": cause, "message": str(error), "tracking": "error",
                "recovery": "History was saved and the completed work removed before tracking failed; do not retry "
                            f"archive. {resolve}; a later create or update applies tracking again."}
    return result
