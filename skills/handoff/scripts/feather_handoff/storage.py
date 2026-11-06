"""Project containment and content snapshots shared by public operations."""
from dataclasses import dataclass
import errno
import hashlib
import os
from pathlib import Path
import re
import stat
import subprocess
import secrets


class HandoffError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def git_environment() -> dict[str, str]:
    """Keep a parent Git process from redirecting the explicitly selected project or the captured output.

    User configuration variables (GIT_CONFIG_PARAMETERS, GIT_CONFIG_COUNT/KEY/VALUE, GIT_CONFIG_GLOBAL/SYSTEM,
    HOME, ...) stay: they cannot select another repository and keep ignore and trust decisions the user's own."""
    environment = dict(os.environ)
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE",
                "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_NAMESPACE",
                "GIT_IMPLICIT_WORK_TREE", "GIT_PREFIX", "GIT_GRAFT_FILE", "GIT_NO_REPLACE_OBJECTS",
                "GIT_REPLACE_REF_BASE", "GIT_SHALLOW_FILE", "GIT_CONFIG",
                "GIT_REDIRECT_STDIN", "GIT_REDIRECT_STDOUT", "GIT_REDIRECT_STDERR"):
        environment.pop(key, None)
    environment.update(GIT_OPTIONAL_LOCKS="0", LC_ALL="C")
    return environment


# Every Git command starts with these after the resolved executable: no configured pager runs, no optional index
# refresh is written, and the empty core.fsmonitor value disables a configured fsmonitor whether Git reads the
# setting as a boolean or a hook path.
GIT_COMMAND = ("--no-pager", "--no-optional-locks", "-c", "core.fsmonitor=")

WINDOWS = os.name == "nt"
# The only file name the resolver accepts. On Windows no PATHEXT applies: a git.cmd or git.bat is a batch file, which
# cmd.exe parses again with its own quoting and expansion rules, so the arguments Git receives would no longer be the
# ones given here.
GIT_NAME = "git.exe" if WINDOWS else "git"
_SEPARATORS = "\\/" if WINDOWS else "/"
# An entry still holding a variable reference was never expanded; it names no directory the user meant.
_UNEXPANDED = re.compile(r"%[^%]+%" if WINDOWS else r"\$(?:\{|[A-Za-z_])")


def _fully_qualified(entry: str) -> bool:
    """A path that names one directory whatever the current directory and drive are.

    Windows: a drive letter followed by a separator, or a UNC path \\\\server\\share; never drive-relative (C:foo),
    rooted without a drive (\\foo), or a device path (\\\\?\\, \\\\.\\). Decided from the text, not ntpath.isabs,
    whose answer for rooted paths differs between Python versions; _considered also skips one holding a further `:`
    or a character in U+F000-U+F0FF (see _colon_split). POSIX: starts with /."""
    if not WINDOWS:
        return entry.startswith("/")
    if len(entry) >= 3 and entry[0].isascii() and entry[0].isalpha() and entry[1] == ":" and entry[2] in _SEPARATORS:
        return True
    if len(entry) < 5 or entry[0] not in _SEPARATORS or entry[1] not in _SEPARATORS or entry[2] in _SEPARATORS:
        return False
    parts = re.split(r"[\\/]", entry[2:])
    return len(parts) >= 2 and parts[0] not in {"?", "."} and bool(parts[1])


# POSIX namespaces whose paths name something different in every process, such as /proc/self/cwd or
# /proc/<pid>/cwd for a current directory and /dev/fd/<n> for an open directory: an entry under them starts with /
# yet can name the current directory.
_PROCESS_NAMESPACES = (("proc",), ("dev", "fd"))


def _climbs(entry: str) -> bool:
    """POSIX: the entry has a `..` component. The kernel follows a symbolic link before it applies the `..` after it,
    so the text alone cannot tell where such an entry leads: with the /var/run -> /run link that many distributions
    ship, /var/run/../proc/self/cwd is /proc/self/cwd. Windows resolves `..` from the text before it follows any
    link, so a `..` component there leads where its text says."""
    return not WINDOWS and ".." in entry.split("/")


