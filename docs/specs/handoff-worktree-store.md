# Handoff worktree store

Label: `ready-for-agent`

Vocabulary follows [CONTEXT.md](../../CONTEXT.md), which defines Active handoff, Follow-up record and Handoff tidy; this spec adds Handoff store and Working checkout. The record format, the write discipline and the tool's existing results stay as the handoff skill defines them, except where an item below changes them.

## Problem Statement

The handoff tool finds the project root with Git's top level. In a linked worktree that is the worktree's own directory, so every record written there lands inside that worktree. Claude Code desktop starts many sessions in worktrees it created, and that causes three problems:

1. **Records are lost with the worktree.** `.feather/handoffs/` is ignored by default, and `git worktree remove` without `--force` deletes ignored files without a warning and exits 0. This was reproduced in a disposable repository. When a worktree is cleaned up or archived, its active handoffs, history and sealed archives go with it, and nothing reports the loss.
2. **Records are fragmented.** A record written in worktree A cannot be seen from the main checkout or from worktree B. A fresh session there lists no pending work, which is wrong and looks right.
3. **History is fragmented.** Each worktree keeps its own `history.md`, so completed work cannot be searched in one place.

The skill currently says only that cross-project and worktree synchronization is outside its scope, so the user has no supported way to keep handoffs across worktrees.

## Solution

All checkouts of one repository share one Handoff store: `.feather/handoffs/` in the repository's main worktree. A session in a linked worktree reads and writes records there, while source baselines and the record's environment still describe the checkout the session works in, its Working checkout. A session in the main worktree, a non-Git project and an explicit root behave as before, so existing records need no migration.

When the main worktree cannot be identified, or the store cannot be written from the current session, the tool says so and writes nothing, rather than falling back to records inside the linked worktree. Tracked records keep following their checkout, because a tracked record belongs to its branch.

Sharing one store makes concurrent sessions normal, so the tool serializes every history mutation with a short-lived lock. A stale lock is reported, never removed automatically; the user decides whether to clear it.

Records left in other stores, such as those a linked worktree wrote before this change, are reported when work is listed. They move into the shared store only through an explicit `adopt` operation the user confirms, which stops on a name or history conflict.

## Acceptance

