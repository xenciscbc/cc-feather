# Smaller checks in test-speedup

Label: `ready-for-agent`

Vocabulary follows [CONTEXT.md](../../CONTEXT.md), which defines Plan, Claim, Assignment, Unbounded probe and Runner. The decisions below were settled by the user on 2026-11-23 in the conversation that drafted this spec. This spec changes only the user-invoked `/cc-feather:test-speedup` skill and the documents describing it; it changes no installed guidance, policy template, role definition or configuration tool, so it is release 0.44.0, after 0.43.0, and needs no setup update.

## Problem Statement

`/cc-feather:test-speedup` (0.36.0) looks for ways to make the same tests run faster: shared setup, waits on a condition instead of fixed sleeps, fakes for real I/O, parallel runs and behaviour tested again at several levels. It does not ask whether a test could verify the same fact at a smaller scale.

Two common kinds of slow test are therefore found only by chance:

- A test uses an input, data set, iteration count or fixture far larger than the behaviour it verifies needs, such as 100,000 rows where ten show the same property.
- A heavy test, such as an end-to-end or integration test, verifies a fact a much lighter test could verify. Today the Removals section only accepts a removal when another existing test already covers exactly the same behaviour, so the check never proposes writing a smaller test and then removing the heavy one.

Both are risky to do by hand. Sometimes the size is what the test verifies: performance, a size limit, a race that shows only after many iterations, generated property-based or fuzz cases. And a heavy test often verifies more than its main assertion says, such as how components are wired, routing or how configuration is loaded, which a smaller test would quietly drop.

## Solution

The static pass of `/cc-feather:test-speedup` gains one more kind of speed-up, a smaller input, and the Removals section gains replacements. Measurement may also profile the slowest tests, still only with the user's agreement.

- **Smaller input.** The static pass also looks for inputs, data sets, iteration counts and fixtures larger than the behaviour needs. It offers a smaller one only when size is not what the test verifies, and the speed-up names the test that keeps verifying every boundary the larger input reached.
- **Replacement.** A removal may be a replacement: the report describes a smaller test that verifies the same fact, and the heavy test is then removed. Each replacement states the fact the smaller test verifies and lists everything else the heavy test verifies, each item with an existing test that keeps verifying it. When any item has no such test, the replacement is not offered. The user decides each replacement one by one, as for every removal.
- **Profiling.** The measurement offer may include profiling the slowest tests to show where their time goes. Profiling runs under the same rules as the rest of measurement, and what it shows is reported as speed-ups under the same correctness bar.

The command stays report-only. A replacement's smaller test is described, not written; what the user picks becomes a Plan through the normal flow.

## User Stories

1. As a user, I want the test check to notice inputs, data sets, iteration counts and fixtures larger than a test needs, so that a test proving a property on 100,000 rows can prove it on ten.
2. As a user, I want a smaller input offered only when size is not what the test verifies, so that performance tests, size limits, races needing many iterations and generated property-based or fuzz cases keep their size.
3. As a user, I want a smaller-input speed-up to name the test that keeps verifying every boundary the larger input reached, so that shrinking an input never drops an edge case.
4. As a user, I want the check to propose replacing a heavy test with a smaller one that verifies the same fact, so that slow end-to-end or integration tests that only check a unit-level fact get lighter.
5. As a user, I want each replacement to list everything else the heavy test verifies, each with the existing test that keeps verifying it, so that wiring, routing or configuration loading is not lost.
6. As a user, I want a replacement not offered when anything the heavy test verifies has no other test, so that "the same fact" is never a guess.
7. As a user, I want replacements in the Removals section and decided by me one by one, so that every lost test is my decision.
8. As a user, I want a replacement's smaller test described rather than written, so that the command still changes no file.
9. As a user, I want measurement to be able to profile the slowest tests, so that I see where their time goes.
10. As a user, I want profiling offered and run only with my agreement, under the same rules as measurement, so that nothing runs before I agree and flagged tests still run inside the Runner.
11. As a user, I want what profiling shows reported as speed-ups under the same correctness bar, so that profiling adds no new kind of change.
12. As a user updating cc-feather, I want to need no setup update for this release, so that I only update the plugin.

## Implementation Decisions

