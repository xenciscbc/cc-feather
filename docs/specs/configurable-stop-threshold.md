# Configurable Stop threshold

Label: `ready-for-agent`

Vocabulary follows [CONTEXT.md](../../CONTEXT.md). The decisions below were settled by the user on 2026-10-10 in two grilling rounds (Q1–Q13) and a confirmation of the conventions that follow from them. This spec changes the number fixed by [ADR 0004](../adr/0004-consecutive-failure-review-budget.md) and the bounds [ADR 0009](../adr/0009-security-critical-claims-get-an-adversarial-review.md) derives from it; it changes nothing else in either decision. The [0.19.0 review follow-ups spec](review-followups-0-19-0.md) listed changing review budgets as out of scope, so this is release 0.20.0.

The user agreed to the first version on 2026-10-10 (009828b). Plan review call 1 (automatic) returned REVISE: the cost bounds were linear in K although a fix after REFUTED restarts code review while verification's count runs across fixes (B1); a change of K did not cover a stop an explicit pass had cleared or an inherited one (B2); a value saved in the conversation applied as a session choice, against the project-over-user order (B3); ADR 0006 and other README paragraphs stating the fixed numbers were not covered (B4); the glossary change in 009828b fails an existing test (B5); and the Schedule could not record the review history C4 requires (B6). The user decided on 2026-10-10 to keep the range 2–10 with the corrected costs (Q14) and that a saved value re-resolves rather than acting as a session choice (Q15); the other blockers and the non-blocking findings are revised below.

The analyst agreed with the classification below. No Claim is Security-critical. The Stop threshold only decides how many consecutive automatic calls without a pass stop a step: it changes no verdict, no pass requirement, no Acceptance gate condition, no role's tools or limits and no place sensitive data goes. The value written into guidance is an integer the configuration tool validates, never user text.

## Problem Statement

In auto, every step of the Automatic flow stops after two consecutive automatic calls without a pass and waits for the user's explicit request. Two is fixed. A user whose reviews often need a third or fourth round, for example on a large Claim or a Security-critical claim whose Adversarial review is likely to return BROKEN once, has to step in every time, even when they would rather let the flow keep going. A user who wants the flow to keep trying cannot say so, either for one session or as a standing preference for a project or for all their projects.

## Solution

The number becomes the **Stop threshold**, one integer K from 2 to 10 that applies to every step: plan review, code review, outcome verification and Adversarial review. The default stays 2, so an installation where nobody sets it behaves exactly as today.

The user can set K:

- for the current task or session, by saying so or with `/cc-feather:stop-threshold <K>` without a scope; nothing is written;
- for a project or for their user configuration, with `/cc-feather:stop-threshold <K> project|user`, which saves it through the configuration tool and writes one sentence stating it into the managed delegation guidance; a project's value overrides the user's.

`default` in place of K removes the saved value for that scope. Everything else about counting stays as ADR 0004 and ADR 0002 define it: only an automatic pass resets a count, failed, interrupted and protocol-failure calls count, switching models or renaming never resets, verification's count runs across fixes, counts are per session, and Explicit requests sit outside the count.

## Claims

Each Claim's acceptance is listed under its own heading below the table. Each Claim is a vertical slice: it changes every document that states or summarises its rule (procedure, skill, READMEs, setup document, ADR) together with the tests that pin it.

