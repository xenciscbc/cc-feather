# Setup/model validation

Validated on 2026-09-23 in this repository on Windows, Python 3.11.9 and Claude Code 2.1.280. The main Agent wrote role/policy/skill integration; the executor implemented the configuration tool and its tests. Parent review found and closed Unicode stdout, alternate-name collision, scope validation, backup-path and model-only update gaps. No live Claude configuration or model session was installed/launched.

## Executed checks

| Check | Result |
| --- | --- |
| `python -B -m unittest tests.test_feather_config -v` | 16 cases: 15 passed, 1 skipped because Windows symlink creation was unavailable |
| Parent `python -B -m unittest tests.test_feather_config tests.test_plugin_portability -v` | 18 cases: 16 passed, 2 skipped (same symlink restriction, optional cross-runtime test without CODEX_FEATHER_ROOT) |
| Actual subprocess CLI lifecycle with Chinese/space project path and CP950 environment | Passed install(off), model change, review(auto), update, show, temporary session export, remove and final check |
| Original handoff runtime/tests | All 20 imported file hashes still match upstream-manifest.json; prior cross-runtime evidence is in compatibility.md |
| Plugin and marketplace `claude plugin validate ... --json` | Passed |
| Three skill frontmatter checks via skill-creator quick_validate under Python UTF-8 mode | Passed |
| Local Markdown links in shipped skills | All referenced files exist |

The configuration tests cover project/user scope, exact Explore deployment, different filenames declaring Explore (including BOM/quoted/commented names), stale previews, unmanaged conflicts, altered managed files, preservation of settings/handoff/unrelated guidance, model-field independence, installed-body preservation during model/session operations, update persistence, review-mode toggling, backup/rollback, malformed state and hard-link rejection.

A parent smoke test ran Python as a real subprocess with PYTHONIOENCODING=cp950 and PYTHONUTF8=0. The CLI emitted valid UTF-8 JSON for every lifecycle operation, preserved analyst effort when only its model changed, kept permanent Explore settings unchanged after a session export, and removed owned configuration afterward. All work was in temporary projects and configuration roots.

## Claim boundaries

- Native CLI manifest validation did not enumerate role contents (`contents: []`); it is not claimed as proof that Claude loaded each deployed role. An initial attempt in the system temporary drive was skipped by the native validator as a linked directory; using a workspace temporary directory validated the manifest but still did not enumerate roles.
- Real Claude dispatch, model/effort selection, automatic skill discovery, plan-review behavior and the auto/off policy's behavioral compliance remain untested. Use a fresh supported Claude session and /tasks to observe actual execution. Saved configuration is explicitly labeled requested-only by the tool.
- The review cap/mode is expressed in managed policy. There is no hook-enforced workflow counter or runtime interception.
- Per-scope locks serialize this tool, not arbitrary editors or other applications. Conditional rollback and preimage checks do not create a global atomic filesystem transaction. A concurrent alias/path change remains outside a complete filesystem isolation guarantee.
- Collision scanning covers the selected scope's agents tree. Managed/CLI overrides, nearer nested project roots, provider restrictions and unavailable launch context need separate runtime checks. Settings diagnostics are observations, not a full Claude precedence evaluator.
- Initial Windows symlink creation was unavailable; hard-link rejection passed. Subsequent Ubuntu/WSL configuration validation is recorded below; macOS remains untested.

## Reproduce

```text
python -B -m unittest tests.test_feather_config tests.test_plugin_portability -v
claude plugin validate . --json
claude plugin validate .claude-plugin/plugin.json --json
```

To rerun the optional handoff cross-runtime test, set CODEX_FEATHER_ROOT to a codex-feather checkout as described in compatibility.md. To inspect requested native definitions without installation:

```text
python -B scripts/feather_config.py session --project /absolute/existing/project --scope project
```

The raw session result is a Claude --agents JSON object. It does not launch a model, modify files, set the current session's effort or automatically enable main-session delegation policy.

## 0.2.1 command relocation and dedicated toggles

Main Agent completed the command rename and documentation changes on 2026-09-23. The manifest registers handoff, setup, model, auto-on and auto-off. Toggle skills are user-invoked only; no argument/session records a conversation preference, while project/user uses the existing preview/apply review operation.

- Full unittest discovery with CODEX_FEATHER_ROOT pointing to the sibling upstream checkout: 91 tests, 89 passed, 2 skipped because Windows symlink creation was unavailable. Cross-runtime alternating record writes passed.
- Claude marketplace and plugin manifest validation: passed with no warnings. The validator returned no content inspection results; this is not live skill execution validation.
- Parsed all five skill frontmatters, checked their names against directory names and both toggle invocation flags; all local Markdown links under skills resolve.
- All recorded manifest hashes matched; all 12 handoff runtime files remained byte-identical to upstream. Eight inherited tests contain only local-path/text normalization adaptations recorded in the provenance manifest.
- No live Claude installation, skill invocation or model dispatch was performed. Changes have not been committed or pushed.

## Default-off follow-up

Automatic plan review now defaults to off for a new installation and uninstalled show/check. Existing saved choices remain intact during update. The scoped permanent toggle writes both the managed CLAUDE.md block and state.json; session-only toggles do not write either file. After this change, the configuration suite passed 15 cases and skipped one Windows symlink case. Assertions cover default-off preview, saved state and the rendered guidance line. Live Claude behavior remains untested.

## P2: preserve POSIX file permissions

The main Agent fixed atomic replacement of existing configuration files to copy their POSIX mode to the temporary file before publishing it. Failure to set the mode leaves the original file untouched and removes the temporary file. New files retain the private temporary-file default. The same helper preserves mode during ordinary updates and rollback; this does not claim preservation of ownership, ACLs or extended attributes.

Validation: `python -B -m unittest tests.test_feather_config -v` on Windows passed 16 tests and skipped 2 (POSIX-only lifecycle and unavailable symlink creation). The same suite using `python3` in existing Ubuntu/WSL passed all 18 tests. Linux test data used its native temporary filesystem, verifying mode 0640 through install, review toggle, update, injected state-write failure/rollback and remove, plus mode 0600 for a new file. No real Claude user configuration was changed.

## 0.3.0 native role rename

Native role names now match their keys: scout, analyst, mech-executor, executor, security-executor and Explore. State schema version 2 denotes unprefixed filenames; version 1 remains readable and removable. Setup update migrates intact owned legacy roles, preserves choices/review mode and refuses occupied target names or source drift. Model/review changes and session export request migration first.

Windows configuration suite: 21 cases, 19 passed and 2 platform-related skips. Ubuntu/WSL: all 21 passed; after strengthening rollback to restore the mode of a deleted legacy file, the two affected Linux migration/permission cases passed again, and the Windows suite passed again. Tests cover collisions at both target filenames and alternate files declaring the same name, migration rollback, old installation removal, saved setting preservation and native session exports. Plugin manifest validation passed without warnings; role names and local documentation links matched. No live Claude role dispatch was run. Main Agent completed these changes directly.
