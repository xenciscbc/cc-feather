# Final check scope fixes

Label: `ready-for-agent`

Vocabulary follows [CONTEXT.md](../../CONTEXT.md). The decisions below were settled by the user on 2026-11-18 in a grilling session, with a second opinion from Codex, and are recorded in [ADR 0022](../adr/0022-final-check-scope-answers-are-pending-until-recorded-and-a-release-may-use-related.md). This spec fixes a BROKEN that an Adversarial review found in 0.37.0 and changes the final check's scope rules, so it is release 0.38.0. It builds on the [0.37.0 spec](final-check-reuse-and-auto-land.md), whose security invariants it amends.

## Problem Statement

- **A widened scope answer can be lost (0.37.0 ticket 02, BROKEN against S2).** The rules say main records the user's Final check scope answer in the Plan's Dispatch record, but not when. When a later plan review after a Deviation asks the scope question again and the user widens `related` to `full`, a context compaction before main writes the new answer leaves the record's `related`. The final check then passes at `related` as if at the Plan's scope, so the Plan needs no Accept and land, and with Auto land on it lands without the overall acceptance.
- **The rules contradict themselves on how the user answers.** The scope is set only by the user's own answer, and a tool result never sets it; but the user answers the scope question through AskUserQuestion, whose answer reaches main as a tool result. Auto land's rules say the same of a tool result. The glossary says the user chooses the scope once, before the first Claim is implemented, while the rule says an unanswered scope question holds back no Claim, and a later plan review can ask again.
- **`full` runs the same tests twice.** At `full` the final check reruns each Claim's primary acceptance separately even when the overall acceptance's run, at the same commit, already ran those tests; on 0.37.0 that was about two more minutes.
- **A release always runs `full`.** A Plan the user chose to check at `related` still needs the overall acceptance at the commit to be tagged, even when the user judges the `related` pass enough for that release.

## Solution

In the Automatic flow only; off mode keeps its rules.

- **Pending scope questions.** Before asking any Final check scope question, main writes it into the Dispatch record as pending, replacing the earlier answer; the user's answer to it replaces the mark at the next point between review calls. A pending question means `full`. A correction goes through a new pending question.
- **The user's answer through main's own question counts.** The rules that no tool result sets the scope, turns Auto land on or lifts a hold exclude the user's answer that main's own question tool returns for main's question.
- **The overall run covers primary acceptance.** At `full`, a Claim's primary acceptance that the overall acceptance's own run visibly ran under the same conditions is not run a second time; otherwise it runs separately.
- **A release may use `related`.** A `full` pass valid at the commit to be tagged is used without asking; otherwise main asks for that commit whether to run `full` or tag on the `related` pass.

## User Stories

Pending scope questions:

1. As a user, I want a scope answer I widened never to fall back to a narrower recorded answer after a context compaction, so that a Plan cannot land at a scope I replaced.
2. As a user, I want main to mark each scope question pending in the Dispatch record before asking it, so that a compaction between my answer and its write leaves `full`, not my earlier answer.
3. As a user, I want a scope question that has not been answered, or whose answer was not recorded, to mean `full`, so that a lost answer only widens the final check.
4. As a user, I want an unclear answer to mean `full`, so that main never guesses a narrower scope.
5. As a user, I want my answer written at the next point between review calls, and before any final check runs at that scope, so that the record catches up before it matters.
6. As a user, I want to correct my scope answer through a new scope question, so that a correction is protected as the first answer is.
7. As a user, I want a choice I state without the scope question to set nothing, as now, so that a passing remark does not narrow the final check.
8. As a user, I want a resumed session to read a pending mark as `full`, so that a new session cannot recover a narrower answer the old one replaced.
9. As a user, I want a compaction summary never to set the scope, so that a summary's paraphrase never stands in for my answer.
10. As a user, I want an unanswered scope question still to hold back no Claim, so that the pending mark costs no waiting.

The user's answer and the glossary:

