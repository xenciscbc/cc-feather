"""The work a checkout holds, as the listing reports it next to its lease: facts only, never a judgement of use.

Each part is known with its facts or unknown with the reason, never guessed: the uncommitted and untracked changes,
the commits relative to the default branch, and the handoff records that name the checkout. Handoff records are read
only through the handoff tool's own `list` output, always starting from the main worktree, and the handoff tool is
never changed."""
import json
import os
from pathlib import Path
import subprocess
import sys

from feather_handoff.storage import HandoffError, lazy_fetch_guard, run_git

from .checkouts import Checkout, Repository, same_path

HANDOFF_TOOL = Path(__file__).resolve().parents[3] / "handoff" / "scripts" / "handoff.py"
HANDOFF_TIMEOUT = 60
# At most this many uncommitted and this many untracked paths are listed per checkout; the counts are always whole.
PATH_LIMIT = 100
REMOTE = "refs/remotes/origin/"
# Characters that continue a path name; any other character after a checkout's path ends it.
PATH_CHARACTERS = frozenset("-_.~+@#$%&!'^`")


def unknown(reason: str) -> dict:
    return {"state": "unknown", "reason": reason}


def object_guard(repository: Repository) -> bool | str:
    """What lazy_fetch_guard returned for the Git commands below that read objects, or why none may run."""
    try:
        return lazy_fetch_guard(repository.main)
    except (HandoffError, OSError, subprocess.TimeoutExpired) as error:
        return f"Git commands that read objects were not run: {error}"


def _git(repository: Repository, guard: bool, *arguments: str, directory: Path | None = None) -> str:
    """One Git command's output; Unknown-style failures are raised as OSError with the reason."""
    try:
        result = run_git(directory or repository.main, *arguments, errors="replace", no_lazy_fetch=guard)
    except subprocess.TimeoutExpired as error:
        raise OSError(f"git {arguments[0]} timed out: {error}") from None
    if result.returncode:
        raise OSError(f"git {' '.join(arguments[:2])} failed: " + (result.stderr.strip() or f"exit {result.returncode}"))
    return result.stdout


def _commit(repository: Repository, guard: bool, ref: str) -> str | None:
    """The commit ref names, or None when no such ref exists."""
    result = run_git(repository.main, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}", errors="replace",
                     no_lazy_fetch=guard)
    if result.returncode == 1:
        return None
    if result.returncode:
        raise OSError(f"git rev-parse {ref} failed: " + (result.stderr.strip() or f"exit {result.returncode}"))
    return result.stdout.strip()


def default_branch(repository: Repository, guard: bool | str) -> dict:
    """The branch `origin/HEAD` names; without it the one of main and master that exists when exactly one does."""
    if isinstance(guard, str):
        return unknown(guard)
    try:
        symbolic = run_git(repository.main, "symbolic-ref", "--quiet", REMOTE + "HEAD", errors="replace")
        if symbolic.returncode == 0:
            target = symbolic.stdout.strip()
            name = target[len(REMOTE):] if target.startswith(REMOTE) else ""
            if not name:
                return unknown(f"origin/HEAD names {target!r}, which is not a branch of origin")
            local = _commit(repository, guard, f"refs/heads/{name}")
            remote = _commit(repository, guard, target)
            if local is None and remote is None:
                return unknown(f"origin/HEAD names {name}, which exists neither as a local branch nor as {target}")
            return {"state": "known", "name": name, "source": "origin/HEAD",
                    "local": None if local is None else f"refs/heads/{name}", "remote": None if remote is None
                    else target}
        if symbolic.returncode != 1:
            return unknown("git symbolic-ref origin/HEAD failed: "
                           + (symbolic.stderr.strip() or f"exit {symbolic.returncode}"))
        if _commit(repository, guard, REMOTE + "HEAD") is not None:
            return unknown("origin/HEAD exists but is not a symbolic ref, so it names no default branch")
        found = [name for name in ("main", "master") if _commit(repository, guard, f"refs/heads/{name}") is not None]
    except (OSError, subprocess.TimeoutExpired) as error:
        return unknown(f"The default branch could not be established: {error}")
    if len(found) != 1:
        which = "both main and master exist" if found else "neither main nor master exists"
        return unknown(f"origin/HEAD does not exist and {which}, so the default branch cannot be determined")
    return {"state": "known", "name": found[0], "source": "main-or-master", "local": f"refs/heads/{found[0]}",
            "remote": None}


