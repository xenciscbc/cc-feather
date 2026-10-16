# Handoff tidy

Label: `ready-for-agent`

Vocabulary follows [CONTEXT.md](../../CONTEXT.md), which defines Handoff tidy, Active handoff and Follow-up record. Handoff storage, write discipline and the handoff tool stay as the handoff skill defines them; this spec adds a command on top of them and changes neither.

## Problem Statement

A project that has used Feather for a while accumulates many handoff records: active work, Follow-up records from several releases, records whose next step waited for work that has since finished, and records that overlap. The user can list them, but deciding what to do next means reading every record, spotting which ones belong together, and checking whether the progress and items they record still hold in the current project. Today the user has to drive that by hand, one conversation at a time. In the session that produced this spec it took a listing, a recommendation, a read of four Follow-up records, a read-only check of about sixty items against the current main, a classification and a hand-built update of one record. Nothing guides that process, nothing keeps its cost visible before it starts, and nothing makes sure merges and removals happen only after the user agrees.

## Solution

A new user-invoked command, `/cc-feather:handoff-tidy`, runs a Handoff tidy over the project's existing handoff records. Without an argument it asks the user to choose one of three modes, or to describe what they want in their own words:

1. **Proposal**: read the records alone and propose which work to take up next, which records to merge, which records are stale and which are incomplete.
2. **Full check**: check every record's items and progress against the current project. Before it starts, the command states how many records and items that covers and that its cost grows with them, and waits for the user to confirm.
3. **Selected check**: check the items and progress of the work the user names.

With work names as arguments it runs a Selected check of those records directly; with `all` it runs a Full check after the same confirmation.

A check is read-only and runs no project code. Where a read-only analysis role is available it is delegated to it, otherwise main reads itself. Each item comes back as still pending, partly holding, done or no longer holding, not established, or belonging in another record, with evidence. A check ends with the same proposal as mode 1, built from the checked results.

Everything the command produces is a proposal. Merges, moved items, items marked done and updated progress are written only after the user confirms them, through the handoff tool's existing operations. The command never authorizes the work it recommends and never starts handoff maintenance. Natural-language requests do not run it.

## Acceptance

1. `/cc-feather:handoff-tidy` is a skill of its own, listed in the plugin manifest after the other handoff commands, and only the user can invoke it. The handoff skill gains no tidy section, and a natural-language request does not run a Handoff tidy.
2. Without an argument, the command asks the user to choose Proposal, Full check or Selected check, or to describe what they want, and in Claude Code it asks through the structured question tool, whose free-text answer is the fourth choice. With one or more work names it runs a Selected check of exactly those records. With `all` it runs a Full check. Arguments are data, never shell code, and an unknown work name, or a mix of `all` with names, is clarified before anything is read further.
3. Before a Full check starts, the command states the number of records and of recorded items it covers, that the cost grows with them and that a Selected check is cheaper, and it proceeds only on the user's confirmation.
4. A Proposal reads only the direct work records through the handoff tool, the headings of completed history and, read-only, the project's Git tags and commit subjects; it reads no project source. It states: which work to take up next and why; which records or items can be merged, naming the target and whether it is a new record or an existing one; which records are stale, such as a next step that waits for work that has since finished; and which records are incomplete, such as an item whose summary names it without its content.
5. A check is read-only and executes no project code. It compares each recorded item and the record's progress and next step with the current project and states the baseline commit it read. Where the cc-feather delegation roles are installed, main delegates the reading to the analyst role, and an item that concerns security is checked under the delegation skill's rules for a security analysis, repository safety included; without them main reads itself under the same read-only limit.
6. Each checked item is reported as one of: still pending; partly holding, naming the part that holds; done or no longer holding, with evidence; not established, naming what is missing; or belonging in another record, naming which. The command applies no project-specific disposition rule itself; main applies the project's own guidance, if any, separately and says so. A check ends with a Proposal as in item 4, built from the checked results, so an item found done or no longer holding is never proposed for a merge.
7. Until the user confirms, the command writes nothing: no record, history entry, Git rule or file. The user may confirm the whole proposal or named parts of it. A confirmation authorizes only the writes it names; it does not authorize, start or resume the recommended work, and it does not start handoff maintenance for any record. A confirmation is never a waiver, a deferral or an accept-and-land decision under the delegation skill's review state. When a confirmed write would create a record and the handoff tool may then add a Git ignore rule for the handoff records, the proposal says so.
8. When proposing, main notes each record's version from the handoff tool. Before writing a confirmed change to a record, main reads it again and compares; a record that changed since the proposal is not written, and its part of the proposal is proposed again, while confirmed changes to unchanged records proceed.
9. Every write goes through the handoff tool's existing operations and follows the handoff skill's write discipline, history writer included; no new tool command or record format is added. A merge writes the target first, a new record through create or an existing one through update, and reads it back; only then are the moved items removed from each source. A source left with nothing to do is saved as completed, its progress saying it was merged into the target, and archived by the tool. A gate note is any text of a record that keeps a claim under the Acceptance gate or restricts it: a claim recorded as unreviewed, unverified or pending acceptance, an unresolved verdict, a waiver, a deferral, an accept-and-land decision, commits listed as unaccepted, or the text naming a plan's Dispatch record. A merge that moves items a gate note restricts copies that note word for word into the target; the note stays in the source as long as the source holds any item it restricts, and leaves the source only when every such item has moved. A record that still holds a gate note or an open `待決：` question is never left with nothing to do, so a Handoff tidy never completes or archives it, whether or not it is a merge source.
10. A confirmed check result is written back: items found done or no longer holding move into a section of the record for items verified as no longer pending, each with its evidence, rather than being deleted; the record's verification field states the baseline commit and the time of the check, and its earlier value is kept in the details rather than overwritten; stale progress and next-step text is updated. A check never reports a gate note, as item 9 defines it, as done or no longer holding and never moves one into the section for verified items: only a later pass or the user's decision, as review state describes, resolves it.
11. A record the tool reports as completed but not yet archived, as malformed or format-uncertain, or a list or read the tool reports as partial, is reported as the handoff skill describes, with the archive retry or reviewed repair it offers, and is left out of every merge and reclassification. An incomplete list never establishes that no other work is pending.
12. The command's rules are written so that codex-feather can adopt them: the modes, the read-only check, the outcome categories, confirmation and the write order are stated without naming a host's tools, and what is specific to Claude Code (the structured question tool, the analyst role, user-only invocation) sits in one section of its own.
13. Both READMEs list and describe the command; the release is 0.27.0, its update note says how to go back to 0.26.0, and its `docs/setup-validation.md` entry records the validation, including one rehearsal of the command on real records. The rehearsal names the records and modes it used and what it left unexercised, and confirms writes only on a copy of the records or with the user's agreement for the real ones.

