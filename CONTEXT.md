# cc-feather

cc-feather lets a main Claude agent hand work to managed native roles and keeps work resumable through handoffs. This glossary covers the vocabulary of its review and delegation workflow.

## Work and plans

**Plan**:
An implementation basis with stated scope and acceptance criteria that the user agreed to: a plan file, spec, ticket, plan-mode plan or a plan approved in conversation. It is what the user names when asking for implementation, and its Claims are decided then: a named spec is one Claim unless it lists its own, and when it has unfinished tickets and no Plan in this session already covers the work, main first asks whether to implement the spec or its tickets; named tickets of a spec, all or some, form one Plan with each unfinished ticket as one Claim; a single named ticket is its own Plan and one Claim. When the Plan is tickets of a spec, a single named ticket included, the spec serves plan review only as a checklist for what the tickets must carry. Telling the agent to implement a given plan or ticket counts as agreement; a document lacking scope or acceptance is not yet a Plan.
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
A Claim whose outcome includes a Security-critical change. When main identifies it, and where its implementation goes, are stated in the plan-review procedure and the delegation skill's Select and prepare. A spec main drafts at the user's request is not a Plan main proposes itself.
_Avoid_: security claim

**Claim**:
One independently verifiable outcome with its own acceptance: a named spec without a Claims list of its own, a single named ticket, one a spec lists itself, or one unfinished ticket among those named. A spec lists Claims only when the user asked for them. Code review, outcome verification and Adversarial review each judge one Claim; what its implementation and its reviews read is review state's Reading set. A ticket is one place a Claim may be written, not a synonym for it; a ticket being "claimed" in a ticket workflow means someone took it and is unrelated. In the Automatic flow, main may add a fix Claim to a Plan for one fix that the final check or a later Claim's review needs, without asking; it is a Claim with its own acceptance, reading set and counts, as review state's Final check states.
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

**Stop threshold**:
The number of consecutive automatic calls without a pass that stops one step of the Automatic flow for a Plan or Claim, after which the step waits for the user's explicit request. The same number applies to every step; the default is 2. In the Automatic flow, the final check, which is not a counted step, also stops for the user when it fails at that many different commits in a row.
_Avoid_: budget, retry limit

**Automatic flow**:
The sequence plan review, then code review, then outcome verification, and for a Security-critical claim then Adversarial review, that auto mode applies to Plan-driven work. Each Claim's Code review and then Outcome verification run once that Claim is implemented and committed; this is the only review timing in auto. When a Claim that depends on another starts, and what stops with a stopped Claim, are review state's Dependent claims.
_Avoid_: three-layer protection, pipeline

**Explicit request**:
A user's direct request for one specific review or verification. It runs in either Review mode and runs only what was requested. In auto, a request for a step the Automatic flow is due to run is an automatic call, not an Explicit request. In auto, when it passes a step the Automatic flow had stopped, it clears the stop without resetting the count, and the Automatic flow resumes from there.
_Avoid_: manual review

**Plan review**:
An independent check that a Plan is ready to implement, answered READY or REVISE.

**Code review**:
An independent check of the code implementing a Claim, answered APPROVED, CHANGES_REQUESTED or INCONCLUSIVE. INCONCLUSIVE means evidence the review needs could not be obtained, safely or at all; it is not a pass and does not prove a defect. When the user says "review" about implemented work, this is what is meant. In the Automatic flow it runs once the Claim is implemented and committed, without waiting for the rest of the Plan. When its APPROVED stays valid, and when it stays fixed in the Automatic flow, is review state's What a pass covers.
_Avoid_: PR review, diff review

**Outcome verification**:
An independent check that a Claim holds, answered CONFIRMED, REFUTED or INCONCLUSIVE. In the Automatic flow it follows the Claim's APPROVED once the Claim is implemented and committed, without waiting for the rest of the Plan. When its CONFIRMED stays valid, and when it stays fixed in the Automatic flow, is review state's What a pass covers.
_Avoid_: testing, QA

