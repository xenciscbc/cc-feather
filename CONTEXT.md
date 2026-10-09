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
Work started without a Plan. In auto, Unplanned work that makes a Security-critical change, migrates data or is irreversible must first become Plan-driven work.
_Avoid_: ad-hoc edit, small fix

**Security-critical change**:
A change to a security guarantee at a trust boundary, or to the implementation or configuration of a security control, including where sensitive data goes and how untrusted data is interpreted downstream. Authentication, authorization, sessions and CSRF, credentials, cryptography, input validation and access control are typical examples, not a closed list.
_Avoid_: security boundary change, sensitive change

**Security-critical claim**:
A Claim whose outcome includes a Security-critical change. It is identified when the Plan is written or, for a Plan main did not write, before its first review.
_Avoid_: security claim

**Claim**:
One independently verifiable outcome with its own acceptance, listed in a Plan or written as an unfinished ticket in the Plan's named scope. Code review and outcome verification each judge one Claim. A ticket is one place a Claim may be written, not a synonym for it; a ticket being "claimed" in a ticket workflow means someone took it and is unrelated.
_Avoid_: change, slice

**Implementation phase**:
The span from the user's authorization to implement until completion is reported, including code review, outcome verification and, for a Security-critical claim, Adversarial review. Discussion and planning before that authorization are outside it.
_Avoid_: execution, build phase

**Deviation**:
A difference between implemented work and its Plan. It is material when it changes the Plan's outcome, scope or acceptance; discovering a security control or invariant the Plan lacks is also material, while touching boundary code the Plan already covers is not.
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
The sequence plan review, then code review, then outcome verification, and for a Security-critical claim then Adversarial review, that auto mode applies to Plan-driven work.
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

**Adversarial review**:
An independent attempt to break a Security-critical claim, made in the Automatic flow after it is approved and confirmed at the same commit, against disposable targets the brief names, answered HELD, BROKEN or INCONCLUSIVE. Outside the flow it needs no prior passes and, with no target, may be static. BROKEN means a vulnerability the change introduced or made exploitable, or a promised security fix that still reproduces; a pre-existing vulnerability becomes separate work and does not change the verdict.
_Avoid_: pentest, red team, security review

**Blocking finding**:
A Code review finding that holds completion: a correctness bug, security problem, data loss, regression or deviation from the Plan.

**Non-blocking finding**:
A Code review finding that does not hold completion: style, naming, a refactoring suggestion or an issue that predates the change. It is recorded as follow-up work.
_Avoid_: nit, minor issue

**Unreviewed claim**:
A Claim whose Code review stopped after two consecutive automatic calls without APPROVED. It is not complete. It is not landed on the default branch, released or reported complete. The only exception is the user's Accept and land decision.
_Avoid_: failed review, skipped review

**Unverified claim**:
A Claim that needs Outcome verification but has no currently valid CONFIRMED, for example because its Outcome verification has not run yet, was refuted, ended INCONCLUSIVE or stopped, or its CONFIRMED expired after a relevant change. It is not complete. It is not landed on the default branch, released or reported complete. The only exception is the user's Accept and land decision.
_Avoid_: failed verification

**Active handoff**:
An unfinished Feather handoff record for the work under the project's `.feather/handoffs/`. It is how unresolved verdicts and gate notes reach a resumed session.
_Avoid_: handoff file, notes

**Pending-acceptance claim**:
A gated Claim whose Active handoff note says it has passed one or more of the steps it needs (code review, outcome verification and, for a Security-critical claim, Adversarial review), or has an Accept and land decision, but is not yet landed, released or reported complete. It stays under the Acceptance gate until then, or until it is cancelled with its commits decided.
_Avoid_: approved claim, half-passed claim

**Acceptance gate**:
The rule that a gated Claim, one of Plan-driven work in the Automatic flow or one an active handoff records as unreviewed, unverified or pending acceptance, is landed, released or tagged, reported complete or has its ticket set to a done value only with a valid APPROVED and a valid CONFIRMED, and for a Security-critical claim a valid HELD as well, or with the user's Accept and land decision. Committing it, and in auto pushing it to a branch main created and opening a pull request, are not gated; review state's Commits before the passes and Repository authority limit when main may do them.
_Avoid_: commit gate

**Landing**:
Putting a Claim on the remote default branch by pushing it there or merging it, directly or through a pull request. Opening a pull request is not landing, and permission to open one is not permission to merge it.
_Avoid_: shipping

**Accept and land**:
The user's explicit, recorded acceptance of a named gated Claim without one or both passes, or of a Security-critical claim without its HELD, with the commit it accepts, the missing passes and the remaining risk, and for a missing HELD the known vulnerabilities. It satisfies the Acceptance gate for that Claim until a relevant change, is never READY, APPROVED, CONFIRMED or HELD, and a casual "done" becomes one only after main confirms and records it.
_Avoid_: sign-off, override
