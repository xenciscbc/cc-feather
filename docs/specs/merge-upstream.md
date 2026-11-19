# Merge upstream

Label: `ready-for-agent`

Vocabulary follows [CONTEXT.md](../../CONTEXT.md), which defines Plan, Claim, Dispatch record, Landing, Auto land, Accept and land, Acceptance gate, Final check scope and Checkout lease; this spec adds Upstream merge and Integration report.

## Problem Statement

Users increasingly run several Plans at once, each in its own Git worktree. When one Plan lands first, the remote default branch moves while another Plan is still under review or waiting at the end of its Plan. That Plan can no longer land as a fast-forward: Auto land stops, and a manual landing would carry a commit no review judged.

Today the user has to work out by hand what the new upstream changes mean for the waiting Plan: which of its Claims touch the same files, whether a conflict resolution changed a reviewed Claim, which passes still hold, which reviews have to run again, whether the final check must rerun and which Security-critical Claims lose their HELD. The rules say how passes reopen, but they say it per Claim and in prose spread across review state, and nothing gathers the facts. Getting it wrong either lands upstream interactions nobody reviewed, or reruns every review of the Plan when only a few were affected.

Merging also has traps of its own: main must not rewrite pushed history, a merge commit is unjudged and fails Auto land's range check, and a merge pushed too early can no longer be thrown away and redone when its conflict resolution turns out wrong.

## Solution

cc-feather gains a user-invoked skill, `merge-upstream`, for a Plan in the automatic flow whose remote default branch moved. With the user's agreement, main fetches and merges the remote default branch into the Plan's work branch, locally and without pushing. A read-only tool reports the facts of that Upstream merge: what upstream changed, what the merge result changed, and where each Claim's files meet either. From those facts main writes an Integration report: for each Claim, whether its passes reopen or stay with the reason, which Adversarial reviews rerun, and the final check.

The Integration report is separate from the Plan: the Plan's text, its tickets and its Claims stay as they are, and no ticket or Claim is added. It gets plan review, and the user approves it. Main then reruns the reopened reviews under the original Claims, recorded in the Plan's own Dispatch record, runs the final check at the merge commit and the Adversarial reviews the report names. Only when everything passes does main push, and only on the user's command: a Plan that went through an Upstream merge never lands under Auto land.

When Auto land stops because the remote default branch moved, its report suggests `merge-upstream`. The skill never runs on its own.

## User Stories

