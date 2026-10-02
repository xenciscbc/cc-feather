# Handoff compatibility and initial validation

The initial cc-feather runtime is copied byte-for-byte from the local codex-feather
checkout's `skills/feather-handoff/scripts/`. It does not require that checkout at
runtime. Eight upstream runtime test modules are included unchanged. The captured
file hashes are in [upstream-manifest.json](upstream-manifest.json). Git declined
source revision lookup because of checkout ownership; no trust settings were
changed. The hashes identify the actual imported bytes, not a claimed release.

The skill and references are adapted for Claude Code: plugin-relative launcher
resolution, Claude invocation, no feather-setup dependency, and completion based
on the whole requested work. Runtime code and record schemas are unchanged.
That initial 0.1.0 package had no delegation installer or model configuration. Version 0.2.0 adds them separately; see [setup validation](setup-validation.md). The handoff runtime remains unchanged.

## Preserved contract

- Active work: `.feather/handoffs/<work>.md`.
- Completed history: `.feather/handoffs/history.md`.
- Explicitly sealed history: `.feather/handoffs/archive/<batch>.md`.
- Existing Chinese field labels, status tokens, completion identities, complete
  record bodies, optional source baselines, and optimistic version checks.
- Read/list/history searches remain read-only. Resume is an agent workflow that
  inspects the record and current sources before continuing authorized work.
- Completion saves the final record and archives it. Partial failures retain
  recoverable data and stable retry identities.
- Cross-session writes still need an externally coordinated single writer.
- Claude memory lookup is an explicitly selected, read-only skill workflow,
  separate from the Feather Python commands.

## Checks performed on 2026-09-23

Working directory: this repository. Environment: Windows, Python 3.11.9,
Claude Code 2.1.280.

| Check | Result |
| --- | --- |
| Eight inherited runtime test modules | 73 tests: 72 passed, 1 skipped because Windows symlink creation was not permitted |
| Relocated skill in a directory containing spaces, with a Unicode project path | Passed; create/read/compare/update/complete/seal/clear worked, plugin and source files stayed unchanged |
| Alternating codex-feather and cc-feather CLIs on the same records | Passed; versions, full record content, baseline and history identities survived |
| Imported runtime and test source hashes | All 20 files byte-identical to the source checkout |
| `claude plugin validate . --json` | Marketplace valid, no warnings |
| `claude plugin validate .claude-plugin/plugin.json --json` | Plugin valid, no warnings |
| skill-creator `quick_validate.py` under Python UTF-8 mode | Passed |

Manifest validation is not installation or model behavior validation. No real
Claude skill session, automatic discovery, memory lookup, or Linux/macOS run was
performed. The symlink test remains unverified on this host. The additional
relocation and interoperability tests use subprocess CLI calls, not model sessions.

## Reproduce

Run the included suite without external dependencies:

```sh
python -B -m unittest discover -s tests -v
claude plugin validate . --json
claude plugin validate .claude-plugin/plugin.json --json
```

The optional cross-runtime test is skipped unless `CODEX_FEATHER_ROOT` points to
a codex-feather checkout. To run it on PowerShell:

```powershell
$env:CODEX_FEATHER_ROOT = 'D:/path/to/codex-feather'
python -B -m unittest tests.test_plugin_portability -v
```

The tests create their records in temporary projects. They never operate on the
source checkout's handoff records. For future upstream refreshes, review schema
and instruction changes, rerun the suite and cross-runtime test, and update the
hash manifest only after reviewing the new imported bytes.

## Command relocation in 0.2.1

The local skill is now `skills/handoff`, invoked as `/cc-feather:handoff`. The 12 runtime files remain byte-identical to upstream. The eight inherited test modules now reference the relocated local path and use normalized text line endings. The original all-20-files identity result above describes the initial import, not the adapted tests. `upstream-manifest.json` maps current paths and hashes to original upstream paths and records adapted source hashes. Record schemas and on-disk handoff locations are unchanged.

## Local history fixes pending upstream

`history.py` and `history_mutations.py` now differ from upstream; their upstream hashes are recorded under `adaptations` in `upstream-manifest.json`.

- Legacy-format entry starts are recognized only before the first modern `## <work> · 完成：<time>` entry. Archival only appends modern entries, so a completed body whose details hold a heading followed by `完成：…` or `狀態：完成` no longer blocks archival with `history-format`, nor leaves later clear or seal refusing the history.
- `clear` and `seal` parse an archive source under its queried `archive/<batch>.md` name, matching the identities `history` returns.
- `history.py` also computes byte offsets in one incremental pass; `history_mutations.py` `clear` runs the same pending-archive check as `seal`, so clearing an entry whose completed work file still exists is deferred with `pending-archive`.

Further local runtime fixes (also pending upstream; `archiving.py`, `writing.py`, `cli.py`, `storage.py` and `observations.py` now have `adaptations` entries recording their upstream hashes):

- `archiving.py`, `writing.py`: `check_archivable` refuses to save a `完成` work (create or update) whose body would not archive as exactly one history entry, for example a body line shaped like `## <title> · 完成：<time>`; nothing is written. `archive` reports such an already-stuck work as `format`, naming the offending line and the repair path. A completed work accepts exactly one edit, `update {version, replacement}` keeping the same title, `更新` and `狀態：完成`, passing the archive check, with no matching identity already in history. `skills/handoff/references/tool.md` ("Update and completion") documents this. The title line is compared after stripping, matching `summary()` and history parsing.
- `cli.py`: invalid JSON, non-UTF-8 and over-deep stdin are `input` errors, and any other unexpected exception is a JSON `internal` error with exit 2, so the JSON/exit-code contract always holds.
- `writing.py`, `archiving.py`: `update` details are normalized to the file's newline; archival into a CRLF history uses CRLF for the marker and separator (work bodies stay byte-exact), and the retry check accepts a CRLF separator only where another entry starts at the entry's end. New history files stay LF.
- `storage.py`: superscript `COM¹²³` and `LPT¹²³` names are reserved. `observations.py`: when `st_ino` is unavailable, duplicate-source detection uses the resolved path instead of `(st_dev, 0)`.

Deferred, no change: relaxing `same_body` for a retry after the following entry was cleared (indistinguishable on disk from the upstream-tested extra-newline conflict; outcome is a preserved-data `conflict`), and a history lock for the check-then-replace lost-update window (a lock would not coordinate codex-feather, adds stale-lock failure modes and contradicts the documented single-writer contract).

New local-only tests live in `tests/test_handoff_local_fixes.py`; it is not in the manifest `files` or `adaptations`.

`tests/test_handoff_history.py` replaces the expectation that such a heading inside modern history is reported as an uncertain boundary. Re-import both files once upstream carries an equivalent fix.
