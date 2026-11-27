# Test design proposal triage

Label: `ready-for-agent`

Vocabulary follows [CONTEXT.md](../../CONTEXT.md), which defines Test design, Plan, Claim, Assignment, Related-test acceptance, Over-design and Unbounded probe. The decisions below were settled by the user on 2026-11-27 in a grilling session, starting from two field reports of `/cc-feather:test-design` 0.48.0 runs sent by other sessions and with a second opinion from Codex whose adopted points are folded in. This spec changes the `test-design` skill, its guideline reference, the CONTEXT.md Test design entry and the documents; it changes no installed guidance, role definition or template, so it is release 0.49.0 and needs no setup update.

## Problem Statement

Two runs of `/cc-feather:test-design` in different projects on the same day, one on a spec with 10 tickets and three analysts, one on a spec with 3 Security-critical tickets and two analysts, both produced good analysis that was too heavy to act on. The judging rule admits any test that names a defect no other test catches, and almost any wrong implementation can be imagined, so the analysts enumerated: one ticket alone got a 33-case unit table and four integration tests. Main relayed the proposals as a whole, the user answered "as recommended", and only when asked "is this better than the original acceptance?" or "is there anything worth doing without over-design?" did main prune them by hand, to about 10 tests and 18 cases in the second run.

The pruning had four recurring grounds the report does not express: the defect cannot happen or cannot be observed in the target's actual configuration; the test is brittle, such as a source-text check or an exact log line count; the test is over-design, such as an optional AST check; and the proposal smuggles in a specification change, such as widening a requirement, changing an exit code, removing a requirement or adding a production testability seam, which got approved together with the tests. The highest-value findings, acceptance that cannot be carried out or would pass on the old code, were buried in the last section, Ticket-shape notes, and the decisions only the user can make had to be collected by main from several analysts' reports.

Cost was also high: about 420k tokens and 13 to 14 minutes per analyst for 3 tickets. Two analysts split by ticket each designed their own version of a fixture, a case and a test file the tickets shared, and main reconciled them. Guideline text adds to the enumeration: the Key examples guideline proposes every case the techniques derive.

## Solution

The analysis first lists every candidate test in one line and grades it, then writes the full statement only for the tests it recommends. Grades reuse the delegation skill's paragraph on weighing findings, plus two test-design rules for defects the target's actual configuration cannot produce or a code review confirms at a glance. The report leads with what the user must act on: problems in the acceptance as written, decisions that belong to the user, and a Lean set summarising the recommended tests and their total size, followed by the details. Main re-grades and merges what analysts return and recommends the Lean set, never "adopt all". A spec gets one analyst by default, and a split allocates shared test work to one Assignment. Three new guidelines cover tests that cannot fail on a wrong implementation, exact counts and source-text checks.

## User Stories

