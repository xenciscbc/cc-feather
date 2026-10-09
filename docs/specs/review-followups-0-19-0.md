# Review follow-ups for 0.19.0

Label: `ready-for-agent`

Vocabulary follows [CONTEXT.md](../../CONTEXT.md). This spec collects the non-blocking findings that the 0.18.0 code reviews and verifications (Claims C1–C6 of [the security-critical routing spec](security-critical-routing.md)) and the 2026-10-07 overall review of v0.13.2 left open and that still hold at v0.18.0 (699d8e4). Two read-only analyst triages on 2026-10-09 checked every recorded item against the current text and dropped those already fixed; the remaining items, with evidence, are in the gitignored handoff `.feather/handoffs/followups-0-19-0.md`. The decisions below were settled by the user on 2026-10-09 in three grilling rounds, the third after an independent Codex opinion (gpt-6-astra, high effort) whose corrections the user adopted. It amends [ADR 0009](../adr/0009-security-critical-claims-get-an-adversarial-review.md).

The release is 0.19.0 because it changes installed role definitions, so users run a setup update. No Claim is Security-critical: every Claim changes review procedures, role instructions, documentation or tests, none changes a security guarantee at a trust boundary or the implementation or configuration of a security control, and the adversary's limits remain model instructions, not a control, as ADR 0009 records. The user may reclassify any Claim when agreeing to this spec.

## Problem Statement

The 0.18.0 review flow works, but its rules disagree with each other in places a user or main can trip over.

A fix made after outcome verification refutes a claim, or after Adversarial review breaks it, goes back to code review, yet the reviewer role is never told how to use the verifier's or adversary's findings, which range to judge, or whether it may adjudicate rejections that belong to another role. After BROKEN, nothing says what the code review and verification briefs carry. When an outcome verification call is interrupted, the next call is not told so and the procedure only describes a narrowed recheck.

Adversarial review has gaps of its own. When main finds that a HELD left an invariant uncovered and treats the call as INCONCLUSIVE, the rule that the next call waits for changed evidence can block a retry that only needs the omitted coverage, and nothing says the downgraded HELD must not reset the count. A change that shares security assumptions is said to reopen a HELD in review state, while the Adversarial review procedure says an accepted claim is not reopened. The `/cc-feather:adversarial-review` command does not say what it reviews when the workspace is clean and no range is given, or when only paths are given; it puts a gated claim that is not Security-critical outside the gate and reviews its workspace, while review state requires a clean commit for every gated claim. Early explicit calls, changed acceptance and the handoff note are described in ways that are correct only when read together with other rules.

The security analysis that precedes plan review says the user approves the plan afterwards, unconditionally, while the plan-review procedure says an unchanged plan needs no new approval; the READMEs and ADR 0009 repeat the unconditional version. Switching from off to auto after an off-mode analysis is not addressed.

Installed role definitions and READMEs drift from the glossary: the executor's inline definition of a Security-critical change is narrower than the canonical one, "security-sensitive" survives in the security-executor role and READMEs, the English README assigns "security implementation" to security-executor while the zh-TW README says Security-critical changes, the adversary row says "never edits" and "no project edits" despite the fixture exception, and "read-only Git" is undefined for the adversary. ADR 0009 omits the composition rule and when a HELD stops holding. The setup document repeats a rollback instruction. Several tests are fragile or redundant: a shipped-file scan fails on any non-UTF-8 ignored file, a skill count is hard-coded twice, and some new rules are pinned only as anywhere-in-file text.

## Solution

Ship 0.19.0 with the Claims below:

- give the code review of a post-REFUTED or post-BROKEN fix one rule, stated in the reviewer role and both procedures, and tell an outcome verification call whether the previous call completed;
- make the Adversarial review procedure, review state and the command agree on retries, counts, reopening, early calls, the reviewed range and gated claims that are not Security-critical;
- make the pre-approval sequence defer to the plan-review approval rule, and cover the switch from off to auto;
- align the role templates, READMEs, ADR 0009 and the setup document with the glossary and the procedures;
- harden the tests, and release with a setup-update step.

