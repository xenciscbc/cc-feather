"""JSON output around the Speed-up record's commands; the protocol is in the launcher, scripts/speedup.py.

Every handled result prints one JSON object and exits 0: ok and changed are answers, not failures. Status error
(usage, input, a location that cannot be used or written, an unreadable record, an internal failure) exits 2."""
import argparse
import json
import sys

from feather_handoff.cli import Parser, input_payload
from feather_handoff.storage import HandoffError, creation_denied

from .commands import COMMANDS, STDIN, WRITING
from .location import Location, SpeedupError
from .store import VERSION, Changed, Store


def parser() -> Parser:
    root_options = Parser(add_help=False)
    root_options.add_argument("--project", default=argparse.SUPPRESS,
                              help="Any directory of the project, in any checkout (required)")
    result = Parser(description="Feather Speed-up record (Python 3.11+)", parents=[root_options])
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("read", parents=[root_options], help="The record and the store's version")
    commands.add_parser("changes", parents=[root_options], help="The scope's files against the record (JSON stdin)")
    for name, text in (("record-run", "Record an analysis run (JSON stdin)"),
                       ("classify", "Classify items not found again (JSON stdin)"),
                       ("decide", "Record the user's decisions (JSON stdin)"),
                       ("measure", "Store a measurement and compare it (JSON stdin)")):
        command = commands.add_parser(name, parents=[root_options], help=text)
        command.add_argument("--version", required=True, help="The store version the caller read")
    show = commands.add_parser("show", parents=[root_options], help="Read-only summary, items [STATE] or runs")
    show.add_argument("form", nargs="*", help="Nothing, `items [STATE]` or `runs`")
    prune = commands.add_parser("prune", parents=[root_options],
                                help="Remove a selection; a dry run without --version")
    prune.add_argument("--measurements-before", metavar="DATE")
    prune.add_argument("--keep-measurements", metavar="N", type=int)
    prune.add_argument("--obsolete", action="store_true")
    prune.add_argument("--landed-before", metavar="DATE")
    prune.add_argument("--version", help="The version the dry run returned; removes exactly its selection")
    return result


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    location = None
    try:
        args = parser().parse_args()
        if not hasattr(args, "project"):
            raise HandoffError("usage", "the following arguments are required: --project")
        version = getattr(args, "version", None)
        if version is not None and VERSION.fullmatch(version) is None:
            raise HandoffError("usage", "--version must be the store version a read returned")
        payload = None
        if args.command in STDIN:
            payload = input_payload()
            if not isinstance(payload, dict):
                raise SpeedupError("input", "Input must be one JSON object")
        location = Location(args.project)
        store = Store(location)
        state = store.require(version) if args.command in WRITING else store.load()
        result = COMMANDS[args.command](store, state, args, payload)
    except Changed:
        result = {"status": "changed", "version": Store(location).load().version,
                  "message": "The store changed since that version was read. Nothing was written; read it again, "
                             "merge and write again."}
    except (OSError, UnicodeError, ValueError) as error:
        code = "location-unwritable" if creation_denied(error) else getattr(error, "code", "io")
        result = {"status": "error", "code": code, "message": str(error)}
        if code == "location-unwritable":
            result["message"] = (f"The record location {location.directory} is not writable: {error}. Nothing was "
                                 "written, here or elsewhere.")
    except Exception as error:
        result = {"status": "error", "code": "internal", "message": f"{type(error).__name__}: {error}"}
    if location is not None:
        result.update(location.view())
    print(json.dumps(result, ensure_ascii=False))
    return 2 if result["status"] == "error" else 0
