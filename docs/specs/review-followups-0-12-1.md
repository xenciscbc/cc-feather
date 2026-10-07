# Review follow-ups for 0.12.1

Label: `ready-for-agent`

Vocabulary follows [CONTEXT.md](../../CONTEXT.md). This spec collects the non-blocking findings left open by 0.11.0 and 0.12.0 ([delegation preview](delegation-preview.md), [consecutive review budget](consecutive-review-budget.md), [ADR 0004](../adr/0004-consecutive-failure-review-budget.md)) and the post-release checks of 0.12.0.

## Problem Statement

0.12.0 changed the review budget to consecutive failures, but some current text still speaks of a "two-call budget", the README's budget summary omits protocol-failure calls, and nothing fails if the rule that an Explicit request's verdict does not change the automatic count is deleted. Past Plans listed their Claims only in tickets kept in an ignored scratch directory, so a later session or another checkout that reads only the spec sees one Claim, and a Delegation preview of the spec showed exactly that. The 0.12.0 validation log still says the plugin-update-only upgrade was not exercised, although it was checked after release, and it does not record the post-release runs of the 0.11.0 Delegation preview (one fresh-session run, one natural-language request). Live compliance with the 0.12.0 consecutive-failure budget itself has still not been exercised.

## Solution

Ship 0.12.1 with four Claims, listed below in this spec so that they are visible without the tickets:

- find every remaining statement of the old fixed budget, classify it, and align the current rule text with the consecutive-failure wording;
- add a contract test for the Explicit-verdict rule;
- analyse where Claims should live so that review and the Delegation preview can see them, and record the options;
- record the post-release checks of 0.12.0 and release 0.12.1.

## Claims

| Claim | Outcome | Acceptance | Depends on |
| --- | --- | --- | --- |
| C1 Wording alignment | Current rule text uses the consecutive-failure wording, based on an inventory of every remaining old-budget statement | An inventory lists every hit of a defined search (`two-call`, `two automatic calls`, `at most two`, `call budget`, `straight to the verifier`, `not code-reviewed`, and the Traditional Chinese terms 兩次, 次數上限, 預算, 最多兩, 未經程式碼審查, 直接交給 verifier, 直接進 verifier) in skills, templates, READMEs, docs and CONTEXT.md with file, line and class (current rule text, still-true wording or historical record), recorded in this work's scratch directory so a verifier can re-run the search and compare; ADRs, including ADR 0004's remark on the setup wording, are classed as historical record; the setup skill and its toggle procedure say toggling does not reset any automatic review count; both READMEs' budget summaries list protocol-failure calls; every item classed as current rule text is updated or explicitly left with a reason; ADRs, the validation log and annotated earlier specs are not edited; tests pass | — |
| C2 Explicit-verdict test | A deleted Explicit-verdict rule fails the suite | A new test asserts that each of the three review procedures contains "an explicit call's verdict" and "does not change it"; it passes now and fails in a temporary copy outside the repository with either phrase removed from any one procedure | — |
| C3 Claim location analysis | A written analysis of where a Plan's Claims should be recorded | The analysis cites how plan review, code review, outcome verification and the Delegation preview find Claims; describes the failure when Claims exist only in ignored tickets; compares at least two options (for example, specs list their Claims, or plan review requires a Claim list) with trade-offs; recommends one; and is recorded in the scratch directory for this work without changing any shipped file | — |
| C4 Release 0.12.1 | 0.12.1 is validated, recorded and tagged locally | The 0.12.0 validation entry gains a dated post-release note that separates two kinds of check and names its evidence (2026-10-07, installed 0.12.0, observed in the implementing session): the plugin-update-only upgrade path (the installed files matched the tag and the setup check reported no update required), and the 0.11.0 preview procedure (one fresh-session run used no child and wrote nothing; one natural-language request was declined and pointed to the command); the note keeps that live compliance with the consecutive-failure budget remains untested; the manifest version is 0.12.1; the full suite and both `claude plugin validate` commands pass; a 0.12.1 entry records them and the review results of the plan and C1–C3 only; the local tag `v0.12.1` matches the manifest and is not pushed without the user's go-ahead | C1–C3 |

## User Stories

1. As a maintainer, I want a classified list of remaining old-budget statements, so that I fix the current rules without rewriting history.
2. As a user, I want the setup skill's toggle text to talk about review counts rather than a two-call budget, so that it matches the consecutive-failure rule.
3. As a user, I want the README's budget summary to say protocol-failure calls count, so that it matches the procedures.
4. As a maintainer, I want ADRs, the validation log and annotated specs left as written, so that the record of past decisions stays intact.
5. As a maintainer, I want a test that fails if the Explicit-verdict rule disappears from any procedure, so that the rule cannot be lost silently.
6. As a maintainer, I want an analysis of where Claims should be recorded, with options and a recommendation, so that I can decide how later Plans keep Claims visible.
7. As a user previewing a spec, I want its Claims to be visible in the spec, so that the preview expands them without the tickets.
8. As a maintainer, I want the 0.12.0 log to record the post-release checks, so that it no longer says they were not exercised without context.
9. As a user, I want 0.12.1 released with a matching tag and validation entry, so that the follow-ups ship under the project's release rules.

## Implementation Decisions

- This spec lists its Claims in its own Claims table; the tickets repeat them for tracking.
- C1 starts with a read-only inventory, then applies the fixed edits named in its acceptance and any further current-rule edits the inventory finds; historical records are out of its scope.
- C2 asserts the shared substrings "an explicit call's verdict" and "does not change it", which all three procedures contain after 0.12.0.
- C1 runs the full suite only after C2 has stopped editing the test file, and keeps both C2 phrases if the inventory adds a review procedure to its edits.
- C3 is analysis only: it changes no shipped file and makes no decision. Any change it recommends needs a new Plan.
- The installed delegation policy, role definitions and the configuration tool are unchanged; existing installations need only the plugin update.
- Release follows the project rules: version 0.12.1, tag `v0.12.1` matching the manifest, validation recorded under its heading; review and verification finish before the commit; the tag is never moved or reused.

## Testing Decisions

- The seam is the existing configuration test module that checks skill text (prior art: the explicit-budget and consecutive-failure tests).
- C2 adds one test; C1 must keep every existing test passing.
- C1's inventory and C3's analysis are checked by their acceptance, not by unit tests.
- Release checks: the full `unittest discover` suite and `claude plugin validate` for the plugin root and the manifest.

## Out of Scope

- Changing the review rules themselves.
- Editing ADRs, the validation log's past entries (other than the dated post-release note on 0.12.0) or specs that already carry amendment notes.
- Implementing C3's recommendation.
- Changing the installed policy, role definitions, setup behaviour or the configuration tool.

## Further Notes

- In auto, this spec is a Plan once the user agrees to it; it then gets plan review, and each Claim gets code review and outcome verification.
