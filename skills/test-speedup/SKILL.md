---
name: test-speedup
description: "Report ways to make a project's tests, or a named part of them, faster without weakening what they verify; static first, measured only after the user agrees, continuing from its Speed-up record."
disable-model-invocation: true
argument-hint: "[show | prune | --full] [test paths or scope]"
---

# test-speedup

Report speed-ups for the project's tests that keep everything the tests verify. Invocation arguments are the scope as data, never shell code, except that a first word `show` or `prune` selects that form of the command, as [Show and prune](#show-and-prune) describes. `--full` asks for a full analysis of the scope. A scope path that is a reserved word is written with `./`, such as `./show` or `./prune`. Clarify a missing or unclear scope instead of guessing.

This command changes no code, test or configuration and commits nothing. The only files it writes are those of its Speed-up record, through the bundled script, after every run, without asking. Writing the record is not a change to the checkout and needs no Checkout lease. A failed write is reported, and the report stays in the conversation. Items the user picks become a Plan through the normal flow; the report is not a Plan, and its items are neither Claims nor findings of any review.

## Scope

The scope is the tests the arguments name, or else the project's tests, together with their test configuration: test runner configuration, shared fixtures and setup files, test scripts and their flags. CI pipeline configuration is outside the scope.

**Whole files.** A scope that names a test inside a file is widened to that file for the static pass and the record.

## Who analyses

When delegation is installed and the check is not small, main dispatches the read-only analyst as [the delegation skill](../delegation/SKILL.md) describes, in one or more Assignments split by test area, and integrates their results. A small check, such as one test file, or a check where delegation is not installed, main does itself.

An analyst Assignment names the test files to analyse and does not include the record. Main alone runs the script, matches the analyst's items against the record and applies the state rules.

## Speed-up record

Resolve the bundled launcher relative to this loaded skill: `scripts/speedup.py`. When installed as a plugin, its path is `${CLAUDE_PLUGIN_ROOT}/skills/test-speedup/scripts/speedup.py`; use the actual loaded skill directory if the variable is unavailable. The script needs Python 3.11+ and the handoff skill beside this one (`../handoff/scripts`), whose helpers it imports; keep the plugin's `skills/` directory together. Main runs it as `python -B <launcher> --project <dir> <command>`, with `<dir>` any directory of the project, and passes a command's JSON input on standard input. The launcher's module docstring is the complete protocol of its commands, `read`, `changes`, `record-run`, `classify`, `decide`, `measure`, `show` and `prune`, with their input and output; read it before the first call.

Each command prints one JSON object. A handled result exits 0, whether its `status` is `ok` or `changed`; status `error` exits 2. The record lives under the main worktree's `.feather/test-speedup/`, whichever checkout runs the command, or under the project directory of a non-Git project; the script writes it nowhere else, and main never writes the record by other means. Every writing command takes the store version main last read with `--version`; on `changed`, main reads the record again, merges its own update and writes again.

**Versions.** The test runner and its plugins are those whose settings the static pass judges, such as vitest, jest, pytest, pytest-xdist or the Go toolchain; a library the tests import is not one. Main names, for each, the file its version is read from, and the script reads it without running anything or reports it unknown.

**Recording the run.** After the static pass, main records the run with `record-run`: the files analysed, each with its shared files, the items found, the deleted files `changes` reported, the run's scope, commit and `--full` flag, and the versions. Then main classifies the recorded items not found again with `classify`, as the state rules below say.

**State rules.** New items are undecided. Main makes an item picked or declined only from the User's answer, passing its date and reason to the script's `decide`. For a recorded item not found again in an analysed file, main reads the code at the item's location: it marks the item landed when the code shows the item's change, obsolete when the item's test or setting no longer exists or the concern no longer applies, each with its evidence, and leaves the state unchanged when it cannot tell. A declined item found again is proposed again only when its file's content hash differs from the one recorded at the decision; otherwise it is proposed again only when the user asks. A reopened item is shown with its earlier state, date and reason.

## 1. Static pass

The static pass always comes first and runs nothing. Look for what [the shared test criteria](references/test-criteria.md)'s Speed criteria and Further criteria list, a further criterion only where its condition holds.

