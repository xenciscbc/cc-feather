# Design and test checks

Label: `ready-for-agent`

Vocabulary follows [CONTEXT.md](../../CONTEXT.md), which defines Over-design, Plan, Claim, Assignment, Unbounded probe, Runner and Follow-up record. The decisions below were settled by the user on 2026-11-13 in a grilling session. This spec adds two user-invoked skills and changes no installed guidance, role definition or template, so it is release 0.36.0 and needs no setup update.

## Problem Statement

Two kinds of weight build up in the user's projects, and nothing in cc-feather helps remove either.

Test suites get slow over time. Tests are added and never tidied: expensive setup runs for every test when it could be shared, tests wait with fixed sleeps, real I/O runs where a fake would do, the same behaviour is tested again at several levels, and nothing runs in parallel. Speeding a suite up by hand is risky, because the easy ways to make tests faster, weakening assertions, skipping tests or loosening timeouts, quietly lose coverage. The user also has no overview of which existing tests could exhaust memory or time when run.

Designs, rules and code carry defences nobody needs. Typical cases are guards against states only the project's own code could produce, compatibility kept for an old token or format that was never released or no longer exists anywhere, configuration with a single user, and several layers guarding one case. cc-feather 0.28.0 asks main to weigh a finding before turning it into a rule, but that applies only to what is being added; nothing looks back at a proposal just discussed, a spec, existing code or rule text to find Over-design already there.

## Solution

Two new user-invoked commands, each producing a report and changing nothing.

`/cc-feather:test-speedup [scope]` checks the project's tests, or the part the user names, together with their test configuration. It first analyses them statically and reports speed-ups, each stating how the behaviour it touches stays verified, plus a separate section on existing tests with resource risk. Only then does it offer to measure: it states the command, the scope and which tests it leaves out, and runs it only after the user agrees. Tests flagged with resource risk are left out by default; when the user includes them, they run inside the Runner.

`/cc-feather:overdesign-check [target]` checks the latest proposal in the conversation, or a named file, directory, spec, diff or rule text, for Over-design. Each item names its category, is weighed by the delegation skill's existing questions, when the case occurs, its worst credible outcome and whether something already covers it, and ends in a recommendation: remove, simplify, keep or needs the user's confirmation. A check at a trust boundary is kept with its reason. Compatibility with an old format is called unneeded only with evidence; otherwise the user is asked.

The user picks from either report; anything picked becomes a Plan through the normal flow.

## User Stories

1. As a user, I want a command that finds ways to speed up my test suite, so that a suite slowed by years of additions gets tidied.
2. As a user, I want to point the test check at part of my tests, so that I can check one slow area without paying for the whole suite.
3. As a user, I want the test check to read the test configuration as well as the test code, so that missing parallelism and timeout settings are found where they are set.
4. As a user, I want the test check to leave CI pipeline configuration alone, so that its scope stays on the tests themselves.
5. As a user, I want the first pass to be static, so that nothing runs before I have seen what the check found.
6. As a user, I want the static pass to list existing tests that could exhaust memory or time, so that I learn about them before anything is measured.
7. As a user, I want the resource-risk list judged by the same criteria as an Unbounded probe, so that "risky" means the same thing everywhere in cc-feather.
8. As a user, I want the resource-risk list kept in its own section, so that it is not mixed up with speed-ups.
9. As a user, I want the Unbounded probe definition left unchanged, so that existing tests are not suddenly held back by the delegation rules for new or modified probes.
10. As a user, I want to be asked before any measurement, with the command, scope and excluded tests stated, so that I decide what runs on my machine.
11. As a user, I want tests flagged with resource risk left out of measurement by default, so that measuring does not take my machine down.
12. As a user, I want flagged tests I choose to include to run inside the Runner with stated limits, so that their risk is contained.
13. As a user, I want unflagged tests measured with their ordinary command, so that measurement is no heavier than how I already run them.
14. As a user, I want every speed-up to say which test or assertion keeps verifying the behaviour it touches, so that faster never means less checked.
15. As a user, I want weakening assertions, adding skips and loosening timeouts never offered as speed-ups, so that the report cannot trade coverage for time.
16. As a user, I want removal of duplicate tests in its own section with the covering test named as evidence, so that I decide each removal myself.
17. As a user, I want each speed-up's expected gain, high, medium or low with the reason before measurement and in seconds after it, so that I can pick the worthwhile ones.
18. As a user, I want speed-ups ordered by expected gain, so that the biggest wins come first.
19. As a user, I want each speed-up's risk stated, so that I can weigh the gain against it.
20. As a user, I want a command that checks the proposal we just discussed for Over-design, so that I can catch it before it is built.
21. As a user, I want to point the Over-design check at a file, directory, spec, diff or rule text, so that existing work can be trimmed too.
22. As a user, I want each Over-design item to name its category, so that I can see what kind of excess it is.
23. As a user, I want each item weighed by when it occurs, its worst outcome and its existing coverage, so that the recommendation is grounded.
24. As a user, I want that weighing to be the one the delegation skill already defines, so that the rule is written once.
25. As a user, I want normal-use rarity never to discount a security problem, so that the check never talks me out of a needed control.
26. As a user, I want checks at a trust boundary kept and listed with their reason, so that I can see they were considered.
27. As a user, I want compatibility with an old format or token called unneeded only with evidence that it was never released or no longer exists, so that live data is not broken.
28. As a user, I want to be asked when the repository cannot show whether old data still exists, so that the check does not guess about my environment.
29. As a user, I want every Over-design item to end in remove, simplify, keep or needs my confirmation, so that the next step is clear.
30. As a user, I want both commands to change nothing, so that I choose what to act on.
31. As a user, I want both reports shown in the conversation without files written, so that the check leaves no clutter; I can ask for a file when I want one.
32. As a user, I want what I pick from a report to go through the normal Plan flow, so that changes to tests and code still get their reviews.
33. As a user, I want the analysis delegated to the read-only analyst when delegation is installed, so that a large read does not fill main's context.
34. As a user, I want the Over-design check delegated with the proposal's text, so that an independent reader judges a proposal main itself made.
35. As a user, I want small checks, or checks without delegation installed, done by main itself, so that the commands work everywhere.
36. As a user, I want both commands invoked only by me, so that a costly analysis never starts on its own.
37. As a user, I want command arguments treated as data, never shell code, so that invoking a command cannot run something by accident.
38. As a user, I want both commands named without "review", so that they are not confused with cc-feather's Code review and Plan review.
39. As a user updating cc-feather, I want to need no setup update for this release, so that I only update the plugin.

