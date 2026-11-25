# Test speed-ups, first batch

Label: `ready-for-agent`

Vocabulary follows [CONTEXT.md](../../CONTEXT.md), which defines Plan, Claim, Unbounded probe and Runner. This spec applies the first batch of speed-ups from the `/cc-feather:test-speedup` report on cc-feather's own tests of 2026-11-25, which the user chose on 2026-11-25 as the low-risk batch: no assertion is weakened, no test design changes, and the second batch (shared fixtures and in-process tool calls) is recorded separately in `.feather/handoffs/test-speedup-batch-2.md`. This spec changes only files under `tests/` and the validation document; it changes no shipped file, so it is landed without a version change or tag, as `docs/specs/test-module-split.md` was, and the next release carries it.

## Problem Statement

The whole suite, `python -B -m unittest discover -s tests -t .`, takes about 500 s on the maintainer's Windows machine and starts about 18,000 processes. Measurement on 2026-11-25 (inside the Runner, per-test timing and cProfile) found time spent on work the tests do not verify:

- `tests/test_merge_upstream_tool.py` builds the same Git fixture, 51 Git commands with clones, pushes and a submodule, once for each of its five test classes (about 2.7 s each), and `ListsTest` runs the tool with the same input once per test in `setUp`.
- Five rule-pin modules read old tagged text with `git cat-file` or `git show` again for every sentence they pin; `test_feather_delegation_dedupe.py` alone starts about 470 Git processes to read 11 files at one tag.
- The configuration tool calls `os.fsync` once per written file; `FeatherConfigTests` does so about 4,000 times, 6.2 s, and no test asserts anything about it except the two that test `_replace` directly.
- `PendingUnknownTest` in `tests/test_handoff_local_fixes.py` and `request()` in `tests/test_handoff_adopt.py` start a tool subprocess (about 140 ms each) only to read a history id or a record version before the step the test verifies.
- `tests/test_leases_park.py` imports the `CriticalSectionTest` class itself from `tests/test_leases_tool.py`, so unittest collects and runs its three tests a second time in the park module.

## Solution

Five independent changes, one per ticket, each in its own test files. Every test keeps its assertions, its inputs and what it verifies; only repeated setup, repeated reads, an fsync no test verifies, and a duplicate collection go away. After all five are accepted, main measures each change's modules before and after and records the gain.

## User Stories

1. As the maintainer, I want the merge-upstream fixture built once per module, so that five identical builds become one.
2. As the maintainer, I want `ListsTest` to run the tool once for its shared input, so that eight identical runs become one.
3. As the maintainer, I want tagged text read once per file and tag, so that pin tests stop starting hundreds of identical Git processes.
4. As the maintainer, I want a missing tag or Git to skip exactly as today, so that caching changes no test's outcome.
5. As the maintainer, I want config tests that do not test durability to skip `fsync`, so that thousands of disk flushes stop costing seconds.
6. As the maintainer, I want the tests of `_replace` itself to keep the real `fsync`, so that the write path is still exercised as shipped.
7. As the maintainer, I want preparation reads done in-process, so that a test pays for a subprocess only where the subprocess is what it verifies.
8. As the maintainer, I want the critical-section tests to run once, so that the suite does not repeat them under another module's name.
9. As the maintainer, I want each change's gain measured and recorded, so that I know what the batch saved.
10. As the maintainer, I want no release for this batch, so that users are not asked to update for a change that does not affect them.

## Implementation Decisions

