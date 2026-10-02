# Plan-driven automatic review with a dedicated reviewer

Label: `ready-for-agent`

Vocabulary follows [CONTEXT.md](../../CONTEXT.md). The role decision is recorded in [ADR 0001](../adr/0001-dedicated-reviewer-role.md).

Status: part of this spec (plan-driven triggers and a code review step done by analyst) already exists as an uncommitted, verified change. This spec describes the complete target; the analyst code review mode is replaced by the reviewer role and is never released.

## Problem Statement

A user who turns on auto mode expects work done from a Plan to be protected before it is reported complete. Today auto mode is triggered by "material risk", a judgment the main agent makes on its own, so the same kind of work is reviewed one day and skipped the next. Implemented code gets an outcome check but no review of the code itself, so maintainability problems, hidden bugs outside the acceptance tests and deviations from the Plan can pass. When a review does find problems, there is no shared line between what must be fixed now and what can wait, and nowhere defined to keep what can wait.

Long waits are a second problem. When the main agent stops mid-implementation to ask the user something and the user is away, the conversation's context cache expires; resuming then costs more, and if the session is lost the progress since the last handoff update is gone.

## Solution

In auto mode, every piece of Plan-driven work goes through the same Automatic flow: Plan review before implementation, Code review of each Claim after its primary acceptance passes, then Outcome verification of that Claim. Unplanned work that changes a security boundary, migrates data or is irreversible must first become Plan-driven work through a reviewed Plan the user approves. Other Unplanned work is not reviewed automatically; the user asks when they want a review.

Code review is done by a new `reviewer` role that reads the diff itself, separates Blocking findings from Non-blocking findings, and answers APPROVED or CHANGES_REQUESTED within a two-call automatic budget. Blocking findings are fixed or rejected with evidence; Non-blocking findings become follow-up work. A Claim whose Code review runs out of calls without APPROVED is an Unreviewed claim and is not complete.

When an active handoff exists, the main agent updates it before stopping to wait for the user during the Implementation phase, and unresolved review verdicts are recorded in the handoff as plain text (amended by ADR 0002: counts are per session).

## User Stories

