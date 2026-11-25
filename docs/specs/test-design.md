# Test design

Label: `ready-for-agent`

Vocabulary follows [CONTEXT.md](../../CONTEXT.md), which defines Test design, Plan, Claim, Assignment, Related-test acceptance, Declared test suite, Unbounded probe, Unbounded run configuration, Runner and Over-design. The decisions below were settled by the user on 2026-11-25 in a grilling session, with a web research pass on industry test-design guidance and a second opinion from Codex whose adopted points are folded in. This spec adds one user-invoked skill, moves part of `test-speedup` into a reference both skills share and adds checks to `test-speedup`'s static pass; it changes no installed guidance, role definition or template, so it is release 0.47.0 and needs no setup update.

## Problem Statement

`/cc-feather:test-speedup` looks at tests that already exist: it measures and checks the tests, their configuration and their environment, and finds what is slow, redundant or risky after the fact. Nothing helps the user decide which tests to write in the first place. When a spec is cut into tickets, each ticket's acceptance names tests, but what those tests should verify, at which level, with which cases, how large their inputs are and how many times they run is left to whoever writes them.

The result is the waste `test-speedup` later has to find: the same fact tested at several levels, inputs far larger than the behaviour needs, a loop of ten thousand runs where ten would prove the same thing, real I/O where a fake would do, tests that can never fail, and tests that are missing for the error paths and boundaries the spec does state. Industry guidance on test design exists, but it is scattered, its sources disagree in places, and none of it is tied to cc-feather's own rules for bounded runs and suite gates.

## Solution

A new user-invoked command, `/cc-feather:test-design [target]`, that reports a Test design for one target and changes nothing. The target is the latest proposal or Plan in the conversation, a named spec or ticket, or an existing feature named by its code path or module.

The report proposes the tests the target needs. Its judging rule is that every proposed test names the defect it would catch, a concrete wrong implementation, that no other proposed or existing test catches, and uses the smallest input and the fewest runs that still catch it. Each proposed test states that defect, its expected result and where that result comes from, its level, how its cases are chosen, its size and number of runs with why they suffice, and the bound of its work. The report also lists the existing tests that already verify part of the target, the checks that need manual verification, the existing tests the proposed ones would make redundant, the proposed tests with resource risk, and notes that may change how the tickets are cut.

The ideal moment is after a spec is cut into tickets and before the user names the Plan for implementation, so that plan review sees the tests the user adopted in the tickets' acceptance. What the user picks enters a ticket's acceptance only through an edit the user asks for.

The speed standards `test-speedup` already applies move into a reference both commands share, so a test the new command proposes already avoids what `test-speedup` would later flag. The shared reference also gains a few checks from the user's own guideline notes, so `test-speedup`'s static pass looks for them too.

## User Stories

