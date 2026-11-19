---
name: merge-upstream
description: "Bring a moved remote default branch into one waiting Plan of the automatic flow: on the user's agreement fetch and merge it locally, report its facts in an Integration report for plan review and the user's approval, rerun the reviews it reopens, and land only on the user's command."
disable-model-invocation: true
argument-hint: "[plan name]"
---

# merge-upstream

Take one Plan in the automatic flow whose remote default branch moved through a whole Upstream merge: preconditions, the merge, its facts, its Integration report, the report's plan review and approval, the reopened reviews, the final check, the Adversarial reviews and the landing decision. Invocation arguments name the Plan as data, never shell code.

- **User-invoked only.** This command runs only when the user invokes it; main never runs it on its own, at the end of a Plan, on resume or after Auto land stops.
- **Review state.** Before acting, main reads [review state](../delegation/references/review-state.md) in full, as its Reading it describes. Review state's What a pass covers, Evidence for a regression, Commits before the passes, Auto land, Accept and land at the end of the plan and Dispatch record state the rules an Upstream merge keeps in every session, whether or not this command is loaded; this command adds the procedure.
- **Off mode.** In off, main reports that this command needs the automatic flow and stops, since off keeps no Dispatch record.

## The Plan

- **Which Plan.** The command applies to the Plan the user names, or else to the sole Plan whose Dispatch record shows it waiting, its reviews under way or at the decision at the end of the Plan and not yet landed; otherwise main asks the user which Plan.
- **Work branch.** The work branch is the Plan's branch that its Dispatch record records main created for the work, checked out in this checkout.

## Preconditions

- **Preconditions.** Before asking to merge, main checks each of these, and on any failure, or when one cannot be established, it reports which one and stops: the workspace is clean, `git -c core.safecrlf=false status --porcelain --untracked-files=all --ignore-submodules=none` listing nothing; HEAD is on a branch, not detached, and that branch is the work branch; the remote default branch resolves as review state's Commit and completion resolves it; the work branch is checked out in no other checkout, as `git worktree list --porcelain` shows, and no other checkout's Checkout lease names it, as the lease tool's `list` shows; the Plan's Dispatch record can be read; and the Plan is in the automatic flow.

## Fetch and merge