1. As a user in auto mode, I want every piece of Plan-driven work to be reviewed, so that protection does not depend on the agent's judgment of risk.
2. As a user, I want a plan file, spec, ticket, plan-mode plan or a plan I approved in conversation all to count as a Plan, so that I do not have to convert my plans into one format.
3. As a user, I want telling the agent to implement a given ticket or plan to count as my agreement, so that I am not asked to confirm twice.
4. As a user, I want a document without scope or acceptance not to count as a Plan, so that review always has something concrete to check against.
5. As a user, I want the agent to fill in missing scope or acceptance and confirm with me before treating a document as a Plan, so that weak tickets do not silently skip review.
6. As a user, I want unplanned security-boundary, data-migration or irreversible work to require a reviewed Plan I approve, so that the riskiest changes never start on the agent's own authority.
7. As a user, I want the agent never to approve its own Plan for such work, so that a human decides before irreversible changes.
8. As a user, I want small Unplanned work to go without automatic review, so that trivial edits stay fast and cheap.
9. As a user in auto mode, I want the agent to state before implementing whether the work is Plan-driven and therefore reviewed, so that a skipped review is a visible decision.
10. As a user in off mode, I want no such statement and no automatic review, so that off really means off.
11. As a user, I want an Explicit request for Plan review, Code review or Outcome verification to work in either mode, so that I can always ask for one check.
12. As a user, I want an Explicit request to run only what I asked for, so that asking for verification does not also start a code review.
13. As a user, I want an explicit verification request not to need a prior Code review, so that I can verify existing work directly.
14. As a user, I want "review" about implemented work to mean Code review and "review" about a Plan to mean Plan review, so that I do not have to name the procedure.
15. As a user, I want a Plan to list its Claims with their own acceptance, so that review boundaries are checked before implementation instead of chosen afterwards.
16. As a user, I want a Plan without listed Claims to be treated as one Claim, so that existing tickets work without rewriting.
17. As a user, I want Plan review to flag Claims cut too finely to verify independently, so that review cost stays proportional.
18. As a user, I want a revision within my approved outcome, scope and acceptance to proceed without asking me again, so that routine fixes do not interrupt me.
19. As a user, I want a material Deviation from the Plan to need my approval again, so that the work I approved is the work that gets done.
20. As a user, I want a re-review after a Deviation to share the Plan's existing two-call budget, so that renaming or splitting a Plan cannot reset it.
21. As a user, I want Code review to run only after the primary acceptance passes, so that review effort is not spent on incomplete code.
22. As a user, I want Code review to happen before Outcome verification, so that the verifier's limited calls check the final code.
23. As a user, I want Code review and Outcome verification to judge the same Claim, so that the two checks cover the same boundary.
24. As a user, I want the reviewer to get the diff itself from a base revision, so that the implementing agent cannot narrow what is reviewed.
25. As a user, I want the reviewer to include new untracked files, so that new code is not missed.
26. As a user, I want the reviewer to use history to tell a regression from an issue that predates the change, so that old problems do not block my work.
27. As a user, I want the reviewer to run static checks such as lint and type check, so that mechanical problems are caught cheaply.
28. As a user, I want the reviewer not to run the test suite, so that review does not duplicate verification or wait on slow tests.
29. As a user, I want the reviewer never to edit code, so that every change stays with the implementer and is re-verified.
30. As a user, I want any file the reviewer's commands change to be detected and reported, so that its no-edit rule is checked rather than trusted.
31. As a user, I want correctness bugs, security problems, data loss, regressions and Plan deviations to be Blocking findings, so that these always stop completion.
32. As a user, I want style, naming, refactoring suggestions and pre-existing issues to be Non-blocking findings, so that they do not hold up delivery.
33. As a user, I want every Blocking finding fixed or rejected with concrete evidence, so that findings are not dismissed by preference.
34. As a user, I want the reviewer to judge the agent's rejection evidence on its second call, so that a wrong rejection can be upheld.
35. As a user, I want the primary acceptance rerun after any review fix, so that a fix does not break the Claim.
36. As a user, I want at most two automatic Code review calls per Claim, counting failed or interrupted calls, so that review cannot loop.
37. As a user, I want changing the model or wording not to reset that count, so that the cap means something.
38. As a user, I want a Claim without APPROVED after two calls to be an Unreviewed claim that is not complete and is not committed, so that running out of calls never counts as passing.
39. As a user, I want automatic Outcome verification not to start for an Unreviewed claim, so that verification is not spent on code that failed review.
40. As a user, I want a fix made after the verifier refutes a Claim to go straight to the verifier's recheck, so that the two budgets do not interact.
41. As a user, I want the final report to say when such a fix was not code-reviewed, so that I know what was checked.
42. As a user, I want Non-blocking findings listed in the final report by default, so that I can decide whether to act on them.
43. As a user with an active handoff, I want Non-blocking findings collected into a separate follow-up work item, so that they do not clutter the current work and are not forgotten.
44. As a user, I want a Claim touching a security boundary to tell the reviewer which trust boundaries to check, so that security gets attention without an extra review layer.
45. As a user, I want the agent to update an active handoff before it stops to wait for me during the Implementation phase, so that a long wait or a lost session does not lose progress.
46. As a user, I want that update to be light — current conclusion, the pending question and the next step — and skipped when nothing changed, so that it costs little.
47. As a user, I want no such updates during discussion or planning, so that the handoff is not churned by conversation.
48. As a user without delegation installed, I want this handoff rule to apply anyway, so that cache expiry is handled regardless of review settings.
49. As a user, I want unresolved review verdicts and what they block kept in an active handoff, so that a resumed session does not commit or report an unresolved claim. (Amended by ADR 0002; counts are per session.)
50. As a user sharing handoff records with codex-feather, I want that note to need no runtime change, so that both tools keep reading the same records. (Amended by ADR 0002.)
51. As a user, I want a dedicated reviewer role, so that analyst keeps its tool-enforced read-only guarantee.
52. As a user, I want to set the reviewer's model and effort like other roles, so that I can trade review depth for cost.
53. As a user, I want the reviewer to default to opus with high effort, so that review is as rigorous as verification out of the box.
54. As a user of an existing installation, I want setup update to add the reviewer while keeping my model choices and review mode, so that upgrading needs no reinstall.
55. As a user, I want check and show to tell me when the reviewer is missing, so that I know an update is needed.
56. As a user who updated the plugin but not the setup, I want required Code review to be blocked rather than skipped, so that the protection does not silently disappear.
57. As a user who already has an agent named reviewer, I want setup to move the installation to its cc- prefix, so that my agent is not overwritten.
58. As a user, I want to export the reviewer in a session agents object, so that session overrides work for it.
59. As a user planning a downgrade, I want the docs to say that a version without the reviewer cannot read a state that records it, so that I remove or restore first.
60. As a maintainer, I want the review vocabulary defined in one glossary, so that docs and skills use consistent terms.

## Implementation Decisions