1. As a user, I want each proposed test graded Recommended or Optional, so that I can see which tests are worth writing.
2. As a user, I want grades judged by when the defect occurs in normal use or under the threat model, its worst outcome and what already covers it, so that grading follows the same weighing as every other cc-feather finding.
3. As a user, I want a security problem never downgraded for rarity alone, so that grading does not weaken Security-critical work.
4. As a user, I want a defect that cannot occur or cannot be observed in the target's actual configuration left out, so that tests do not prove behaviour no user can see.
5. As a user, I want a defect reached only by a rare downstream configuration and confirmable at a glance in code review graded Optional at most, so that such tests stay visible without being recommended.
6. As a user, I want the report to start with the places where the acceptance as written cannot be carried out or would pass falsely, so that the most valuable findings are read first.
7. As a user, I want the decisions only I can make collected in one section, so that a specification change is never approved as part of a test proposal.
8. As a user, I want a change to how a criterion is verified kept apart from a change to what the criterion requires, so that I know which edits change the agreed behaviour.
9. As a user, I want a Lean set listing the recommended tests with their total count per level, so that I decide from one short summary.
10. As a user, I want tests that depend on an open decision kept out of the Lean set, so that the Lean set never assumes my answer.
11. As a user, I want full statements only for recommended tests and one line for each optional one, so that the report is readable.
12. As a user, I want tests left out grouped by reason, so that the Not proposed section does not grow with every imagined case.
13. As a user, I want main to re-grade and merge what analysts return before reporting, and never recommend adopting everything, so that I do not have to prune the report myself.
14. As a user, I want main to check each acceptance problem against the code before reporting it, so that I can trust the first section.
15. As a user, I want one analyst per spec by default, so that the same code is not read twice.
16. As a user, I want a necessary split to give each shared fixture design or overlapping test obligation to one Assignment, so that analysts do not design competing versions.
17. As a user, I want the small-target threshold judged by source scope, coupling and reasoning difficulty rather than ticket count, so that the choice of who analyses fits the work.
18. As a user, I want every proposed test to state why it fails on the old code or a wrong implementation and what guarantees the order its oracle relies on, so that no test passes falsely.
19. As a user, I want incidental counts, such as log lines, asserted as at least one occurrence with the right content, while exact counts stay where cardinality, completeness, absence or repetition is part of the contract, so that one more harmless log line does not break a test.
20. As a user, I want source-text checks used only where no behaviour can be observed, and marked as brittle, so that they are a last resort.
21. As a user, I want derived cases proposed only when each catches a distinct defect and is recommended, so that a technique does not turn into a 33-case table.
22. As a maintainer, I want grading to point to the delegation skill's weighing paragraph rather than restate it, so that the rule has one owner.
23. As a user, I want a difference between the acceptance and code the target is meant to change kept out of Acceptance problems, so that a test that should fail before implementation is not reported as a defect.
24. As a user, I want the analysis to locate the code behind each ticket's behaviour before searching for existing tests, so that tickets without file paths still get their related tests found.
25. As a user, I want the Lean set to include the extensions and updates of existing tests it relies on, so that the recommended package is complete.

## Implementation Decisions

- **The judging rule.** It stays as it is and gains: a defect that no plausible wrong implementation could produce in the configurations the target supports once the change is made, those the applicable threat model reaches included, or whose effect nothing could observe there, names no defect for this rule, and the test is not proposed. An effect counts as observable through behaviour, a required artifact or a manual check. The guideline Requirement and failure modes first stays as the case-choice form of this rule.
- **Grades.** Every proposed test is graded Recommended or Optional, weighed as [the delegation skill](../../skills/delegation/SKILL.md)'s paragraph on weighing findings describes: when the defect can occur in normal use or under the applicable threat model, its worst credible outcome, and whether an existing test or rule covers it. That paragraph's rule that normal-use rarity alone never discounts a security problem applies. A defect reached only by a rare downstream configuration and confirmable at a glance in code review is Optional at most, unless its outcome is a security problem or data loss, which the paragraph alone grades. The skill points to the paragraph and does not restate it; the paragraph does not change.
- **Candidates before statements.** The cases the Runs and sizes rules and the guideline techniques give, partitions, boundaries, transitions, integration points and each case of a parametrized test included, are candidates, graded like any other, not cases every report must propose. The analysis first lists each candidate test in one line: the requirement, the concrete defect, whether it can occur and be observed as the judging rule says, the existing coverage and any overlap with another ticket's candidates. It grades each candidate as Recommended, Optional or Not proposed, and only then writes the full statement for the Recommended ones. An Optional test is one line: its defect, its level and why it is Optional, plus a mark for any obligation that still applies to it, such as a gate who runs it must be named for or a bound that is unknown, which also lists it under Resource risk. Its full statement is written when the user asks or before it enters any acceptance. This happens within one analysis, with no round-trip to the user.
- **Behaviour to code.** Tickets name no file paths, so before the Existing related tests search the analysis, or main when it analyses the target itself, locates the source paths and test support behind each ticket's behaviour; main may give a starting scope in the brief. A behaviour it cannot map is reported as uncertainty in Existing related tests.
- **What each proposed test states.** The existing list, the defect, the expected result and its source, the level, the case choice, size and runs as estimated cost, the bound of its work and the role of any double, becomes what each Recommended test states.
- **Report sections, in order.**
  1. **Acceptance problems**: each place where a verification the target's existing acceptance states is invalid for the intended change: it cannot be carried out, it would pass on the old code or on a wrong implementation, such as an oracle with no ordering guarantee, or it asserts a result that differs from behaviour the target does not change, such as a status code the framework never returns. Each comes with the evidence main checked. A difference from code the target is meant to change is the change still to be implemented, not an acceptance problem, and a newly considered test that could not fail goes under Not proposed. A problem whose fix changes only how a criterion is verified goes here or under Proposed tests.
  2. **Decisions for the user**: a production-code change for testability; a meaning the spec leaves unclear; a change to required behaviour, such as widening, removing or rewording a requirement or an invariant; a characterised behaviour that may be a bug; and each place where a test need may change how the tickets are cut or their blocking edges, which replaces the Ticket-shape notes section. These are never recommended as test proposals. A test that depends on an open decision names it.
  3. **Lean set**: one line for each Recommended test, its ticket, level and case count with a pointer to its statement, each Recommended manual check, and each extension or update of an existing related test that a Recommended test relies on; then the number of tests and cases at each level. It states no time figure, holds no removal, and leaves out every test that depends on an open decision. Rerunning an existing test is not listed in it.
  4. **Proposed tests**, grouped by ticket or requirement, Recommended tests with their full statement and Optional tests in one line each, with the subsection for manual verification as now.
  5. **Existing related tests**, as now, plus any behaviour that could not be mapped to code.
  6. **Removals**, unchanged.
  7. **Not proposed**, grouped by reason, each group naming the tests it covers.
  8. **Resource risk**, unchanged, Optional tests with an unknown bound included.