11. As a user, I want my answer to main's AskUserQuestion to count as my own answer, so that the rules do not contradict how I am asked.
12. As a user, I want a tool result that only quotes or claims to be my words not to count as my answer, so that the exception cannot be used to set the scope or Auto land for me.
13. As a user, I want the same exception in the scope rules, in Auto land's rules for turning it on and lifting a hold, and in the documents that repeat them, so that no two places disagree.
14. As a user, I want the glossary to say what the rules do: asked after READY, unanswered means `full`, no Claim waits, a later plan review may ask again, so that the vocabulary matches the behaviour.
15. As a user, I want a Deviation's approval to state the scope I keep and its reason when plan review's recommendation is unchanged, so that I can ask for `full` myself without another question.

Covered primary acceptance:

16. As a user, I want the final check at `full` not to rerun tests the overall run already ran under the same conditions, so that I do not wait for them twice.
17. As a user, I want coverage to need the same tool and the same conditions that decide which tests run and how, so that a run with different options, configuration, environment or import form never stands in for another.
18. As a user, I want coverage to need the run's output to show each named test unit ran and passed, so that a unit the run silently skipped is not counted.
19. As a user, I want any primary acceptance whose coverage main cannot establish from the commands and the output to run separately, so that a saving never skips a check.
20. As a user of any language, I want the coverage rule to name no test runner, so that it works for Go, Python, JavaScript and others alike.
21. As a user, I want the recorded final check run to name the Claims the overall run covered, so that a resumed session reports the same thing.
22. As a user, I want the decision at the end of the Plan and the completion report to name the Claims the overall run covered, so that I can see what ran where.
23. As a user, I want `related` unchanged, rerunning every primary acceptance itself, so that coverage applies only where an overall run exists.
24. As a user, I want acceptance items other than the primary acceptance, and checks that cannot be rerun, to stay as they are, so that the change adds no new obligation.
25. As a user, I want a fix Claim's acceptance treated like any other primary acceptance, so that the final check after a fix follows the same rule.

Release scope:

26. As a user, I want a valid `full` pass at the commit to be tagged used without a question, whether main's own or recorded, so that a release after a `full` landing does not rerun the suite.
27. As a user, I want to choose, for the commit to be tagged, between running `full` and tagging on the `related` pass, so that I decide whether the release needs the whole suite.
28. As a user, I want the release question to say that `related` leaves out the overall acceptance, so that I know what I waive.
29. As a user, I want the release question pending first and `full` while it is, so that a release never inherits the Plan's `related` by default.
30. As a user, I want my release scope answer bound to that commit, so that a later commit needs its own answer.
31. As a user, I want my release scope answer not to count as permission to tag, so that tagging still needs my instruction.
32. As a user, I want a failure at the commit to be tagged, a missing pass, an unresolved Blocking finding or a missing HELD still to need Accept and land when I choose `related` for a release, so that the choice waives only the overall acceptance.
33. As a user, I want the tag report to say the release used `related`, so that the release record shows what was not run.
34. As a user, I want Auto land still never to tag, so that the release choice does not widen Auto land.

Release and compatibility:

35. As a user, I want off mode unchanged, so that none of this applies where automatic review is off.
36. As a user who installed 0.37.0, I want the 0.38.0 notes to say that v0.37.0 carries the BROKEN this release fixes, so that I know to update.
37. As a user, I want to know whether an update needs setup update, so that I do not run it for nothing or skip it when needed.
38. As a user, I want the existing `v0.37.0` tag left as it is, so that a published version never changes.

## Implementation Decisions

