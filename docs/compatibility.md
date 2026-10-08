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

## Follow-up fixes pending upstream

These further local divergences are recorded in the `adaptations` entries for `storage.py`, `writing.py` and `cli.py`. The on-disk record, history and baseline formats are unchanged.

- `storage.py`: Git runs without the inherited variables that select another repository or redirect its output. Besides `GIT_DIR`, `GIT_WORK_TREE`, `GIT_COMMON_DIR`, `GIT_INDEX_FILE`, `GIT_OBJECT_DIRECTORY`, `GIT_ALTERNATE_OBJECT_DIRECTORIES` and `GIT_NAMESPACE`, this now covers the rest of Git's local repository list (`GIT_IMPLICIT_WORK_TREE`, `GIT_PREFIX`, `GIT_GRAFT_FILE`, `GIT_NO_REPLACE_OBJECTS`, `GIT_REPLACE_REF_BASE`, `GIT_SHALLOW_FILE`, `GIT_CONFIG`) and Git for Windows' `GIT_REDIRECT_STDIN`, `GIT_REDIRECT_STDOUT` and `GIT_REDIRECT_STDERR`. User configuration variables stay on purpose (`GIT_CONFIG_PARAMETERS`, `GIT_CONFIG_COUNT`/`GIT_CONFIG_KEY_<n>`/`GIT_CONFIG_VALUE_<n>`, `GIT_CONFIG_GLOBAL`, `GIT_CONFIG_SYSTEM`, `GIT_CONFIG_NOSYSTEM`, `HOME`, `XDG_CONFIG_HOME`, `USERPROFILE`, `GIT_CEILING_DIRECTORIES`, `GIT_DISCOVERY_ACROSS_FILESYSTEM`): they cannot select another repository, and removing them would break `safe.directory` and make ignore decisions differ from the user's own Git. A successful root discovery whose output is empty or not an absolute path is `uncertain` instead of falling back to the current directory.
- `writing.py`: the details-update check compares the following level-1/2 headings together with their offsets inside the verbatim tail, so a fence change that hides those headings and exposes identical example lines is still refused with `details-format`.
- `cli.py`: a missing file is `not-found` only when it lies inside the selected project (or, when the error names no file, for `read`, `archive` or `compare` of a named work); any other missing file is `io`.

The `observations.py` entry now also records its earlier change: source change detection ignores `st_ctime`, as `read_file` does.

## Round-3 review fixes pending upstream

These local divergences are recorded in the `adaptations` entries for `archiving.py`, `writing.py`, `storage.py`, `history_mutations.py` and `cli.py`. The on-disk record, history and baseline formats are unchanged; codex-feather reads and writes the same files. The `archive` input key below is a command input, never stored.

