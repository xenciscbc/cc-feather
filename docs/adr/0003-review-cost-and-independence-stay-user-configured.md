# Claim granularity, review cost and reviewer independence stay outside the review flow

In auto, every Claim of plan-driven work gets its own code review and outcome verification on opus/high roles, and those roles usually share the main session's model. That raised two concerns: cost grows with the number of Claims, and fresh context does not remove blind spots a shared model has. We kept the review flow and package defaults unchanged. How finely a Plan is cut into Claims is decided by whatever produced the Plan, such as a spec, planning or ticket-splitting skill, not by cc-feather; cost and model diversity are role settings the user chooses with cc-feather:model.

## Considered Options

- **Let main merge related Claims into one review or verification at review time**: main would decide what counts as related while it also wants to save calls, so the judgment is unreliable and tends to over-merge.
- **Add granularity rules to plan review**, such as having analyst also flag Claims bundled too coarsely: Claim sizing is a planning decision that belongs to the skill or person writing the Plan; cc-feather reviews the Plan it is given. Analyst's earlier check that Claims are not cut too finely is removed for the same reason; its check that each Claim is independently verifiable with its own acceptance stays, because review and verification judge one Claim at a time.
- **Skip a step for some Claim types**: changes the review contract rather than its configuration; ADR 0001 already keeps code review and verification separate.
- **Lower package defaults, for example a cheaper reviewer or verifier**: setup update keeps saved role choices, so existing installations would not change, and whether a weaker or lower-effort role misses more defects is unmeasured.
- **Require review roles to run on a model different from main**: setup does not know the main model, and CLI, managed or environment settings can make children use it anyway, so the rule could not be enforced or verified.
- **Use another vendor's model by default**: not every user has one; it remains an explicitly requested second opinion.

## Consequences

The README tells users how many automatic calls auto makes and how to lower cost or add model diversity with cc-feather:model, for example a lower verifier effort or a different analyst or reviewer model. Switching a role's model never resets a step's two-call budget. Plans whose Claims are too fine or too coarse are fixed where the Plan is written. Revisit if measured cost, missed defects or retry rates show a default should change.

(Amended by ADR 0010: the two-call budget is the value at the default Stop threshold of 2; the Stop threshold is now one user-configurable number from 2 to 10, the README gives the number of automatic calls in terms of it, and switching a role's model never resets a step's count toward it.)