def _process_relative(entry: str) -> bool:
    """POSIX: the entry is /proc, /dev/fd or under one of them, judged from the text without resolving links.

    Repeated separators and `.` components are ignored, so neither //proc//self/cwd nor /proc/./self/cwd/ escapes.
    Only meaningful for an entry without a `..` component; _considered skips every entry with one first."""
    parts = [part for part in entry.split("/") if part not in {"", "."}]
    return any(tuple(parts[:len(namespace)]) == namespace for namespace in _PROCESS_NAMESPACES)


# Private-use characters that Git for Windows' MSYS runtime, like Cygwin, maps back to the ASCII characters Windows
# forbids in names: U+F03A becomes `:`.
_MSYS_MAPPED = re.compile("[\uf000-\uf0ff]")


def _colon_split(entry: str) -> bool:
    """Windows: the fully qualified entry holds a `:` anywhere but right after its drive letter, and a UNC entry
    any `:`, or the entry holds any character in U+F000-U+F0FF, which the MSYS layer maps back to such characters
    (U+F03A to `:`). Git for Windows' MSYS layer reads such a value as several entries split at that `:` for the
    programs it starts, so C:\\tools:. would hand them `.`, and so would C:\\tools followed by U+F03A and `.`. A
    drive-letter entry's own `:` is at index 1 and a UNC entry starts with two separators, so both `:` cases are a
    `:` from index 2 on; the private-use range is skipped wherever it appears."""
    return WINDOWS and (":" in entry[2:] or bool(_MSYS_MAPPED.search(entry)))


def _considered(entry: str) -> bool:
    """One directory the user named, the same for every process and current directory: nonempty, fully qualified,
    expanded and, on Windows, without a `:`, or a character in U+F000-U+F0FF, that Git's MSYS layer would split at
    (see _colon_split), on POSIX without a `..` component and outside /proc and /dev/fd. Classifies PATH entries
    and GIT_EXEC_PATH alike."""
    return (bool(entry) and "\0" not in entry and _fully_qualified(entry) and not _UNEXPANDED.search(entry)
            and not _colon_split(entry) and (WINDOWS or not (_climbs(entry) or _process_relative(entry))))


def git_search_path(value: str | None) -> list[str]:
    """The PATH entries the resolver considers and the only ones Git's own PATH keeps, in their order.

    An absent or empty PATH has none. On Windows one pair of surrounding double quotes is removed first. Empty,
    relative, not fully qualified and unexpanded entries are skipped, on Windows every entry with a `:` anywhere but
    right after its drive letter, every UNC entry with a `:` and every entry with a character in U+F000-U+F0FF
    (see _colon_split), and on POSIX every entry with a `..` component (see _climbs) and every entry under /proc or
    /dev/fd (see _process_relative), so neither the current directory nor a directory relative to it takes part."""
    entries = []
    for entry in (value or "").split(os.pathsep):
        if WINDOWS and len(entry) >= 2 and entry[0] == entry[-1] == '"':
            entry = entry[1:-1]
        if _considered(entry):
            entries.append(entry)
    return entries


def _missing_git() -> FileNotFoundError:
    """The error subprocess.run raises today when it cannot find a bare `git`, so every caller's handling holds."""
    if WINDOWS:
        return FileNotFoundError(errno.ENOENT, "The system cannot find the file specified", None, 2)
    return FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), "git")


def resolve_git(value: str | None) -> str:
    """The Git executable the handoff tool starts: the first git_search_path entry holding GIT_NAME as a regular
    file after following links, and on POSIX executable, returned as the entry joined with that name (not a link's
    target). Entries git_search_path skips are never looked at: empty, relative and not fully qualified ones,
    unexpanded ones, on Windows those with a `:` anywhere but right after the drive letter (any `:` in a UNC entry)
    or with a character in U+F000-U+F0FF, and on POSIX those with a `..` component or under /proc or /dev/fd, which
    can name the current directory although they start with /. Raises FileNotFoundError when no entry has one. Asks
    neither the operating system nor Python to search (no shutil.which, os.get_exec_path or os.defpath), starts no
    process and keeps no result between calls."""
    for entry in git_search_path(value):
        candidate = os.path.join(entry, GIT_NAME)
        try:
            found = stat.S_ISREG(os.stat(candidate).st_mode)
        except (OSError, ValueError):
            continue
        if found and (WINDOWS or os.access(candidate, os.X_OK)):
            return candidate
    raise _missing_git()