- **Merge-upstream fixture (ticket 01).** In `tests/test_merge_upstream_tool.py`, the work `MergeUpstreamBase.setUpClass` does (base directory, isolated Git environment, `installed_git_version`, `build()`) runs once per module, for example in `setUpModule` with `unittest.enterModuleContext` and `addModuleCleanup`, and the five classes read it. The skip when the base directory lies inside the project stays and skips the module's fixture-using classes as today. Tests that change state keep working on their own copies or repositories (`copy_work`, `own_origin`, the single-branch, criss-cross and partial cases); `ReadOnlyTest.test_a_run_changes_nothing_and_reaches_no_remote` keeps checking that a run changes nothing. `ListsTest` runs the tool once in `setUpClass` and keeps the `status == ok` check there; each test reads the shared result. `SettingsTest`'s own baseline run is not shared with `ListsTest`.
- **Tagged text cache (ticket 02).** In `tests/test_feather_delegation_dedupe.py` (`tagged`), `tests/test_feather_retained_passes.py` (`tagged` and the five `tagged_place` helpers), `tests/test_feather_repo_trust.py` (`tagged_blob`, `tagged_tree` and the read at about line 905), `tests/test_feather_completion_criteria.py` (`tagged_path`, `tagged`, `previous`) and `tests/test_feather_final_check.py` (`tagged` and the three `git show` reads of `V0_37_0`), the Git result for one revision and path is read once per process and kept in a module-level cache keyed by revision and path. Every revision read is a tag or a fixed commit, which the project never moves. The cache keeps the outcome as well as the text: a revision that is missing, Git that cannot be run or times out, and a path missing at the revision lead to the same `skipTest`, `None`, `''` or assertion failure on every call as today. Each module keeps its own Git invocation, including the pinned `GIT_READ` prefix where it uses one. `tagged_tree` may read its blobs with one `git cat-file --batch` process instead of one process per file, with the same prefix and the same results. `tagged_blob`'s signature stays, since `tests/test_feather_repo_trust_docs.py` imports it.
- **No fsync in apply-heavy config tests (ticket 03).** In `tests/test_feather_config.py`, `FeatherConfigTests`, `SavedStopThresholdTests` and `LeasesComponentTests` replace `config.os.fsync` with a no-op for each test, for example `self.enterContext(mock.patch.object(config.os, "fsync"))` in `setUp`. `test_replace_copies_mode_before_publish_and_preserves_original_on_failure` and `test_guidance_mode_survives_lifecycle_and_rollback` run with the real `fsync`, by restoring it in those tests or by moving them to a class without the patch with their bodies unchanged. `scripts/feather_config.py` is not changed.
- **Preparation reads in-process (ticket 04).** `PendingUnknownTest.payload` reads history through `LocalFixesBase.invoke` instead of `run_tool`. `request()` in `tests/test_handoff_adopt.py` reads each version and id with the same commands it runs today (`read --work`, `history`, `history --include-sealed`, each with `--exact-root` against the source checkout) through `SharedBase.invoke` instead of `run_tool`, asserting exit code 0 as `run_tool` does. The `clear`, `seal` and `adopt` runs each test verifies keep running as they do today.
- **Duplicate collection (ticket 05).** `tests/test_leases_park.py` no longer binds the name `CriticalSectionTest` in its module namespace; `ParkLeaseTest` reaches `write_lock` through the module, for example `from tests import test_leases_tool` and `test_leases_tool.CriticalSectionTest.write_lock(...)`. The suite's test count drops by exactly the three duplicated tests and every other test id stays.
- **Measurement.** After the last ticket is accepted and before the Plan is landed, main measures each ticket's modules at the Plan base and at the final commit in the same session, with the same method: per-test timing of `python -B -m unittest` over those modules, run inside the Runner, with `FEATHER_LINK_TEST_DIR` under `J:\gotmp\` and the two busy-spin tests (`test_leases_tool.CriticalSectionTest.test_a_concurrent_reader_delays_a_release_but_leaves_nothing_behind`, `test_leases_takeover.RenewTest.test_a_concurrent_reader_delays_a_renew_but_does_not_fail_it`) left out. Scratch copies of the Plan base for this live under `J:\gotmp\` and are removed afterwards. Main reports each ticket's seconds before and after, and the whole suite's.
- **Validation record.** Main records the measurement and the final check under a heading of its own in `docs/setup-validation.md`, `## Test speed-ups, first batch`, after the Plan's review round, as it records a review round after a release.
- **Not affected.** Every shipped file: skills, templates, scripts, the plugin manifest, both READMEs, the reference documents and CONTEXT.md. `tests/feather_support.py`, the second batch's shared fixtures and every other test module.

## Testing Decisions

- These are changes to tests, so the evidence is that the same tests pass with the same assertions: each ticket's diff changes no assertion and no input a test verifies, and its modules pass.
- A test id list taken with `unittest`'s discovery before and after each ticket is equal, except ticket 05, where it drops exactly the three `tests.test_leases_park` copies of `CriticalSectionTest`.
- Ticket 02's cache is shown to keep the skip behaviour by reading the code paths, not by a new test; no test is added for test helpers.
- Ticket 03's two `_replace` tests run with the real `fsync`, which a reviewer checks in the diff.
- The Plan's overall acceptance is the full suite, `python -B -m unittest discover -s tests -t .` with `FEATHER_LINK_TEST_DIR` under `J:\gotmp\`. It is the Plan's overall acceptance, which the final check runs for each commit to be landed, not for each Claim, and it is not part of any Claim's acceptance; each ticket cites it.

## Out of Scope

- The second batch: SharedBase and StoreFixture templates and in-process tool calls (`.feather/handoffs/test-speedup-batch-2.md`).
- Timeouts for subprocess calls without one and a time limit for the whole run, which stay undecided in `.feather/handoffs/test-speedup-batch-1.md`.
- Process-level parallel runs.
- Speeding up the configuration tool's own `_safe_path` checks, which is a change to shipped code.
- Any change to what a test verifies, its inputs or its sizes.

## Further Notes

- **Measured base.** 2026-11-25 at aad2f67, inside the Runner: `test_merge_upstream_tool` 26.9 s; `test_feather_delegation_dedupe` 8.2 s, `test_feather_retained_passes` 5.5 s, `test_feather_repo_trust` 6.1 s, `test_feather_completion_criteria` 3.0 s, `test_feather_final_check` 1.6 s; `FeatherConfigTests` 39.2 s with `fsync` 6.2 s under cProfile; `PendingUnknownTest` 10.9 s, `test_handoff_adopt` 30.2 s; the duplicated `CriticalSectionTest` about 2.4 s. The estimate for the batch is 45 to 50 s. The measurement after the batch is compared with a base measured again in the same session, not with these numbers.
- **Tickets.** Five tickets under `.scratch/test-speedup-batch-1/issues/`, one per change, independent of each other, each with related-test acceptance.
- Automatic plan review is on, so the tickets get plan review before implementation.
