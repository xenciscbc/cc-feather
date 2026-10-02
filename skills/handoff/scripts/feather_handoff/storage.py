"""Project containment and content snapshots shared by public operations."""
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import stat
import subprocess
import secrets


class HandoffError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def git_environment() -> dict[str, str]:
    """Keep a parent Git process from redirecting the explicitly selected project."""
    environment = dict(os.environ)
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE",
                "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_NAMESPACE"):
        environment.pop(key, None)
    environment.update(GIT_OPTIONAL_LOCKS="0", LC_ALL="C")
    return environment


# Canonical project roots resolved in this process; links above them were followed once.
_ROOTS: set[str] = set()


def register_root(path: Path) -> None:
    _ROOTS.add(os.path.normcase(str(path)))


def reset_roots() -> None:
    _ROOTS.clear()


def check_path(path: Path) -> None:
    """Check existing ancestors before following any target, including junctions.

    The walk stops at a registered project root after confirming it still resolves to itself."""
    chain = [path, *path.parents]
    for index, part in enumerate(chain):
        key = os.path.normcase(str(part))
        if key in _ROOTS:
            try:
                current = os.path.normcase(os.path.realpath(part, strict=True))
            except OSError:
                current = None
            if current != key:
                raise HandoffError("unsafe-path", f"Project root changed after it was resolved: {part}")
            chain = chain[:index + 1]
            break
    for part in reversed(chain):
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise HandoffError("unsafe-path", f"Link/reparse path is not supported: {part}")
        if part != path and not stat.S_ISDIR(info.st_mode):
            raise HandoffError("unsafe-path", f"Ancestor is not a directory: {part}")
        if stat.S_ISREG(info.st_mode) and info.st_nlink != 1:
            raise HandoffError("unsafe-path", f"Hard-linked file is not supported: {part}")


def _same(first, second) -> bool:
    one, two = os.stat(first), os.stat(second)
    if not one.st_ino or not two.st_ino:  # identity unavailable: compare resolved spellings
        return os.path.normcase(os.path.realpath(first)) == os.path.normcase(os.path.realpath(second))
    return (one.st_dev, one.st_ino) == (two.st_dev, two.st_ino)


def _discover(path: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(path), "rev-parse", "--show-toplevel"], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=5, env=git_environment())


def _non_git(result: subprocess.CompletedProcess, path: Path) -> bool:
    if "not a git repository" not in result.stderr.lower():
        return False
    # A broken .git marker is not evidence of a non-Git project.
    for ancestor in [path, *path.parents]:
        try:
            (ancestor / ".git").lstat()
        except FileNotFoundError:
            continue
        return False
    return True


def _unresolved_root(requested: str, exact: bool) -> dict:
    """Previous behavior where the volume cannot resolve real paths: links anywhere are refused."""
    path = Path(requested)
    check_path(path)
    if not path.is_dir():
        raise HandoffError("project", f"Project directory does not exist: {path}")
    info = {"requested": str(path), "path": str(path.resolve()), "state": "uncertain"}
    if exact:
        return {**info, "state": "explicit"}
    try:
        result = _discover(path)
        if result.returncode == 0:
            path = Path(result.stdout.strip())
            check_path(path)
            if not path.is_dir():
                raise HandoffError("project", f"Git root is not a directory: {path}")
            return {**info, "path": str(path.resolve()), "state": "git"}
        if _non_git(result, path):
            return {**info, "state": "non-git"}
        return {**info, "reason": result.stderr.strip() or "Git root discovery failed"}
    except (OSError, subprocess.TimeoutExpired) as error:
        return {**info, "reason": str(error)}


def _resolve_root(value: str, exact: bool) -> tuple[dict, bool]:
    """Resolve links above the project once; returns the root and whether it is a trusted canonical root."""
    requested = os.path.abspath(value)
    try:
        canonical = os.path.realpath(requested, strict=True)
    except (FileNotFoundError, NotADirectoryError):
        raise HandoffError("project", f"Project directory does not exist: {requested}") from None
    except OSError:
        if not os.path.isdir(requested):
            raise HandoffError("project", f"Project directory does not exist: {requested}") from None
        return _unresolved_root(requested, exact), False
    if not os.path.isdir(canonical):
        raise HandoffError("project", f"Project directory does not exist: {requested}")
    info = {"requested": requested, "path": canonical, "state": "uncertain"}
    if exact:
        return {**info, "state": "explicit"}, True
    path = Path(canonical)
    try:
        result = _discover(path)
        if result.returncode == 0:
            top = os.path.realpath(result.stdout.strip(), strict=True)
            if not os.path.isdir(top):
                raise HandoffError("project", f"Git root is not a directory: {top}")
            root = next((item for item in [path, *path.parents] if _same(item, top)), None)
            if root is None:
                return {**info, "reason": f"Git root {top} does not contain {canonical}"}, True
            relative = Path(os.path.normcase(canonical)).relative_to(os.path.normcase(str(root))).parts
            asked = Path(requested).parts
            kept = len(asked) - len(relative)
            # Only links above the repository root are resolved; the rest must be spelled as resolved.
            if (kept < 1 or [os.path.normcase(part) for part in asked[kept:]] != list(relative)
                    or not _same(os.path.realpath(Path(*asked[:kept]), strict=True), root)):
                return {**info, "reason": "the path crosses a link below the repository root; confirm with --exact-root"}, True
            return {**info, "path": str(root), "state": "git"}, True
        if _non_git(result, path):
            return {**info, "state": "non-git"}, True
        return {**info, "reason": result.stderr.strip() or "Git root discovery failed"}, True
    except (OSError, subprocess.TimeoutExpired) as error:
        return {**info, "reason": str(error)}, True