def commits(repository: Repository, checkout: Checkout, base: dict, guard: bool | str) -> dict:
    """The checkout's HEAD against the local default branch when it exists, otherwise the remote one."""
    if base["state"] != "known":
        return unknown(f"The default branch is unknown: {base['reason']}")
    if isinstance(guard, str):
        return unknown(guard)
    head = checkout.head
    if not head or not head.strip("0"):
        return unknown("The checkout's HEAD names no commit")
    ref, kind = (base["local"], "local") if base["local"] else (base["remote"], "remote")
    try:
        counted = _git(repository, guard, "rev-list", "--left-right", "--count", f"{ref}...{head}", "--").split()
        behind, ahead = int(counted[0]), int(counted[1])
    except (OSError, ValueError, IndexError) as error:
        return unknown(f"The commits relative to {ref} could not be counted: {error}")
    return {"state": "known", "compared_with": ref, "kind": kind, "ahead": ahead, "behind": behind}


def changes(repository: Repository, checkout: Checkout, guard: bool | str) -> dict:
    """The uncommitted and untracked changes, read with the checkout's own Git directory and work tree named so that
    no other repository is ever discovered in its place."""
    if not checkout.exists:
        return unknown(f"The checkout's directory {checkout.path} is missing")
    if checkout.prunable is not None:
        return unknown(f"Git marks the worktree prunable: {checkout.prunable}")
    if checkout.key is None:
        return unknown(checkout.key_reason or "The checkout's administration identity is unknown")
    if isinstance(guard, str):
        return unknown(guard)
    git_directory = repository.common if checkout.main else repository.common / "worktrees" / checkout.key
    try:
        output = _git(repository, guard, f"--git-dir={git_directory}", f"--work-tree={checkout.path}", "status",
                      "--porcelain=v1", "-z", "--untracked-files=all", directory=Path(checkout.path))
    except OSError as error:
        return unknown(f"The changes could not be read: {error}")
    uncommitted, untracked = [], []
    fields = output.split("\0")
    index = 0
    while index < len(fields):
        field = fields[index]
        index += 1
        if len(field) < 4:
            continue
        status, path = field[:2], field[3:]
        if status[0] in "RC":
            index += 1  # the rename's or copy's source path
        if status == "??":
            untracked.append(path)
        else:
            uncommitted.append({"status": status, "path": path})
    return {"state": "known", "uncommitted": uncommitted[:PATH_LIMIT], "untracked": untracked[:PATH_LIMIT],
            "uncommitted_count": len(uncommitted), "untracked_count": len(untracked),
            "truncated": len(uncommitted) > PATH_LIMIT or len(untracked) > PATH_LIMIT}


def _normalized(text: str) -> str:
    text = text.replace("\\", "/")
    return text.lower() if os.name == "nt" else text


def _path_character(character: str) -> bool:
    return character.isalnum() or character in PATH_CHARACTERS


def _contains(text: str, path: str) -> bool:
    """Whether text holds path whole: not inside a longer name before it, and followed by a separator, a character
    that is not part of a path name, or the end (a full stop ends it when the text or a space follows)."""
    start = 0
    while (found := text.find(path, start)) >= 0:
        start = found + 1
        end = found + len(path)
        if found and (_path_character(text[found - 1]) or text[found - 1] == "/"):
            continue
        after = text[end:end + 1]
        if (not after or after == "/" or not _path_character(after)
                or (after == "." and (end + 1 == len(text) or text[end + 1].isspace()))):
            return True
    return False


def named_checkout(environment: str, paths: list[str]) -> int | None:
    """The index of the checkout whose whole path the environment field contains, the longest one when several do,
    compared with separators unified and, on Windows, case-insensitively."""
    text = _normalized(environment)
    best, length = None, -1
    for index, path in enumerate(paths):
        target = _normalized(path).rstrip("/")
        if target and len(target) > length and _contains(text, target):
            best, length = index, len(target)
    return best


def _store_failure(result: object) -> str | None:
    """Why one store's own `list` result does not show that store read in full, or None."""
    if not isinstance(result, dict):
        return "the handoff tool's list result is not a JSON object"
    if result.get("status") == "error":
        return f"{result.get('code')}: {result.get('message')}"
    issues = result.get("issues")
    if not isinstance(issues, list) or not isinstance(result.get("items"), list):
        return "the handoff tool's list result has no items and issues"
    if issues:
        return "; ".join(f"{issue.get('work') or 'store'}: {issue.get('code')}: {issue.get('message')}"
                         for issue in issues if isinstance(issue, dict)) or "the store reported issues"
    return None


def _store(result: dict) -> str | None:
    root = result.get("root")
    store = root.get("store") if isinstance(root, dict) else None
    return os.path.join(store, ".feather", "handoffs") if isinstance(store, str) else None