1. As a user running Plans in parallel worktrees, I want one command that brings the remote default branch into a waiting Plan, so that I do not have to work out the integration by hand each time.
2. As a user, I want the skill to run only when I invoke it, so that no integration happens without my decision.
3. As a user, I want Auto land's stop report to suggest the skill when the remote default branch moved, so that I know what to do next.
4. As a user, I want main to ask before it fetches and merges, so that I can choose to wait or land another Plan first.
5. As a user, I want the skill to tell me when the remote default branch has not moved, so that I do not run an integration that is not needed.
6. As a user, I want the merge done only in the local checkout and not pushed, so that it can be thrown away and redone if its review finds a problem.
7. As a user, I want the skill to merge and never rebase, so that the reviewed commits and their recorded identities stay valid.
8. As a user, I want main never to force-push or rewrite history that is already on a remote, so that nobody else's view of the branch changes under them.
9. As a user, I want the skill to check whether the merge commit already reached a remote before main discards or redoes it, so that a push I made myself is never rewritten.
10. As a user, I want main to resolve merge conflicts and the report to name every resolved path, so that I can see where main's own judgement entered.
11. As a user, I want a conflict resolution in a Claim's files to reopen that Claim's reviews, so that main's resolution gets reviewed like any other change.
12. As a user, I want the report to list what upstream changed, including deletions, both sides of renames, mode and type changes and submodules, so that no change is hidden by how Git shows it.
13. As a user, I want the report to list what the merge result changed against the Plan's tip before the merge, so that conflict resolutions and silent interactions are visible, not only upstream's own diff.
14. As a user, I want each Claim's overlap with upstream and with the merge result listed, so that I see which Claims are candidates to reopen.
15. As a user, I want changes to tests, fixtures, runner configuration and build configuration marked separately, so that a change to how acceptance is checked is never read as unrelated.
16. As a user, I want upstream changes to a spec or ticket a Claim's reading set cites called out, so that new upstream text never becomes a Claim's acceptance without my decision.
17. As a user, I want every Claim the report keeps to carry a reason, so that "unaffected" is a stated judgement, not an absence of overlap.
18. As a user, I want file overlap treated only as a candidate, with dependencies, fixtures, reading sets and environment judged by main, so that a Claim is not kept just because its files were not touched.
19. As a user, I want the Integration report reviewed by plan review before anything is reviewed again, so that the judgement of which Claims are unaffected gets an independent check.
20. As a user, I want to approve the Integration report after plan review, so that the scope of re-review is my decision.
21. As a user, I want the approval step to say that pushing waits until all reviews pass and that I can ask for an earlier push, so that I know the default and how to change it without an extra question.
22. As a user, I want reopened reviews to run under the original Claims and be recorded in the Plan's own Dispatch record, so that one record shows the Plan's whole review history.
23. As a user, I want the Integration report kept apart from the Plan's text and tickets, so that the Plan I agreed to is not rewritten and no ticket is added.
24. As a user, I want regressions in the re-review judged against each Claim's original base revision, so that a defect the Plan introduced is never treated as pre-existing because upstream moved.
25. As a user, I want reopened review calls to continue their counts and stops, so that an integration never resets a Stop threshold.
26. As a user, I want the final check to rerun at the merge commit, every Claim's primary acceptance included, so that the commit to be landed is the one that was checked.
27. As a user, I want every Security-critical Claim awaiting landing to get Adversarial review at the new final commit, so that a HELD from an older commit never covers the merged one.
28. As a user, I want unresolved verdicts, open findings, a BROKEN's findings and recorded holds to stay with their Claims after the merge, so that an integration never clears them.
29. As a user, I want a cancelled Claim's commits on the branch reported, so that their disposition is decided before landing.
30. As a user, I want the skill to stop when part of the Plan already landed, and report which Claims are accepted, so that accepted work is not reopened and unaccepted work is not taken for landed.
31. As a user, I want the skill to refuse while another checkout holds a lease on the same branch or the branch is checked out elsewhere, so that two sessions never integrate one branch at once.
32. As a user, I want a second Upstream merge when the remote moves again during re-review, recorded after the first, so that each integration stays traceable.
33. As a user, I want a Plan that went through an Upstream merge to land only on my command or my Accept and land decision, so that Auto land never pushes a merge it was not designed to judge.
34. As a user, I want the end-of-Plan decision to list every Claim on the branch with its state after the integration, so that landing the branch lands nothing I did not see.
35. As a user, I want the handoff updated when the skill stops to wait for me, so that a fresh session can resume the integration.
36. As a user, I want the skill to take the Checkout lease before it merges and renew it at its milestones, so that other sessions see the checkout is in use.
37. As a user, I want the tool to be read-only and never fetch, merge, push or change files, so that every change to the repository is main's, under the rules I already know.
38. As a user, I want the tool to report facts and leave every pass judgement to main and plan review, so that a mechanical overlap never decides acceptance.
39. As a user in off mode, I want the skill to report that it needs the automatic flow, so that it does not invent review state off mode does not keep.
40. As a user, I want the skill to report and stop on a dirty workspace, a detached HEAD or an unknown default branch, so that it never merges into a state it cannot describe.

## Implementation Decisions

