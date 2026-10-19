"""repo-check: report what in a directory could run code or redirect reads, without running any of it.

Usage: python -I -B repo_check.py <absolute directory>

Prints one UTF-8 JSON report on standard output and writes nothing anywhere. The report has `complete`, the Git
version and path used, and a list of findings, each with a category, a path or configuration key, its origin where
known and a one-line description. Every entry the tool could not examine, every Git command that failed and every
output it could not parse is a finding of the category `not-examined`, and `complete` is true only when there is
none. The report lists only the items on the fixed checklist below, for the directory as it is now; it never states
that the directory can be trusted.

How it reads the directory:

- Git is found by walking PATH in order, considering only fully qualified entries and skipping every entry inside the
  checked directory, which is reported. It is started by that absolute path, from its own directory, with a PATH of
  only the considered entries, and never from the current or the checked directory.
- Git is pointed at the repository only by `-C <absolute path>`, and only when the layout is the plain one (see
  `analyse_layout`). Configuration files are read as data only by `config --file <absolute path> --no-includes`, from
  Git's own directory, outside every repository. Every Git command other than `git --version` carries the flags in
  `COMMON_FLAGS`, plus `--no-lazy-fetch` on Git 2.45.0 or later. The subcommands are the closed list in
  `REPOSITORY_COMMANDS` and the data read; the tool never runs `git status`, a working-tree diff, textconv, an
  external diff, a filter, or a command that refreshes or writes the index, objects, refs or configuration, or that
  contacts a remote. On older Git it reads neither the index nor any object when a promisor remote is declared.
- The tool walks the working tree itself with metadata that does not follow links, taking each entry's attributes
  from its parent directory's listing, and never descends into a link, junction, other reparse point or cloud
  placeholder. Every metadata read and file open goes through the single function `fs`, which tests observe.
- A path that repository content names (an include target, a `CLAUDE.md` import) is opened only when its text,
  normalised without resolving links, lies inside the checked directory and the walk found every component of it
  to be a plain directory and the file a regular file with one link. Any other target is reported by its text only.
- It imports nothing from the checked directory and runs no file from it.
"""

from __future__ import annotations

import json
import os
import re
import stat
import subprocess
import sys

WINDOWS = os.name == "nt"
CASE_INSENSITIVE = WINDOWS or sys.platform == "darwin"
REPORT_FORMAT = 1
MIN_PYTHON = (3, 11)
OLD_GIT = (2, 32, 0)
NO_LAZY_FETCH_FROM = (2, 45, 0)
READ_LIMIT = 4 * 1024 * 1024
IMPORT_DEPTH = 5
GIT_TIMEOUT = 300

# Every Git command other than `git --version` starts with these: no pager, no optional index refresh, no replacement
# objects, and no fsmonitor, attributes file or excludes file from any configuration.
COMMON_FLAGS = ("--no-pager", "--no-optional-locks", "--no-replace-objects", "-c", "core.fsmonitor=",
                "-c", "core.attributesFile=", "-c", "core.excludesFile=")
# The closed list of subcommands run with `-C <checked directory>`, each with the options it must carry.
REPOSITORY_COMMANDS = {
    "rev-parse": (),
    "ls-files": ("--stage",),
    "check-attr": ("--cached",),
    "cat-file": (),
    "for-each-ref": (),
}
# Removed from Git's environment so that nothing but `-C` selects the repository; every GIT_CONFIG* variable too.
REMOVED_ENVIRONMENT = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_OBJECT_DIRECTORY",
                       "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_NAMESPACE")

FILE_ATTRIBUTE_REPARSE_POINT = 0x400
FILE_ATTRIBUTE_OFFLINE = 0x1000
FILE_ATTRIBUTE_RECALL_ON_OPEN = 0x40000
FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS = 0x400000
PLACEHOLDER_ATTRIBUTES = FILE_ATTRIBUTE_OFFLINE | FILE_ATTRIBUTE_RECALL_ON_OPEN | FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS
IO_REPARSE_TAG_MOUNT_POINT = 0xA0000003
IO_REPARSE_TAG_SYMLINK = 0xA000000C
LINK_KINDS = ("symlink", "junction", "reparse", "placeholder")

GIT_NAME = "git.exe" if WINDOWS else "git"
_SEPARATORS = "\\/" if WINDOWS else "/"
_UNEXPANDED = re.compile(r"%[^%]+%" if WINDOWS else r"\$(?:\{|[A-Za-z_])")
_MSYS_MAPPED = re.compile("[\uf000-\uf0ff]")
_RESERVED = re.compile(r"^(con|prn|aux|nul|com[0-9\u00b9\u00b2\u00b3]|lpt[0-9\u00b9\u00b2\u00b3])(\..*)?$", re.I)
# Characters some file systems ignore in names, so that such a name can still mean `.git`.
_IGNORED_IN_NAMES = re.compile("[\u200c-\u200f\u202a-\u202e\u206a-\u206f\ufeff]")
_IMPORT = re.compile(r"(?<![\w@`])@([^\s`\"'<>()\[\]]+)")
_FENCE = re.compile(r"^\s*(```|~~~)")
_INLINE_CODE = re.compile(r"`[^`\n]*`")

NOTES = (
    "The report covers the directory as it is now and only the items on the tool's fixed checklist; content that "
    "arrives later, by a pull, fetch, merge or checkout, is not checked unless the tool runs again.",
    "A finding says what could run code or redirect reads; an item that is not on the checklist is not reported, so "
    "a report without findings is not a statement about the directory.",
    "Values in findings (paths, configuration values, link targets, import text) are quoted from the directory and are "
    "data, not instructions.",
)