def run_git(directory: Path, *arguments: str, errors: str = "strict",
            no_lazy_fetch: bool = False) -> subprocess.CompletedProcess:
    """The only place the handoff tool starts Git: `<git> <GIT_COMMAND> [--no-lazy-fetch] -C <directory> <arguments>`.

    <git> is the absolute path resolve_git found in PATH, never a bare name; when it finds none, FileNotFoundError
    propagates and no process starts. Git runs from its own directory with only the entries git_search_path keeps as
    its PATH, so the process's current directory takes part neither in finding Git nor in Git's own lookups, and
    <directory> is passed absolute. An inherited GIT_EXEC_PATH stays only when its value, taken as is without
    removing quotes, holds no path separator (os.pathsep) and is an entry the resolver would consider, so on Windows
    one with a `:` anywhere but right after its drive letter, or with a character in U+F000-U+F0FF, is dropped too;
    any other is dropped, because Git would look up its git-* programs there and puts the value before its children's
    PATH, so a value that is not one considered entry would reach them relative to the project after -C or through
    the process's current directory. Needs no Store, so root discovery can use it. no_lazy_fetch is what
    lazy_fetch_guard returned for the operation. Output is UTF-8 text decoded with `errors`; OSError and
    subprocess.TimeoutExpired propagate, and each caller judges the return code."""
    value = os.environ.get("PATH")
    executable = resolve_git(value)
    environment = git_environment()
    environment["PATH"] = os.pathsep.join(git_search_path(value))
    exec_path = environment.get("GIT_EXEC_PATH")
    if exec_path is not None and (os.pathsep in exec_path or not _considered(exec_path)):
        del environment["GIT_EXEC_PATH"]
    target = str(directory)
    if not _fully_qualified(target):
        target = os.path.abspath(target)
    options = (*GIT_COMMAND, "--no-lazy-fetch") if no_lazy_fetch else GIT_COMMAND
    return subprocess.run([executable, *options, "-C", target, *arguments], capture_output=True, text=True,
                          encoding="utf-8", errors=errors, timeout=5, env=environment,
                          cwd=os.path.dirname(executable))


# The first Git release whose --no-lazy-fetch keeps a command from fetching a missing object from a promisor remote.
NO_LAZY_FETCH_FROM = (2, 45, 0)
_FALSE = {"false", "no", "off", "0", ""}


def _promisor_keys(listing: str) -> list[str]:
    """Settings in a `git config --list -z` listing that declare a promisor remote.

    A remote.<name>.promisor set to a value Git reads as false declares nothing; any other value, including one Git
    would reject, counts as declared."""
    found = []
    for entry in listing.split("\0"):
        key, separator, value = entry.partition("\n")
        name = key.lower()
        if name == "extensions.partialclone" or (name.startswith("remote.") and name.endswith(".partialclonefilter")):
            found.append(key)
        elif name.startswith("remote.") and name.endswith(".promisor"):
            if not separator or value.strip().lower() not in _FALSE:
                found.append(key)
    return found


