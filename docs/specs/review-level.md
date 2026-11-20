# Review level

Label: `ready-for-agent`

Vocabulary follows [CONTEXT.md](../../CONTEXT.md). The decisions below were settled by the user on 2026-11-20 in a grilling session, with a second opinion from Codex, and are recorded in [ADR 0023](../adr/0023-a-plans-review-level-is-the-users-choice.md). This spec changes the delegation skill's plan-review and review-state rules, the automatic review toggle's meaning and the READMEs, so it is release 0.42.0.

## Problem Statement

In auto, a small fix with a known cause takes as long as a feature. A UI adjustment, a wording change or a different log message becomes Plan-driven work as soon as it is written as a ticket or spec, and then runs the whole Automatic flow: plan review, possibly several rounds of it, code review, outcome verification, a Final check scope question, the final check and the decision at the end of the Plan. For a one-line fix that is several agent calls, several minutes of waiting each and one or two questions, for checks the fix gains little from.

The user can already avoid this, but only by remembering to: not writing the fix as a ticket, so it is Unplanned work, or saying the task is off and then asking for a code review by hand. Nothing offers the lighter path when a small ticket comes up, and when the user does remember, the independent code review depends on remembering it too.

## Solution

Before the first Claim of a Plan of Plan-driven work is implemented in auto, main recommends a Review level for that Plan, with a one-line reason, and the user chooses:

- **`standard`**: the Automatic flow, as today.
- **`light`**: off for that Plan, plus three things main does on its own. Once a Claim is implemented, main requests its Code review from the reviewer role. It runs every item of the Claim's acceptance and reports each observed result. Then it stops in the conversation, without a question tool, listing what is left to do, landing included.
- **`off`**: the existing task-level off for that Plan.

Main recommends `light` only for a narrow case: one Claim with a known cause and small scope, acceptance that shows the outcome directly, not Security-critical, no migration, no irreversible operation, no foreseeable resource risk and no change to shared test support or build configuration. Everything off mode keeps still applies under `light`, including the classification of Security-critical claims, their security analysis and their routing to security-executor. No new setting is added, and the installed delegation guidance does not change: its existing sentence that a task choice to turn automatic review off overrides it already covers `light` and `off`.

An installation where the user always chooses `standard` behaves as 0.41.0, except that main asks the question.

## User Stories

1. As a user, I want main to offer a lighter path when I ask it to implement a small ticket in auto, so that a one-line fix does not wait for the whole Automatic flow.
2. As a user, I want the choice made once per Plan, before its first Claim is implemented, so that I decide before any work or review starts.
3. As a user, I want main to recommend a level with a one-line reason, so that I can accept the recommendation without working it out myself.
4. As a user, I want the recommended option listed first, so that accepting it is one click.
5. As a user, I want to choose between `standard`, `light` and `off`, so that I can pick full review, one independent review, or none.
6. As a user, I want saying "implement T at light" to count as my choice, so that I am not asked a question I have already answered.
7. As a user, I want a level written in a ticket or spec to inform the recommendation and never to be taken as my choice, so that a document cannot lower the review of my work on its own.
8. As a user, I want main to recommend `light` only for one Claim with a known cause and small scope, so that work that needs plan review is not steered away from it.
9. As a user, I want main to recommend `light` only when the acceptance shows the outcome directly, so that a UI wording fix is checked by seeing the wording, not only by a build.
10. As a user, I want main never to recommend `light` for a Security-critical claim, so that security changes keep their security analysis and Adversarial review by default.
11. As a user, I want main never to recommend `light` for a migration, an irreversible operation, a foreseeable resource risk or a change to shared test support or build configuration, so that the light path stays for fixes whose failure is cheap.
12. As a user, I want `light` to keep every rule off mode keeps, so that a Security-critical change discovered in a light Plan still gets a security analysis and goes to security-executor.
13. As a user, I want a light Plan's Code review done by the reviewer role, never by main, so that the one check `light` keeps is independent.
14. As a user, I want main to request that Code review on its own once the Claim is implemented, so that I do not have to remember to ask.
15. As a user, I want main's requests for that Code review counted as automatic calls of the Claim's Code review, so that a review that keeps failing stops at the Stop threshold and waits for me.
16. As a user, I want main to fix the findings of a CHANGES_REQUESTED and request the Code review again, so that a light Plan ends with an approved change when it can.
17. As a user, I want main to run every item of the Claim's acceptance and report each observed result, so that I see what was actually checked.
18. As a user, I want an acceptance item that could not be run reported as not run, so that a skipped check is never shown as passed.
19. As a user, I want a light Plan to end in the conversation without a question tool, so that I can leave with `/clear` or a new session without paying for another model call on a pending question.
20. As a user, I want the end of a light Plan to list the Code review's verdict, the acceptance results, any open findings and what is left, landing included, so that I can decide from that one message.
21. As a user, I want main to land a light Plan only on my instruction, so that the light path never lands on its own.
22. As a user, I want main to stop and ask me to choose the level again when a light Plan turns out to need a Security-critical change, so that the lighter level never silently covers security work.
23. As a user, I want main to stop and ask me to choose the level again when a light Plan has a material Deviation, so that work grown beyond the small fix gets the review it now needs.
24. As a user, I want the level to be `standard` whenever my choice is not known in the session, for example after a context compaction, so that losing the answer never lowers the review.
25. As a user, I want main never to raise or lower the level on its own, so that the level is always my decision.
26. As a user, I want an Active handoff, when one exists, to record the level I chose, so that a resumed session continues at that level instead of falling back to `standard`.
27. As a user, I want the question asked only in auto, so that off mode, where nothing runs automatically, does not gain a question.
28. As a user, I want the question asked only for Plan-driven work, so that Unplanned work stays as it is.
29. As a user, I want the question to come after main has decided the Plan, including the choice between a spec and its tickets, so that I choose a level for the Plan that will actually be implemented.
30. As a user, I want changing a Plan's level midway to follow the existing rules for a mode change, so that no count resets and no finding is erased.
31. As a user, I want no new setting or installed guidance change, so that existing installations need no setup update to use it.
32. As a user, I want the README to explain the three levels and when main recommends each, so that I know what I give up with `light`.
33. As a maintainer, I want the definition of `light` written once in review state and referred to elsewhere, so that the rule has one owner, as ADR 0017 requires.

