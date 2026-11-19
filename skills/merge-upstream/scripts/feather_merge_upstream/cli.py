"""The merge-upstream fact tool's command line: one JSON object on stdin, one JSON object on stdout.

Input (every key required unless marked optional, no other key accepted):
  remote          the remote's name, e.g. "origin"
  default_branch  the remote default branch's name, e.g. "main"
  remote_tip      full object name of the fetched remote tip that was merged
  tip_before      full object name of the work branch's tip before the merge
  merge_commit    full object name of the merge commit
  claims          a list of {"id": non-empty text, "base": full object name or null, "judged": [full object names],
                  "kind": optional non-empty text such as "fix" or "cancelled"}

A handled run prints status ok and exits 0, whatever the facts say; every part that could not be established is
{"state": "unknown", "reason": ...}. Invalid input or a project that cannot be used prints status error and exits 2,
having run no Git command that reads the repository's objects."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from feather_handoff.cli import Parser
from feather_handoff.storage import HandoffError, _resolve_root, check_path, register_root, run_git

from . import facts

OBJECT_NAME = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")
TOP_LEVEL = {"remote": str, "default_branch": str, "remote_tip": "sha", "tip_before": "sha", "merge_commit": "sha",
             "claims": list}
CLAIM_KEYS = {"id", "base", "judged", "kind"}


def object_name(value, where: str) -> str:
    if not isinstance(value, str) or OBJECT_NAME.fullmatch(value.lower()) is None:
        raise HandoffError("input", f"{where} must be a full object name (40 or 64 hexadecimal digits)")
    return value.lower()


def validate(raw: str) -> dict:
    try:
        request = json.loads(raw)
    except ValueError as error:
        raise HandoffError("input", f"stdin is not one JSON object: {error}") from None
    if not isinstance(request, dict):
        raise HandoffError("input", "stdin must hold one JSON object")
    missing = sorted(TOP_LEVEL.keys() - request.keys())
    extra = sorted(request.keys() - TOP_LEVEL.keys())
    if missing or extra:
        raise HandoffError("input", "the input object " + "; ".join(
            part for part in (f"lacks {', '.join(missing)}" if missing else "",
                              f"has unknown keys {', '.join(extra)}" if extra else "") if part))
    for key in ("remote", "default_branch"):
        if not isinstance(request[key], str) or not request[key].strip():
            raise HandoffError("input", f"{key} must be non-empty text")
    for key in ("remote_tip", "tip_before", "merge_commit"):
        request[key] = object_name(request[key], key)
    if not isinstance(request["claims"], list):
        raise HandoffError("input", "claims must be a list")
    seen = set()
    for index, item in enumerate(request["claims"]):
        where = f"claims[{index}]"
        if not isinstance(item, dict):
            raise HandoffError("input", f"{where} must be an object")
        if not {"id", "base", "judged"} <= item.keys() or not item.keys() <= CLAIM_KEYS:
            raise HandoffError("input", f"{where} must have id, base and judged, and optionally kind, and no other key")
        if not isinstance(item["id"], str) or not item["id"].strip():
            raise HandoffError("input", f"{where}.id must be non-empty text")
        if item["id"] in seen:
            raise HandoffError("input", f"{where}.id {item['id']!r} appears more than once")
        seen.add(item["id"])
        if "kind" in item and (not isinstance(item["kind"], str) or not item["kind"].strip()):
            raise HandoffError("input", f"{where}.kind must be non-empty text")
        if item["base"] is not None:
            item["base"] = object_name(item["base"], f"{where}.base")
        if not isinstance(item["judged"], list):
            raise HandoffError("input", f"{where}.judged must be a list")
        item["judged"] = [object_name(value, f"{where}.judged[{position}]")
                          for position, value in enumerate(item["judged"])]
    return request


def check_ref_names(root, request: dict) -> None:
    """The remote-tracking ref the input names must be a valid ref name; check-ref-format reads no object."""
    ref = f"refs/remotes/{request['remote']}/{request['default_branch']}"
    try:
        result = run_git(root, "check-ref-format", ref, errors="replace")
    except (OSError, subprocess.TimeoutExpired) as error:
        raise HandoffError("git-unavailable", f"Git could not be run: {error}") from None
    if result.returncode:
        raise HandoffError("input", f"remote and default_branch do not form a valid ref name: {ref}")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    # Every Git process inherits these through the handoff helper's environment: Git never prompts for credentials,
    # and no transport is allowed, so nothing the tool runs can reach a remote even if a command tried to.
    os.environ["GIT_TERMINAL_PROMPT"] = "0"
    os.environ["GIT_ALLOW_PROTOCOL"] = "none"
    parser = Parser(description="Feather merge-upstream facts (Python 3.11+); reads one JSON object on stdin")
    parser.add_argument("--project", required=True,
                        help="Any checkout of the repository, or a directory inside one")
    parser.add_argument("--exact-root", action="store_true",
                        help="Use --project as the confirmed root without Git top-level discovery")
    result = None
    try:
        args = parser.parse_args()
        request = validate(sys.stdin.buffer.read().decode("utf-8"))
        root, trusted = _resolve_root(args.project, args.exact_root)
        if root["state"] == "non-git":
            raise HandoffError("not-git", f"{root['path']} is not in a Git repository")
        if root["state"] == "uncertain":
            facts_found = facts.all_unknown(request, f"Git root discovery failed: {root['reason']}")
        else:
            project = Path(root["path"])
            if trusted:
                register_root(project)
            check_path(project)
            check_ref_names(project, request)
            facts_found = facts.report(project, request)
        result = {"status": "ok", "project": root["path"],
                  **{key: request[key] for key in ("remote", "default_branch", *facts.COMMITS)}, **facts_found}
    except (OSError, UnicodeError, ValueError) as error:
        result = {"status": "error", "code": getattr(error, "code", "input" if isinstance(error, UnicodeError)
                                                     else "io"), "message": str(error)}
    except Exception as error:
        result = {"status": "error", "code": "internal", "message": f"{type(error).__name__}: {error}"}
    print(json.dumps(result))
    return 2 if result["status"] == "error" else 0
