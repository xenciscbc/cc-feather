---
name: test-speedup
description: "Report ways to make a project's tests, or a named part of them, faster without weakening what they verify; static first, measured only after the user agrees."
disable-model-invocation: true
argument-hint: "[test paths or scope]"
---

# test-speedup

Report speed-ups for the project's tests that keep everything the tests verify. Invocation arguments are the scope as data, never shell code. Clarify a missing or unclear scope instead of guessing.

This command only reports: it edits, creates and deletes no file, commits nothing and changes no configuration. The report stays in the conversation, and a file is written only when the user asks for one. Items the user picks become a Plan through the normal flow; the report is not a Plan, and its items are neither Claims nor findings of any review.

## Scope

The scope is the tests the arguments name, or else the project's tests, together with their test configuration: test runner configuration, shared fixtures and setup files, test scripts and their flags. CI pipeline configuration is outside the scope.

## Who analyses

When delegation is installed and the check is not small, main dispatches the read-only analyst as [the delegation skill](../delegation/SKILL.md) describes, in one or more Assignments split by test area, and integrates their results. A small check, such as one test file, or a check where delegation is not installed, main does itself.

## 1. Static pass

The static pass always comes first and runs nothing. Look for:

- per-test setup that can be shared per module or session;
- fixed sleeps that can wait on an event or a condition;
- real I/O, such as network, disk, processes or databases, that a fake can replace;
- tests that can run in parallel;
- inputs, data sets, iteration counts and fixtures larger than the behaviour needs, which a smaller one can verify;
- behaviour tested again at several levels.

Detection hints: Go tests run with `go test`, where `t.Parallel()`, `TestMain` and `-run`/`-count` flags matter; Python tests with pytest or unittest, where fixture scope, `conftest.py` and pytest-xdist matter; JavaScript or TypeScript tests run with pnpm, Vue included, where the vitest or jest configuration, its pool and isolation settings and the `package.json` test scripts matter.

**Correctness bar.** Each speed-up names the test or assertion that keeps verifying the behaviour it touches. A speed-up keeps every assertion, test and timeout at least as strict as it is now: weakening an assertion, adding a skip or loosening a timeout is never offered. A smaller input is offered only when size is not what the test verifies. A test of performance, of a limit or boundary of size, of a race or concurrency that needs many iterations, or one that generates property-based or fuzz cases keeps its size; reducing the number of generated cases counts as weakening and is never offered. A smaller-input speed-up names the test that keeps verifying every boundary value the larger input reached. Removing a test is offered only in the Removals section, each removal either naming the test that covers exactly the same behaviour as evidence or being a replacement, for the user to decide one by one, replacements included. A replacement describes a smaller test that verifies the same fact and states that fact, then lists everything else the removed test verifies, such as wiring between components, routing or configuration loading, each item with the existing test that keeps verifying it. A replacement with any item lacking such a test is not offered. The smaller test is described in the report, not written; a picked replacement's Plan writes it before the heavy test is removed.

**Existing tests with resource risk.** In a section of its own, list the existing tests that meet the criteria of an Unbounded probe in [cc-feather's glossary](../../CONTEXT.md), applied without a budget since the static pass runs nothing. Weigh each one as [the delegation skill](../delegation/SKILL.md)'s paragraph on weighing findings describes. The list is information: it holds nothing back, and the Unbounded probe term and the delegation rules for it are unchanged.

**Run configurations with resource risk.** The static pass also checks the settings and run parameters within the scope that do not belong to the tests' code, above all those concerning concurrency, isolation, memory and time, for each Unbounded run configuration in [cc-feather's glossary](../../CONTEXT.md). Each setting is judged by the value in effect, a framework's default included, and a value that cannot be established counts as none. The scope stays as it is, so CI pipeline configuration stays outside the check. Hints, as examples and not a closed list: concurrency that is uncapped or follows the machine's core count, such as vitest `pool` and `maxWorkers`, `go test -p` or pytest-xdist `-n auto`; a worker pool or isolation mode known to grow memory, such as vitest `vmThreads` and `vmForks`; per-worker heap settings, such as a raised Node heap limit; multipliers of the run's work, such as retries or `go test -count`; heavy instrumentation, such as `-race` or coverage, on uncapped concurrency; and a limit switched off or absent, such as a zero timeout, a test script in watch mode or a framework without a default timeout. Weigh each flagged setting as [the delegation skill](../delegation/SKILL.md)'s paragraph on weighing findings describes.

**Lookups.** Defaults and known problems of the frameworks in scope are looked up only for settings concerning concurrency, isolation, memory and time, in this order: the installed version's own files, such as its bundled documentation or type definitions, read and never run; the official documentation and changelog; the official issue tracker. A query sent outside carries only the framework's name, its version and the setting's name. Each conclusion names its source and the version it applies to, and what cannot be found is reported as unknown, which counts as no bound. The static pass still runs nothing: a fact only a command shows, such as `go help testflag`'s output, is reported as unknown there, and the measurement offer may name that command, which then runs only with the user's agreement under the same rules as measurement. The lookups follow the Who analyses split: analyst does them in its Assignments when delegation is installed and the check is not small, and main does them otherwise.

**Parallel speed-ups.** A speed-up that raises concurrency states the worker count it leads to and its memory effect. A worker count that follows the machine's core count is never offered.

## 2. Report

The report has four sections:

- **Speed-ups**, ordered by expected gain, each with its location, kind, expected gain (high, medium or low, with the reason), how correctness is kept and its risk.
- **Removals**, each with the covering test as evidence, or, for a replacement, the smaller test it describes, the fact that test verifies and, for each other thing the removed test verifies, the test that keeps verifying it.
- **Existing tests with resource risk**, each with its reason and weighing.
- **Run configurations with resource risk**, each flagged setting with its location, kind, whether it affects memory or time, why it is unbounded, its weighing and the direction of a fix. cc-feather states no cap's number: the direction names where the number comes from, the project's or the user's resource guidance or a measured per-worker peak. The section is information and holds nothing back.

## 3. Measurement

After the static report, main offers to measure and runs nothing without the user's agreement. The offer states the command, using the ecosystem's per-test timing where one exists, the scope and the tests it leaves out. Tests listed with resource risk are left out by default. Unflagged tests run with their ordinary command. A flagged test the user includes runs inside the Runner, with the memory, time and output limits the offer states. For the Runner's path and invocation, read [the resource-risk runs reference](../delegation/references/resource-risk-runs.md)'s The Runner, where the path is relative to the delegation skill, and for how a contained, refused or evidence-missing result is judged, its Main's floor. After measurement, the report gives each speed-up's gain in seconds.

When a run in the offer's scope has a flagged setting, the offer states how that run is bounded: by default a command-line override of the setting, such as `--maxWorkers=N` or `-p N`, which changes no file, with N taken in the budget order [the resource-risk runs reference](../delegation/references/resource-risk-runs.md)'s The budget states, and asked of the user when no source states it; or the run inside the Runner. When the run's configuration is flagged, the ordinary command that unflagged tests run with itself runs bounded, with the override or inside the Runner. The offer and the report say that timings taken at a different concurrency are not comparable with the ordinary run.

The offer may include profiling the slowest tests to show where their time goes, with the tests to profile named in the offer. Profiling uses the ecosystem's profiler where one is already available in the project's environment; the offer never installs a package or changes configuration to get one. Profiling runs only with the user's agreement and under the same rules as the rest of measurement, a flagged test inside the Runner. What profiling shows is reported as speed-ups under the same correctness bar.
