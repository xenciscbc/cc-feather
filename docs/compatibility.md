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
