# Review follow-ups for 0.16.0

Label: `ready-for-agent`

Vocabulary follows [CONTEXT.md](../../CONTEXT.md). This spec collects the findings of the 2026-10-08 overall review of v0.16.0 (da4948c): three independent reviews (Python tooling, procedure documents, release hygiene), an independent Codex review, and two Claude–Codex discussions that settled how each finding is fixed. It amends the acceptance gate of [the commit-before-acceptance spec](commit-before-acceptance.md) and [ADR 0007](../adr/0007-commit-before-acceptance.md). It also absorbs the documentation and provenance patch that had been planned as 0.16.1, so the upstream manifest is reconciled once.

Decisions U1–U4 were settled by the user on 2026-10-08 (see Decisions). The release is 0.17.0, confirmed by the user on 2026-10-08, because it changes installed role definitions and adds a user-decision kind. After the first plan review the user also settled U5 and U6 and authorised the revisions they need (see Decisions). The plan passed plan review (an explicit READY on the third call, after two automatic REVISE verdicts), and the user agreed to this spec on 2026-10-08.

## Problem Statement

0.16.0 moved the acceptance gate from committing to landing, release, reporting complete and ticket completion, but the rules around it leave the user exposed in several ways.

Turning automatic review on lets main commit, push to working branches and open pull requests without asking, yet the guidance the user sees when turning it on, and the paragraph loaded into every session, never says so; the toggle even says turning a mode on "does not grant implementation authority". Main can read that as a reason not to commit, and then a gated review can never be dispatched, or it can act on an authority that lives only in a reference it loads on demand. A shared branch the user forgot to name, such as `develop`, is open to unaccepted pushes. In off mode, a claim an active handoff records as unreviewed also gets the push authority, although the user never turned the automatic flow on.

The user's ways of accepting work disagree. Saying "done", or any completion value including `wontfix`, makes a ticket finished, and a finished ticket counts as accepted for landing and release, so a cancelled claim's unreviewed commits can reach the default branch with the next landing. A deliberate, recorded waiver, on the other hand, can never complete a gated claim, so a claim the user knowingly accepts can never be reported complete. Setting `wontfix` after a cancellation is both required and forbidden.

Two defects can let unaccepted work through. In off mode, an explicit code review that passes removes the handoff note that put the claim under the gate, and nothing starts verification, so a later session lands the claim unverified. A review call that fails or is interrupted counts as a call, and the reviewer and analyst roles narrow a "second review" to earlier findings, so a retry after a call that judged nothing can approve code nobody reviewed.

The handoff tool has two defects. When the first Git probe times out or Git cannot be run, a save reports success and completed work is archived without the ignore rule the skill promises, so handoff records can be staged by a later broad `git add`. The work header ends at a heading recognised by an older rule than the one 0.15.0 introduced, so a field-like line under an indented or tab-separated heading in the user's own notes is read as a header field and overwritten by an update.

Finally, the upstream manifest's hashes for five handoff runtime files no longer match what ships, the 0.15.0 changes are not recorded as adaptations or compatibility differences, and several documents are stale: a personal path in the zh-TW README, "nine skills" for ten, pre-release wording without update commands, a pre-0.16.0 definition of `resolved`, an unwarned review-mode reset on reinstall, and an install of both components refused because of an unrelated saved model.

## Solution

Ship 0.17.0 with the Claims below, listed in this spec so they are visible without tickets:

- say plainly, where the user turns automatic review on and in the always-loaded guidance, what repository actions the automatic flow lets main take, and narrow them for pre-existing branches and for off mode as the user decided;
- give the user one explicit, recorded way to accept a gated claim without both passes, and stop won't-do values and casual statements from counting as acceptance;
- keep a gated claim gated until it is landed, released or reported complete, whatever single pass it has;
- make review scope depend on what a completed review covered, not on how many calls were attempted;
- report a failed first Git probe as the existing partial tracking failure;
- end the work header at the same heading rule everywhere;
- reconcile provenance and stale documents, and release with an explicit setup-update step.

## Claims

Each Claim's acceptance is listed under its own heading below the table. Claims are committed separately, in the order C1 to C8. Each commit leaves the full `unittest discover` suite passing; any existing assertion a Claim changes is updated in the same commit with the reason in the commit message.