1. **Store selection.** The tool resolves two locations: the Working checkout, which is the Git top level of `--project` as today, and the Handoff store. When the Working checkout is a linked worktree of a non-bare repository and its tracking state (item 6) is untracked, the store is `.feather/handoffs/` under the repository's main worktree. In every other case it stays under the Working checkout as today: the main worktree itself, a non-Git project, `--exact-root`, and tracked mode.
2. **Main worktree discovery.** The Working checkout is a linked worktree only when the filesystem identities of its `git rev-parse --absolute-git-dir` and `--path-format=absolute --git-common-dir` differ, so a main checkout with a separate Git directory keeps its own store. The main worktree is the first entry of `git worktree list --porcelain -z`, run from the Working checkout. It is accepted only when it is not marked bare, its directory exists, it is neither the common directory nor inside it (Git reports the Git directory itself as the first entry for a separate Git directory or a submodule), its own top level is itself, and its Git directory is the repository's common directory. Paths are compared with the tool's existing filesystem identity check, so Windows drive-letter case, 8.3 short names and forward or back slashes do not decide the result. The candidate store directory passes the tool's existing link and reparse-point checks; an aliased store, such as a junction or symlink to another directory, is refused as it is today. When the main worktree cannot be accepted, the root state is `uncertain` with a reason naming what failed, reads report the Working checkout's own records as partial as they do today for an uncertain root, and every mutation is refused until the user confirms a root through the existing explicit-root recovery.
3. **Root report.** Every result's `root` object gains `checkout` (the Working checkout path) and `store` (the directory that holds `.feather/handoffs/`), and a `shared` flag that is true when they differ. Existing fields keep their meaning; `path` stays the store's directory, so callers that only read `path` still find the records.
4. **Observations stay in the Working checkout.** `snapshot`, `compare` and the save-time check of a baseline read sources and Git state from the Working checkout, never from the store's directory. A baseline captured in a linked worktree and compared from that same worktree reports no change when nothing changed there, whatever the main worktree's state.
5. **Unwritable store.** When writing to the shared store fails because the operating system or the session sandbox denies access, the result is `error` with code `store-unwritable`, naming the store path and saying that the session needs write access to it. The tool writes nothing in the Working checkout in its place, and leaves any file it already wrote recoverable as its write discipline describes. A tracking setup that fails after the record was saved is reported as the existing `tracking-failed` partial.
6. **Tracking state.** The Working checkout is in tracked mode when its `.gitignore` holds the tool's tracking marker, or when its index already tracks a file under `.feather/handoffs/`. The decision is made per run from the Working checkout and is reported as `root.tracking`, `tracked` or `untracked`. Ignore rules are written to the `.gitignore` of the checkout that holds the store, and a shared run writes no other file outside the store. A `track` choice in a shared run is refused, because tracking is chosen from the checkout whose records it should track. Detecting the tracking state runs the existing lazy-fetch guard first, and a detection failure makes the root `uncertain`. Switching tracking moves no records; records left in the previous store are reported under item 9.
7. **History lock.** Every operation that changes `history.md` or `archive/`, namely the archive step of a completed save, `archive`, `clear`, `seal` and `adopt`, holds `.feather/handoffs/.history.lock` from the history read it acts on until its last history write and source removal are verified. The lock is created exclusively and holds the creating process ID, host name and creation time. When the lock already exists, the operation changes nothing and returns `history-locked` with the lock's creation time, holder, age and version, the hash of its content. An age above ten minutes is also reported as `stale: true`. A completed save that cannot take the lock is saved as `partial` with `defer_history`, as when another writer holds history today, and a later `archive` retries it. The lock file is not a work file: `list`, `pending-unknown` checks and Handoff tidy never treat it as a record.
8. **Clearing a stale lock.** A new `unlock` command removes the lock only when its content is unchanged since the user saw it, as given by the version the `history-locked` result returned, and only when it is stale; otherwise it returns `conflict` or `not-stale` and changes nothing. The skill runs `unlock` only on the user's explicit decision after showing the lock's holder and age; it never runs it automatically.
9. **Other stores.** `list` also reports `other_stores`: one entry for each other checkout of the repository from `git worktree list` whose `.feather/handoffs/` exists, plus the shared store itself when the current run uses a checkout-local store. Each entry gives the checkout path, the work file names with their status, and whether `history.md` or `archive/` holds anything. A checkout that cannot be read, or that no longer exists, is listed with its reason and makes the result incomplete, so it never establishes that no pending work exists elsewhere. Work names are qualified by their checkout so that equal names in different stores stay distinct. `other_stores` lists only; it reads no record body beyond the status line.
10. **Adopt.** A new `adopt` command moves named work files, and optionally the history entries and sealed archives, of one other store reported under item 9 into the current store. The command takes the source checkout, the work names, whether to include history and archives, and the version of each source file read. The source must be a checkout listed by `git worktree list` of the same repository and must pass the same link checks as a store. For each work file, a target with the same name returns `conflict` and moves nothing for that file. Otherwise the target is created and read back, and only then is the source removed, after a reread shows the source unchanged. History entries are added under the history lock by completion identity, work title plus completion time: an identity already present with the same body is skipped, one present with a different body returns `conflict`, and the source history keeps every entry that was not added. A sealed archive whose name already exists in the target returns `conflict`. The skill runs `adopt` only after the user confirms the exact files and entries; it never moves records automatically.
11. **Environment and resume.** When `root.shared` is true, the handoff skill records the Working checkout path, branch and commit in the record's optional `環境：` field on create and on each update that changes them. On resume, a record whose `環境：` names another checkout is reported as belonging to that checkout: the four-part resume summary names it, main does not switch branches or checkouts to match it, and work that needs that checkout's files waits for the user. `環境：` is provenance, not evidence that uncommitted work in that checkout still exists.
12. **Skill text.** The handoff skill replaces "Cross-project/worktree synchronization is outside this skill" with the rules of items 1, 5, 6, 7, 8, 9, 10 and 11 in the user-facing form the skill uses, and its root rule names the Handoff store. The tool reference documents the new root fields, `store-unwritable`, `history-locked`, `unlock`, `other_stores` and `adopt`. Both READMEs replace the statement that there is no automatic worktree synchronization with what is now shared, what is not, and the sandbox requirement. The rules are written without naming a host's tools, so codex-feather can adopt them.
13. **Glossary and ADR.** CONTEXT.md gains Handoff store and Working checkout, and Active handoff refers to the Handoff store instead of the project's `.feather/handoffs/`. ADR 0018 records the choice of the main worktree over the Git common directory and over per-worktree records, and the choice of a lock over an external single-writer rule.
14. **Release.** The release is 0.31.0. Its update note says that the plugin update and a fresh session are enough, because no installed role definition or policy changes; that codex-feather sessions keep writing records in linked worktrees until codex-feather adopts the same runtime, and that `list` reports those records; and how to go back to 0.30.0, including that records written to the shared store stay readable there. The `docs/setup-validation.md` entry records the validation, including one rehearsal in a real linked worktree on Windows that confirms whether a desktop worktree session can write the main worktree's store.

