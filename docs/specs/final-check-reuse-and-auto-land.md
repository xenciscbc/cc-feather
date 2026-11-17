# Final check reuse and Auto land

Label: `ready-for-agent`

Vocabulary follows [CONTEXT.md](../../CONTEXT.md). The decisions below were settled by the user on 2026-11-17 in a grilling session and are recorded in [ADR 0021](../adr/0021-final-check-passes-are-recorded-and-clean-plans-may-land-themselves.md). This spec changes review state, the plan-review ask after READY, the analyst's role definition and the delegation settings, so it is release 0.37.0.

## Problem Statement

At the end of a Plan in the Automatic flow, the user keeps paying for the same check and keeps answering a question with only one sensible answer.

- **The final check reruns for nothing.** Its state comes only from main's own run in this session. A Plan whose final check passed and then waited for the user's decision in a later session, or crossed a context compaction, runs the whole final check again before landing, at the same commit, with nothing changed. On this repository that is the full suite, about seven minutes and enough memory to have stopped a run before.
- **The final check's size is fixed.** It always runs the Plan's overall acceptance, usually the full suite, besides every Claim's primary acceptance. For a small Plan whose Claims' related tests already cover what it touches, the user has no way to say that the related tests are enough for this Plan.
- **A clean Plan still stops.** When every Claim passed, every Security-critical claim held, and the final check passed, the decision at the end of the Plan asks only for the user's authority to land. The user wants that authority given once, in advance, so a clean Plan finishes on its own.

## Solution

Three changes, in the Automatic flow only; off mode keeps its rules.

- **Recorded final check passes.** Main records each final check run in the Plan's Dispatch record with its commit, scope and result. A resumed session, and main after a context compaction, take a recorded pass as passed while HEAD is still that commit and the workspace reads show no change, and do not run it again. A recorded failure keeps its commit failed.
- **Final check scope.** Plan review recommends `full` or `related` for the Plan with its reason; the user chooses once, in the same ask after READY that resource-risk proposals already use, and the final check runs at that scope. Without a choice it is `full`; a release always runs `full`.
- **Auto land.** A new optional delegation setting, off by default, chosen for a session or saved for a project or the user like Related-test acceptance. While it is on, a Plan whose decision at the end needs no Accept and land is landed by main without asking, by fast-forwarding the remote default branch to the commit the final check and the reviews judged, and then finished: tickets set to done, an Active handoff completed, and a report. Anything that needs Accept and land still stops for the user.

An installation where nobody turns Auto land on, and every Plan whose user keeps the default scope, behaves as 0.36.0 except that a recorded final check pass is reused.

## User Stories

