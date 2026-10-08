# Review follow-ups for 0.15.0

Label: `ready-for-agent`

Vocabulary follows [CONTEXT.md](../../CONTEXT.md). This spec collects the non-blocking findings left open by the 0.14.0 code reviews and verifications of tickets 03–06 ([review state rules](review-state-rules.md), [ADR 0006](../adr/0006-review-state-validity-and-completion.md)), the live scenarios observed after the 0.14.0 release, and the 2026-10-07 overall review of v0.14.0 (880f78c). That review's handoff defects F1–F3 and a POSIX-only test failure were already fixed on this branch (de7562a, d61b03b) as unplanned edits; C6 records them in the release. Its reviewer and analyst retry-scope finding (K1) belongs to the separate reviewer-template-review-modes work, which needs a setup update, and is out of scope here.

Decisions D1 (option c) and D2 (option A) were settled on 2026-10-08. The user agreed to this spec on 2026-10-08.

## Problem Statement

0.14.0 wrote the review state model down, but several sentences say more or less than the rule they summarise. The resumed-session re-review rule does not say it applies in auto, so an off-mode session could read it as a reason to start a plan review the user did not ask for. A release claim's ticket is set to resolved after its commit, before the tag postcondition is checked, and nothing says the status goes back when the postcondition fails. Plan review step 4 does not say a claim-changing blocker waits for the user's authorisation before it can be dispositioned FIX, and step 1's "decides other than to defer it" can be read as letting a re-review decision lift the restriction. README, glossary and ADR wording has drifted in smaller ways, and several README and glossary rules are only indirectly tested or are paired with phrases the text no longer uses. A live scenario found no rule for a plan that was implemented outside the session before any plan review. Separately, the configuration tool rejects Bedrock inference-profile ARNs, which Claude Code accepts as model values.

## Solution

Ship 0.15.0 with the Claims below, listed in this spec so they are visible without tickets:

- make the procedure text say exactly what the rules mean (auto-only re-review, release ticket order, authorisation before a claim-changing FIX, re-review not lifting a restriction);
- align README (EN and zh-TW), glossary and the ADR text written in 0.14.0 with the procedures;
- close the listed contract-test gaps;
- when a plan was implemented and has no plan-review state in this session, let the user choose whether to run plan review first;
- accept Bedrock inference-profile ARNs as role model values;
- record the 0.14.0 live scenarios and the branch's earlier fixes, and release 0.15.0.

## Claims

Each Claim's acceptance is listed under its own heading below the table. Claims are committed separately, in the order C1, C2, C3, C4, C5, C6.