## User Stories

1. As a user working in a desktop worktree session, I want my handoff saved somewhere that survives the worktree, so that cleaning up or archiving the session does not delete my progress.
2. As a user, I want a fresh session in the main checkout to list the work I recorded in a worktree, so that "no pending work" is never a false answer.
3. As a user running several worktree sessions at once, I want them all to see the same records, so that I can pick up any of them from anywhere.
4. As a user, I want completed work from every worktree in one history, so that I can search it in one place.
5. As a user who never uses worktrees, I want nothing to change, so that my existing records and habits keep working.
6. As a user with existing records in the main checkout, I want them used in place, so that I do not have to migrate anything.
7. As a user of a non-Git project, I want handoff to behave as before, so that the change only affects Git worktrees.
8. As a user who passes an explicit root, I want that root used exactly, so that I stay in control when discovery is wrong.
9. As a user, I want a source baseline captured in my worktree to compare against my worktree, so that the main checkout's state never makes my work look changed.
10. As a user, I want each record to show which checkout, branch and commit it came from, so that I know where its work lives.
11. As a user resuming a record from a different worktree, I want to be told it belongs elsewhere, so that I do not act on the wrong files.
12. As a user, I want main never to switch my branch or checkout to match a record, so that resuming stays safe.
13. As a user, I want to be told clearly when the session cannot write the shared store, so that I can grant access instead of losing records silently.
14. As a user, I want the tool never to fall back to writing inside the worktree, so that I do not end up with records that disappear later.
15. As a user, I want discovery failures, such as a bare repository or a missing main worktree, reported with a reason, so that I can confirm a root myself.
16. As a user who tracks handoff records in Git, I want tracked records to stay with their checkout, so that they keep belonging to their branch.
17. As a user, I want to see whether the current run uses tracked or untracked mode, so that I know where records go.
18. As a user who switches tracking, I want records in the old location reported rather than silently moved, so that nothing is lost or duplicated.
19. As a user with two sessions finishing work at the same moment, I want both completions to reach history, so that no completed record is lost.
20. As a user, I want a completion that finds history locked to be kept and retried later, so that a busy history never loses my record.
21. As a user, I want a lock left by a crashed session reported with its holder and age, so that I can decide whether to clear it.
22. As a user, I want a stale lock cleared only when I say so, so that a live writer is never interrupted.
23. As a user, I want the lock file never to appear as a work record, so that listings and tidy stay clean.
24. As a user upgrading from 0.30.0, I want records my worktrees already wrote to be listed, so that I find them before those worktrees are removed.
25. As a user, I want leftover records named with their checkout, so that two records with the same name do not get confused.
26. As a user, I want an unreadable or missing worktree reported as incomplete, so that I never assume nothing is left there.
27. As a user, I want to move chosen leftover records into the shared store, so that they are safe from worktree cleanup.
28. As a user, I want a move to stop when a record with the same name exists, so that nothing is overwritten.
29. As a user, I want a moved record written and verified before its source is removed, so that a failed move never loses it.
30. As a user, I want leftover history entries merged without duplicates, so that history stays exact.
31. As a user, I want history entries that conflict in content to be reported rather than merged, so that I decide which one is right.
32. As a user, I want nothing moved without my confirmation, so that adopting records is always my choice.
33. As a user mixing Claude Code and Codex, I want to be told that codex-feather still writes worktree-local records until it adopts the change, so that I know where to look.
34. As a maintainer, I want the store choice and the lock recorded in an ADR, so that later changes know why the main worktree was chosen.
35. As a maintainer, I want the rules written without naming a host's tools, so that codex-feather can adopt them unchanged.
36. As a maintainer, I want the release validated in a real Windows worktree, so that the sandbox assumption is checked rather than inferred.

## Implementation Decisions