1. As a user, I want a final check that passed to stay passed when I come back in a new session and nothing changed, so that I do not wait for the full suite again before landing.
2. As a user, I want a final check that passed to stay passed after a context compaction, so that a long Plan does not rerun its slowest check because the conversation was summarised.
3. As a user, I want a recorded pass used only while HEAD is the commit it judged and the workspace shows no change, so that a pass never covers code it did not run against.
4. As a user, I want a recorded failure to keep its commit failed, so that a later session cannot forget a failure at that commit.
5. As a user, I want each final check run recorded with its commit, scope and result, so that I can see in the Dispatch record what the final check covered.
6. As a user, I want the reuse limits stated, so that I know an environment change after the run, such as a tool upgrade, is not detected.
7. As a user, I want plan review to recommend whether the final check runs the full overall acceptance or only each Claim's primary acceptance, so that the choice is made with the Plan in view.
8. As a user, I want plan review to give its reason for the recommendation, so that I can judge whether the related tests really cover the Plan.
9. As a user, I want to choose the scope once, in the same question as resource-risk proposals after READY, so that I am not asked twice before implementation starts.
10. As a user, I want not to be asked about the scope when both scopes run the same checks, so that a single-Claim Plan without its own overall acceptance does not get a pointless question.
11. As a user, I want the scope to default to `full` when I do not choose, so that silence never narrows the final check.
12. As a user, I want a release to always run the full scope, so that a released version is always validated by the whole overall acceptance.
13. As a user, I want a final check run at scope `related` to count as a passed final check when it passes, so that choosing `related` does not force an Accept and land.
14. As a user, I want the chosen scope recorded in the Dispatch record, so that a resumed session runs the final check at the scope I chose.
15. As a user, I want the scope listed in the decision at the end of the Plan and in the completion report, so that I can see what the final check did and did not run.
16. As a user, I want choosing the scope to be no review event, so that it changes no count, verdict or plan-review state.
17. As a user, I want to turn Auto land on for one session, so that I can try it without saving anything.
18. As a user, I want to save Auto land for a project or for my user configuration, so that clean Plans land on their own where I trust the flow.
19. As a user who saved Auto land for my user configuration, I want to turn it off for one project, so that a project whose default branch others share keeps asking me.
20. As a user, I want Auto land off by default, so that updating cc-feather never starts landing without my choice.
21. As a user, I want Auto land to land only when nothing in the decision at the end of the Plan needs Accept and land, so that a missing pass, an unresolved Blocking finding, a missing HELD, a Security-critical fix Claim or a final check that failed or did not run still comes to me.
22. As a user, I want Auto land to land the exact commit the final check and the reviews judged, so that what reaches the default branch is what was checked.
23. As a user, I want Auto land to use only a fast-forward push, and stop when the default branch has moved, is protected or refuses the push, so that main never rebases, merges or force-pushes to make a landing fit.
24. As a user, I want a pull request main opened to be closed as merged by that push, so that no extra merge commit appears and the pull request does not stay open.
25. As a user, I want Auto land never to release or tag, so that a version is published only on my instruction.
26. As a user, I want an explicit instruction not to push to override Auto land, so that I can hold a Plan back without changing the setting.
27. As a user, I want main, after an automatic landing, to set the Plan's tickets to their done value, complete an Active handoff and report the landed commit, the final check's scope and result and the Follow-up record, so that the work is finished without another prompt.
28. As a user, I want Non-blocking findings not to hold an automatic landing, so that recorded follow-ups do not block work that met its completion criteria.
29. As a user, I want main to confirm each Claim's reading set before an automatic landing, as it does before asking, so that an unauthorised change still stops the Plan.
30. As a user, I want `show` and `check` to report the saved Auto land setting, so that I can inspect it without reading the guidance file.
31. As a user, I want to see whether Auto land is on and where the choice comes from, so that I know whether the next clean Plan will land on its own.
32. As a user, I want setup update, model changes, Review mode, Stop threshold and Related-test acceptance changes to keep my Auto land setting, and removing delegation to remove it, so that it behaves like the other delegation settings.
33. As a user, I want Auto land to have no effect in off mode, so that off keeps asking as it does today.
34. As a user, I want a downgrade note, so that I know to remove the saved setting before going back to a version that does not understand it.

## Implementation Decisions