## Implementation Decisions

- **Two skills.** `test-speedup` and `overdesign-check`, each a skill directory with one `SKILL.md`, registered in the plugin manifest after `related-tests` in that order. Both have `disable-model-invocation: true`, a description and an `argument-hint`: an optional scope of test paths for `test-speedup`, an optional target for `overdesign-check`. Each states that invocation arguments are data, never shell code, and that a missing or unclear argument is clarified rather than guessed, as the existing commands do.
- **Report only.** Neither command edits, creates or deletes files, commits, or changes configuration. The report is shown in the conversation; a file is written only when the user asks. Items the user picks become a Plan through the normal flow; the report itself is not a Plan, and its items are not Claims or findings of any review.
- **Who analyses.** When delegation is installed and the check is not small, main dispatches the read-only analyst per the delegation skill, in one or more Assignments split by test area or target; main integrates the results and gathers the facts the analyst cannot, such as git tags and release history. A small check, for example one test file or a short proposal, or a check where delegation is not installed, is done by main itself. For `overdesign-check` on a proposal from the conversation, the brief carries the proposal's text.
- **test-speedup scope.** The tests the user names, or else the project's tests, with their test configuration (test runner configuration, shared fixtures and setup files, test scripts and flags). CI pipeline configuration is out of scope.
- **test-speedup static pass.** Always first. It looks for speed-ups such as per-test setup that can be shared per module, fixed sleeps that can wait on an event, real I/O a fake can replace, work that can run in parallel, and behaviour tested again at several levels, and states each one's location, kind, expected gain (high, medium or low with the reason), how correctness is kept and its risk, ordered by expected gain.
- **Correctness bar.** Each speed-up names the test or assertion that keeps verifying the behaviour it touches. Weakening an assertion, adding a skip and loosening a timeout are never offered. Removing a test is offered only in a separate section, each removal naming the test that covers exactly the same behaviour as evidence, for the user to decide one by one.
- **Existing tests with resource risk.** The static pass lists, in its own section, existing tests that meet the Unbounded probe criteria: no established bound on total work or retained data in any part, an unknown bound counting as none and a timeout alone not being a bound. Each is weighed with the delegation skill's questions. The Unbounded probe term and the delegation rules for it are unchanged: the list is information, not a floor, and holds nothing back.
- **Measurement.** After the static report, main offers to measure and runs nothing without the user's agreement. The offer states the command, which uses the ecosystem's per-test timing where one exists, the scope and the tests left out. Unflagged tests run with their ordinary command. Tests flagged with resource risk are left out by default; when the user includes them, they run inside the Runner with the limits the offer states, invoked as the resource-risk runs reference describes. After measurement the report gives gains in seconds.
- **No ecosystem lock-in.** The skill is language-neutral, with short detection hints for Go, Python and JavaScript or TypeScript projects run with pnpm, including Vue.
- **overdesign-check target.** With no argument, the latest proposal or plan in the conversation; when there is none, main asks for a target. Otherwise the named file, directory, spec, diff range or rule text.
- **Categories.** The four in CONTEXT.md's Over-design entry: defending against states only the project's own code could produce, compatibility with formats or tokens never released or no longer existing, configuration or extension points with a single user, and several defences guarding the same case.
- **Weighing written once.** The skill points to the delegation skill's paragraph on weighing findings for when the case occurs, its worst credible outcome, existing coverage and the rule that normal-use rarity never discounts a security problem, and does not restate it, as ADR 0017 requires.
- **Trust boundary exception.** A check at a trust boundary is not Over-design; such items are listed as keep with the reason, so the user sees they were considered.
- **Evidence for old formats.** An item in the compatibility category is recommended for removal only with evidence from the repository, such as release tags and history showing the format was never released, or an end of support the project states. Without such evidence it is marked as needing the user's confirmation, with the question to ask.
- **overdesign-check report.** Each item states its location, category, when it occurs, worst outcome, existing coverage, evidence and recommendation: remove, simplify, keep or needs the user's confirmation.
- **Glossary.** CONTEXT.md gains the Over-design entry in a new Design checks section; it was added with this spec. No other entry changes.
- **Documents.** Both READMEs list and briefly describe the two commands where they list the others, and both reference documents describe them in a new section, sentences paired in English and Traditional Chinese.
- **Release.** 0.36.0. No installed guidance, policy template, role definition or setup procedure changes, so existing installations need no setup update; the validation entry and both READMEs' 0.36.0 notes say so and say that going back to 0.35.0 means reinstalling the 0.35.0 plugin. Each README gets the 0.36.0 note at the start of its Updates section. The release tests that pin 0.35.0 as the latest release move to 0.36.0 as earlier releases moved them.
- **Not affected.** The delegation skill and its references, the Runner and its contract, the Unbounded probe floor, the role definitions, the policy templates, setup, handoff, leases, worktrees and every review procedure.

