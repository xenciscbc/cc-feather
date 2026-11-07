"""Move records a user confirmed from one other checkout's Handoff store into the current store (adopt).

Trust boundary: the source checkout path comes only from this command's input and is validated on every run; it is
never taken from a list result's other_stores. It must resolve strictly to a non-bare checkout that `git worktree list
--porcelain -z`, run from the Working checkout, reports, whose Git directory is the repository's common directory or
lies directly under its worktrees/, and whose common directory is the current one. Its strict real path is registered
as a pinned root, so the path check covers its .feather/, handoffs/, every file read, replaced or removed there, and
its history lock, and refuses a root replaced after resolution. The two stores must differ in filesystem identity and
neither may contain the other, checked before the first read and again before each removal.

Every target is created exclusively, so a name conflict is decided by the create alone, and read back before its
source is checked against the version the input gave and removed; a failure before removal removes nothing. History
entries are merged by completion identity under the target store's history lock, and the source history is rewritten
only by a version-checked replace after the target's reread confirms every added entry; history.md is never removed.
The source store's history lock is held as well while its history changes or its archives are removed. Outside the
target store directory adopt writes only the target checkout's ignore rules, through the default tracking create
applies, and inside the validated source store the files it removes, the history.md it replaces and the lock it
creates and removes."""
import os
from pathlib import Path
import stat
import subprocess

from .archiving import _candidate, _matching, _newline
from .history import HistoryDocument, HistoryEntry, parse_history
from .history_mutations import remainder, selection
from .other_stores import _records
from .storage import (LOCK_NAME, HandoffError, HistoryLock, Snapshot, Store, _fully_qualified,
                      _mark_denied, _same,
                      acquire_history_lock, check_path, create_file, creation_denied, is_work_name, lazy_fetch_guard,
                      legal_name, read_file, register_root, replace_file, run_git, with_history_lock)
from .tracking import ensure_tracking
from .writing import input_object

OPTIONS = {"source", "works", "history", "archives"}


def _refused(message: str) -> HandoffError:
    return HandoffError("scope", f"{message}. Nothing was changed")


def _versions(raw: object, label: str) -> dict[str, str]:
    """Names mapped to the version of the source file read; two names equal after case folding are refused."""
    if raw is None:
        return {}
    if (not isinstance(raw, dict) or not raw
            or any(not isinstance(name, str) or not isinstance(version, str) for name, version in raw.items())):
        raise HandoffError("input", f"{label} must be a nonempty JSON object mapping each file name to the version "
                           "of the source file read")
    folded: dict[str, str] = {}
    for name in raw:
        if name.casefold() in folded:
            raise HandoffError("input", f"{label} names {folded[name.casefold()]!r} and {name!r}, which are equal "
                               "after case folding; name each file once. Nothing was changed")
        folded[name.casefold()] = name
    return dict(raw)


def _history_request(raw: object) -> dict | None:
    if raw is None:
        return None
    if (not isinstance(raw, dict) or set(raw) != {"version", "ids"} or not isinstance(raw["version"], str)
            or not isinstance(raw["ids"], list) or not raw["ids"]
            or any(not isinstance(item, str) for item in raw["ids"]) or len(set(raw["ids"])) != len(raw["ids"])):
        raise HandoffError("input", "history must be {version, ids}: the source history version read and a "
                           "nonempty list of distinct entry identities")
    return raw


def _guard(directory: Path) -> bool:
    """The lazy-fetch guard of one -C directory. adopt runs no command there that can read objects, so, as for
    other_stores, a promisor remote the installed Git cannot guard only drops --no-lazy-fetch."""
    try:
        return lazy_fetch_guard(directory)
    except HandoffError as error:
        if error.code not in {"promisor-remote", "promisor-unknown"}:
            raise
        return False


def _git(directory: Path, *arguments: str, lazy: bool) -> subprocess.CompletedProcess:
    try:
        result = run_git(directory, *arguments, errors="replace", no_lazy_fetch=lazy)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise _refused(f"git {' '.join(arguments)} could not be run in {directory}: {error}") from None
    if result.returncode:
        raise _refused(f"git {' '.join(arguments)} failed in {directory}: "
                       + (result.stderr.strip() or f"exit {result.returncode}"))
    return result