| Claim | Outcome | Acceptance | Depends on |
| --- | --- | --- | --- |
| C1 Saved Stop threshold | The configuration tool saves, validates, shows, preserves and removes K per scope and states a set K in the delegation guidance, and the setup document describes it | [C1](#c1-acceptance) | — |
| C2 Procedures use the Stop threshold | Every review procedure, review state and the delegation preview stop at K resolved from the session, the guidance or the default, handle a change of K mid-count, and state costs in K; the READMEs, ADR 0010 and the amendment notes describe it | [C2](#c2-acceptance) | C1 |
| C3 Stop-threshold command | `/cc-feather:stop-threshold` sets K for the session, a project or the user, and the READMEs list it | [C3](#c3-acceptance) | C1, C2 |
| C4 Release 0.20.0 | 0.20.0 is validated, recorded with its update and downgrade notes and tagged after acceptance | [C4](#c4-acceptance) | C1–C3 |

**Schedule.** Every Claim edits the shared test module and C2 and C3 share the READMEs, so a later Claim's commit is a change to an earlier Claim's files and would reopen its passes under review state. Claims are therefore implemented and committed one at a time in the order C1 to C4, each commit labelled as unaccepted as review state's Commits before the passes describes; Before C1, one commit updates only the existing glossary assertion for Unreviewed claim to the wording 009828b gave it, so the suite passes again (B5); that commit, or the last later commit that changes only this spec, is C1's base revision, and each later Claim's base revision is the previous Claim's last commit. Once C4 is committed, that commit is the candidate, and each Claim gets code review and then outcome verification in the order C1 to C4 at the candidate: code review judges the Claim's own range, later commits being context only, and verification checks the Claim's full acceptance. A fix is a new commit and a new candidate, and each Claim whose passes it reopens gets its reopened steps again. A commit that only records the review history in C4's validation entry reopens C4 alone, and main states for each other Claim why it does not affect its passes; C4's code review and verification, and the suite result its entry records, are then at that recording commit (B6). Nothing is pushed until every Claim is accepted, and the tag follows C4 item 4.

Each commit leaves the full `unittest discover` suite passing; each Claim updates the existing assertions its change affects in the same commit, with the reason in the commit message, and pins its new rules as whole sentences in the document and section that state them, README rules paired in both languages.

### C1 acceptance

1. **Setting.** The configuration tool's `review` command accepts `--stop-threshold` with an integer from 2 to 10 or `default`, in project and user scope, with or without `--review-mode`, through the usual preview and `--apply --expected-plan` steps. It needs the delegation component installed in that scope, like `--review-mode`.
2. **Validation.** 1, 11, 0, a negative number, a non-integer or any other text is refused with a usage or configuration error before anything is written; so is `--stop-threshold` on a command other than `review` or with delegation absent from the scope.
3. **State.** The delegation record in the scope's state gains the Stop threshold only when a value is set; `default` removes it, so a scope that never set one, or set it back to default, has a record identical to 0.19.0's. Loading a state whose Stop threshold is outside 2–10 or not an integer, including a JSON boolean, is refused like other malformed state.
4. **Guidance.** A scope with a set K has one sentence in its managed delegation block, separate from the automatic review paragraph and present whether the Review mode is auto or off: in user scope it states that the Stop threshold for automatic review is K; in project scope it states the Stop threshold in this project is K and that this overrides broader Feather guidance. A scope without a set K has no such sentence, and its guidance bytes equal what 0.19.0 writes for the same choices, so no older-template warning appears; a scope with a set K shows no older-template warning either. Delegation guidance from a template older than the one this release can edit is not changed by `--stop-threshold`: the command is refused with the instruction to run setup update first.
5. **Show and check.** `show` and `check` report the scope's saved Stop threshold, or the default 2 with an indication that none is set. The `session` export is unchanged by a set K.
6. **Preservation and removal.** Setup update, `model`, switching `--review-mode` and installing or removing the handoff component keep a set K and its sentence; removing the delegation component removes both. A failed write rolls back the state and guidance as for the other settings.
7. **Setup document.** The setup document describes the setting, its scopes and default, that the guidance sentence is how main learns a saved value, and that the limit remains an agent instruction rather than a hook-enforced counter.
8. **Tests.** Tests through the tool's command line cover items 1–6, including byte equality of guidance for a scope without K, the project override sentence, the sentence in off mode, no older-template warning with K set, the refusal on older-template guidance, a boolean in state, the unchanged `session` export, rollback, and preservation across update, `model` and Review mode changes.

### C2 acceptance

1. **Resolution.** Review state defines the Stop threshold in effect for a session as, in order: the user's task or session choice; otherwise the value the loaded project guidance states; otherwise the value the loaded user guidance states; otherwise 2. Main never raises or lowers it on its own; a task or session choice comes only from the user's own words in this conversation. A guidance value that is not an integer from 2 to 10 is not used: main takes the next source and reports the invalid value. When main cannot establish whether a task or session choice exists, for example after context compaction, it treats the threshold as unknown, as review state's Unknown state does for counts: affected steps are treated as stopped and main asks the user.
2. **Stopping at K.** Review state's Consecutive non-pass count and Stop transition, and the plan review, code review, outcome verification and Adversarial review procedures, stop a step after K consecutive automatic calls without a pass instead of two; every sentence that states the fixed two as the stopping point now refers to the Stop threshold. Sentences about a second call that follows a non-pass keep their meaning.
3. **One rule for the next automatic call (B2).** A step's next automatic call for a work needs the user's explicit request exactly while that step's count for the work is at or above the Stop threshold in effect, and is made without one while it is below. This single rule replaces each statement that derives the need for a request from a count left where it stopped: after an explicit pass that cleared a stop, for a reopened call, for a review after a Material deviation, for the review of a fix, and for work that inherits an overlapping plan's count and stop; review state's Clearing a stop, Reopened calls and Overlap, the plan review, code review, outcome verification and Adversarial review procedures, both READMEs and ADR 0006's amendment note state it, and tests pin those sentences. An explicit pass still clears a stop without changing the count, and a valid pass stays valid whatever K is.
4. **Changing K mid-count.** A change of K never changes a count; the rule in item 3 is applied with the new K at once. A stopped step whose count is now below the new K resumes automatically, because the change is the user's own act; a step whose count reaches or exceeds the new K stops at once. Main lists the steps the change resumed or stopped in its reply. A value the user saves in project or user scope in this conversation replaces any earlier task or session choice in this conversation, and the Stop threshold in effect is resolved again from the saved values in the order of item 1, so this session uses what a new session would (Q15): a user value saved where the project states its own is reported as overridden by it.
5. **Stating K.** Whenever a review decision comes up, main states the Stop threshold in effect and its source (task, session, project, user or default), as it does for the Review mode, so a compacted summary is more likely to keep a session choice; a session choice does not cross sessions and is not written into a handoff.
6. **Unchanged rules.** The procedures still say that only an automatic pass resets a count; that failed, interrupted and protocol-failure calls count; that mode changes, renamed Plans, cosmetic splits and a different reviewer, model or wording never reset it; that outcome verification's count runs across fixes and resets only on CONFIRMED; that code review of a fix after REFUTED or BROKEN counts from the reset of its earlier APPROVED; that counts are per session; and that Explicit requests sit outside the count. The pre-approval security analysis is not a counted step and K does not apply to it.
7. **Preview and cost (B1, Q14).** The delegation preview states the Stop threshold in effect and its source and gives each stop in terms of K, in one uninterrupted attempt: a Claim makes at most K(K+1) automatic calls (up to K verification calls, between which up to K − 1 fixes each get up to K code reviews, plus up to K code reviews before the first verification); a Security-critical claim at most K³ + K² + K (also up to K Adversarial reviews, between which up to K − 1 fixes after BROKEN each get up to K(K+1) code review and verification calls); a Plan with N Claims of which S are Security-critical about K + K(K+1)N + K³S. Each reopened Claim or approved Material deviation adds calls, including up to K plan reviews for each deviation.
8. **READMEs (B4).** Both READMEs state the rule in terms of the Stop threshold wherever they state the fixed number: the budget, cost and preview paragraphs, and the paragraphs on a step that has not passed, validity and reopening, what happens after a stop, and partial overlap, including the statement that a Claim refuted twice in a row stops after one rechecked fix, which becomes: a Claim refuted K times in a row stops after K − 1 automatically rechecked fixes. They give the bounds for K = 2 (6, 14, 2 + 6N + 8S) and K = 10 (110, 1110, 10 + 110N + 1000S), say that the bounds grow faster than K because each fix is reviewed again, and say how to set it.
9. **Decision record.** ADR 0010 records that the Stop threshold is one user-configurable integer from 2 to 10 with default 2, resolved from task or session, project guidance, user guidance, default; the rule in item 3; that a change of K resumes or stops steps but never changes a count, and a saved change re-resolves; the cost bounds of item 7, and that the user kept the range 2–10 knowing them (Q14); why the minimum is 2 (a single non-pass can be a transient interruption or protocol failure, and stopping on it would interrupt the user for noise), why there is no unlimited value (ADR 0004 rejected an unbounded loop), and why one number rather than one per step. Its Considered Options cover a fixed two, per-step values, allowing 1 or unlimited, a smaller maximum, a saved value acting as a session choice, and main reading the saved value with the tool at each decision. ADR 0002, ADR 0003, ADR 0004, ADR 0006 and ADR 0009 each get an amendment note that their fixed two, six and fourteen (and ADR 0002's two more automatic calls) are the values at the default Stop threshold, and ADR 0006's note also carries item 3's rule.
10. **Retired wording.** Tests assert that no shipped skill file, README or the setup document states two consecutive automatic calls, six calls per Claim, fourteen per Security-critical claim, a Claim refuted twice stopping after one rechecked fix, or a request needed because a count stays where it stopped, as a fixed rule, except where the text gives the K = 2 example; the pinned whole sentences cover items 1–8.

### C3 acceptance

1. **Command.** `/cc-feather:stop-threshold <2–10|default> [session|project|user]` is a user-invoked skill. Its arguments are data, never shell code. Without a scope, or with `session`, it applies to the conversation, writes nothing and runs no tool, and reminds the user that the value holds only in this conversation, that a new or resumed session uses the saved value (stated from the loaded guidance), and that compaction may drop it, offering the `project` or `user` form to keep it.
2. **Saved scopes.** With `project` or `user`, it previews the configuration tool's `review --stop-threshold`, summarises the scope and change, applies with identical arguments and the returned plan, then reads `show` and reports the saved value and owning path. The explicit scoped command authorises the change without a routine confirmation; conflicts are preserved and reported. Delegation absent from that scope is reported as needing setup, and the command never installs it or chooses user scope unasked.
3. **Effect now.** After applying a value in any scope, it applies C2 item 4 to the current session, including re-resolving after a saved change and reporting a user value the project overrides, and lists the steps resumed or stopped.
4. **Shared procedure.** The procedure lives in a reference under the setup skill, like the Review mode toggle procedure, and the command and the delegation skill both point to it, so a natural-language request to change the Stop threshold, which cannot load a user-invoked command, follows the same procedure. The delegation guidance template is not changed for this, so unset guidance stays byte-identical.
5. **Refusals.** A value outside 2–10, a non-integer or an unknown or conflicting scope is refused or clarified before anything is applied or written.
6. **Packaging and listing.** The command is registered with the plugin's skills, with frontmatter that disables model invocation and gives an argument hint like `auto-on`; the setup document's count of packaged skills becomes twelve; both READMEs list the command next to `auto-on` and `auto-off`, and the setup skill's component and command lists include it.
7. **Tests.** Tests pin the command's scope, reminder and authorisation sentences and the delegation skill's pointer, and update any test that counts or lists the shipped skills.

### C4 acceptance

1. **Version.** `plugin.json` is 0.20.0 and the release tag will be `v0.20.0`.
2. **Validation record.** `docs/setup-validation.md` has a 0.20.0 entry recording the full `unittest discover` result at the commit C4 is verified at (see the Schedule), the review history of C1–C4, which cc-feather version's roles and procedures performed the reviews (the installed 0.19.0, not this release's candidate), that no live scenario was run under 0.20.0's own procedures, and a check that a 0.19.0 installation updated to 0.20.0 keeps byte-identical guidance and state until a Stop threshold is set.
3. **Update and downgrade notes.** The entry, the setup document and both READMEs' update paragraphs say that existing installations need only the plugin update and a fresh session; that a scope with a set Stop threshold is rejected by a 0.19.x or older configuration tool, so a downgrade first sets it back to `default` in that scope; and that a session or task choice needs nothing.
4. **Tag.** The tag is created only after C1–C4 are accepted and the user authorises the release, and its version matches `plugin.json` at the tagged commit.

## User Stories

1. As a user in auto, I want to raise the Stop threshold, so that the flow keeps reviewing a hard Claim without asking me after every second failure.
2. As a user, I want one number to apply to every step, so that I do not have to reason about four separate limits.
3. As a user, I want the Stop threshold limited to 2–10, so that a typo cannot make the flow stop on one transient failure or loop for a hundred calls.
4. As a user who never sets it, I want the Stop threshold to stay 2, so that upgrading changes nothing for me.
5. As a user, I want to set it for this session only without writing any file, so that I can try a higher value on one piece of work.
6. As a user, I want to save it for a project, so that a repository with large Claims always gets more rounds.
7. As a user, I want to save it in my user configuration, so that all my projects share my preferred value.
8. As a user, I want a project's value to override my user value, so that a project can be stricter or looser than my default.
9. As a user, I want `default` to remove a saved value, so that I can return to the package behaviour without editing files.
10. As a user, I want the saved value to reach main through the guidance it already loads, so that no extra tool call happens before each review decision.
11. As a user whose installation has no saved value, I want my guidance to stay byte-identical, so that I see no outdated-template warning.
12. As a user in off mode, I want a saved value to be kept and written, so that a later session auto-on uses it.
13. As a user, I want invalid values refused before anything is written, so that a mistake never leaves a half-applied setting.
14. As a user, I want `show` and `check` to report my Stop threshold per scope, so that I can see what is in force.
15. As a user, I want setup update, model changes and Review mode switches to keep my Stop threshold, so that I set it once.
16. As a user, I want removing delegation to remove the Stop threshold with it, so that nothing is left behind.
17. As a user whose step has stopped, I want raising K above the count to resume it, so that changing the setting is enough to continue.
18. As a user, I want lowering K to or below the current count to stop that step at once, so that my new limit takes effect immediately.
19. As a user, I want a change of K never to reset a count, so that changing the setting is not a way to erase failures.
20. As a user, I want main to list the steps a change resumed or stopped, so that I know what happens next.
21. As a user, I want a value I save in this conversation to apply to this session at once, resolved in the same order a new session would use, so that I do not have to set it twice and this session and the next agree.
22. As a user, I want main never to change the Stop threshold on its own, so that only I decide how long the flow keeps trying.
23. As a user, I want main to state the Stop threshold in effect and where it came from at each review decision, so that I can check it and a compacted summary keeps it.
24. As a user, I want a session choice not to cross sessions, so that a resumed session starts from my saved value as with the Review mode.
25. As a user, I want every other counting rule unchanged, so that what I know about resets, failed calls and Explicit requests still holds.
26. As a user, I want the delegation preview to show K, its source and the resulting maximum calls, so that I can see the cost before implementation.
27. As a user, I want the READMEs to give the bounds for K = 2 and K = 10 and say they grow faster than K, so that I understand what raising it costs.
28. As a user reading the Traditional Chinese README, I want the same rules as the English one, so that both audiences are told the same thing.
29. As a user, I want a `/cc-feather:stop-threshold` command with the same scopes as `auto-on` and `auto-off`, so that the setting works like the one I already know.
30. As a user, I want the session form of the command to remind me that nothing was written, so that I am not surprised in the next session.
31. As a user, I want the command to report when delegation is not installed in a scope, so that it never installs anything unasked.
32. As a user downgrading, I want to be told that a saved Stop threshold blocks an older tool, so that I set it back to default first.
33. As a maintainer, I want ADR 0010 to record why the minimum is 2, why there is no unlimited value and why there is one number, so that a later reader does not reopen those choices without reason.
34. As a maintainer, I want ADR 0003, ADR 0004 and ADR 0009 to note that their fixed numbers are the default values, so that the record stays consistent without rewriting decisions.
35. As a maintainer, I want tests to fail if a shipped document reintroduces a fixed two-call limit, so that the documents cannot drift back.

## Implementation Decisions

- **One integer for every step.** The Stop threshold applies to plan review, code review, outcome verification and Adversarial review alike. Per-step values were rejected for now: no need for them is known and they would turn the cost formula into four variables; a later per-step override could be added without breaking a single saved value.
- **Range and default.** Integers 2 to 10 inclusive; default 2. Zero is unnecessary because `off` already exists, 1 is excluded so a transient failure never stops a step alone, and there is no unlimited value.
- **Delivery through guidance.** Plugin skill files are shared by every installation, so a saved value reaches main only through the managed delegation block the configuration tool renders. The procedures read the value the loaded guidance states; they do not run the tool at each decision.
- **Rendering.** The sentence is rendered only for a scope with a set value, separately from the automatic review paragraph and in both Review modes; the project form adds that it overrides broader Feather guidance, mirroring the existing project off line. This keeps unset installations byte-identical.
- **State schema.** The delegation record's fixed key set gains one optional key, present only when set. Older tools reject a record that carries it; this is accepted and documented, following the precedent of the adversary role in 0.18.0.
- **Configuration interface.** The `review` command gains `--stop-threshold`; it combines with `--review-mode` in one plan. No other command accepts it.
- **Resolution order.** Task or session choice, then project guidance, then user guidance, then 2. A choice comes only from the user's words; main states K and its source with each review decision. An invalid guidance value is skipped and reported; an unknown session choice is handled like an unknown count.
- **Next automatic call.** One rule decides whether a step's next automatic call needs the user's request: only while its count is at or above the Stop threshold in effect. It replaces the statements that derive the need for a request from a count left where it stopped, so a cleared, reopened, inherited or fix review all follow it.
- **Mid-count changes.** Counts never change with K; the rule above is applied with the new K at once, so a stopped step below the new K resumes and a step at or above it stops. A saved change in the conversation replaces an earlier session choice and re-resolves from the saved values.
- **Cost bounds.** Because a fix after REFUTED or BROKEN is code-reviewed with a fresh count while verification's and Adversarial review's counts run across fixes, the bounds are K(K+1) per Claim and K³ + K² + K per Security-critical claim, not linear in K; the user kept the range 2–10 knowing this.
- **Command.** A new user-invoked skill mirrors the `auto-on` and `auto-off` toggle procedure for scopes, reminders and authorisation.
- **Not affected.** The pre-approval security analysis, Explicit request rules, the Acceptance gate, handoff records and the handoff runtime, role definitions and their tools.

## Testing Decisions

- One seam: the existing configuration tool test module, which runs the tool through its command line and reads its JSON output, as the existing `--review-mode` tests do. Tests check external behaviour: results, `show` output, the bytes of state and guidance files, and refusals that leave files unchanged.
- The procedures, skills, READMEs, setup document and ADRs are model instructions without an executable seam. Following the project's existing practice, tests in the same module pin each new rule as a whole sentence in the document and section that states it, README rules paired in both languages, and assert that retired fixed-number wording is gone, like the existing tests for wording retired in 0.16.0 and the shipped-wording scan.
- Prior art: the `--review-mode` lifecycle and rollback tests, the guidance byte-equality tests, the role-template compatibility data for older versions, the `*_wording_from_0_16_0_is_gone` tests and the shipped-files scan.

## Out of Scope

- Per-step Stop thresholds, or different values for Security-critical claims.
- Values below 2, above 10 or unlimited.
- Carrying a session choice across sessions or recording it in a handoff.
- Hook-enforced counting; the limit stays an agent instruction.
- Setting the Stop threshold through `install`, `session` export or `/cc-feather:model`.
- Changing any other counting rule of ADR 0002 or ADR 0004, the Acceptance gate, or how Claims are cut.

## Further Notes

- `CONTEXT.md` defines **Stop threshold** and redefines **Unreviewed claim** in terms of it; that glossary change was made during the grilling and is committed with this spec.
- Automatic plan review is on, so this spec gets plan review before implementation once the user agrees to it.
- The handoff `.feather/handoffs/configurable-review-budget.md` records the grilling decisions Q1–Q13.
