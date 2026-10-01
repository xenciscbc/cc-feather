# cc-feather

cc-feather lets a main Claude agent hand work to managed native roles and keeps work resumable through handoffs. This glossary covers the vocabulary of its review and delegation workflow.

## Work and plans

**Plan**:
An implementation basis with stated scope, claims and acceptance criteria that the user agreed to: a plan file, spec, ticket, plan-mode plan or a plan approved in conversation. Telling the agent to implement a given plan or ticket counts as agreement; a document lacking scope or acceptance is not yet a Plan.
_Avoid_: task list, todo

**Plan-driven work**:
Work carried out to implement a Plan. In auto mode it is the only work that gets the automatic review flow.
_Avoid_: planned task, ticket work

**Unplanned work**:
Work started without a Plan. Unplanned work that changes a security boundary, migrates data or is irreversible must first become Plan-driven work.
_Avoid_: ad-hoc edit, small fix

**Claim**:
One independently verifiable outcome listed in a Plan, with its own acceptance. Code review and outcome verification each judge one Claim.
_Avoid_: ticket, change, slice

**Implementation phase**:
The span from the user's authorization to implement until completion is reported, including code review and outcome verification. Discussion and planning before that authorization are outside it.
_Avoid_: execution, build phase

**Deviation**:
A difference between implemented work and its Plan. It is material when it changes the Plan's outcome, scope or acceptance.
_Avoid_: scope creep, drift

## Review

**Review mode**:
The setting, `auto` or `off`, that decides whether the Automatic flow runs.
_Avoid_: auto review, review switch

**Automatic flow**:
The sequence plan review, then code review, then outcome verification that auto mode applies to Plan-driven work.
_Avoid_: three-layer protection, pipeline

**Explicit request**:
A user's direct request for one specific review or verification. It runs in either Review mode and runs only what was requested.
_Avoid_: manual review

**Plan review**:
An independent check that a Plan is ready to implement, answered READY or REVISE.

**Code review**:
An independent check of the code implementing a Claim, answered APPROVED or CHANGES_REQUESTED. When the user says "review" about implemented work, this is what is meant.
_Avoid_: PR review, diff review

**Outcome verification**:
An independent check that a Claim holds, answered CONFIRMED, REFUTED or INCONCLUSIVE.
_Avoid_: testing, QA

**Blocking finding**:
A Code review finding that holds completion: a correctness bug, security problem, data loss, regression or deviation from the Plan.

**Non-blocking finding**:
A Code review finding that does not hold completion: style, naming, a refactoring suggestion or an issue that predates the change. It is recorded as follow-up work.
_Avoid_: nit, minor issue

**Unreviewed claim**:
A Claim whose Code review ended without APPROVED after its automatic calls were used up. It is not complete.
_Avoid_: failed review, skipped review
