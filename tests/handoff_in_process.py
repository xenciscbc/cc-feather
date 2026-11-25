"""Call the handoff tool's entry point in the test process instead of starting it (test support, no tests).

Each call gives `feather_handoff.cli.main()` the argument list a subprocess gets, its first item the tool's
path, a standard input whose `buffer` holds the bytes the subprocess would read, and a standard output
captured as UTF-8 bytes and decoded as the matching subprocess helper decodes it. The exit code `main()`
returns is compared with `expected` as that helper compares the process's return code. The root registry is
reset before and after each call, so every call starts, as a fresh tool process would, with no registered root.
An exception `main()` does not handle propagates and fails the test, as a crashed process fails the
return-code assertion. Only the observable contract is used: input bytes, JSON output and exit code.
"""
import io
import json
from pathlib import Path
import sys
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/handoff/scripts"
TOOL = SCRIPTS / "handoff.py"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from feather_handoff import cli, storage  # noqa: E402


def call(project, args, data: bytes) -> tuple[int, bytes, str]:
    """Run the tool once with `data` on standard input; return its exit code, output bytes and error text."""
    stdin = io.TextIOWrapper(io.BytesIO(data), encoding="utf-8")
    stdout = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
    stderr = io.StringIO()
    storage.reset_roots()
    try:
        with mock.patch.object(sys, "argv", [str(TOOL), "--project", str(project), *args]), \
                mock.patch.object(sys, "stdin", stdin), mock.patch.object(sys, "stdout", stdout), \
                mock.patch.object(sys, "stderr", stderr):
            code = cli.main()
        stdout.flush()
        return code, stdout.buffer.getvalue(), stderr.getvalue()
    finally:
        storage.reset_roots()


def run_local(test, *args, payload=None, raw=None, expected=0) -> dict:
    """In-process `LocalFixesBase.run_tool`: `raw` as given, otherwise the payload's UTF-8 JSON (`null` for none)."""
    data = raw if raw is not None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    code, output, errors = call(test.project, args, data)
    stdout = output.decode("utf-8")
    test.assertEqual(code, expected, stdout + errors)
    return json.loads(stdout)


def run_tool(test, *args, payload=None, expected=0) -> dict:
    """In-process `HandoffToolTest.run_tool`: the payload's JSON, or empty input when there is none."""
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else b""
    code, output, errors = call(test.project, args, data)
    # The subprocess helper reads its output as UTF-8 text with universal newlines.
    stdout = io.TextIOWrapper(io.BytesIO(output), encoding="utf-8").read()
    test.assertEqual(code, expected, stdout + errors)
    return json.loads(stdout)
