"""repo-check: report what in a directory could run code or redirect reads, without running any of it.

Usage: python -I -B repo_check.py <absolute directory>

Prints one UTF-8 JSON report on standard output and writes nothing anywhere. The report has `complete`, the Git
version and path used, and a list of findings, each with a category, a path or configuration key, its origin where
known and a one-line description. Every entry the tool could not examine, every Git directory, common directory or
worktree it could not read, every ref storage it does not read, every configuration read that failed and every output
it could not parse is a finding of the category `not-examined`, and `complete` is true only when there is none. The
report lists only the items on the fixed checklist below, for the directory as it is now; it never states that the
directory can be trusted.

How it reads the directory:

- Git runs on nothing in the checked directory. It runs only as `git --version` and as
  `git --no-pager config --file - --no-includes --list -z`, which reads configuration bytes the tool hands it on
  standard input, so Git opens no path the directory names and discovers no repository. Git is found by walking PATH
  in order, considering only fully qualified entries and skipping every entry inside the checked directory, which is
  reported; it is started by that absolute path, from its own directory, with a PATH of only the considered entries,
  the variables that select a repository removed and GIT_CEILING_DIRECTORIES set to its directory's parent. When the
  Git executable's own directory is itself a repository, no configuration read runs.
- The tool reads everything else itself, as data: the layout of every Git directory Git may select inside the checked
  directory (see `git_directories`), their configuration, hooks, `info/attributes`, the refs under `refs/replace/`
  and `packed-refs`, and the working tree's `.gitattributes` and `.gitmodules`. It reads no object, no index and no
  reftable.
- The tool walks the working tree itself with metadata that does not follow links, taking each entry's attributes
  from its parent directory's listing, and never descends into a link, junction, other reparse point or cloud
  placeholder. Every metadata read and file open goes through the single function `fs`, which tests observe.
- A path that repository content names (a gitfile, `commondir` or include target, a `CLAUDE.md` import) is opened
  only when its text, followed component by component without resolving links, lies inside the checked directory,
  crosses no link and the walk found every component of it to be a plain directory and the file a regular file with
  one link. Any other target is reported by its text only.
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
REPORT_FORMAT = 2
MIN_PYTHON = (3, 11)
OLD_GIT = (2, 32, 0)
READ_LIMIT = 4 * 1024 * 1024
PIECE = 64 * 1024
LINE_LIMIT = 64 * 1024
IMPORT_DEPTH = 5
GIT_TIMEOUT = 300

# The only Git command other than `git --version`: a configuration file read as data from standard input.
CONFIG_READ = ("--no-pager", "config", "--file", "-", "--no-includes", "--list", "-z")
# Removed from Git's environment, with every GIT_CONFIG* variable, so that nothing selects a repository for Git.
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
_MSYS_MAPPED = re.compile("[-]")
_RESERVED = re.compile(r"^(con|prn|aux|nul|com[0-9¹²³]|lpt[0-9¹²³])(\..*)?$", re.I)
# Characters some file systems ignore in names, so that such a name can still mean `.git`.
_IGNORED_IN_NAMES = re.compile("[‌-‏‪-‮⁪-⁯﻿]")
_IMPORT = re.compile(r"(?<![\w@`])@([^\s`\"'<>()\[\]]+)")
_FENCE = re.compile(r"^\s*(```|~~~)")
_INLINE_CODE = re.compile(r"`[^`\n]*`")
_HEAD_CONTENT = re.compile(r"^(ref:\s*refs/\S.*|[0-9a-f]{40}|[0-9a-f]{64})\s*$", re.S)
_PACKED_REPLACE = re.compile(rb"^([0-9a-f]{40,64}) (refs/replace/.+)$")

NOTES = (
    "The report covers the directory as it is now and only the items on the tool's fixed checklist; content that "
    "arrives later, by a pull, fetch, merge or checkout, is not checked unless the tool runs again.",
    "A finding says what could run code or redirect reads; an item that is not on the checklist is not reported, so "
    "a report without findings is not a statement about the directory.",
    "The index, objects and commits were not read, so attribute and module files, gitlinks and symbolic-link entries "
    "that exist only there are not reported.",
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
    (bytes, metadata of the open handle). pieces: the same open and checks without the size limit; returns (pieces,
    metadata), where pieces is a context manager that yields the file's bytes in pieces of PIECE bytes and closes the
    file when it exits."""
    if operation == "lstat":
        return os.lstat(path)
    if operation == "stat":
        return os.stat(path)
    if operation == "scandir":
        with os.scandir(path) as entries:
            return [(entry.name, entry.stat(follow_symlinks=False)) for entry in entries]
    if operation == "readlink":
        return os.readlink(path)
    if operation in ("read", "pieces"):
        flags = os.O_RDONLY
        for name in ("O_BINARY", "O_NOFOLLOW", "O_NONBLOCK", "O_NOCTTY"):
            flags |= getattr(os, name, 0)
        descriptor = os.open(path, flags)
        try:
            info = os.fstat(descriptor)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise OSError(0, "not a regular file with one link when opened")
            if operation == "read" and info.st_size > READ_LIMIT:
                raise OSError(0, f"larger than {READ_LIMIT} bytes")
        except BaseException:
            os.close(descriptor)
            raise
        if operation == "pieces":
            class Pieces:
                def __enter__(self):
                    return self

                def __exit__(self, *_details):
                    os.close(descriptor)

                def __iter__(self):
                    while True:
                        piece = os.read(descriptor, PIECE)
                        if not piece:
                            return
                        yield piece

            return Pieces(), info
        try:
            chunks = []
            remaining = READ_LIMIT + 1
            while remaining > 0:
                chunk = os.read(descriptor, min(PIECE, remaining))
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