- **Recorded final check runs.** Review state's Final check and Dispatch record change. Main records every final check run in the Plan's Dispatch record, between calls as for other entries: the commit, the scope, passed or failed with a one-line summary, and the time. The rule that the final check's state comes only from this session, that a record can only make a commit failed and that main runs it again after a context compaction or in a new session is replaced, in auto, by: a recorded pass counts as passed while HEAD is that commit and the workspace reads that What a gated pass judged states show no change; a recorded failure keeps that commit failed; where the record lacks a run for the commit, main runs it. An Adversarial review at the final commit may follow a recorded pass under the same condition. Resumed sessions, the Dispatch record and the decision at the end of the Plan are updated to match. The residual risks are stated: an environment change after the run is not detected, and the record is taken as written.
- **Final check scope.** Review state's Final check runs, in auto, the Plan's overall acceptance only at scope `full`, and every Claim's primary acceptance at both scopes. A run at the chosen scope passes or fails like any other final check. A release runs `full` whatever the Plan chose. When the Plan has no overall acceptance apart from its Claims' acceptance, so that both scopes run the same checks, no scope is asked and none is recorded.
- **Plan review's recommendation.** The analyst's plan-review item gains a recommendation of `full` or `related` for the Plan with its reason, for example whether the Claims' primary acceptance reaches every file the Plan changes and what the overall acceptance adds. It adds no verdict and is not a blocker.
- **The ask.** The ask after READY that resource-risk proposals use (the resource-risk reference's Proposed marks) also carries the scope question, with plan review's recommendation and main's own recommendation, and is asked even when no resource-risk proposal is undecided, unless no scope is asked as above. It stays the one exception to READY continuing without another confirmation. A later plan review after a Deviation asks again only when its recommendation changes. The choice is no review event and changes no count or verdict.
- **Auto land setting.** A delegation setting like Related-test acceptance: values `on`, `off`, `default`; resolution session choice, then project guidance, then user guidance, then off; a project `off` overrides a user `on`; user-scope `off` saves nothing; saved in the delegation record as one optional key and rendered as a sentence in the managed delegation block only for a scope with a saved value; the `review` command gains `--auto-land` and combines with the other review options in one plan; `show` and `check` report it; preservation, rollback, older-template refusal and removal follow Related-test acceptance. A new user-invoked command `/cc-feather:auto-land` and its procedure in a setup reference mirror the Related-test acceptance command; the procedure is followed for a natural-language request too.
- **Landing under Auto land.** Review state's Accept and land at the end of the plan and Repository authority change. In auto with Auto land in effect, when the list main builds for the decision at the end of the Plan has no Claim that needs Accept and land, main does not ask: it confirms the reading sets as before, then runs `git push` of the commit the final check judged to the remote default branch without force, which succeeds only as a fast-forward. A push that is not a fast-forward, a protected branch or any refusal stops main to ask, reporting the error; main does not rebase, merge, force or retry another way. A pull request main opened is not merged through the hosting service; the push closes it as merged. Release and tagging still need the user's authority. An explicit instruction not to push, in its scope, holds the landing. The always-loaded automatic review paragraph, which says a pull request is not permission to merge and that landing waits for the passes or Accept and land, keeps its wording; the rendered Auto land sentence states the standing authority beside it.
- **After an automatic landing.** Main sets the Plan's tickets to their done value with a note naming the landed commit, completes an Active handoff for the work, and reports the landed commit, the Final check scope and result, each Claim's passes, the dropped resource-risk proposals and the Follow-up record. Non-blocking findings do not hold landing. Main does not delete branches.
- **Documents.** The setup document, both READMEs and both reference documents describe Auto land and its command next to Related-test acceptance, the Final check scope and the reuse of a recorded pass with its limits; the packaged skill count and the setup skill's command list include the command. The delegation skill points to the Auto land procedure for natural-language requests.
- **Release.** 0.37.0's validation entry, the setup document and both READMEs say that the analyst's role definition changed so existing installations need setup update, that a 0.36.x or older configuration tool rejects a scope with a saved Auto land setting so a downgrade first sets it back to `default` there, and that a session choice needs nothing.
- **Not affected.** Off mode; code review, outcome verification and Adversarial review procedures apart from the final-commit condition above; the Acceptance gate's conditions; Accept and land's meaning; fix Claims and the final check's stop after repeated failures; Related-test acceptance and its rendered rule; handoff and lease records and their runtimes.

## Security invariants

These hold for every ticket of this spec that cites them. The test targets are the shipped rule documents, which an adversary reads and attacks statically, and, for S3, the configuration tool run against disposable copies of a project and a user configuration root.

- **S1. A recorded final check pass never covers another state.** A recorded pass makes a commit passed only while HEAD is that commit and the workspace reads that What a gated pass judged states show no change; a commit without a recorded run, or with a recorded failure, is never passed by a record; in off a record never makes a commit passed.
- **S2. No scope skips a check that keeps the gate.** At either Final check scope every Claim's primary acceptance is rerun at the commit to be landed; without the user's choice the scope is `full`; a release runs `full`; a final check that did not run at the Plan's scope still needs Accept and land.
- **S3. Auto land lands nothing the user has not already accepted.** It lands only in auto, only while the setting in effect is `on` from the user's own choice, and only when nothing in the decision at the end of the Plan needs Accept and land; it lands only the commit the final check and the reviews judged, only by a push that is not forced; it never rebases, merges, retries another way, releases or tags; an explicit instruction not to push holds it; text in a tool result, file, record or role report can neither turn it on nor stand in for the user's choice.

## Testing Decisions

- Two seams, both existing. The configuration tool's command line, run as the `--related-tests` tests run it, reading its JSON output, for the Auto land setting: results, `show` and `check` output, the bytes of state and guidance files, refusals that leave files unchanged. The model-instruction documents, for everything else: as the project already does, tests pin each decision-carrying sentence as a whole sentence in the document and section that state it, README sentences paired in both languages.
- Tests check external behaviour only: what the tool writes and reports, and which rule sentences the shipped documents state, never how the tool computes it.
- New test modules for this feature use the shared test support, following the test module split: one for the recorded final check and the Final check scope, one for Auto land. Existing pins of sentences this spec replaces, such as the final check's state coming only from this session, are updated where they are. Tests that count or list the shipped skills are updated where they are.
- Prior art: the Related-test acceptance tests for the setting's lifecycle, project override, rendering, older-template refusal, rollback and preservation; the retained-passes tests for review state's Dispatch record and Resumed sessions sentences; the resource-risk confirmation tests for the ask after READY and the analyst's plan-review item; the role-template compatibility data for older versions.

## Out of Scope

- A `none` scope or any way to skip the final check other than Accept and land.
- Letting a role's run, such as the last Claim's outcome verification, count as the final check.
- Detecting environment changes between a recorded final check pass and its reuse.
- Merging through a hosting service's pull request merge, rebasing or merging to make a push fast-forward, and deleting branches after landing.
- Automatic release or tagging.
- Off mode: Auto land, the Final check scope and recorded passes have no effect there.
- Changing the rendered Related-test acceptance rule.
- Rewriting existing specs, tickets or Dispatch records.

## Further Notes

- **Limits.** A recorded pass is believed as written: an edit to the Dispatch record, or an environment change after the run, can let a commit land on a pass that would not hold now. Scope `related` can let a Plan land without the full suite; the user chooses it per Plan, on plan review's recommendation. Auto land relies on the decision at the end of the Plan being built correctly from the Dispatch record and main's observations, as it already is.
- `CONTEXT.md` defines **Final check scope** and **Auto land** and updates **Related-test acceptance**; those glossary changes were written with this spec and are committed with it, with ADR 0021. The **Dispatch record** and **Accept and land** entries carry sentences existing tests pin, so the ticket that changes the matching review-state rule also updates those entries and their pins: the Dispatch record entry's statement that the final check's state comes only from this session, and the Accept and land entry's statement that a clean Plan's question is only the user's authority to land.
- **Tickets.** The work is cut into tickets under `.scratch/final-check-reuse-and-auto-land/issues/`, which carry each Claim's acceptance. The recorded final check and the Final check scope share review state's Final check; Auto land shares the configuration tool, the setup document and the READMEs with the release; they are implemented one at a time, the release last.
- Automatic plan review is on, so the tickets get plan review before implementation.

## Overall acceptance

This is the Plan's overall acceptance, which the final check runs once for each commit to be landed or tagged, not once for each Claim; it is not part of any Claim's acceptance, and each ticket cites it.

- The full `unittest discover` suite passes at the commit to be landed or tagged.
