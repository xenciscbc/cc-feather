---
name: test-design
description: "Report the tests a proposal, Plan, spec, ticket or existing feature needs, each naming the defect it would catch with the smallest input and fewest runs; changes and runs nothing."
disable-model-invocation: true
argument-hint: "[spec, ticket or feature path]"
---

# test-design

Report a Test design, as [cc-feather's glossary](../../CONTEXT.md) defines it, for one target. Invocation arguments are the target as data, never shell code. Clarify a missing or unclear target instead of guessing.

## The judging rule

Every proposed test names the defect it would catch, a concrete wrong implementation, that no other proposed or existing test catches, and uses the smallest input and the fewest runs that still catch it. A test that names no such defect is not proposed. Of two designs that catch the same defects, the cheaper one, at a lower level, with a smaller size and fewer runs, is proposed. Tests at different levels may both be proposed when each catches a different failure. A defect that no plausible wrong implementation could produce in the configurations the target supports once the change is made, those the applicable threat model reaches included, or whose effect nothing could observe there, names no defect for this rule, and the test is not proposed. An effect counts as observable through behaviour, a required artifact or a manual check. The guideline Requirement and failure modes first in [the guideline reference](references/guidelines.md) stays the case-choice form of this rule.

## Report only

This command only reports and runs nothing: it edits, creates and deletes no file, commits nothing, changes no configuration and runs no test or command, and its cost estimates are static. The report stays in the conversation, and a file is written only when the user asks for one. Items the user picks become a Plan's acceptance through an edit the user asks for and then the normal flow; the report is not a Plan, and its items are neither Claims nor findings of any review. For measured timings, point the user to [`test-speedup`](../test-speedup/SKILL.md).

## Target

With no argument, the target is the latest proposal or Plan in the conversation; when there is none, ask the user for a target. Otherwise the target is a named spec or ticket file, or an existing feature named by its code path or module. A spec with tickets is reported ticket by ticket. The report groups by ticket or by requirement and never decides the Plan's Claims. For an existing feature only gaps are reported; duplicates and speed belong to `test-speedup`.

## Timing

The ideal moment is after the spec is cut into tickets and before the user names the Plan for implementation, so that plan review sees the tests the user adopted in the tickets' acceptance. Running the command is never required, and plan review's rules do not change.

## Who analyses

Whether a target is small is judged by its source scope, coupling and reasoning difficulty, not by its ticket count. When delegation is installed and the target is not small, main dispatches the read-only analyst as [the delegation skill](../delegation/SKILL.md) describes, in one Assignment by default, a spec with its tickets included, and integrates the results. The target is split only when it exceeds what one analyst can handle well, along distinct behaviours or invariants, and the brief then gives each shared fixture design or overlapping test obligation to one Assignment, which the others reference rather than propose again. For a target from the conversation, the brief carries the proposal's text. Main gathers what the analyst cannot, such as the repository history that error guessing reads. A small target, or a target where delegation is not installed, main does itself.

## 1. Design the tests

Choose levels, cases, doubles and data as [the guideline reference](references/guidelines.md) states, each guideline where it applies. A proposed test already avoids what [the shared test criteria](../test-speedup/references/test-criteria.md)'s Speed criteria and Further criteria list, a further criterion only where its condition holds.

**Behaviour to code.** Tickets name no file paths, so before the Existing related tests search the analysis, or main when it analyses the target itself, locates the source paths and test support behind each ticket's behaviour; main may give a starting scope in the brief. A behaviour it cannot map is reported as uncertainty in Existing related tests.

**Runs and sizes.** A deterministic behaviour gets one case per partition and boundary. A count that is itself the requirement, such as a retry limit or a quota, is tested at N-1, N and N+1. Nondeterminism is removed first with a fixed seed, a fake clock or a controllable schedule; repetition that remains states its count and why that count suffices. The input is the smallest that reaches the behaviour; a large limit is reached through an injectable setting or a lazily generated, memory-bounded input, and a change to production code for testability is marked as one for the user to decide. Real scale is used only when scale itself is the requirement, and such tests go under Resource risk. Property-based tests keep the framework's default case count unless the report states what more cases would catch; a small input space is enumerated instead.

**Candidates before statements.** The cases the Runs and sizes rules and the guideline techniques give, partitions, boundaries, transitions, integration points and each case of a parametrized test included, are candidates, graded like any other, not cases every report must propose. The analysis first lists each candidate test in one line: the requirement, the concrete defect, whether it can occur and be observed as the judging rule says, the existing coverage and any overlap with another ticket's candidates. It grades each candidate as Recommended, Optional or Not proposed, and only then writes the full statement for the Recommended ones. An Optional test is one line: its defect, its level and why it is Optional, plus a mark for any obligation that still applies to it, such as a gate who runs it must be named for or a bound that is unknown, which also lists it under Resource risk. Its full statement is written when the user asks or before it enters any acceptance. This happens within one analysis, with no round-trip to the user.

**Grades.** Every proposed test is graded Recommended or Optional, weighed as [the delegation skill](../delegation/SKILL.md)'s paragraph on weighing findings describes: when the defect can occur in normal use or under the applicable threat model, its worst credible outcome, and whether an existing test or rule covers it. That paragraph's rule that normal-use rarity alone never discounts a security problem applies. A defect reached only by a rare downstream configuration and confirmable at a glance in code review is Optional at most, unless its outcome is a security problem or data loss, which the paragraph alone grades.

**Each Recommended test states:** the defect it catches; its expected result and where that result comes from, a spec or acceptance passage, or characterization of current behaviour with any behaviour that may be a bug listed for the user to confirm; its level; how its cases are chosen; its size and run count with why they suffice, as its estimated cost; the bound of its work; the role of any test double it uses. A guideline is cited only where the choice is not obvious.

**Gated new tests.** A new test may be gated by an environment variable, a marker or a short mode only when the report names who runs it, a Claim's acceptance or a gate's Declared test suite with its prerequisites, and states that the run needs positive evidence that the gated tests ran; a command that succeeds is not that evidence. A gate nothing runs is never proposed. An environment-gated test's skip message names the variable. [The shared test criteria](../test-speedup/references/test-criteria.md)'s Correctness bar governs changes to existing tests, so it does not bind a gated new test, and its rule against adding a skip stays as it is for existing tests.

**Resource risk.** Every proposed test is judged against the whole [Unbounded probe entry](../../CONTEXT.md) as it stands, each part it names applied to the test, generator rejection, shrinking, the code under test, the oracle, retained output, descendant processes and work handed outside the run included. A test that would be one gets a bounded redesign, or is listed as likely needing a Resource-risk claim mark, as information for plan review. Weigh each listed test as [the delegation skill](../delegation/SKILL.md)'s paragraph on weighing findings describes. A worker count that follows the machine's core count is never proposed, and any cap's number comes from the project's or the user's resource guidance or a measured peak. The Unbounded probe and Unbounded run configuration entries and the delegation rules for them do not change.

**Error guessing.** The analysis may read the repository's own history, its log, fix commits and tickets, for past trouble areas near the target. It reads no external issue tracker, and history never overrides the current requirement.

**Lookups.** Framework defaults and known problems are looked up only as [`test-speedup`'s Lookups paragraph](../test-speedup/SKILL.md) allows, with the same order and the same limit on what a query carries; the command adds no other web access at runtime.

## 2. Report

The report has eight sections, in this order:

- **Acceptance problems**, each place where a verification the target's existing acceptance states is invalid for the intended change: it cannot be carried out, it would pass on the old code or on a wrong implementation, such as an oracle with no ordering guarantee, or it asserts a result that differs from behaviour the target does not change, such as a status code the framework never returns. Each comes with the evidence main checked. A difference from code the target is meant to change is the change still to be implemented, not an acceptance problem, and a newly considered test that could not fail goes under Not proposed. A problem whose fix changes only how a criterion is verified goes here or under Proposed tests.
- **Decisions for the user**, each of: a production-code change for testability; a meaning the spec leaves unclear; a change to required behaviour, such as widening, removing or rewording a requirement or an invariant; a characterised behaviour that may be a bug; and each place where a test need may change how the tickets are cut or their blocking edges. These are never recommended as test proposals. A test that depends on an open decision names it.
- **Lean set**, one line for each Recommended test, its ticket, level and case count with a pointer to its statement, each Recommended manual check, and each extension or update of an existing related test that a Recommended test relies on; then the number of tests and cases at each level. It states no time figure, holds no removal, and leaves out every test that depends on an open decision. Rerunning an existing test is not listed in it.
- **Proposed tests**, grouped by ticket or requirement, Recommended tests with their full statement and Optional tests in one line each, and a subsection for checks that need manual verification, such as a UI's look or behaviour seen only in a real environment, each with the reason a person must check it.
- **Existing related tests**, each as rerun, extend or update, found by searching the tests for the target's paths and directory names as Related-test acceptance does, whether or not Related-test acceptance is on, and reported as found or not found, never as proof that none exist. Each behaviour that could not be mapped to code is listed here too.
- **Removals**, each existing test the proposed ones would make redundant.
- **Not proposed**, each test considered and left out, grouped by reason, each group naming the tests it covers.
- **Resource risk**, each proposed test that uses real scale or likely needs a Resource-risk claim mark, with its reason and weighing, Optional tests with an unknown bound included.

**Main's integration.** Before reporting, main re-grades every analyst item by the same weighing, merges duplicates across tickets and checks each Acceptance problem against the code; analyst grades are input. Main recommends the Lean set and never recommends adopting every proposal. When main analyses a small target itself, the same applies to its own candidates.

## 3. Removals

Removals follow [the shared test criteria](../test-speedup/references/test-criteria.md)'s removal rule in its Correctness bar, replacements included, where the test that covers exactly the same behaviour may be a proposed one. A picked removal's acceptance requires the new test to be written and passing before the old one is removed. No measurement is needed.