| Claim | Outcome | Acceptance | Depends on |
| --- | --- | --- | --- |
| C1 Procedure precision | The delegation procedures state the rules exactly | [C1](#c1-acceptance) | — |
| C2 Document alignment | README (EN, zh-TW), CONTEXT.md and the 0.14.0 ADR text match the procedures as C1 leaves them | [C2](#c2-acceptance) | C1 |
| C3 Contract-test gaps | Each listed rule fails the suite when its text is removed | [C3](#c3-acceptance) | C1, C2 |
| C4 Plan implemented before its plan review | In auto, when review is due for implemented work whose plan has no plan-review state in this session, main asks the user whether to run plan review first (decision D1, option c) | [C4](#c4-acceptance) | C1, C2 |
| C5 Bedrock ARN model values | A role model can be a Bedrock inference-profile ARN (decision D2, option A) | [C5](#c5-acceptance) | — |
| C6 Release 0.15.0 | 0.15.0 is validated, recorded and tagged locally | [C6](#c6-acceptance) | C1–C5 |

Every Claim's acceptance ends with: the full `unittest discover` suite passes after its commit, and any existing assertion the Claim changes is updated in the same commit with the reason in the commit message.

### C1 acceptance

Files: `skills/delegation/references/review-state.md`, `plan-review.md`, `code-review.md`, `skills/delegation/SKILL.md`, and the assertions in `tests/test_feather_config.py` that pin the replaced phrases.

1. Auto-only re-review: review-state.md Resumed sessions and plan-review.md step 1 say that *in auto* a resumed session reviews an unfinished plan again before implementing it; both keep that an unresolved verdict recorded in an active handoff restricts the related work in either mode.
2. No restriction carries over: review-state.md's "without an active handoff record, nothing carries into a resumed session" and plan-review.md's "without such a record nothing carries over" say that no restriction carries over without such a record.
3. Lifting a restriction: plan-review.md step 1's "or the user decides other than to defer it" says the restriction lasts until a later call passes it or the user cancels the work, changes its acceptance or waives it; a re-review is another call and lifts it only by passing, and a deferral keeps it.
4. Release order: review-state.md Ticket status says a claim with a postcondition has its ticket set to the completion value only after the postcondition holds; review-state.md Postconditions says a postcondition that does not hold leaves the claim incomplete and its ticket unfinished, with the observed state noted; SKILL.md's "After a claim passes and is committed, update its ticket" carries the same condition.
5. Authorisation first: plan-review.md step 4 says a blocker that needs claims added, split or changed cannot be dispositioned FIX until the user authorises the claim change.
6. Off and the commit rule: code-review.md's opening keeps "the unreviewed rule in step 6 applies only to the automatic flow" only together with a pointer to review state's commit rule, which still covers a claim an active handoff records as unreviewed or unverified in either mode.
7. Waiver: review-state.md's waiver sentence says a waiver is never recorded as READY, APPROVED or CONFIRMED.

### C2 acceptance

Files: `README.md`, `README.zh-TW.md`, `CONTEXT.md`, `docs/adr/0005-the-named-plan-and-its-tickets.md` (its 0.14.0 amendment note), `docs/adr/0006-review-state-validity-and-completion.md`, and the assertions that pin the replaced phrases, including README_RULES and the ADR test.

1. CONTEXT.md Unverified claim keeps "no currently valid CONFIRMED" as the definition and gives INCONCLUSIVE, a stopped verification and an expired CONFIRMED as examples ("for example"), so that a claim whose verification has not run or was refuted is also covered, as README.md's Not passed bullet states.
2. README Cost (EN) and 成本 (zh-TW) each say "one uninterrupted attempt" / 「一次不中斷的完成過程」 once, and the clause that states "six" / 「六」 still contains "uninterrupted" / 「不中斷」.
3. README Resumed session and 恢復的 session carry C1's wording, keeping the phrases "an unfinished plan is reviewed again" and 「未完成的計畫會重新審查」: that re-review happens in auto; the restriction lasts until a later review passes it or you cancel, change acceptance or waive (replacing "or you decide other than to defer it" / 「或你作出延後以外的決定」); without an active handoff record no restriction carries over (replacing "nothing carries over" / 「什麼都不會帶過去」).
4. README Ticket status and Ticket 狀態 say a claim with a postcondition, such as a release tag, has its ticket set only after the postcondition holds.
5. README Your decisions and 你的決定 say a waiver never counts as READY, APPROVED or CONFIRMED.
6. README "No edits" / 「不改文件」 is renamed "Claim changes" / 「修改 claim」, and its README_RULES entry is renamed with it.
7. ADR 0005's amendment note "(Amended by ADR 0006: another checkout …)" says ignored and hidden directories are searched only when the project's instructions do not say where tickets live.
8. ADR 0006's decision paragraph (line 5) names the scope of "Claim changes a review requires" (claims added, split or changed because of a REVISE blocker), replaces "Work overlapping a stopped Plan keeps its count and stop" with wording that names the stopped Plan's count and stop, and gains an amendment note that a Claim with postconditions has its ticket set only after they hold; ADR 0006's Consequences sentence "searches ignored and hidden directories" gets the same condition as item 7.

### C3 acceptance

Files: `tests/test_feather_config.py` only. Each new assertion passes now and fails in a temporary copy outside the repository with its phrase removed; the verifier repeats that check.

1. README Commit / Commit 條件: a check scoped to that bullet asserts "for any claim an active handoff records as unreviewed or unverified" and 「進行中的交接記錄為未審查或未驗證的 claim」.
2. README Not passed / 未通過: a check scoped to that bullet asserts "A claim without a valid CONFIRMED is unverified" and 「沒有有效 CONFIRMED 的 claim 視為未驗證」.
3. review-state.md Reopened calls: asserts "which is zero after an automatic pass".
4. The uninterrupted-attempt test also finds the per-claim bound written as the numeral 6 ("6 calls", "6 automatic", 「6 次」) without matching "2 + 6N" or "6N". Its proof is a temporary copy that keeps the "six" clause and adds a clause with "6 calls" but no "uninterrupted" (and the zh-TW equivalent), which the old test passes and the new test fails.
5. README_RULES entries are paired with the 0.14.0 rule rather than older sentences: "Claim changes" (as renamed by C2) with "only after your authorisation" / 「在你授權後才修改」 and review-state's "only after the user authorises it"; "Plan-mode and conversation plans" with plan-review's "is identified only from its original text, an available record or a version the user confirms"; "Resumed session" with "an unfinished plan is reviewed again" / 「未完成的計畫會重新審查」 and review-state's "reviews an unfinished plan again before implementing it".
6. GLOSSARY_RULES entries are paired with the 0.14.0 rule: "Explicit request" with "it clears the stop without resetting the count" and review-state's "clears the stop and leaves the count unchanged"; "Plan" with "its unfinished tickets in the named scope as claims" and plan-review's "each unfinished ticket in the named scope is one claim".
7. The ADR test checks ADR 0004's whole amendment note, not only its prefix, and asserts the authorisation sentence ("only after the user authorises it") in the ADR 0005 note, ADR 0006's decision paragraph and ADR 0006's Consequences.

### C4 acceptance

Files: `review-state.md`, `plan-review.md`, `preview.md`, `skills/delegation/SKILL.md`, `README.md`, `README.zh-TW.md`, `tests/test_feather_config.py`.

1. The case: in auto, the user asks for review, or the flow reaches review, for a plan that is implemented in part or whole and has no plan-review state in this session (no automatic plan-review call and no recorded user decision on its plan review), whether it was implemented in another session, outside Claude, or in this session while review was off. An explicit READY given before the flow reached plan review does not count as plan-review state (review-state "What an explicit call runs"); main names it. A plan whose plan review ran in this session, including one that stopped, was cleared by an explicit READY or was decided by the user, follows the existing stop, clearing and decision rules, and main does not ask again. When plan-review state cannot be established, the Unknown state rule applies, and work overlapping a stopped plan keeps the Overlap rule.
2. Before any call, main states the case, names any record it found of an earlier plan review (a handoff, ticket comment or validation entry) without treating it as a pass, and asks the user to choose:
   - plan review first: an automatic plan review call of the flow, covering the whole plan, with the implemented claims and their changes as context; a REVISE then follows plan-review steps 4 and 5, and changes needed in already implemented claims are fixes that go through code review;
   - straight to code review: recorded as a waiver of the missing READY for the implemented claims, with its scope, visible in the report and in any active handoff; claims of the plan not yet implemented still get plan review before they are implemented.
   Main dispatches neither call until the user answers.
3. This rule comes first: SKILL.md's "review the plan if the work is not yet implemented and review the code if it is", review-state's Classifying a request, README "Asking for a review" / 「要求審查時」, and the resumed-session re-review rule (for a plan with any implemented claim) each defer to it.
4. The Delegation preview flags such a plan.
5. Contract tests cover the rule in review-state.md and plan-review.md, including the sentence that a plan with plan-review state in this session follows the existing rules, the deferral in SKILL.md and both READMEs, and the preview flag.

### C5 acceptance

Files: `scripts/feather_config.py`, `docs/setup.md`, `tests/test_feather_config.py`.

1. A role model may be `arn:<partition>:bedrock:<region>:<12-digit account>:application-inference-profile/<id>` or `…:inference-profile/<id>`, with partition `aws`, `aws-us-gov` or `aws-cn`, an id of letters, digits, dot, underscore, colon and hyphen that ends with a letter or digit, and at most 2048 characters in total; no `[1m]`-style suffix follows an ARN. Other identifiers keep their current syntax and 128-character limit.
2. The ARN is written as a plain YAML scalar, unquoted: the accepted syntax has no space, `#` or leading indicator, so it reads back as the same string, and the existing comparisons (`_edit_role_fields`, session export, `_load_state`) and template rendering stay unchanged.
3. Tests with a synthetic ARN and installed roles: model preview and apply; changing the role to an alias and back to the ARN; update re-rendering with a saved ARN; session export, installed and not installed, returning the exact string; an over-length ARN, an ARN with a suffix, an ARN ending in a colon (which would not parse as a plain YAML value), and a non-profile ARN rejected. The existing MODEL_RE's acceptance of a trailing colon for other identifiers predates this plan and is out of scope.
4. docs/setup.md states the accepted ARN syntax and a downgrade note: an older cc-feather reports a saved ARN as an invalid state, so set the role to an alias before downgrading.
5. No live Bedrock dispatch is claimed.

### C6 acceptance

Files: `docs/setup-validation.md`, `.claude-plugin/plugin.json`, any other version reference the project's release rules name.

1. A new "0.15.0 review follow-ups" entry, as the 0.14.0 entry promised, records the 0.14.0 live scenarios with the plugin version each loaded: a spec then one of its tickets in one session; unknown state after compaction; and the auto review of a ticket implemented outside the session (session 7694beb9), classified as automatic code review at 0/2 without a plan review, which led to C4. Where no available record states the loaded version, main asks the user before writing it.
2. The entry records the handoff fixes of de7562a (ATX headings with indent or tab, exact `.gitignore` lines, blank titles) and the test fix of d61b03b as unplanned edits made before this Plan, and the review results of the plan and C1–C5.
3. The manifest version is 0.15.0, a minor release because C5 changes setup behaviour; the full suite and both `claude plugin validate` commands pass, or the entry says which could not run here and why.
4. If tickets were written, each is set to its completion value only after the local tag `v0.15.0` matches the manifest. The tag is not pushed without the user's go-ahead.

## Decisions

- **D1, option c (2026-10-08).** A live 0.14.0 scenario asked, in auto, for review of a ticket implemented outside the session that this session had never plan-reviewed; main classified it as automatic code review and did not go back to plan review. The existing rules miss it: a resumed session re-reviews an unfinished plan *before implementing it*, and that point has passed. The same gap arises in one session when work is implemented in off and auto is turned on before review. The user knows whether the plan was reviewed before, so main asks rather than deciding (C4). Options not taken: (a) always run plan review first; (b) always go straight to code review.
- **D2, option A (2026-10-08).** Widen the model syntax so an inference-profile ARN can be a role model (C5). Option not taken: (B) document the limit only. This changes setup behaviour, so the release is 0.15.0.

## User Stories

1. As a user in off mode, I want a resumed session not to start a plan review I did not ask for, so that off means off.
2. As a user in either mode, I want an unresolved verdict recorded in an active handoff to keep restricting work, so that turning review off does not hide a known problem.
3. As a maintainer releasing, I want a ticket to stay unfinished until its tag postcondition holds, so that a resumed session does not skip a failed release.
4. As a user, I want a claim-changing blocker to wait for my authorisation before main fixes it, so that claims change only with my consent.
5. As a user, I want only a passing re-review to lift a restriction, so that asking for another review is not mistaken for accepting the risk.
6. As a reader, I want the README, glossary and ADRs to say what the procedures say, so that I can trust the summary.
7. As a maintainer, I want each of these rules to fail the suite when its text is removed, so that they cannot drift silently.
8. As a user who knows whether an already implemented plan was reviewed elsewhere, I want main to ask me whether to run plan review first, so that I neither pay for a review I already had nor skip one silently.
9. As a Bedrock user, I want to set an inference-profile ARN as a role model, so that cc-feather accepts the values Claude Code accepts.
10. As a maintainer, I want the 0.14.0 live observations and this branch's earlier fixes recorded with the release, so that the validation log is complete.

## Implementation Decisions

- This spec lists its Claims in its own Claims table. Tickets under `.scratch/` are optional and, if written, mirror the table.
- C1 changes the delegation procedures, C2 the documents, C3 the tests, C4 the procedures and documents for its rule, C5 the configuration tool and setup documentation. A Claim may update existing assertions that pin text it changes, in its own commit, with the reason. Each Claim is its own commit.
- ADR 0005's amendment note and ADR 0006 were written in 0.14.0 and are corrected in place for clarity; ADR 0006 gains one amendment note for the release ticket order. Earlier ADRs, past validation entries and annotated earlier specs are not edited; the 0.14.0 live scenarios go into the new 0.15.0 entry, as the 0.14.0 entry said they would.
- The installed delegation policy and role definitions are unchanged; C1–C4 need only the plugin update. C5 changes the configuration tool but not installed roles.
- Release follows the project rules: tag matching the manifest, validation recorded under its heading, review and verification finished before the commit, the tag never moved or reused.

## Testing Decisions

- The seam is the existing configuration test module that checks skill and document text (prior art: README_RULES, GLOSSARY_RULES and the ADR note tests).
- C3 proves each new assertion by removing its phrase in a temporary copy outside the repository.
- C4's tests cover the procedure rule, the deferrals and the preview flag.
- C5 adds configuration-tool tests with a synthetic ARN; no AWS connection.
- Release checks: the full `unittest discover` suite and `claude plugin validate` for the plugin root and the manifest.

## Out of Scope

- Reviewer and analyst template changes (reviewer-template-review-modes), including the retry-scope finding K1.
- Changing the review budget, the five decision kinds or the state model beyond C1 and C4.
- Live Bedrock dispatch verification.
- Cross-session locking for handoff history, and the merge-marker guard limits already documented in `docs/compatibility.md`.

## Further Notes

- In auto, this spec becomes a Plan once the user agrees to it; it then gets plan review, and each Claim gets code review and outcome verification.
