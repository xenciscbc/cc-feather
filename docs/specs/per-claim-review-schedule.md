# Each Claim is reviewed as soon as it is implemented

Label: `ready-for-agent`

Vocabulary follows [CONTEXT.md](../../CONTEXT.md), whose Review schedule and Review group entries were added for this spec. It builds on [the claims-at-implementation spec](claims-at-implementation.md) and is implemented after it. The decisions were settled in a grilling with the user on 2026-10-13, on top of the user's decisions of 2026-10-10 recorded in the handoff `review-schedule-per-claim`; they are recorded in ADR 0013, written as part of this work. This is the second stage of that work; the first, the test module split, shipped on main after 0.20.0.

This spec has no Claims table: implementing it makes it one Claim against the Acceptance below, and cutting it into tickets first makes each ticket a Claim.

## Problem Statement

In auto, code review, outcome verification and Adversarial review start once the whole reviewed Plan is implemented. A defect in an early Claim is found only after every later Claim is built on it, and its fix then reopens the later Claims that share its files. In 0.20.0, C3's defect surfaced only after C4 was done, and the fix reopened C1, C2 and C4. Reviewing each Claim as soon as it is done would find such defects early, but because a pass reopens whenever a Claim's files change, reviewing Claims one by one while later Claims keep editing the same files makes passes reopen in a chain. Nothing today tells main which Claims to review together, when a downstream Claim may start, or what to do when the working tree changes while a review runs.

## Solution

In auto, each Claim is reviewed as soon as it is implemented: code review, then outcome verification and, for a Security-critical claim, Adversarial review. A Claim that depends on another starts only after that one has a currently valid pass.

For a Plan with more than one Claim, main makes a Review schedule when implementation starts. Claims expected to write the same files, or whose acceptance can only be checked with another done, form a Review group: they are implemented together and then each is reviewed on its own at the same commit. Every other Claim follows its `Blocked by` order. Plan review checks the schedule; an active handoff records it; it is never written into the spec or tickets and never changes the Claims. Main may regroup Claims not yet started, stating why and telling the user.

Within one working tree, reviews and implementation are serial: while a review call runs, main does not change that working tree. Main does not create worktrees for reviews on its own. Work the user already runs in separate worktrees proceeds in parallel, each worktree serial in itself.

Before landing or release, main runs the Plan's overall acceptance once at the final commit; a failure reopens the Claims it affects.

## Acceptance

1. **Per-Claim timing.** In auto, plan review and the review procedures state that each Claim, or each Review group once all its members are implemented, gets code review, then outcome verification and, for a Security-critical claim, Adversarial review, as soon as it is implemented and committed, instead of after the whole Plan. Off mode is unchanged.
2. **Downstream start.** A Claim with `Blocked by` dependencies, or placed after a Review group, starts implementation only when every Claim it depends on has a currently valid APPROVED and CONFIRMED, plus HELD for a Security-critical claim. An accept-and-land decision does not release a downstream Claim. Across sessions, a dependency whose ticket was set to a done value after valid passes, with no relevant change since, releases its downstream Claims; one set to a done value on an accept-and-land decision does not, and its downstream waits for passes in the current session or the user's decision. Independent Claims continue while a dependency is stopped or under review.
3. **Review schedule.** For a Plan with more than one Claim, main makes a Review schedule when implementation starts: its Review groups, each with its members and its reason (expected shared files, or an acceptance that needs another member done), and the order of the other Claims from their `Blocked by` lines. It goes into the plan-review brief, plan review judges it, and an active handoff records it. It is not written into the spec or tickets and never adds, splits or merges Claims. A Plan with one Claim needs none.
4. **Review groups.** Members are implemented in their internal dependency order, committed, and reviewed after the last one is done, each in its own code review, outcome verification and, where required, Adversarial review at the same commit. Each member keeps its own verdicts and counts and the Stop threshold applies to each.
5. **Regrouping.** Main may regroup Claims not yet started, stating the reason, telling the user and updating the handoff, without another plan review. Claims started or already passed keep their state; a change that touches a passed Claim's files reopens it under the existing rules.
6. **Dependency reopened.** When a dependency is reopened while a downstream Claim is being implemented, the downstream Claim may continue, but its reviews wait until the dependency passes again. The downstream Claim's briefs name the dependency commit they rely on, and a later change to what the downstream Claim depends on reopens it under the existing rules.
7. **Serial within a working tree.** While a code review, outcome verification or Adversarial review call runs, main does not change the working tree it judges, and implementation of the next Claim in that tree waits until the call ends. Main does not create a worktree for a review on its own. Work the user runs in separate worktrees may proceed in parallel, each worktree serial in itself; shared test resources stay governed by each brief's target start and reset.
8. **Final check.** Before landing or release, main runs the Plan's overall acceptance checks at the final commit, within repository safety's Execution rules. It is not a counted step. A failure reopens the Claims it affects, and landing and release wait for their passes again.
9. **Already implemented Claims.** When a Review schedule is made for a Plan with some Claims already implemented (Implemented before plan review, or auto turned on mid-Plan), the schedule covers the Claims not yet implemented; the implemented ones are reviewed first, those sharing files as one Review group at the current commit and the rest in `Blocked by` order, and their downstream Claims start under item 2.
10. **Preview.** The Delegation preview lists the Review schedule it expects, marked as a forecast that binds nothing; the binding schedule is the one made when implementation starts.
11. **Glossary and ADR.** `CONTEXT.md`'s Review schedule and Review group entries state the rules above (already added; checked, not rewritten). ADR 0013 records the decision and its rejected options.
12. **READMEs.** `README.md` and `README.zh-TW.md` explain per-Claim timing, the Review schedule with an example of a Review group and a downstream Claim, serial work within a working tree, and the final check; both say the same thing and match the procedures, and the cost explanation states how a Review schedule affects it.
13. **Tests.** Contract tests pin the new statements and fail on the text before this spec; pins of replaced statements (review after the whole Plan) are updated or become absence pins; the full suite passes in both discovery forms.
14. **Live rehearsal.** With the installed roles of the candidate, main runs a disposable three-ticket Plan in auto: two tickets writing the same file form a Review group and the third is blocked by one of them. The record shows the Review schedule judged by plan review, the group reviewed at one commit with separate calls, the third ticket starting only after its dependency's passes, no working-tree change during a review call, and the final check. The rehearsal, its environment and its result are recorded in the release's validation entry; a deviation from the rules is a finding, not a pass.
15. **Release.** The plugin version is the next one after the claims-at-implementation release (0.24.0, unless the user releases both specs together); `claude plugin validate .` passes; `docs/setup-validation.md` gains the release entry with test counts and skips, the rehearsal, the review round and the note that only the plugin update is needed; the tag is created after the user's go-ahead, only after checking that it matches `plugin.json` at the tagged commit and does not already exist.