def judge_records(checkouts: list[Checkout], main: dict, others: dict[str, dict]) -> list[dict]:
    """Each checkout's handoff part, in order, from the main worktree's `list` result and each other store's own
    explicit-root `list` result, keyed by the `checkout` its `other_stores` entry names.

    Whether a store was read is judged from that store's own result only, never from the main call's overall status
    or complete: the main worktree's store from its own issues and read failures, each other store from its own
    call. An uncertain root or an unreadable main store makes the part unknown everywhere; a failed enumeration of
    the other checkouts makes it unknown for every linked worktree; an unreadable store of X, or X's missing
    directory, only for X."""
    root = main.get("root") if isinstance(main, dict) else None
    everywhere = None
    if not isinstance(root, dict):
        everywhere = "The handoff tool's list result names no root: " + (_store_failure(main) or "no root")
    elif root.get("state") != "git":
        everywhere = f"The handoff tool's root is {root.get('state')}: {root.get('reason') or 'not a Git root'}"
    else:
        enumeration = main.get("other_stores_issues")
        if not isinstance(enumeration, list) or not isinstance(main.get("other_stores"), list):
            everywhere = "The handoff tool's list result does not report other stores"
        elif any(isinstance(issue, dict) and issue.get("code") == "project-root-uncertain" for issue in enumeration):
            everywhere = "The handoff tool's root is uncertain: " + "; ".join(
                str(issue.get("message")) for issue in enumeration if isinstance(issue, dict))
        else:
            failure = _store_failure(main)
            if failure is not None:
                everywhere = f"The main worktree's Handoff store could not be read: {failure}"
    if everywhere is not None:
        return [unknown(everywhere) for _ in checkouts]
    paths = [checkout.path for checkout in checkouts]
    reasons: dict[int, str] = {}
    read = [(_store(main), main["items"])]
    for entry in main["other_stores"]:
        if not isinstance(entry, dict):
            continue
        where = entry.get("listed") or entry.get("checkout")
        index = next((i for i, path in enumerate(paths) if isinstance(where, str) and same_path(path, where)), None)
        issues = entry.get("issues") if isinstance(entry.get("issues"), list) else []
        missing = [issue for issue in issues if isinstance(issue, dict) and issue.get("code") == "missing"]
        result = others.get(entry.get("checkout"))
        if missing:
            reason = str(missing[0].get("message"))
        elif result is None:
            reason = f"The Handoff store in {where} was not read"
        else:
            failure = _store_failure(result)
            reason = None if failure is None else f"The Handoff store in {where} could not be read: {failure}"
        if reason is None:
            read.append((_store(result), result["items"]))
        elif index is not None:
            reasons[index] = reason
    enumeration = main["other_stores_issues"]
    parts = []
    for index, checkout in enumerate(checkouts):
        if not checkout.main and enumeration:
            parts.append(unknown("The other checkouts could not all be enumerated, so this worktree's own store may "
                                 "not have been listed: " + "; ".join(str(issue.get("message")) for issue in
                                                                     enumeration if isinstance(issue, dict))))
        elif not checkout.exists:
            parts.append(unknown(f"The checkout's directory {checkout.path} is missing"))
        elif index in reasons:
            parts.append(unknown(reasons[index]))
        else:
            parts.append({"state": "known", "records": []})
    for store, items in read:
        for item in items:
            if not isinstance(item, dict) or not isinstance(item.get("environment"), str):
                continue
            index = named_checkout(item["environment"], paths)
            if index is not None and parts[index]["state"] == "known":
                parts[index]["records"].append({key: item.get(key) for key in
                                                ("work", "title", "status", "record_status", "updated")}
                                               | {"store": store})
    return parts


def handoff_list(project: str, exact: bool) -> dict:
    """The handoff tool's own `list` result for project, or an error result saying why it was not obtained."""
    command = [sys.executable, "-B", str(HANDOFF_TOOL), "--project", project, *(["--exact-root"] if exact else []),
               "list"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace",
                                timeout=HANDOFF_TIMEOUT, stdin=subprocess.DEVNULL,
                                env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"status": "error", "code": "handoff-tool", "message": f"The handoff tool could not be run: {error}"}
    try:
        value = json.loads(result.stdout)
    except ValueError:
        return {"status": "error", "code": "handoff-tool",
                "message": f"The handoff tool printed no JSON (exit {result.returncode}): {result.stderr.strip()}"}
    if not isinstance(value, dict):
        return {"status": "error", "code": "handoff-tool", "message": "The handoff tool printed no JSON object"}
    return value


def handoff_records(repository: Repository, checkouts: list[Checkout]) -> list[dict]:
    """Each checkout's handoff part: the main worktree's `list`, then each store it reports under other_stores
    through `list` with that checkout as explicit root."""
    main = handoff_list(str(repository.main), False)
    others = {}
    for entry in main.get("other_stores") or []:
        if not isinstance(entry, dict) or not isinstance(entry.get("checkout"), str):
            continue
        if any(isinstance(issue, dict) and issue.get("code") == "missing" for issue in entry.get("issues") or []):
            continue
        others[entry["checkout"]] = handoff_list(entry["checkout"], True)
    return judge_records(checkouts, main, others)