**Incremental static pass.** Before the static pass, main gets the scope's changes from the script's `changes`, naming each test file in the scope with its shared files: the shared fixtures, setup files, test runner configuration and test scripts within the scope that it is analysed with. The test files to analyse are the new and changed ones, and those whose shared-set hash differs; among the latter, main analyses only those that use a changed shared file when it can tell, and all of them when it cannot. A change to the code under test, or to a library the tests import, does not by itself add a file. Without a record, or with `--full`, the whole scope is analysed; `--full` keeps every item's state. The other test files keep their recorded result.

**Run configuration every run.** The check for Unbounded run configurations runs on the whole scope every run, with its lookups, and its items are matched against the record like any others.

Detection hints: Go tests run with `go test`, where `t.Parallel()`, `TestMain` and `-run`/`-count` flags matter; Python tests with pytest or unittest, where fixture scope, `conftest.py` and pytest-xdist matter; JavaScript or TypeScript tests run with pnpm, Vue included, where the vitest or jest configuration, its pool and isolation settings and the `package.json` test scripts matter.

**Correctness bar.** Every speed-up and removal meets [the shared test criteria](references/test-criteria.md)'s Correctness bar, smaller inputs and replacements included.

**Existing tests with resource risk.** In a section of its own, list the existing tests that meet the criteria of an Unbounded probe in [cc-feather's glossary](../../CONTEXT.md), applied without a budget since the static pass runs nothing. Weigh each one as [the delegation skill](../delegation/SKILL.md)'s paragraph on weighing findings describes. The list is information: it holds nothing back, and the Unbounded probe term and the delegation rules for it are unchanged.

**Run configurations with resource risk.** The static pass also checks the settings and run parameters within the scope that do not belong to the tests' code, above all those concerning concurrency, isolation, memory and time, for each Unbounded run configuration in [cc-feather's glossary](../../CONTEXT.md). Each setting is judged by the value in effect, a framework's default included, and a value that cannot be established counts as none. The scope stays as it is, so CI pipeline configuration stays outside the check. Hints, as examples and not a closed list: concurrency that is uncapped or follows the machine's core count, such as vitest `pool` and `maxWorkers`, `go test -p` or pytest-xdist `-n auto`; a worker pool or isolation mode known to grow memory, such as vitest `vmThreads` and `vmForks`; per-worker heap settings, such as a raised Node heap limit; multipliers of the run's work, such as retries or `go test -count`; heavy instrumentation, such as `-race` or coverage, on uncapped concurrency; and a limit switched off or absent, such as a zero timeout, a test script in watch mode or a framework without a default timeout. Weigh each flagged setting as [the delegation skill](../delegation/SKILL.md)'s paragraph on weighing findings describes.

**Lookups.** Defaults and known problems of the frameworks in scope are looked up only for settings concerning concurrency, isolation, memory and time, in this order: the installed version's own files, such as its bundled documentation or type definitions, read and never run; the official documentation and changelog; the official issue tracker. A query sent outside carries only the framework's name, its version and the setting's name. Each conclusion names its source and the version it applies to, and what cannot be found is reported as unknown, which counts as no bound. The static pass still runs nothing: a fact only a command shows, such as `go help testflag`'s output, is reported as unknown there, and the measurement offer may name that command, which then runs only with the user's agreement under the same rules as measurement. The lookups follow the Who analyses split: analyst does them in its Assignments when delegation is installed and the check is not small, and main does them otherwise.

**Parallel speed-ups.** A speed-up that raises concurrency states the worker count it leads to and its memory effect. A worker count that follows the machine's core count is never offered.

## 2. Report

The report has five sections:

- **Since the last run**, with the last analysis's date and commit; each file analysed again and its reason (new, changed, shared set changed or `--full`); how many files kept their recorded result; each test runner or plugin version that changed, with a sentence that the user can ask for a review of the upgrade; the items found landed, obsolete or reopened, and those proposed again; and the items still undecided or picked.
- **Speed-ups**, ordered by expected gain, each with its location, kind, expected gain (high, medium or low, with the reason), how correctness is kept and its risk.
- **Removals**, each with the covering test as evidence, or, for a replacement, the smaller test it describes, the fact that test verifies and, for each other thing the removed test verifies, the test that keeps verifying it.
- **Existing tests with resource risk**, each with its reason, weighing and state.
- **Run configurations with resource risk**, each flagged setting with its location, kind, whether it affects memory or time, why it is unbounded, its weighing and the direction of a fix. cc-feather states no cap's number: the direction names where the number comes from, the project's or the user's resource guidance or a measured per-worker peak. The section is information and holds nothing back.