1. As a user, I want a command that proposes which tests a spec, ticket or feature needs, so that tests are designed before they are written rather than tidied after.
2. As a user, I want to run it on the latest proposal in the conversation without naming a file, so that I can check a design while we are still discussing it.
3. As a user, I want to run it on a named spec, so that I get proposals for all of its tickets at once.
4. As a user, I want to run it on a single ticket, so that I can check one ticket without paying for the whole spec.
5. As a user, I want to run it on an existing feature named by its code path, so that I can find the tests an old feature is missing.
6. As a user, I want the report grouped by ticket or by requirement, so that I can copy what I pick into the right ticket's acceptance.
7. As a user, I want the report not to decide the Plan's Claims, so that Claims are still decided when I name what to implement.
8. As a user, I want the command to change no file, so that running it is always safe.
9. As a user, I want the command to run nothing, so that it never spends machine resources or touches services.
10. As a user, I want only me to be able to run it, so that it never runs inside plan review or the Automatic flow on its own.
11. As a user, I want what I pick to enter a ticket's acceptance only when I ask for that edit, so that the report never changes a plan behind my back.
12. As a user, I want to know the best moment to run it in the delegation flow, so that plan review checks the tests I adopted.
13. As a user, I want every proposed test to name the defect it would catch, so that no proposed test is one that can never fail.
14. As a user, I want a test that catches nothing another test does not already catch left out, so that the same fact is not tested twice.
15. As a user, I want tests at different levels allowed when each catches a different failure, such as wiring, serialization or configuration, so that removing duplication does not remove real evidence.
16. As a user, I want every proposed test to state its expected result and where it comes from, so that I can check the test against the spec rather than against the code.
17. As a user, I want expected results taken only from the current behaviour of an existing feature marked as characterization, with any behaviour that may be a bug listed for me to confirm, so that a test does not lock a bug in.
18. As a user, I want each behaviour tested at the lowest level that can observe it, so that tests stay fast and point to the place that broke.
19. As a user, I want level ratios used only to spot a bad shape, not as a target, so that a fixed pyramid is not forced on every project.
20. As a user, I want cases chosen from the requirement and its failure modes, such as invalid input, authorization failure, cancellation, recovery and concurrency, so that error paths are not forgotten.
21. As a user, I want equivalence partitions, boundary values, decision tables and state transitions used as tools for choosing cases, so that the case set is small but still complete.
22. As a user, I want three-value boundary analysis used where a wrong comparison or an off-by-one is a real risk and two-value analysis otherwise, so that boundaries cost no more than they need to.
23. As a user, I want code coverage used only to find untested code, not as a threshold, while partition, boundary or transition coverage may still be acceptance, so that coverage numbers do not invite empty tests.
24. As a user, I want a deterministic behaviour tested once per partition and boundary, so that ten thousand identical runs are never proposed.
25. As a user, I want a count that is itself the requirement, such as a retry limit or quota, tested only at its boundary, so that a limit of five is tested with five and six, not with a loop.
26. As a user, I want nondeterminism removed with a fixed seed, a fake clock or a controllable schedule before repetition is proposed, so that a test proves something rather than samples it.
27. As a user, I want any repetition that remains to state its count and why that count suffices, so that I can judge it.
28. As a user, I want the smallest input that reaches the behaviour, such as one row more than a page rather than ten thousand rows, so that tests use little memory and time.
29. As a user, I want a large limit tested through an injectable setting or a lazily generated input, with a production-code change marked as one, so that I decide whether the code changes for testability.
30. As a user, I want real scale used only when scale itself is the requirement, and such tests listed under resource risk, so that heavy tests are deliberate.
31. As a user, I want property-based tests to keep the framework's default case count unless the report states what more cases would catch, so that case counts are not raised by habit.
32. As a user, I want a small input space enumerated instead of sampled, so that a four-value enum gets four cases, not a hundred random ones.
33. As a user, I want the cheaper of two designs that catch the same defects, so that the same evidence costs less.
34. As a user, I want each proposed test's size and run count stated as its estimated cost, so that I can compare designs without running them.
35. As a user, I want test doubles named by their role when a test uses one, so that I know whether state or interaction is checked.
36. As a user, I want real implementations preferred when they are suitable, fakes next, and interaction checks only when the interaction is the requirement, so that tests do not break on every refactor.
37. As a user, I want SQL and data access verified on the same database engine, with fake-data tests kept for the logic after the data arrives, so that dialect, constraint and NULL errors are not missed.
38. As a user, I want writable test data isolated per test while immutable shared fixtures may be shared, so that tests do not interfere and do not pay for needless databases.
39. As a user, I want a controlled local database or subprocess treated as hermetic, so that hermetic is not misread as forbidding every real dependency.
40. As a user, I want the three hard prohibitions for external dependencies, a hard-coded connection string when an environment variable is unset, connecting to production by default and credentials in test files, never proposed, so that no proposal creates those risks.
41. As a user, I want a gated new test proposed only when the report names who runs it, a Claim's acceptance or a gate's Declared test suite, so that a gate nothing runs is never proposed.
42. As a user, I want a gated test's run to require positive evidence that it actually ran, so that a successful command with every test skipped is not taken as a pass.
43. As a user, I want the skip message of an environment-gated test to name the variable that enables it, so that anyone can turn it on.
44. As a user, I want every proposed test to state the bound of its work, so that no proposal is an Unbounded probe.
45. As a user, I want a proposed fuzz or property run judged against the whole Unbounded probe definition, generator rejection and shrinking included, with any cap's number taken from the project's resource guidance or a measurement, so that a cap is not invented.
46. As a user, I want worker counts that follow the machine's core count never proposed, so that a proposal does not exhaust memory on a large machine.
47. As a user, I want a proposed test that may need a Resource-risk claim mark flagged as information, so that plan review can weigh it.
48. As a user, I want the existing tests that already verify part of the target listed as rerun, extend or update, so that I can name them in acceptance.
49. As a user, I want existing related tests found the way Related-test acceptance finds them and reported as found or not found, never as proof that none exist, so that a missed test is not mistaken for a gap.
50. As a user, I want checks only a person can do, such as a UI's look or behaviour seen only in a real environment, proposed as manual verification with the reason, so that they are not silently dropped.
51. As a user, I want the tests deliberately not proposed listed with the reason, so that I see what was considered.
52. As a user, I want existing tests the proposed ones would make redundant listed as removals for me to decide one by one, under the same evidence rule as `test-speedup`, so that duplication is cleaned up without losing coverage.
53. As a user, I want a picked removal to require the new test to be written and passing before the old one is removed, so that coverage never has a gap.
54. As a user, I want notes on where a test need may change how tickets are cut, so that I can recut tickets before plan review.
55. As a user, I want error guessing to draw on the repository's own history of fixes, so that past trouble areas get tests.
56. As a user, I want the command never to send project content outside, so that research on frameworks carries only framework names, versions and setting names.
57. As a user, I want a guideline cited in the report only where a choice is not obvious, so that the report stays short.
58. As a user, I want ecosystem hints for Go, Python and JavaScript or TypeScript, so that proposals use each framework's idioms, such as table-driven tests, parametrize and fake timers.
59. As a user, I want a large target analysed by the read-only analyst and a small one by main, so that the cost fits the target.
60. As a user, I want `test-speedup`'s static pass to also check for the new items, a DOM-less frontend test run in a DOM environment, a fixed port, a wait without a timeout, output collected without a limit and missing cleanup on failure paths, so that both commands share one standard.
61. As a user, I want a test that verifies time itself to keep real elapsed time only when real scheduling or clock integration is the property, so that a fake clock is used wherever it verifies the same logic.
62. As a user, I want `test-speedup`'s existing protections, no added skip, no fewer generated cases, size kept for performance, limit and race tests, unchanged, so that sharing the standard weakens nothing.
63. As a maintainer, I want each shared rule written once and the other command pointing to it, so that the two commands cannot drift apart.
64. As a maintainer, I want the shared reference to point to the resource-risk, suite and review rules rather than copy them, so that their owners stay the only place they are stated.
65. As a maintainer, I want the guideline reference to carry no source labels or citations, so that it stays a working rule set rather than a bibliography.
66. As a maintainer, I want the release notes to say that `test-speedup` gains checks, so that the change in its behaviour is not hidden as a refactor.
67. As a maintainer, I want the new command named without "plan" or "review", so that it is not confused with a Plan, plan review or code review.