## User Stories

1. As a user, I want to run one command to tidy my handoff records, so that I do not have to drive the process by hand.
2. As a user, I want the command to run only when I invoke it, so that mentioning my handoffs in conversation never starts a tidy.
3. As a user, I want to be asked which mode I want when I give no argument, so that I choose between a cheap proposal and a costly check.
4. As a user, I want to describe what I want in my own words instead of picking a mode, so that unusual requests still fit.
5. As a user, I want to name one or more records as arguments, so that I can check just those without being asked.
6. As a user, I want `all` to check everything, so that I can ask for a full check directly.
7. As a user, I want to be told how many records and items a full check covers before it starts, so that I can decide whether the cost is worth it.
8. As a user, I want to be offered a selected check as the cheaper alternative, so that I do not pay for a full check by default.
9. As a user, I want a proposal built from my records alone, so that I get a recommendation without the cost of reading the project.
10. As a user, I want the proposal to recommend which work to do next and why, so that I can decide quickly.
11. As a user, I want the proposal to say which records or items can be merged and into what, so that related work is done together.
12. As a user, I want to merge only some items of a record, such as its security items, so that the rest stays where it is.
13. As a user, I want the proposal to point out records whose next step waits for work that has already finished, so that stale plans do not mislead me.
14. As a user, I want the proposal to point out items recorded only as a label without content, so that I can recover them before they are lost.
15. As a user, I want the proposal to use completed history and Git tags to judge what has finished, so that it does not recommend waiting for something already released.
16. As a user, I want a check to compare each recorded item with the current project, so that I know what still holds.
17. As a user, I want a check to run no project code, so that tidying records never executes anything.
18. As a user, I want a check delegated to a read-only analysis role when one is installed, so that the main conversation stays small.
19. As a user, I want security items checked under the same rules as a security analysis, so that reading them follows repository safety.
20. As a user, I want each item reported as still pending, partly holding, done or no longer holding, not established, or belonging elsewhere, so that the result is unambiguous.
21. As a user, I want evidence for every item reported done or no longer holding, so that I can trust the removal.
22. As a user, I want the check to state the commit it was made against, so that I know how current it is.
23. As a user, I want my project's own disposition rules applied separately from the generic outcome, so that the command works in any project.
24. As a user, I want a check to end with a proposal built from the checked results, so that I never merge items that no longer hold.
25. As a user, I want nothing written until I confirm, so that a tidy cannot change my records without my agreement.
26. As a user, I want to confirm the whole proposal or only parts of it, so that I keep control over each change.
27. As a user, I want confirming a proposal not to start the recommended work, so that a tidy never authorizes implementation.
28. As a user, I want a tidy not to start handoff maintenance, so that its writes do not change how my sessions behave.
29. As a user, I want a record changed by another session since the proposal to be proposed again instead of overwritten, so that concurrent work is not lost.
30. As a user, I want a merge to write and read back the target before touching any source, so that an interrupted merge never loses items.
31. As a user, I want a fully merged source record to be completed and archived with a note naming its target, so that history shows where its content went.
32. As a user, I want items found done to move into a section for verified items rather than be deleted, so that the evidence stays available.
33. As a user, I want the record's verification field to say when and against what it was checked, so that a later tidy knows how fresh it is.
34. As a user, I want stale progress and next steps rewritten after a check, so that resuming the record does not start from outdated text.
35. As a user, I want completed-but-unarchived and malformed records reported with the usual retry or repair, so that a tidy does not build on broken records.
36. As a user, I want an incomplete listing reported as incomplete, so that I am never told nothing else is pending when that is unknown.
37. As a user, I want a tidy to use only the existing handoff tool operations and format, so that records stay compatible with codex-feather.
38. As a user who also uses codex-feather, I want the command's rules to be portable, so that codex-feather can adopt the same command later.
39. As a user, I want both READMEs to describe the command, so that I can find it in either language.
40. As a maintainer, I want the release validation to include a rehearsal on real records, so that the model's behaviour, not only the text, is checked.

