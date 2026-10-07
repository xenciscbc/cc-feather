# Review state rules: recovery, validity, completion and resumption

Label: `ready-for-agent`

Vocabulary follows [CONTEXT.md](../../CONTEXT.md). The decisions below come from two independent reviews of v0.13.2 (Codex and analyst), a Codex discussion that agreed fifteen resolutions, and the user's choices on the remaining six; ADR 0006, written as part of this work, records them.

## Problem Statement

The automatic review flow's state transitions are only partly written down. After a step stops, an explicitly requested call that passes has a different effect in each of the three steps, and outcome verification contradicts itself about whether such a pass completes a claim. Nothing says when an APPROVED or CONFIRMED verdict stops being valid after the work changes again, so a claim edited after it passed may or may not be reviewed again. Release claims require verification before a commit that their own acceptance (the tag) can only be checked after. A new plan that partly overlaps a stopped plan can restart the count. When the count or verdicts cannot be established after context compaction, the procedure gives no fallback. Resumed sessions have only one direction of the verdict-inheritance rule in the procedure, and whether passing verdicts carry over is unstated. Tickets are judged "finished" by a status nobody maintains, so shipped tickets stay `ready-for-agent`. An unverified claim may be committed although an unreviewed one may not. "The user decides" has no defined meaning. A user's plain "review" in auto mode is not classified, and a generic retry could be read as an extra review call. The glossary contradicts the procedures in three places, ADR 0005 carries a stale consequence, and contract tests check only phrase presence in the procedures, so documents drift unnoticed.

## Solution

One state model governs plan review, code review and outcome verification, written once and cited by each procedure. An automatic stop is cleared by an explicitly requested pass, which leaves the count unchanged and lets the automatic flow continue to the next step. A pass is valid only for the content it judged; a relevant later change reopens the affected review and verification. Release claims verify the candidate before the commit and confirm the tag and version after it. Overlap keeps a stopped plan's state, unknown state is treated as stopped, resumed sessions inherit unresolved verdicts in both directions while passing verdicts do not carry over, and a generic retry counts as a review call. Main keeps ticket status current when the project defines a completion value, and a claim is committed only with both passes valid unless the user explicitly allows a work-in-progress commit. The user's decisions are recorded as one of five kinds. The glossary, ADRs and both READMEs are brought in line, and tests check the new rules and the documents against the procedures.

## User Stories

1. As a user whose automatic review stopped, I want my explicitly requested review that passes to clear the stop and let the flow continue, so that I am not stuck after fixing the problem.
2. As a user, I want that explicit pass to leave the count unchanged, so that later automatic calls in the same step still need my request.
3. As a user, I want the three review steps to treat a stopped step the same way, so that I can predict what happens.
4. As a user, I want an explicit verification made before code review to still not complete a claim, so that the order of the flow cannot be skipped.
5. As a user in auto mode, I want my "review" to be classified by whether the flow was due to run that step, so that saying "review" cannot bypass the budget.
6. As a user, I want main to tell me whether a review counts as automatic or explicit before dispatching it, so that I know its effect.
7. As a user, I want every attempted call, including a recovery retry, to count, so that retries are not free extra reviews.
8. As a user, I want a stopped step never to be re-run as a retry, so that the stop holds.
9. As a user, I want unknown review state after compaction to be treated as stopped and to be asked, so that main never assumes a count of zero.
10. As a user, I want each review result to show the current count, so that summaries keep it.
11. As a user, I want a new plan overlapping a stopped plan to keep that work stopped, so that renaming or widening the scope cannot restart the count.
12. As a user, I want new work outside the overlap to be counted on its own, so that unrelated additions are not blocked.
13. As a user, I want the first review of an overlapping plan to see the inherited findings, so that settled issues are not lost.
14. As a user, I want a pass to stay valid only for the content it judged, so that a later change is reviewed again.
15. As a user, I want main to explain why an unrelated change does not reopen a claim, so that I can check its judgement.
16. As a user, I want a change only to the verification environment to reopen verification, so that a confirmation still matches how the claim runs.
17. As a user, I want claims committed only with both passes valid, so that unverified work does not land.
18. As a user who needs a work-in-progress commit, I want to allow it explicitly and see it labelled unaccepted, so that it is not mistaken for finished work.
19. As a user releasing a version, I want the candidate verified before the commit and the tag confirmed after it, so that every acceptance item can actually be checked.
20. As a user, I want "at most six calls per claim" described as one uninterrupted attempt, so that I estimate cost correctly.
21. As a user, I want main to mark a ticket done with the version or commit once its claim passes and is committed, so that ticket status stays current.
22. As a user whose project defines no completion value, I want main to report which tickets it considers done, so that I can update them.
23. As a user, I want my decisions recorded as re-review, deferral, cancellation, changed acceptance or waiver, so that their effect is clear.
24. As a user who waives a review, I want the waiver and its risk kept in the report, so that it is never presented as a pass.
25. As a user, I want "continue" or turning auto off not to accept a known defect, so that defects are not silently waved through.
26. As a user resuming a session, I want unresolved verdicts recorded in an active handoff to restrict the related work in both directions, so that naming the spec or a ticket cannot escape them.
27. As a user resuming a session, I want an unfinished plan to be reviewed again, so that a fresh session does not trust verdicts it did not see.
28. As a user resuming a session, I want finished tickets not to be redone, so that completed work is not repeated.
29. As a user, I want a review blocker that needs claim changes to be decided by me or my planning step, so that main does not restructure my plan alone.
30. As a user who authorises such a change, I want the old-to-new claim mapping and unresolved blockers kept, so that history stays traceable.
31. As a user with a plan-mode or conversation plan, I want a new session to use the original text or a version I confirm, so that claims are not guessed.
32. As a reader of the glossary, I want Plan, Unplanned work and Unverified claim defined as the procedures use them, so that the documents agree.
33. As a reader of ADR 0005, I want an amendment note on its stale consequence, so that I am not misled.
34. As a maintainer, I want ADR 0006 to record these decisions and rejected options, so that later readers know why.
35. As a reader of either README, I want the state rules and edge cases described in the same words, so that both languages agree.
36. As a maintainer, I want a test that fails when a README or glossary statement has no matching procedure rule, so that documents cannot drift silently.
37. As a maintainer, I want contract tests for every load-bearing rule, so that deleting one is caught.
38. As a user with an existing installation, I want this change from the plugin update alone, so that no setup update is needed.