## Implementation Decisions

- **One new skill.** `test-design`, a skill directory with its `SKILL.md` and a guideline reference, registered in the plugin manifest after `overdesign-check`. It has `disable-model-invocation: true`, a description and an `argument-hint` for an optional target. It states that invocation arguments are data, never shell code, and that a missing or unclear target is clarified rather than guessed, as the existing commands do.
- **Report only, runs nothing.** The command edits, creates and deletes no file, commits nothing, changes no configuration and runs no test or command; its cost estimates are static. The report stays in the conversation, and a file is written only when the user asks for one. Items the user picks become a Plan's acceptance through an edit the user asks for and then the normal flow; the report is not a Plan, and its items are neither Claims nor findings of any review. For measured timings it points the user to `test-speedup`.
- **Target.** With no argument, the latest proposal or Plan in the conversation; when there is none, the user is asked. Otherwise a named spec or ticket file, or an existing feature named by its code path or module. A spec with tickets is reported ticket by ticket; the report groups by ticket or by requirement and never decides the Plan's Claims. For an existing feature only gaps are reported; duplicates and speed belong to `test-speedup`.
- **Timing.** The command states the ideal moment: after the spec is cut into tickets and before the user names the Plan for implementation. Running it is never required, and plan review's rules do not change.
- **Who analyses.** When delegation is installed and the target is not small, main dispatches the read-only analyst as the delegation skill describes, in one or more Assignments split by ticket or feature area, and integrates their results; main gathers what the analyst cannot, such as repository history for error guessing. A small target, such as one ticket, or a target where delegation is not installed, main does itself.
- **The judging rule.** Stated first in the skill: every proposed test names the defect it would catch, a concrete wrong implementation, that no other proposed or existing test catches, and uses the smallest input and the fewest runs that still catch it. A test that names no such defect is not proposed. Of two designs that catch the same defects, the cheaper one, lower level, smaller size and fewer runs, is proposed. Tests at different levels may both be proposed when each catches a different failure.
- **Runs and sizes.** A deterministic behaviour gets one case per partition and boundary. A count that is itself the requirement is tested at N−1, N and N+1. Nondeterminism is removed first with a fixed seed, a fake clock or a controllable schedule; repetition that remains states its count and why that count suffices. The input is the smallest that reaches the behaviour; a large limit is reached through an injectable setting or a lazily generated, memory-bounded input, and a change to production code for testability is marked as one for the user to decide. Real scale is used only when scale itself is the requirement, and such tests go under resource risk. Property-based tests keep the framework's default case count unless the report states what more cases would catch; a small input space is enumerated instead.
- **Each proposed test states:** the defect it catches; its expected result and where that result comes from, a spec or acceptance passage, or characterization of current behaviour with any behaviour that may be a bug listed for the user to confirm; its level; how its cases are chosen; its size and run count with why they suffice, as its estimated cost; the bound of its work; the role of any test double it uses. A guideline is cited only where the choice is not obvious.
- **Gated new tests.** A new test may be gated by an environment variable, a marker or a short mode only when the report names who runs it, a Claim's acceptance or a gate's Declared test suite with its prerequisites, and states that the run needs positive evidence that the gated tests ran; a command that succeeds is not that evidence. A gate nothing runs is never proposed. An environment-gated test's skip message names the variable. `test-speedup`'s rule against adding a skip to an existing test is unchanged.
- **Resource risk.** Every proposed test is judged against the Unbounded probe entry as it stands, with every part of it, generator rejection, shrinking, the code under test, the oracle, retained output, descendants and external work, and an unknown bound counting as none. A test that would be one gets a bounded redesign, or is listed as likely needing a Resource-risk claim mark, as information for plan review. A worker count that follows the machine's core count is never proposed, and any cap's number comes from the project's or the user's resource guidance or a measured peak. The Unbounded probe and Unbounded run configuration entries and the delegation rules for them do not change.
- **Report sections.** Proposed tests, grouped by ticket or requirement, with a subsection for checks that need manual verification; Existing related tests, as rerun, extend or update, found by searching the tests for the target's paths and directory names as Related-test acceptance does, reported as found or not found and never as proof that none exist, whether or not Related-test acceptance is on; Removals; Not proposed, each with its reason; Resource risk; Ticket-shape notes.
- **Removals.** An existing test the proposed ones would make redundant is listed for the user to decide one by one, under the removal rule in the shared reference: the proposed test that covers exactly the same behaviour, and for everything else the old test verifies, such as wiring, routing or configuration loading, the test that keeps verifying it; with any item lacking one, the removal is not offered. A picked removal's acceptance requires the new test to be written and passing before the old one is removed. No measurement is needed.
- **Error guessing.** The analysis may read the repository's own history, its log, fix commits and tickets, for past trouble areas near the target. It reads no external issue tracker, and history never overrides the current requirement.
- **Lookups.** Framework defaults and known problems are looked up only as `test-speedup`'s lookups already allow, with the same order and the same limit on what a query carries; the command adds no other web access at runtime.
- **Guideline reference.** Bundled with the skill, written once at authoring time from the research and the user's notes, without source labels or citations. Its content, each guideline with when it applies and when it does not:
  - Levels and sizes: the lowest level that can observe the behaviour; scope and size stated, the smallest size preferred; no test that adds no evidence beyond another level's; one focused integration test per integration point, broad tests for a few critical journeys and for risks only an assembled system shows; level ratios only diagnose shape.
  - Case choice: start from the requirement and its failure modes; equivalence partitions with invalid ones; boundary values, three-value where a wrong comparison or off-by-one is a real risk and two-value otherwise, stated as cc-feather's default; decision tables for combined conditions; state transitions, valid transitions first and invalid ones one per case when the risk is high; error guessing; code coverage as a diagnostic only, while technique coverage may be acceptance.
  - Doubles: real implementation when suitable, then a fake, then a stub, interaction checks only when the interaction is the requirement; doubles at awkward boundaries, the clock wrapped; no mocking of types the project does not own where an adapter it owns can stand between; a fake the project maintains is checked against the real implementation.
  - Test quality: observable behaviour through the public interface; one behaviour per test with a name that says it; test bodies straight-line and self-contained while shared test support follows ordinary reuse; independent, repeatable, self-checking tests; hermetic meaning isolated and self-contained, a controlled local dependency included; known causes of nondeterminism designed out.
  - Property-based testing and fuzzing: only with a large input space and a property that holds for all inputs, model-based and postcondition properties preferred; generators and their distribution checked, valid inputs generated rather than filtered; always-run suites use fixed seeds or a corpus, open-ended exploration only in explicit time-boxed runs; a failure found becomes a regression case.
  - Acceptance: each acceptance test traces to a criterion, positive cases then negative ones; a few key examples per rule, with technique-derived cases also proposed for the user to place in acceptance or in a regression set.
  - External dependencies: the same engine for SQL and data access, controlled data allowing exact assertions, live-data comparisons only with a consistent snapshot; a decision order, a disposable same-engine instance first, otherwise a read-only gated smoke test that asserts no changing volumes or values; fake-data tests never replace real-dependency tests, as each layer verifies a different fact; the three hard prohibitions; an environment variable rather than a build tag for gating, since a build tag hides compile errors.
  - Ecosystem hints for Go, Python and JavaScript or TypeScript run with pnpm, Vue included, such as table-driven tests and subtests, fixture scope and parametrize, isolation and fake timers.