def lazy_fetch_guard(directory: Path) -> bool:
    """Run before an operation's first Git command that can read objects, and before tracking writes anything.

    Reads the effective configuration with includes followed. Returns False when it declares no promisor remote and
    True when it declares one and Git is 2.45.0 or later, so every later command must pass no_lazy_fetch=True.
    Raises HandoffError promisor-remote when an older Git could fetch from the remote, and promisor-unknown when the
    configuration or the Git version cannot be established; then no command that can read objects may run. OSError
    and subprocess.TimeoutExpired propagate. The configuration and version reads themselves read no objects."""
    listing = run_git(directory, "config", "--list", "--includes", "-z", errors="replace")
    if listing.returncode:
        raise HandoffError("promisor-unknown",
                           "Could not read the Git configuration to find whether it declares a promisor remote: "
                           + (listing.stderr.strip() or f"git config exited with {listing.returncode}"))
    keys = _promisor_keys(listing.stdout)
    if not keys:
        return False
    reported = run_git(directory, "version", errors="replace")
    match = re.match(r"git version (\d+)\.(\d+)\.(\d+)", reported.stdout.strip())
    if reported.returncode or not match:
        raise HandoffError("promisor-unknown",
                           f"The Git configuration declares a promisor remote ({', '.join(keys)}), and the installed "
                           "Git version could not be established")
    version = tuple(map(int, match.groups()))
    if version < NO_LAZY_FETCH_FROM:
        raise HandoffError("promisor-remote",
                           f"The Git configuration declares a promisor remote ({', '.join(keys)}), and Git "
                           f"{'.'.join(map(str, version))} cannot disable lazy fetch (2.45.0 or later can); no command "
                           "that could fetch from that remote was run")
    return True


# Canonical roots (Working checkouts and checkouts that hold the store) resolved strictly in this process; links
# above them were followed once.
_ROOTS: set[str] = set()


def register_root(path: Path) -> None:
    _ROOTS.add(os.path.normcase(str(path)))


def reset_roots() -> None:
    _ROOTS.clear()


FILE_ATTRIBUTE_REPARSE_POINT = 0x400
IO_REPARSE_TAG_NAME_SURROGATE = 0x20000000


def _listed_reparse_tag(part: Path) -> int:
    """The reparse tag from the parent directory listing, which reports it without opening or following the entry.

    Returns 0 when the entry cannot be identified exactly once."""
    try:
        with os.scandir(part.parent) as entries:
            matches = [entry for entry in entries if os.path.normcase(entry.name) == os.path.normcase(part.name)]
        chosen = [entry for entry in matches if entry.name == part.name] or matches
        if len(chosen) != 1:
            return 0
        return getattr(chosen[0].stat(follow_symlinks=False), "st_reparse_tag", 0)
    except OSError:
        return 0


def _is_link(part: Path, info) -> bool:
    """Symbolic links and name-surrogate reparse points (junctions, mount points) are aliases.

    Other reparse points, such as cloud-file placeholders or deduplicated files, hold ordinary data. lstat reports
    the tag of a point it did not follow; a zero tag with the reparse attribute means CPython followed a
    non-surrogate point, so the tag comes from the directory listing. An unidentified tag counts as a link."""
    if stat.S_ISLNK(info.st_mode):
        return True
    if not getattr(info, "st_file_attributes", 0) & FILE_ATTRIBUTE_REPARSE_POINT:
        return False
    tag = getattr(info, "st_reparse_tag", 0) or _listed_reparse_tag(part)
    return not tag or bool(tag & IO_REPARSE_TAG_NAME_SURROGATE)


def check_path(path: Path) -> None:
    """Check existing ancestors before following any target, including junctions.

    The walk stops at a registered root after confirming it still resolves to itself."""
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
        if _is_link(part, info):
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
    return run_git(path, "rev-parse", "--show-toplevel", errors="replace")


NO_TOP_LEVEL = "Git root discovery succeeded without reporting an absolute top-level path"


def _top_level(result: subprocess.CompletedProcess) -> str | None:
    """The reported top level; empty or relative output must never fall back to the working directory."""
    top = result.stdout.strip()
    return top if Path(top).is_absolute() else None


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
            top = _top_level(result)
            if top is None:
                return {**info, "reason": NO_TOP_LEVEL}
            path = Path(top)
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
            top = _top_level(result)
            if top is None:
                return {**info, "reason": NO_TOP_LEVEL}, True
            top = os.path.realpath(top, strict=True)
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


class _StoreRefused(Exception):
    """The Handoff store of a linked worktree could not be accepted; the message is the root's reason."""