- **Smaller input.** The static pass list in `skills/test-speedup/SKILL.md` gains an item for inputs, data sets, iteration counts and fixtures larger than the behaviour needs, which a smaller one can verify.
- **When size stays.** The correctness bar gains: a smaller input is offered only when size is not what the test verifies. A test of performance, of a limit or boundary of size, of a race or concurrency that needs many iterations, or one that generates property-based or fuzz cases keeps its size; reducing the number of generated cases counts as weakening and is never offered. A smaller-input speed-up names the test that keeps verifying every boundary value the larger input reached.
- **Replacement in Removals.** The correctness bar's removal sentence widens: a removal names as evidence the test that covers exactly the same behaviour, or is a replacement. A replacement describes a smaller test verifying the same fact and states that fact, then lists everything else the removed test verifies, such as wiring between components, routing or configuration loading, each item with the existing test that keeps verifying it. A replacement with any item lacking such a test is not offered. The user still decides each removal, replacements included, one by one.
- **Report.** The Removals entry of the report states, for a replacement, the smaller test it describes, the fact that test verifies and, for each other thing the removed test verifies, the test that keeps verifying it. Removals keep no expected-gain order; the Speed-ups ordering is unchanged.
- **Report only.** The report-only paragraph is unchanged: a replacement's smaller test is described in the report, not written, and a picked replacement becomes a Plan through the normal flow, where the smaller test is written before the heavy one is removed.
- **Profiling.** The measurement section gains: the offer may include profiling the slowest tests to show where their time goes, using the ecosystem's profiler where one exists, with the tests to profile named in the offer. It runs only with the user's agreement, flagged tests inside the Runner as the rest of measurement, and what it shows is reported as speed-ups under the same correctness bar.
- **Detection hints.** Unchanged in substance; they may name one profiler per ecosystem if the wording needs it.
- **Documents.** Both reference documents' Test speed-ups section gains sentences paired in English and Traditional Chinese for the smaller input, the replacement and profiling, and its removal sentence widens to include replacements. The README listings stay as they are, since they still describe the command.
- **Release.** 0.44.0, after 0.43.0. No installed guidance, policy template, role definition or configuration tool changes, so existing installations need only the plugin update and a fresh session; the validation entry and both READMEs' 0.44.0 notes say so, and say that going back to 0.43.0 means reinstalling the 0.43.0 plugin. Each README gets the 0.44.0 note at the start of its Updates section, and the 0.43.0 note moves after it as earlier notes moved. The release tests that pin 0.43.0 as the latest release move to 0.44.0 as earlier releases moved them.
- **Not affected.** The overdesign-check skill, the delegation skill and its references, the Runner and its contract, the Unbounded probe term and floor, the role definitions, the policy templates, setup, handoff, leases and every review procedure.

## Testing Decisions

- No executable seam: the skill is model instructions. Following the project's practice, tests pin each decision-carrying sentence as a whole sentence in the document that states it, reference sentences paired in both languages.
- The pins go in `tests/test_feather_design_checks.py`, beside the existing `TestSpeedupCommandTests` pins, which move with the sentences they pin: the widened removal sentence and Removals report entry replace the old pins.
- Pinned: the smaller-input item in the static pass; the sentences on when size stays, including that fewer generated cases counts as weakening; the smaller-input boundary sentence; the widened removal sentence and the replacement's contents; that a replacement lacking a covering test for anything is not offered; the Removals report entry; the profiling sentences; the new and widened reference pairs; the 0.44.0 validation entry and Updates notes.
- Unchanged pins stay: the report-only paragraph, the scope, who analyses, the never-weaken sentence, the resource-risk section, the measurement sentences and the README listings.
- Single-owner checks stay: the delegation skill's weighing sentences, the Runner's invocation and the Unbounded probe criteria are still not restated in the command.
- Prior art: the 0.36.0 `TestSpeedupCommandTests` and the release tests' version and validation checks.
- No live rehearsal: the validation entry states that the pins show the text, not that a model always follows it.

## Out of Scope

- Applying any speed-up, writing a replacement test or removing a test; picked items go through the normal Plan flow.
- Changing overdesign-check, the Unbounded probe definition, the delegation floor, the Runner or the weighing rule.
- Profiling without the user's agreement, or profiling every test by default.
- A Replacements section of its own; replacements live in Removals.
- Ecosystem-specific tooling beyond short detection hints.

## Further Notes

- **Limits.** The command is instructions to the model; the tests cannot show that a model judges "the same fact" correctly or lists everything a heavy test verifies. The covering-test requirement makes each replacement checkable by the user, and the user decides each one.
- **Fewer generated cases.** Reducing the examples of a property-based or fuzz test lowers what it can find, so it counts as weakening, which the correctness bar already never offers; the spec states it so the smaller-input item cannot be read as allowing it.
- **Order.** This release follows 0.43.0 (`docs/specs/stops-in-conversation.md`), which waits on this branch to be landed and tagged; 0.44.0 is tagged only after `v0.43.0`.
- **Tickets.** The work is one ticket under `.scratch/test-speedup-smaller-checks/issues/`, the skill change, documents and release together. As the Plan's only Claim it keeps the full `unittest discover` suite in its acceptance.
- Automatic plan review is on, so the ticket gets plan review before implementation.