- **Shared test criteria.** The speed criteria of `test-speedup`'s static pass, its correctness bar and its removal rule, replacements included, move into one reference in the `test-speedup` skill; `test-speedup` and `test-design` both point to it and neither restates it. The operation-specific conditions stay where they apply: the bar against weakening, skipping, loosening timeouts and reducing generated cases governs changes to existing tests. The reference points to the resource-risk, suite, delegation and review rules and copies none of them.
- **New criteria.** The shared reference gains, each with when it applies: a frontend test that needs no DOM runs without a DOM environment; a test server binds port 0 rather than a fixed port; a wait on a channel, promise or condition has a timeout; collected output has a limit; failure paths clean up goroutines, connections and transactions; a fixed sleep becomes an event or condition wait, or a fake clock where it verifies the same logic, and real elapsed time stays only when real scheduling or clock integration is the property. `test-speedup`'s static pass checks for them as it does for the others.
- **Glossary.** CONTEXT.md gains the Test design entry in its Design checks section; it was added with this spec. No other entry changes.
- **Documents.** Both READMEs list and briefly describe the command where they list the others, and both reference documents describe it in a section after Over-design check's, sentences paired in English and Traditional Chinese. The `test-speedup` reference section states the new checks. The setup document's count of the skills the plugin packages becomes twenty-two, and the tests that pin that count follow it.
- **Release.** 0.47.0. No installed guidance, policy template, role definition or setup procedure changes, so existing installations need no setup update; the validation entry and both READMEs' 0.47.0 notes say so, say that `test-speedup` gains checks, and say that going back to 0.46.0 means reinstalling the 0.46.0 plugin. Each README gets the note at the start of its Updates section. The release tests that pin 0.46.0 as the latest release move to 0.47.0 as earlier releases moved them.
- **Not affected.** The delegation skill and its references, plan review and every review procedure, the Runner and its contract, the Unbounded probe and Unbounded run configuration entries, Related-test acceptance, the Test suite catalogue rules, the role definitions, the policy templates, setup and its procedures (the setup document changes only its count of packaged skills, as Documents states), handoff, leases and worktrees.