def components(text: str):
    """The components of a path's text, split at the platform's separators, with empty ones dropped."""
    return [part for part in re.split(r"[\\/]" if WINDOWS else "/", text) if part]


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


KIND_TEXT = {"symlink": "a symbolic link", "junction": "a junction", "reparse": "a reparse point",
             "placeholder": "a cloud placeholder", "special": "not a regular file or directory", "dir": "a directory",
             "file": "a file", "unknown": "an entry that could not be examined",
             "ambiguous": "one of several entries whose names the tool reads as the same"}


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
        ("extensions", "refstorage"): ("setting", "selects how Git stores refs"),
        ("attr", "tree"): ("setting", "makes Git read attributes from a tree it names"),
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


def clip(text, limit: int) -> dict:
    """The `value` field of a finding quoting text, cut to limit characters, with `truncated` set when it was cut."""
    if text is None:
        return {}
    return {"value": text[:limit], "truncated": True if len(text) > limit else None}


def parse_listing(text: str):
    """Entries of `git config --list -z` output: (key, value), value None for a key without '='."""
    entries = []
    for item in text.split("\0"):
        if not item:
            continue
        key, separator, value = item.partition("\n")
        if not re.fullmatch(r"[A-Za-z0-9-]+\.(?:[^\n]*\.)?[A-Za-z][A-Za-z0-9-]*", key):
            raise ValueError(f"unexpected configuration key {key[:80]!r}")
        entries.append((key, value if separator else None))
    return entries