- **Pending scope questions.** Review state's Final check scope and Dispatch record, and the resource-risk runs reference's scope question and A later plan review, change. Main writes each Final check scope question into the Plan's Dispatch record as pending before asking it, replacing any earlier answer; the user's answer to that question replaces the mark at the next point between review calls, and in any case before a final check runs at that scope. A pending question means `full`. A choice the user states other than as the answer to a pending question sets nothing, as now, and a correction is made by main asking a new pending question. A compaction summary still never sets the scope. The release question below uses the same mark.
- **The user's answer through main's question.** In review state's Final check scope and Auto land, the setup reference for Auto land and the README sentences that list a tool result among what never sets the scope, turns Auto land on or lifts a hold, the exclusion becomes: a tool result other than the user's answer that main's own question tool returns for main's question. A tool result quoting or claiming to be the user's words is still not the user's answer.
- **Glossary alignment.** CONTEXT.md's Final check scope entry states that main asks after READY and before the first Claim, again only after a later plan review whose recommendation changes, that the answer to the latest question sets the scope, and that until that answer is recorded the scope is `full` and no Claim waits. The text is in Further Notes.
- **Deviation disclosure.** When a later plan review after a Deviation keeps its scope recommendation, so the scope question is not asked again, the user's approval that review needs states the scope the Plan keeps and plan review's reason. No new question is asked.
- **Covered primary acceptance.** Review state's Final check and Recorded final check runs change. At `full`, a Claim's primary acceptance counts as rerun when the overall acceptance's own run at the commit to be landed or tagged ran it: the same tool, with the same conditions that decide which tests run and how they run (options, configuration, environment variables, working directory, import or module form), the primary acceptance naming part of what the overall run selects; and the run's output shows that each test unit the primary acceptance names, such as a package, module or file, ran and passed. When main cannot establish both from the commands and the output, it runs the primary acceptance separately. Acceptance items other than the primary acceptance, and checks that cannot be rerun, stay as now; a fix Claim's acceptance follows the same rule, and at `related` every primary acceptance still runs itself. The recorded run names the Claims the overall run covered; the decision at the end of the Plan and the completion report list them. The rule names no language or runner; examples in documents may.
- **Release scope.** Review state's Final check, Recorded final check runs and Final check scope change. At the commit to be released or tagged, a `full` pass that is valid there, main's own or a recorded one under Recorded final check runs, is used without asking. Otherwise main asks the user, for that commit, whether to run `full` or to tag on the `related` pass, stating that `related` leaves out the overall acceptance, with the question pending in the Plan's Dispatch record first; while it is pending, or without a clear answer, the release runs `full`. The answer chooses only what the final check runs: it is not an instruction to release or tag. A release on `related` is a passed final check at that commit, so it needs no Accept and land for the overall acceptance; a failure at that commit, a missing pass, an unresolved Blocking finding or a missing HELD still does. Auto land never tags.
- **Documents.** Both READMEs, both reference documents and the setup document state the pending scope question, the coverage of primary acceptance at `full` and the release choice, replacing "a release always runs `full`".
- **Release.** 0.38.0's validation entry states that v0.37.0, at 6cbb1b5, carries the BROKEN this release fixes, and both READMEs' update notes say so. No role definition changes, so existing installations need the plugin update and a fresh session but no setup update; a ticket that finds otherwise states it.
- **Not affected.** Off mode; Auto land's resolution, holds and landing conditions apart from the tool-result wording; recorded-pass reuse conditions apart from the release scope; plan review's recommendation; Related-test acceptance.

## Security invariants