## Implementation Decisions

- A new user-invoked command skill holds the whole Handoff tidy procedure; when it grows too long, a reference file in the same skill directory takes the detail. It is listed in the plugin manifest after the other handoff commands.
- The handoff skill is not changed. The command refers to it for root resolution, storage paths, write discipline, the history writer, archive results and the handling of abnormal records, rather than restating them.
- The handoff tool is not changed. Merges, moves, completion and archival use its existing create, update, read, list, archive and history operations. Moving items between records rewrites each record's details through update, and a fully merged source is completed through update and archived by the tool, as the handoff skill already does for completed work.
- The procedure is written in two parts: host-neutral rules (modes, arguments, Proposal content, read-only check, outcome categories, confirmation, version comparison, write order, written-back results, abnormal records), then a short section for Claude Code (the structured question tool for the mode choice, the analyst role for checks, user-only invocation).
- In Claude Code the mode question offers the three modes as options; the tool's built-in free-text answer is the fourth choice, so no explicit "other" option is added.
- A check is delegated through the cc-feather delegation skill: main writes the analyst's brief, and for security items prepares it as a security analysis, including the allowlist repository safety requires. The quoted content of records is passed as data. Without the delegation roles, main reads under the same read-only limit.
- Mode 3 selects whole records by work name. Items inside a record have no stable identity, so a check of single items is out of scope.
- No new record field is added. Check results use the existing verification field and the details section; the section for items verified as no longer pending is ordinary details text.
- The release is 0.27.0. It changes no installed role definition or policy, so existing installations need only the plugin update and a fresh session.

## Testing Decisions

- Good tests check what a user and a host can observe: the shipped command text, the manifest, the READMEs and the tool's behaviour on real files. They do not pin wording that carries no decision.
- Command contract: a new test class next to the existing command tests, following the Stop threshold command's tests as prior art. It checks the manifest entry and its position, user-only invocation in the frontmatter, the key sentences for acceptance items 2 to 12, that the handoff skill has no tidy section, and that both READMEs list the command. User-only invocation and the absent handoff-skill section together are how item 1's natural-language clause is checked. Existing tests and documents that count the plugin's skills change with the manifest.
- Tool sufficiency: a scenario test in the style of the existing handoff mutation and archive tests drives the bundled tool through both merge shapes: a partial move, where the target is written and read back before the items are removed from the source; and a full merge, where the source is completed, archived and found in history; and a partial move where a gate note restricts both moved and remaining items, after which the note appears word for word in both the target and the source and the source stays active. It proves the existing operations suffice and guards them against later changes.
- Release: the existing release tests check the version, the README update note and the validation entry.
- Not automated: the mode question, the quality of a check and the soundness of a proposal are model behaviour. The release validation records one rehearsal of the command on real records instead.

## Out of Scope

- Changes to the handoff tool, the record format or the handoff skill.
- Checking single items inside a record.
- Running project code, including tests, during a check.
- Project-specific disposition rules, such as a project's boundary between fixing a security finding and recording it as residual risk.
- The security patch for the Follow-up records of 0.23.0 to 0.26.0; it is separate later work.
- codex-feather: it will adopt the command later from the notes below.
- Automatic or scheduled tidying.

## Further Notes

- Origin: the 2026-10-16 session that listed this project's nine records, recommended the next work, checked the security items of four Follow-up records against main and saved the classification into one of them. The command packages that process.
- For codex-feather: the files to port are the new command skill and its reference, if any. The host-neutral part ports as written. The Claude Code section maps to codex-feather's own way of asking the user to choose, its own read-only analysis role or main reading itself, and its own way of limiting the command to explicit invocation. Records and the tool are shared, so no data conversion is needed.