def _git_path(directory: Path, *arguments: str, lazy: bool) -> str:
    """The one existing, fully qualified directory a rev-parse query reports."""
    output = _git(directory, *arguments, lazy=lazy).stdout
    text = output[:-1] if output.endswith("\n") else output
    if not text or any(character in text for character in "\r\n\0") or not _fully_qualified(text) \
            or not os.path.isdir(text):
        raise _refused(f"git {' '.join(arguments)} in {directory} did not report exactly one existing absolute "
                       "directory")
    return text


def _identical(first, second) -> bool:
    try:
        return _same(first, second)
    except (FileNotFoundError, NotADirectoryError):
        return False
    except OSError as error:
        raise _refused(f"{first} could not be compared with {second}: {error}") from None


def _source_checkout(store: Store, value: object) -> Path:
    """S06-2: the strict real path of a checkout of the current repository named by the input."""
    if store.root["state"] != "git":
        raise _refused(f"adopt moves records between checkouts of one Git repository, and this root is "
                       f"{store.root['state']}, which has no other checkout to adopt from")
    if not isinstance(value, str) or not value or "\0" in value or not _fully_qualified(value):
        raise HandoffError("input", "source must be the absolute path of another checkout of this repository")
    try:
        source = Path(os.path.realpath(value, strict=True))
    except OSError as error:
        raise _refused(f"The source {value} could not be resolved to a strict real path: {error}") from None
    if not source.is_dir():
        raise _refused(f"The source {source} is not a directory")
    lazy = _guard(store.project)
    listed = _git(store.project, "worktree", "list", "--porcelain", "-z", lazy=lazy)
    listed_checkout = False
    for record in _records(listed.stdout):
        path = record[0][len("worktree "):] if record[0].startswith("worktree ") else ""
        if not path or not _fully_qualified(path) or "\n" in path or "bare" in record[1:]:
            continue
        if os.path.isdir(path) and _identical(path, source):
            listed_checkout = True
            break
    if not listed_checkout:
        raise _refused(f"The source {source} is not a checkout that git worktree list reports for this repository")
    common = _git_path(store.project, "rev-parse", "--path-format=absolute", "--git-common-dir", lazy=lazy)
    source_lazy = _guard(source)
    git_directory = _git_path(source, "rev-parse", "--absolute-git-dir", lazy=source_lazy)
    source_common = _git_path(source, "rev-parse", "--path-format=absolute", "--git-common-dir", lazy=source_lazy)
    if not _identical(source_common, common):
        raise _refused(f"The source {source} belongs to another repository: its Git common directory "
                       f"{source_common} is not {common}")
    if not (_identical(git_directory, common) or _identical(Path(git_directory).parent, Path(common) / "worktrees")):
        raise _refused(f"The Git directory {git_directory} of the source {source} is neither the repository's "
                       f"common directory nor one of its worktrees")
    return source


def _contains(outer: Path, inner: Path) -> bool:
    """Whether inner is outer or below it, by spelling of the canonical paths and by filesystem identity."""
    first, second = os.path.normcase(str(outer)), os.path.normcase(str(inner))
    if second == first or second.startswith(first.rstrip("\\/") + os.sep):
        return True
    return any(_identical(part, outer) for part in [inner, *inner.parents])


def _require_distinct(source: Path, store: Store) -> None:
    """S06-1: the source store and the target store differ in filesystem identity and neither contains the other."""
    source_directory = source / ".feather" / "handoffs"
    if _identical(source, store.store_checkout):
        raise _refused(f"The source {source} holds the current Handoff store {store.directory}; there is nothing to "
                       "adopt from it")
    if _contains(store.directory, source_directory) or _contains(source_directory, store.directory):
        raise _refused(f"The source store {source_directory} and the current Handoff store {store.directory} are "
                       "the same directory or one contains the other")


class _SourceStore:
    """The two paths acquire_history_lock reads, for the validated source store."""

    def __init__(self, directory: Path):
        self.directory = directory
        self.history_lock = directory / LOCK_NAME


def _unwritable(store: Store, error: BaseException) -> HandoffError:
    return HandoffError("store-unwritable", f"The Handoff store {store.directory} is not writable: {error}")