## User Stories

1. As a user, I want each Claim reviewed as soon as it is done, so that a defect is found before later Claims build on it.
2. As a user, I want a downstream Claim to wait for its dependency's valid passes, so that it is not built on code that may still change.
3. As a user, I want independent Claims to continue while another is under review or stopped, so that one stopped Claim does not stall unrelated work.
4. As a user, I want Claims that write the same files reviewed together, so that reviewing one does not reopen another in a chain.
5. As a user, I want each Review group to carry a stated reason, so that I can see why Claims were grouped and challenge it.
6. As a user, I want plan review to check the Review schedule, so that a poor grouping is caught before implementation.
7. As a user, I want the Review schedule kept out of my spec and tickets, so that the documents I agreed to are not edited for scheduling.
8. As a user, I want the Review schedule never to add, split or merge Claims, so that the Claims stay what I named.
9. As a user, I want each member of a Review group to keep its own verdicts and counts, so that grouping does not hide a failing Claim.
10. As a user, I want an accept-and-land decision not to release downstream Claims, so that accepting a risk on one Claim does not let others build on it unreviewed.
11. As a user resuming in a new session, I want a dependency accepted with valid passes to release its downstream ticket, so that finished work is not reviewed again before the next ticket starts.
12. As a user, I want main to regroup Claims not yet started when the schedule proves wrong, and tell me, so that a bad forecast does not force needless reopening.
13. As a user, I want regrouping never to touch started or passed Claims, so that it cannot be used to escape a review.
14. As a user, I want a downstream Claim to keep going when its dependency is reopened, with its reviews waiting, so that work already done is not thrown away.
15. As a user, I want a downstream Claim's briefs to name the dependency commit they rely on, so that a review judges against the right version.
16. As a user, I want main not to change a working tree while a review of it runs, so that every pass judges exactly the commit it names.
17. As a user of a project with costly setup, I want main not to create worktrees for reviews on its own, so that reviews do not trigger reinstalls or rebuilds.
18. As a user who already works in several worktrees, I want them to proceed in parallel, so that the serial rule does not slow down work I separated myself.
19. As a user, I want one overall acceptance run at the final commit before landing or release, so that a dependency main missed is still caught.
20. As a user, I want that final run not to count toward the Stop threshold, so that it does not stop the flow by itself.
21. As a user turning auto on mid-Plan, I want implemented Claims reviewed first with the same grouping rule, so that the schedule covers the whole Plan consistently.
22. As a user, I want the Delegation preview to show the expected Review schedule, so that I can judge the cost before asking for implementation.
23. As a user in off mode, I want nothing to change, so that reviews still run only when I ask.
24. As a user reading either README, I want the schedule explained with an example, so that I know when reviews will happen.
25. As a maintainer, I want the decision and its rejected options in ADR 0013, so that later readers know why reviews run per Claim.
26. As a maintainer, I want a live rehearsal with the installed roles, so that the rules are seen being followed, not only stated.
27. As a user with an existing installation, I want the change from the plugin update alone, so that I do not need to rerun setup update.

