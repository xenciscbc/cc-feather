"""The repository's checkouts as Git registers them, and the one lease location they all share.

Every checkout is found from the main worktree: the lease location is `.feather/leases/` under it whatever the
Working checkout's handoff tracking choice or explicit root, and nothing is ever stored anywhere else. A checkout is
keyed by Git's per-worktree administration identity (the name of its directory under `<common dir>/worktrees/`), and
the main worktree by MAIN_KEY, which Git never produces because it sanitizes a leading dot away."""
from dataclasses import dataclass
import os
from pathlib import Path
import subprocess

from feather_handoff.storage import (HandoffError, _StoreRefused, _git_directory, _main_worktree, _resolve_root,
                                     check_path, legal_name, register_root, run_git)

MAIN_KEY = ".main"


class LeaseError(HandoffError):
    """A failure reported as status error with its code."""


class Unknown(Exception):
    """A fact that could not be established; reported as unknown with the reason, never guessed."""


def same_path(first: str, second: str) -> bool:
    return os.path.normcase(os.path.normpath(first)) == os.path.normcase(os.path.normpath(second))


@dataclass
class Checkout:
    path: str
    main: bool
    head: str | None
    branch: str | None
    detached: bool
    key: str | None
    key_reason: str | None = None
    # The Git worktree lock's reason as written ("" for a lock without one), or None when the worktree is unlocked.
    locked: str | None = None
    # Why Git marks the worktree prunable, or None; a lock hides this mark, so exists is checked as well.
    prunable: str | None = None
    exists: bool = True

    def view(self) -> dict:
        return {"path": self.path, "main": self.main, "key": self.key, "head": self.head, "branch": self.branch,
                "detached": self.detached, "directory_exists": self.exists, "prunable": self.prunable}


class Repository:
    """The repository of --project: its main worktree and the lease location under it.

    location_problem holds why the lease location cannot be used; reads of leases are then unknown and writes fail,
    and nothing falls back to another directory."""

    def __init__(self, project: str, exact_root: bool):
        root, trusted = _resolve_root(project, exact_root)
        if root["state"] == "non-git":
            raise LeaseError("not-git", f"{root['path']} is not in a Git repository; checkout leases need Git")
        if root["state"] == "uncertain":
            raise Unknown(f"Git root discovery failed: {root['reason']}")
        self.project = Path(root["path"])
        if trusted:
            register_root(self.project)
        try:
            common = Path(_git_directory(self.project, "rev-parse", "--path-format=absolute", "--git-common-dir"))
            self.main = _main_worktree(self.project, common)
        except _StoreRefused as refused:
            raise Unknown(f"The main worktree could not be established: {refused}") from None
        self.common = common
        register_root(self.main)
        self.directory = self.main / ".feather" / "leases"
        self.location_problem: str | None = None
        try:
            check_path(self.directory / ".gitignore")
            for part in (self.main / ".feather", self.directory):
                if part.exists() and not part.is_dir():
                    raise HandoffError("not-directory", f"Not a directory: {part}")
        except (OSError, HandoffError) as error:
            self.location_problem = f"The lease location {self.directory} cannot be used: {error}"

    def require_location(self) -> None:
        if self.location_problem is not None:
            raise LeaseError("location", f"{self.location_problem}. Nothing was written, here or elsewhere.")

    def _admin_keys(self) -> dict[str, str | None]:
        """Each linked worktree's path (as its administration directory's gitdir file names it) to its key; a path
        named by more than one directory maps to None."""
        keys: dict[str, str | None] = {}
        admin = self.common / "worktrees"
        try:
            entries = sorted(os.scandir(admin), key=lambda entry: entry.name)
        except FileNotFoundError:
            return keys
        for entry in entries:
            if not entry.is_dir(follow_symlinks=False):
                continue
            try:
                text = Path(entry.path, "gitdir").read_text(encoding="utf-8").strip()
            except (OSError, UnicodeError):
                continue
            if not os.path.isabs(text):
                text = os.path.join(entry.path, text)
            path = os.path.normcase(os.path.normpath(os.path.dirname(os.path.normpath(text))))
            keys[path] = None if path in keys else entry.name
        return keys

    def checkouts(self) -> list[Checkout]:
        """Every worktree `git worktree list` reports, the main worktree first; Unknown when the query fails."""
        try:
            listed = run_git(self.main, "worktree", "list", "--porcelain", "-z", errors="replace")
        except (OSError, subprocess.TimeoutExpired) as error:
            raise Unknown(f"git worktree list could not be run: {error}") from None
        if listed.returncode:
            raise Unknown("git worktree list failed: " + (listed.stderr.strip() or f"exit {listed.returncode}"))
        records, current = [], []
        for field in listed.stdout.split("\0"):
            if field:
                current.append(field)
            elif current:
                records.append(current)
                current = []
        if current or not records:
            raise Unknown("git worktree list --porcelain -z did not report complete worktree records")
        keys = self._admin_keys()
        result = []
        for index, record in enumerate(records):
            if not record[0].startswith("worktree "):
                raise Unknown("a git worktree list record does not start with a worktree path")
            path = record[0][len("worktree "):]
            values = dict(item.split(" ", 1) if " " in item else (item, "") for item in record[1:])
            branch = values.get("branch")
            if branch is not None and branch.startswith("refs/heads/"):
                branch = branch[len("refs/heads/"):]
            checkout = Checkout(path=path, main=index == 0, head=values.get("HEAD"), branch=branch,
                                detached="detached" in values, key=None, locked=values.get("locked"),
                                prunable=values.get("prunable"), exists=os.path.isdir(path))
            if index == 0:
                if not same_path(path, str(self.main)):
                    raise Unknown(f"git worktree list names {path} first, not the main worktree {self.main}")
                checkout.key = MAIN_KEY
            else:
                key = keys.get(os.path.normcase(os.path.normpath(path)))
                try:
                    if key is None or key.startswith("."):
                        raise HandoffError("key", "no single administration directory names it")
                    legal_name(f"{key}.json")
                    checkout.key = key
                except HandoffError as error:
                    checkout.key_reason = f"The checkout's administration identity is unknown: {error}"
            result.append(checkout)
        return result

    def current(self, checkout: Checkout) -> Checkout:
        """The same checkout as Git registers it now, with its lock as it is now; Unknown when it is gone."""
        for fresh in self.checkouts():
            if fresh.key is not None and fresh.key == checkout.key:
                return fresh
        raise Unknown(f"Git no longer registers the checkout {checkout.path} under the key {checkout.key}")

    def find(self, path: str) -> Checkout:
        """The registered checkout whose top-level directory is path."""
        target = os.path.abspath(path)
        for checkout in self.checkouts():
            try:
                if os.path.samefile(target, checkout.path):
                    return checkout
            except OSError:
                # A worktree whose directory is missing is still named by its registered path.
                if not checkout.exists and same_path(target, checkout.path):
                    return checkout
        raise LeaseError("not-a-checkout", f"{target} is not the top-level directory of a checkout that Git registers "
                         "for this repository")