- `archiving.py`, `writing.py`: `archive` accepts an optional `tracking` (`default` or `track`, validated like create/update) next to `version` (upstream: only `version`). After a successful archival it applies that tracking choice for the project; a tracking failure then returns `partial`, `code: tracking-failed`, `archived: true` with the archival fields. A completed save whose tracking failed is still not archived automatically, and its `recovery` now says to resolve the Git rules and run `archive` with the current version and the same tracking choice (a completed work refuses normal updates); other works keep "retry update with the current version". The archival run by a completed save does not apply tracking a second time.
- `writing.py`: a details update is refused with `details-format`, file unchanged, when the existing details hide level-1/2 headings inside a code fence that is still open at the end of the details, or inside a fence that also holds a same-character opener with an info string (for example a swallowed `## 檔案基準` JSON block). Headings inside a closed, self-contained fenced example stay allowed, so `tests/test_handoff_snapshots.py` is unchanged. Not detected: an unclosed opener followed by a manual section that ends with exactly one bare fence line.
- `writing.py`: a supplied optional field that is blank after stripping is an `input` error on create and update (required fields keep "Missing or empty"); upstream saved it, and later partial updates of that field were refused. Create normalizes CRLF and CR in `details` to LF.
- `storage.py`: work names and listing share one rule, a `.md` suffix after a nonempty stem other than `history.md`, so `--work .md` is `unsafe-name` (upstream created a file that `list` never showed). `replace_file` makes its temporary file writable before removing it, suppresses cleanup errors so the original error propagates, and reports a failed replacement of a target without the write bit as `read-only` (upstream left the temporary file and reported the cleanup `PermissionError` as `io`).
- `storage.py`: only symbolic links and name-surrogate reparse points (tag bit `0x20000000`, such as junctions and mount points) count as links. When `lstat` shows the reparse attribute with a zero tag (CPython followed a non-surrogate point), the tag comes from the parent directory's `os.scandir` entry; a missing entry or a zero tag stays refused. Other tags, such as cloud-file placeholders and deduplicated files, are read as ordinary data (upstream refused every reparse point). Hard-link and non-directory-ancestor checks are unchanged.
- `history_mutations.py`: a malformed work blocks `clear` and `seal` with `pending-unknown` only when it might be completed: unreadable or undecodable, no title on the first line, or not exactly one status line anywhere in the file (`狀態` after optional spaces or tabs, then a full-width or ASCII colon) whose value is `進行中` or `受阻`. Other malformed works are re-checked like the rest before writing and listed in the result's `warnings`.
- `cli.py`: a duplicate JSON key on stdin is `code: input` (upstream: `snapshot-format`), message unchanged.
- `archiving.py`: archival into an existing empty or whitespace-only `history.md` writes the `# 交接歷史` header and an LF entry marker, as for a new history, through the same replace path.

Test changes: in `tests/test_handoff_local_fixes.py` the former `PendingUnknownTest.test_malformed_work_blocks_clear_and_seal_as_pending_unknown`, whose readable `進行中` work with a zone-less timestamp expected `pending-unknown`, now expects `ok` with a warning; pending-unknown coverage moves to completed, duplicate-status, merge-conflict and untitled works. New tests for these fixes live in `tests/test_handoff_local_fixes.py` and, for the reparse rule and hard links, `tests/test_handoff_links.py` (the junction and hard-link tests run under `FEATHER_LINK_TEST_DIR` when set).

Test adaptations: `tests/test_handoff_archive.py`, `tests/test_handoff_storage.py`, `tests/test_handoff_tool.py` (whose setup the roots and snapshots tests share), `ObservationUnitTest` in `tests/test_handoff_snapshots.py` and the local `tests/test_handoff_local_fixes.py` build their temporary projects from `os.path.realpath(...)`, so the suite also passes when the system temporary directory is reached through a junction or symlink. The in-process `Store` tests in `tests/test_handoff_storage.py` and `tests/test_handoff_roots.py` reset the root registry. In `tests/test_handoff_links.py` the mock-based fallback test (`UnsupportedStrictRealpathTest`) and the empty-output discovery test no longer need strict realpath support from the volume; only the latter's strict-realpath subtest still skips with "strict realpath unsupported".

## Conflict-copy check pending upstream

This local divergence is recorded in the `adaptations` entry for `history_mutations.py`. The on-disk record, history and baseline formats are unchanged; codex-feather reads and writes the same files.

- `history_mutations.py`: after the selected-identity check, so `pending-archive` and `conflict` keep precedence, a work without format problems also blocks `clear` and `seal` with `pending-unknown` ("cannot rule out an unfinished archival") when its whole text has more than one status line (`狀態` after optional spaces or tabs, then a full-width or ASCII colon; inside code fences and indented lines too) or a merge-conflict marker line (`<<<<<<<`, `>>>>>>>` or `|||||||` at the line start, followed by a space or the line end; `=======` is not checked because it also underlines setext headings). This catches a git conflict copy kept after the title line, or a second record pasted below the details, that a later archival could restore after its entry was cleared or sealed (upstream and the previous local rule let such a work pass). Cost: an unfinished work whose details quote a line starting with `狀態` and a colon blocks clear and seal until that line is reworded; `skills/handoff/SKILL.md` ("Clear and seal results") and `skills/handoff/references/tool.md` document the cause and the repairs.
- `writing.py`, unchanged by decision: a details update stays refused with `details-format` when a closed example that hides a heading is followed by a fence left open to the end of the details. The text alone cannot tell this from an unclosed opener that swallowed a later section holding a bare code block, so narrowing the check would turn that refusal into silent loss of the section. `skills/handoff/references/tool.md` documents the case and the ways forward.