## Implementation Decisions

- **Where the rules live.** Plan review states per-Claim timing, the Review schedule it judges and the downstream start rule, replacing "once the reviewed plan is implemented". Review state carries Review groups, regrouping, a reopened dependency, the serial rule, the final check and already implemented Claims, beside its existing validity and completion rules. Code review, outcome verification and Adversarial review state when a Claim or Review group is ready for them. The delegation skill's rule on parallel work gains the serial rule for review calls. The preview gains the forecast schedule.
- **Grouping criterion.** A Review group is formed when Claims are expected to write the same files, or one's acceptance can be checked only with another done. A `Blocked by` line alone orders Claims without grouping them. Because reopening stays file-level, a Plan whose Claims all touch a shared file becomes one group, which matches today's behaviour; finer reopening is out of scope.
- **Reviews of a group.** Each member gets its own call with its own brief; installed role definitions and their report formats are unchanged.
- **Regrouping is not a deviation.** A Review schedule does not change a Plan's outcome, scope or acceptance, so regrouping is not a material deviation and needs no plan review; it must be visible to the user and recorded.
- **Serial rule.** It follows from the existing rule that a gated pass judges a workspace equal to the commit its brief names and unchanged during the call; this spec makes main's behaviour explicit. A worktree the user set up for parallel work is its own workspace.
- **Final check.** It is main's own run of the Plan's overall acceptance, such as the full test suite, not a review step, and it does not count. It adds no new verdict: its failure reopens Claims under the existing rules.
- **Unchanged.** Reopening stays file-level. The Stop threshold, counts per session, Unknown state, cross-session rules, the acceptance gate, composed Adversarial review and ticket status rules are unchanged. Installed role definitions, the installed policy, the handoff skill and the configuration tool are unchanged.
- **ADR 0013** records per-Claim timing with Review schedules. Rejected: reviewing after the whole Plan (late defects and chained reopening after fixes); writing the schedule into the Plan (main would edit documents the user agreed to); relying on the planning step to merge coupled work into one ticket (tickets are cut for independent verification, not for shared files); one call reviewing a whole group (changes installed roles and breaks per-Claim reading); review worktrees created by main (setup cost in other projects); worktree-parallel implementation and dependency-precise reopening (deferred until needed).

## Testing Decisions

- The seam is the existing contract tests on shipped text: key-phrase pins in the procedures and paired pins in both READMEs, with absence pins for removed wording. Prior art: the Stop threshold procedures, review-state rules and claim-source tests.
- New pins assert: per-Claim timing; the Review schedule's content, its plan review and its exclusion from specs and tickets; the grouping criterion; separate calls per member; the downstream start rule, including accept-and-land and the cross-session case; regrouping; a reopened dependency; the serial rule and its worktree exception; the final check and that it is not counted; already implemented Claims; the preview's forecast. Each fails on the text before this spec.
- The live rehearsal is the second seam, needed because these rules depend on main's conduct: it runs once at the candidate with the installed roles, in a disposable repository outside the project, and is recorded, not automated.
- READMEs, `CONTEXT.md` and the ADR are checked at outcome verification against the procedures.
- Release checks: the full suite in both discovery forms and `claude plugin validate .`.

## Out of Scope

- Worktree-parallel implementation within one Plan, and how passes carry over when branches from separate worktrees are merged; the final check is the only safeguard this spec adds for merged work.
- Reopening by precise dependency instead of by file.
- Wording and test items in the follow-up cleanup record, including the review-state, README Budget, Adversarial review and RETIRED-pattern items.
- Live rehearsal of other review scenarios, which remain with the handoff `review-live-rehearsal`.
- Off mode, Claim sizing and what a Claim's reviews read, which the claims-at-implementation spec settles.

## Further Notes

- Security-critical classification of this spec's Claims happens before its first plan review. It changes when Adversarial review runs and what releases downstream work, so it may be classified as Security-critical, which would bring a security analysis before plan review.
- The `CONTEXT.md` entries were added during the grilling, on the claims-at-implementation branch, and should be committed with this spec's implementation.
- The grilling's decisions are recorded in the handoff `review-schedule-per-claim`.
- Rollback: before anything is pushed, the unpushed commits can be dropped with the user's agreement; after the release, a user reinstalls the previous version.
