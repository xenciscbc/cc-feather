"""JSON output around the lease tool's commands: acquire, renew, release, take-over and list.

Every handled result prints one JSON object and exits 0: ok, held, locked, refused, changed, changed-hands, busy and
unknown are answers, not failures. Status error (usage, input, a location that cannot be used or written, an internal
failure) exits 2."""
import argparse
import json
import re
import sys

from feather_handoff.cli import Parser
from feather_handoff.storage import HandoffError, creation_denied

from .checkouts import Repository, Unknown
from . import locks, records

VERSION = re.compile(r"[0-9a-f]{64}")
OUTCOME = {"acquire": "acquired", "renew": "renewed", "release": "released", "take-over": "taken_over"}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    root_options = Parser(add_help=False)
    root_options.add_argument("--project", default=argparse.SUPPRESS,
                              help="Any checkout of the repository, or a directory inside one (required)")
    root_options.add_argument("--exact-root", action="store_true", default=argparse.SUPPRESS,
                              help="Use --project as the confirmed root without Git top-level discovery")
    parser = Parser(description="Feather checkout leases (Python 3.11+)", parents=[root_options])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", parents=[root_options], help="Every registered checkout with its lease state")
    acquire = commands.add_parser("acquire", parents=[root_options], help="Take the lease on one checkout")
    acquire.add_argument("--checkout", help="The checkout's top-level directory (default: the project's root)")
    acquire.add_argument("--session", required=True, help="A label naming the session that takes the lease")
    acquire.add_argument("--purpose", required=True, help="What the checkout is used for")
    acquire.add_argument("--runtime", default="claude-code", help="The agent runtime (default: claude-code)")
    acquire.add_argument("--accept-session-lock", metavar="REASON",
                         help="The Claude Code session lock reason (`claude session <name> (pid N)`) this session "
                              "observed right after it created the worktree; that exact lock is accepted in place of "
                              "the lease's own")
    renew = commands.add_parser("renew", parents=[root_options], help="Record activity on a lease the caller holds")
    renew.add_argument("--checkout", help="The checkout's top-level directory (default: the project's root)")
    renew.add_argument("--lease-id", required=True, help="The lease_id the caller's acquire or take-over returned")
    renew.add_argument("--purpose", help="The new purpose (default: unchanged)")
    take_over = commands.add_parser("take-over", parents=[root_options],
                                    help="Take over, on the user's choice, a lease the user judges left behind")
    take_over.add_argument("--checkout", help="The checkout's top-level directory (default: the project's root)")
    take_over.add_argument("--version", required=True,
                           help="The lease version the user was shown, as list or a refused acquire returned it")
    take_over.add_argument("--session", required=True, help="A label naming the session that takes the lease over")
    take_over.add_argument("--purpose", required=True, help="What the checkout is used for")
    take_over.add_argument("--runtime", default="claude-code", help="The agent runtime (default: claude-code)")
    release = commands.add_parser("release", parents=[root_options], help="Return a lease the caller holds")
    release.add_argument("--checkout", help="The checkout's top-level directory (default: the project's root)")
    release.add_argument("--lease-id", required=True, help="The lease_id the caller's acquire returned")
    args = repository = None
    try:
        args = parser.parse_args()
        if not hasattr(args, "project"):
            parser.error("the following arguments are required: --project")
        repository = Repository(args.project, getattr(args, "exact_root", False))
        if args.command == "list":
            result = records.listing(repository)
        else:
            checkout = repository.find(args.checkout or str(repository.project))
            if args.command == "acquire":
                if not args.session.strip() or not args.purpose.strip():
                    raise HandoffError("input", "--session and --purpose must not be empty")
                attested = args.accept_session_lock
                if attested is not None and not locks.is_session_lock(attested):
                    raise HandoffError("input", "--accept-session-lock must be a Claude Code session lock reason, "
                                       "`claude session <name> (pid N)`")
                result = records.acquire(repository, checkout, args.session, args.purpose, args.runtime, attested)
            elif args.command == "renew":
                if args.purpose is not None and not args.purpose.strip():
                    raise HandoffError("input", "--purpose must not be empty")
                result = records.renew(repository, checkout, args.lease_id, args.purpose)
            elif args.command == "take-over":
                if VERSION.fullmatch(args.version) is None:
                    raise HandoffError("input", "--version must be the lease version list or acquire returned")
                if not args.session.strip() or not args.purpose.strip():
                    raise HandoffError("input", "--session and --purpose must not be empty")
                result = records.take_over(repository, checkout, args.version, args.session, args.purpose,
                                           args.runtime)
            else:
                result = records.release(repository, checkout, args.lease_id)
    except Unknown as unknown:
        result = {"status": "unknown", "reason": str(unknown)}
        if getattr(args, "command", None) == "list":
            result.update(complete=False, checkouts=[])
        elif getattr(args, "command", None) in OUTCOME:
            result[OUTCOME[args.command]] = False
    except (OSError, UnicodeError, ValueError) as error:
        code = "location-unwritable" if creation_denied(error) else getattr(error, "code", "io")
        result = {"status": "error", "code": code, "message": str(error)}
        if code == "location-unwritable":
            result["message"] = (f"The lease location {repository.directory} is not writable: {error}. Nothing was "
                                 "written, here or elsewhere.")
    except Exception as error:
        result = {"status": "error", "code": "internal", "message": f"{type(error).__name__}: {error}"}
    if repository is not None and hasattr(repository, "directory"):
        result.update(location=str(repository.directory), main_worktree=str(repository.main),
                      project=str(repository.project))
    print(json.dumps(result, ensure_ascii=False))
    return 2 if result["status"] == "error" else 0
