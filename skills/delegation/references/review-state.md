# Review state

Plan review, code review and outcome verification keep the same kind of state for each step. This file names it once; [plan review](plan-review.md), [code review](code-review.md) and [outcome verification](outcome-verification.md) state how their own step changes it.

| State | Meaning |
| --- | --- |
| Work identity | What the step judges: the logical plan for plan review, one claim for code review and for outcome verification, identified as in [plan review](plan-review.md). |
| Reviewed content | What a call actually judged: the plan text supplied, or the claim's change from its base revision and the acceptance checks supplied. |
| Call source | Automatic, when the call belongs to the automatic flow, including a call the user requests for a step the flow is due to run or, in a step whose stop was cleared, a later call that step needs; explicit, when the user asks for a step that has stopped or a review outside the flow. Explicit calls are outside the automatic budget. |
| Consecutive non-pass count | Automatic calls in a row that did not pass, including failed, interrupted and protocol-failure calls. Two in a row stop the step. |
| Valid verdict | The last pass for the work, READY, APPROVED or CONFIRMED, while it stays valid as described under Validity and completion. |
| Blockers | Unresolved findings and verdicts, with what each one blocks. |

State lives in the current session's task. Counts are per session; an unresolved verdict reaches a resumed session only through an active handoff record. Each procedure's step 1 or step 3 says how to recover this state before another automatic call.

## Transitions

- **Stop.** Two consecutive automatic calls without a pass stop the step for that work; it waits for the user's explicit request.
- **Clearing a stop.** An explicit call that passes clears the stop and leaves the count unchanged, and in auto the automatic flow continues to the next step. Because the count stays where it stopped, a later automatic call in the same step for the same work, such as a reopened review or the review of a fix, needs the user's explicit request; that requested call is still an automatic call of the flow, so a pass resets the count and a non-pass stops the step again.
- **What an explicit call runs.** An explicit call runs only the requested step; what follows a stop it cleared is the automatic flow resuming, not part of the request. An explicit review or verification made before the automatic flow reached that step does not count as that step's pass.
- **Classifying a request.** In auto, when the user asks for a review, the call is automatic if the flow is due to run that step for that work, and explicit if the step has stopped or the request is outside the flow. State the classification before dispatching.
- **What counts as a call.** Every attempted call counts, including a generic retry after a temporary failure, and a stopped step is never dispatched again as a retry. A missing role or fresh context found before dispatch is a precondition failure, not a call.
- **Unknown state.** When the count, verdicts or blockers cannot be established in this session, for example after context compaction, which does not start a new session, treat the step as stopped and ask the user. State the current count with each review result.
- **Overlap.** Work that overlaps a stopped plan keeps that plan's count and stop and gains no new automatic calls: an automatic READY of the widened plan does not clear the inherited stop for the overlapping work, while an explicit pass covering it does. The first review of the new plan receives the inherited findings with their dispositions. Independent new work is counted on its own, and counts of different plans are not added.

## Validity and completion

- **What a pass covers.** A pass covers the work identity, its acceptance and the reviewed content it judged. A later change to a claim's files or to what they depend on reopens code review and outcome verification for that claim; a change only to the environment, such as installed tools or external state, reopens outcome verification only. For any other later change, main states why it does not affect the pass. Updating a ticket's status is not a relevant change. A plan's READY is reopened by a material deviation, as [plan review](plan-review.md) step 5 describes.
- **Reopened calls.** A reopened call continues the step's count from where it stands, which is zero after an automatic pass. After an explicit pass that cleared a stop the count is unchanged, so a reopened automatic call needs the user's explicit request.
- **Commit and completion.** For a claim of plan-driven work in the automatic flow, and for any claim an active handoff records as unreviewed or unverified, main commits the claim or reports it complete only with a valid APPROVED and a valid CONFIRMED. A work-in-progress commit of such a claim needs the user's explicit permission and is labelled unaccepted in its message. Off mode otherwise keeps its behaviour.
- **Postconditions.** An acceptance item that can exist only after an authorised operation, such as a release tag after its commit, is a postcondition: outcome verification covers the rest of the claim before the operation, and main checks and reports it after the operation. A postcondition that does not hold leaves the claim incomplete.

## Ticket status and user decisions

- **Ticket status.** After a claim passes and is committed, main sets its ticket's status to the completion value the project's tracker convention defines for done work, with a note naming the version or commit. Without a defined value, main reports which tickets it considers done and leaves their status alone. A ticket is finished when its status equals one of the completion values that convention defines, such as one for work that will not be done, or the user says it is done; without a defined value, main asks.
- **User decisions.** Where a procedure waits for the user to decide, main records the decision as one of re-review, deferral, cancellation, changed acceptance or waiver, with its scope. Re-review is another call, classified as above. Deferral keeps the work and its blockers waiting. Cancellation drops the work and its open findings. Changed acceptance replaces the claim's acceptance and reopens its review and verification as under Validity and completion. A waiver accepts a named open finding or missing pass; it stays visible with its remaining risk in the report and in any active handoff, and is never recorded as APPROVED or CONFIRMED. A waiver does not complete a claim the commit rule covers: such a claim is committed only as a work-in-progress commit the user allows, until a later pass. Saying "continue" or turning auto off does not accept a known defect.