def _git_directory(directory: Path, *arguments: str) -> str:
    """The one path a rev-parse query reports: exactly one line, fully qualified, naming an existing directory.

    A non-zero exit, empty or relative output, or more than one line, such as an older Git echoing an option it does
    not know, is refused; nothing falls back to a relative path or the working directory."""
    command = " ".join(arguments)
    try:
        result = run_git(directory, *arguments, errors="replace")
    except (OSError, subprocess.TimeoutExpired) as error:
        raise _StoreRefused(f"git {command} could not be run in {directory}: {error}") from None
    if result.returncode:
        raise _StoreRefused(f"git {command} failed in {directory}: "
                            + (result.stderr.strip() or f"exit {result.returncode}"))
    text = result.stdout[:-1] if result.stdout.endswith("\n") else result.stdout
    if not text or any(character in text for character in "\r\n\0") or not _fully_qualified(text):
        raise _StoreRefused(f"git {command} in {directory} did not report exactly one absolute path")
    if not os.path.isdir(text):
        raise _StoreRefused(f"git {command} in {directory} reported {text}, which is not an existing directory")
    return text


def _identical(first, second) -> bool:
    try:
        return _same(first, second)
    except OSError as error:
        raise _StoreRefused(f"could not compare {first} with {second}: {error}") from None


def _common_directory(checkout: Path) -> Path | None:
    """The repository's common directory when the Working checkout is a linked worktree, else None.

    Decided only by the filesystem identities of its Git directory and the common directory, so a main checkout
    with a separate Git directory is never linked."""
    git_directory = _git_directory(checkout, "rev-parse", "--absolute-git-dir")
    common = _git_directory(checkout, "rev-parse", "--path-format=absolute", "--git-common-dir")
    return None if _identical(git_directory, common) else Path(common)


def _main_worktree(checkout: Path, common: Path) -> Path:
    """The strict real path of the main worktree of a linked worktree's repository.

    Only the first NUL-delimited record of `git worktree list --porcelain -z` run from the Working checkout is
    read. It must name a fully qualified path, not be marked bare, resolve strictly to an existing directory that is
    neither the common directory nor inside it (Git reports the Git directory itself for a separate Git directory or
    a submodule), be its own top level, hold a .git entry, and have the common directory as its Git directory."""
    try:
        listed = run_git(checkout, "worktree", "list", "--porcelain", "-z", errors="replace")
    except (OSError, subprocess.TimeoutExpired) as error:
        raise _StoreRefused(f"git worktree list could not be run: {error}") from None
    if listed.returncode:
        raise _StoreRefused("git worktree list --porcelain -z failed: "
                            + (listed.stderr.strip() or f"exit {listed.returncode}"))
    fields = listed.stdout.split("\0")
    if "" not in fields:
        raise _StoreRefused("git worktree list --porcelain -z reported no NUL-terminated worktree record")
    record = fields[:fields.index("")]
    if not record or not record[0].startswith("worktree "):
        raise _StoreRefused("the first git worktree list record does not start with a worktree path")
    candidate = record[0][len("worktree "):]
    if not _fully_qualified(candidate) or "\n" in candidate:
        raise _StoreRefused(f"the first git worktree list record has no absolute path: {candidate!r}")
    if "bare" in record[1:]:
        raise _StoreRefused(f"the repository's first worktree entry {candidate} is bare, so it has no main worktree "
                            "to hold the shared Handoff store")
    try:
        main = Path(os.path.realpath(candidate, strict=True))
    except FileNotFoundError:
        raise _StoreRefused(f"the main worktree {candidate} does not exist; it may have been moved or deleted") from None
    except OSError as error:
        raise _StoreRefused(f"the main worktree {candidate} could not be resolved to a strict real path: {error}") from None
    if not main.is_dir():
        raise _StoreRefused(f"the main worktree {main} is not a directory")
    if any(_identical(part, common) for part in [main, *main.parents]):
        raise _StoreRefused(f"the first worktree entry {main} is the repository's Git directory or inside it "
                            "(a separate Git directory or a submodule), not a main worktree")
    if not _identical(_git_directory(main, "rev-parse", "--show-toplevel"), main):
        raise _StoreRefused(f"the main worktree {main} is not its own Git top level")
    try:
        (main / ".git").lstat()
    except OSError:
        raise _StoreRefused(f"the main worktree {main} holds no .git entry") from None
    if not _identical(_git_directory(main, "rev-parse", "--absolute-git-dir"), common):
        raise _StoreRefused(f"the Git directory of the main worktree {main} is not the repository's common directory")
    return main