- **Agreement.** Main names the Plan, its work branch, the remote and the default branch, and asks the user whether to fetch and merge now; the user may instead wait or land another Plan first. The agreement comes only from the user's own message or the user's answer, as review state's Final check scope defines it, and it authorises this Plan's integration only.
- **Lease.** After the user agrees and before fetching, main takes or renews the Checkout lease of this checkout, as [the lease rules](../leases/SKILL.md#main-agent-rules) describe, and when it cannot take it, stops as they describe.
- **Fetch.** Main fetches the remote with `git fetch <remote>` and reads the remote default branch's tip with `git ls-remote <remote> refs/heads/<branch>`, which must print exactly one line naming a commit the fetch brought in; otherwise it reports and stops.
- **Already landed.** When any commit after the Plan's base revision on the work branch is an ancestor of the fetched tip, part of the Plan already reached the remote default branch: main reports, from the Dispatch record, which Claims are accepted and which are not, and stops for the user.
- **Nothing to integrate.** When the fetched tip is an ancestor of the work branch, as `git merge-base --is-ancestor <tip> HEAD` shows by exiting 0, main reports that nothing needs integrating and stops, unless Resuming below applies.
- **Merge.** Otherwise main merges the fetched tip, named by its full SHA, into the work branch with `git merge --no-ff -m "<message>" <full SHA>`, the message naming the remote default branch, resolves any conflicts itself, stages each resolved path by name with `git --literal-pathspecs add -- <paths>`, and commits the merge locally with `git commit --no-edit`.
- **No pull, rebase, force or push.** It never uses `git pull`, never rebases or forces, and pushes nothing in this step.
- **Merge commit.** The merge commit has exactly two parents, the work branch's tip before the merge first and the fetched tip second; when a conflict cannot be resolved, main reports it and asks the user, changing nothing further.

## Discarding a merge

- **When main may discard.** Main may throw away and redo its own merge, for example after plan review finds a wrong resolution, only when all of these hold: the merge commit is the work branch's tip, as `git rev-parse HEAD` shows; the workspace reads What a gated pass judged states show no change; every remote `git remote` lists was just fetched with `git fetch <remote>` and each fetch exited 0; and the tool, run after those fetches, reports the merge commit on no remote-tracking ref, every remote of its `remote_tracking` part known with `contains_merge_commit` false.
- **How.** It discards with `git reset --keep <full SHA of the tip before the merge>` and never uses a method that drops uncommitted changes, such as `git reset --hard`.
- **Otherwise.** When any of these conditions cannot be established, main does not discard, and fixes the merge with new commits, as review state's Commits before the passes requires.

## The facts

- **The tool.** Resolve the bundled launcher relative to this loaded skill: `scripts/merge_upstream.py`. When installed as a plugin, its path is `${CLAUDE_PLUGIN_ROOT}/skills/merge-upstream/scripts/merge_upstream.py`; use the actual loaded skill directory if the variable is unavailable. The tool needs Python 3.11+ and the handoff skill beside this one (`../handoff/scripts`), whose helpers it imports; keep the plugin's `skills/` directory together.
- **Running it.** Main runs `python -B <launcher> --project <checkout>` with one JSON object on stdin: `remote`, `default_branch`, `remote_tip`, `tip_before` and `merge_commit`, each commit by its full SHA, and `claims`, a list holding every Claim of the Plan, fix Claims and cancelled Claims included, each as `{"id", "base", "judged", "kind"}` with its base revision and judged commits as main reads them from the Dispatch record, and `kind` `fix` or `cancelled` where it applies.
- **Its output.** It prints one JSON object, status `ok` with exit 0 or status `error` with exit 2. Each part is `{"state": "known", ...}` or `{"state": "unknown", "reason": ...}`: `merge_parents` (with `as_expected`), `merge_base`, `upstream` (the merge base to the remote tip) and `merge_result` (the tip before the merge to the merge commit), each change with its status, both modes, kinds and objects; `resolution`, the paths both sides changed, each with whether the merge differs from each parent; `claims`, each Claim's own changed paths and their overlap with both lists, or `not-implemented` or unknown with the reason; `classification`, paths classed as test support, fixtures, runner configuration or build configuration, as advice only; and `remote_tracking`, for each remote whether the merge commit is on any of its remote-tracking refs.
- **Facts only.** The tool is read-only: it never fetches, merges, pushes or writes a ref, the index, the working tree or a record, and it leaves every pass judgement to main and plan review. A status `error` stops main, which reports it. A part the tool reports unknown gives no reason to keep a pass.

## Integration report

- **Entry.** Main writes the Integration report in the Plan's Dispatch record as an Upstream merge entry, after any earlier one, between review calls: the remote, the default branch, the remote tip, the tip before the merge and the merge commit by full SHA; the tool's facts, or the file beside the Dispatch record under `.feather/dispatch/` that holds them, named with its SHA-256; every resolved path; each Claim's outcome with main's reason; the Adversarial reviews to rerun; and any upstream change to a Claim's reading set.
- **Outcomes.** For each Claim, main writes "reopens code review and outcome verification", "reopens outcome verification only" or "passes stay", with its reason, judged as review state's What a pass covers states.
- **Judging.** File overlap is only a candidate: main judges dependencies, fixtures, reading sets and environment itself, and a Claim is never kept only because the merge did not touch its files. A merge result that changes a Claim's own files or acceptance checks, a conflict resolution included, reopens its code review and outcome verification. A cancelled Claim's commits on the branch are reported as unaccepted, as review state's Commit and completion describes.
- **Adversarial reviews.** The report lists, for every Security-critical Claim awaiting landing other than a fix Claim, its Adversarial review at the commit to be landed, with the upstream changes that share security assumptions with that Claim as input to its brief: read the [adversarial-review procedure](../delegation/references/adversarial-review.md)'s step 9 and follow it.
- **Reading sets.** An upstream change to a spec, ticket or other text a Claim's reading set cites is reported as a material deviation for the user to decide, never adopted: read the [plan-review procedure](../delegation/references/plan-review.md)'s step 5 and follow it.
- **No Plan change.** The report changes no Plan text, ticket or Claim, and adds no ticket or Claim.
- **Hash.** Main records the report's hash with it: the SHA-256 of the entry's text before its hash, READY and approval.

## Plan review of the report

- **Brief.** The report gets plan review under [the plan-review procedure](../delegation/references/plan-review.md): the brief carries the report, the Plan, the tool's facts, the Claims' recorded passes, the upstream diff and the merge result's diff for every path a kept reason relies on, and the full diff of every resolved path, a path no Claim owns included. The analyst checks each kept pass's reason, each reopened scope and each resolution.
- **Count.** Calls count as plan review calls of the Plan, continuing its count and stopping at the Stop threshold in effect, as review state's Stop threshold describes.
- **Scope question.** After READY, main asks the Plan's Final check scope again, as review state's Final check scope describes for a later plan review.
- **Approval.** Main then asks the user to approve the report, naming its hash, the merge commit and the Claims it keeps and reopens; the ask states that pushing waits until every pass the report requires is in, and that the user may ask for an earlier push.
- **Binding.** The READY and the approval hold only for the report's recorded hash and the merge commit's full SHA; a changed report, a redone merge or a new Upstream merge needs a new report, READY and approval.
- **Who approves.** The approval comes only from the user's own message or the user's answer, as review state's Final check scope defines it; main records it with that hash and SHA in the Dispatch record, and a resumed session takes it from there, as review state's Resumed sessions describes.
- **Until approved.** No reopened review runs before the report's READY and approval, and until both hold every Claim the merge touched counts as reopened, as review state's What a pass covers states.

## Re-review

- **Original Claims.** Reopened reviews are calls of the original Claims, continuing their counts as review state's Reopened calls describes, and are recorded in the Plan's own Dispatch record.
- **Briefs.** Their briefs diff each Claim from its original base revision to the commit judged and name the report's reason for reopening.
- **Existing behaviour.** Existing behaviour is taken both at the Claim's original base revision and at the merged remote tip: a defect already present at the remote tip is pre-existing unless the merge result changed it, as review state's Evidence for a regression states.
- **What stays.** Unresolved verdicts, open findings, a BROKEN's findings and recorded holds stay with their Claims, and a cancelled Claim's commits stay listed. A Claim kept by an approved report keeps its passes.

## Final check and Adversarial review

- **Final check.** The final check runs at the commit to be landed, the merge commit or a later one, as review state's Final check describes; a recorded run at an earlier commit does not cover it.
- **Adversarial review.** Every Security-critical Claim awaiting landing, other than a fix Claim, gets Adversarial review at that commit after that final check passes, whatever the report says about its files: read the [adversarial-review procedure](../delegation/references/adversarial-review.md)'s At the final commit and follow it.

## Pushing and landing

- **Pushing.** Main pushes no commit that has the merge commit as an ancestor before every pass the report requires is in, unless the user asks for an earlier push to the branch main created, as review state's Commits before the passes states.
- **Landing.** A Plan with an Upstream merge lands only on the user's own command or Accept and land, never under Auto land, as review state's Auto land states.
- **End of the Plan.** At the end of the Plan main asks the user as review state's Accept and land at the end of the plan describes, even when nothing needs accept and land, and the list covers every Claim on the branch with its state after the integration.

## Repeated movement

- **Another merge.** When the remote default branch moves again before landing, a new invocation records a second Upstream merge after the first, with its own report, READY and approval; the first one's re-review results stay with the commits they judged.

## Handoff and lease

- **Before each wait.** Before stopping to wait for the user, for the agreement to merge, the approval of the report or the landing decision, main updates the work's Active handoff when one exists and renews its Checkout lease.
- **No record of its own.** This command writes no handoff record of its own.

## Resuming

- **Resuming.** When the user invokes this command again for a Plan whose latest Upstream merge has no approval yet, or still has reopened reviews to run, and the fetched tip is an ancestor of the work branch, main continues that Upstream merge from the step its entry shows instead of merging again.

## Limits

- **What this flow does not check.** The report's kept passes rest on main's judgement and one plan review, so a dependency neither sees can still land unreviewed. A push the user makes outside the session is outside these rules: this command sees one only through the remote-tracking refs a fetch updates, so a push by URL, or to a remote or ref the fetch does not cover, is not seen before a discard. Main takes the Dispatch record as written.
- **A merge outside this command.** A merge of the remote default branch that main makes without this command is an edit outside the Plan's Claims: review state's What a pass covers reopens every Claim it touches, with no report to keep a pass, and Auto land's refusal of a range with a merge commit holds it.