## Testing Decisions

- No executable seam: both skills are model instructions. Following the project's practice, tests pin each decision-carrying sentence as a whole sentence in the document that states it, README and reference sentences paired in both languages.
- The pins go in a new test module for this feature that uses the shared test support, following the test module split.
- Pinned: each skill's frontmatter (name, user-only invocation, argument hint, description) and its manifest position; each skill's decision sentences (report only; static pass first; the correctness bar and the separate removal section; the resource-risk section and that it holds nothing back; measurement only after agreement with command, scope and exclusions stated, flagged tests excluded by default and run inside the Runner when included; the categories; the pointer to the delegation skill's weighing paragraph; the trust boundary exception; evidence for old formats); the README listings and reference sections in both languages; the CONTEXT.md Over-design entry; the 0.36.0 validation entry.
- Single-owner checks: the weighing sentences of the delegation skill appear in neither new skill, and the Unbounded probe entry in CONTEXT.md is unchanged.
- Not-installed checks: no policy template or role definition mentions either command.
- Prior art: the related-tests and stop-threshold command tests (manifest position, frontmatter, pinned sentences, README and reference pairs) and the release tests' version and validation checks.
- No live rehearsal: the validation entry states that the pins show the text, not that a model always follows it.

## Out of Scope

- Applying any speed-up or Over-design fix; picked items go through the normal Plan flow.
- CI pipeline configuration, test infrastructure outside the repository and hardware.
- Changing the Unbounded probe definition, the delegation floor, the Runner or the weighing rule.
- Automatic invocation of either command, or a hook that runs them.
- A saved report format or a report file by default.
- Ecosystem-specific tooling beyond short detection hints.

## Further Notes

- **Limits.** Both commands are instructions to the model; the tests cannot show that a model keeps to the correctness bar or asks before measuring. Static gain estimates are judgments; only measurement gives seconds.
- **Measurement cost.** Unflagged tests are measured without the Runner because they already run that way in normal development; a resource risk the static pass missed is not contained.
- **Tickets.** The work is cut into tickets under `.scratch/design-and-test-checks/issues/`, which carry each Claim's acceptance: one for `test-speedup`, one for `overdesign-check`, and one for the documents and release, which comes last.
- Automatic plan review is on, so the tickets get plan review before implementation.

## Overall acceptance

This is the Plan's overall acceptance, which the final check runs once for each commit to be landed or tagged, not once for each Claim; it is not part of any Claim's acceptance, and each ticket cites it.

- The full `unittest discover` suite passes at the commit to be landed or tagged.