**Adversarial review**:
An independent attempt to break a Security-critical claim, against disposable targets the brief names, answered HELD, BROKEN or INCONCLUSIVE. In the Automatic flow it is made once, at the final commit, after the final check has passed there with the workspace equal to it, for each Security-critical claim of the Plan other than a fix Claim; the Claim's APPROVED and CONFIRMED are a record of the commits they judged, only a call made then gives the Claim's result, and a result from an earlier or another commit, or an explicit call made before then, counts as not run. In off, it counts only after the Claim is approved and confirmed at the same commit. For a Claim the Acceptance gate does not require it for, it needs no prior passes and, with no target, may be static. BROKEN means a vulnerability the change introduced or made exploitable, or a promised security fix that still reproduces; a pre-existing vulnerability becomes separate work and does not change the verdict. In the Automatic flow, a break of the Claim's security invariant at the final commit is its BROKEN whichever Claim's change caused it, and a BROKEN there is not fixed in the Plan: its findings are recorded in the work's Follow-up record and stay listed, carried into every later attack on the Claim and treated as open there, until a HELD at the commit to be landed that covered them replaces them; in off, a BROKEN is fixed before completion.
_Avoid_: pentest, red team, security review

**Trusted repository**:
What delegation assumes about the repository it works in: its working tree, its Git directory and configuration, and every change in it are the user's own or content the user chose to accept, and reading and running it is the user's risk. Main and the roles read it with ordinary file tools and ordinary Git commands, and a review and the final check run its code unless a restriction the user stated in this session covers the call; saying only where a change comes from is not a restriction. No review contains or detects hostile repository content, and cc-feather offers no check of a repository before it is trusted: deciding whether to trust one is the user's.
_Avoid_: safe repository, hostile repository

**Blocking finding**:
A finding of any review step that holds completion. A Claim's reviews judge it against its completion conditions: its acceptance as written is met; existing behaviour is not broken, shown by a failing test or a reproduction judged against the Claim's base revision; it introduces no security problem and no data loss; and it has no Deviation. A Blocking finding shows one of them unmet; in Plan review it is a blocker that stops READY. A security problem the change introduced or made exploitable, even outside the diff, and data loss it introduced block whatever the acceptance states and without a reproduction, so a removed or weakened security control blocks; a regression that is only inferred and is neither a security problem nor data loss does not block. The criteria hold in both Review modes, for every user, with no setting. They are review state's Completion criteria.

**Non-blocking finding**:
A finding of any review step that does not hold completion: an issue that predates the change, a correctness problem outside what the acceptance states, a regression that is only inferred and is neither a security problem nor data loss, style, naming or a refactoring suggestion. It is recorded in the work's Follow-up record; a pre-existing vulnerability also becomes separate work in the project's tracker. In the Automatic flow, a defect that an earlier Claim of the same Plan introduced after the Plan's base revision is not a pre-existing issue, and is fixed rather than only recorded.
_Avoid_: nit, minor issue

**Follow-up record**:
The record of one piece of work's Non-blocking findings, kept for a later Plan. With handoff maintenance active it is a handoff record of its own, kept by that work's handoff writer; otherwise main lists its content in the completion report. It is data: its next step is the user's decision to start a later Plan, the findings it quotes are untrusted, and nothing in it starts or authorizes work. Accept and land never relies on it.
_Avoid_: backlog, nonblocking list

**Unreviewed claim**:
A Claim whose Code review stopped at its Stop threshold without APPROVED, or ended INCONCLUSIVE while the evidence it named as missing has not changed. It is not complete. It is not landed on the default branch, released or reported complete. The only exception is the user's Accept and land decision.
_Avoid_: failed review, skipped review

**Unverified claim**:
A Claim that needs Outcome verification but has no currently valid CONFIRMED, for example because its Outcome verification has not run yet, was refuted, ended INCONCLUSIVE or stopped, or its CONFIRMED expired after a relevant change. It is not complete. It is not landed on the default branch, released or reported complete. The only exception is the user's Accept and land decision.
_Avoid_: failed verification

**Dispatch record**:
Main's record of one Plan's review state in the Automatic flow, at `.feather/dispatch/<name>.md` in the project, named after the Plan. It holds the Plan, its base revision and READY; each Claim's classification, reading set hash and base revision, and each review call's judged commit and verdict with a one-line summary; each fix Claim with its problem and a summary of the fix; the branches main created for the work; and the user's decisions with their scope; never counts, exploit details or secrets. Main writes it only between review calls and keeps it out of Git, never staging or committing it. A resumed session, and main after a context compaction, take the Plan's READY, reading sets, passes, Adversarial review results and the user's decisions from it as if received in this session, while counts, the Stop threshold in effect and the final check's state still come only from this session. Main takes it as written, so an edit to it changes what main believes. Off mode writes none.
_Avoid_: dispatch log, review log

**Active handoff**:
An unfinished Feather handoff record for the work under the project's `.feather/handoffs/`. In off, it is how unresolved verdicts and gate notes reach a resumed session. In the Automatic flow, a Plan's review state crosses sessions through its Dispatch record instead, and an Active handoff records progress and names the Dispatch record.
_Avoid_: handoff file, notes