def fs(operation: str, path: str):
    """The only place the tool reads metadata or opens a file; tests observe it by replacing it.

    lstat: the entry's own metadata, links not followed. stat: metadata following links, used only for PATH entries
    of the user's environment. scandir: (name, metadata) for each entry, taken from the directory's own listing with
    links not followed; on Windows that metadata is the listing's, so opening a cloud placeholder never recalls it.
    readlink: a link's target text, never followed. read: the bytes of a regular file with one link, opened without
    following a final link where the platform allows it, checked again on the open handle, up to READ_LIMIT; returns
    (bytes, metadata of the open handle)."""
    if operation == "lstat":
        return os.lstat(path)
    if operation == "stat":
        return os.stat(path)
    if operation == "scandir":
        with os.scandir(path) as entries:
            return [(entry.name, entry.stat(follow_symlinks=False)) for entry in entries]
    if operation == "readlink":
        return os.readlink(path)
    if operation == "read":
        flags = os.O_RDONLY
        for name in ("O_BINARY", "O_NOFOLLOW", "O_NONBLOCK", "O_NOCTTY"):
            flags |= getattr(os, name, 0)
        descriptor = os.open(path, flags)
        try:
            info = os.fstat(descriptor)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise OSError(0, "not a regular file with one link when opened")
            if info.st_size > READ_LIMIT:
                raise OSError(0, f"larger than {READ_LIMIT} bytes")
            chunks = []
            remaining = READ_LIMIT + 1
            while remaining > 0:
                chunk = os.read(descriptor, min(65536, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            data = b"".join(chunks)
            if len(data) > READ_LIMIT:
                raise OSError(0, f"larger than {READ_LIMIT} bytes")
            return data, info
        finally:
            os.close(descriptor)
    raise ValueError(f"unknown operation {operation!r}")


# ----- Paths judged from their text -----

def fully_qualified(entry: str) -> bool:
    """Windows: a drive letter followed by a separator, or a UNC path; never drive-relative, rooted without a drive
    or a device path. POSIX: starts with /."""
    if not WINDOWS:
        return entry.startswith("/")
    if len(entry) >= 3 and entry[0].isascii() and entry[0].isalpha() and entry[1] == ":" and entry[2] in _SEPARATORS:
        return True
    return is_unc(entry)


def is_unc(entry: str) -> bool:
    if not WINDOWS:
        return entry.startswith("//") and not entry.startswith("///")
    if len(entry) < 5 or entry[0] not in _SEPARATORS or entry[1] not in _SEPARATORS or entry[2] in _SEPARATORS:
        return False
    parts = re.split(r"[\\/]", entry[2:])
    return len(parts) >= 2 and parts[0] not in {"?", "."} and bool(parts[1])


def considered(entry: str) -> bool:
    """A PATH entry that names one directory whatever the current directory is: nonempty, fully qualified, expanded,
    on Windows with no `:` after its drive letter and no character in U+F000-U+F0FF, on POSIX with no `..` component
    and not in /proc or /dev/fd."""
    if not entry or "\0" in entry or not fully_qualified(entry) or _UNEXPANDED.search(entry):
        return False
    if WINDOWS:
        return ":" not in entry[2:] and not _MSYS_MAPPED.search(entry)
    parts = entry.split("/")
    if ".." in parts:
        return False
    named = [part for part in parts if part not in {"", "."}]
    return named[:1] != ["proc"] and named[:2] != ["dev", "fd"]


def same_text(path: str) -> str:
    return os.path.normcase(os.path.normpath(path)) if CASE_INSENSITIVE or WINDOWS else os.path.normpath(path)


def native(path: str) -> str:
    """The form the tool uses for its own file system calls: on Windows an extended-length path, so that a name
    Windows would otherwise reinterpret (a trailing dot or space, a reserved device name) names the entry itself."""
    if not WINDOWS or path.startswith("\\\\?\\"):
        return path
    if path.startswith("\\\\"):
        return "\\\\?\\UNC\\" + path[2:]
    return "\\\\?\\" + path


def unusual_name(name: str) -> str | None:
    if any(ord(character) < 32 or ord(character) == 127 for character in name):
        return "holds a control character"
    if name.startswith("-"):
        return "starts with '-', which a command can read as an option"
    if name.endswith((".", " ")):
        return "ends with a dot or space, which Windows drops"
    if _RESERVED.match(name.rstrip(". ")):
        return "is a Windows reserved device name"
    return None


def git_variant(name: str) -> bool:
    """A name that some file system or Git platform reads as `.git`."""
    bare = _IGNORED_IN_NAMES.sub("", name).rstrip(". ").lower()
    return bare == ".git" or re.fullmatch(r"git~\d+", bare) is not None


def classify(info) -> str:
    attributes = getattr(info, "st_file_attributes", 0)
    if attributes & FILE_ATTRIBUTE_REPARSE_POINT:
        tag = getattr(info, "st_reparse_tag", 0)
        if tag == IO_REPARSE_TAG_SYMLINK or stat.S_ISLNK(info.st_mode):
            return "symlink"
        if tag == IO_REPARSE_TAG_MOUNT_POINT:
            return "junction"
        if (tag & 0xFFFF0FFF) == 0x9000001A or attributes & PLACEHOLDER_ATTRIBUTES:
            return "placeholder"
        return "reparse"
    if stat.S_ISLNK(info.st_mode):
        return "symlink"
    if attributes & PLACEHOLDER_ATTRIBUTES:
        return "placeholder"
    if stat.S_ISDIR(info.st_mode):
        return "dir"
    if stat.S_ISREG(info.st_mode):
        return "file"
    return "special"


def bare_layout(head, objects, refs) -> bool:
    """Whether entries of these kinds (None for a missing entry) named `HEAD`, `objects` and `refs` in one directory
    may make it a bare repository layout to Git. `HEAD` counts unless it is a directory: Git accepts a regular file
    and also a symbolic link whose target starts with `refs/`, and an entry the tool cannot classify is counted too,
    so that the result errs towards a repository."""
    return head is not None and head != "dir" and objects is not None and objects != "file" \
        and refs is not None and refs != "file"


KIND_TEXT = {"symlink": "a symbolic link", "junction": "a junction", "reparse": "a reparse point",
             "placeholder": "a cloud placeholder", "special": "not a regular file or directory", "dir": "a directory",
             "file": "a file", "ambiguous": "one of several entries whose names the tool reads as the same"}


class Entry:
    __slots__ = ("parts", "kind", "info", "nlink", "identity", "target")

    def __init__(self, parts, kind, info):
        self.parts = parts
        self.kind = kind
        self.info = info
        self.nlink = None
        self.identity = None
        self.target = None


# ----- Configuration keys on the fixed list -----

def split_key(key: str):
    section, _, rest = key.partition(".")
    if "." in rest:
        subsection, _, name = rest.rpartition(".")
    else:
        subsection, name = None, rest
    return section.lower(), subsection, name.lower()


def truthy(value) -> bool:
    if value is None:
        return True
    text = value.strip().lower()
    if text in {"true", "yes", "on"}:
        return True
    try:
        return int(text, 0) != 0
    except ValueError:
        return False


def listed_key(key: str, value):
    """(kind, description) for a key on the fixed list, or None. kind is 'program', 'path', 'include', 'promisor',
    'layout' or 'setting'."""
    section, subsection, name = split_key(key)
    sub = subsection is not None
    plain = {
        ("core", "fsmonitor"): ("program", "runs a program as the fsmonitor hook whenever Git reads the index"),
        ("core", "hookspath"): ("path", "selects the directory Git runs hooks from"),
        ("core", "sshcommand"): ("program", "runs a program for SSH transport"),
        ("core", "askpass"): ("program", "runs a program to ask for credentials"),
        ("core", "pager"): ("program", "runs a pager program for Git output"),
        ("core", "editor"): ("program", "runs an editor program"),
        ("core", "gitproxy"): ("program", "runs a proxy program for the git protocol"),
        ("sequence", "editor"): ("program", "runs an editor program for rebase"),
        ("core", "attributesfile"): ("path", "names a file Git reads attributes from"),
        ("core", "excludesfile"): ("path", "names a file Git reads ignore patterns from"),
        ("core", "worktree"): ("path", "moves the working tree Git uses"),
        ("diff", "external"): ("program", "runs an external diff program"),
        ("diff", "orderfile"): ("path", "names a file Git reads diff order from"),
        ("interactive", "difffilter"): ("program", "runs a filter program for interactive diffs"),
        ("gpg", "program"): ("program", "runs a signing program"),
        ("credential", "helper"): ("program", "runs a credential helper program"),
        ("uploadpack", "packobjectshook"): ("program", "runs a program when objects are served"),
        ("protocol", "allow"): ("setting", "changes which transports Git allows"),
        ("mailmap", "file"): ("path", "names a file Git reads author mappings from"),
        ("mailmap", "blob"): ("setting", "names a blob Git reads author mappings from"),
        ("blame", "ignorerevsfile"): ("path", "names a file Git reads ignored revisions from"),
        ("log", "showsignature"): ("setting", "makes log run the signature program"),
        ("submodule", "recurse"): ("setting", "makes commands act on submodules too"),
        ("include", "path"): ("include", "includes another configuration file"),
        ("extensions", "partialclone"): ("promisor", "declares a promisor remote that Git fetches missing objects from"),
    }
    if not sub and (section, name) in plain:
        return plain[(section, name)]
    if section == "core" and name == "bare" and not sub:
        return ("layout", "makes Git treat the repository as bare") if truthy(value) else None
    if section == "pager" and not sub:
        return "program", "runs a pager program for one command"
    if section == "alias" and not sub:
        return ("program", "an alias that runs a shell command") if (value or "").lstrip().startswith("!") else None
    if section == "hook" and sub:
        return "program", "configures a hook command"
    if not sub:
        return None
    three = {
        ("diff", "textconv"): ("program", "runs a text conversion program for diffs"),
        ("diff", "command"): ("program", "runs a diff driver program"),
        ("difftool", "cmd"): ("program", "runs a diff tool program"),
        ("mergetool", "cmd"): ("program", "runs a merge tool program"),
        ("filter", "clean"): ("program", "runs a clean filter program when files are added or compared"),
        ("filter", "smudge"): ("program", "runs a smudge filter program when files are checked out"),
        ("filter", "process"): ("program", "runs a long-running filter program"),
        ("merge", "driver"): ("program", "runs a merge driver program"),
        ("gpg", "program"): ("program", "runs a signing program"),
        ("credential", "helper"): ("program", "runs a credential helper program"),
        ("remote", "uploadpack"): ("program", "runs a program in place of upload-pack when fetching"),
        ("remote", "receivepack"): ("program", "runs a program in place of receive-pack when pushing"),
        ("url", "insteadof"): ("setting", "rewrites remote URLs"),
        ("url", "pushinsteadof"): ("setting", "rewrites push URLs"),
        ("protocol", "allow"): ("setting", "changes whether Git allows a transport"),
        ("includeif", "path"): ("include", "includes another configuration file when its condition holds"),
        ("remote", "promisor"): ("promisor", "declares a promisor remote that Git fetches missing objects from"),
        ("remote", "partialclonefilter"): ("promisor", "sets a partial clone filter for a promisor remote"),
    }
    if (section, name) == ("gpg", "defaultkeycommand") and subsection.lower() == "ssh":
        return "program", "runs a program to choose the SSH signing key"
    if (section, name) == ("remote", "promisor") and not truthy(value):
        return None
    if (section, name) in three:
        return three[(section, name)]
    if section == "submodule" and name == "update" and (value or "").lstrip().startswith("!"):
        return "program", "runs a shell command to update the submodule"
    if section == "remote" and name in {"url", "pushurl"} and (value or "").lstrip().lower().startswith("ext::"):
        return "program", "an ext:: remote URL, which runs a command"
    return None


def parse_listing(text: str):
    """Entries of `git config --null --list` output: (key, value), value None for a key without '='."""
    entries = []
    for item in text.split("\0"):
        if not item:
            continue
        key, separator, value = item.partition("\n")
        if not re.fullmatch(r"[A-Za-z0-9-]+\.(?:[^\n]*\.)?[A-Za-z][A-Za-z0-9-]*", key):
            raise ValueError(f"unexpected configuration key {key[:80]!r}")
        entries.append((key, value if separator else None))
    return entries


def parse_config_text(text: str):
    """A small reader for configuration text held in a blob (`.gitmodules`): (key, value) pairs. Raises ValueError on
    a line it cannot read."""
    entries = []
    section = None
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line[0] in "#;":
            continue
        header = re.match(r'^\[\s*([A-Za-z0-9.-]+)(?:\s+"((?:[^"\\]|\\.)*)")?\s*\](.*)$', line)
        if header:
            name, subsection, rest = header.groups()
            if subsection is None:
                section = name.lower()
            else:
                section = name.lower() + "." + re.sub(r"\\(.)", r"\1", subsection)
            line = rest.strip()
            if not line or line[0] in "#;":
                continue
        if section is None:
            raise ValueError(f"line {number} lies outside a section")
        pair = re.match(r"^([A-Za-z][A-Za-z0-9-]*)\s*(?:=\s*(.*))?$", line)
        if not pair:
            raise ValueError(f"line {number} cannot be read")
        key, value = pair.groups()
        if value is not None:
            value = _config_value(value)
        entries.append((f"{section}.{key.lower()}", value))
    return entries


def _config_value(text: str) -> str:
    out = []
    quoted = False
    index = 0
    while index < len(text):
        character = text[index]
        if character == '"':
            quoted = not quoted
        elif character == "\\" and index + 1 < len(text):
            index += 1
            out.append({"n": "\n", "t": "\t", "b": "\b"}.get(text[index], text[index]))
        elif character in "#;" and not quoted:
            break
        else:
            out.append(character)
        index += 1
    return "".join(out).strip()


# ----- The check -----

class Check:
    def __init__(self, root: str):
        self.root = root
        self.findings = []
        self.entries = {}
        self.unlisted = set()
        self.listed = {}
        self.git_path = None
        self.git_directory = None
        self.git_version = None
        self.git_version_text = None
        self.environment = None
        self.no_lazy_fetch = False
        self.read_configs = {}

    # Findings

    def add(self, category: str, description: str, **fields):
        finding = {"category": category}
        finding.update({key: value for key, value in fields.items() if value is not None})
        finding["description"] = description
        self.findings.append(finding)
        return finding

    def missing(self, description: str, **fields):
        return self.add("not-examined", description, **fields)

    # Paths below the checked directory

    def key(self, parts):
        return tuple(part.casefold() for part in parts) if CASE_INSENSITIVE else tuple(parts)

    def absolute(self, parts) -> str:
        return os.path.join(self.root, *parts) if parts else self.root

    @staticmethod
    def rel(parts) -> str:
        return "/".join(parts) if parts else "."

    def inside(self, path: str):
        """The components below the checked directory of an absolute path, judged from its text normalised without
        resolving links, or None when it does not lie inside."""
        normal = os.path.normpath(path)
        root = os.path.normpath(self.root)
        compare = os.path.normcase if CASE_INSENSITIVE or WINDOWS else (lambda text: text)
        if compare(normal) == compare(root):
            return ()
        prefix = root if root.endswith(os.sep) else root + os.sep
        if not compare(normal).startswith(compare(prefix)):
            return None
        return tuple(part for part in normal[len(prefix):].split(os.sep) if part)

    def lookup(self, parts):
        return self.entries.get(self.key(parts))

    def children(self, parts):
        return list(self.listed.get(self.key(parts), ()))

    def descendants(self, parts):
        prefix = self.key(parts)
        return [entry for key, entry in self.entries.items() if len(key) > len(prefix) and key[:len(prefix)] == prefix]

    def path_problem(self, parts, final: str = "file"):
        """Why the path below the checked directory may not be read or handed to Git, from the walk's results, or
        None: every component must be a plain directory, the last one a regular file with one link (or a directory
        when final is 'dir'), and on Windows no component may have a name Windows reads differently."""
        for index in range(1, len(parts) + 1):
            prefix = parts[:index]
            if self.key(prefix[:-1]) in self.unlisted or any(self.key(prefix[:cut]) in self.unlisted
                                                              for cut in range(index)):
                return f"{self.rel(prefix[:-1])} could not be listed"
            entry = self.lookup(prefix)
            if entry is None:
                return f"{self.rel(prefix)} does not exist"
            if WINDOWS and unusual_name(entry.parts[-1]):
                return f"{self.rel(entry.parts)} {unusual_name(entry.parts[-1])}"
            last = index == len(parts)
            wanted = final if last else "dir"
            if entry.kind != wanted:
                return f"{self.rel(entry.parts)} is {KIND_TEXT.get(entry.kind, entry.kind)}"
            if last and final == "file":
                if entry.nlink is None:
                    return f"{self.rel(entry.parts)} could not be examined"
                if entry.nlink != 1:
                    return f"{self.rel(entry.parts)} has {entry.nlink} links"
        return None

    def real_parts(self, parts):
        entry = self.lookup(parts)
        return entry.parts if entry else tuple(parts)

    def read_file(self, parts, purpose: str):
        """The bytes of a file below the checked directory that passes path_problem, or None after a not-examined
        finding."""
        problem = self.path_problem(parts)
        if problem:
            self.missing(f"{purpose} was not read: {problem}", path=self.rel(parts))
            return None
        entry = self.lookup(parts)
        try:
            data, info = fs("read", native(self.absolute(entry.parts)))
        except OSError as error:
            self.missing(f"{purpose} could not be read: {error.strerror or error}", path=self.rel(entry.parts))
            return None
        if entry.identity and (info.st_ino, info.st_dev) != entry.identity and entry.identity[0]:
            self.missing(f"{purpose} changed while it was read", path=self.rel(entry.parts))
            return None
        return data

    # The walk

    def walk(self):
        """List the checked directory with metadata that does not follow links. Every entry is recorded with its kind
        from its parent's listing; a regular file also gets its link count from lstat. Names in one listing that the
        tool's lookups read as the same (on a file system that folds case, names that differ only in case) are all
        recorded as 'ambiguous', listed as not examined and never descended into, read or handed to Git, because
        the tool cannot tell which of them Git opens."""
        stack = [()]
        while stack:
            parts = stack.pop()
            try:
                listing = fs("scandir", native(self.absolute(parts)))
            except OSError as error:
                self.unlisted.add(self.key(parts))
                self.missing(f"could not be listed: {error.strerror or error}", path=self.rel(parts))
                continue
            counts = {}
            for name, _info in listing:
                counts[self.key(parts + (name,))] = counts.get(self.key(parts + (name,)), 0) + 1
            for name, info in sorted(listing, key=lambda item: item[0], reverse=True):
                child = parts + (name,)
                if counts[self.key(child)] > 1:
                    entry = Entry(child, "ambiguous", info)
                    self.entries[self.key(child)] = entry
                    self.listed.setdefault(self.key(parts), []).append(entry)
                    self.missing("another entry in the same directory has a name that differs only in case, so the "
                                 "tool cannot tell which one Git uses; neither was examined", path=self.rel(child))
                    continue
                entry = Entry(child, classify(info), info)
                self.entries[self.key(child)] = entry
                self.listed.setdefault(self.key(parts), []).append(entry)
                if entry.kind == "dir":
                    stack.append(child)
                elif entry.kind == "file":
                    try:
                        metadata = fs("lstat", native(self.absolute(child)))
                    except OSError as error:
                        entry.kind = "unknown"
                        self.missing(f"could not be examined: {error.strerror or error}", path=self.rel(child))
                        continue
                    if not stat.S_ISREG(metadata.st_mode) or classify(metadata) != "file":
                        entry.kind = classify(metadata)
                        continue
                    entry.nlink = metadata.st_nlink
                    entry.identity = (metadata.st_ino, metadata.st_dev)
                elif entry.kind in ("symlink", "junction"):
                    try:
                        entry.target = fs("readlink", native(self.absolute(child)))
                    except (OSError, ValueError) as error:
                        entry.target = None
                        reason = getattr(error, "strerror", None) or error
                        self.missing(f"the link's target could not be read: {reason}", path=self.rel(child))

    # Git

    def find_git(self):
        value = os.environ.get("PATH")
        kept = []
        for raw in (value or "").split(os.pathsep):
            entry = raw[1:-1] if WINDOWS and len(raw) >= 2 and raw[0] == raw[-1] == '"' else raw
            if not considered(entry):
                if entry:
                    self.add("environment", "PATH entry skipped: it is not a fully qualified directory", path=raw)
                continue
            if self.inside(entry) is not None:
                self.add("environment", "PATH entry skipped: it lies inside the checked directory", path=raw)
                continue
            kept.append(entry)
        executable = None
        for entry in kept:
            candidate = os.path.join(entry, GIT_NAME)
            try:
                info = fs("stat", candidate)
            except (OSError, ValueError):
                continue
            if stat.S_ISREG(info.st_mode) and (WINDOWS or info.st_mode & 0o111):
                executable = candidate
                break
        environment = {}
        kept_text = {same_text(entry) for entry in kept}
        for name, setting in os.environ.items():
            upper = name.upper()
            if upper in REMOVED_ENVIRONMENT or upper == "GIT_CONFIG" or upper.startswith("GIT_CONFIG_") \
                    or upper in ("PATH", "GIT_CEILING_DIRECTORIES", "LC_ALL", "LANGUAGE"):
                continue
            if upper == "GIT_EXEC_PATH" and (not considered(setting) or same_text(setting) not in kept_text):
                self.add("environment", "GIT_EXEC_PATH dropped from Git's environment: it is not one of the PATH "
                         "entries Git is given", path=setting)
                continue
            environment[name] = setting
        environment["PATH"] = os.pathsep.join(kept)
        environment["GIT_CEILING_DIRECTORIES"] = os.path.dirname(self.root) or self.root
        environment["LC_ALL"] = "C"
        environment["LANGUAGE"] = "C"
        self.environment = environment
        if executable is None:
            self.missing("no Git was found in the fully qualified PATH entries outside the checked directory, so "
                         "nothing that needs Git was examined")
            return
        self.git_path = executable
        self.git_directory = os.path.dirname(executable)
        try:
            result = subprocess.run([executable, "--version"], executable=executable, cwd=self.git_directory,
                                    env=environment, input=b"", capture_output=True, timeout=GIT_TIMEOUT)
        except (OSError, subprocess.SubprocessError) as error:
            self.missing(f"git --version could not run: {error}")
            self.git_path = None
            return
        text = result.stdout.decode("utf-8", "replace").strip()
        self.git_version_text = text
        match = re.match(r"git version (\d+)\.(\d+)(?:\.(\d+))?", text)
        if result.returncode or not match:
            self.missing("the Git version could not be read, so Git was treated as older than 2.45.0",
                         value=text[:200])
            self.git_version = (0, 0, 0)
        else:
            self.git_version = tuple(int(part or 0) for part in match.groups())
        self.no_lazy_fetch = self.git_version >= NO_LAZY_FETCH_FROM
        if self.git_version < OLD_GIT and match:
            self.add("git-layout", "Git is older than 2.32, which lacks protections later versions apply to "
                     "repositories", value=text)
        inside = self.repository_above(self.git_directory, include_self=True)
        if inside:
            self.missing("the Git executable's directory, where configuration files are read as data, lies inside a "
                         "repository, whose configuration those reads could apply", path=inside)

    def repository_above(self, directory: str, include_self: bool):
        """The first directory, from directory (or its parent) upwards, that holds a `.git` entry or is a bare
        repository layout, found with the tool's own metadata reads; None when there is none."""
        current = os.path.normpath(directory)
        if not include_self:
            parent = os.path.dirname(current)
            if parent == current:
                return None
            current = parent
        while True:
            try:
                fs("lstat", native(os.path.join(current, ".git")))
                return current
            except OSError:
                pass
            try:
                head = fs("lstat", native(os.path.join(current, "HEAD")))
                objects = fs("lstat", native(os.path.join(current, "objects")))
                refs = fs("lstat", native(os.path.join(current, "refs")))
                if bare_layout(classify(head), classify(objects), classify(refs)):
                    return current
            except OSError:
                pass
            parent = os.path.dirname(current)
            if parent == current:
                return None
            current = parent

    def run_git(self, arguments, data: bytes = b""):
        """Run one Git command from the closed list; returns stdout bytes, or None after a not-examined finding."""
        if arguments[:2] == ["config", "--file"]:
            if len(arguments) != 6 or arguments[3:] != ["--no-includes", "--null", "--list"]:
                raise ValueError("not the data read")
        elif arguments[:1] == ["-C"]:
            if arguments[1] != self.root or arguments[2] not in REPOSITORY_COMMANDS:
                raise ValueError("not on the closed list")
            for option in REPOSITORY_COMMANDS[arguments[2]]:
                if option not in arguments[3:]:
                    raise ValueError(f"{arguments[2]} without {option}")
        else:
            raise ValueError("not on the closed list")
        flags = (*COMMON_FLAGS, "--no-lazy-fetch") if self.no_lazy_fetch else COMMON_FLAGS
        command = [self.git_path, *flags, *arguments]
        label = " ".join(arguments[2:4] if arguments[0] == "-C" else arguments[:2])
        try:
            result = subprocess.run(command, executable=self.git_path, cwd=self.git_directory, env=self.environment,
                                    input=data, capture_output=True, timeout=GIT_TIMEOUT)
        except (OSError, subprocess.SubprocessError) as error:
            self.missing(f"git {label} could not run: {error}")
            return None
        stderr = result.stderr.decode("utf-8", "replace").strip()
        if result.returncode or stderr:
            if arguments[0] == "-C" and ("dubious ownership" in stderr or "safe.directory" in stderr):
                raise OwnershipRefused(stderr)
            self.missing(f"git {label} failed (exit {result.returncode})", value=stderr[:500] or None)
            return None
        return result.stdout

    def read_config(self, parts, origin_label: str):
        """The (key, value) entries of a configuration file below the checked directory, read as data without
        following includes; None after a not-examined finding."""
        if self.git_path is None:
            self.missing(f"{origin_label} was not read: no Git to read it with", path=self.rel(parts))
            return None
        problem = self.path_problem(parts)
        if problem:
            self.missing(f"{origin_label} was not read: {problem}", path=self.rel(parts))
            return None
        real = self.real_parts(parts)
        output = self.run_git(["config", "--file", self.absolute(real), "--no-includes", "--null", "--list"])
        if output is None:
            return None
        try:
            entries = parse_listing(output.decode("utf-8", "surrogateescape"))
        except ValueError as error:
            self.missing(f"{origin_label} could not be parsed: {error}", path=self.rel(real))
            return None
        # Keyed by the same normalised key as every lookup, so that `.git/Config` on a file system that folds case is
        # found as `.git/config`, the file Git reads.
        self.read_configs[self.key(real)] = (self.rel(real), entries)
        return entries

    def report_config(self, parts, entries, base_parts, seen=None):
        """Findings for the listed keys of one configuration file, and its includes read as data when they lie inside
        the checked directory and pass the walk's checks."""
        seen = set() if seen is None else seen
        seen.add(self.key(parts))
        origin = self.rel(self.real_parts(parts))
        config_directory = self.absolute(self.real_parts(parts[:-1]))
        for key, value in entries:
            listed = listed_key(key, value)
            if not listed:
                continue
            kind, description = listed
            fields = {"key": key, "value": value, "origin": origin}
            if kind in ("path", "include") and value:
                base = config_directory if kind == "include" or split_key(key)[2] == "worktree" else \
                    self.absolute(base_parts)
                fields.update(self.locate(value, base))
            category = "configuration"
            self.add(category, description, **fields)
            if kind == "include" and value:
                self.follow_include(value, config_directory, origin, seen)

    def follow_include(self, value, base, origin, seen):
        location = self.locate(value, base)
        target = location.get("inside_path")
        if location.get("location") != "inside" or target is None:
            self.missing("include target not read: it lies outside the checked directory or is not a plain path; "
                         "its text is listed only", value=value, origin=origin)
            return
        parts = tuple(target.split("/")) if target != "." else ()
        if self.key(parts) in seen:
            return
        entries = self.read_config(parts, "include target")
        if entries is not None:
            self.report_config(parts, entries, (), seen)

    def locate(self, value: str, base: str) -> dict:
        """Where a path value points, judged from its text: inside the checked directory (and whether it crosses a
        link there), outside it, a UNC path, or a form that cannot be placed."""
        text = value.strip()
        if text.startswith("~") or text.startswith("%(prefix)"):
            return {"location": "outside"}
        if WINDOWS:
            text = text.replace("/", "\\")
        if is_unc(text):
            return {"location": "unc"}
        if fully_qualified(text):
            candidate = text
        elif WINDOWS and (re.match(r"^[A-Za-z]:", text) or text.startswith("\\")):
            return {"location": "unresolved"}
        else:
            candidate = os.path.join(base, text)
        parts = self.inside(candidate)
        if parts is None:
            return {"location": "outside"}
        result = {"location": "inside", "inside_path": self.rel(parts)}
        for index in range(1, len(parts) + 1):
            entry = self.lookup(parts[:index])
            if entry is None:
                break
            if entry.kind in LINK_KINDS:
                result["crosses_link"] = self.rel(entry.parts)
                break
        return result

    def analyse_layout(self):
        """Decide whether the layout is the plain one, the only one on which `-C` commands run: `.git` is a directory,
        not a link and not a gitfile; it holds a `HEAD` file and `objects` and `refs` directories, so that Git accepts
        it and does not go on to the top; it has no `commondir` and no `objects/info/alternates`; no entry of it is a
        link, junction or other reparse point; the top is not itself a bare repository layout (see `bare_top`); and
        `.git/config` and `.git/config.worktree`, read as data, hold no include, no `core.worktree`, no true
        `core.bare` and no `core.attributesFile` or `core.excludesFile`."""
        plain = True
        top = [entry for entry in self.children(()) if entry.parts[-1] == ".git"
               or (CASE_INSENSITIVE and entry.parts[-1].casefold() == ".git")]
        git = top[0] if top else None
        bare = self.bare_top()
        if bare:
            plain = False
            head = self.lookup(("HEAD",))
            self.add("git-layout", "the checked directory is itself a bare repository layout (HEAD, objects and refs "
                     "at its top), which Git can use as a repository", path=".",
                     kind=None if head.kind == "file" else head.kind, target=head.target)
            if self.lookup(("config",)):
                entries = self.read_config(("config",), "the bare layout's configuration")
                if entries is not None:
                    self.report_config(("config",), entries, ())
            self.hooks(("hooks",))
        if git is None:
            if bare:
                return self.not_plain()
            self.add("git-layout", "the checked directory has no .git entry of its own", path=".")
            return False
        name = git.parts
        if git.kind in LINK_KINDS:
            self.add("git-layout", f".git is {KIND_TEXT[git.kind]}; it was not followed", path=self.rel(name),
                     target=git.target)
            return self.not_plain()
        if git.kind == "file":
            self.gitfile(name)
            return self.not_plain()
        if git.kind != "dir":
            self.add("git-layout", f".git is {KIND_TEXT.get(git.kind, git.kind)}", path=self.rel(name))
            return self.not_plain()
        if self.key(name) in self.unlisted:
            return self.not_plain()
        # Git uses `.git` only when it accepts it as a Git directory; otherwise it goes on to try the top itself as a
        # bare repository, whose configuration it then applies. So `.git` must hold a `HEAD` file and `objects` and
        # `refs` directories.
        for required, wanted in (("HEAD", "file"), ("objects", "dir"), ("refs", "dir")):
            entry = self.lookup(name + (required,))
            if entry is None or entry.kind != wanted:
                plain = False
                found = "is missing" if entry is None else f"is {KIND_TEXT.get(entry.kind, entry.kind)}"
                self.add("git-layout", f"the Git directory's {required} {found}, so Git may not accept .git as a Git "
                         f"directory and may look for another; it needs {KIND_TEXT[wanted]}",
                         path=self.rel(name + (required,)))
        for descendant in self.descendants(name):
            if self.key(descendant.parts) in self.unlisted:
                plain = False
            if descendant.kind in LINK_KINDS:
                plain = False
                self.add("git-layout", f"an entry of the Git directory is {KIND_TEXT[descendant.kind]}; it was not "
                         "followed", path=self.rel(descendant.parts), target=descendant.target)
            elif descendant.kind == "special":
                plain = False
                self.add("git-layout", "an entry of the Git directory is not a regular file or directory",
                         path=self.rel(descendant.parts))
            elif descendant.kind in ("unknown", "ambiguous"):
                plain = False
        linked = [descendant for descendant in self.descendants(name)
                  if descendant.kind == "file" and descendant.nlink and descendant.nlink > 1]
        if linked:
            self.add("git-layout", f"{len(linked)} files in the Git directory have more than one link, as a clone "
                     "from a local path creates; they were only examined, never opened", path=self.rel(name))
        common = self.lookup(name + ("commondir",))
        if common is not None:
            plain = False
            text = self.read_file(name + ("commondir",), "commondir")
            value = text.decode("utf-8", "surrogateescape").strip() if text is not None else None
            fields = self.locate(value, self.absolute(name)) if value else {}
            self.add("git-layout", "commondir makes Git use another directory's objects, refs and configuration",
                     path=self.rel(common.parts), value=value, **fields)
        alternates = self.lookup(name + ("objects", "info", "alternates"))
        if alternates is not None:
            plain = False
            text = self.read_file(alternates.parts, "alternates")
            if text is not None:
                base = self.absolute(name + ("objects",))
                for line in text.decode("utf-8", "surrogateescape").splitlines():
                    if line.strip() and not line.startswith("#"):
                        self.add("git-layout", "alternates make Git read objects from another directory",
                                 path=self.rel(alternates.parts), value=line, **self.locate(line, base))
        for file_name, required in (("config", True), ("config.worktree", False)):
            parts = name + (file_name,)
            if self.lookup(parts) is None and not required:
                continue
            entries = self.read_config(parts, f".git/{file_name}")
            if entries is None:
                plain = False
                continue
            self.report_config(parts, entries, ())
            for key, value in entries:
                section, subsection, option = split_key(key)
                if subsection is None and section == "core" and option in ("worktree", "attributesfile",
                                                                              "excludesfile"):
                    plain = False
                elif subsection is None and section == "core" and option == "bare" and truthy(value):
                    plain = False
                elif section in ("include", "includeif") and option == "path":
                    plain = False
        if not plain or bare:
            return self.not_plain()
        return True

    def bare_top(self) -> bool:
        """Whether the checked directory's top may be a bare repository layout: an entry named `HEAD` of any kind but
        a directory (a regular file, a symbolic link, which Git accepts when its target starts with `refs/`, a
        junction or other reparse point, an ambiguous name, a special file or anything the walk could not classify)
        together with `objects` and `refs` entries that are not regular files (a directory, or a link Git would
        follow to one). Erring towards a bare layout only stops the `-C` commands."""
        head, objects, refs = (self.lookup((name,)) for name in ("HEAD", "objects", "refs"))
        return bare_layout(head and head.kind, objects and objects.kind, refs and refs.kind)

    def not_plain(self):
        self.missing("Git was not run on the repository because its layout is not the plain one: the index, "
                     "attributes, refs and submodule entries were not examined")
        return False

    def gitfile(self, parts):
        data = self.read_file(parts, "the gitfile")
        if data is None:
            return
        text = data.decode("utf-8", "surrogateescape").strip()
        match = re.match(r"gitdir:\s*(.*)$", text)
        if not match:
            self.add("git-layout", ".git is a file that does not name a Git directory", path=self.rel(parts),
                     value=text[:500])
            return
        value = match.group(1).strip()
        location = self.locate(value, self.root)
        self.add("git-layout", ".git is a gitfile that points Git at another Git directory", path=self.rel(parts),
                 value=value, **location)
        target = location.get("inside_path")
        if location.get("location") == "inside" and target and "crosses_link" not in location:
            directory = tuple(target.split("/"))
            problem = self.path_problem(directory, final="dir")
            if problem:
                self.missing(f"the gitfile's target was not read: {problem}", path=target)
                return
            for file_name in ("config", "config.worktree"):
                if self.lookup(directory + (file_name,)) is None:
                    continue
                entries = self.read_config(directory + (file_name,), "the gitfile target's configuration")
                if entries is not None:
                    self.report_config(directory + (file_name,), entries, ())
            self.hooks(directory + ("hooks",))
        elif "crosses_link" in location:
            self.missing("the gitfile's target was not read: it crosses a link", value=value)

    def other_git_directories(self):
        """Configuration and hooks of submodules and linked worktrees, read as data and reported."""
        git = self.lookup((".git",))
        if git is None or git.kind != "dir":
            return
        name = git.parts
        modules = self.lookup(name + ("modules",))
        if modules is not None and modules.kind != "dir":
            self.missing(f"the submodule Git directories were not examined: .git/modules is "
                         f"{KIND_TEXT.get(modules.kind, modules.kind)}", path=self.rel(modules.parts))
        elif modules is not None:
            for directory in self.module_directories(modules.parts):
                for file_name in ("config", "config.worktree"):
                    if self.lookup(directory + (file_name,)) is None:
                        continue
                    entries = self.read_config(directory + (file_name,), "a submodule's configuration")
                    if entries is not None:
                        self.report_config(directory + (file_name,), entries, (), set())
                self.hooks(directory + ("hooks",))
        worktrees = self.lookup(name + ("worktrees",))
        if worktrees is not None and worktrees.kind == "dir":
            for worktree in self.children(worktrees.parts):
                if worktree.kind != "dir":
                    continue
                gitdir = self.lookup(worktree.parts + ("gitdir",))
                value = None
                if gitdir is not None:
                    data = self.read_file(gitdir.parts, "a linked worktree's gitdir")
                    value = data.decode("utf-8", "surrogateescape").strip() if data is not None else None
                self.add("git-layout", "a linked worktree", path=self.rel(worktree.parts), value=value)
                if self.lookup(worktree.parts + ("config.worktree",)) is not None:
                    parts = worktree.parts + ("config.worktree",)
                    entries = self.read_config(parts, "a linked worktree's configuration")
                    if entries is not None:
                        self.report_config(parts, entries, (), set())
                self.hooks(worktree.parts + ("hooks",))

    def module_directories(self, parts):
        """The submodule Git directories below parts, recognised by their layout: a `HEAD` file with `objects` and
        `refs` directories, `config` not required. A directory holding none of those names is one level of a
        submodule name with slashes and is searched further; one holding some but not that layout cannot be
        classified and is listed as not examined."""
        found = []
        for child in sorted(self.children(parts), key=lambda entry: entry.parts):
            if child.kind != "dir":
                continue
            head, objects, refs = (self.lookup(child.parts + (name,)) for name in ("HEAD", "objects", "refs"))
            if head is not None and head.kind == "file" and objects is not None and objects.kind == "dir" \
                    and refs is not None and refs.kind == "dir":
                found.append(child.parts)
                nested = self.lookup(child.parts + ("modules",))
                if nested is not None and nested.kind == "dir":
                    found.extend(self.module_directories(nested.parts))
            elif any(self.lookup(child.parts + (name,)) is not None
                     for name in ("HEAD", "objects", "refs", "config", "commondir")):
                self.missing("a directory under .git/modules that is not a complete Git directory (a HEAD file with "
                             "objects and refs directories), so its configuration and hooks were not examined",
                             path=self.rel(child.parts))
            else:
                found.extend(self.module_directories(child.parts))
        return found

    def hooks(self, parts, origin=None):
        directory = self.lookup(parts)
        if directory is None:
            return
        if directory.kind != "dir":
            self.add("hooks", f"the hooks directory is {KIND_TEXT.get(directory.kind, directory.kind)}; it was not "
                     "followed", path=self.rel(directory.parts), target=directory.target, origin=origin)
            return
        for entry in sorted(self.children(parts), key=lambda entry: entry.parts):
            if entry.parts[-1].endswith(".sample"):
                continue
            self.add("hooks", "a hook Git can run", path=self.rel(entry.parts), origin=origin,
                     kind=None if entry.kind == "file" else entry.kind)

    def top_configs(self):
        """(origin, entries) of `.git/config` and `.git/config.worktree` as read, the origin spelled as on disk."""
        git = self.lookup((".git",))
        if git is None:
            return []
        keys = [self.key(git.parts + (name,)) for name in ("config", "config.worktree")]
        return [self.read_configs[key] for key in keys if key in self.read_configs]

    def hooks_path(self):
        for origin, entries in self.top_configs():
            for key, value in entries:
                if key.lower() != "core.hookspath" or not value:
                    continue
                location = self.locate(value, self.root)
                if location.get("location") == "inside" and "crosses_link" not in location:
                    target = location["inside_path"]
                    self.add("hooks", "core.hooksPath names a directory inside the working tree, so its content "
                             "chooses the hooks Git runs", path=target, origin=origin)
                    self.hooks(tuple(target.split("/")) if target != "." else (), origin=origin)

    def repository(self):
        """The `-C` commands, run only for the plain layout."""
        try:
            self._repository()
        except OwnershipRefused as refused:
            self.add("git-layout", "Git refused the directory for its ownership (safe.directory); the tool does not "
                     "override that", value=str(refused)[:500])
            self.missing("Git was not run on the repository because Git refused it for its ownership")

    def _repository(self):
        # Confirmed without comparing paths: Git resolves links in the paths it prints on POSIX, so a checked
        # directory reached through a link would not match its own text. An empty prefix says that `-C` landed on the
        # top of the working tree, and a Git directory printed as the relative `.git` says that Git selected the
        # `.git` in that directory, not one it found elsewhere.
        output = self.run_git(["-C", self.root, "rev-parse", "--is-bare-repository", "--show-prefix", "--git-dir"])
        if output is None:
            self.missing("the repository's layout could not be confirmed, so no further Git command ran")
            return
        lines = output.decode("utf-8", "surrogateescape").split("\n")
        if lines != ["false", "", ".git", ""]:
            self.missing("Git did not report the checked directory as the working tree of its .git, so no further "
                         "Git command ran", value="\n".join(lines)[:500])
            return
        # Decided before any command that reads the index or objects: reading a sparse index expands it, which reads
        # trees, and on Git older than 2.45.0 a missing one is fetched from the promisor remote.
        promisor = self.promisor_declared()
        if promisor and not self.no_lazy_fetch:
            self.missing("a promisor remote is declared and this Git is older than 2.45.0, which cannot stop reads of "
                         "missing objects from fetching them, so Git read neither the index nor any object: the index "
                         "entries (mode 120000 entries, gitlinks, .gitattributes and .gitmodules), their content, the "
                         "attribute drivers and the refs under refs/replace/ were not examined",
                         value=", ".join(promisor))
            return
        listing = self.run_git(["-C", self.root, "ls-files", "--stage", "-z"])
        if listing is None:
            return
        index = []
        for item in listing.decode("utf-8", "surrogateescape").split("\0"):
            if not item:
                continue
            match = re.fullmatch(r"(\d{6}) ([0-9a-f]{40,64}) (\d)\t(.+)", item, re.S)
            if not match:
                self.missing("git ls-files output could not be parsed", value=item[:200])
                return
            index.append(match.groups())
        attributes, gitmodules = [], None
        for mode, object_id, _stage, path in index:
            if mode == "120000":
                self.add("index", "an index entry with mode 120000, which a checkout that supports symbolic links "
                         "creates as a link", path=path)
            elif mode == "160000":
                self.add("refs-and-submodules", "a gitlink (submodule commit) in the index", path=path,
                         value=object_id)
            if path == ".gitattributes" or path.endswith("/.gitattributes"):
                attributes.append((path, object_id))
            if path == ".gitmodules":
                gitmodules = object_id
        for path, object_id in attributes:
            blob = self.run_git(["-C", self.root, "cat-file", "blob", object_id])
            if blob is None:
                continue
            self.report_attributes(blob.decode("utf-8", "surrogateescape"), path)
        if index:
            self.attribute_drivers([path for mode, _object_id, _stage, path in index if mode != "160000"])
        if gitmodules:
            blob = self.run_git(["-C", self.root, "cat-file", "blob", gitmodules])
            if blob is not None:
                self.report_gitmodules(blob.decode("utf-8", "surrogateescape"))
        refs = self.run_git(["-C", self.root, "for-each-ref", "--format=%(refname)%00%(objectname)", "refs/replace/"])
        if refs is not None:
            for line in refs.decode("utf-8", "surrogateescape").splitlines():
                name, separator, target = line.partition("\0")
                if not separator:
                    self.missing("git for-each-ref output could not be parsed", value=line[:200])
                    continue
                self.add("refs-and-submodules", "a replacement ref, which makes Git show another object in place of "
                         "the one named", key=name, value=target)

    def promisor_declared(self):
        found = []
        for _origin, entries in self.top_configs():
            for key, value in entries:
                listed = listed_key(key, value)
                if listed and listed[0] == "promisor":
                    found.append(key)
        return found

    def report_attributes(self, text: str, origin: str):
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            drivers = re.findall(r"(?:^|\s)(filter|diff|merge)=(\S+)", stripped)
            macro = stripped.startswith("[attr]")
            if drivers or macro:
                self.add("attributes", "selects a driver whose configured program Git runs" if drivers
                         else "defines an attribute macro", origin=origin, value=stripped,
                         drivers=[f"{name}={value}" for name, value in drivers] or None)

    def attribute_drivers(self, paths):
        output = self.run_git(["-C", self.root, "check-attr", "--cached", "-z", "--stdin", "filter", "diff", "merge"],
                              data="\0".join(paths).encode("utf-8", "surrogateescape") + b"\0")
        if output is None:
            return
        fields = output.decode("utf-8", "surrogateescape").split("\0")
        if fields and fields[-1] == "":
            fields.pop()
        if len(fields) % 3:
            self.missing("git check-attr output could not be parsed")
            return
        selected = {}
        for index in range(0, len(fields), 3):
            path, attribute, value = fields[index:index + 3]
            if value in ("unspecified", "unset", "set"):
                continue
            selected.setdefault(f"{attribute}={value}", []).append(path)
        for driver, paths in sorted(selected.items()):
            self.add("attributes", "tracked files that select this driver", key=driver, value=paths[:20],
                     count=len(paths))

    def report_gitmodules(self, text: str):
        try:
            entries = parse_config_text(text)
        except ValueError as error:
            self.missing(f".gitmodules could not be parsed: {error}", path=".gitmodules")
            return
        for key, value in entries:
            section, subsection, name = split_key(key)
            if section != "submodule" or subsection is None:
                continue
            if name in ("path", "url"):
                self.add("refs-and-submodules", f"a submodule's {name} in .gitmodules", key=key, value=value,
                         origin=".gitmodules")
            elif name == "update" and (value or "").lstrip().startswith("!"):
                self.add("refs-and-submodules", "a submodule update setting that runs a shell command", key=key,
                         value=value, origin=".gitmodules")

    def info_attributes(self):
        git = self.lookup((".git",))
        if git is None or git.kind != "dir":
            return
        parts = git.parts + ("info", "attributes")
        if self.lookup(parts) is None:
            return
        data = self.read_file(parts, ".git/info/attributes")
        if data is not None:
            self.report_attributes(data.decode("utf-8", "surrogateescape"), self.rel(parts))

    # The working tree

    def working_tree(self):
        git = self.lookup((".git",))
        git_key = self.key(git.parts) if git is not None else None
        for key in sorted(self.entries):
            entry = self.entries[key]
            if git_key is not None and key[:len(git_key)] == git_key:
                continue
            path = self.rel(entry.parts)
            name = entry.parts[-1]
            if entry.kind in ("symlink", "junction"):
                self.add("working-tree", f"{KIND_TEXT[entry.kind]}; it was not followed", path=path,
                         target=entry.target)
            elif entry.kind in ("reparse", "placeholder"):
                self.add("working-tree", f"{KIND_TEXT[entry.kind]}; it was not opened or followed", path=path)
            elif entry.kind == "special":
                self.add("working-tree", "an entry that is not a regular file or directory", path=path)
            elif entry.kind == "file" and entry.nlink and entry.nlink > 1:
                self.add("working-tree", f"a file with {entry.nlink} links, so it shares its content with another "
                         "name; it was not opened", path=path)
            problem = unusual_name(name)
            if problem:
                self.add("working-tree", f"a name that {problem}", path=path)
            if git_variant(name) and entry is not git:
                self.add("working-tree", "a nested repository or a name Git can read as .git", path=path,
                         kind=entry.kind)
            elif entry.kind == "dir":
                head = self.lookup(entry.parts + ("HEAD",))
                objects = self.lookup(entry.parts + ("objects",))
                refs = self.lookup(entry.parts + ("refs",))
                if head is not None and head.kind == "file" and objects is not None and objects.kind == "dir" \
                        and refs is not None and refs.kind == "dir" and not git_variant(name):
                    self.add("working-tree", "a nested bare repository layout (HEAD, objects and refs)", path=path)

    # Claude Code and agent files

    def claude_files(self):
        git = self.lookup((".git",))
        git_key = self.key(git.parts) if git is not None else None
        imports_from = []
        for key in sorted(self.entries):
            entry = self.entries[key]
            if git_key is not None and key[:len(git_key)] == git_key:
                continue
            name = entry.parts[-1]
            folded = name.casefold() if CASE_INSENSITIVE else name
            path = self.rel(entry.parts)
            in_claude = any((part.casefold() if CASE_INSENSITIVE else part) == ".claude" for part in entry.parts[:-1])
            if folded == ("claude.md" if CASE_INSENSITIVE else "CLAUDE.md"):
                self.add("claude-code", "CLAUDE.md, which Claude Code loads as instructions", path=path)
                imports_from.append(entry.parts)
            elif folded == ("claude.local.md" if CASE_INSENSITIVE else "CLAUDE.local.md"):
                self.add("claude-code", "CLAUDE.local.md, which Claude Code loads as instructions", path=path)
                imports_from.append(entry.parts)
            elif folded == ("agents.md" if CASE_INSENSITIVE else "AGENTS.md"):
                self.add("claude-code", "AGENTS.md, which agents load as instructions", path=path)
            elif folded == ".mcp.json" and len(entry.parts) == 1:
                self.add("claude-code", ".mcp.json, which configures MCP servers Claude Code can start", path=path)
                self.mcp_servers(entry.parts)
            elif folded == ".claude":
                self.add("claude-code", "a .claude directory: settings, hooks, commands, agents and skills",
                         path=path, kind=None if entry.kind == "dir" else entry.kind)
            elif in_claude:
                self.add("claude-code", "a file in a .claude directory", path=path,
                         kind=None if entry.kind == "file" else entry.kind)
                if folded in ("settings.json", "settings.local.json"):
                    self.settings_hooks(entry.parts)
        for parts in imports_from:
            self.imports(parts, 0, set())

    def load_json(self, parts, purpose):
        data = self.read_file(parts, purpose)
        if data is None:
            return None
        try:
            return json.loads(data.decode("utf-8-sig"))
        except (UnicodeDecodeError, ValueError) as error:
            self.missing(f"{purpose} could not be parsed: {error}", path=self.rel(parts))
            return None

    def settings_hooks(self, parts):
        settings = self.load_json(parts, "Claude Code settings")
        if not isinstance(settings, dict):
            return
        hooks = settings.get("hooks")
        if isinstance(hooks, dict):
            for event, groups in hooks.items():
                for group in groups if isinstance(groups, list) else []:
                    for hook in (group.get("hooks") if isinstance(group, dict) else None) or []:
                        if isinstance(hook, dict):
                            self.add("claude-code", "a Claude Code hook command, which runs on its event, also when a "
                                     "session starts in this directory", key=f"hooks.{event}",
                                     value=hook.get("command"), origin=self.rel(parts))
        for name in ("mcpServers", "apiKeyHelper", "statusLine"):
            if name in settings:
                self.add("claude-code", "a Claude Code setting that can start a program", key=name,
                         value=json.dumps(settings[name], ensure_ascii=False)[:500], origin=self.rel(parts))

    def mcp_servers(self, parts):
        servers = self.load_json(parts, ".mcp.json")
        if not isinstance(servers, dict) or not isinstance(servers.get("mcpServers"), dict):
            return
        for name, server in servers["mcpServers"].items():
            if isinstance(server, dict):
                command = " ".join(str(part) for part in [server.get("command"), *(server.get("args") or [])]
                                   if part is not None)
                self.add("claude-code", "an MCP server Claude Code can start", key=f"mcpServers.{name}",
                         value=command or server.get("url"), origin=self.rel(parts))

    def imports(self, parts, depth, seen):
        if self.key(parts) in seen:
            return
        seen.add(self.key(parts))
        data = self.read_file(parts, "an instruction file")
        if data is None:
            return
        origin = self.rel(parts)
        base = self.absolute(parts[:-1])
        fenced = False
        for line in data.decode("utf-8", "replace").splitlines():
            if _FENCE.match(line):
                fenced = not fenced
                continue
            if fenced:
                continue
            for value in _IMPORT.findall(_INLINE_CODE.sub("", line)):
                value = value.rstrip(".,;:!?")
                if not value:
                    continue
                location = self.locate(value, base)
                self.add("claude-code", "an @ import, which Claude Code loads into the instructions; listed by its "
                         "text", value=value, origin=origin,
                         location=location.get("location"), inside_path=location.get("inside_path"),
                         crosses_link=location.get("crosses_link"))
                target = location.get("inside_path")
                if location.get("location") != "inside" or "crosses_link" in location or target in (None, "."):
                    continue
                target_parts = tuple(target.split("/"))
                entry = self.lookup(target_parts)
                if entry is None or entry.kind != "file":
                    continue
                if depth + 1 < IMPORT_DEPTH:
                    self.imports(entry.parts, depth + 1, seen)

    # The whole run

    def run(self):
        self.ancestors()
        self.find_git()
        outer = self.repository_above(self.root, include_self=False)
        self.walk()
        own = self.lookup((".git",)) is not None or self.bare_top()
        if outer:
            self.add("git-layout", "an outer repository lies above the checked directory", path=outer)
            if not own:
                self.missing("the checked directory has no Git directory of its own, so Git commands run in it use the "
                             "outer repository's configuration, hooks and attributes, which this report does not "
                             "cover", path=outer)
        plain = self.analyse_layout()
        self.other_git_directories()
        git = self.lookup((".git",))
        if git is not None and git.kind == "dir":
            self.hooks(git.parts + ("hooks",))
        self.hooks_path()
        self.info_attributes()
        if plain and self.git_path:
            self.repository()
        self.working_tree()
        self.claude_files()

    def ancestors(self):
        """Report a link in the checked directory's own path; such a link does not fail any check."""
        current = self.root
        while True:
            try:
                info = fs("lstat", native(current))
            except OSError:
                info = None
            if info is not None and classify(info) in LINK_KINDS:
                target = None
                try:
                    target = fs("readlink", native(current))
                except (OSError, ValueError):
                    pass
                which = "the checked directory itself" if current == self.root else "a directory above the checked one"
                self.add("environment", f"{which} is reached through {KIND_TEXT[classify(info)]}", path=current,
                         target=target)
            parent = os.path.dirname(current)
            if parent == current:
                break
            current = parent

    def report(self):
        return {
            "tool": "repo-check",
            "format": REPORT_FORMAT,
            "checked_directory": self.root,
            "complete": not any(finding["category"] == "not-examined" for finding in self.findings),
            "git": {"path": self.git_path, "version": self.git_version_text},
            "findings": self.findings,
            "notes": list(NOTES),
        }


class OwnershipRefused(Exception):
    pass


def emit(report) -> None:
    text = json.dumps(report, ensure_ascii=False, indent=1)
    sys.stdout.buffer.write(text.encode("utf-8", "backslashreplace") + b"\n")
    sys.stdout.buffer.flush()


def main(argv) -> int:
    if sys.version_info < MIN_PYTHON:
        emit({"tool": "repo-check", "complete": False, "error": "Python 3.11 or later is required"})
        return 2
    if len(argv) != 1 or not argv[0] or not fully_qualified(argv[0]) or argv[0].startswith(("\\\\?\\", "\\\\.\\")):
        emit({"tool": "repo-check", "complete": False,
              "error": "usage: python -I -B repo_check.py <absolute directory>"})
        return 2
    root = os.path.normpath(argv[0])
    try:
        info = fs("lstat", native(root))
        listable = stat.S_ISDIR(info.st_mode) or classify(info) in ("junction", "symlink")
    except OSError as error:
        emit({"tool": "repo-check", "complete": False, "error": f"the directory cannot be examined: {error.strerror}"})
        return 2
    if not listable:
        emit({"tool": "repo-check", "complete": False, "error": "the path is not a directory"})
        return 2
    check = Check(root)
    try:
        check.run()
    except Exception as error:  # the report still says what it established, and that it stopped
        check.missing(f"the check stopped early on an unexpected error: {type(error).__name__}: {error}")
    emit(check.report())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
