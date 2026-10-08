# Review follow-ups for 0.14.1

Label: `needs-triage`

Vocabulary follows [CONTEXT.md](../../CONTEXT.md). This spec collects the non-blocking findings left open by the 0.14.0 code reviews and verifications of tickets 03–06 ([review state rules](review-state-rules.md), [ADR 0006](../adr/0006-review-state-validity-and-completion.md)), the live scenarios observed after the 0.14.0 release, and the 2026-10-07 overall review of v0.14.0 (880f78c). That review's handoff defects F1–F3 and a POSIX-only test failure were already fixed on this branch (de7562a, d61b03b) as unplanned edits; C6 records them in the release. Its reviewer and analyst retry-scope finding (K1) belongs to the separate reviewer-template-review-modes work, which needs a setup update, and is out of scope here.

Two decisions below are open; this spec is not a Plan until the user settles them and agrees to it.

## Problem Statement

0.14.0 wrote the review state model down, but several sentences say more or less than the rule they summarise. The resumed-session re-review rule does not say it applies in auto, so an off-mode session could read it as a reason to start a plan review the user did not ask for. A release claim's ticket is set to resolved after its commit, before the tag postcondition is checked, and nothing says the status goes back when the postcondition fails. Plan review step 4 does not say a claim-changing blocker waits for the user's authorisation before it can be dispositioned FIX, and step 1's "decides other than to defer it" can be read as letting a re-review decision lift the restriction. README, glossary and ADR wording has drifted in smaller ways, and several README and glossary rules are only indirectly tested or are paired with phrases the text no longer uses. A live scenario found no rule for a plan that was implemented outside the session before any plan review. Separately, the configuration tool rejects Bedrock inference-profile ARNs, which Claude Code accepts as model values.

## Solution

Ship 0.14.1 with the Claims below, listed in this spec so they are visible without tickets:

- make the procedure text say exactly what the rules mean (auto-only re-review, release ticket order, authorisation before a claim-changing FIX, re-review not lifting a restriction);
- align README (EN and zh-TW), glossary and the ADR text written in 0.14.0 with the procedures;
- close the listed contract-test gaps;
- add a rule for a plan implemented before its plan review, once decided;
- settle Bedrock ARN model values, once decided;
- record the 0.14.0 live scenarios and the branch's earlier fixes, and release 0.14.1.

## Claims

| Claim | Outcome | Acceptance | Depends on |
| --- | --- | --- | --- |
| C1 Procedure precision | The delegation procedures state the rules exactly | `review-state.md` Resumed sessions and the matching sentence in `plan-review.md` step 1 say an unfinished plan is reviewed again in auto, and keep that an unresolved verdict recorded in an active handoff restricts work in either mode; Ticket status says a claim with a postcondition is set to its completion value only after the postcondition holds, and a postcondition that fails leaves the ticket unfinished with the observed state noted; `plan-review.md` step 4 says a blocker that needs a claim change cannot be dispositioned FIX until the user authorises the change; step 1 says a re-review is another call and lifts the restriction only by passing; `code-review.md`'s opening points to review state for the rule that off does not lift the commit condition on a claim an active handoff records as unreviewed or unverified; the waiver sentence names READY alongside APPROVED and CONFIRMED; "nothing carries over" becomes "no restriction carries over" wherever it summarises the inheritance rule; existing tests pass or are updated in the same change with the reason | — |
| C2 Document alignment | README (EN, zh-TW), CONTEXT.md and the 0.14.0 ADR text match the procedures | CONTEXT.md Unverified claim no longer reads as a complete list where the procedures are wider; README Cost says "one uninterrupted attempt" once; README Resumed session and its zh-TW counterpart carry C1's auto-only wording; the README label "No edits" is renamed to match its content and the README_RULES mapping and zh-TW label change with it; ADR 0005's 0.14.0 amendment note says ignored and hidden directories are searched only when the project's instructions do not say where tickets live; ADR 0006 Consequences names the scope of "a review requires" and replaces the unclear "its" in "keeps its count and stop" | C1 |
| C3 Contract-test gaps | Each listed rule fails the suite when its text is removed | Tests cover: README Commit's handoff scope; README Not passed's unverified sentence; review-state's "zero after an automatic pass"; the "six" spelling of the per-claim bound (and no "6 calls"); plan-review's "or the user says it is done; without a defined value, ask"; README "with its scope" and zh-TW 「並註明範圍」; README "main edits only after your authorisation" and "an unfinished plan is reviewed again" in EN and zh-TW, directly; README_RULES No edits (as renamed in C2), Plan-mode and Resumed session, and GLOSSARY_RULES Explicit request and Plan, paired with phrases the current text uses; the ADR test checks the whole ADR 0004 note, not only its prefix, and the authorisation sentence wherever it appears. Each new assertion passes now and fails in a temporary copy outside the repository with its phrase removed | C1, C2 |
| C4 Plan implemented before its plan review | The procedures say what main does when a plan in the named scope is already implemented but has not been plan-reviewed in this session | Per decision D1 below: `plan-review.md`, `review-state.md`, both READMEs and the Delegation preview procedure state the rule and its classification (automatic or explicit), main states it before dispatching, and a contract test covers it | C1, D1 |
| C5 Bedrock ARN model values | Per decision D2 below | Option A: `scripts/feather_config.py` accepts an `arn:aws:bedrock:…:application-inference-profile/…` or `inference-profile/…` value for a role model in model and session; preview, apply and session export keep the whole string; the written frontmatter quotes it and the tool's own reader returns the same value; other identifiers keep their current syntax; `docs/setup.md` states the accepted syntax; tests cover a synthetic ARN. Option B: `docs/setup.md` states that ARNs are not accepted and how to configure one outside cc-feather; no code change. Either way, no live Bedrock dispatch is claimed | D2 |
| C6 Release 0.14.1 | 0.14.1 is validated, recorded and tagged locally | The 0.14.0 validation entry gains a dated post-release note recording the live scenarios (same-session spec then ticket; state unknown after compaction; auto review of a ticket implemented outside the session, session 7694beb9, classified as automatic code review at 0/2 without a plan review) with what each showed; the 0.14.1 entry records the handoff fixes of de7562a (ATX headings with indent or tab, exact `.gitignore` lines, blank titles) and the test fix of d61b03b as unplanned edits made before this Plan, and the review results of the plan and C1–C5; the manifest version is 0.14.1 (or 0.15.0 if C5 takes option A); the full suite and both `claude plugin validate` commands pass; each ticket's status is set only after the tag matches the manifest; the local tag is not pushed without the user's go-ahead | C1–C5 |

