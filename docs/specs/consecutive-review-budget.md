# Consecutive-failure review budget and re-review of verification fixes

Label: `ready-for-agent`

Vocabulary follows [CONTEXT.md](../../CONTEXT.md). Counts stay per session as recorded in [ADR 0002](../adr/0002-session-scoped-review-counts.md); this work changes what a count measures within a session.

## Problem Statement

In auto, each step of the Automatic flow allows two automatic calls in total per Plan or Claim. A pass does not give back the calls used before it. A Plan that passes plan review on its second call therefore has no call left when a Material deviation later needs another plan review, and the work stops for an Explicit request even though nothing has failed since the pass. A fix made after outcome verification returns REFUTED goes straight back to the verifier without Code review, so the code that fixes the failure is never reviewed. And the README does not say when a Plan is reviewed again during implementation or how the budget behaves, so users cannot predict when the flow stops for them.

## Solution

Each step counts consecutive automatic calls that did not pass, per Plan for plan review and per Claim for code review and outcome verification. A pass (READY, APPROVED, CONFIRMED) resets that step's count to zero. Two consecutive automatic calls without a pass stop the step: the work stops and waits for the user's explicit request, as it does today when the budget runs out.

A fix made after REFUTED goes back through Code review before the verifier rechecks it. Code review starts that fix with a fresh count, since its previous call passed. Outcome verification does not reset on a new fix, only on CONFIRMED, so a Claim refuted on two consecutive calls stops after one automatically rechecked fix round.