## Testing Decisions

- No executable seam: both skills are model instructions. Following the project's practice, tests pin each decision-carrying sentence as a whole sentence in the document that states it, README and reference sentences paired in both languages.
- The pins go in the existing design checks test module, beside the `test-speedup` and `overdesign-check` tests, using the shared test support.
- Pinned for `test-design`: frontmatter (name, user-only invocation, argument hint, description) and manifest position after `overdesign-check`; report only and runs nothing; the target rules and grouping by ticket without deciding Claims; the timing; who analyses; the judging rule; the runs-and-sizes rules; what each proposed test states; gated new tests and positive evidence; the resource-risk rule; the six report sections; removals and their order; error guessing; the lookups pointer.
- Pinned for the guideline reference: one sentence per guideline group, the three hard prohibitions and the absence of source labels.
- Moved pins: the `test-speedup` sentences that move into the shared reference are pinned there instead, with the same wording where the wording does not change; `test-speedup` keeps a pointer to the reference, and a pin checks that neither skill restates the shared criteria.
- Pinned new criteria: each new item and its condition in the shared reference, and the sleep rule's wording.
- Single-owner checks: the Unbounded probe and Unbounded run configuration entries are unchanged, the delegation skill's weighing and resource rules appear in neither skill nor in the shared reference, and the shared reference points to them.
- Glossary: the CONTEXT.md Test design entry.
- Not-installed checks: no policy template or role definition mentions the new command.
- Prior art: the `test-speedup` and `overdesign-check` command tests (manifest position, frontmatter, pinned sentences, linked rules not restated, README and reference pairs, not-installed check) and the release tests' version and validation checks.
- What makes a good test here is the same as for the earlier commands: a pin checks a whole decision sentence where it is stated, not a keyword, and a single-owner check proves a rule is stated once.
- Live rehearsal: the validation entry records a run of the command on one spec with tickets and states that the pins show the text, not that a model always follows it.