## Claims

Each Claim's acceptance is listed under its own heading below the table. Each Claim is a vertical slice: it changes every document that states or summarises its rule (procedure, role template, READMEs, ADR) together with the tests that pin it. Only the release depends on other Claims. Because every Claim edits the shared test module and several share documents, Claims are implemented and committed one at a time in the order C1 to C8. Each commit leaves the full `unittest discover` suite passing; each Claim updates the existing assertions its change affects in the same commit, with the reason in the commit message, and pins its new rules as whole sentences in the document and section that state them, README rules paired in both languages. ADR 0009 gets one amendment note for this release: the first Claim that adds to it (C4) creates it and later Claims add their items to it, without rewriting the ADR's decision text.

| Claim | Outcome | Acceptance | Depends on |
| --- | --- | --- | --- |
| C1 Security-critical wording | Role definitions, both READMEs and the shipped-wording scan use the glossary's Security-critical wording, and the scan cannot fail on an ignored non-UTF-8 file | [C1](#c1-acceptance) | — |
| C2 Adversary limits described consistently | The adversary role defines read-only Git, and both READMEs describe its limits without contradicting the fixture exception | [C2](#c2-acceptance) | — |
| C3 Post-fix re-review | A fix after REFUTED or BROKEN gets one defined code review, its briefs carry the findings at the decided disclosure level, and an outcome verification brief says whether the previous call completed | [C3](#c3-acceptance) | — |
| C4 Adversarial review retries, reopening and disclosure | Retry after INCONCLUSIVE, the count, HELD reopening, changed acceptance, stops and disclosure agree across the procedure, review state, the READMEs and ADR 0009 | [C4](#c4-acceptance) | — |
| C5 Command scope and gated claims | The command's reviewed range is defined for every argument and workspace combination, and a gated claim that is not Security-critical is reviewed on a clean commit without prior passes | [C5](#c5-acceptance) | — |
| C6 Pre-approval approval rule | The security analysis sequence defers approval to plan review's approval rule and covers the switch from off to auto, in the procedure, the READMEs and ADR 0009 | [C6](#c6-acceptance) | — |
| C7 Test maintenance | The role-key, prefix-upgrade and skill-count tests are robust and non-redundant | [C7](#c7-acceptance) | — |
| C8 Release 0.19.0 | 0.19.0 is validated, recorded with its setup-update and rollback steps, and tagged after acceptance | [C8](#c8-acceptance) | C1–C7 |

### C1 acceptance

1. **Executor (sw-1).** The executor role's inline definition of a Security-critical change adds "including where sensitive data goes and how untrusted data is interpreted downstream", so it matches the delegation skill's definition.
2. **Security-executor (sw-2).** The security-executor role's description and scope use "Security-critical" instead of "security-sensitive"; both READMEs' role tables and routing text use Security-critical wording instead of "security-sensitive" and 「安全敏感」.
3. **Security-executor's share (sw-3).** The English README's routing paragraph says the implementation of Security-critical changes belongs to security-executor, as the zh-TW README does.
4. **Absence tests.** Tests assert that no shipped role template and neither README contains "security-sensitive", and that the zh-TW README does not contain 「安全敏感」.
5. **Shipped-wording scan (sw-4).** The scan for retired security-boundary wording reads only files that ship (files under the skill and template directories that Git does not ignore, plus the READMEs and setup document), so an ignored non-UTF-8 file cannot fail it; its pattern matches "security" and "boundary" separated by whitespace or a hyphen; it asserts that the glossary mentions the retired phrase only in its _Avoid_ line.

### C2 acceptance

1. **Adversary Git (adv-1).** The adversary role states that read-only Git commands change no refs, index or configuration and contact no remote, as a sentence added beside the existing permission, so the existing safety-limit assertion keeps its sentence. The existing safety limits and the clarification that they are instructions are unchanged.
2. **Adversary row (adv-2).** Both READMEs' adversary row describe its limits without contradicting the fixture exception: it never fixes the code, and it changes project files only for a fixture the brief lists in a call that needs no clean workspace, resetting it afterwards.
3. **Model table (adv-5).** The zh-TW default-model table names the adversary row in the same style as the other rows.
4. A test asserts that both adversary rows state the fixture exception.

### C3 acceptance

1. **One rule for the fix review (reviewer (b), ar-3).** Code review states, once, for a fix after REFUTED or after BROKEN: when the immediately preceding code review call for the claim completed, the review is a narrowed second review whose judged range starts at the commit that call judged, with the full diff from the claim's base revision supplied as context; when it did not complete, the next call reviews the claim's full scope from its base revision, as review state's completed-call rule says.
2. **Findings in the brief.** The brief carries the verifier's or adversary's findings with main's FIX or REJECT disposition for each. The reviewer checks that each FIX finding is addressed in the code and that the fix introduces no regression. It does not adjudicate a rejection of a verifier or adversary finding, which stays with that role; it keeps its own authority to uphold its own earlier findings and to report any blocking defect it finds in the fix.
3. **Reviewer role.** The reviewer role states item 2 and conditions its narrowing on the brief saying the previous call completed, as it already does; its existing sentence keyed on "the previous call for this claim" stays a single line.
4. **Procedures agree.** Outcome verification step 4 and Adversarial review step 7 point to the code review rule of item 1 instead of restating it. Adversarial review step 7 states that the code review and outcome verification briefs after BROKEN carry the adversary's findings as item 5 describes.
5. **Disclosure (Q11).** A finding passed from Adversarial review to code review or outcome verification carries by default the violated invariant, the location, the root cause and the observed and expected behaviour, without exploit steps; main adds non-public supporting detail when a role needs it to judge the fix. This never forbids the verifier's existing reproduction and counterexample duties.
6. **Verification after an incomplete call (Q8).** Outcome verification step 2 says the brief states whether the previous call for the claim completed, and step 4 says that after a call that did not complete the next call verifies the claim's full acceptance rather than only the original failure. The verifier role is not changed, since it has no narrowing sentence.
7. The scenario table maps: a fix after REFUTED with a completed preceding review; a fix after BROKEN; a fix review after a failed review call; a rejected verifier finding in a fix review; an interrupted verification call followed by a recheck.

### C4 acceptance

1. **Retry by cause (ar-1, Q4).** The Adversarial review procedure distinguishes, for any INCONCLUSIVE whether the adversary returned it or main derived it from a HELD under step 6: when the open item is coverage the role could have examined with the targets and evidence it had, the next call may run once the brief names each uncovered invariant and gap; when it lacks a target, evidence or prerequisite, the existing rule applies and the next call waits for that to change. Either call counts toward the two-call stop.
2. **Count.** A HELD that main does not accept under step 6 counts as a non-pass and never resets the automatic count; explicit calls stay outside the count.
3. **HELD reopening (sw-7).** Review state's statement that a change sharing a claim's security assumptions reopens its HELD names the exception in Adversarial review step 9: when the change belongs to a new claim, the new claim owns the composed review and the accepted claim is not reopened.
4. **Changed acceptance (ar-4).** Review state's changed-acceptance decision says it reopens the claim's HELD as well as its review and verification.
5. **Early explicit HELD (ar-8, ar-9).** Review state's Clearing a stop says an explicit HELD obtained before the claim's valid APPROVED and CONFIRMED does not clear a stop, and What an explicit call runs says that its rule on early explicit calls holds in off as well as auto.
6. **Handoff note (ar-6).** Adversarial review step 8's handoff note points to step 10, so a tracked handoff records findings only as a summary.
7. **README disclosure (sw-8).** The English README's disclosure sentence lists "an ADR or a validation entry" among public records and says exploit details "stay only in" untracked records, matching the procedure and the zh-TW README.
8. **ADR 0009 (sw-7, sw-6).** This Claim creates ADR 0009's 0.19.0 amendment note, recording composition (a review of changes that share security assumptions covers their composed revision, and a new claim owns the composed review without reopening an accepted one) and when a HELD stops holding (the reopening triggers in review state, with that exception). Tests pin these items and ADR 0009's two considered options on hooks or frontmatter and on reviewer, verifier and analyst templates, which are not yet pinned.
9. ar-4, ar-8 and ar-9 clarify behaviour that other rules already imply; the commit message says so.
10. The scenario table maps: HELD missing an invariant, then a retry naming it; INCONCLUSIVE for a missing target, then no retry until the target changes; a downgraded HELD followed by an automatic BROKEN (stop); a new claim sharing assumptions with an accepted one; changed acceptance after HELD; an early explicit HELD while the step is stopped.

### C5 acceptance

1. **Gated claims that are not Security-critical (Q13, original ar-10).** The command separates two questions. Whether the acceptance gate covers the claim decides whether the call needs a clean commit: for any gated claim, the workspace equals the named commit, as review state's What a gated pass judged requires. Whether the gate requires Adversarial review for the claim decides whether the call needs a valid APPROVED and CONFIRMED and can count as the step's pass: only for a Security-critical claim the gate covers. A gated claim that is not Security-critical therefore gets a clean-commit call that needs no prior passes and satisfies no gate.
2. **Reviewed range for ungated work (Q6).**
   1. With a commit range, the call reviews that range, judged at the range's end commit; uncommitted changes are excluded and the report says so. Dynamic probing tests only what the brief's targets run; when the range's end is not the workspace's content, the report says the targets cannot be shown to run that revision and treats what needs execution as INCONCLUSIVE.
   2. Without a range and with uncommitted changes, the call reviews the change against HEAD, including staged, unstaged and in-scope untracked files; committed branch changes are not included, and the report says so.
   3. Without a range and with a clean workspace, main asks the user which range to review.
   4. Paths narrow the range of 2.1 or 2.2. When the paths have no change in that range, main asks the user instead of reviewing whole files.
3. **Early calls (ar-7, ar-11).** The Adversarial review procedure's step 1 and the command's Before the passes use the same condition, a claim that does not yet have a valid APPROVED and a valid CONFIRMED at the same commit, and say which commit an early explicit call reviews: the commit the user names, or HEAD when the user names none, with the workspace equal to it.
4. **Narrowed scope (ar-12).** The command's statement that paths or a narrower scope never reduce what a HELD must cover points to review state's narrowed second review, and says the two coexist: narrowing follows the completed-call rule, and a HELD still covers every invariant and open gap.
5. **READMEs.** Both READMEs' command paragraph and the command's argument hint state items 1 and 2 in summary; tests pin the paragraph's sentence that targets come only from an approved plan or the user's own arguments (sw-6), in both languages.
6. **ADR 0009.** The amendment note gains the separation of a gated claim's clean commit from the gate's requirement of Adversarial review.
7. The scenario table maps: a gated non-Security-critical claim with a dirty workspace (refused until clean); one on a clean commit (runs, satisfies no gate); a commit range with a dirty workspace; no range with a dirty workspace; no range with a clean workspace (main asks); paths with no change (main asks); an early explicit call naming no commit.

### C6 acceptance

1. **One approval rule (pre-1, Q2).** Plan review's security analysis paragraph replaces both of its approval formulations ("approves the plan only after both" and "then approves it") with one statement that the user's approval follows plan review step 5: a disposition that adds a security invariant or otherwise materially changes outcome, scope or acceptance needs the user's approval of the revised plan; a plan the analysis leaves unchanged keeps the user's earlier agreement. The separate rule that main never approves its own plan for unplanned risky work is unchanged.
2. **Off to auto (pre-2, Q3).** The paragraph adds: when auto is turned on for a plan whose Security-critical claim had a security analysis in off, that analysis is reused while its trust boundary, attacker capability and controls still apply, and otherwise reopens under the existing triggers; main dispositions its findings and records the test targets before the automatic plan review; an explicit READY from off does not count as the step's pass. Work already implemented in off first follows review state's Implemented before plan review.
3. **READMEs.** Both READMEs' pre-approval sentence states items 1 and 2; tests pin the README statements that a READY waiver does not waive the security analysis and that off mode does not force the sequence (sw-6), in both languages.
4. **ADR 0009.** The amendment note gains that approval after security analysis follows plan review's approval rule.
5. **Position pins (pre-3).** The tests for the 0.18.0 pre-approval rules assert each sentence within its section (the waiver sentence in review state's Implemented before plan review bullet, the delegation skill's sentence in its security analysis paragraph), not only somewhere in the file.
6. The scenario table maps: analysis adds an invariant (user approves again); analysis changes nothing (earlier agreement stands); off-mode analysis then auto with unchanged boundary; the same with a new trust boundary; work implemented in off then auto.

### C7 acceptance

1. **Role keys (adv-4).** The redundant forbidden-key loop after the exact key-list assertion is removed, and the role-list count test's condition is rewritten for readability without changing what it accepts.
2. **Prefix upgrade (adv-4).** A test upgrades a 0.17.0 installation whose roles already use the `cc-` prefix and asserts the update adds `cc-adversary`.
3. **Skill count (ar-13 N8).** The skill count is derived from the manifest in one place; the hard-coded count is removed.

### C8 acceptance

1. `.claude-plugin/plugin.json` is 0.19.0.
2. **Upgrade fixture.** Tests build an installation from the exact 0.18.0 role templates of every role this release changes (executor, security-executor, adversary, reviewer), not from current templates with selected lines replaced, and assert that `show` and `check` report those roles stale with `role_update_required`, and that setup update renders the current text.
3. The 0.19.0 validation entry and both READMEs' Updates sections say a setup update is required in every scope where delegation is installed, followed by a fresh session, because role definitions changed.
4. **Rollback (sw-5).** The setup document's rollback paragraph states one recovery instruction covering every older version it lists, including 0.17.0 and older with an adversary-bearing state, instead of the adversary-specific sentence plus the generic one. The assertions pinning the adversary sentence are updated with the reason in the commit message.
5. The suite and `claude plugin validate` pass on Windows, with Python and Claude Code versions, test counts and skip reasons recorded. The entry records the live scenarios run for C3–C6 with the installed native roles after setup update, and those not exercised.
6. Before the tag is created, main checks that the manifest version is 0.19.0 and that no `v0.19.0` tag exists. The tag `v0.19.0` is created only after both passes and only with the user's go-ahead; that it names the release commit and matches the manifest version are checked afterwards as postconditions.

## Decisions

Settled by the user on 2026-10-09; "Codex" marks a correction from the independent opinion that the user adopted in the third round.

- **Q1: one release.** Every still-valid item ships in 0.19.0 with one setup update. Options not taken: procedures first, templates in 0.20.0; defects only.
- **Q2: approval after security analysis follows plan review step 5.** Adding an invariant changes acceptance and needs approval; an unchanged plan keeps the earlier agreement. All approval formulations change together (Codex). Option not taken: always approve again.
- **Q3: off to auto reuses an applicable analysis.** Reuse is conditional on boundary, attacker capability and controls still applying; findings are dispositioned, not all turned into invariants; implemented work first follows Implemented before plan review (Codex). Option not taken: leave the interaction implicit.
- **Q4: retry by cause.** Coverage the role could have examined may be retried with the gaps named; a missing target, evidence or prerequisite still waits; the same holds for an adversary-returned INCONCLUSIVE; a downgraded HELD never resets the count (Codex). Option not taken: exempt every main-derived INCONCLUSIVE.
- **Q5: the glossary's Adversarial review definition is scoped by the Acceptance gate** (committed in 03bda37). "Outside the flow" stays in use for explicit requests and is not added to _Avoid_.
- **Q6: the command's range.** As in C4 item 2. The whole-file fallback for paths with no change was dropped (Codex): it would be a new review mode whose BROKEN cannot apply to pre-existing vulnerabilities. Option not taken: review whole files at HEAD.
- **Q7: the fix review is a narrowed second review only after a completed call, judged from the previously judged commit; the reviewer keeps its own authority** (Codex). Option not taken: always judge from the approved commit.
- **Q8: an interrupted verification is followed by full-acceptance verification, and the brief says whether the previous call completed** (Codex).
- **Q10: vertical Claims.** Each Claim changes every document that states or summarises its rule, with its tests; only the release depends on other Claims, and shared files are handled by implementing and committing Claims in order (re-cut with the to-tickets method after the user's review). Options not taken: separate README, ADR and test-only Claims; dependencies for file overlaps.
- **Q11: minimal disclosure by default** for findings passed from Adversarial review to other roles, not a ban (Codex).
- **Q12: the glossary change was committed separately** as unplanned work, not a gated claim.
- **Q13: a gated claim always needs a clean commit; prior passes are needed only where the gate requires Adversarial review** (Codex, restoring original ar-10).
- Dropped as optional: ADR 0006's Consequences wording (W11) and the README review-or-verification wording (ar-5 residue).

## User Stories

1. As a user whose claim was refuted, I want the code review of the fix to judge what changed since the last completed review, so that it neither repeats the whole review nor misses the fix.
2. As a user, I want a code review after a failed review call to cover the whole claim, so that a retry never approves code nobody reviewed.
3. As a user, I want the reviewer to check that each finding main chose to fix is actually fixed, so that a fix that misses the finding is caught before verification.
4. As a user, I want rejections of the verifier's or adversary's findings judged by that role, so that the reviewer does not overrule a role it cannot reproduce.
5. As a user, I want the reviewer to keep reporting new blocking defects in a fix, so that a narrowed review is still an independent review.
6. As a user whose Security-critical claim was broken, I want the fix's code review and verification to see what was broken, so that they can judge the fix.
7. As a user, I want exploit steps kept out of other roles' briefs unless needed, so that exploit details spread no further than necessary.
8. As a user, I want a verification after an interrupted call to verify the whole claim, so that an interruption never narrows coverage.
9. As a user, I want an Adversarial review that skipped an invariant to be retried with that invariant named, so that a coverage slip does not leave my claim blocked for good.
10. As a user, I want a retry for a missing test target to wait until the target exists, so that calls are not wasted.
11. As a user, I want a HELD that main rejected never to reset the count, so that the two-call stop still means something.
12. As a user, I want an accepted claim not to be reopened when a later claim shares its security assumptions, so that the new claim owns the composed review.
13. As a user, I want changing a claim's acceptance to reopen its HELD, so that the review matches what is now promised.
14. As a user, I want an early explicit HELD not to clear a stopped step, so that only a valid review clears it.
15. As a user with a tracked handoff, I want a stopped Adversarial review recorded only as a summary, so that exploit details do not reach the repository.
16. As a user running `/cc-feather:adversarial-review` on a commit range, I want uncommitted changes left out and reported, so that I know what was reviewed.
17. As a user with uncommitted changes and no range, I want the command to review them, including new files, so that work in progress can be attacked.
18. As a user with a clean workspace and no range, I want to be asked what to review, so that the command does not guess.
19. As a user naming paths that did not change, I want to be asked rather than get a whole-file review, so that a verdict always means what BROKEN means.
20. As a user with a gated claim that is not Security-critical, I want an Adversarial review of it to run on its clean commit, so that the result matches the commit the other passes judge.
21. As a user, I want such a review to need no prior passes and satisfy no gate, so that asking for it costs nothing in the flow.
22. As a user, I want an early explicit call to say which commit it reviewed, so that I can relate its findings to the passes that follow.
23. As a user approving a Security-critical plan, I want to be asked again only when the security analysis changed the plan, so that I am not asked twice for the same plan.
24. As a user, I want to approve the plan again when the analysis added a security invariant, so that I agree to what will be enforced.
25. As a user switching from off to auto, I want an off-mode analysis reused when it still applies, so that no analysis runs twice for nothing.
26. As a user switching from off to auto, I want the findings dispositioned before the automatic plan review, so that the review judges the revised plan.
27. As a user who implemented work in off, I want switching to auto to ask me first as for any implemented work, so that the rule I already know applies.
28. As a reader of the README, I want both languages to say the same thing about security-executor and the adversary, so that neither misleads me.
29. As a maintainer, I want the role definitions to use the glossary's terms, so that the installed roles route the same changes the procedures do.
30. As a user, I want the adversary told what read-only Git means, so that it does not fetch or rewrite state while attacking.
31. As a maintainer, I want ADR 0009 to record composition and when a HELD stops holding, so that the decision record is complete.
32. As a user downgrading, I want one rollback instruction for every older version, so that I follow one procedure.
33. As a maintainer, I want the test suite not to fail because of an ignored non-UTF-8 file, so that a local artefact does not break the build.
34. As a maintainer, I want the skill count stated once, so that adding a skill updates one place.
35. As a user upgrading from 0.18.0, I want `check` to tell me which roles are stale and that setup update fixes them, so that I am not running old instructions.

## Implementation Decisions

- **Code review procedure** holds the single fix-review rule (C2 item 1); outcome verification and Adversarial review point to it.
- **Outcome verification procedure** gains the previous-call completion in its brief and the full-acceptance recheck after an incomplete call.
- **Adversarial review procedure** gains the cause-based retry rule, the count rule for a downgraded HELD, the brief contents and disclosure level after BROKEN, the step 8 pointer to step 10, and the shared early-call condition with the command.
- **Review state procedure** gains the composition exception to HELD reopening, HELD in changed acceptance, and the early-HELD clarifications; each rule is stated once there and other documents point to it.
- **Adversarial-review command** separates the gate's coverage of the claim (clean commit) from the gate's requirement of Adversarial review (prior passes), and defines the reviewed range for each argument and workspace combination.
- **Plan review procedure** replaces the two approval formulations with a pointer to step 5 and adds the off-to-auto sentence.
- **Role templates**: executor, security-executor, adversary and reviewer change, so the release requires a setup update; verifier, analyst and the rest are unchanged.
- **READMEs** change only to summarise rules the procedures state and to align the two languages.
- **ADR 0009** gets an amendment note; its decision text and historical release entries are not rewritten.
- **Setup document** merges its rollback instructions.

## Testing Decisions

- Tests check external behaviour: what a shipped document says and what the configuration tool installs and reports. No new seam is introduced.
- **S1, procedure contracts (existing seam).** The configuration tool's test module pins procedure, template, README, glossary and ADR text. New rules are pinned as whole sentences in the document and section that state them, README rules paired in both languages, and replaced wording gets absence checks where a Claim says so. The scenario table maps each scenario listed in C3–C6 to the sentences governing it. Prior art: the review-state rule tests, the security routing scenario tests and the README pairing tests.
- **S2, configuration tool (existing seam).** In-process tests install from the exact 0.18.0 templates of the changed roles, assert stale-role reporting and that setup update renders current text, and upgrade a prefixed 0.17.0 installation that lacks the adversary. Prior art: the 0.16.0 stale-template tests and the adversary upgrade tests.
- Text tests cannot prove agent behaviour; the C8 validation entry records which live scenarios ran with the installed native roles and which did not.
- The full suite runs on Windows for every Claim and for the release.

## Out of Scope

- A whole-file audit mode for the command.
- Changing review budgets, the one-retry rule, the stop rules or the default-branch rules.
- Enforcing the adversary's limits through permission settings, hooks or a sandbox.
- ADR 0006's Consequences wording and the README review-or-verification wording.
- Rewriting historical spec, ADR decision text or validation entries.

## Further Notes

- The roles installed on the machine where this spec was written appeared to carry 0.16.0 prompts; live scenarios for C8 run only after setup update with the 0.19.0 package, and the validation entry says which roles were installed.
- The ticket files mirror the Claims table under `.scratch/review-followups-0-19-0/issues/`.
- C5 item 3's choice of HEAD for an early explicit call that names no commit was made while writing this spec, to settle ar-11's unclear reference.