Both READMEs and the setup documentation explain the review rules a user needs: when a Plan is reviewed again during implementation (only a Material deviation, which also needs the user's approval), what does not trigger re-review, how the consecutive-failure budget works, and what that means for cost.

## User Stories

1. As a user in auto, I want a pass to reset a step's count, so that a later re-review is not refused because of failures that a pass already resolved.
2. As a user, I want a step to stop after two consecutive automatic calls without a pass, so that a failing review never loops without me.
3. As a user, I want plan review counted per Plan, and code review and outcome verification counted per Claim, so that one Claim's failures do not stop another Claim.
4. As a user, I want a Material deviation after READY to get a plan review with a fresh count, so that an approved change can be reviewed without an Explicit request.
5. As a user, I want a Material deviation still to need my approval of the revised Plan, so that resetting the count never lets the agent widen the work alone.
6. As a user, I want a fix made after REFUTED to go through Code review before the verifier rechecks it, so that no fixing code is left unreviewed.
7. As a user, I want Code review of that fix to start from a fresh count, so that a review that passed earlier does not consume the fix's review calls.
8. As a user, I want outcome verification's count to keep running across fixes and reset only on CONFIRMED, so that refute-fix-approve cycles cannot repeat forever.
9. As a user, I want a Claim refuted twice in a row to stop and wait for me, so that I decide what happens after one automatically rechecked fix round.
10. As a user, I want switching the reviewer, the model, the wording or renaming the Plan never to reset a count, so that only a real pass resets it.
11. As a user, I want failed, interrupted and protocol-failure calls still to count as calls without a pass, so that broken calls cannot be retried indefinitely.
12. As a user, I want Explicit requests still to sit outside the automatic count, so that asking for a review never changes the automatic budget.
13. As a user, I want counts still to be per session and unresolved verdicts still to cross sessions only through an active handoff, so that the session rules I know stay the same.
14. As a user, I want an Unreviewed claim to mean two consecutive Code review calls without APPROVED, so that the term matches the new budget.
15. As a user, I want the README to say when a Plan is reviewed again during implementation, so that I know which changes stop dependent work.
16. As a user, I want the README to say which adjustments do not trigger re-review, such as wording or changes within the approved scope, so that I do not expect needless reviews.
17. As a user, I want the README to describe the consecutive-failure budget and when the flow stops for me, so that I can predict interruptions.
18. As a user, I want the README's cost statement to reflect re-review of verification fixes and resets after a pass, so that I can estimate the maximum number of calls.
19. As a user reading the Traditional Chinese README, I want the same explanation as the English one, so that both audiences get the same rules.
20. As a user reading the setup documentation, I want its description of the automatic limits to match the procedures, so that the documents do not contradict each other.
21. As a maintainer, I want the decision and its rejected alternatives recorded in an ADR, so that a later reader knows why a pass resets the count and why verification does not reset on a fix.
22. As a user with an existing installation, I want the new rules from the plugin update alone, so that I do not need to rerun setup update.

## Implementation Decisions

- **One budget rule for all three steps.** Each step counts consecutive automatic calls without a pass: per logical Plan for plan review, per Claim for code review and per Claim for outcome verification. A pass (READY, APPROVED, CONFIRMED) resets that count to zero. Two consecutive calls without a pass stop automatic submission for that step, with the existing consequences: an Explicit request is required for another call; an unresolved verdict, open findings, an Unreviewed claim or an unverified Claim are kept and recorded in an active handoff as today.
- **Unchanged non-reset rules.** Failed, interrupted and protocol-failure calls count as calls without a pass. Mode changes, renamed Plans, cosmetic splits and a different reviewer, model or wording never reset a count. Counts remain per session (ADR 0002). Explicit calls remain outside the count.
- **Material deviation.** After READY, a Material deviation stops dependent work, gets plan review with the count that the pass reset, and still needs the user's approval of the revised Plan. If no automatic call remains because two consecutive plan reviews did not pass, the existing stop-and-report rule applies.
- **Verification fixes are code-reviewed.** After REFUTED, a fix goes to Code review first and then to the verifier's recheck. Code review counts from zero after its previous APPROVED. The existing rule that such a fix skips Code review and is reported as not code-reviewed is removed from both the code-review and outcome-verification procedures. The verifier's second call still rechecks the original failure plus a bounded regression check.
- **Verification does not reset on a fix.** Outcome verification's count for a Claim runs across fixes and resets only on CONFIRMED, so a Claim refuted on two consecutive calls stops after one automatically rechecked fix round. A Claim therefore makes at most six automatic calls (code review twice before and twice after the fix, verification twice), and a Plan with N Claims about 2 + 6N, plus up to two plan reviews for each Material deviation the user approves.
- **Second-call wording.** The procedures' references to "the second review" or "the second call" mean the call that follows a non-pass.
- **Only automatic passes reset.** An Explicit request's READY, APPROVED or CONFIRMED does not reset the automatic count, although it can still resolve an unresolved verdict as today.
- **Reviewing a fix.** Code review of a fix after REFUTED diffs against the Claim's original base revision, as for the first review, and is given the verifier's REFUTED findings and what changed since the APPROVED review.
- **Glossary.** Unreviewed claim is redefined as a Claim whose Code review stopped after two consecutive automatic calls without APPROVED.
- **ADR 0004** records the decision and notes that it amends ADR 0002's consequence that a resume may run up to two more automatic calls (a resume now starts a fresh consecutive count): a pass resets the count, two consecutive failures stop, fixes after REFUTED are code-reviewed, and verification does not reset on a new fix. Rejected alternatives: keeping a fixed total per Plan or Claim (a pass leaves no budget for an approved deviation); resetting verification on every fix (refute-fix-approve can loop without bound); keeping fixes outside Code review (fixing code goes unreviewed).
- **Documentation.** Both READMEs explain the review rules in their automatic review section: when a Plan is reviewed again (Material deviation, defined as a change to the Plan's outcome, scope or acceptance, which stops dependent work and needs the user's approval), what does not trigger re-review, the consecutive-failure budget, the fix path after REFUTED, and an updated cost statement. The setup documentation's description of the automatic limits is updated to match.
- **Delegation preview wording.** The preview procedure and the preview sections of both READMEs replace the fixed maximum of two calls per Plan or Claim with the consecutive-failure rule.
- **Superseded statements.** Earlier specs that state the fixed two-call budget or that a fix after REFUTED skips Code review (the plan-driven review spec and the delegation preview spec) get an "(Amended by ADR 0004 …)" note on each such statement, following the existing amendment notes in those specs.
- **Checked and unchanged.** The setup skill and its toggle procedure say toggling does not reset any automatic budget, and the delegation skill only defers to the procedures; both stay true and are not edited.
- **No installed change.** The installed delegation policy, role definitions, the setup skill and the configuration tool are unchanged; existing installations need only the plugin update and a fresh session.
- **Release.** The work ships as 0.12.0: the manifest version is bumped, the tag `v0.12.0` matches it, and the validation is recorded under its version heading in the setup validation log. The validation entry records the plan review and the code review and outcome verification of the first two claims; the release claim's own review results go in the completion report, not the log. Release changes pass code review and outcome verification before they are committed; the local tag is created on that commit afterwards and is not pushed without the user's go-ahead. Once the tag exists it is never moved or reused; a correction ships as 0.12.1.

## Testing Decisions

- Good tests assert the published contract: the rule statements in the shipped procedures, not their full wording.
- The seam is the existing configuration test module, which already checks the procedures' text (prior art: `test_explicit_reviews_are_outside_every_automatic_budget`). New or changed cases:
  - each of the three procedures states the consecutive-failure rule and that a pass resets the count;
  - the code-review and outcome-verification procedures no longer state that a fix after REFUTED skips Code review, and the outcome-verification procedure states that the fix goes to Code review first;
  - the outcome-verification procedure states that its count resets only on CONFIRMED.
- Existing tests that assert the explicit-call statements keep passing unchanged.
- READMEs and setup documentation are checked at acceptance by an independent verifier against the procedures, not by unit tests.
- Release checks: the full `unittest discover` suite and `claude plugin validate` for the plugin root and the manifest.
- Live model compliance with the new budget is not tested and is recorded as untested in the validation log.

## Out of Scope

- Hook-enforced counters; the budget remains model instructions.
- Changing the per-session scope of counts or the handoff recording rules (ADR 0002).
- Changing the installed delegation policy, role definitions, the setup skill or the configuration tool.
- Changing what counts as a Material deviation, or removing the user's approval of a revised Plan.
- Changing Explicit request behaviour.
- Changing the Delegation preview beyond its call-limit wording.

## Further Notes

- The Delegation preview procedure and its README sections describe "the maximum automatic calls: two per Plan and two per Claim". Under the consecutive rule that is no longer a total, so they are reworded to say each step stops after two consecutive calls without a pass.
- In auto, this spec is a Plan the user agreed to once confirmed, so its implementation goes through plan review, code review and outcome verification.