- **The skill.** A new user-invocable skill `merge-upstream`, not invoked by the model on its own. It applies to one Plan in the automatic flow, named by the user or the sole Plan whose Dispatch record shows it waiting; otherwise main asks which. In off mode it reports that it needs the automatic flow and stops.
- **Preconditions.** Main stops and reports when the workspace is not clean, HEAD is detached, the default branch cannot be resolved as Commit and completion resolves it, the work branch is checked out in another checkout or another checkout's lease names it, or the Plan's Dispatch record cannot be read. When part of the Plan's commits already reached the remote default branch, main reports which Claims are accepted and which are not and stops for the user.
- **Fetch and merge.** After the user agrees, main takes or renews the Checkout lease, fetches the remote, and when the remote default branch is an ancestor of the work branch reports that nothing needs integrating. Otherwise it merges the remote default branch into the work branch with an ordinary non-fast-forward merge, resolving any conflicts itself, and commits the merge locally. It never rebases, forces, or pushes in this step. The merge's authority is the user's agreement for this Plan's integration only.
- **Discarding a merge.** Main may throw away and redo its own unpushed merge, for example after plan review finds a wrong resolution, only after the tool shows that the merge commit is on no remote-tracking ref after a fresh fetch. A merge commit that reached a remote is fixed with new commits, as Commits before the passes requires.
- **The tool.** A new read-only command-line tool beside the leases tool, reusing the handoff tool's Git discovery and path checks. It reads one JSON object on stdin and prints one JSON object. Input: the remote and default branch, the remote tip, the work branch's tip before the merge, the merge commit, and each Claim's identifier, base revision and judged commits as main reads them from the Dispatch record. Output: the merge base; upstream's changed paths from the merge base to the remote tip and the merge result's changed paths from the tip before the merge to the merge commit, each with status, both rename sides, mode and type changes and submodules, read without external diff or text conversion; the paths whose merge needed resolution; for each Claim, its own changed paths and their overlap with each of the two lists; paths classed as test support or build configuration; and whether the merge commit is on any remote-tracking ref. It never fetches, merges, pushes, writes refs, the index or the working tree. Unknown parts are reported as unknown with the reason, never as empty.
- **Integration report.** Main writes it in the Plan's Dispatch record as an Upstream merge entry: the remote tip, the tip before the merge, the merge commit, the tool's facts or where they are kept, and for each Claim either "reopens code review and outcome verification", "reopens outcome verification only" or "passes stay" with main's reason, judged as What a pass covers states; the Adversarial reviews to rerun; the final check at the merge commit at the Plan's Final check scope; and any upstream change to a Claim's reading set, which main reports as a material deviation for the user to decide, never adopts. It changes no Plan text, ticket or Claim.
- **Plan review of the report.** The report gets plan review under the plan-review procedure: the brief carries the report, the Plan, the tool's facts and the Claims' recorded passes; the analyst checks each kept pass's reason and each reopened scope. Calls count as plan review calls of the Plan. After READY main asks the user to approve the report; the ask states that pushing waits until every pass the report requires is in, and that the user may ask for an earlier push.
- **Re-review.** Reopened reviews are calls of the original Claims, continuing their counts as Reopened calls describes. Their briefs diff each Claim from its original base revision to the merge commit and name the report's reason for reopening. Regressions are judged against the Claim's original base revision. Unresolved verdicts, open findings, a BROKEN's findings and recorded holds stay with their Claims. A Claim kept by an approved report keeps its passes for the merge commit.
- **Final check and Adversarial review.** The final check runs at the merge commit as Final check describes; a recorded run at an earlier commit does not cover it. Every Security-critical Claim awaiting landing, other than a fix Claim, gets Adversarial review at the merge commit after that final check passes, whatever the report says about its files.
- **Landing.** A Plan whose Dispatch record holds an Upstream merge lands only on the user's own command or Accept and land, never under Auto land. The end-of-Plan list covers every Claim on the branch with its state after the integration. Main pushes nothing for the integration before every pass the report requires is in, unless the user asks for an earlier push to the branch main created.
- **Auto land's stop.** When Auto land stops because the remote default branch is not an ancestor of the judged commit, main's report suggests `merge-upstream` and does nothing else.
- **Repeated movement.** When the remote moves again before landing, a new invocation records a second Upstream merge after the first; the first one's re-review results stay with the commits they judged.
- **Handoff and lease.** Before stopping to wait for the user (agreement to merge, approval of the report, landing), main updates an Active handoff and renews its Checkout lease. The skill writes no handoff record of its own.
- **Documents.** The delegation skill and review state describe the Upstream merge where they describe What a pass covers, Auto land and the Dispatch record; both READMEs, the setup document and the reference documents list the new skill; the packaged skill count is updated.
- **Not affected.** Off mode; plan review, code review, outcome verification and Adversarial review procedures apart from the briefs above; the Acceptance gate's conditions; Auto land's checks for Plans without an Upstream merge; the handoff and lease tools' behaviour.

## Security invariants

