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
- `cli.py`: invalid JSON, non-UTF-8 and over-deep stdin are `input` errors, and any other unexpected exception is a JSON `internal` error with exit 2, so the JSON/exit-code contract holds for every invocation except `--help`.
- `writing.py`, `archiving.py`: `update` details are normalized to the file's newline; archival into a CRLF history uses CRLF for the marker and separator (work bodies stay byte-exact), and the retry check accepts a CRLF separator only where another entry starts at the entry's end. New history files stay LF.
- `storage.py`: superscript `COM¹²³` and `LPT¹²³` names are reserved. `observations.py`: when `st_ino` is unavailable, duplicate-source detection uses the resolved path instead of `(st_dev, 0)`.

Deferred, no change: relaxing `same_body` for a retry after the following entry was cleared (indistinguishable on disk from the upstream-tested extra-newline conflict; outcome is a preserved-data `conflict`), and a history lock for the check-then-replace lost-update window (a lock would not coordinate codex-feather, adds stale-lock failure modes and contradicts the documented single-writer contract).

New local-only tests live in `tests/test_handoff_local_fixes.py` and `tests/test_handoff_links.py`; neither is in the manifest `files` or `adaptations`.

`tests/test_handoff_history.py` replaces the expectation that such a heading inside modern history is reported as an uncertain boundary. Re-import both files once upstream carries an equivalent fix.

## Review fixes pending upstream

These local divergences are also pending upstream. `tracking.py` now has an `adaptations` entry, and the entries for `writing.py`, `cli.py`, `storage.py` and `history_mutations.py` describe them. The on-disk record, history and baseline formats are unchanged; codex-feather reads and writes the same files.

- `writing.py`: a details update that would hide or change the level-1/2 sections after `## 詳細紀錄` (for example an unclosed code fence) is refused with `details-format` and nothing is written. Create/update results add `warnings` for level-1/2 headings inside details and update results add `preserved_sections`. A completed save whose archival then fails returns `partial` with `code: archive-failed`, `cause_code` and `recovery: retry-archive` instead of an `error` for already saved work.
- `tracking.py`: `tracking: track` records the choice as the `.gitignore` comment `# cc-feather: track /.feather/handoffs/` (removing only the exact `/.feather/handoffs/` rule, in one write); later default saves report `existing-rule` and leave `.gitignore` unchanged. The marker is Git-inert and unknown to codex-feather, whose default save still appends the rule while no handoff is tracked.
- `history_mutations.py`: a malformed or unreadable work file blocks `clear` and `seal` with `pending-unknown` (upstream: `pending-archive`).
- `cli.py`: usage errors return the JSON envelope with `code: usage` and a missing selected file `code: not-found`, exit 2 (upstream: argparse text with exit 2, and `io`).
- `storage.py`: a linked or junction `--project` path or ancestor above the project is resolved once with a strict real path; `root.path` reports it and `root.requested` the supplied spelling. Every path check stops at that registered root after confirming it still resolves to itself (`unsafe-path`, "Project root changed after it was resolved"). The Git root is the resolved path or its nearest ancestor that is the same directory as the Git top level, and a supplied path that crosses a link below the repository root is `uncertain`. Links, junctions, reparse points and hard links at or below the root stay refused. Where a volume cannot resolve strict real paths, the previous full-ancestor link refusal applies (upstream refuses links anywhere in the path). `create_file` removes the partial file it created when writing fails, after confirming the same file identity, and re-raises the original error.

Test adaptations: `tests/test_handoff_tool.py` expects the tracking marker after `tracking: track`. `tests/test_handoff_roots.py` and `tests/test_handoff_snapshots.py` import their fixtures through the `tests` package, so `python -B -m unittest tests.test_handoff_snapshots tests.test_handoff_roots` works from the repository root, and reset the root registry after building stores in-process.

The link tests in `tests/test_handoff_links.py` run under `FEATHER_LINK_TEST_DIR` when it is set (they create and remove a unique subdirectory there) and otherwise under the system temporary directory. They skip with "strict realpath unsupported" on a volume that cannot resolve strict real paths, such as some RAM disks:

```powershell
$env:FEATHER_LINK_TEST_DIR = 'D:/path/on/an/NTFS/volume'
python -B -m unittest discover -s tests -t . -v
```