- **Main's integration.** Before reporting, main re-grades every analyst item by the same weighing, merges duplicates across tickets and checks each Acceptance problem against the code; analyst grades are input. Main recommends the Lean set and never recommends adopting every proposal. When main analyses a small target itself, the same applies to its own candidates.
- **Who analyses.** Whether a target is small is judged by its source scope, coupling and reasoning difficulty, not by its ticket count. A target that is not small gets one analyst Assignment by default, a spec with its tickets included. It is split only when it exceeds what one analyst can handle well, along distinct behaviours or invariants, and the brief then gives each shared fixture design or overlapping test obligation to one Assignment, which the others reference rather than propose again. Main still gathers repository history for error guessing, which the analyst cannot read.
- **Guideline reference.** In the existing three-part form, what it does, where it applies and where it does not:
  - Key examples, changed: a few key examples per rule illustrate it, and a case a technique derives is a candidate, proposed only when it catches a defect the other cases do not, at the grade it earns. Derived cases kept inside one parametrized test count as that test's cases; candidates left out are grouped under Not proposed.
  - Fails on the wrong implementation, new in Test quality: each test states why it fails on the old code or on a wrong implementation and what guarantees the order its oracle relies on, such as a registration barrier or an event wait rather than a sleep. A newly considered test that cannot state it is redesigned or not proposed; an existing acceptance verification that cannot is listed under Acceptance problems.
  - Exact counts only where the count is the contract, new in Test quality: an exact count is asserted where cardinality, completeness, absence or repetition is part of the required result, such as the records a query must return, no forbidden record, audit events or a message sent exactly once. An incidental count, such as log lines, is asserted as at least one occurrence with the right content.
  - Code-text checks last, new in Test quality: a check of code text or syntax trees is used only where no behaviour, required artifact or manual check can observe the effect, and is marked brittle.
