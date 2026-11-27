# Review level: recommend light by content, not by Claim count

Label: `ready-for-agent`

Vocabulary follows [CONTEXT.md](../../CONTEXT.md), which defines Review level, Plan, Claim and Plan-driven work. The decision below was settled by the user on 2026-11-27, after main applied the `light` recommendation to the [test design and speed-up review fixes](test-design-review-fixes.md) and had to keep its release out of the Plan. This spec changes when main recommends `light`; it changes no rule of what `light` does, no installed guidance, role definition, template or script.

## Problem Statement

Main recommends `light` only for "a Plan of one Claim" with a known cause and a small scope. The rules of `light` already handle several Claims: the stop at the end waits until every Claim of a Plan at `light` has finished its Code review, and off mode, which `light` runs in, reopens a Claim's code review when another Claim changes its files. Only the recommendation counts Claims.

The count stands in for what plan review would catch across Claims: one Claim building on another's design, so that an error in the first carries into the second, or Claims that together miss the spec's outcome. Those depend on the content, not on the number. Three independent wording fixes carry almost no cross-Claim risk, yet must be split into three Plans to be recommended `light`, while one Claim can still miss its spec's outcome. [ADR 0023](../adr/0023-a-plans-review-level-is-the-users-choice.md) and [the Review level spec](review-level.md) give no reason for the number; the spec's user story says only that work that needs plan review is not to be steered away from it.

## Solution

The recommendation asks of each Claim what it asked of the one: a known cause, a small scope and acceptance that shows its outcome directly. It adds that no Claim builds on another's design and that none is Security-critical, and the Plan-wide conditions stay. The number of Claims does not decide it.

## User Stories

1. As a user, I want main to recommend `light` for a Plan of several small, independent Claims, so that I do not split such a Plan only to get the recommendation.
2. As a user, I want a Plan whose Claims build on one another's design recommended `standard`, so that plan review still sees the design they share.
3. As a user, I want every other condition kept, applied to each Claim and to the Plan, so that `light` stays a narrow recommendation.

## Implementation Decisions

- **The condition.** Review state's Recommending light becomes: main recommends `light` only for a Plan whose Claims each have a known cause, a small scope and acceptance that shows its outcome directly, none of which builds on another's design, as a Claim that lists another under `Blocked by` does, and none of which is a Security-critical claim, and that migrates no data, performs no irreversible operation, has no foreseeable resource risk and changes no shared test support or build configuration. A sentence follows: the number of Claims does not decide it.
- **Glossary.** The CONTEXT.md Review level entry carries the same condition in place of its "a Plan of one Claim" sentence, and the sentence that the number of Claims does not decide it.
- **Decision record.** ADR 0024 records the change and its reason, and ADR 0023 gains an "Amended by ADR 0024" line after its decision list, as earlier ADRs record their amendments.
- **Documents.** Both READMEs' and both reference documents' Review level sections carry the new condition in place of the one-Claim sentence, the reference keeping its "since those are the fixes whose failure is cheap" clause, and both reference documents add that the number of Claims does not decide it. Sentences are paired in English and Traditional Chinese.
- **Not affected.** What `light` does (Levels, Light adds, The stop at the end, Leaving light, Unknown level), plan review and its Review level question, the other review steps, off mode, the [Review level spec](review-level.md) as shipped, setup, role definitions and templates.

## Testing Decisions

- No executable seam: the rules are model instructions. Following the project's practice, tests pin each decision-carrying sentence as a whole sentence where it is stated, README and reference sentences paired in both languages.
- The pins go in `tests/test_feather_review_level.py`: the review-state pin, the README pair and the reference pair move to the new wording; new pins cover the number-of-Claims sentence in review state, the glossary entry's condition, the reference pair for the number of Claims and the ADR 0023 amendment line.
- Old wording: a check shows that "a Plan of one Claim" and "a plan of one claim" no longer appear in review state, CONTEXT.md, the READMEs or the reference documents, and "只有一個 claim" no longer appears in the Traditional Chinese README or reference.
- Prior art: the Review level pins in `tests/test_feather_review_level.py`.

## Out of Scope

- Any change to what `light` does, or a new review level.
- A limit on the number of Claims at `light`, or a threshold for small.
- Rewriting the shipped Review level spec.

## Further Notes

- **Tickets.** One ticket, `.scratch/review-level-content-condition/issues/01-content-condition.md`. It ships in release 0.50.0 with [the test design and speed-up review fixes](test-design-review-fixes.md).
- **Review level.** The user chose `light` for this Plan, which meets the current and the new condition.
- **Limits.** Whether one Claim builds on another's design is judged by main from the Plan; a dependency it misses loses plan review for that Plan, the same residual risk the other conditions carry.

## Overall acceptance

This is the Plan's overall acceptance, which the final check runs once for each commit to be landed or tagged, not once for each Claim; it is not part of any Claim's acceptance, and each ticket cites it.

- The full `unittest discover` suite passes at the commit to be landed or tagged.
