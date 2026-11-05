"""Respect existing Git tracking choices when recording handoffs."""
from pathlib import Path
import subprocess

from .storage import (HandoffError, Store, check_path, create_file, lazy_fetch_guard, read_file, replace_file,
                      run_git)


RULE = "/.feather/handoffs/"
# A Git comment: records an explicit track choice without unignoring anything.
MARKER = "# cc-feather: track /.feather/handoffs/"


def rule_line(line: str) -> str:
    """A .gitignore line as Git reads it: leading whitespace is part of the pattern, trailing spaces are not."""
    return line.rstrip("\r\n").rstrip(" ")


def detect_tracking(checkout: Path) -> str:
    """The tracking state of a Working checkout while its store is chosen: tracked when its own .gitignore holds the
    track marker or its index already tracks a file under .feather/handoffs/, otherwise untracked.

    Runs entirely in the Working checkout, after that checkout's own lazy-fetch guard, with paths relative to it; it
    never reads the marker of the checkout that holds the store. HandoffError (promisor-remote, promisor-unknown,
    unsafe-path, git), OSError, UnicodeError and subprocess.TimeoutExpired propagate: the state is then unknown."""
    lazy = lazy_fetch_guard(checkout)
    path = checkout / ".gitignore"
    check_path(path)
    try:
        content = read_file(path).data.decode("utf-8")
    except FileNotFoundError:
        content = ""
    if any(rule_line(line) == MARKER for line in content.splitlines()):
        return "tracked"
    listed = run_git(checkout, "ls-files", "--", ".feather/handoffs/", errors="replace", no_lazy_fetch=lazy)
    if listed.returncode:
        raise HandoffError("git", listed.stderr.strip() or f"git ls-files exited with {listed.returncode}")
    return "tracked" if listed.stdout.strip() else "untracked"


def require_track_choice(store: Store, choice: str) -> None:
    """Before a save or archive writes anything: a track choice is refused in a run that uses the shared store."""
    if choice == "track" and store.root["shared"]:
        raise HandoffError("input", "tracking is chosen from the checkout whose records it should track; this run "
                           f"keeps its records in the shared Handoff store under {store.store_checkout}, so choose "
                           "track from that checkout. Nothing was written")


def git(store: Store, *arguments: str, no_lazy_fetch: bool = False) -> subprocess.CompletedProcess:
    """A command applying the ignore rules, run in the checkout that holds the store with paths relative to it."""
    return run_git(store.store_checkout, *arguments, no_lazy_fetch=no_lazy_fetch)


def object_reads(store: Store) -> bool:
    """The promisor-remote check before the first command that can read objects and before any write to the rules.

    Runs in the same directory as git(), the checkout that holds the store, so the answer governs exactly the
    commands it guards. Returns whether those commands carry --no-lazy-fetch; raises promisor-remote or
    promisor-unknown when none may run, and git-unavailable when Git could not be run, like the first probe."""
    try:
        return lazy_fetch_guard(store.store_checkout)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise HandoffError("git-unavailable", f"Git could not be run or did not respond: {error}") from None


def ensure_tracking(store: Store, work: str, choice: str) -> str:
    """Apply the ignore rules for one work file in the checkout that holds the store: its .gitignore, and ls-files
    and check-ignore there after that checkout's lazy-fetch guard."""
    try:
        probe = git(store, "rev-parse", "--is-inside-work-tree")
    except (OSError, subprocess.TimeoutExpired) as error:
        # Without a Git answer the ignore rule cannot be applied; the save reports a partial tracking failure.
        raise HandoffError("git-unavailable", f"Git could not be run or did not respond: {error}") from None
    if probe.returncode and "not a git repository" not in probe.stderr.lower():
        raise HandoffError("git", probe.stderr.strip() or "Git tracking could not be checked")
    if probe.stdout.strip() != "true":
        return "non-git"
    relative = f".feather/handoffs/{work}"
    path = store.store_checkout / ".gitignore"
    check_path(path)
    original = read_file(path) if path.exists() else None
    content = original.data.decode("utf-8") if original else ""
    newline = "\r\n" if "\r\n" in content else "\n"
    marked = any(rule_line(line) == MARKER for line in content.splitlines())
    if choice == "default" and marked:
        # Reads no object and writes nothing, so it needs no promisor-remote check.
        return "existing-rule"
    lazy = object_reads(store)
    if choice == "track":
        changed = "".join(line for line in content.splitlines(keepends=True) if rule_line(line) != RULE)
        if not marked:
            changed += (newline if changed and not changed.endswith("\n") else "") + MARKER + newline
        if changed != content:
            if original:
                replace_file(original, changed.encode("utf-8"))
            else:
                create_file(path, changed.encode("utf-8"))
        ignored = git(store, "check-ignore", "-q", "--", relative, no_lazy_fetch=lazy)
        if ignored.returncode == 0:
            raise HandoffError("tracking-blocked", f"Work saved, but broader Git rules still ignore {relative}; user decision needed")
        if ignored.returncode not in {0, 1}:
            raise HandoffError("git", ignored.stderr.strip())
        return "track"
    tracked = git(store, "ls-files", "--", ".feather/handoffs/", no_lazy_fetch=lazy)
    if tracked.returncode:
        raise HandoffError("git", tracked.stderr.strip())
    if tracked.stdout.strip():
        return "existing-tracking"
    ignored = git(store, "check-ignore", "-v", "--", relative, no_lazy_fetch=lazy)
    if ignored.returncode not in {0, 1}:
        raise HandoffError("git", ignored.stderr.strip())
    if ignored.stdout.strip():
        # Verbose check-ignore also reports a matching explicit unignore rule.
        return "existing-rule"
    changed = content + (newline if content and not content.endswith("\n") else "") + RULE + newline
    if original:
        replace_file(original, changed.encode("utf-8"))
    else:
        create_file(path, changed.encode("utf-8"))
    return "ignored"
