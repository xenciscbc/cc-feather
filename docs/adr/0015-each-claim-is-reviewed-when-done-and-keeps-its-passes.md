# Each Claim is reviewed when it is done, and keeps its passes

In auto, code review and outcome verification started once the reviewed Plan was implemented. A pass was reopened by any later change to its Claim's files, and most Plans have Claims that share files, so reviewing a Claim earlier would only have been reopened later. Reviews therefore waited until the whole Plan was implemented, and a problem in an early Claim was found only after later Claims were built on it. [ADR 0013](0013-only-what-a-claims-acceptance-needs-holds-its-completion.md) deferred per-Claim timing to separate work on retained passes.

This record is written in parts, each by the ticket that implements its rule, so that its implementation and reviews can check it against the procedures they change. This part records per-Claim timing.

The user decided (2026-10-14 and 2026-10-15; the [spec](../specs/retained-passes.md) carries the acceptance):

- **Per-Claim timing.** In the Automatic flow, each Claim's code review and then outcome verification run once that Claim is implemented and committed, replacing the rule that reviews start once the reviewed Plan is implemented. It is the only review timing in auto: no setting or Plan statement selects another. A single-Claim Plan is unchanged.
- **Still serial.** Implementation and reviews in one working tree stay serial, so a Claim with no dependency still waits for a review call running in the same working tree.
- **Dependent Claims wait.** A Claim that lists another under Blocked by, or otherwise depends on it as its Plan states, starts only after that Claim has valid APPROVED and CONFIRMED. Claims with no such dependency do not wait for other Claims' passes. Where a Plan states no dependencies between its Claims, main follows the Plan's order and treats each Claim as depending on those before it.
- **A stopped upstream Claim.** When a Claim's code review or outcome verification stops, its outcome verification cannot be resolved, it has a Deviation, or it would need Accept and land, every Claim that depends on it stops and main asks the user. The user may decide that named dependent Claims proceed; main records it under User decisions as a deferral of the upstream Claim whose scope names the dependent Claims allowed to start, and the upstream Claim stays a Pending-acceptance claim until the user's decision at the end of the Plan or until its passes become valid.

This amends [ADR 0013](0013-only-what-a-claims-acceptance-needs-holds-its-completion.md): per-Claim review timing, which it deferred to separate work on retained passes, is now the only review timing in auto. Off mode, the completion criteria, the serial rule, repository safety and the Execution rule are unchanged, and so are the installed policy and the reviewer, verifier, adversary, analyst and executor definitions.

## Considered Options

- **Review after the whole Plan is implemented**: a problem in an early Claim is found only after later Claims were built on it.
- **A setting or Plan statement that chooses the timing**: two timings double the rules and tests.

## Consequences

A problem in an early Claim is found before later Claims build on it. A Claim that depends on another waits for that Claim's passes, so when the upstream Claim stops, its dependent Claims wait for the user, who can let named ones proceed while the upstream Claim stays pending acceptance. Within one working tree, a Claim with no dependency still waits for a review call running there. These rules are instructions to the model, kept consistent by tests rather than enforced by a tool.

## Fixed passes

This part records fixed passes. A pass was reopened by any later change to its Claim's files, so when a later Claim's implementation or fix touched a shared file, every earlier Claim that had passed lost its code review and outcome verification and was reviewed again, even when the change touched nothing it relied on; each reopened review could surface its own findings, and each fix could reopen the next Claim.

The user decided (2026-10-14 and 2026-10-15, the second day after a security analysis; the [spec](../specs/retained-passes.md) carries the acceptance and its security invariants):

