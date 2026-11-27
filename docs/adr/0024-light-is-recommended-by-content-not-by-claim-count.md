# `light` is recommended by the content of a Plan's Claims, not by their number

[ADR 0023](0023-a-plans-review-level-is-the-users-choice.md) let main recommend `light` only for a Plan of one Claim with a known cause and a small scope. The rules of `light` already handle several Claims, and off mode, which `light` runs in, reopens a Claim's code review when another Claim changes its files; only the recommendation counted Claims. The count stood in for what plan review catches across Claims, one Claim building on another's design or Claims that together miss the spec's outcome, and gave no reason of its own. A Plan of three independent wording fixes had to be split into three Plans to be recommended `light`.

The user decided (2026-11-27) that main recommends `light` for a Plan whose Claims each have a known cause, a small scope and acceptance that shows its outcome directly, none of which builds on another's design, as a Claim that lists another under `Blocked by` does, and none of which is a Security-critical claim, while the Plan migrates no data, performs no irreversible operation, has no foreseeable resource risk and changes no shared test support or build configuration. The number of Claims does not decide it. What `light` does, and that the level is the user's choice, do not change.

## Considered Options

- **Keep one Claim**: simple to check, but it splits independent small work into Plans only to get the recommendation, and it does not stop one Claim from missing its spec's outcome.
- **A maximum number of Claims**: still a proxy; any number is arbitrary and says nothing about how the Claims relate.

## Consequences

Whether one Claim builds on another's design is main's judgement from the Plan, a recommendation the user still decides on. A dependency main misses loses plan review for that Plan, the same residual risk the other recommendation conditions carry.