def _target_directory(store: Store) -> None:
    """Create the target store directory and its .feather/ parent through the path check when they do not exist."""
    check_path(store.directory)
    if store.directory.is_dir():
        return
    try:
        store.directory.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        _mark_denied(error)
        if creation_denied(error):
            raise _unwritable(store, error) from None
        raise
    check_path(store.directory)


def _code(error: BaseException) -> str:
    if isinstance(error, FileNotFoundError):
        return "not-found"
    return getattr(error, "code", "io")


def _present(path: Path) -> bool | None:
    try:
        return os.path.lexists(path)
    except (OSError, ValueError):
        return None


class _Run:
    """One adopt run: the validated source, the target store and what was created in the target."""

    def __init__(self, store: Store, source: Path):
        self.store, self.source = store, source
        self.directory = source / ".feather" / "handoffs"
        self.created: list[str] = []

    def partial(self, item: dict, error: BaseException | None, message: str | None = None) -> dict:
        """A failure after the target was written and before its source was removed: nothing was removed."""
        result = {**item, "code": "partial", "message": message or str(error),
                  "source_present": _present(Path(item["source_path"])),
                  "target_present": _present(Path(item["target_path"])),
                  "recovery": "Both copies are kept; compare the source and target paths before deciding"}
        if error is not None:
            result["cause_code"] = _code(error)
        return result

    def remove(self, item: dict, path: Path, version: str) -> dict:
        """Check the source against the version given, then remove it and confirm it is gone."""
        try:
            if read_file(path).version != version:
                return self.partial(item, None, f"The source {path} changed after it was read; it was kept")
            _require_distinct(self.source, self.store)
            check_path(path)
            path.unlink()
            if os.path.lexists(path):
                return self.partial(item, None, f"The source {path} still exists after removal")
        except (OSError, ValueError) as error:
            return self.partial(item, error)
        return {**item, "moved": True}

    def move(self, key: str, name: str, version: str, source_path: Path, target_path: Path, checked) -> dict:
        """S06-3 for one work file or sealed archive: create the target exclusively, reread it and match the source
        snapshot's bytes, check the source against the version given, remove it, confirm it is gone. checked
        validates the name and passes both paths through the path check before anything is read."""
        item = {key: name, "moved": False, "source_path": str(source_path), "target_path": str(target_path)}
        try:
            checked()
            snapshot = read_file(source_path)
        except (OSError, ValueError) as error:
            return {**item, "code": _code(error), "message": str(error)}
        if snapshot.version != version:
            return {**item, "code": "conflict", "message": f"The source {source_path} changed since it was read; "
                    "nothing was moved for it"}
        # Only reports what a failed create left behind; the conflict itself is decided by the exclusive create.
        present = _present(target_path)
        try:
            create_file(target_path, snapshot.data)
        except (OSError, ValueError) as error:
            if getattr(error, "code", None) == "exists":
                return {**item, "code": "conflict", "message": f"The current store already holds {target_path}; "
                        "nothing was moved for it"}
            if creation_denied(error):
                return {**item, "code": "store-unwritable", "store": str(self.store.directory),
                        "message": str(_unwritable(self.store, error))}
            if not present and _present(target_path):
                self.created.append(self.relative(target_path))
                return self.partial(item, error)
            return {**item, "code": _code(error), "message": str(error)}
        self.created.append(self.relative(target_path))
        try:
            if read_file(target_path).data != snapshot.data:
                return self.partial(item, None, f"The target {target_path} differs from the source after it was "
                                                "written; the source was kept")
        except (OSError, ValueError) as error:
            return self.partial(item, error)
        return self.remove(item, source_path, version)

    def relative(self, path: Path) -> str:
        return path.relative_to(self.store.directory).as_posix()

    def work(self, name: str, version: str) -> dict:
        source_path, target_path = self.directory / name, self.store.directory / name

        def checked():
            legal_name(name)
            if not is_work_name(name):
                raise HandoffError("unsafe-name", "Work must be a direct Markdown file <name>.md other than "
                                   "history.md")
            check_path(source_path)
            self.store.work_path(name)
        return self.move("work", name, version, source_path, target_path, checked)

    def archive(self, name: str, version: str) -> dict:
        source_path, target_path = self.directory / "archive" / name, self.store.archive / name

        def checked():
            legal_name(name)
            if not name.lower().endswith(".md"):
                raise HandoffError("unsafe-name", "A sealed archive must be a Markdown file <batch>.md")
            check_path(source_path)
            check_path(target_path)
        return self.move("archive", name, version, source_path, target_path, checked)

    def history(self, request: dict) -> dict:
        """Add the selected source entries the target lacks, then remove exactly those from the source history."""
        source_path, target_path = self.directory / "history.md", self.store.history
        section = {"source_path": str(source_path), "target_path": str(target_path), "added": [], "skipped": [],
                   "conflicts": []}
        try:
            original = read_file(source_path)
            if original.version != request["version"]:
                raise HandoffError("conflict", f"The source history {source_path} changed since it was read; "
                                   "nothing was changed in either history")
            document = parse_history(original, "history.md")
            entries = selection(document, request["ids"])
            try:
                existing = read_file(target_path)
            except FileNotFoundError:
                existing = None
            target = parse_history(existing, "history.md") if existing is not None else None
            if target is not None and target.issues:
                raise HandoffError("history-format", f"The current history {target_path} has ambiguous or invalid "
                                   "entry boundaries; nothing was changed in either history")
        except (OSError, ValueError) as error:
            return {**section, "code": _code(error), "message": str(error)}
        added: list[HistoryEntry] = []
        for entry in entries:
            matches = _matching(target, entry.title, entry.completed) if target is not None else []
            if len(matches) == 1 and _same_entry(matches[0], entry):
                section["skipped"].append(entry.identity)
            elif matches:
                section["conflicts"].append({"id": entry.identity, "title": entry.title,
                                             "completed": entry.completed, "code": "conflict",
                                             "message": "The current history holds this completion identity with "
                                                        "a different body, or more than once; both histories keep "
                                                        "their entries"})
            else:
                added.append(entry)
        if not added:
            return section
        newline = _newline(existing)
        data = b"".join(entry.content_bytes if entry.content_bytes.endswith(b"\n") else entry.content_bytes + newline
                        for entry in added)
        candidate = _candidate(existing, data)
        before = len(target.entries) if target is not None else 0
        preview = parse_history(Snapshot(target_path, candidate), "history.md")
        if not _confirms(preview, added, before):
            return {**section, "code": "history-format",
                    "message": "The selected entries cannot be appended to the current history as exactly these "
                               "entries; nothing was changed in either history"}
        item = {"source_path": str(source_path), "target_path": str(target_path)}
        present = existing is not None or _present(target_path)
        try:
            saved = create_file(target_path, candidate) if existing is None else replace_file(existing, candidate)
        except (OSError, ValueError) as error:
            if creation_denied(error):
                return {**section, "code": "store-unwritable", "store": str(self.store.directory),
                        "message": str(_unwritable(self.store, error))}
            if _code(error) in {"exists", "conflict"}:
                return {**section, "code": "conflict", "message": f"{error}; nothing was changed in either history"}
            if (existing is None and not present and _present(target_path)) or (existing is not None
                                                                                and _changed(existing)):
                self.created.append("history.md")
                return {**section, **self.partial(item, error)}
            return {**section, "code": _code(error), "message": str(error)}
        self.created.append("history.md")
        try:
            verified = parse_history(read_file(target_path), "history.md")
        except (OSError, ValueError) as error:
            return {**section, **self.partial(item, error)}
        if verified.snapshot.data != saved.data or not _confirms(verified, added, before):
            return {**section, **self.partial(item, None, "The current history does not hold exactly the added "
                                                          "entries after it was written; the source history was kept")}
        # The current history now holds these entries; they leave the source only through the replace below.
        section.update(added=[entry.identity for entry in added], version=verified.snapshot.version)
        expected = remainder(document, added)
        try:
            _require_distinct(self.source, self.store)
            rewritten = replace_file(original, expected)
            if read_file(source_path).data != expected:
                raise HandoffError("changed", f"The source history {source_path} differs from the expected "
                                   "remainder after it was rewritten")
        except (OSError, ValueError) as error:
            return {**section, **self.partial(item, error)}
        section["source_version"] = rewritten.version
        return section