New tests live in `PendingUnknownTest` and `SwallowedDetailsTest` in `tests/test_handoff_local_fixes.py`; no existing test expectation changed.

## Heading, tracking and title fixes pending upstream (0.15.0 and 0.17.0)

These local divergences are recorded in the `adaptations` entries for `baseline.py` and `records.py` (new), `tracking.py`, `writing.py` and `cli.py`. The on-disk record, history and baseline formats are unchanged; codex-feather reads and writes the same files, but the two tools can read a record's sections and header differently, as below.

- `baseline.py`, `writing.py` (0.15.0): a heading is a CommonMark ATX heading, up to three spaces of indent, one to six `#`, then a space, a tab or the line end. Indented (`  ## Notes`) and tab-separated (`##<Tab>Notes`) headings and an empty `##` now bound the managed details and baseline sections, are kept by details updates and are checked for fence swallowing (upstream: only a column-0 `#` run followed by a space).
- `baseline.py`, `records.py`, `writing.py` (0.17.0): the work header under the first-line `# ` title ends at the first such heading outside a code fence, for both the summary that read/list report and partial header updates (upstream: the first column-0 `#` run followed by a space, fences ignored). Lines are split only at LF (a CRLF line ends there too), so characters such as `\x0c` or `\x85` stay inside a field value. A heading inside a fence no longer ends the header, and a fence left open runs the header to the end of the file, so field-like lines below it are read as header fields where upstream stopped at the fenced heading. Field-like lines under an indented, tab-separated or empty heading are no longer header fields. Records whose headings both rules recognise read and update byte for byte as before.
- `tracking.py` (0.15.0): `.gitignore` lines are compared as Git reads them: leading whitespace is part of the pattern and trailing spaces are not. An indented `# cc-feather: track /.feather/handoffs/` marker is no longer a marker, and `tracking: track` keeps an indented user rule instead of removing it (upstream compared stripped lines).
- `records.py` (0.15.0): read/list report a work whose title is blank after the `# ` as a format problem, "Work title must not be blank" (upstream accepted it).
- `tracking.py`, `writing.py` (0.17.0): when the first Git probe cannot run Git (a missing executable or another operating-system error) or times out, a create or update now saves the work and returns `status: partial`, `code: tracking-failed`, `cause_code: git-unavailable`, exit 2; a completed work is not archived, and the recovery says to wait for Git and then apply tracking once with update or `archive` using the same tracking choice. Upstream, and earlier cc-feather, returned a complete save with tracking `not-checked`. This changes documented behaviour for a deliberately selected `--exact-root` without Git: with Git unavailable the save is now only partial. A directory Git reports as not a repository still saves completely as non-Git.
- `cli.py` (0.10.1): `--project` and `--exact-root` are accepted before or after the subcommand (upstream: before it only). The manifest hash for `cli.py` was not refreshed then and is corrected now.

Manifest corrections: `tests/test_handoff_mutations.py` is byte-identical to its upstream source (its recorded source hash equals the shipped one), so its adaptation entry, which claimed a path and line-ending change, is removed; the 0.2.1 note above about the eight inherited test modules does not apply to it. `tests/test_feather_config.py` (`UpstreamManifestTests`) now fails when a listed file does not ship, its hash differs from the shipped bytes, or an adaptation names an unlisted file or records no change.
