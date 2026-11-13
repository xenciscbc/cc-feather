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
- behaviour tested again at several levels.

Detection hints: Go tests run with `go test`, where `t.Parallel()`, `TestMain` and `-run`/`-count` flags matter; Python tests with pytest or unittest, where fixture scope, `conftest.py` and pytest-xdist matter; JavaScript or TypeScript tests run with pnpm, Vue included, where the vitest or jest configuration, its pool and isolation settings and the `package.json` test scripts matter.

**Correctness bar.** Each speed-up names the test or assertion that keeps verifying the behaviour it touches. A speed-up keeps every assertion, test and timeout at least as strict as it is now: weakening an assertion, adding a skip or loosening a timeout is never offered. Removing a test is offered only in the Removals section, each removal naming the test that covers exactly the same behaviour as evidence, for the user to decide one by one.

**Existing tests with resource risk.** In a section of its own, list the existing tests that meet the criteria of an Unbounded probe in [cc-feather's glossary](../../CONTEXT.md), applied without a budget since the static pass runs nothing. Weigh each one as [the delegation skill](../delegation/SKILL.md)'s paragraph on weighing findings describes. The list is information: it holds nothing back, and the Unbounded probe term and the delegation rules for it are unchanged.

## 2. Report

The report has three sections:

- **Speed-ups**, ordered by expected gain, each with its location, kind, expected gain (high, medium or low, with the reason), how correctness is kept and its risk.
- **Removals**, each with the covering test as evidence.
- **Existing tests with resource risk**, each with its reason and weighing.

## 3. Measurement

After the static report, main offers to measure and runs nothing without the user's agreement. The offer states the command, using the ecosystem's per-test timing where one exists, the scope and the tests it leaves out. Tests listed with resource risk are left out by default. Unflagged tests run with their ordinary command. A flagged test the user includes runs inside the Runner, with the memory, time and output limits the offer states. For the Runner's path and invocation, read [the resource-risk runs reference](../delegation/references/resource-risk-runs.md)'s The Runner, where the path is relative to the delegation skill, and for how a contained, refused or evidence-missing result is judged, its Main's floor. After measurement, the report gives each speed-up's gain in seconds.
