# Review state

Plan review, code review and outcome verification keep the same kind of state for each step. This file names it once; [plan review](plan-review.md), [code review](code-review.md) and [outcome verification](outcome-verification.md) state how their own step changes it.

| State | Meaning |
| --- | --- |
| Work identity | What the step judges: the logical plan for plan review, one claim for code review and for outcome verification, identified as in [plan review](plan-review.md). |
| Reviewed content | What a call actually judged: the plan text supplied, or the claim's change from its base revision and the acceptance checks supplied. |
| Call source | Automatic, when the automatic flow makes the call, or explicit, when the user asked for it. Explicit calls are outside the automatic budget. |
| Consecutive non-pass count | Automatic calls in a row that did not pass, including failed, interrupted and protocol-failure calls. Two in a row stop the step. |
| Valid verdict | The last pass for the work: READY, APPROVED or CONFIRMED. |
| Blockers | Unresolved findings and verdicts, with what each one blocks. |

State lives in the current session's task. Counts are per session; an unresolved verdict reaches a resumed session only through an active handoff record. Each procedure's step 1 or step 3 says how to recover this state before another automatic call.