class GitDirectory:
    """A Git directory the tool reads: its components below the checked directory, the label the report gives it,
    the directory relative paths in its configuration start from (the top of its working tree, or the Git directory
    itself for a layout without one), and whether a missing `config` or `hooks` is reported. base is None when that
    directory could not be established, and base_problem then says why. A `core.worktree` in the Git directory's own
    configuration replaces base when it is read (see `Check.working_tree_base`)."""
    __slots__ = ("parts", "label", "base", "report_absent", "fields", "base_problem")

    def __init__(self, parts, label, base, report_absent, fields=None, base_problem=None):
        self.parts = parts
        self.label = label
        self.base = base
        self.report_absent = report_absent
        self.fields = fields or {}
        self.base_problem = base_problem


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
        self.git_version_text = None
        self.environment = None
        self.config_blocked = None
        self.queue = []
        self.queued = set()
        self.object_links = 0
        self.rejected_git = False

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
        """The lookup key of a path below the checked directory: on a file system that ignores letter case, every
        component as `str.upper().casefold()`, a superset of the folding such file systems apply."""
        return tuple(part.upper().casefold() for part in parts) if CASE_INSENSITIVE else tuple(parts)

    def is_git_name(self, name: str) -> bool:
        return self.key((name,)) == self.key((".git",))

    def inside_git_name(self, parts) -> bool:
        """Whether a path lies inside a directory named `.git`, judged only from its components below the checked
        directory."""
        return any(self.is_git_name(part) for part in parts[:-1])

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

    def subtree(self, parts):
        """Every entry below parts that the walk listed, without passing through anything but directories."""
        found = []
        stack = [parts]
        while stack:
            for child in self.children(stack.pop()):
                found.append(child)
                if child.kind == "dir":
                    stack.append(child.parts)
        return sorted(found, key=lambda entry: entry.parts)

    def status(self, parts, final: str = "file"):
        """('ok', None), ('absent', why) or ('fail', why) for a path below the checked directory, from the walk's
        results. ok: every component is a plain directory and the last one a regular file with one link (or a
        directory when final is 'dir'), and on Windows no component has a name Windows reads differently. absent: a
        component does not exist, or one above the last is a regular file, so the path cannot exist. fail: anything
        else, such as a component that is a link, a special file, a name that collides with another or a directory
        the walk could not list; such a path is never read or handed to Git."""
        if self.key(()) in self.unlisted:
            return "fail", "the checked directory could not be listed"
        for index in range(1, len(parts) + 1):
            prefix = parts[:index]
            if self.key(prefix[:-1]) in self.unlisted:
                return "fail", f"{self.rel(prefix[:-1])} could not be listed"
            entry = self.lookup(prefix)
            if entry is None:
                return "absent", f"{self.rel(prefix)} does not exist"
            shown = self.rel(entry.parts)
            if WINDOWS and unusual_name(entry.parts[-1]):
                return "fail", f"{shown} {unusual_name(entry.parts[-1])}"
            if index < len(parts):
                if entry.kind == "file":
                    return "absent", f"{shown} is a file"
                if entry.kind != "dir":
                    return "fail", f"{shown} is {KIND_TEXT.get(entry.kind, entry.kind)}"
                continue
            if entry.kind != final:
                return "fail", f"{shown} is {KIND_TEXT.get(entry.kind, entry.kind)}"
            if final == "file":
                if entry.nlink is None:
                    return "fail", f"{shown} could not be examined"
                if entry.nlink != 1:
                    return "fail", f"{shown} has {entry.nlink} links"
        return "ok", None

    def real_parts(self, parts):
        entry = self.lookup(parts)
        return entry.parts if entry else tuple(parts)

    def read_bytes(self, parts, purpose: str):
        """('ok', bytes), ('absent', None) or ('fail', None) for a file below the checked directory; a failure is
        listed as not examined."""
        state, why = self.status(parts)
        if state == "absent":
            return "absent", None
        if state == "fail":
            self.missing(f"{purpose} was not read: {why}", path=self.rel(self.real_parts(parts)))
            return "fail", None
        entry = self.lookup(parts)
        try:
            data, info = fs("read", native(self.absolute(entry.parts)))
        except OSError as error:
            self.missing(f"{purpose} could not be read: {error.strerror or error}", path=self.rel(entry.parts))
            return "fail", None
        if entry.identity and entry.identity[0] and (info.st_ino, info.st_dev) != entry.identity:
            self.missing(f"{purpose} changed while it was read", path=self.rel(entry.parts))
            return "fail", None
        return "ok", data

    def locate(self, value: str, base_parts, home: bool = False) -> dict:
        """Where a path value points, judged from its text without resolving links: inside the checked directory
        (with the components it names), outside it, a UNC path, or a form that cannot be placed. The text is followed
        component by component from the checked directory or from base_parts, so that a component that is a link is
        found on the text as written; a `..` after such a component cannot be placed from the text and leaves the
        location unresolved. home: a value starting with `~` or `%(prefix)`, which Git expands, lies outside."""
        text = value
        if home and (text.startswith("~") or text.startswith("%(prefix)")):
            return {"location": "outside"}
        if not text or "\0" in text or "\n" in text:
            return {"location": "unresolved"}
        if WINDOWS:
            text = text.replace("/", "\\")
        if is_unc(text):
            return {"location": "unc"}
        if fully_qualified(text):
            written = components(text)
            root = components(self.root)
            anchor = (lambda part: part.upper().casefold()) if CASE_INSENSITIVE or WINDOWS else (lambda part: part)
            written = [part for part in written if part != "."]
            if len(written) < len(root) or any(anchor(a) != anchor(b) for a, b in zip(written, root)):
                return {"location": "outside"}
            start, rest = [], written[len(root):]
        elif WINDOWS and (re.match(r"^[A-Za-z]:", text) or text.startswith("\\")):
            return {"location": "unresolved"}
        else:
            start, rest = list(base_parts), components(text)
        current = start
        crossed = None
        for part in rest:
            if part == ".":
                continue
            if part == "..":
                if crossed is not None:
                    return {"location": "unresolved", "crosses_link": crossed}
                if not current:
                    return {"location": "outside"}
                current.pop()
                continue
            if WINDOWS and unusual_name(part):
                return {"location": "unresolved"}
            current.append(part)
            if crossed is None:
                entry = self.lookup(tuple(current))
                if entry is not None and entry.kind in LINK_KINDS:
                    crossed = self.rel(entry.parts)
        result = {"location": "inside", "inside_path": self.rel(tuple(current))}
        if crossed is not None:
            result["crosses_link"] = crossed
        return result

    @staticmethod
    def location_problem(location: dict):
        """Why a located target may not be opened, or None."""
        if location.get("crosses_link") is not None:
            return f"it crosses the link {location['crosses_link']}"
        return {"inside": None, "outside": "it lies outside the checked directory", "unc": "it is a UNC path",
                "unresolved": "its text cannot be placed without resolving it"}[location["location"]]

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
        environment["LC_ALL"] = "C"
        environment["LANGUAGE"] = "C"
        self.environment = environment
        if executable is None:
            self.missing("no Git was found in the fully qualified PATH entries outside the checked directory, so no "
                         "configuration file was read")
            return
        self.git_path = executable
        self.git_directory = os.path.dirname(executable)
        environment["GIT_CEILING_DIRECTORIES"] = os.path.dirname(self.git_directory) or self.git_directory
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
            self.missing("the Git version could not be read, so whether it is older than 2.32 is not known",
                         **clip(text, 200))
        elif tuple(int(part or 0) for part in match.groups()) < OLD_GIT:
            self.add("git-layout", "Git is older than 2.32, which lacks protections later versions apply to "
                     "repositories", value=text)
        if self.git_directory_is_repository(self.git_directory):
            self.config_blocked = "the Git executable's directory is itself a repository, whose configuration Git " \
                                  "would apply to a configuration read"
            self.missing("no configuration file was read: the Git executable's directory is itself a repository, the "
                         "one Git would find under the ceiling the tool sets", path=self.git_directory)
            return
        above = self.repository_above(self.git_directory)
        if above:
            self.add("environment", "a repository lies above the Git executable's directory; the ceiling the tool sets "
                     "keeps Git from finding it, so this is information only", path=above)

    def git_directory_is_repository(self, directory: str) -> bool:
        """Whether the Git executable's directory is a repository Git could find there: it holds a `.git` entry, or,
        looked up by exact name, a `HEAD` that is not a directory together with `objects` and `refs` entries of any
        kind or a `commondir`. An unrelated `HEAD` alone (such as a program of that name) does not count."""
        def exists(name):
            try:
                return fs("lstat", native(os.path.join(directory, name)))
            except OSError:
                return None

        if exists(".git") is not None:
            return True
        head = exists("HEAD")
        if head is None or classify(head) == "dir":
            return False
        return (exists("objects") is not None and exists("refs") is not None) or exists("commondir") is not None

    def repository_above(self, directory: str):
        """The first directory above directory that holds a `.git` entry or a `HEAD` entry that is not a directory,
        found with the tool's own metadata reads; None when there is none."""
        current = os.path.normpath(directory)
        while True:
            parent = os.path.dirname(current)
            if parent == current:
                return None
            current = parent
            try:
                fs("lstat", native(os.path.join(current, ".git")))
                return current
            except OSError:
                pass
            try:
                if classify(fs("lstat", native(os.path.join(current, "HEAD")))) != "dir":
                    return current
            except OSError:
                pass

    def config_entries(self, data: bytes, purpose: str, path: str):
        """The (key, value) entries of configuration bytes, read by Git from standard input without following
        includes; None after a not-examined finding."""
        if self.git_path is None:
            self.missing(f"{purpose} was not read: no Git to read it with", path=path)
            return None
        if self.config_blocked:
            self.missing(f"{purpose} was not read: {self.config_blocked}", path=path)
            return None
        try:
            result = subprocess.run([self.git_path, *CONFIG_READ], executable=self.git_path, cwd=self.git_directory,
                                    env=self.environment, input=data, capture_output=True, timeout=GIT_TIMEOUT)
        except (OSError, subprocess.SubprocessError) as error:
            self.missing(f"{purpose} was not read: Git could not run: {error}", path=path)
            return None
        stderr = result.stderr.decode("utf-8", "replace").strip()
        if result.returncode or stderr:
            self.missing(f"{purpose} could not be read by Git (exit {result.returncode})", path=path,
                         **clip(stderr or None, 500))
            return None
        try:
            return parse_listing(result.stdout.decode("utf-8", "surrogateescape"))
        except ValueError as error:
            self.missing(f"{purpose} could not be parsed: {error}", path=path)
            return None

    def read_config(self, parts, purpose: str):
        """'absent', None after a not-examined finding, or the entries of a configuration file below the checked
        directory. The file is found by its normalised name, so that `.git/Config` on a file system that folds case
        is read as `.git/config`, the file Git reads."""
        state, data = self.read_bytes(parts, purpose)
        if state != "ok":
            return "absent" if state == "absent" else None
        return self.config_entries(data, purpose, self.rel(self.real_parts(parts)))

    @staticmethod
    def parts_of(inside_path: str):
        return tuple(inside_path.split("/")) if inside_path != "." else ()

    @staticmethod
    def relative(value: str) -> bool:
        """Whether a path value's text is placed from a base directory: not a `~` or `%(prefix)` value, a UNC path,
        a fully qualified path or, on Windows, a drive-relative or rooted one."""
        text = value.replace("/", "\\") if WINDOWS else value
        if text.startswith(("~", "%(prefix)")) or is_unc(text) or fully_qualified(text):
            return False
        return not (WINDOWS and (re.match(r"^[A-Za-z]:", text) or text.startswith("\\")))

    def working_tree_base(self, directory: GitDirectory, files):
        """Git places relative path values in a Git directory's configuration from the top of the working tree that
        runs them, which a `core.worktree` in that configuration names relative to the Git directory. When the
        configuration files (not their includes, see `report_config`) set `core.worktree`, it replaces the Git
        directory's base when its text lies inside the checked directory, crosses no link and names a directory the
        walk found; otherwise the base is not established."""
        values = [value for _parts, entries in files for key, value in entries
                  if split_key(key) == ("core", None, "worktree")]
        if not values:
            return
        if len(set(values)) > 1:
            problem = "core.worktree is set more than once with different values"
        elif not values[0]:
            problem = "core.worktree is empty"
        else:
            location = self.locate(values[0], directory.parts)
            problem = self.location_problem(location)
            if problem is None:
                parts = self.parts_of(location["inside_path"])
                state, why = self.status(parts, "dir")
                if state == "ok":
                    directory.base, directory.base_problem = parts, None
                    return
                problem = why
            problem = f"the directory core.worktree names: {problem}"
        directory.base, directory.base_problem = None, problem

    def report_config(self, parts, entries, directory: GitDirectory, seen=None, included=False):
        """Findings for the listed keys of one configuration file of a Git directory, and its includes read as data
        when they lie inside the checked directory and pass the walk's checks. A relative path value is placed from
        the Git directory's base; when that base is not established, the value is unresolved and not examined."""
        seen = set() if seen is None else seen
        seen.add(self.key(parts))
        real = self.real_parts(parts)
        origin = self.rel(real)
        for key, value in entries:
            listed = listed_key(key, value)
            if not listed:
                continue
            kind, description = listed
            section, subsection, name = split_key(key)
            fields = {"key": key, "value": value, "origin": origin}
            location = None
            unplaced = None
            if kind in ("path", "include") and value:
                if kind == "include":
                    base = real[:-1]
                elif name == "worktree":
                    base = directory.parts
                else:
                    base = directory.base
                if base is None and self.relative(value):
                    location = {"location": "unresolved"}
                    unplaced = ("it is relative to the working tree, and the working tree could not be established: "
                                f"{directory.base_problem}")
                else:
                    location = self.locate(value, base or (), home=True)
                fields.update(location)
            self.add("configuration", description, **fields)
            if included and (section, subsection, name) == ("core", None, "worktree"):
                self.missing("core.worktree is set in an included file, so the relative paths in this Git directory's "
                             "configuration may have been placed from another working tree than the one Git uses",
                             value=value, origin=origin)
            if kind == "include":
                if value:
                    self.follow_include(value, location, origin, directory, seen)
            elif subsection is not None or not value:
                continue
            elif (section, name) == ("core", "worktree") and self.location_problem(location):
                self.missing(f"the working tree this configuration names was not examined: "
                             f"{self.location_problem(location)}", value=value, origin=origin)
            elif (section, name) == ("core", "hookspath"):
                # Git runs the hooks in this directory, so one the tool cannot list leaves the report incomplete.
                problem = unplaced or self.location_problem(location)
                if problem:
                    self.missing(f"the hooks directory core.hooksPath names was not examined: {problem}",
                                 value=value, origin=origin)
                else:
                    self.hooks_path(location["inside_path"], origin)
            elif unplaced:
                self.missing(f"the file {key} names was not placed: {unplaced}", value=value, origin=origin)
            elif (section, name) == ("extensions", "refstorage") and value.strip().lower() != "files":
                self.missing(f"the refs of {self.rel(directory.parts)} were not examined: its ref storage is not "
                             "files", value=value, origin=origin)

    def follow_include(self, value, location, origin, directory, seen):
        problem = self.location_problem(location)
        if problem:
            self.missing(f"include target not read: {problem}; its text is listed only", value=value, origin=origin)
            return
        target = location["inside_path"]
        parts = tuple(target.split("/")) if target != "." else ()
        if self.key(parts) in seen:
            return
        entries = self.read_config(parts, "an include target")
        if entries == "absent":
            self.missing("include target not read: it does not exist", value=value, origin=origin)
        elif entries is not None:
            self.report_config(parts, entries, directory, seen, included=True)

    def hooks_path(self, target: str, origin: str):
        parts = self.parts_of(target)
        self.add("hooks", "core.hooksPath names a directory inside the checked directory, so its content chooses the "
                 "hooks Git runs", path=target, origin=origin)
        state, why = self.status(parts, "dir")
        if state == "fail":
            self.missing(f"the hooks directory core.hooksPath names was not listed: {why}", path=target,
                         origin=origin)
        elif state == "ok":
            self.list_hooks(parts, origin)

    def list_hooks(self, parts, origin=None):
        for entry in sorted(self.children(parts), key=lambda entry: entry.parts):
            if entry.parts[-1].endswith(".sample"):
                continue
            self.add("hooks", "a hook Git can run", path=self.rel(entry.parts), origin=origin,
                     kind=None if entry.kind == "file" else entry.kind)

    # Git directories

    def enqueue(self, directory: GitDirectory):
        key = self.key(directory.parts)
        if key in self.queued:
            return
        self.queued.add(key)
        self.queue.append(directory)

    def target(self, location: dict, value: str, what: str, origin: str, label: str, base, base_problem=None):
        """Queue the Git directory a gitfile or `commondir` names when it may be read, or list it as not
        examined."""
        problem = self.location_problem(location)
        if problem:
            self.missing(f"{what} was not examined: {problem}", value=value, origin=origin)
            return
        self.enqueue(GitDirectory(self.parts_of(location["inside_path"]), label, base, True,
                                  base_problem=base_problem))

    def gitfile(self, parts):
        """A `.git` file: Git reads the Git directory's path from it."""
        state, data = self.read_bytes(parts, "a gitfile")
        if state != "ok":
            return
        text = data.decode("utf-8", "surrogateescape")
        if not text.startswith("gitdir: "):
            self.add("git-layout", "a .git file that does not name a Git directory, which Git refuses",
                     path=self.rel(parts), **clip(text, 500))
            return
        value = text[len("gitdir: "):].rstrip("\r\n")
        location = self.locate(value, parts[:-1])
        self.add("git-layout", "a gitfile, which points Git at another Git directory", path=self.rel(parts),
                 value=value, **location)
        self.target(location, value, "the Git directory the gitfile names", self.rel(parts),
                    "the Git directory a gitfile names", parts[:-1])

    def git_directories(self):
        """Queue every Git directory Git may select inside the checked directory: a top `.git` directory, a gitfile's
        target, and any directory, the top or one the walk found, that holds a `HEAD` entry of any kind other than a
        directory, whatever kind its `objects` and `refs` entries are. Directories inside a directory named `.git`
        are not counted this way (they are its own `logs`, `refs`, `modules` and `worktrees`); submodule and linked
        worktree Git directories are found from the Git directory that holds them, and common directories from
        `commondir`. Then read each one."""
        head = self.lookup(("HEAD",))
        for key in sorted(self.entries):
            entry = self.entries[key]
            parts = entry.parts
            if self.inside_git_name(parts):
                continue
            if self.is_git_name(parts[-1]):
                base = parts[:-1]
                if entry.kind == "dir":
                    label = "the checked directory's .git" if len(parts) == 1 else "a nested repository's .git"
                    self.enqueue(GitDirectory(parts, label, base, True))
                elif entry.kind == "file":
                    self.gitfile(parts)
                else:
                    self.add("git-layout", f".git is {KIND_TEXT.get(entry.kind, entry.kind)}; it was not followed",
                             path=self.rel(parts), target=entry.target)
                    self.missing(f"the Git directory .git names was not examined: it is "
                                 f"{KIND_TEXT.get(entry.kind, entry.kind)}", path=self.rel(parts))
                continue
            if entry.kind == "dir":
                nested_head = self.lookup(parts + ("HEAD",))
                if nested_head is not None and nested_head.kind != "dir":
                    self.enqueue(GitDirectory(parts, "a nested directory holding a HEAD entry that is not a directory, "
                                              "which Git can use as a Git directory", parts, True))
        if self.lookup((".git",)) is None and (head is None or head.kind == "dir"):
            self.add("git-layout", "the checked directory has no Git directory of its own: no .git entry and no HEAD "
                     "entry at its top", path=".")
        if head is not None and head.kind != "dir":
            self.enqueue(GitDirectory((),"the checked directory itself is a bare repository layout: it holds a HEAD "
                                      "entry that is not a directory, so Git can use it as a Git directory", (), True,
                                      {"kind": None if head.kind == "file" else head.kind, "target": head.target}))
        while self.queue:
            self.read_git_directory(self.queue.pop(0))

    def read_git_directory(self, directory: GitDirectory):
        parts = directory.parts
        shown = self.rel(parts)
        state, why = self.status(parts, "dir")
        if state != "ok":
            self.missing(f"{directory.label} was not read: {why}", path=shown)
            return
        finding = self.add("git-layout", f"a Git directory Git may use: {directory.label}", path=shown,
                           **directory.fields)
        absent = []
        files = []
        for name in ("config", "config.worktree"):
            entries = self.read_config(parts + (name,), f"the configuration {self.rel(parts + (name,))}")
            if entries == "absent":
                if name == "config":
                    absent.append("config")
            elif entries is not None:
                files.append((parts + (name,), entries))
        self.working_tree_base(directory, files)
        for file_parts, entries in files:
            self.report_config(file_parts, entries, directory)
        hooks = parts + ("hooks",)
        state, why = self.status(hooks, "dir")
        if state == "absent":
            absent.append("hooks")
        elif state == "fail":
            self.missing(f"the hooks directory was not listed: {why}", path=self.rel(self.real_parts(hooks)))
        else:
            self.list_hooks(self.real_parts(hooks))
        if absent and directory.report_absent:
            finding["absent"] = absent
        self.head(directory)
        state, data = self.read_bytes(parts + ("info", "attributes"), "info/attributes")
        if state == "ok":
            self.report_attributes(data.decode("utf-8", "surrogateescape"),
                                   self.rel(self.real_parts(parts + ("info", "attributes"))))
        self.replace_refs(directory)
        self.packed_refs(directory)
        reftable = self.lookup(parts + ("reftable",))
        if reftable is not None:
            self.missing("the refs in reftable were not examined: the tool does not read reftable",
                         path=self.rel(reftable.parts))
        self.commondir(directory)
        self.alternates(directory)
        self.modules(directory)
        self.worktrees(directory)
        if self.is_git_name(parts[-1] if parts else ""):
            self.git_directory_entries(directory)

    def head(self, directory: GitDirectory):
        """The checked directory's own `.git/HEAD`: Git uses `.git` only when it accepts this HEAD, and otherwise
        looks for another Git directory, the top or one above."""
        if len(directory.parts) != 1 or not self.is_git_name(directory.parts[0]):
            return
        entry = self.lookup(directory.parts + ("HEAD",))
        problem = None
        if entry is None:
            problem = "is missing"
        elif entry.kind == "symlink":
            if not (entry.target or "").startswith("refs/"):
                problem = "is a symbolic link whose target does not start with refs/"
        elif entry.kind != "file":
            problem = f"is {KIND_TEXT.get(entry.kind, entry.kind)}"
        else:
            state, data = self.read_bytes(entry.parts, ".git/HEAD")
            if state == "ok" and not _HEAD_CONTENT.match(data.decode("utf-8", "replace")):
                problem = "holds content Git rejects"
        if problem:
            self.rejected_git = True
            self.add("git-layout", f"the Git directory's HEAD {problem}, so Git may not accept .git and may use "
                     "another Git directory, the top or one above", path=self.rel(directory.parts + ("HEAD",)))

    def replace_refs(self, directory: GitDirectory):
        replace = directory.parts + ("refs", "replace")
        state, why = self.status(replace, "dir")
        if state == "fail":
            self.missing(f"the replacement refs were not listed: {why}", path=self.rel(self.real_parts(replace)))
            return
        if state == "absent":
            return
        real = self.real_parts(replace)
        for entry in self.subtree(real):
            if entry.kind == "dir":
                continue
            name = "refs/replace/" + "/".join(entry.parts[len(real):])
            state, data = self.read_bytes(entry.parts, "a replacement ref")
            value = data.decode("utf-8", "surrogateescape").strip() if state == "ok" else None
            self.add("refs-and-submodules", "a replacement ref, which makes Git show another object in place of the "
                     "one named", key=name, **clip(value, 200), origin=self.rel(entry.parts))

    def packed_refs(self, directory: GitDirectory):
        """The replacement refs in `packed-refs`, read in pieces so that a large file is read whole."""
        parts = directory.parts + ("packed-refs",)
        state, why = self.status(parts)
        if state == "absent":
            return
        origin = self.rel(self.real_parts(parts))
        if state == "fail":
            self.missing(f"packed-refs was not read: {why}", path=origin)
            return
        entry = self.lookup(parts)
        try:
            pieces, info = fs("pieces", native(self.absolute(entry.parts)))
        except OSError as error:
            self.missing(f"packed-refs could not be read: {error.strerror or error}", path=origin)
            return
        if entry.identity and entry.identity[0] and (info.st_ino, info.st_dev) != entry.identity:
            with pieces:
                pass
            self.missing("packed-refs changed while it was read", path=origin)
            return
        pending = b""
        overlong = False
        found = []
        try:
            with pieces:
                for piece in pieces:
                    lines = (pending + piece).split(b"\n")
                    pending = lines.pop()
                    if len(pending) > LINE_LIMIT:
                        overlong, pending = True, b""
                    found.extend(match for match in map(_PACKED_REPLACE.match, lines) if match)
        except OSError as error:
            self.missing(f"packed-refs could not be read: {error.strerror or error}", path=origin)
            return
        if pending:
            match = _PACKED_REPLACE.match(pending.rstrip(b"\r"))
            if match:
                found.append(match)
        for match in found:
            self.add("refs-and-submodules", "a replacement ref, which makes Git show another object in place of the "
                     "one named", key=match.group(2).decode("utf-8", "surrogateescape").rstrip("\r"),
                     value=match.group(1).decode("ascii"), origin=origin)
        if overlong:
            self.missing(f"packed-refs holds a line longer than {LINE_LIMIT} bytes, which was not examined",
                         path=origin)

    def commondir(self, directory: GitDirectory):
        parts = directory.parts + ("commondir",)
        state, data = self.read_bytes(parts, "commondir")
        if state != "ok":
            return
        value = data.decode("utf-8", "surrogateescape").rstrip("\r\n")
        location = self.locate(value, directory.parts)
        origin = self.rel(self.real_parts(parts))
        self.add("git-layout", "commondir makes Git use another directory's objects, refs, configuration and hooks",
                 path=origin, value=value, **location)
        self.target(location, value, "the common directory commondir names", origin,
                    "the common directory a commondir file names", directory.base, directory.base_problem)

    def alternates(self, directory: GitDirectory):
        parts = directory.parts + ("objects", "info", "alternates")
        state, data = self.read_bytes(parts, "alternates")
        if state != "ok":
            return
        origin = self.rel(self.real_parts(parts))
        for line in data.decode("utf-8", "surrogateescape").splitlines():
            if line.strip() and not line.startswith("#"):
                self.add("git-layout", "alternates make Git read objects from another directory", path=origin,
                         value=line, **self.locate(line, directory.parts + ("objects",)))

    def modules(self, directory: GitDirectory):
        modules = directory.parts + ("modules",)
        state, why = self.status(modules, "dir")
        if state == "fail":
            self.missing(f"the submodule Git directories were not examined: {why}",
                         path=self.rel(self.real_parts(modules)))
        elif state == "ok":
            # A submodule's working tree is the directory its `core.worktree` names (see `working_tree_base`); one a
            # gitfile names was queued earlier with the gitfile's directory as its base.
            for parts in self.module_directories(self.real_parts(modules)):
                self.enqueue(GitDirectory(parts, "a submodule Git directory", None, True, base_problem=(
                    "no gitfile in the checked directory names this submodule Git directory and its configuration "
                    "sets no core.worktree")))

    def module_directories(self, parts):
        """The submodule Git directories below parts, at any depth, since a submodule's name can hold `/`: a
        directory holding a `HEAD` entry that is not a directory. A directory holding none of `HEAD`, `objects`,
        `refs`, `config` or `commondir` is one level of such a name and is searched further; one holding some of them
        but no such `HEAD`, and any entry that is not a directory, cannot be classified and is listed as not
        examined. A submodule's own `modules` is searched when its Git directory is read."""
        found = []
        for child in sorted(self.children(parts), key=lambda entry: entry.parts):
            if child.kind != "dir":
                self.missing(f"an entry under modules that is {KIND_TEXT.get(child.kind, child.kind)}, which the tool "
                             "does not follow, so the submodule Git directory it may stand for was not examined",
                             path=self.rel(child.parts), target=child.target)
                continue
            head = self.lookup(child.parts + ("HEAD",))
            if head is not None and head.kind != "dir":
                found.append(child.parts)
            elif any(self.lookup(child.parts + (name,)) is not None
                     for name in ("HEAD", "objects", "refs", "config", "commondir")):
                self.missing("a directory under modules that is not a Git directory (no HEAD entry that is not a "
                             "directory), so its configuration and hooks were not examined", path=self.rel(child.parts))
            else:
                found.extend(self.module_directories(child.parts))
        return found

    def worktrees(self, directory: GitDirectory):
        worktrees = directory.parts + ("worktrees",)
        state, why = self.status(worktrees, "dir")
        if state == "fail":
            self.missing(f"the linked worktrees were not examined: {why}", path=self.rel(self.real_parts(worktrees)))
            return
        if state == "absent":
            return
        for worktree in self.children(self.real_parts(worktrees)):
            shown = self.rel(worktree.parts)
            if worktree.kind != "dir":
                self.missing(f"an entry under worktrees that is {KIND_TEXT.get(worktree.kind, worktree.kind)} was not "
                             "examined", path=shown, target=worktree.target)
                continue
            gitdir_state, data = self.read_bytes(worktree.parts + ("gitdir",), "a linked worktree's gitdir")
            value = data.decode("utf-8", "surrogateescape").rstrip("\r\n") if gitdir_state == "ok" else None
            location = self.locate(value, worktree.parts) if value else {}
            self.add("git-layout", "a linked worktree", path=shown, value=value, **location)
            problem = self.location_problem(location) if value else (
                "it has no gitdir file" if gitdir_state == "absent" else "its gitdir file was not read or is empty")
            if value and problem:
                self.missing(f"the linked worktree's working tree was not examined: {problem}", path=shown,
                             value=value)
            # The working tree's top is the directory holding the `.git` entry the gitfile names.
            base = None
            if problem is None:
                top = self.parts_of(location["inside_path"])
                if top and self.is_git_name(top[-1]):
                    top = top[:-1]
                state, why = self.status(top, "dir")
                if state == "ok":
                    base = top
                else:
                    problem = why
            self.enqueue(GitDirectory(worktree.parts, "a linked worktree's Git directory", base, False,
                                      base_problem=None if base is not None else
                                      f"the working tree its gitdir file names: {problem}"))

    def git_directory_entries(self, directory: GitDirectory):
        """Links and special entries inside a directory named `.git`, and one summary of its files with more than one
        link, as a clone from a local path creates in `objects`."""
        for entry in self.subtree(directory.parts):
            if entry.kind in LINK_KINDS:
                self.add("git-layout", f"an entry of the Git directory is {KIND_TEXT[entry.kind]}; it was not "
                         "followed", path=self.rel(entry.parts), target=entry.target)
            elif entry.kind == "special":
                self.add("git-layout", "an entry of the Git directory is not a regular file or directory",
                         path=self.rel(entry.parts))

    # The working tree's attribute and module files

    def gitattributes(self):
        for key in sorted(self.entries):
            entry = self.entries[key]
            if self.key((entry.parts[-1],)) != self.key((".gitattributes",)) or self.inside_git_name(entry.parts):
                continue
            state, data = self.read_bytes(entry.parts, ".gitattributes")
            if state == "ok":
                self.report_attributes(data.decode("utf-8", "surrogateescape"), self.rel(entry.parts))

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

    def gitmodules(self):
        state, data = self.read_bytes((".gitmodules",), ".gitmodules")
        if state != "ok":
            return
        origin = self.rel(self.real_parts((".gitmodules",)))
        entries = self.config_entries(data, ".gitmodules", origin)
        if entries is None:
            return
        for key, value in entries:
            section, subsection, name = split_key(key)
            if section != "submodule" or subsection is None:
                continue
            if name in ("path", "url"):
                self.add("refs-and-submodules", f"a submodule's {name} in .gitmodules", key=key, value=value,
                         origin=origin)
            elif name == "update" and (value or "").lstrip().startswith("!"):
                self.add("refs-and-submodules", "a submodule update setting that runs a shell command", key=key,
                         value=value, origin=origin)

    # The working tree

    def working_tree(self):
        """Entries outside every directory named `.git`, whose own entries are reported when it is read as a Git
        directory (see `git_directory_entries`)."""
        for key in sorted(self.entries):
            entry = self.entries[key]
            if self.inside_git_name(entry.parts) or entry.parts == self.real_parts((".git",)):
                if entry.kind == "file" and entry.nlink and entry.nlink > 1:
                    self.object_links += 1
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
            if git_variant(name):
                self.add("working-tree", "a nested repository or a name Git can read as .git", path=path,
                         kind=entry.kind)
            elif entry.kind == "dir":
                head = self.lookup(entry.parts + ("HEAD",))
                if head is not None and head.kind != "dir":
                    self.add("working-tree", "a nested directory Git can use as a Git directory (it holds a HEAD "
                             "entry that is not a directory)", path=path)
        if self.object_links:
            self.add("git-layout", f"{self.object_links} files in Git directories have more than one link, as a clone "
                     "from a local path creates; they were only examined, never opened", path=".git")

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
        state, data = self.read_bytes(parts, purpose)
        if state != "ok":
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
                         **clip(json.dumps(settings[name], ensure_ascii=False), 500), origin=self.rel(parts))

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
        state, data = self.read_bytes(parts, "an instruction file")
        if state != "ok":
            return
        origin = self.rel(parts)
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
                location = self.locate(value, parts[:-1], home=True)
                self.add("claude-code", "an @ import, which Claude Code loads into the instructions; listed by its "
                         "text", value=value, origin=origin,
                         location=location.get("location"), inside_path=location.get("inside_path"),
                         crosses_link=location.get("crosses_link"))
                if self.location_problem(location) or location["inside_path"] == ".":
                    continue
                entry = self.lookup(tuple(location["inside_path"].split("/")))
                if entry is None or entry.kind != "file":
                    continue
                if depth + 1 < IMPORT_DEPTH:
                    self.imports(entry.parts, depth + 1, seen)

    # The whole run

    def run(self):
        self.ancestors()
        self.find_git()
        outer = self.repository_above(self.root)
        self.walk()
        self.git_directories()
        self.outer(outer)
        self.gitattributes()
        self.gitmodules()
        self.working_tree()
        self.claude_files()

    def outer(self, outer):
        """An outer repository above the checked directory. Git uses it for commands run in the checked directory when
        the directory has no Git directory of its own that Git accepts: no `.git` entry, or a `.git` directory whose
        HEAD Git rejects, and a top that is not a repository by the narrow test (a `HEAD` that is not a directory
        with `objects` and `refs`, or with a `commondir`)."""
        if not outer:
            return
        self.add("git-layout", "an outer repository lies above the checked directory", path=outer)
        git = self.lookup((".git",))
        head = self.lookup(("HEAD",))
        top = head is not None and head.kind != "dir" and (
            (self.lookup(("objects",)) is not None and self.lookup(("refs",)) is not None)
            or self.lookup(("commondir",)) is not None)
        own = top or (git is not None and not (git.kind == "dir" and self.rejected_git))
        if not own:
            self.missing("the checked directory has no Git directory of its own that Git surely accepts, so Git "
                         "commands run in it can use the outer repository's configuration, hooks and attributes, which "
                         "this report does not cover", path=outer)

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
