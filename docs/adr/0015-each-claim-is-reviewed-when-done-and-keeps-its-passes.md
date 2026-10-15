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