def _same_entry(first: HistoryEntry, second: HistoryEntry) -> bool:
    """Bodies equal apart from the line terminators that frame a following entry."""
    return first.body_bytes.rstrip(b"\r\n") == second.body_bytes.rstrip(b"\r\n")


def _confirms(document: HistoryDocument, added: list[HistoryEntry], before: int) -> bool:
    """The document parses without issues, keeps its earlier entries and holds every added identity once, with its
    body."""
    if document.issues or len(document.entries) != before + len(added):
        return False
    for entry in added:
        matches = _matching(document, entry.title, entry.completed)
        if len(matches) != 1 or matches[0].identity != entry.identity or not _same_entry(matches[0], entry) \
                or not matches[0].boundary_known:
            return False
    return True


def _changed(snapshot: Snapshot) -> bool:
    try:
        return read_file(snapshot.path).data != snapshot.data
    except (OSError, ValueError):
        return True


def _source_lock(directory: Path) -> HistoryLock:
    try:
        return acquire_history_lock(_SourceStore(directory))
    except HandoffError:
        raise
    except OSError as error:
        raise HandoffError("io", f"The source store's history lock {directory / LOCK_NAME} could not be created: "
                           f"{error}. Nothing was changed") from None


def _target_lock(store: Store) -> HistoryLock:
    try:
        return acquire_history_lock(store)
    except HandoffError:
        raise
    except OSError as error:
        if creation_denied(error):
            raise _unwritable(store, error) from None
        raise