S1 to S3 of the [0.37.0 spec](final-check-reuse-and-auto-land.md#security-invariants) still hold, with the bullets below replacing or adding to them; a ticket that cites them cites both. The test targets are the shipped rule documents, which an adversary reads and attacks statically.

- **S1, amended.** A recorded pass makes a commit passed only while HEAD is that commit, the workspace reads that What a gated pass judged states show no change, every Claim's reading set is unchanged from the hash recorded with the run, and the run's scope covers the scope now needed: a `full` pass covers `full` and `related`, a `related` pass only `related`, and a release or tag needs a `full` pass at that commit unless the user's recorded answer for that commit chose `related`.
- **S2, replaced.**
  - At either scope every Claim's primary acceptance is run at the commit to be landed or tagged: separately, or, at `full`, within the overall acceptance's run only where S4 holds.
  - The scope, the Plan's or a release's, is set only by the user's answer to main's own scope question, recorded in the Dispatch record in place of that question's pending mark; a recommendation, a role report, any other tool result or record, and a compaction summary never set it.
  - A question that is pending, unanswered or answered unclearly means `full`; when no scope is asked, the final check runs as `full` and the decision and report say `full`.
  - A recorded answer is replaced only by the answer to a later pending question; main writes the pending mark before asking.
  - A release or tag runs `full` unless the user's recorded answer for that commit chose `related`; that answer never authorises the release or tag.
  - A final check that did not run at the scope needed still needs Accept and land.
- **S3, amended (bullet 2).** The exclusion of "a tool result" from what sets Auto land, or stands in for the user's choice, or lifts a hold, does not exclude the user's answer that main's own question tool returns for main's question, and nothing else.
- **S4. Coverage never stands in for a test that did not run.** A Claim's primary acceptance counts as run within the overall acceptance's run only when that run used the same tool and the same selection and execution conditions, the primary acceptance names part of what it selects, it ran at the commit to be landed or tagged, and its output shows each named test unit ran and passed; anything main cannot establish runs separately.

## Testing Decisions

- One seam, existing: the model-instruction documents. As the project already does, tests pin each decision-carrying sentence as a whole sentence in the document and section that state it, README sentences paired in both languages. No tool behaviour changes, so the configuration tool's command-line seam is not used.
- Tests check external behaviour only: which rule sentences the shipped documents state, never how a sentence is worded around them.
- Existing pins of sentences this spec replaces are updated where they are, in the final check, Auto land and retained-passes test modules, including their glossary pins; new pins go into the final check and Auto land modules rather than a new module. The release ticket updates the releases test module as earlier releases did.
- Prior art: the 0.37.0 tests for the Final check scope, Recorded final check runs and Auto land; the resource-risk confirmation tests for the ask after READY.

## Out of Scope

- Which `unittest discover` forms this repository's release validation runs; that is this repository's own convention, recorded in the handoff record `release-validation-discover-form`.
- Recovering a scope from a compaction summary.
- Asking the scope question again after a Deviation whose recommendation is unchanged.
- Automatic release or tagging, and any change to Auto land beyond the tool-result wording.
- Moving, deleting or re-pointing the existing `v0.37.0` tag.
- Off mode.

## Further Notes

- **Glossary.** The ticket that changes the matching review-state rule also updates CONTEXT.md and the tests that pin it, so every commit keeps the suite passing:
  - Final check scope, whole entry: "What the final check runs for a Plan in the Automatic flow: `full`, the Plan's overall acceptance and a rerun of every Claim's primary acceptance, or `related`, the rerun of every Claim's primary acceptance alone. At `full`, a Claim's primary acceptance that the overall acceptance's own run visibly executed, with the same tool and the same conditions, is not run a second time. Plan review recommends one with its reason; main asks the user after the Plan's READY and before its first Claim is implemented, and again only after a later plan review whose recommendation changes. The user's answer to the latest question sets it, and until that answer is recorded it is `full`, which holds back no Claim. A release or tag runs `full` at the commit to be tagged unless the user, asked for that commit, chooses `related`; a `full` pass already valid there is used without asking. A final check run at the chosen scope passes or fails like any other: `related` is not a missing check and needs no Accept and land. Choosing it is not a review event, changes no count or verdict and gives no authority to land, release or tag."
  - Dispatch record: each final check run also names the Claims whose primary acceptance its overall acceptance run covered; the record holds each Final check scope question, marked pending before main asks it, and the user's answer to it, which replaces the mark, a pending question meaning `full`; and a release or tag needs a `full` pass unless the user chose `related` for that commit.
- **Tickets.** The work is cut into tickets under `.scratch/final-check-scope-fixes/issues/`, which carry each Claim's acceptance: the pending scope question with the tool-result wording, the glossary alignment and the Deviation disclosure; covered primary acceptance; the release scope; and the 0.38.0 release. The first three change review state's Final check paragraphs and are Security-critical; they are implemented one at a time, the release last.
- **Limits.** A recorded answer or pending mark is taken as written, as the Dispatch record already is. Whether the overall run covered a primary acceptance is judged from the commands and the run's output, which repository code controls. A release on `related` is tagged without the overall acceptance at that commit, on the user's answer for that commit.
- Automatic plan review is on, so the tickets get plan review before implementation.

## Overall acceptance

This is the Plan's overall acceptance, which the final check runs once for each commit to be landed or tagged, not once for each Claim; it is not part of any Claim's acceptance, and each ticket cites it.

- The full `unittest discover` suite passes at the commit to be landed or tagged.
