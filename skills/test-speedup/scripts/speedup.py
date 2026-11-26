"""Feather's Speed-up record command (Python 3.11+, standard library only).

It keeps the Speed-up record of /cc-feather:test-speedup. It never runs a test, never reads a file beyond hashing it
or reading a version from it, and never parses a report, a spec or a handoff record. It imports the handoff skill's
helpers, which the plugin ships beside this skill as skills/handoff/scripts/feather_handoff, for Git top-level and
main-worktree discovery and for the file operations they offer; the handoff tool itself is never changed.

PROTOCOL

Invocation: `python -B speedup.py --project DIR <command> [options]`, with --project accepted before or after the
command. DIR is any directory of the project. Commands marked (stdin) read one UTF-8 JSON object from standard input;
a duplicate JSON key in it is an input error. Every command prints one JSON object on standard output. A handled
result exits 0 with its `status`, `ok` or `changed`; status `error` exits 2, a usage error included, and carries
`code` and `message`. Once the location is known every result also carries `location` (the record's directory),
`project` (the Working checkout's top level, or the project directory outside Git) and `main_worktree` (null outside
Git).

Location. In a non-bare Git repository the record lives under the main worktree's `.feather/test-speedup/`, whichever
checkout --project names; outside Git, under the project directory's `.feather/test-speedup/`. A bare repository
(code `bare-repository`), Git discovery that fails (code `location`), a main worktree that cannot be established (code
`main-worktree`), a location that is not a directory or crosses a link (code `location`) and a directory that cannot
be created or written (code `location-unwritable`) are errors, and nothing is written anywhere else. There is no
tracked mode and no option to choose another root. The directory holds its own `.gitignore` containing `*`, written
before anything else; the project's `.gitignore` is never edited. Reading commands create nothing.

Store. The store is `record.json` (the record) plus the files `measurements/<name>.json` beside it, one per
measurement, never changed once written. Paths in the store and in input are relative to the Working checkout's top
level, written with `/`; `\\` in input is read as `/`, and absolute paths, `..` and paths that leave the top level
through a link are input errors. Dates are ISO 8601 with a time zone; a date in input is optional where it is listed
and defaults to now.

Schema version and store version. `schema_version` (the integer 1) is the format of `record.json` and of each
measurement file. The store version is a token for the whole store, the record and its list of measurement files:
`absent` when neither `record.json` nor any measurement file exists (the absent-record version token), otherwise the
SHA-256 hex of the canonical JSON `{"measurements": [sorted file names], "record": <SHA-256 hex of record.json's bytes,
or null>}`. Every command returns `version`. Every writing command (record-run, classify, decide, measure, and prune
with --version) takes `--version V`, the version it read, and when the store's version is no longer V it writes
nothing and returns `{"status": "changed", "version": <current>}`; the caller then reads again, merges its own update
and writes again. A measurement added or removed changes the version. There is no lock: two writes at the same instant
can both pass the check and the later one wins, a residual risk accepted because two sessions rarely run
test-speedup at once and the worst outcome is an extra analysis or a decision asked again.

Hashes. A file's content hash is the SHA-256 hex of its bytes. A shared set is the list of shared files main names for
one test file (shared fixtures, setup files, test runner configuration, test scripts within the scope); its hash is
the SHA-256 hex of the canonical JSON list of `[path, content hash or null when missing]` pairs sorted by path, so a
shared file that changed, was added to the set, was removed from it or went missing changes the hash.

Items. A Speed-up item has a `section`: `speed-up`, `removal`, `test-resource-risk` or
`run-configuration-resource-risk`; a `file`; and exactly one of `tests` (a non-empty list of test ids) or `setting` (a
non-empty string). Its canonical key is the compact JSON text (no spaces, non-ASCII kept) of
`[section, file, "tests", [test ids]]`, the test ids deduplicated and sorted by code point, or of
`[section, file, "setting", setting]`. Its state is `undecided`, `picked`, `declined`, `landed` or `obsolete`; each
change of state appends the state it left to `history` as `{state, date, reason}`. Two items of one record-run input
that share a key are an input error with code `duplicate-key` naming the keys, and nothing is written; main merges
them and submits again.

Item input (record-run `items`): `{"section", "file", "tests" | "setting", "location", "description",
"expected_gain", "correctness", "risk"}`; `description` is a non-empty string, the other text fields strings or null.

Version source input (`versions`): `{"name": "<runner or plugin>", "source": "<path>" | null, "line": "go" |
"toolchain"}`, `line` only for go.mod (default `go`). A relative source is read from the Working checkout's top level;
an absolute one as given. The version is read from a `package.json`'s `version`, a `.dist-info` directory's or a
`METADATA`/`PKG-INFO` file's `Version:` header, go.mod's `go` or `toolchain` line, `.python-version`'s first line, or
`pyvenv.cfg`'s `version` or `version_info` key. Output: `{"name", "source", "version", "state": "read" | "unknown",
"reason"}` (reason only when unknown). A version read from go.mod, .python-version or pyvenv.cfg is the one the project
declares; the toolchain actually used can differ.

Commands.

read
  -> {"status": "ok", "present": bool, "record": {...} | null, "measurements": [names], "version"}.
  The record: {"schema_version": 1, "files": {path: {"content_hash", "shared_set_hash", "shared": {path: hash |
  null}, "commit", "analysed"}}, "items": {key: item}, "runs": [{"date", "scope", "commit", "full", "versions"}]}.
  An item: {"key", "section", "file", "tests" | "setting", "location", "description", "expected_gain", "correctness",
  "risk", "state", "state_date", "state_reason", "decision": {"date", "reason", "content_hash"} | null, "landed":
  {"date", "evidence"} | null, "obsolete": {"date", "evidence"} | null, "first_seen", "last_seen_commit",
  "history": [...]}. A file's commit is shown only, never used to detect change.

changes (stdin) {"scope": [paths], "files": [{"path", "shared": [paths]}], "versions": [sources]}
  Read-only. A scope entry `.` is the whole top level; otherwise a path covers itself and what lies below it. Every
  listed file must exist. -> {"status": "ok", "version", "present", "last_run": {"date", "commit"} | null,
  "files": [{"path", "state": "new" | "changed" | "unchanged" | "deleted", "content_hash", "recorded_content_hash",
  "shared_set_hash", "recorded_shared_set_hash", "shared_set_changed": bool | null, "shared_changes": [{"path",
  "change": "added" | "removed" | "changed"}]}], "versions": {"now": [...], "last_run": [...] | null, "changed":
  [{"name", "last_run", "now"}]}}. A recorded file is `deleted` only when it is inside the scope, not listed and
  missing on disk. `shared_set_changed` is null for a new or deleted file. The recorded hashes are those of the file's
  last analysis, so a shared-set change stays reported for a test file until a run analyses it again.

record-run --version V (stdin) {"scope": [paths], "commit": str | null, "full": bool, "date"?, "files": [{"path",
"shared": [paths]}], "deleted": [paths], "items": [item input], "versions": [sources]}
  Updates the listed files' entries only (hashes taken now); removes each deleted file's entry (it must be recorded,
  inside the scope and missing) and marks its items obsolete with the deletion as evidence; matches each found item to
  a recorded one by key: a new key is added undecided, a matched undecided, picked or declined item keeps its state, a
  matched landed or obsolete item is reopened as undecided with its earlier state kept in history; appends the run.
  -> {"status": "ok", "version", "found": [{"key", "outcome": "new" | "matched" | "reopened", "state",
  "decision_content_hash", "content_hash", "decided_file_changed": bool | null}], "obsoleted": [keys],
  "not_found": [{"file", "items": [{"key", "state", "section", "location", "description"}]}]}. not_found lists, for
  each analysed file, its recorded undecided, picked or declined items not found again; a run-configuration item is
  also listed when its file is inside the scope. decided_file_changed compares a declined or picked item's decision
  hash with its file's content now. The script infers no other state: main classifies not_found items with classify.

classify --version V (stdin) {"items": [{"key", "state": "landed" | "obsolete" | "unchanged", "evidence", "date"?}]}
  landed and obsolete need a non-empty evidence and record {date, evidence}; unchanged changes nothing. An unknown key
  is an input error (code `unknown-item`) and nothing is written. -> {"status": "ok", "version", "items": [{"key",
  "state"}]}.

decide --version V (stdin) {"items": [{"key", "state": "picked" | "declined", "reason", "date"?}]}
  Sets each item's state with the decision's date, reason and its file's content hash now (null when missing), as
  main passes them from the user's answer. -> {"status": "ok", "version", "items": [{"key", "state", "decision"}]}.

measure --version V (stdin) {"commit": str | null, "date"?, "key": {"command", "selected", "concurrency", "override",
"runner", "left_out"}, "succeeded": bool, "total_seconds": number, "tests": {test id: seconds}}
  Stores the measurement as a new file. The comparison key's values are any JSON (lists ought to be sorted by the
  caller); date and commit are not part of it. Two measurements are comparable only when their keys are equal and both
  succeeded. -> {"status": "ok", "version", "measurement": name, "comparison": {"available": false, "reason"} |
  {"available": true, "against": {"measurement", "date", "commit"}, "total": {"before", "after", "seconds",
  "factor"}, "rose": [...], "fell": [...], "only_before": [ids], "only_after": [ids]}, "landed": [...]}. rose and fell
  are the ten tests whose time rose most and fell most, each {"test", "before", "after", "seconds", "factor"}, ties
  broken by test id; factor is after/before, null for a zero earlier time. landed holds, for each landed item that
  names tests, {"key", "landed", "before", "after"}, each side {"state": "available", "measurement", "date", "times":
  {id: seconds | null}} or {"state": "unavailable"}: the last comparable measurement (same key as this one) dated
  before the landing date and the first dated at or after it.

show [items [STATE] | runs]
  Read-only. Without a form: {"status": "ok", "present", "version", "last_analysis": {"date", "commit"} | null,
  "items_by_state": {state: n}, "last_measurement": {"measurement", "date", "key", "total_seconds", "succeeded"} |
  null, "files_changed": n (recorded files whose content changed or went missing since analysed), "forms": [...]}.
  `items [STATE]` adds "items" (all, or of one state); `runs` adds "runs" and "measurements" (each with name, date,
  commit, key, succeeded, total_seconds). With no record and no measurement: {"present": false, "message", "forms"}.

prune [--measurements-before DATE] [--keep-measurements N] [--obsolete] [--landed-before DATE] [--version V]
  A selection is the union of the options given (at least one): measurements dated before DATE, all but the last N
  measurements by date, obsolete items, and landed items whose landing date is before DATE. Undecided, picked and
  declined items are never selected. A DATE without a time zone is local time. Without --version it is a dry run:
  {"status": "ok", "dry_run": true, "version", "remove": {"items": [keys], "measurements": [names]}}. With --version
  it removes exactly that selection: {"status": "ok", "dry_run": false, "version", "removed": {...}}; a removal that
  fails part-way returns status error, code `partial`, with `removed` and `not_removed`. There is no reset of the whole
  record.

Error codes: usage, input, duplicate-key, unknown-item, record (an unreadable record or measurement), bare-repository,
location, main-worktree, location-unwritable, partial, io, internal, python-version. The record is trusted like other
`.feather/` records; no check against forgery is made."""
import json
import os
import sys

sys.dont_write_bytecode = True

if sys.version_info < (3, 11):
    print(json.dumps({"status": "error", "code": "python-version",
                      "message": "Python 3.11+ required. Ask whether to help install it."}))
    sys.exit(2)

_SKILLS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(1, os.path.join(_SKILLS, "handoff", "scripts"))

from feather_speedup.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