- **Passes stay fixed.** In auto, a Claim's valid APPROVED and CONFIRMED are a judgement of the commit they judged and are not reopened by a change to the Claim's files or to what they depend on that lies within the range judged by another Claim's completed code review and outcome verification of the same Plan, both of which passed; a fix Claim counts as another Claim. A Blocking finding in that other Claim's reviews is that Claim's to fix.
- **A fixed pass needs a passing review of the change.** A Claim's passes stay fixed only for a change inside that range. When that other Claim's review stops, is cancelled, is deferred or ends in Accept and land without both passes, its changes reopen the Claims whose files or dependencies they touch, under the earlier rules.
- **What still reopens.** Any other change keeps the earlier rules: an edit outside the Plan's Claims, a rebase, an environment or test target change, a change to the Claim's reading set, or a change whose Claim ends without both passes. What reopens a Security-critical claim's HELD is unchanged by this part.
- **Another Claim's acceptance checks.** A Claim may change a file that another Claim's acceptance checks run or read, such as its tests, expected values, fixtures, discovery or runner configuration and their support code, only where the changing Claim's own reading set states that it does; otherwise the change is a Deviation and a Blocking finding. Main decides which files these are from the changing Claim's commit, files it adds included, and counts a file it cannot rule out as one of them. When the changing Claim's diff changes such a file, its code review brief also carries the acceptance of each Claim whose checks the file serves, as a stated exception to the rule that a brief carries only the recorded reading set, and the reviewer checks from the diff that the change does not weaken that acceptance; a weakening is a Blocking finding. The installed reviewer definition is unchanged; the code review procedure states this in the brief.
- **Off mode and leaving auto.** Fixed passes hold in auto only, and off keeps the earlier rules. When automatic review is turned off for a Plan before the user's decision at the end of the Plan, every fixed pass whose Claim's files or dependencies another Claim changed after it is reopened under the earlier rules, and the cross-session rules of off apply from then on.
- **Limits.** A later Claim's reviewer reads only its own reading set and may not know an earlier Claim's design intent, and a property of an earlier Claim that no acceptance check the final check runs covers can be broken without the final check noticing.

Fixed passes are enough because every change that keeps a pass fixed has passed its own Claim's reviews, which judge that Claim's whole change, and the final check at the final commit still runs the acceptance checks of the Plan, so a Claim that breaks a checked behaviour of another is still caught there and fixed in the Claim that caused it; what those checks cannot see is stated under Limits. The brief carries another Claim's acceptance only for a change to that Claim's acceptance checks, because carrying every earlier Claim's acceptance into each later review would widen every review, and that change is the one case where the reviewer cannot judge a weakening without it.

This amends [ADR 0006](0006-review-state-validity-and-completion.md) (what a pass covers): in auto, a change to a Claim's files or dependencies within the range another Claim's passing code review and outcome verification of the same Plan judged no longer reopens the Claim's code review and outcome verification. ADR 0006's rule that a pass covers only the content it judged still holds for every other change and for every change in off.

Considered options for this part:

- **Keep file-level reopening in auto**: it chains reviews through shared files.
- **The Retention check**, an independent narrowed review of the earlier Claim plus a rerun of its primary acceptance: in projects whose Claims share test modules it almost always reopens outcome verification, its checks grow with the square of the Claims, and making it safe needed many extra rules.
- **Carry every earlier Claim's acceptance into later reviews**: it widens every review.

Consequences of this part: a later Claim's change to a shared file no longer restarts the reviews of earlier Claims, so a round no longer chains through every Claim that shares a file. A fixed pass rests on the review of the change that touched it, so a Claim whose reviews do not end with both passes reopens the Claims it touched, and turning automatic review off during a Plan reopens them too. What a later Claim's reviewer and the final check cannot see, stated under Limits, can land unnoticed. These rules are instructions to the model, kept consistent by tests rather than enforced by a tool.

## The final check and fix Claims

This part records the final check's reruns, fix Claims and the Plan's base revision. The final check ran the Plan's overall acceptance checks at the commit to be landed, and a failure reopened the Claims it affected; a failure that could not be attributed with evidence reopened every Claim the check covered, which under fixed passes would restart the reviews they keep. A finding that a later Claim's review reported as predating its change was only recorded, even when an earlier Claim of the same Plan had introduced it.

The user decided (2026-10-14 and 2026-10-15, the second day after a security analysis; the [spec](../specs/retained-passes.md) carries the acceptance and its security invariants):