def _select_store(root: dict, trusted: bool) -> tuple[Path, bool, str | None]:
    """The checkout that holds the Handoff store: (its directory, whether it came from a strict real-path resolution
    and may be registered as a root, why it is uncertain or None).

    For a Git root that is a linked worktree, the tracking state is detected in the Working checkout first and
    reported as root["tracking"]; an untracked one keeps its records in the main worktree, accepted by _main_worktree
    and registered as the strict real path of that worktree once its store directory passes the path check. Every
    other root keeps the store under the root that discovery selected, strictly resolved exactly when that root is.
    When the main worktree or the tracking state cannot be established, root["state"] becomes uncertain with the
    reason, and the store stays under the Working checkout so reads stay partial there and every mutation is
    refused; it never falls back to an unregistered store."""
    checkout = Path(root["path"])
    if root["state"] != "git":
        return checkout, trusted, root["reason"] if root["state"] == "uncertain" else None
    try:
        common = _common_directory(checkout)
        if common is None:
            return checkout, trusted, None
        from .tracking import detect_tracking
        try:
            root["tracking"] = detect_tracking(checkout)
        except (OSError, ValueError, subprocess.TimeoutExpired) as error:
            raise _StoreRefused(f"the tracking state of the linked worktree {checkout} could not be detected: "
                                f"{getattr(error, 'code', type(error).__name__)}: {error}") from None
        if root["tracking"] == "tracked":
            return checkout, trusted, None
        main = _main_worktree(checkout, common)
        key = os.path.normcase(str(main))
        registered = key in _ROOTS
        register_root(main)
        try:
            check_path(main / ".feather" / "handoffs")
        except HandoffError as error:
            if not registered:
                _ROOTS.discard(key)
            raise _StoreRefused(f"the shared Handoff store under the main worktree {main} is refused: {error}") from None
        return main, True, None
    except _StoreRefused as refused:
        reason = f"Handoff store discovery failed: {refused}"
        root.update(state="uncertain", reason=reason)
        return checkout, trusted, reason


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


# Windows errors that deny access to a path (ERROR_ACCESS_DENIED, ERROR_WRITE_PROTECT); a sharing or lock violation
# also maps to EACCES but is a file another process holds, not a denial. Only mkdir reports winerror: a file opened
# through the C runtime reports errno alone, and EACCES there also covers a directory already at the target path, so
# create_file judges a failed open only when nothing exists at the target.
_DENIED_WINDOWS = {5, 19}
_DENIED_ERRNO = {errno.EACCES, errno.EPERM, errno.EROFS}


def _mark_denied(error: OSError) -> None:
    """Tag error when creating a new file or directory failed because the operating system or the session sandbox
    denied access; the error itself propagates unchanged, so every caller keeps its own result for it.

    Only creations are judged: a denied creation leaves every existing file as it was, while a failed replacement of
    an existing target can also mean that another process holds it open or that it is read-only."""
    winerror = getattr(error, "winerror", None)
    if WINDOWS and winerror is not None:
        denied = winerror in _DENIED_WINDOWS
    else:
        denied = error.errno in _DENIED_ERRNO
    if denied:
        error.handoff_creation_denied = True


def creation_denied(error: BaseException) -> bool:
    """Whether error is a creation in the store that _mark_denied judged denied; nothing was written by it."""
    return isinstance(error, OSError) and getattr(error, "handoff_creation_denied", False)