def adopt_records(store: Store, raw: object) -> dict:
    """adopt with {source, works?, history?, archives?}: works and archives map each name to the version of the
    source file read, and history is {version, ids} for the source history. See the module docstring."""
    store.require_write_root()
    payload = input_object(raw)
    if set(payload) - OPTIONS:
        raise HandoffError("input", f"Unknown adopt options: {sorted(set(payload) - OPTIONS)}")
    works = _versions(payload.get("works"), "works")
    archives = _versions(payload.get("archives"), "archives")
    history = _history_request(payload.get("history"))
    if not works and not archives and history is None:
        raise HandoffError("input", "Name at least one work file, the history entries or an archive to adopt")
    source = _source_checkout(store, payload.get("source"))
    _require_distinct(source, store)
    register_root(source)
    run = _Run(store, source)
    check_path(run.directory)
    try:
        info = run.directory.lstat()
    except FileNotFoundError:
        raise HandoffError("not-found", f"The source checkout {source} has no Handoff store "
                           f"{run.directory}; nothing was changed") from None
    if not stat.S_ISDIR(info.st_mode):
        raise HandoffError("not-directory", f"Not a handoff directory: {run.directory}")
    _target_directory(store)

    def moves() -> dict:
        return {"works": [run.work(name, version) for name, version in works.items()],
                "history": run.history(history) if history is not None else None,
                "archives": [run.archive(name, version) for name, version in archives.items()]}

    def locked() -> dict:
        if history is None and not archives:
            return moves()
        moved = with_history_lock(_source_lock(run.directory), moves)
        if "lock_left" in moved:
            # lock_left keeps reporting the current store's lock, as for every other history mutation.
            moved["source_lock_left"] = moved.pop("lock_left")
        return moved

    result = with_history_lock(_target_lock(store), locked)
    complete = (all(item["moved"] for item in (*result["works"], *result["archives"]))
                and (result["history"] is None or ("code" not in result["history"]
                                                    and not result["history"]["conflicts"])))
    result = {"status": "ok" if complete else "partial", "complete": complete,
              "source": {"checkout": str(source), "store": str(run.directory)}, "target": str(store.directory),
              **result}
    if run.created:
        try:
            result["tracking"] = ensure_tracking(store, run.created[0], "default")
        except (OSError, ValueError, subprocess.TimeoutExpired) as error:
            result.update(status="partial", complete=False, code="tracking-failed", cause_code=_code(error),
                          tracking="error", message=str(error),
                          recovery="The records were adopted before tracking failed; do not retry adopt. Resolve "
                                   "the Git rules; a later create or update applies tracking again.")
    return result
