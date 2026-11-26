"""Where the Speed-up record lives: the main worktree's `.feather/test-speedup/` in a non-bare Git repository,
whichever checkout asks, or the project directory's outside Git; never anywhere else."""
import os
from pathlib import Path
import subprocess

from feather_handoff.storage import (HandoffError, _StoreRefused, _git_directory, _main_worktree, _resolve_root,
                                     check_path, register_root, run_git)


class SpeedupError(HandoffError):
    """A failure reported as status error with its code."""


def _bare(path: str) -> bool:
    try:
        result = run_git(Path(path), "rev-parse", "--is-bare-repository", errors="replace")
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0 and result.stdout.strip() == "true"


class Location:
    """The project of --project: its top level (`top`), its main worktree (`main`, None outside Git) and the record's
    directory (`directory`)."""

    def __init__(self, project: str):
        root, trusted = _resolve_root(project, False)
        if root["state"] == "uncertain":
            if _bare(root["path"]):
                raise SpeedupError("bare-repository", f"{root['path']} is in a bare repository, which has no main "
                                   "worktree to hold the Speed-up record. Nothing was written.")
            raise SpeedupError("location", f"Git root discovery failed: {root.get('reason')}. Nothing was written.")
        self.top = Path(root["path"])
        if trusted:
            register_root(self.top)
        if root["state"] == "non-git":
            self.git = False
            self.main = None
            base = self.top
        else:
            self.git = True
            try:
                common = Path(_git_directory(self.top, "rev-parse", "--path-format=absolute", "--git-common-dir"))
                self.main = _main_worktree(self.top, common)
            except _StoreRefused as refused:
                raise SpeedupError("main-worktree", f"The main worktree could not be established: {refused}. "
                                   "Nothing was written.") from None
            register_root(self.main)
            base = self.main
        self.directory = base / ".feather" / "test-speedup"
        try:
            check_path(self.directory / "measurements" / "x.json")
            check_path(self.directory / "record.json")
            for part in (base / ".feather", self.directory, self.directory / "measurements"):
                if os.path.lexists(part) and not part.is_dir():
                    raise HandoffError("not-directory", f"Not a directory: {part}")
        except (OSError, HandoffError) as error:
            raise SpeedupError("location", f"The record location {self.directory} cannot be used: {error}. Nothing "
                               "was written, here or elsewhere.") from None

    def view(self) -> dict:
        return {"location": str(self.directory), "project": str(self.top),
                "main_worktree": None if self.main is None else str(self.main)}