| Claim | Outcome | Acceptance | Depends on |
| --- | --- | --- | --- |
| C1 Repository-action authority | The automatic flow's commit, push and pull-request authority is disclosed where the user turns it on and in always-loaded guidance, applies to pre-existing branches and off mode as decided (U1, U2, U4), and is distinct from acceptance | [C1](#c1-acceptance) | — |
| C2 Acceptance and completion | One explicit "accept and land" decision (U3) is the only way past the gate without both passes; won't-do values and casual statements never count as acceptance; cancellation leaves a visible disposition | [C2](#c2-acceptance) | C1 |
| C3 Gate lifetime | A gated claim stays gated after either single pass, until it is landed, released or reported complete, across sessions through the active handoff | [C3](#c3-acceptance) | C2 |
| C4 Review retry coverage | After a call that did not complete, the next call reviews the claim's full scope; narrowing follows only a completed review | [C4](#c4-acceptance) | C1 |
| C5 Tracking probe failures | A failed first Git probe is reported as the partial tracking failure, and completed work is not archived automatically | [C5](#c5-acceptance) | — |
| C6 Header boundary | Reading and updating a work header use the same heading rule as the managed sections | [C6](#c6-acceptance) | — |
| C7 Provenance and documents | The manifest, compatibility notes and listed documents describe what ships; installing both components is not refused for an unrelated saved model | [C7](#c7-acceptance) | C5, C6 |
| C8 Release 0.17.0 | 0.17.0 is validated, recorded with its setup-update step, and tagged locally after both passes | [C8](#c8-acceptance) | C1–C7 |

### C1 acceptance

1. **Disclosure (U1).** The always-loaded automatic-review paragraph, the toggle's Meaning, the auto-on description and both READMEs' switch sections each say that in auto main commits claims of plan-driven work before their passes, pushes them to branches it created for the work and may open a pull request listing the unaccepted claims, without asking, and that landing, release, reporting complete and ticket completion still wait for the passes. The Meaning no longer reads as the opposite: turning a mode on grants this scoped repository authority and no authority to implement, merge or release.
2. **Commit before a gated call.** The review-state rule for commits before the passes says that before dispatching a gated code review or outcome verification main ensures the content is committed and the named-commit precondition holds; when a commit is needed, this authority permits it without asking; an already suitable commit needs no new one.
3. **Distinct authorities.** The rule says opening a pull request is not permission to merge it, a pass is a condition for landing or release and not a request to perform either, and an explicit user instruction not to commit or push overrides the authority. When that instruction leaves a gated call without the commit it needs, main reports the claim blocked rather than reviewing an uncommitted workspace.
4. **Pre-existing branches (U2).** Main pushes freely only to a branch it created for the current work; before pushing to a remote branch that already existed and that it did not create, it asks the user. In a resumed session main treats a branch as its own only when an active handoff records that it created the branch for this work; otherwise it asks. The default-branch rules are unchanged.
5. **Off mode (U4).** For a claim the gate covers only because an active handoff records it, main may make the local commit a gated call needs without asking; pushes and pull requests follow ordinary off-mode behaviour, so main asks. The gate still applies. The push and pull-request authority therefore applies only to claims of plan-driven work in auto: no sentence in review state or either README still grants it to every claim an active handoff records, and a test asserts the 0.16.0 wording is gone.
6. README (EN, zh-TW) Commit / Commit 條件 states items 1, 3, 4 and 5; CONTEXT.md gains entries for the acceptance gate and for landing.

### C2 acceptance

1. **Accept and land (U3).** Review state's user decisions gain a sixth kind, accept and land: the user's explicit acceptance of a named gated claim without one or both passes. Main records its scope, the missing passes and the remaining risk; it stays visible in the report and in any active handoff, is never recorded as READY, APPROVED or CONFIRMED, and satisfies the acceptance gate for that claim as it stands. It names the commit it accepts, and a later relevant change to the claim ends it, as for a pass. Unlike a pass, it is the user's decision, so one recorded in an active handoff still satisfies the gate in a resumed session while no relevant change has followed the commit it names (U5).
2. **Casual statements.** A user statement that work is done counts as acceptance only after main confirms it with the user and records it as accept and land; otherwise it means the work is not to be redone.
3. **Finished is not accepted.** Review state separates "not redone" from "accepted": every finished ticket is not redone, but only a ticket set to a done value after valid passes or an accept-and-land decision counts as accepted for landing and release, and only while no relevant change has reopened its claim. A won't-do value never counts as acceptance.
4. **Completion values.** The gate's ban on setting a completion value before both passes covers done values only; a won't-do value is set on the user's recorded cancellation, so the claim-changes rule and the gate no longer conflict.
5. **Cancellation.** A cancelled claim's commits that remain on a branch are listed as unaccepted until the user decides their disposition (revert with a new commit, keep off the default branch, or accept and land); landing a branch that carries them waits for that decision. Pushed history is still never rewritten.
6. **Waivers.** The waiver rule says separately that a waiver names the finding or pass it waives (a missing READY can be waived as Implemented before plan review allows), that it does not complete a gated claim, and that a labelled work-in-progress push the user allows moves commits to the default branch without satisfying release or completion.
7. **Handoff completion.** The handoff skill says a work is saved as complete only after its gated claims are accepted or disposed of; closing tickets or ending a session does not justify it.
8. Review state's Resumed sessions rule and both READMEs' Resumed session / 恢復的 session bullets exempt from fresh passes only a claim whose ticket was set to a done value after valid passes or an accept-and-land decision, with no relevant change since, instead of any finished ticket; a test asserts, in review state and those two README bullets only (historical ADR and spec text is not rewritten), that "unless its ticket is finished", 「除非它的 ticket 已完成」 and the whole 0.16.0 clause "a claim whose ticket is finished is not redone and counts as accepted for landing and release" are gone.
9. The tracker convention's `resolved` reads "implemented and accepted (both passes, or the user's accept-and-land decision)"; README Your decisions / 你的決定 and Ticket status / Ticket 狀態 state items 1–5; CONTEXT.md defines accept and land.

### C3 acceptance

1. **Pending acceptance.** When a pass resolves an active handoff's unreviewed or unverified note for a gated claim, main replaces it with a note that the claim is pending acceptance, naming what is still missing and that it must not be landed on the default branch, released or reported complete. An accept-and-land decision does not remove the note: main records the decision in it, and the note then counts as the record that keeps the claim under the gate until it is landed. Main removes the note only when the claim is landed, released or reported complete, or cancelled with its commits disposed of. When a relevant change ends an accept-and-land decision, the note returns to pending acceptance, naming what is missing.
2. Code review step 6 and outcome verification step 6 point to this rule instead of removing the note on a pass; no sentence there removes the note in any case other than those item 1 lists. Review state's gate coverage names a claim an active handoff records as unreviewed, unverified or pending acceptance.
3. A resumed session that finds a pending-acceptance note keeps the claim under the gate and obtains passes from the current session, as passing verdicts still do not cross sessions, unless the note records an accept-and-land decision that still holds under C2 item 1 (U5).
4. CONTEXT.md defines an active handoff (an unfinished record under the handoff store for the work) and a pending-acceptance claim; README Resumed session / 恢復的 session states item 3.

### C4 acceptance

1. Review state distinguishes a completed call (one that returned a verdict for the content it judged) from a call that failed, was interrupted or broke protocol. Only a completed review establishes coverage.
2. A second review, and the range "from the previously judged commit", follow only a completed review; after a call that did not complete, the next call reviews the claim's full scope from its base revision (for plan review, the whole plan), carrying any partial findings as evidence. Budgets and the one-retry rule are unchanged.
3. The reviewer and analyst role templates narrow a second review only when the brief says the earlier review completed; otherwise they review the full scope.
4. Code review step 2 and plan review step 2 say the brief states whether the earlier call completed.

### C5 acceptance

1. A first Git probe that cannot run Git (a missing executable or another operating-system error) or times out is reported as the partial `tracking-failed` result: the work is saved, the result is `complete: false` with exit status 2, completed work is not archived automatically, and the result carries `cause_code: git-unavailable` (U6). Its recovery text says the work is saved and tracking was not applied because Git could not be run or did not respond, not to repeat create or update now, and, once Git runs, to apply tracking with update for active work or archive for completed work, using the same tracking choice. It does not say to retry while Git is unavailable, so a root without Git does not loop. A directory Git reports as not a repository is still reported as non-Git.
2. Explicit archive keeps its existing contract when tracking then fails: history is saved, the work is removed, `archived` stays true and the recovery says not to retry archive.
3. The handoff tool reference says that a deliberately selected non-Git root with Git unavailable now saves only partially, with `cause_code: git-unavailable`, and the release records this as a compatibility change. The handoff skill's archive guidance and the snapshot reference's tracking-failure note (`skills/handoff/references/snapshots.md`) tell main, on a `git-unavailable` partial, to report it and wait for Git rather than retry.

### C6 acceptance

1. Reading a work's summary and updating its header fields find the end of the header with one shared, fence-aware heading rule, the CommonMark ATX rule the managed sections already use (up to three spaces of indent, then a space, a tab or the end of the line).
2. The canonical first-line `# ` title is unchanged, as are completion identities and archival.
3. A record whose headings were already recognised reads and updates byte for byte as before.

### C7 acceptance

1. The upstream manifest's current-file hashes match the shipped files after the final edits; baseline and records gain adaptation entries; tracking and writing entries describe the 0.15.0 and this release's changes; original upstream hashes are kept; the test-mutations entry no longer contradicts itself. The compatibility notes record the heading, `.gitignore` whitespace, blank-title and tracking-probe differences.
2. A test fails when a manifest-listed file's current hash or path does not match what ships.
3. The zh-TW README's install line uses a placeholder path; the setup document says ten skills; both READMEs replace "After publishing this version" with the actual update commands; the setup document warns that remove and reinstall resets the review mode unless `--review-mode` is given.
4. Installing both components is not refused because of a saved model the current version rejects when delegation is already installed and only handoff would be installed.

### C8 acceptance

1. `.claude-plugin/plugin.json` is 0.17.0.
2. The 0.17.0 validation entry and both READMEs say a setup update is required in every scope where delegation is installed, followed by a fresh session, because role definitions changed; the entry does not repeat the earlier releases' "no setup update" conclusion.
3. The suite and `claude plugin validate` pass on Windows, with Python and Claude Code versions, test counts and skip reasons recorded; an upgrade of an installation made from the 0.16.0 templates is exercised, and afterwards the installed reviewer and analyst roles contain C4's new text and an auto installation's guidance contains C1's new paragraph. The entry and both READMEs note that until setup update, `review` refuses to switch the mode of a 0.16.0 auto installation and asks for setup update first.
4. The entry records the live scenarios run for C1–C4 and those not exercised, and notes that v0.16.0 tags da4948c, the clarification commit after the 0.16.0 release commit.
5. A new ADR records U1–U6 and the gate-lifetime and retry-coverage corrections, and ADR 0007 gains an amendment note pointing to it.
6. Before the tag is created, main checks that the manifest version is 0.17.0 and that no `v0.17.0` tag exists. The tag `v0.17.0` is created only after both passes and only with the user's go-ahead; that it names the release commit and matches the manifest version are checked afterwards as postconditions.

## Decisions

- **U1: keep the automatic flow's repository authority, and disclose it.** In auto, committing before the passes, pushing to working branches and opening pull requests stay on by default (0.16.0 D1, D4); they are stated where the user turns auto on and in the always-loaded guidance. Options not taken: make push and pull requests a separate opt-in; ask before every push.
- **U2: ask before pushing to a pre-existing branch.** Main pushes freely only to branches it created for the current work and asks before pushing to a remote branch that already existed. This narrows 0.16.0 D2. Options not taken: keep D2 (only the default branch and branches the user names are protected); push only to branches main created.
- **U3: accept and land.** The user may accept a gated claim without both passes through an explicit, recorded decision; a casual "done" counts only once confirmed and recorded as one. Options not taken: nothing substitutes for the passes; any statement that work is done counts, acknowledged as an exception.
- **U4: off mode commits locally, asks before pushing.** For a claim an active handoff restricts in off mode, main may make the local commit a gated call needs; pushes and pull requests follow off-mode behaviour. Options not taken: keep the full automatic-flow authority in off; ask before every commit too.
- **U5: accept and land across sessions** (after plan review call 1, 2026-10-08). An accept-and-land decision recorded in an active handoff still satisfies the gate in a resumed session, like a waiver kept in a handoff, until a relevant change follows the commit it names. Option not taken: the user decides again in every session.
- **U6: Git unavailable at the first probe** (after plan review call 1, 2026-10-08). The partial result carries its own `cause_code: git-unavailable` and a recovery that waits for Git instead of retrying, so a deliberately selected root without Git does not loop. Option not taken: reuse the generic tracking-failure recovery, which says to retry update.

## User Stories

1. As a user turning automatic review on, I want the toggle to tell me that main will commit, push to working branches and open pull requests without asking, so that I agree to that knowingly.
2. As a user, I want the paragraph loaded in every session to state that authority, so that main neither refuses to commit nor acts on an authority it read only on demand.
3. As a user, I want main to commit a claim before a gated review only when the review needs it, so that I do not get empty or duplicate commits.
4. As a user, I want a pull request main opens to stay unmerged until its claims pass, so that opening one never lands work.
5. As a user, I want my explicit "don't push" to win over the automatic authority, so that I stay in control of my remote.
6. As a user working on a shared `develop` branch, I want main to ask before pushing to it, so that unaccepted commits do not reach branches others pull.
7. As a user in a cloud session, I want main to push its own working branch freely, so that a reclaimed container loses nothing.
8. As a user who turned auto off, I want main to ask before pushing a claim my handoff still restricts, so that off means what I chose.
9. As a user who turned auto off, I want main to make the local commit a review needs without asking, so that asking for a review does not stall.
10. As a user who knowingly accepts a claim whose review keeps failing, I want one explicit decision that records my acceptance and its risk, so that I can land, release and finish the work.
11. As a user, I want a casual "done" to be confirmed before it counts as acceptance, so that a passing remark never bypasses the gate.
12. As a user who cancels a claim, I want its leftover commits listed until I decide what happens to them, so that cancelled work is never landed by accident.
13. As a user, I want `wontfix` to mean only that the work will not be done, so that closing a ticket never counts as accepting its code.
14. As a user, I want a ticket marked `resolved` in an earlier session to stay accepted only while its code is unchanged, so that later edits are reviewed again.
15. As a user, I want a waiver to say exactly which finding or pass it waives, so that I know the risk I am carrying.
16. As a user, I want a work-in-progress push I allow to be clearly separate from completion and release, so that allowing the push does not mark the work done.
17. As a user who asked for an explicit code review in off mode, I want the claim to stay gated until it is verified and landed, so that an approval alone never lets it reach the default branch.
18. As a user resuming work, I want the handoff to tell me which claims still await acceptance, so that the next session does not land them unchecked.
19. As a user, I want a review call that crashed to be followed by a full review, so that an approval always rests on a review that actually happened.
20. As a reviewer role, I want the brief to say whether the earlier review completed, so that I know whether to narrow my scope.
21. As a user, I want the retry budget to stay as it is, so that fixing coverage does not make reviews more expensive by default.
22. As a user with a slow repository, I want a timed-out Git probe reported as a partial tracking failure, so that my handoff records are not left unignored while the save claims success.
23. As a user whose Git is not on the tool's PATH, I want the save reported as partial, so that I fix the environment before records can be staged.
24. As a user of a genuinely non-Git directory, I want saves to keep succeeding, so that non-Git projects are not degraded.
25. As a user archiving completed work explicitly, I want a later tracking failure not to make me retry the archive, so that history is not duplicated.
26. As a user writing my own notes in a handoff, I want an indented or tab-separated heading to end the header, so that a field-like line in my notes is never overwritten.
27. As a user with existing handoff records, I want them to read and update exactly as before, so that the fix changes nothing that already worked.
28. As a user sharing records with codex-feather, I want the differences from upstream recorded, so that I know where the two tools diverge.
29. As a maintainer, I want a test that fails when the upstream manifest drifts from what ships, so that provenance cannot silently go stale again.
30. As a zh-TW reader, I want the install instructions free of the maintainer's local path, so that I can follow them on my own machine.
31. As a user updating the plugin, I want the README to give the actual update commands, so that I do not have to look them up.
32. As a user recovering from an unsafe saved model by reinstalling, I want to be warned that the review mode resets, so that I restore auto deliberately.
33. As a user installing handoff next to an existing delegation installation, I want the install not to be refused over an unrelated saved model, so that adding a component just works.
34. As a user upgrading to 0.17.0, I want the release to tell me to run setup update and start a fresh session, so that my installed roles get the retry fix.
35. As a maintainer, I want the validation entry to record which live scenarios ran on Windows, so that the evidence matches the platform I use.
36. As a maintainer, I want the release tagged only after both passes and only with my go-ahead, so that no unaccepted release is published.

## Implementation Decisions

- **Review state procedure** gains: the commit-before-a-gated-call rule; the distinction between repository authority, acceptance and merge or release authority; the pre-existing-branch rule; the off-mode rule; the accept-and-land decision kind; the split between "not redone" and "accepted"; the done-value scope of the gate; the cancellation disposition; the pending-acceptance note; and the completed-call definition for review coverage. Each rule is stated once there; other documents point to it.
- **Code review and outcome verification procedures** replace "remove that note" on a pass with a pointer to the pending-acceptance rule, and their step 2 briefs state whether the earlier call completed.
- **Plan review procedure** step 2 states the same for analyst briefs.
- **Reviewer and analyst role templates** condition their second-review narrowing on a brief that says the earlier review completed. This changes installed role definitions, so the release requires a setup update.
- **Always-loaded automatic-review paragraph, toggle Meaning and auto-on description** carry the disclosure (U1). The paragraph stays short: it names the actions and the gate and points to the procedure.
- **Handoff skill** ties saving a work as complete to its gated claims being accepted or disposed of.
- **Handoff tracking** stops converting a failed first probe into a normal "not-checked" result; it raises an error with `cause_code: git-unavailable`, and the save path reports it as `tracking-failed` with the waiting recovery of U6 instead of the generic retry text; explicit archive keeps its existing contract. Genuine non-Git detection is unchanged.
- **Handoff header parsing** moves to one shared helper, reused by summary and header updates, built on the heading rule the managed-section parser already uses and aware of code fences. Title detection keeps the first-line `# ` contract.
- **Configuration tool** limits the unsafe-saved-model refusal on install to the components the install actually writes.
- **Glossary** gains acceptance gate, landing, active handoff, pending-acceptance claim and accept and land.
- **ADR**: a new ADR records U1–U6 and the two corrections; ADR 0007 gets an amendment note. Historical release entries are not rewritten.

## Testing Decisions

- Tests check external behaviour: what a shipped document says, what the handoff command returns and writes, and what the configuration tool installs. They do not inspect internal functions except at the one in-process seam below.
- **S1, procedure contracts (existing seam).** The configuration tool's test module already pins procedure, template, README, glossary and ADR text. New rules are pinned as whole sentences in the document that states them, with README rules paired in both languages. The transition scenarios are listed in a table that maps each scenario to the sentences governing it: off-mode handoff with APPROVED only, CONFIRMED only and both; a relevant edit after a pass; resume before acceptance; waiver; cancellation with leftover commits; accept and land, including in a resumed session, after a relevant change, and off mode with accept and land followed by a relevant change before landing (still gated); a casual "done"; off mode with a handoff record and a push or pull request (main asks); auto with a push to a pre-existing branch main did not create (main asks); a user's "don't push"; a call that fails before a verdict; partial findings before an interruption; a completed review followed by a failed follow-up; an exhausted budget; and the negative control that an explicit review of ungated work starts no verification. Prior art: the review-state rule tests and the README and glossary pairing tests.
- Text tests cannot prove agent behaviour; the C8 validation entry records which live scenarios ran with the installed native roles and which did not.
- **S2, handoff command (existing seam).** Heading and tracking behaviour is exercised by running the handoff command as a subprocess, as the local-fixes tests do. A missing Git executable is simulated by a PATH without Git and an explicitly selected root. Each first-probe failure case asserts `cause_code: git-unavailable` and the waiting recovery text. Timeouts and other operating-system errors at the first probe are injected by calling the same command entry point in process with the probe patched; this is the only new seam. Cases cover create and update, active and completed work, both tracking choices, explicit archive after a tracking failure, a real repository selected as an explicit root, and a genuine non-Git directory. Heading cases cover zero to three spaces, tabs, empty headings and levels 1–6 before the first managed section with field-like lines beneath, plus four-space and fenced controls, LF, CRLF, BOM and Unicode, and completion and archive round trips with the body preserved byte for byte. Prior art: the tracking-failure and ATX heading tests in the local-fixes module.
- **S3, configuration tool (existing seam).** In-process tests cover upgrading an installation rendered from the 0.16.0 templates in user and project scope (prefixed names, kept models, efforts and review mode, edited-file conflicts preserved, and the new role and guidance text present afterwards), `review` refused on a 0.16.0 auto installation before setup update, installing both components with a rejected saved model when delegation is already installed, and the manifest integrity check. Prior art: the saved-unsafe-model recovery tests and the role rendering tests.
- The full suite runs on Windows for every Claim and for the release.

## Out of Scope

- A lock for concurrent handoff history writers; the single-writer requirement stays documented.
- Quoting or round-tripping model identifiers that YAML reads as non-strings (`null`, `true`, numbers).
- Checking the Claude Code version before offering AGENTS.md as the policy target.
- Windows reserved names such as `CONIN$` in handoff file names.
- Broadening the work title syntax beyond the first-line `# `.
- Changing review budgets, the one-retry rule or the default-branch rules.

## Further Notes

- The Codex discussions also agreed that the gate and its exceptions should each be stated in one place, with other documents pointing there; this spec applies that to every rule it touches but does not restructure untouched procedure text.
- C5 changes documented behaviour for deliberately selected non-Git roots when Git is unavailable; the release notes call it out.
- Implementation must coordinate ownership of the handoff writing module between C5 and C6.