def resolve_root(value: str, exact: bool = False) -> dict:
    return _resolve_root(value, exact)[0]


def legal_name(name: str) -> None:
    digits = [*map(str, range(1, 10)), "\u00b9", "\u00b2", "\u00b3"]
    reserved = {"CON", "PRN", "AUX", "NUL", *(f"COM{n}" for n in digits), *(f"LPT{n}" for n in digits)}
    if (not name or name in {".", ".."} or name.rstrip(" .") != name
            or any(c in name for c in '/\\:<>"|?*') or any(ord(c) < 32 for c in name)
            or name.split(".")[0].upper() in reserved):
        raise HandoffError("unsafe-name", f"Invalid filename: {name!r}")


@dataclass(frozen=True)
class Snapshot:
    path: Path
    data: bytes

    @property
    def version(self) -> str:
        return hashlib.sha256(self.data).hexdigest()

    @property
    def text(self) -> str:
        return self.data.decode("utf-8-sig")


def read_file(path: Path) -> Snapshot:
    check_path(path)
    before = path.stat()
    if not stat.S_ISREG(before.st_mode):
        raise HandoffError("not-file", f"Not a regular file: {path}")
    with path.open("rb") as handle:
        opened = os.fstat(handle.fileno())
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            raise HandoffError("changed", f"File changed while opening: {path}")
        data = handle.read()
        after_read = os.fstat(handle.fileno())
    check_path(path)
    after = path.stat()
    signature = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
    if signature(before) != signature(after_read) or signature(before) != signature(after):
        raise HandoffError("changed", f"File changed during read: {path}")
    return Snapshot(path, data)


def create_file(path: Path, data: bytes) -> Snapshot:
    check_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    check_path(path)
    try:
        handle = path.open("xb")
    except FileExistsError:
        raise HandoffError("exists", f"Existing data preserved: {path}") from None
    identity = None
    try:
        try:
            opened = os.fstat(handle.fileno())
            identity = (opened.st_dev, opened.st_ino)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        finally:
            handle.close()
    except BaseException:
        # Remove only the partial file this call created; the original error propagates unchanged.
        try:
            if identity is not None and identity[1]:
                check_path(path)
                current = path.lstat()
                if (current.st_dev, current.st_ino) == identity:
                    path.unlink()
        except (OSError, ValueError):
            pass
        raise
    saved = read_file(path)
    if saved.data != data:
        raise HandoffError("changed", f"Saved file differs; preserve and inspect {path}")
    return saved


def require_current(snapshot: Snapshot) -> None:
    if read_file(snapshot.path).version != snapshot.version:
        raise HandoffError("conflict", f"Source changed; reread before writing: {snapshot.path}")


def replace_file(snapshot: Snapshot, data: bytes) -> Snapshot:
    require_current(snapshot)
    if data == snapshot.data:
        return snapshot
    temporary: Path | None = None
    try:
        # Windows tempfile may retry PermissionError up to TMP_MAX even when a
        # sandbox denies writes. Only actual name collisions warrant a retry.
        for _ in range(3):
            candidate = snapshot.path.parent / f".feather-{secrets.token_hex(16)}.tmp"
            try:
                descriptor = os.open(candidate, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o600)
            except FileExistsError:
                continue
            temporary = candidate
            break
        else:
            raise HandoffError("temporary-conflict", "Temporary name collisions; source preserved, retry later")
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, stat.S_IMODE(snapshot.path.stat().st_mode))
        require_current(snapshot)
        os.replace(temporary, snapshot.path)
        temporary = None
        saved = read_file(snapshot.path)
        if saved.data != data:
            raise HandoffError("changed", f"Saved file differs; preserve and inspect {snapshot.path}")
        return saved
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


class Store:
    def __init__(self, project: str, *, exact_root: bool = False):
        self.root, trusted = _resolve_root(project, exact_root)
        self.project = Path(self.root["path"])
        if trusted:
            register_root(self.project)
        self.directory = self.project / ".feather" / "handoffs"
        check_path(self.directory)

    def require_write_root(self) -> None:
        if self.root["state"] == "uncertain":
            raise HandoffError("project-root-uncertain",
                               f"Root discovery failed: {self.root['reason']}. No writes made. "
                               f"Confirm the project root, then use --project <confirmed-root> --exact-root. "
                               f"Current read scope: {self.project}")

    def work_path(self, name: str) -> Path:
        legal_name(name)
        if not name.lower().endswith(".md") or name.lower() == "history.md":
            raise HandoffError("unsafe-name", "Work must be a direct Markdown file other than history.md")
        path = self.directory / name
        check_path(path)
        return path

    def work_paths(self) -> list[Path]:
        check_path(self.directory)
        if not self.directory.exists():
            return []
        if not self.directory.is_dir():
            raise HandoffError("not-directory", f"Not a handoff directory: {self.directory}")
        return sorted((p for p in self.directory.iterdir()
                       if p.suffix.lower() == ".md" and p.name.lower() != "history.md"),
                      key=lambda p: p.name)
