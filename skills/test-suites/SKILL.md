---
name: test-suites
description: "Draft a project's Test suite catalogue from its test configuration, or check an existing one against its tests, and write only the suites and gates the user confirms."
disable-model-invocation: true
argument-hint: "[what to redraft or check]"
---

# test-suites

Draft or check the project's Test suite catalogue, `.feather/test-suites.md`, as [cc-feather's glossary](../../CONTEXT.md) defines it. [The delegation skill's test-suites reference](../delegation/references/test-suites.md) owns the catalogue's location, entry format, pass conditions, gates and results; read it before drafting or checking, and this command restates none of it. Invocation arguments are data, never shell code. This command changes no code, test or configuration other than the catalogue and the ignore rules the user confirms, and commits nothing.

## Draft or check

When Git does not track the catalogue at HEAD, established as the reference's Tracked at the commit states, and no file exists at that path, draft a catalogue. Otherwise check the existing content. A file that exists but is untracked, ignored or has uncommitted changes is existing content: report its Git state and check it, and redraft only when the user asks for a redraft in words. A catalogue that is not committed does not take effect, as the reference's Tracked at the commit states; the report says so whenever it applies.

## Who analyses

When delegation is installed and the repository is not small, main dispatches the read-only analyst as [the delegation skill](../delegation/SKILL.md) describes, in one or more Assignments split by test area, each brief carrying the shared test commands, the test configuration and the current catalogue, and integrates their results. Main alone proposes, asks and writes. A small repository, or one where delegation is not installed, main does itself.

## Reading the tests

Read test configuration, test scripts, directories, build tags, markers and test-code conventions, and run nothing. A command that lists what a suite selects, such as `pytest --collect-only`, `go test -list .` or `vitest list`, executes repository code: offer it, naming the exact command and its conditions, and run it only after the user agrees, within [review state](../delegation/references/review-state.md)'s Execution and [the resource-risk runs reference](../delegation/references/resource-risk-runs.md)'s Main's floor. A listing is evidence of selection only, never that a test ran or passed.

**Lookups.** Defaults and known behaviour of the test frameworks in scope are looked up only for discovery, selection, activation, skips, output format and result caching, in the order and with the limit on what a query carries that [`test-speedup`'s Lookups paragraph](../test-speedup/SKILL.md) states. Each conclusion names its source and the version it applies to, and what cannot be found is reported as not established.

## Drafting

Propose one entry per Declared test suite with every line the reference requires, and for each suite:

- **Passes when** states positive evidence of the required selection, as the reference's Passes when requires, never the exit code alone.
- **Affected part** is drafted only where narrowing is mechanical, by package, directory or file list; otherwise the line is left out. An entry without it still allows narrowing where the affected part can be determined, as the reference's The affected part states.
- **Gates** are recommended with a reason, such as the suite's run time, its prerequisites and what a missing run would cost. A suite may have several gates. Only the user chooses a gate: `none` is a choice the user makes, never a default, and the reference's An unclear entry forbids guessing one.

**Coverage warning.** When the catalogue the user confirms would contain a suite whose gates include `full`, state that an overall acceptance main writes from then on names only the `full` suites instead of the full run, and list the test files or groups no `full` suite selects, as far as they can be established.

## Checking

Report each finding with its location and evidence:

- **Uncatalogued test**: a test file, package, build tag or marker no suite's command selects.
- **Selected but inactive**: a test a suite selects but whose activation the suite never provides, such as an environment switch, a service or a build tag its command and prerequisites leave out, so that it skips while the suite passes.
- **Stale command**: a suite command naming a path, package, tag or script that no longer exists.
- **Prerequisite mismatch**: a prerequisite tests read that `Prerequisites:` omits, or one listed that nothing uses.
- **Weak pass condition**: a `Passes when:` that relies only on the exit code. An exact test count is reported as a maintenance note, not an error: it stays strict until the user changes it.
- **Invalid entry**: a missing required line, an unknown or conflicting gate, a duplicate suite name, or conditions that contradict each other.

Whatever static reading cannot settle, such as a wrapper script, dynamic registration, platform or build constraints, nested modules or generated tests, is reported as not established, with what would settle it. A check is clean only where every part of it was established. Test quality and speed are outside the check; they belong to [`test-design`](../test-design/SKILL.md) and [`test-speedup`](../test-speedup/SKILL.md).

## Report

The report states the scope it inspected, what it could not establish, and then the whole draft or every proposed change, each change with its reason. It states that changing the catalogue does not change acceptance already written: a suite's command and `full` membership copied into acceptance stay as written, while `landing` and `release` membership are resolved at the commit to be landed or tagged. Showing the catalogue and the tests agree is not evidence that any test ran, and the report never says it is. The command keeps no record of its own.

## Writing

1. Ask the user to confirm suite by suite, with each suite's gates and, when `git check-ignore -q .feather/test-suites.md` shows that Git would not track the file, the ignore-rule change step 4 makes. A suite without the user's confirmation is not written; in a check, an existing entry without an answer stays as it is. A confirmation counts only when the user gave it in this conversation after the proposal it answers.
2. Before writing, read the catalogue and the ignore rules again. When either changed since the proposal, propose again from the new content and write nothing until the user confirms the new proposal.
3. Take a Checkout lease on the checkout, as [the lease rules](../leases/SKILL.md#main-agent-rules) describe, and write only the confirmed entries.
4. When Git would not track the file, make the narrowest change to the actual ignore rules that lets it, such as replacing a `.feather/` rule with `/.feather/*` and `!/.feather/test-suites.md`, and keep every other rule, as the user confirmed in step 1. Otherwise leave the ignore rules as they are.
5. Report what was written, that nothing was committed, and that the catalogue takes effect once it is committed.