- **Trigger model.** Review mode keeps the values `auto` and `off`, so saved modes stay valid. (Amended by 53fe8ba: the automatic rules are a paragraph present only in auto; installations from earlier templates keep their mode line until setup update.) Only the meaning of `auto` changes, from risk-triggered to Plan-driven.
- **Automatic flow order.** Plan review, then implementation, then the primary acceptance run by main, then Code review, then main's acceptance rerun after any fix, then Outcome verification. The APPROVED prerequisite for verification applies only to the Automatic flow.
- **Budgets.** Plan review: two automatic calls per Plan. Code review: two per Claim. Outcome verification: two per Claim. Failed, interrupted and protocol-failure calls count, and changing reviewer, model or wording never resets a count within a session (amended by ADR 0002: a resumed session starts a new count). A verdict grants no authority beyond what the user already gave.
- **Claims.** A Plan declares its Claims and their acceptance. Plan review checks that each Claim can be verified independently and is not cut too finely. A Plan without listed Claims is one Claim.
- **Deviation.** Revisions inside the approved outcome, scope and acceptance continue without new approval; a material Deviation needs re-review within the Plan's budget and the user's approval.
- **New role `reviewer`.** It is a leaf role with Read, Glob, Grep and Bash, default model opus and effort high. Its brief contains the Claim, the Plan, a base revision, the file scope including untracked files, the acceptance results and, for security-boundary Claims, the trust boundaries to check. It may use read-only git commands and static checks that do not modify files; it does not run tests and never edits. It answers APPROVED or CHANGES_REQUESTED; each Blocking finding carries file and line evidence, why it blocks, the minimum correction and a closure check, and Non-blocking findings are listed separately. On a second call it checks only the closure of earlier findings, regressions from the fixes and main's rejection evidence. Main compares the workspace before and after each call.
- **analyst.** Its code review mode is removed; analyst keeps general analysis, security analysis and Plan review with read-only tools.
- **Installer.** `reviewer` joins the managed role set and the list of roles that an existing installation may lack. No state schema version change. Check and show report that an update is required while the role is missing; update adds it from package defaults and keeps saved choices. Name collisions use the existing cc- prefix migration. Model changes and session export cover the new role.
- **Delegation workflow.** Gains a Code review procedure and a reviewer row in its role table. Explicit verification requests route to the Outcome verification procedure without Code review; explicit Code review requests route to the Code review procedure without starting verification.
- **Managed delegation policy.** States the Plan-driven trigger, the risky Unplanned work rule, Explicit requests in either mode, and the auto-only statement before implementing.
- **Handoff maintenance policy and handoff skill.** During the Implementation phase, before stopping to wait for the user, an active handoff gets a light update (current conclusion, pending question, next step), skipped when nothing changed. No handoff is created only for this. Unresolved review verdicts and what they block are recorded as plain text in the record and removed once resolved (amended by ADR 0002; the fixed `審查：` segment was dropped). The handoff runtime and record schema do not change.
- **Follow-ups.** Non-blocking findings go in the final report; with an active handoff they become a separate follow-up work item under the handoff skill's existing separable-item rule.
- **Release.** Everything ships together as 0.9.0. The analyst code review mode in the working tree is never released.

## Testing Decisions

- Good tests drive the installer through its command-line interface and assert what a user would observe: deployed agent files, the managed instruction blocks, and the output of check and show. They do not inspect internal helpers.
- The only seam is the existing installer CLI used by the current configuration test suite.
- New cases, following the existing verifier added-role tests as prior art:
  - a fresh install deploys `reviewer` with Read, Glob, Grep and Bash and default opus/high;
  - an installation written with the seven-role set reports that an update is required, and update adds `reviewer` while keeping model choices and review mode;
  - six-role legacy states gain both verifier and reviewer on update;
  - an unowned agent named `reviewer` moves the installation to the cc- prefix and leaves that agent untouched;
  - model changes and session export work for `reviewer`;
  - deployed analyst has no code review mode;
  - the deployed delegation block states the Plan-driven trigger and the auto-only statement, and the deployed handoff block states the update-before-waiting rule.
- Existing helpers that assert the full unprefixed role set are updated to eight roles.
- Skill text that is not deployed (the delegation procedures and the handoff skill) is checked at acceptance by targeted searches and an independent verifier, not by unit tests.
- The handoff runtime's inherited test modules stay unchanged.
- Live model compliance with the flow is not tested and is recorded as untested in the validation log.

## Out of Scope

- Hook-enforced gates or counters; all rules remain model instructions.
- Timer-based handoff updates while waiting for the user; nothing can run between turns, and waking after the cache expires defeats the purpose.
- Creating a handoff solely to hold progress or review state.
- An extra security-analysis layer inside the Automatic flow.
- A per-Plan cap on the number of Claims.
- Changes to the handoff runtime, record schema or codex-feather compatibility contract.
- A state schema version bump or a migration of analyst content, since the analyst code review mode was never released.
- Running the test suite inside Code review.

## Further Notes

- Upgrading needs no remove: the plugin update plus one setup update adds the reviewer. Until that update, required Code review is blocked, so the Automatic flow stops instead of skipping a layer.
- Downgrading to a version without `reviewer` after an update needs remove with the newer plugin first, or a restore from the update's backup manifest.
- Two wording defects found while reviewing the uncommitted change are part of this work: explicit verification requests must route to their procedure, and the statement before implementing applies only in auto mode.