These hold for every ticket of this spec that cites them. The test targets are the shipped rule documents, read and attacked statically, and, for S3, the tool run against disposable repositories created under a new subdirectory of `J:/gotmp/`, outside the project directory, and removed afterwards.

- **S1. An Upstream merge never makes a Claim accepted that the rules would reopen.**
  - A Claim's passes stay after the merge only when the Integration report keeps them with a reason, the report has a valid READY from plan review, and the user approved it; without all three every Claim whose files, dependencies or reading set the merge touched counts as reopened.
  - File overlap absent is never by itself the reason a pass stays.
  - Every Security-critical Claim awaiting landing needs a new Adversarial review result at the merge commit or Accept and land.
  - The final check at the merge commit is required; no earlier run covers it.
  - Regressions are judged against each Claim's original base revision.
  - Unresolved verdicts, open findings, a BROKEN's findings, recorded holds and cancelled Claims' commits stay as they were.
- **S2. An Upstream merge never lands or rewrites without the user.**
  - The merge happens only after the user's agreement for this Plan; the skill never runs on its own.
  - A Plan with an Upstream merge never lands under Auto land.
  - Main never rebases, forces or rewrites a commit that is on a remote; it discards its own merge only after a fresh fetch shows the merge commit on no remote-tracking ref.
  - Nothing of the integration is pushed before every pass the report requires is in, unless the user asks.
- **S3. The tool changes nothing.**
  - It never fetches, merges, pushes, or writes a ref, the index, the working tree or a record.
  - It reports a part it cannot establish as unknown with the reason, never as an empty list.

## Testing Decisions

- Two seams. The model-instruction documents, an existing seam: as the project already does, tests pin each decision-carrying sentence of the new skill and of the review-state changes, and the shipped skill lists and counts. The new tool's command line, a new seam at its only interface: tests build disposable repositories with a local bare remote, produce upstream movement, conflicts, renames, deletions, mode changes, submodules and an already-pushed merge, run the tool with a JSON input and check only its JSON output and that the repository's refs, index and working tree are unchanged.
- Tests check external behaviour only: what the tool reports and which rule sentences the shipped documents state, never how the tool computes it.
- New test modules use the shared test support, following the test module split: one for the tool, one for the rule documents. Tests that count or list the shipped skills are updated where they are.
- Prior art: the leases tool tests for a read-mostly Git tool over disposable worktrees and remotes; the handoff Git helper tests for Git discovery and path refusals; the Auto land tests for review-state sentences about landing and the range check; the retained-passes tests for What a pass covers and the Dispatch record.

## Out of Scope

- Rebasing, in any form, including a branch not yet pushed.
- Running the skill automatically, at the end of a Plan, on resume or after Auto land stops.
- Extending Auto land's range check to Plans with an Upstream merge.
- A separate integration Plan, or Claims or tickets added to the original Plan.
- Merging through a hosting service, or merging the work branch into the default branch.
- Integrating a branch other than the remote default branch, or several Plans at once.
- Off mode.
- Rewriting existing specs, tickets or Dispatch records.

## Further Notes

- **Why not a separate Plan.** Keeping passes fixed across a change is defined only for reviews of the same Plan, and Auto land's range check accepts only commits judged by the Plan being landed; a separate integration Plan would need both rules extended and every restriction of the original Plan inherited. Recording the re-review under the original Claims needs neither.
- **Limits.** The Integration report's kept passes rest on main's judgement and one plan review; a dependency neither sees can still land unreviewed, as today when main states why a change does not affect a pass. A push the user makes outside the session is outside these rules; the skill only detects it before discarding a merge.
- **Glossary.** `CONTEXT.md` gains **Upstream merge** and **Integration report**, written with this spec and committed with it.
- **Security analysis.** The rule ticket is Security-critical because it decides which passes stay valid at the Acceptance gate; in auto it gets a security analysis before plan review.
- **Tickets.** The work is cut into tickets under `.scratch/merge-upstream/issues/`, which carry each Claim's acceptance.
- Automatic plan review is on, so the tickets get plan review before implementation.

## Overall acceptance

This is the Plan's overall acceptance, which the final check runs once for each commit to be landed or tagged, not once for each Claim; it is not part of any Claim's acceptance, and each ticket cites it.

- The full `unittest discover` suite passes at the commit to be landed or tagged.