def create_file(path: Path, data: bytes) -> Snapshot:
    check_path(path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        _mark_denied(error)
        raise
    check_path(path)
    try:
        handle = path.open("xb")
    except FileExistsError:
        raise HandoffError("exists", f"Existing data preserved: {path}") from None
    except OSError as error:
        if not os.path.lexists(path):
            _mark_denied(error)
        raise
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
            except OSError as error:
                _mark_denied(error)
                raise
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
        try:
            os.replace(temporary, snapshot.path)
        except PermissionError:
            try:
                writable = snapshot.path.stat().st_mode & stat.S_IWRITE
            except OSError:
                writable = True
            if not writable:
                raise HandoffError("read-only", f"{snapshot.path} is read-only; existing data preserved") from None
            raise
        temporary = None
        saved = read_file(snapshot.path)
        if saved.data != data:
            raise HandoffError("changed", f"Saved file differs; preserve and inspect {snapshot.path}")
        return saved
    finally:
        if temporary is not None:
            # The copied mode may be read-only, which blocks removal on Windows; the original error propagates.
            try:
                os.chmod(temporary, stat.S_IREAD | stat.S_IWRITE)
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


class Store:
    """The two locations of one invocation, each resolved on its own and never derived from the other.

    project is the Working checkout: sources, Git state and their containment are read there. store_checkout is
    the checkout that holds the Handoff store, where the ignore rules apply; directory is the store directory under
    it, and every work file, history.md and archive/ is a direct descendant of it. Each location is registered as a
    root only when it came from a strict real-path resolution, so the path check stops at it only after confirming
    it still resolves to itself. uncertain maps each uncertain location ("checkout", "store") to its reason; while
    it is nonempty every mutation is refused and reads are partial. An untracked linked worktree's store_checkout
    is its repository's main worktree (see _select_store); every other root keeps it at the Working checkout."""

    def __init__(self, project: str, *, exact_root: bool = False):
        root, trusted = _resolve_root(project, exact_root)
        self.project = Path(root["path"])
        if trusted:
            register_root(self.project)
        self.uncertain: dict[str, str] = {}
        if root["state"] == "uncertain":
            self.uncertain["checkout"] = root["reason"]
        # Selection may turn the root uncertain when a linked worktree's store cannot be established.
        self.store_checkout, store_trusted, store_reason = _select_store(root, trusted)
        if store_trusted:
            register_root(self.store_checkout)
        if store_reason is not None:
            self.uncertain["store"] = store_reason
        shared = os.path.normcase(str(self.project)) != os.path.normcase(str(self.store_checkout))
        # path keeps its place and meaning for callers that read only it: the directory that holds the records.
        self.root = {**root, "path": str(self.store_checkout), "checkout": str(self.project),
                     "store": str(self.store_checkout), "shared": shared}
        self.directory = self.store_checkout / ".feather" / "handoffs"
        self.history = self.directory / "history.md"
        self.archive = self.directory / "archive"
        check_path(self.directory)

    def require_write_root(self) -> None:
        """Refuse a mutation before its first write while either location is uncertain."""
        if "checkout" in self.uncertain:
            raise HandoffError("project-root-uncertain",
                               f"Root discovery failed: {self.uncertain['checkout']}. No writes made. "
                               f"Confirm the project root, then use --project <confirmed-root> --exact-root. "
                               f"Current read scope: {self.project}")
        if "store" in self.uncertain:
            raise HandoffError("project-root-uncertain",
                               f"Handoff store not established ({self.uncertain['store']}). No writes made. "
                               f"Confirm the project root, then use --project <confirmed-root> --exact-root. "
                               f"Current read scope: {self.directory}")

    def unwritable(self, error: BaseException) -> bool:
        """Whether error is a denied creation in the shared Handoff store, reported as store-unwritable; a
        checkout-local store keeps each operation's previous result for the same error."""
        return bool(self.root["shared"]) and creation_denied(error)

    def work_path(self, name: str) -> Path:
        legal_name(name)
        if not is_work_name(name):
            raise HandoffError("unsafe-name", "Work must be a direct Markdown file <name>.md other than history.md")
        path = self.directory / name
        check_path(path)
        return path

    def work_paths(self) -> list[Path]:
        check_path(self.directory)
        if not self.directory.exists():
            return []
        if not self.directory.is_dir():
            raise HandoffError("not-directory", f"Not a handoff directory: {self.directory}")
        return sorted((p for p in self.directory.iterdir() if is_work_name(p.name)), key=lambda p: p.name)


def is_work_name(name: str) -> bool:
    """One rule for creating and listing work: a .md suffix after a nonempty stem, other than history.md."""
    return Path(name).suffix.lower() == ".md" and name.lower() != "history.md"