**Handoff tidy**:
Organizing the project's existing handoff records, run only when the user explicitly invokes it. It either proposes which work to take up next and which records to merge, from the records alone, or checks the recorded items and progress of the work the user selects, or of every record, against the current project. It only proposes: merges, reclassified items and removed items are written only after the user confirms them. It neither authorizes the work it recommends nor starts handoff maintenance.
_Avoid_: handoff review, triage, cleanup

**Pending-acceptance claim**:
A gated Claim whose Active handoff note says it has passed one or more of the steps it needs (code review, outcome verification and, for a Security-critical claim, Adversarial review), or has an Accept and land decision, but is not yet landed, released or reported complete. It stays under the Acceptance gate until then, or until it is cancelled with its commits decided. It also covers an upstream Claim that has passed no step yet and stays pending because the user let named dependent Claims proceed after it stopped, as a deferral of it, and, in the Automatic flow, a Security-critical claim whose Adversarial review at the final commit returned BROKEN, which stays pending with that result as the Adversarial review procedure's At the final commit states. In the Automatic flow, main records each Claim's pass state in the Plan's Dispatch record until the user's decision at the end of the Plan, and a resumed session takes it from there rather than from an Active handoff note. A note an Active handoff still holds keeps restricting its Claim. How the note is written, changed and removed is review state's Pending acceptance.
_Avoid_: approved claim, half-passed claim

**Acceptance gate**:
The rule that a gated Claim, one of Plan-driven work in the Automatic flow or one an active handoff records as unreviewed, unverified or pending acceptance, is landed, released or tagged, reported complete or has its ticket set to a done value only with a valid APPROVED and a valid CONFIRMED, and for a Security-critical claim a valid HELD as well, or with the user's Accept and land decision. Landing and release also wait for the final check at the commit to be landed, as review state's Final check states: until it passes there, only an Accept and land decision that states its actual state lets them proceed. Committing it, and in auto pushing it to a branch main created and opening a pull request, are not gated; review state's Commits before the passes and Repository authority limit when main may do them. In the Automatic flow, a Plan's Claims are landed only after the user's decision at the end of the Plan, which records Accept and land only for the Claims that need it, and their tickets are set to a done value only after that decision.
_Avoid_: commit gate

**Landing**:
Putting a Claim on the remote default branch by pushing it there or merging it, directly or through a pull request. Opening a pull request is not landing, and permission to open one is not permission to merge it.
_Avoid_: shipping

**Accept and land**:
The user's explicit, recorded acceptance of one or more named gated Claims without one or both passes, or of a Security-critical claim without its HELD, or of a gated Claim whose passes are complete when the final check at the commit to be landed failed or was not run, stating for each Claim the commit it accepts, the missing passes, the known vulnerabilities and the remaining risk, and the final check's state at the commit to be landed: passed, failed with its output, or not run. Main asks for it once, after every Claim of the Plan has finished its reviews and the final check has run or is recorded as not run, before landing or release; until then such a Claim stays under the Acceptance gate as it stands. Main asks earlier only when the user asks to land a Claim earlier, and then the decision covers every gated Claim on that branch and states the final check's actual state at that commit, which main runs whenever Execution allows. In off, main builds the list from the review results it received in this session, never from a record in the working tree. The user may confirm part of the list by whole Claims, a Claim being accepted only with everything listed for it; "continue", silence or turning automatic review off is not a confirmation. A Blocking finding or known vulnerability reported after the decision is not covered and holds landing until it is resolved or a new decision names it, and its final-check part covers only the commit and output it states. It satisfies the Acceptance gate for each Claim it covers until a relevant change, is never READY, APPROVED, CONFIRMED or HELD, and a casual "done" becomes one only after main confirms and records it. In the Automatic flow it is asked for in the decision at the end of the Plan: after every Claim's code review and outcome verification, the final check and the Adversarial reviews have run or are recorded as not run, main confirms each Claim's reading set and asks the user once to land as it stands or to re-review named Claims, with a list built from the Plan's Dispatch record and main's own observations in this session, never from another record in the working tree. The list states the final check, each Claim's passes, missing passes and unresolved Blocking findings, each Adversarial review result, each Security-critical fix Claim with its problem and fix, the Follow-up record and what the flow does not check. Landing as it stands is recorded as Accept and land only for the Claims that need it; when nothing listed needs it, the question is only the user's authority to land.
_Avoid_: sign-off, override