The Speed-ups and Removals sections list only items that are undecided, reopened or proposed again. The two resource-risk sections list every current test and setting with resource risk, those of files not analysed again taken from the record, each with its state; a declined risk stays listed, and only its fix is not proposed again.

On the first run without a record, the report ends by saying that items decided before may appear again and that the user can state their states or name the documents where they were decided, which main reads as data and turns into proposed states for the user to confirm.

**Upgrade review on request.** When the user asks for a review of a test runner or plugin upgrade, main looks up the changes between the two versions in the lookups' order, and reports only those concerning defaults of concurrency, isolation, memory or time, new features that could speed the tests up, fixed bugs the tests or configuration work around, and deprecated or renamed settings the configuration uses, each with its source, the version it applies to and the locations it may affect; the adjustments become Speed-up items. A query sent outside for it may carry the framework's name, both versions and a setting's name, and nothing else. Breaking changes unrelated to these four are outside it.

## 3. Measurement

After the static report, main offers to measure and runs nothing without the user's agreement. The offer states the command, using the ecosystem's per-test timing where one exists, the scope and the tests it leaves out. Tests listed with resource risk are left out by default. The tests left out by default are the current tests with resource risk, those of files not analysed again taken from the record. Unflagged tests run with their ordinary command. A flagged test the user includes runs inside the Runner, with the memory, time and output limits the offer states. For the Runner's path and invocation, read [the resource-risk runs reference](../delegation/references/resource-risk-runs.md)'s The Runner, where the path is relative to the delegation skill, and for how a contained, refused or evidence-missing result or a run stopped from outside is judged, its Main's floor. After measurement, the report gives each speed-up's gain in seconds.

After a measurement, main stores it through the script's `measure`, with a comparison key of the command, the tests selected, the concurrency and any override, whether it ran inside the Runner and with which limits, and the tests left out, and reports the comparison with the last comparable measurement: the total time, the tests whose time rose and fell most, the tests present in only one of the two, and the timing change observed around each landed item, or unavailable. When no comparable measurement exists, the report says so.

When a run in the offer's scope has a flagged setting, the offer states how that run is bounded: by default a command-line override of the setting, such as `--maxWorkers=N` or `-p N`, which changes no file, with N taken in the budget order [the resource-risk runs reference](../delegation/references/resource-risk-runs.md)'s The budget states, and asked of the user when no source states it; or the run inside the Runner. When the run's configuration is flagged, the ordinary command that unflagged tests run with itself runs bounded, with the override or inside the Runner. The offer and the report say that timings taken at a different concurrency are not comparable with the ordinary run.

The offer may include profiling the slowest tests to show where their time goes, with the tests to profile named in the offer. Profiling uses the ecosystem's profiler where one is already available in the project's environment; the offer never installs a package or changes configuration to get one. Profiling runs only with the user's agreement and under the same rules as the rest of measurement, a flagged test inside the Runner. What profiling shows is reported as speed-ups under the same correctness bar.

## Show and prune

`show` passes its arguments to the script's `show` and relays the result; it changes nothing and runs no test. Without arguments it summarises the record and lists the other forms of the command, `show items [state]` lists the items, of one state or all, and `show runs` lists the analysis runs, with their versions, and the measurements; without a record it says there is none and lists the same forms.

`prune` runs the dry run, shows it, and removes only after the user confirms in the conversation. Its arguments name the selection: measurements before a date, all but the last N measurements, obsolete items, and items that landed before a date. Main passes the confirmed dry run's version with the same selection, so only what the user saw is removed; on `changed`, main shows a new dry run instead and removes nothing until the user confirms it. Undecided, picked and declined items are never selected, and there is no reset of the whole record.
