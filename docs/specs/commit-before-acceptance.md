# Commit before acceptance, and the 0.15.0 follow-ups

Label: `ready-for-agent`

Vocabulary follows [CONTEXT.md](../../CONTEXT.md). This spec changes where the review flow's acceptance gate sits, decided in [ADR 0006](../adr/0006-review-state-validity-and-completion.md), and collects the non-blocking follow-ups left open by 0.15.0 ([its spec](review-followups-0-15-0.md) and the 0.15.0 entry in [the validation log](../setup-validation.md)).

Decisions D1–D4 were settled on 2026-10-08 (see Decisions). The user agreed to this spec on 2026-10-08.

## Problem Statement

A claim in the automatic flow may be committed only with a valid APPROVED and CONFIRMED; any earlier commit needs the user's explicit permission and an "unaccepted" label. In practice a claim spends several review rounds uncommitted. In an ephemeral cloud session that work is lost if the container is reclaimed, and the session's own stop hook asks for a commit at every turn. A review also judges a moving working tree rather than a fixed revision, so "a pass covers the reviewed content" cannot point to an exact snapshot, and a second review has to reconstruct what the fix changed. The gate that matters (accepted work is not merged, released, reported complete or marked done) is tied to the act of committing rather than to those outcomes.

0.15.0 also left follow-ups: other model identifiers still accept `---` and a trailing colon, which break role frontmatter in the same way C5 of 0.15.0 prevented for Bedrock ARNs (Claude Code ends the frontmatter at any `---`, dropping the role's `tools`); plan-review step 1 can be read as limiting "finished tickets are not redone" to auto; "after any postcondition it has holds" reads awkwardly; and several 0.15.0 sentences have no contract test.

## Solution

Ship 0.16.0 with the Claims below:

- move the acceptance gate from committing to landing on the remote default branch, releasing, reporting complete and marking a ticket done, and let main commit a claim before its passes (and push it to a working branch), with each pass naming the commit it judged;
- make other model identifiers frontmatter-safe;
- finish the 0.15.0 wording and test follow-ups;
- release 0.16.0.

## Claims

Claims are committed separately, in the order C1, C2, C3, C4. Every Claim's acceptance ends with: the full `unittest discover` suite passes after its commit, and any existing assertion the Claim changes is updated in the same commit with the reason in the commit message.

| Claim | Outcome | Acceptance | Depends on |
| --- | --- | --- | --- |
| C1 Commit before acceptance | Main may commit a claim before its passes and push it to a working branch; acceptance gates landing on the remote default branch, release, reporting complete and ticket completion | [C1](#c1-acceptance) | — |
| C2 Frontmatter-safe model identifiers | No accepted model value can end role frontmatter early or fail to parse | [C2](#c2-acceptance) | — |
| C3 0.15.0 wording and test follow-ups | The remaining 0.15.0 wording is precise and its sentences are guarded | [C3](#c3-acceptance) | C1 |
| C4 Release 0.16.0 | 0.16.0 is validated, recorded and tagged locally | [C4](#c4-acceptance) | C1–C3 |

### C1 acceptance

Files: `skills/delegation/references/review-state.md`, `code-review.md`, `outcome-verification.md`, `README.md`, `README.zh-TW.md`, `CONTEXT.md`, a new `docs/adr/0007-*.md`, amendment notes in `docs/adr/0002-*.md` and `0006-*.md`, and the tests that pin the replaced sentences.

1. **The gate.** review-state.md Commit and completion becomes an acceptance gate: for a claim of plan-driven work in the automatic flow, and for any claim an active handoff records as unreviewed or unverified, main lands the claim on the remote default branch (by pushing it there or merging it, directly or through a pull request), releases or tags it, reports it complete, or sets its ticket to a completion value only with a valid APPROVED and a valid CONFIRMED. Landing a branch lands every claim on it, so it waits for every gated claim on that branch; a cancelled claim's commits stay on the branch until the user decides otherwise. The default branch is the branch the `origin` remote's HEAD names (with no `origin`, the only remote's HEAD; with no remote or no HEAD, main asks); a protected or shared branch the user names counts as one.
2. **Commits before the passes.** Before its passes, main may commit such a claim on any branch, and push it to any branch other than a default branch, without the user's permission (D1, D2). It may open a pull request whose description lists the claims still unaccepted, and updates that list as claims pass (D4). It never rewrites pushed history, so a fix is a new commit. Off mode otherwise keeps its behaviour.
3. **What a pass judged.** Main dispatches a code review or outcome verification only when the workspace equals the commit it names in the brief: HEAD is that commit and the claim's file scope has no uncommitted or untracked change, and nothing changes the workspace during the call. The brief names the base revision and that commit; a pass covers that commit's content, as review-state's Validity rules describe, and a second review receives the range from the previously judged commit to the new one. review-state.md's Reviewed content row and code-review.md and outcome-verification.md step 2 say this. The reviewer, verifier and analyst role definitions are unchanged: with a clean workspace at the named commit, the reviewer's diff against the base and the verifier's check of the workspace both judge that commit.
4. **Passes from an earlier session.** review-state.md Resumed sessions says: before a gated operation, a claim needs valid passes from this session, so a claim that passed in an earlier session is reviewed and verified again, counted as usual; a claim whose ticket is finished (a completion value, or the user says it is done) is not redone and counts as accepted for landing and release.
5. **Unreviewed and unverified claims.** code-review.md's opening pointer to review state names the acceptance gate instead of the commit rule; code-review.md and outcome-verification.md step 6 say an unreviewed or unverified claim is not landed on the default branch, released or reported complete (replacing "do not commit it or report it complete" and the work-in-progress clause), and the handoff note says it "must not be landed on the default branch, released or reported complete".
6. **Existing handoff notes.** review-state.md says an active handoff's record that a claim is unreviewed or unverified restricts it under the current gate whatever its wording (such as "must not be committed"), and main updates the wording at the next handoff maintenance.
7. **Working on the default branch (D3).** Main may commit there before the passes, labelling each such commit unaccepted in its message when it creates it. It pushes those commits to the remote default branch only after both passes, or as a work-in-progress push the user explicitly allows. When work on the default branch stays unpushed, main says that a reclaimed environment would lose it. Commits on other branches carry no label; landing them waits for the passes.
8. **Waivers.** review-state.md User decisions: a waived claim the gate covers is landed on the default branch, released or reported complete only after a later pass, or pushed to the default branch as a work-in-progress push the user allows with its commits labelled as in item 7 (replacing the work-in-progress commit clause).
9. **Documents.** README (EN, zh-TW) Commit / Commit 條件, Not passed / 未通過 and Your decisions / 你的決定 state items 1, 2, 4, 7 and 8; CONTEXT.md Unreviewed claim and Unverified claim add "It is not landed on the default branch, released or reported complete."; the README_RULES entries for Commit and Not passed are re-paired with the new procedure phrases.
10. **ADRs.** A new ADR 0007 records the decision, the session rule of item 4 and the rejected options (keep the commit gate; commit locally only; label every early commit; trust passes across sessions by commit), and ADR 0002 and ADR 0006 each gain an amendment note pointing to it, leaving their text otherwise unchanged. A test pins ADR 0007's key phrases and both notes.
11. **Release.** The release flow keeps its order: the release claim is reviewed and verified before the release commit lands on the default branch or is tagged; the tag stays a postcondition.
12. **Tests.** Contract tests pin the new sentences of items 1–8 in review-state.md, code-review.md and outcome-verification.md and the README bullets of item 9, each failing with its phrase removed.

### C2 acceptance

Files: `scripts/feather_config.py`, `docs/setup.md`, `tests/test_feather_config.py`.

1. `MODEL_RE` rejects a value containing `---` anywhere and a value whose last character before the optional `[Nm]` suffix is a colon; every value it accepts today without either stays accepted (for example `opus`, `sonnet`, `claude-opus-4-1`, `us.anthropic.claude-v1:0`, `opus[1m]`, a 128-character identifier).
2. Tests: `opus---x`, `a---b[1m]`, `abc:` and `abc:[1m]` are rejected with "invalid model identifier" by `_validate_choice` and through `model --set`; the examples above stay accepted; each new rejection fails against the 0.15.0 pattern.
3. Recovery: a saved model that the 0.15.0 pattern accepted but the new one rejects does not make the tool unusable. `_load_state` reads it, `show` and `check` report it as an issue naming the role, session export and `update` refuse until it is replaced, and `model --set ROLE.model=<valid>` replaces it. A test saves `abc:` and `a---b` in state, runs `check` (issue reported, nonzero), runs the `model --set` repair and then `check` (ok). Any other invalid saved model is still rejected as before.
4. docs/setup.md says an identifier must not contain `---` or end with a colon, and describes that recovery.

### C3 acceptance

Files: `skills/delegation/references/plan-review.md`, `review-state.md`, `skills/delegation/SKILL.md`, `tests/test_feather_config.py`.

1. plan-review.md step 1 says finished tickets are not redone in either mode.
2. review-state.md Ticket status and SKILL.md say "and any postcondition holds" instead of "and after any postcondition it has holds" / "and any postcondition it has holds", as C1 leaves the surrounding sentences.
3. Tests pin, each failing with its phrase removed, and scoped to the step or bullet named: README "Plan review first is an automatic call that covers the whole plan" and 「先補計畫審查算一次自動呼叫，審查整份計畫」; plan-review step 1's "main asks the user whether to run plan review first or go straight to code review with the missing READY waived"; and the 0.15.0 C1 phrases the verifier found unguarded: "in auto" and "in either mode" in plan-review step 1 and review-state Resumed sessions, plan-review step 4's authorisation clause, the two postcondition clauses in review-state.md and the one in SKILL.md, and the code-review.md opening pointer to the gate (as C1 item 5 rewords it).

### C4 acceptance

Files: `docs/setup-validation.md`, `.claude-plugin/plugin.json`.

1. A "0.16.0" entry records C1–C3 with their commits and review results, states whether a setup update is needed (none expected: role definitions and policy unchanged), and names any check that could not run here.
2. The manifest version is 0.16.0; the full suite and both `claude plugin validate` commands pass.
3. The local tag `v0.16.0` matches the manifest and is not pushed without the user's go-ahead.

## Decisions

Settled by the user on 2026-10-08.

- **D1, (a): push before acceptance.** Main commits and pushes a claim to a working branch without asking. Option not taken: commit locally only, push after both passes or with permission. In a cloud session an unpushed commit is lost with the container, and pushing to a working branch is not landing on the default branch.
- **D2, (a): which branches.** Any branch other than a default branch: the remote HEAD's branch, or a protected or shared branch the user names. Option not taken: only a branch created for the current work.
- **D3: working on the default branch.** Main may commit there before the passes; pushing to the remote default branch still waits for both passes, or for a labelled work-in-progress push the user allows. Options not taken: keep the commit gate on the default branch; push there freely.
- **D4, (a): pull requests.** Main may open a pull request before acceptance, listing the claims still unaccepted; merging is gated. Option not taken: wait for both passes before opening one.

## User Stories

1. As a user in a cloud session, I want each claim committed and pushed while it is reviewed, so that a reclaimed container loses nothing.
2. As a user, I want each review to name the commit it judged, so that I can see exactly what passed.
3. As a user, I want unaccepted work kept out of the default branch, releases and completion reports, so that the gate still protects what matters.
4. As a reviewer, I want a fix to arrive as a new commit, so that a second review sees exactly what changed.
5. As a user working directly on the default branch, I want to commit freely but keep unaccepted commits off the remote default branch unless I allow it, so that others never pull unaccepted work.
6. As a user, I want no model value to break a role file, so that a role never loses its tool restrictions.
7. As a maintainer, I want the 0.15.0 sentences guarded by tests, so that they cannot drift silently.

## Implementation Decisions

- C1 changes the review rules and their documents; ADR 0007 records the change and amends ADR 0002 and ADR 0006 by note, leaving their text otherwise unchanged.
- The reviewer, verifier and analyst role definitions and the installed policy are unchanged, so no setup update is required. The separate reviewer-template-review-modes work, which does need one, stays out of scope.
- This plan's own Claims follow the current commit rule until C1 is committed; later Claims may use the new rule.
- Release follows the project rules: tag matching the manifest, validation recorded under its heading, the tag never moved or reused.

## Testing Decisions

- The seam is the configuration test module that checks skill and document text and the configuration tool (prior art: the 0.15.0 tests).
- Each new or changed assertion passes now and fails in a temporary copy outside the repository with its phrase removed.
- C2's rejection tests fail against the 0.15.0 `MODEL_RE`.

## Out of Scope

- Reviewer and analyst template changes (reviewer-template-review-modes).
- Changing the review budget, decision kinds or state model beyond the commit gate.
- Squashing or rewriting history.