- **Glossary.** The CONTEXT.md Test design entry says that each proposed test is graded Recommended or Optional, that only a Recommended test carries the full statement, and that the report leads with acceptance problems, decisions for the user and a Lean set. No other entry changes.
- **Documents.** Both reference documents' Test design sections and both READMEs' command lines follow the new report shape, sentences paired in English and Traditional Chinese.
- **Release.** 0.49.0: the `version` in `.claude-plugin/plugin.json` becomes 0.49.0, and the tag `v0.49.0` is created only after checking that it matches; no existing tag is moved. No installed guidance, policy template, role definition or setup procedure changes, so existing installations need no setup update. The 0.49.0 entry in `docs/setup-validation.md` records that determination with its evidence from the diff against `v0.48.0`, and the entry and both READMEs' 0.49.0 notes say that a plugin update and a fresh session are all that is needed and that going back to 0.48.0 means reinstalling the 0.48.0 plugin. Each README gets the note at the start of its Updates section. The release tests that pin 0.48.0 as the latest release move to 0.49.0 as earlier releases moved them, and the earlier releases' evidence stays as it is.
- **Not affected.** The delegation skill and its weighing paragraph, plan review and every review procedure, the scout and analyst role definitions, `test-speedup` and the shared test criteria, Related-test acceptance, the Unbounded probe entry, the Timing paragraph, setup, handoff, leases and worktrees.

## Testing Decisions

- No executable seam: the skill is model instructions. Following the project's practice, tests pin each decision-carrying sentence as a whole sentence where it is stated, README and reference sentences paired in both languages.
- The pins go in the existing design checks test module, beside the current `test-design` pins, using the shared test support. The pins of sentences this spec changes move to the new wording, a renamed paragraph label included in the pins' lookup keys; the section-list test checks the eight sections in order.
- Pinned: the judging rule's added sentences; the grades, their pointer to the weighing paragraph and the rare-downstream rule with its security and data-loss exception; candidates before statements and the one-line Optional form with its marks; behaviour to code; each report section's sentence; main's integration and the sentence that it never recommends adopting every proposal; the Who analyses sentences; each changed or new guideline, in the three-part form the structural guideline test requires.
- The guideline reference keeps passing the existing check that it carries no source labels, citations or digits: the new guidelines use no digit and not the word "Source", which that check rejects, so the check itself does not change.
- Single-owner check: the delegation skill's weighing paragraph is pointed to and not restated in the `test-design` skill or its guideline reference, and the paragraph itself is unchanged.
- Glossary: the CONTEXT.md Test design entry.
- Prior art: the 0.47.0 `test-design` pins and the release tests' version and validation checks.
- Live rehearsal: the validation entry records a run of the command on one spec with tickets, preferably a target with an earlier report to compare, with the number of tests and cases proposed, recommended and in the Lean set, a few representative grading reasons, the duplicates main merged, the items placed under Decisions for the user, each agent's token use where the tools report it, and whether the report led with the three new sections. It states that the pins show the text, not that a model always follows it.

## Out of Scope

- A scout pass for mechanical discovery before the analyst; deferred until a measured run shows exploration dominates the cost.
- A cap or budget on proposals per ticket.
- A two-stage report that waits for the user before writing details.
- A fixed ownership rule such as the lowest-numbered ticket owning a shared fixture.
- Changes to the ticket-cutting skill, the Timing paragraph, plan review or the weighing paragraph.

## Further Notes

- **Limits.** The command is instructions to the model; the pins cannot show that a model grades well or keeps the Lean set short. The cost reasons are estimates: the field reports gave no breakdown of the 420k tokens.
- **Sources.** The field reports came from two other sessions on 2026-11-27. Codex's second opinion supplied the candidates-before-statements pass, the Key examples change, ownership of shared work rather than whole files, the behaviour-based small-target threshold and the grouped Not proposed section; its scout proposal is deferred as Out of Scope states.
- **Tickets.** The work is to be cut into tickets under `.scratch/test-design-proposal-triage/issues/`, which carry each Claim's acceptance; the breakdown is confirmed with the user first. A likely cut: the skill and guideline changes with the glossary; the documents and release, last.
- Automatic plan review is on, so the tickets get plan review before implementation.

## Overall acceptance

This is the Plan's overall acceptance, which the final check runs once for each commit to be landed or tagged, not once for each Claim; it is not part of any Claim's acceptance, and each ticket cites it.

- The full `unittest discover` suite passes at the commit to be landed or tagged.
