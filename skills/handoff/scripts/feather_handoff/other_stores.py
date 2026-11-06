"""Records in other checkouts' Handoff stores, reported by list and never changed.

Every checkout of the repository that `git worktree list --porcelain -z`, run from the Working checkout, reports
other than the checkout that holds the current store is looked at; when the current run keeps a checkout-local store,
that enumeration includes the main worktree, which holds the shared store. Only what a user needs before a checkout is
removed is read: the work file names, each one's status line, and whether history.md or archive/ holds anything. No
record body is read beyond the status line, and nothing is written in another checkout."""
import os
from pathlib import Path
import re
import stat
import subprocess

from .storage import HandoffError, Store, _fully_qualified, _same, check_path, is_work_name, lazy_fetch_guard, \
    register_root, run_git

# A status line of the work header (see records.FIELDS) and the ATX heading that ends the header.
_STATUS = re.compile(r"^狀態[：:][ \t]*([^\r\n]*)")
_HEADING = re.compile(r"^ {0,3}#{1,6}(?:[ \t]|$)")
# The header is short; a status line beyond this many bytes is not looked for, so a record body is never read.
_HEADER_LIMIT = 64 * 1024


def _issue(code: str, message: str, work: str | None = None) -> dict:
    return {"code": code, "message": message, **({"work": work} if work is not None else {})}


def _records(listing: str) -> list[list[str]]:
    """The NUL-delimited records of `git worktree list --porcelain -z`; each ends at an empty field."""
    fields = listing.split("\0")
    if fields[-1] != "":
        raise HandoffError("git", "git worktree list --porcelain -z output does not end with a NUL")
    records, current = [], []
    for field in fields[:-1]:
        if field:
            current.append(field)
        elif current:
            records.append(current)
            current = []
    if current:
        raise HandoffError("git", "git worktree list --porcelain -z reported a record without its terminating NUL")
    return records


def _status_line(path: Path) -> str | None:
    """The value of the first status line of the work header, reading no further than that line.

    The file passes the path check before and after it is opened and must stay the file that was checked; reading
    stops at the status line, at the first heading after the title line or after _HEADER_LIMIT bytes."""
    check_path(path)
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode):
        raise HandoffError("not-file", f"Not a regular file: {path}")
    with path.open("rb") as handle:
        opened = os.fstat(handle.fileno())
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            raise HandoffError("changed", f"File changed while opening: {path}")
        check_path(path)
        consumed = 0
        first = True
        while consumed < _HEADER_LIMIT:
            raw = handle.readline(_HEADER_LIMIT - consumed)
            if not raw:
                return None
            consumed += len(raw)
            line = raw.decode("utf-8", errors="replace")
            if first:
                line = line.removeprefix("﻿")
            elif _HEADING.match(line):
                return None
            first = False
            match = _STATUS.match(line)
            if match:
                return match.group(1).strip()
    return None


def _holds_anything(path: Path, directory: bool) -> bool:
    """Whether history.md is a nonempty file, or archive/ a directory with any entry; contents are not read."""
    check_path(path)
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    if directory:
        if not stat.S_ISDIR(info.st_mode):
            raise HandoffError("not-directory", f"Not an archive directory: {path}")
        with os.scandir(path) as entries:
            return any(True for _ in entries)
    if not stat.S_ISREG(info.st_mode):
        raise HandoffError("not-file", f"Not a regular file: {path}")
    return info.st_size > 0


def _code(error: BaseException) -> str:
    if isinstance(error, HandoffError):
        return error.code
    if isinstance(error, PermissionError):
        return "unreadable"
    return "io"