- **Store and checkout are separate.** The store object the tool builds today couples the project root and the record directory. It splits into the Working checkout, used for Git observations, baselines and tracking detection, and the store directory, used for every record, history, archive and lock path. The root guard that refuses writes under an uncertain root applies to both.
- **Main worktree resolver.** A new resolver in the storage module runs the two Git commands of Acceptance item 2 through the tool's existing Git runner, which already scrubs inherited Git environment variables, and parses NUL-delimited porcelain output. It reuses the existing identity comparison and link checks rather than resolving paths by string. It does not reuse the Claude memory lookup's prose, which is read-only guidance with different failure handling.
- **Existing containment check.** Root discovery today rejects a Git root that does not contain the requested directory. That check stays for the Working checkout. The store is validated separately by the resolver, because a main worktree is a sibling of a linked worktree, not an ancestor.
- **No fallback.** A denied write to the store becomes `store-unwritable` and never redirects to the Working checkout. A fallback would recreate the loss this spec fixes.
- **Lock design.** The lock is one file in the store directory, created with exclusive create, written and flushed before the history read, and removed after the final verification, including on handled errors. A crash leaves it in place, which is why it is reported rather than broken. Ten minutes is far above the expected hold time of a history mutation and well below a session's typical idle time. Work-file writes take no lock: one writer per work item stays the rule, and rereads still detect conflicts there.
- **Interfaces.** New results are `store-unwritable`, `history-locked`, `not-stale` and the `other_stores` list. New commands are `unlock`, which takes the lock version, and `adopt`, which takes the source checkout, names, include flags and versions. Existing commands keep their inputs and their existing result codes.
- **Tracking detection** reuses the tracking module's marker and index checks, evaluated against the Working checkout before the store is chosen.
- **Skill and docs.** The skill text, tool reference, READMEs, CONTEXT.md and ADR change as Acceptance items 12 to 14 state. The delegation skill is unchanged; its Active handoff lookup follows the store through the glossary's definition.

## Testing Decisions

- **What a good test is.** A test drives the handoff tool the way the skill does, through its CLI with `--project` and JSON on stdin and stdout, and asserts on results and on the files left on disk. It never calls the resolver or the lock helpers directly.
- **Primary seam: the CLI against real repositories.** The tests follow the existing tool tests, which run the tool as a subprocess. They build a real Git repository in a temporary directory and add linked worktrees with `git worktree add`. They cover:
  - store selection for the main worktree, a linked worktree, a non-Git project, `--exact-root` and tracked mode;
  - list, read, create, update, archive, clear and seal from a linked worktree landing in the main worktree's store;
  - snapshot and compare from a linked worktree reading that worktree's sources while the main worktree has unrelated changes;
  - discovery failure for a bare main entry, a moved or deleted main worktree, a first entry that is the Git directory itself and a store reached through a directory link;
  - a store made read-only, returning `store-unwritable` with the Working checkout unchanged;
  - a pre-created lock file making every history mutation return `history-locked` and leaving every file byte-identical, and a completed save under a lock returning `defer_history`;
  - `unlock` refusing a fresh or changed lock and removing a stale, unchanged one;
  - `other_stores` reporting leftover stores, including a worktree directory deleted behind Git's back;
  - `adopt` moving files, skipping identical history entries, and stopping on a name conflict and on a history body conflict without changing either store.
- **Prior art.** Use the existing tool tests for subprocess invocation and on-disk snapshots. Use the root tests for uncertain-root and refused-write assertions. Use the Git helper and Git lookup tests for building real repositories with a scrubbed Git environment. Use the link tests for junction and symlink fixtures on Windows. Use the archive and mutation tests for history results.
- **Secondary seam: documentation rules.** Following the existing documentation tests, which pin whole sentences, the tests pin the skill's new rules, the tool reference's new results and commands, the README sentences that replace the old worktree statement, and the glossary entries.
- **Platform.** Every test runs on Windows and POSIX. The read-only store test uses a permission change on POSIX and a read-only attribute or denied ACL on Windows, and it is skipped with a stated reason where the platform cannot deny the write.

## Out of Scope

- Delegation's Dispatch records under `.feather/dispatch/`. They have the same loss problem, but review state assumes one working tree, so they need their own decision.
- Changing codex-feather. This spec only keeps the rules host-neutral and tells the user how mixed use behaves until codex-feather adopts the change.
- Storing records in the Git common directory or anywhere outside a working tree.
- Automatic migration of leftover records, and any migration of tracked records.
- A lock for work-file writes or for `.gitignore` updates.
- Protecting the main worktree's store from `git clean -x`, manual deletion or the main worktree's own removal.
- Recovering records from a worktree that was already removed.

## Further Notes

- The decisions in this spec come from a design discussion and a Codex second opinion (gpt-6-astra, effort high). That review found three problems in the first proposal: redirecting the root would have moved baselines to the wrong checkout, a sandboxed worktree session may be unable to write the main checkout, and version checks alone let two concurrent history writers lose a completion. Acceptance items 4, 5 and 7 answer them.
- Whether a Claude Code desktop worktree session on Windows can write the main worktree's directory is inferred, not observed. Acceptance item 14's rehearsal settles it. If it cannot, `store-unwritable` keeps the failure visible, and the Git common directory alternative recorded in ADR 0018 is the next option to weigh.
- At the time of writing, this repository's own records are all in the main checkout, and its one linked worktree holds none, so upgrading here needs no `adopt`.