## Out of Scope

- Writing any proposed test or editing any acceptance; picked items go through the normal flow.
- Running tests or measuring them; that stays with `test-speedup`.
- Automatic invocation, a hook, or any step of plan review or the Automatic flow that runs the command.
- Changing plan review, Related-test acceptance, the Test suite catalogue, the Unbounded probe definition, the Runner or the weighing rule.
- Web research at runtime beyond `test-speedup`'s existing lookups, and any external issue tracker.
- Source labels, citations or statistics such as flaky-test rates in the guideline reference.
- CI pipeline configuration, test infrastructure outside the repository and hardware.
- A saved report format or a report file by default.

## Further Notes

- **Limits.** The command is instructions to the model; the tests cannot show that a model keeps to the judging rule. Cost estimates are judgments made without running anything.
- **Research.** The guideline reference was condensed from a web research pass on test levels and sizes, test doubles, test quality, case-design techniques, property-based testing and fuzzing, framework guidance and requirements-to-test tracing, and from the user's own notes. The fetch tool returned summaries, so the reference paraphrases and quotes nothing.
- **Tickets.** The work is to be cut into tickets under `.scratch/test-design/issues/`, which carry each Claim's acceptance; the breakdown is confirmed with the user first. A likely cut: the shared test criteria and `test-speedup`'s new checks; the `test-design` skill with its guideline reference; the documents and release, last.
- Automatic plan review is on, so the tickets get plan review before implementation.

## Overall acceptance

This is the Plan's overall acceptance, which the final check runs once for each commit to be landed or tagged, not once for each Claim; it is not part of any Claim's acceptance, and each ticket cites it.

- The full `unittest discover` suite passes at the commit to be landed or tagged.