def _entry(listed: str, main: bool, current: Path) -> dict | None:
    """One other checkout's store, None when it is the current store's checkout or holds no .feather/handoffs/.

    The checkout is the strict real path of the path Git lists, registered as a root so the path check confirms it
    still resolves to itself; on a volume that cannot resolve real paths it is the absolute path as listed, and the
    path check then refuses a link anywhere above it. From there `.feather/handoffs/`, each work file, history.md and
    archive/ pass the link, reparse-point and hard-link checks, and a refused path is reported as an issue rather than
    followed. A checkout that no longer exists is reported with code missing."""
    entry = {"checkout": listed, "main_worktree": main, "complete": False, "works": [], "history": None,
             "archive": None, "issues": []}
    try:
        if _same(listed, current):
            return None
    except FileNotFoundError:
        entry["issues"].append(_issue("missing", f"The checkout {listed} that Git lists no longer exists; it may "
                                      "have been moved or deleted, so records it held cannot be confirmed"))
        return entry
    except OSError as error:
        entry["issues"].append(_issue(_code(error), f"The checkout {listed} could not be compared with the current "
                                      f"store's checkout: {error}"))
        return entry
    try:
        real = Path(os.path.realpath(listed, strict=True))
        resolved = True
    except FileNotFoundError:
        entry["issues"].append(_issue("missing", f"The checkout {listed} that Git lists no longer exists; it may "
                                      "have been moved or deleted, so records it held cannot be confirmed"))
        return entry
    except OSError:
        # A volume that cannot resolve real paths: as for such a project root, a link anywhere above is refused.
        real, resolved = Path(os.path.abspath(listed)), False
    entry["checkout"] = str(real)
    if os.path.normcase(str(real)) != os.path.normcase(listed):
        entry["listed"] = listed
    if not real.is_dir():
        entry["issues"].append(_issue("missing", f"The checkout {real} that Git lists is not a directory"))
        return entry
    if resolved:
        register_root(real)
    directory = real / ".feather" / "handoffs"
    entry["store"] = str(directory)
    try:
        check_path(directory)
        try:
            info = directory.lstat()
        except FileNotFoundError:
            return None
        if not stat.S_ISDIR(info.st_mode):
            raise HandoffError("not-directory", f"Not a handoff directory: {directory}")
        with os.scandir(directory) as entries:
            names = sorted(item.name for item in entries if is_work_name(item.name))
    except (OSError, ValueError) as error:
        entry["issues"].append(_issue(_code(error), f"The Handoff store {directory} could not be read: {error}"))
        return entry
    for name in names:
        work = {"work": name, "checkout": str(real), "path": str(directory / name), "status": None}
        try:
            work["status"] = _status_line(directory / name)
        except (OSError, ValueError) as error:
            entry["issues"].append(_issue(_code(error), f"The status of {directory / name} could not be read: {error}",
                                          name))
        entry["works"].append(work)
    for key, path, is_directory in (("history", directory / "history.md", False),
                                    ("archive", directory / "archive", True)):
        try:
            entry[key] = _holds_anything(path, is_directory)
        except (OSError, ValueError) as error:
            entry["issues"].append(_issue(_code(error), f"Whether {path} holds anything could not be read: {error}"))
    entry["complete"] = not entry["issues"]
    return entry


def other_stores(store: Store) -> dict:
    """{other_stores, other_stores_complete, other_stores_issues} for a list result.

    other_stores_complete is false when any checkout could not be read or no longer exists, or when the checkouts
    could not be enumerated; such a result never establishes that no pending work exists elsewhere. Under an
    uncertain root nothing is enumerated. A non-Git project and an explicit root have no other checkout to search."""
    if store.uncertain:
        reasons = "; ".join(store.uncertain.values())
        return {"other_stores": [], "other_stores_complete": False, "other_stores_issues": [_issue(
            "project-root-uncertain", f"Other checkouts were not searched because the root is uncertain: {reasons}")]}
    if store.root["state"] != "git":
        return {"other_stores": [], "other_stores_complete": True, "other_stores_issues": []}
    try:
        try:
            lazy = lazy_fetch_guard(store.project)
        except HandoffError as error:
            if error.code not in {"promisor-remote", "promisor-unknown"}:
                raise
            # `git worktree list` reads no objects, as in store discovery, so it runs without --no-lazy-fetch when
            # the guard forbids only commands that can read objects.
            lazy = False
        listed = run_git(store.project, "worktree", "list", "--porcelain", "-z", errors="replace",
                         no_lazy_fetch=lazy)
        if listed.returncode:
            raise HandoffError("git", "git worktree list --porcelain -z failed: "
                               + (listed.stderr.strip() or f"exit {listed.returncode}"))
        records = _records(listed.stdout)
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        return {"other_stores": [], "other_stores_complete": False, "other_stores_issues": [_issue(
            getattr(error, "code", "git"), f"The repository's checkouts could not be listed: {error}")]}
    entries, issues = [], []
    for index, record in enumerate(records):
        if not record[0].startswith("worktree "):
            issues.append(_issue("git", f"A git worktree list record does not start with a worktree path: "
                                 f"{record[0]!r}"))
            continue
        path = record[0][len("worktree "):]
        if not _fully_qualified(path) or "\n" in path:
            issues.append(_issue("git", f"A git worktree list record has no absolute path: {path!r}"))
            continue
        if "bare" in record[1:]:
            continue  # the repository directory of a bare repository, not a checkout
        entry = _entry(path, index == 0, store.store_checkout)
        if entry is not None:
            entries.append(entry)
    complete = not issues and all(entry["complete"] for entry in entries)
    return {"other_stores": entries, "other_stores_complete": complete, "other_stores_issues": issues}