- **Reruns.** Before the final check, main confirms that each Claim's reading set is unchanged from its recorded content or hash; a change the user did not authorise is a material Deviation. In auto the final check runs at the final commit, as before, and also reruns every Claim's primary acceptance there, taken from its recorded reading set, within repository safety's Execution rules.
- **Attributed failures.** A failure attributed with evidence to a Claim is fixed by that Claim: the fix goes through that Claim's code review and outcome verification, their counts continuing as for a reopened call, and no other Claim is reopened.
- **Fix Claims.** A failure that cannot be attributed with evidence is fixed as a fix Claim, and no Claim is reopened. A fix Claim is a Claim main adds to the Plan for one fix: its acceptance is that the failing check passes, or, for a defect a later Claim's review found, that the reported defect is fixed; its reading set is the Plan's text with that failure or defect; and it gets code review and outcome verification with counts of its own. Main adds it without asking, as it makes a fix today: it gets no plan review and no ticket; a fix beyond the Plan's scope is a Deviation. A fix Claim never changes the check whose failure it fixes or another Claim's acceptance checks; a fix that needs to is a Deviation and stops main to ask the user. A fix Claim that changes a security control is classified as Security-critical by what it does, and main still does not ask: it gets no Adversarial review and is disclosed at the end with its problem and a summary of the fix.
- **The stop.** The final check runs again after each fix. When it fails at as many different commits in a row as the Stop threshold in effect, without passing in between, main stops fixing and asks the user. The final check is still not a counted step; this stop only uses the Stop threshold's value.
- **The Plan's base revision.** Every brief of a Claim's code review, outcome verification and Adversarial review names, besides the Claim's base revision, the Plan's base revision, which main establishes itself from Git in this session. Main, not the role, judges from Git whether a finding a role reports as pre-existing was introduced after it; such a finding is a defect of the Plan or, for a broken security invariant, a BROKEN of the Claim whose invariant it breaks. When a later Claim's review finds a problem in an earlier Claim of the same Plan, a problem that predates the Plan's base revision is a Non-blocking finding that the later Claim fixes only when its own acceptance needs it; a defect introduced after it is not a pre-existing issue: the later Claim fixes it when its acceptance needs it, and otherwise main fixes it as a fix Claim, without reopening the earlier Claim. A later Claim that changes a security control is classified again as Security-critical by what the change does.
- **Off mode.** These rules hold in auto only: in off the final check keeps the earlier rules, a failure that cannot be attributed with evidence reopening every Claim the check covers.
- **Limits.** Acceptance items other than the primary acceptance, and acceptance checks that cannot be rerun, such as a manual check, are not repeated at the final commit.

The user accepted two residual risks with these rules (2026-10-15):

- **Check output.** Repository code that a check runs controls its own output, so it can make a check pass that should fail, hide that a check ran fewer tests, or make a failure point at the wrong Claim; the last only misdirects a fix, after which the final check runs again.
- **Security-critical fix Claims.** A fix Claim that changes a security control gets no plan review, security analysis or Adversarial review; it is disclosed at the end, and the user decides whether to land with it.

The reruns are what let passes stay fixed: every change that keeps a pass fixed has passed its own Claim's reviews, and the final check reruns every Claim's primary acceptance at the final commit, so a Claim that breaks another Claim's checked behaviour is still caught there, and the fix lands in the Claim that caused it. The stop counts failing commits rather than review calls because each fix can pass its own reviews, while fixes that break each other keep the final check failing at new commits.

This amends [ADR 0013](0013-only-what-a-claims-acceptance-needs-holds-its-completion.md) (the unattributed final check failure): in auto, a final check failure that cannot be attributed with evidence no longer reopens every Claim the check covers but is fixed as a fix Claim, and an attributed failure is fixed by its Claim without reopening any other. ADR 0013's final check, its preconditions and its fail-closed state are otherwise unchanged, and so are the completion criteria and repository safety.

Considered options for this part:

- **Reopen an earlier Claim for a defect it introduced**: it restores the chain fixed passes remove.
- **Count a fix's own review calls to stop fixes that break each other**: each fix can pass its own reviews, so the count never reaches the Stop threshold.
- **A new glossary term for a fix outside every Claim**: a fix Claim works as any Claim.
- **Ask the user before a fix Claim that changes a security control**: it stops the Plan for a fix whose purpose is to make it work, so it is disclosed at the end instead.
- **A forced fix round in which every Claim must pass a step before the next**: it adds a global ordering and ignores stops, INCONCLUSIVE, REJECT and deferral.

Consequences of this part: a failure at the end of the Plan no longer reopens every Claim; it is fixed once, in the Claim that caused it or in a fix Claim, and the final check catches a later Claim that broke an earlier Claim's primary acceptance. A defect an earlier Claim introduced is no longer written off as pre-existing, since main judges it against the Plan's base revision rather than the reviewing Claim's. Fixes that keep failing stop for the user at the Stop threshold's value. What the reruns cannot see, stated under Limits, and the residual risks above can land unnoticed or with only the disclosure at the end. These rules are instructions to the model, kept consistent by tests rather than enforced by a tool.