## Implementation Decisions

- **Owner.** Review state defines the Review level once: the three values, what `light` adds to off, the recommendation conditions, the stops that ask for the level again, `standard` while the choice is unknown, and that main never changes it on its own. Plan review, the toggle's meaning and the READMEs refer to it.
- **When it is asked.** In plan review's procedure, at the point where main already states before implementing in auto whether the work is plan-driven and therefore reviewed: for Plan-driven work, main classifies the Claims as it already must, then asks the level once for the Plan with AskUserQuestion, its recommendation first with a one-line reason. It is asked after the spec-or-tickets question when there is one, and before plan review, since `light` and `off` run none. A user instruction that already names the level is the choice and no question is asked.
- **What `light` runs.** Off mode's rules, unchanged, plus: a Code review request main makes for each implemented Claim, counted as an automatic call of that Claim's Code review, so that its consecutive non-pass count stops it at the Stop threshold, with the findings of a CHANGES_REQUESTED fixed as the code-review procedure describes before main requests it again; main's own run of every acceptance item with each observed result, an item not run reported as not run; and the stop at the end in the conversation, without a question tool, listing the Code review verdict, the acceptance results, open findings and what is left, landing included. No Dispatch record, no final check of the Automatic flow (off mode's final check before a landing the user asks for still runs), no Acceptance gate beyond what off mode already applies through an Active handoff, and no Auto land.
- **Leaving `light`.** A discovered Security-critical change or a material Deviation stops the work, and the user chooses the level again; main recommends `standard`. A change of level follows the existing rules for a mode change: counts and findings carry over.
- **Unknown choice.** Until the user's choice is known in the session, the level is `standard`. With an Active handoff, main records the chosen level in it; without one, a context compaction that drops the choice returns the Plan to `standard`, and the existing Implemented before plan review rule handles implemented Claims.
- **Glossary.** `CONTEXT.md` already defines **Review level**, written with this spec. The **Automatic flow** and **Plan-driven work** entries, and the README sentences on what auto covers, are updated by the change that adds the review-state rule, together with the tests that pin them, so that they say the Automatic flow runs at level `standard`.
- **Unchanged.** The configuration tool, the installed delegation guidance template, the role templates, the Automatic flow itself, Dispatch records, Final check scope, Auto land, merge-upstream and the delegation preview.

## Testing Decisions

- One seam, existing: the shipped model-instruction documents. As the project already does, tests pin each decision-carrying sentence as a whole sentence in the document and section that state it, and README sentences paired in both languages.
- Tests check external behaviour only, meaning which rule sentences the shipped documents state, never how main applies them.
- A new test module for this feature, using the shared test support, pins: review state's Review level definition with its three values, what `light` adds, the recommendation conditions, the stops, `standard` while unknown and main never changing the level; plan review's ask, its place before plan review and after the spec-or-tickets question, and that an instruction naming the level is the choice; the toggle's meaning; the README sentences in both languages.
- Existing pins of sentences this spec changes, such as the Automatic flow entry, are updated where they are. The release tests pin 0.42.0.
- Prior art: the Final check scope tests for an ask placed in plan review's procedure and a definition owned by review state; the auto-land tests for README pairs; the delegation-dedupe tests for one owner per rule.

## Out of Scope

- A separate light flow inside auto, with its own Dispatch record, Acceptance gate, final check and Auto land: considered and dropped, as ADR 0023 records.
- Letting the user declare that a Claim main classifies as Security-critical is not Security-critical: not needed, since `light` keeps off mode's security rules.
- A saved default level for a project or user: the level is a per-Plan choice.
- A level shown in the delegation preview.
- **Follow-up:** whether the decision at the end of a `standard` Plan should also stop in the conversation instead of asking with a question tool, for the same token-cost reason ADR 0023 gives for `light`. Recorded here for a later Plan; not part of this change.

## Further Notes

- **Limits.** `light` keeps only one independent check. Its guards are main's recommendation conditions and the user's choice; a fix wrongly judged small loses plan review, outcome verification and the final check, as off mode does. A choice lost to a context compaction without an Active handoff returns the Plan to `standard`, which costs reviews but never removes them.
- **Tickets.** If the user cuts this spec into tickets, they go under `.scratch/review-level/issues/`, each with its own acceptance naming its related test modules, and the release last.
- Automatic plan review is on, so this spec, or its tickets, get plan review before implementation; at that point the Review level question itself applies, and this work, which changes review rules, is `standard`.

## Overall acceptance

This is the Plan's overall acceptance, which the final check runs once for each commit to be landed or tagged, not once for each Claim; it is not part of any Claim's acceptance, and each ticket cites it.

- The full `unittest discover` suite passes at the commit to be landed or tagged.
- `.claude-plugin/plugin.json` states version 0.42.0, and `docs/setup-validation.md` records the release's validation under its version heading.
