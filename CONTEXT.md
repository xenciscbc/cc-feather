# cc-feather

cc-feather lets a main Claude agent hand work to managed native roles and keeps work resumable through handoffs. This glossary covers the vocabulary of its review and delegation workflow.

## Work and plans

**Plan**:
An implementation basis with stated scope and acceptance criteria that the user agreed to, with its claims listed, its unfinished tickets in the named scope as claims, or else one claim: a plan file, spec, ticket, plan-mode plan or a plan approved in conversation. Telling the agent to implement a given plan or ticket counts as agreement; a document lacking scope or acceptance is not yet a Plan.
_Avoid_: task list, todo

**Plan-driven work**:
Work carried out to implement a Plan. In auto mode it is the only work that gets the automatic review flow.
_Avoid_: planned task, ticket work

**Unplanned work**:
Work started without a Plan. In auto, Unplanned work that changes a security boundary, migrates data or is irreversible must first become Plan-driven work.
_Avoid_: ad-hoc edit, small fix

**Claim**:
One independently verifiable outcome with its own acceptance, listed in a Plan or written as an unfinished ticket in the Plan's named scope. Code review and outcome verification each judge one Claim. A ticket is one place a Claim may be written, not a synonym for it; a ticket being "claimed" in a ticket workflow means someone took it and is unrelated.
_Avoid_: change, slice

**Implementation phase**:
The span from the user's authorization to implement until completion is reported, including code review and outcome verification. Discussion and planning before that authorization are outside it.
_Avoid_: execution, build phase

**Deviation**:
A difference between implemented work and its Plan. It is material when it changes the Plan's outcome, scope or acceptance.
_Avoid_: scope creep, drift

## Delegation

**Assignment**:
A bounded piece of work main hands to one native role, with its own brief. Only main creates Assignments; a role completes its Assignment itself and never splits it into further Assignments. One Claim may need several Assignments, and some work stays with main.
_Avoid_: subtask, job

**Delegation preview**:
Main's forecast of how it would carry out one or more Plans, or Unplanned work: each Claim's Assignments and the work main keeps, with the role, model and effort of each, followed once by the roles that perform the Automatic flow. Main produces it alone; it dispatches nothing, starts no review and writes nothing. It is the dispatch basis only in the session that made it: dispatch there may differ from it, and main reports the differences.
_Avoid_: dry run, delegation plan

## Review

**Review mode**:
The setting, `auto` or `off`, that decides whether the Automatic flow runs.
_Avoid_: auto review, review switch

**Automatic flow**:
The sequence plan review, then code review, then outcome verification that auto mode applies to Plan-driven work.
_Avoid_: three-layer protection, pipeline

**Explicit request**:
A user's direct request for one specific review or verification. It runs in either Review mode and runs only what was requested. In auto, a request for a step the Automatic flow is due to run is an automatic call, not an Explicit request. In auto, when it passes a step the Automatic flow had stopped, it clears the stop without resetting the count, and the Automatic flow resumes from there.
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
A Claim whose Code review stopped after two consecutive automatic calls without APPROVED. It is not complete. It is not landed on the default branch, released or reported complete.
_Avoid_: failed review, skipped review

**Unverified claim**:
A Claim that needs Outcome verification but has no currently valid CONFIRMED, for example because its Outcome verification has not run yet, was refuted, ended INCONCLUSIVE or stopped, or its CONFIRMED expired after a relevant change. It is not complete. It is not landed on the default branch, released or reported complete.
_Avoid_: failed verification

**Acceptance gate**:
The rule that a gated Claim, one of Plan-driven work in the Automatic flow or one an active handoff records as unreviewed or unverified, is landed, released or tagged, reported complete or has its ticket set to a completion value only with a valid APPROVED and a valid CONFIRMED. Committing it, and in auto pushing it to a branch main created and opening a pull request, are not gated; review state's Commits before the passes and Repository authority limit when main may do them.
_Avoid_: commit gate

**Landing**:
Putting a Claim on the remote default branch by pushing it there or merging it, directly or through a pull request. Opening a pull request is not landing, and permission to open one is not permission to merge it.
_Avoid_: shipping
