# Review budgets count consecutive failures, and verification fixes are code-reviewed

Each step of the Automatic flow allowed two automatic calls in total per Plan or Claim, so a Plan that passed plan review on its second call had nothing left when an approved Material deviation needed another review, and a fix made after REFUTED went straight back to the verifier without Code review. We now count, per step, consecutive automatic calls without a pass: per Plan for plan review, per Claim for code review and outcome verification. An automatic READY, APPROVED or CONFIRMED resets that count to zero, and two consecutive automatic calls without a pass stop the step for the user's explicit request, as before. A fix after REFUTED goes through Code review, counted from the reset of its earlier APPROVED, before the verifier rechecks it. Outcome verification's count runs across fixes and resets only on CONFIRMED, so a Claim refuted twice in a row stops after one automatically rechecked fix.

The other non-reset rules stay: failed, interrupted and protocol-failure calls count, and mode changes, renamed Plans, cosmetic splits and a different reviewer, model or wording never reset a count. Only an automatic pass resets; an Explicit request stays outside the count. Analyst's statement that its verdict does not reset the review budget stays true, because main applies the reset under the procedure.

## Considered Options

- **Keep a fixed total per Plan or Claim**: a pass would leave no automatic review for a Material deviation the user approves later, so an approved change would always wait for an Explicit request even though nothing had failed.
- **Reset verification's count on every fix**: a refute, fix, approve cycle could repeat without bound, with no point at which the user is asked.
- **Keep fixes after REFUTED outside Code review**: cheaper, but the code that fixes a refuted Claim would never be reviewed.

## Consequences

A Claim makes at most six automatic calls: code review twice before the fix and twice after it, and verification twice. A Plan with N Claims makes about 2 + 6N, plus up to two plan reviews for each Material deviation the user approves and the calls for any Claims such a deviation reopens. Every pass still needs a fresh-context call, and the user still approves every Material deviation, so a reset never lets the agent widen the work alone.

This amends ADR 0002's consequence that a resume may run up to two more automatic calls for the same Plan or Claim: a resume now starts a fresh consecutive count, and the rest of ADR 0002 is unchanged. It also amends ADR 0003's wording that switching a role's model never resets a step's two-call budget: switching still never resets the count of consecutive calls without a pass. The setup skill's statement that toggling never resets any two-call automatic budget stays true when the two calls are read as the stopping threshold. Earlier specs carry amendment notes where they state the old budget.