## Open decisions

- **D1: a plan implemented before plan review.** A live 0.14.0 scenario asked, in auto, for review of a ticket implemented outside the session that this session had never plan-reviewed. Main classified it as automatic code review and did not go back to plan review. Options:
  - (a) Run the plan review first, as an automatic call, then code review and outcome verification. Code review and verification judge against the plan's acceptance, so an unreviewed acceptance weakens both passes; it costs one call.
  - (b) Go straight to code review and state that plan review was skipped because the work is already implemented.
  - (c) Ask the user each time, offering (a) or (b).

  Recommendation: (a). It matches "a resumed session reviews an unfinished plan again", and plan review then checks the acceptance the later passes depend on.
- **D2: Bedrock ARNs.** Option A widens the model syntax (a setup behaviour change, minor version); option B documents the limit only. Recommendation: A, because Claude Code documents ARNs as valid model values and the current rejection is explicit rather than silent, so widening it removes a gap without hiding one.

## User Stories

1. As a user in off mode, I want a resumed session not to start a plan review I did not ask for, so that off means off.
2. As a user in either mode, I want an unresolved verdict recorded in an active handoff to keep restricting work, so that turning review off does not hide a known problem.
3. As a maintainer releasing, I want a ticket to stay unfinished until its tag postcondition holds, so that a resumed session does not skip a failed release.
4. As a user, I want a claim-changing blocker to wait for my authorisation before main fixes it, so that claims change only with my consent.
5. As a user, I want only a passing re-review to lift a restriction, so that asking for another review is not mistaken for accepting the risk.
6. As a reader, I want the README, glossary and ADRs to say what the procedures say, so that I can trust the summary.
7. As a maintainer, I want each of these rules to fail the suite when its text is removed, so that they cannot drift silently.
8. As a user, I want a defined behaviour for reviewing work that was implemented before its plan review, so that the flow is predictable.
9. As a Bedrock user, I want either to set an inference-profile ARN as a role model or to be told how to configure one, so that I am not left with a bare rejection.
10. As a maintainer, I want the 0.14.0 live observations and this branch's earlier fixes recorded with the release, so that the validation log is complete.

## Implementation Decisions

- This spec lists its Claims in its own Claims table. Tickets under `.scratch/` are optional and, if written, mirror the table.
- C1 changes the delegation procedures only; C2 changes documents only; C3 changes tests only. Each Claim is its own commit, and C5 commits separately from the review-rule Claims.
- ADR 0005's amendment note and ADR 0006 were written in 0.14.0 and are corrected in place for clarity, not meaning. Earlier ADRs, past validation entries and annotated earlier specs are not edited.
- The installed delegation policy and role definitions are unchanged; C1–C4 need only the plugin update. C5 option A changes the configuration tool but not installed roles.
- Release follows the project rules: tag matching the manifest, validation recorded under its heading, review and verification finished before the commit, the tag never moved or reused.

## Testing Decisions

- The seam is the existing configuration test module that checks skill and document text (prior art: README_RULES, GLOSSARY_RULES and the ADR note tests).
- C3 proves each new assertion by removing its phrase in a temporary copy outside the repository.
- C5 option A adds configuration-tool tests with a synthetic ARN; no AWS connection.
- Release checks: the full `unittest discover` suite and `claude plugin validate` for the plugin root and the manifest.

## Out of Scope

- Reviewer and analyst template changes (reviewer-template-review-modes), including the retry-scope finding K1.
- Changing the review budget, the five decision kinds or the state model beyond C1 and C4.
- Live Bedrock dispatch verification.
- Cross-session locking for handoff history, and the merge-marker guard limits already documented in `docs/compatibility.md`.

## Further Notes

- In auto, this spec becomes a Plan once D1 and D2 are settled and the user agrees to it; it then gets plan review, and each Claim gets code review and outcome verification.