## Implementation Decisions

- **One state model.** A single section, placed with the review procedures and cited by each of them, defines the per-step state: work identity, reviewed content, call source, consecutive non-pass count, valid verdict and blockers. Each procedure keeps only what is specific to its step.
- **Explicit pass after a stop (user decision).** It clears the stop, leaves the count unchanged and the automatic flow continues to the next step. Because the count is unchanged, any later automatic call in that same step (for example a reopened review) still needs the user's explicit request; that requested call is still an automatic call of the flow, so a pass resets the count and a non-pass stops the step again. An explicit call itself runs only the requested step; what continues afterwards is the automatic flow resuming, so the glossary's Explicit request, the delegation skill and the READMEs say this instead of "leave the next step to the user" for a stopped step. An explicit review or verification made before the automatic flow reached that step does not count as that step's pass; this generalises the existing restriction on explicit verification.
- **Classifying "review" (user decision).** Automatic when the flow is due to run that step; explicit when the step has stopped or the request is outside the flow. Main states the classification before dispatching.
- **Counting.** Every attempted call counts, including a generic recovery retry; a stopped step is not re-dispatched as a retry. A missing role or fresh context before dispatch is a precondition failure, not a call.
- **Unknown state.** Treated as stopped; main asks. Compaction is not a new session. Each review result states the current count.
- **Overlap.** The overlapping work keeps its count and stop and gains no new automatic calls; an automatic READY of the widened plan does not clear the inherited stop for the overlapping work, while an explicit pass that covers it does, as for any stopped step; the first review gets inherited findings and dispositions; independent new work counts separately; counts of different plans are not added.
- **Validity.** A pass covers the claim, acceptance and reviewed content (revision or diff). Relevant changes (the claim's files or dependencies) reopen code review and verification; environment-only changes reopen verification; unrelated changes need a stated reason. Reopened calls continue the step's count from where it stands, which is zero after an automatic pass; after an explicit pass the count is unchanged, so a reopened automatic call needs the user's request. Updating a ticket's status is not a relevant change.
- **Completion and commit (user decision).** For plan-driven claims in the automatic flow, and for any claim an active handoff records as unreviewed or unverified: both passes valid before commit or completion; work-in-progress commits only with the user's explicit permission and labelled unaccepted. Off mode keeps its current behaviour, except for claims an active handoff records as unreviewed or unverified.
- **Two-phase release.** Postconditions of authorised operations (tag after commit) are checked and reported by main afterwards; outcome verification covers the rest before the operation.
- **Ticket status (user decision).** After a claim passes and is committed, main sets its ticket to the project's defined completion value with the version or commit; without a defined value, it reports. A ticket is finished when its status equals the project's defined completion value or the user says it is done; without a defined value main asks. Main does not otherwise edit a spec or ticket to add claims.
- **User decisions (agreed).** Recorded as re-review, deferral, cancellation, changed acceptance or waiver, with scope; waivers stay visible and are never recorded as passes; "continue" or auto-off does not accept defects.
- **Resumed sessions (user decision).** Unresolved verdicts recorded in an active handoff restrict related work in both directions; without an active handoff record no restriction carries over (ADR 0002); counts and passing verdicts do not cross sessions; an unfinished plan gets plan review again; finished tickets are not redone.
- **Plan changes.** Claim additions, splits or changes needed by a REVISE are decided by the user or the planning step; main edits after authorisation, keeping the claim mapping and unresolved blockers. This amends ADR 0005's statement that main never edits a spec or ticket to add claims.
- **Conversation plans.** Identified only from original text, an available record or a user-confirmed version.
- **Unchanged (user decision).** Unplanned non-security edits stay without automatic review regardless of size.
- **Glossary and ADRs.** CONTEXT.md entries for Plan, Unplanned work and a new Unverified claim; an amendment note on ADR 0005; ADR 0006 records the decisions and rejected options (fixed totals, resetting counts on explicit passes, trusting passes across sessions, counting retries as free, rebuilding conversation plans, widening review to unplanned work) and notes that it amends ADR 0004's per-claim six-call consequence and ADR 0005's no-edit statement; ADR 0004 and ADR 0005 each get an amendment note on the affected statement.
- **Installed files unchanged.** No template, policy or configuration-tool change; existing installations need only the plugin update and a fresh session. The reviewer and analyst template changes are a separate work item.
- **Release** as 0.14.0 under the project rules; a correction ships as 0.14.1.

## Testing Decisions

- Good tests assert the published contract — the rule statements in the procedures and the agreement of other documents with them — not wording beyond key phrases, and no layout-only strings.
- Seam 1 (existing): the configuration test module's skill-text contract tests. New cases per claim assert the new statements and fail on the 0.13.2 text; load-bearing rules without tests today get one (partial overlap, all tickets finished, claim list and tickets must agree, refers-to-none is one claim, count continues, main never approves its own plan, no commit when unreviewed, the explicit-verification restriction, unknown state). Negative checks reject the old wording where it would mislead (a per-claim six-call ceiling stated as a total).
- Seam 2 (new, same module): a cross-document mapping. Sources: in README.md the bold-label bullets of the automatic review list and of the "Which document is the plan" list under "Roles and routing"; in README.zh-TW.md the corresponding bullets under 「分派與預設模型」, paired with the English ones through a label table; and the CONTEXT.md entries Plan, Claim, Unplanned work, Explicit request, Unreviewed claim, Unverified claim and Delegation preview. A bullet with more than one bold label is paired by its first label. The test enumerates every bold-label bullet in those lists and fails when one has no mapping entry, when the two languages' bullet labels do not pair up, or when either the document phrase or the procedure phrase of an entry is missing. Existing per-procedure phrase tests are kept by keeping their phrases in each procedure.
- Seams 1 and 2 are the acceptance gate for every ticket that changes rule text or documents. No Python model of the state machine is built.
- Live scenarios are observations, not gates, run after release with the updated installed plugin (a candidate cannot be loaded beside the installed plugin of the same name without risk of testing the old rules): two or three fresh headless sessions (naming a spec then one of its tickets in one session; unknown state after a simulated loss; a "review" request in auto), each recorded with the plugin version it loaded in the report and the handoff, and carried into the next version's validation entry; a result that differs from the expectation is reported as found, not as a release failure.
- Release checks: the full `unittest discover` suite and `claude plugin validate` for the plugin root and the manifest.

## Out of Scope

- The reviewer and analyst role-definition changes (second review after an interrupted first call, post-REFUTED review inputs); they need a setup update and are a separate work item.
- Readability cleanups: splitting plan-review's long paragraph and the Traditional Chinese bold-label punctuation.
- Widening automatic review to unplanned work.
- This repository's own tracker completion value, which is project configuration committed separately.
- Hook-enforced counters or persistent review state.

## Further Notes

- Claims come from the tickets split from this spec; each ticket's acceptance and `Blocked by` lines define its claim and dependencies.
- In auto, this spec is a Plan once the user agrees to it.
