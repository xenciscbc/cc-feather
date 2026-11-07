# Linked worktrees share the main worktree's Handoff store

Until 0.30.0 the handoff tool kept records under `.feather/handoffs/` of the checkout it was run from. A linked worktree therefore had its own records, history and sealed archives, and three problems followed: `git worktree remove` without `--force` deletes ignored files without a warning, so cleaning up or archiving a worktree session deleted its handoffs; a record written in one worktree could not be seen from the main checkout or another worktree, so a fresh session there listed no pending work; and each worktree kept its own history. Desktop worktree sessions made all three common.

The user decided (2026-11-05, after a design discussion and a Codex second opinion; the [spec](../specs/handoff-worktree-store.md) carries the acceptance and its security invariants):

- **The main worktree holds the store.** When the Working checkout is a linked worktree of a non-bare repository and does not track its records, the Handoff store is `.feather/handoffs/` under the repository's main worktree. The main worktree itself, a non-Git project, an explicit root and a checkout that tracks its records keep the store under the Working checkout, so nothing changes for a user who never uses worktrees.
- **The checkout and the store are separate.** Sources, baselines, tracking detection and a record's environment describe the Working checkout; only records, history, archives and the lock live in the store.
- **No fallback.** A denied write to the shared store is reported as `store-unwritable` and never redirected into the worktree, since a fallback would recreate the loss this fixes.
- **A history lock.** Every history mutation holds `.feather/handoffs/.history.lock`, created exclusively, from the history read it acts on until its last write is verified. A held lock returns `history-locked` with its holder and age, and only the user's decision clears a stale one with `unlock`.
- **Leftover records are reported, then moved on confirmation.** `list` reports records in other checkouts' stores, and `adopt` moves only what the user confirms, writing and verifying each target before removing its source.

## Considered Options

- **The Git common directory** (for example `.git/feather/handoffs/`): it survives every worktree and is shared by all of them, but it is hidden from the user and outside every working tree, where tools and session sandboxes expect to write. It stays the next option to weigh if a sandboxed worktree session cannot write the main worktree.
- **Per-worktree records with synchronization**: each worktree keeps its own store and the tool copies or merges between them. Records would still be deleted with their worktree before a synchronization ran, and merging concurrent histories needs the same lock this decision adds, plus conflict rules for work files.
- **An external single-writer rule instead of a lock**: the skill told the user to keep one history writer across sessions. With several worktree sessions sharing one history, a version check alone lets two completions read the same history and one overwrite the other; a rule the sessions cannot see does not prevent it.

## Consequences

A worktree session needs write access to the main worktree's directory. Whether a Claude Code desktop worktree session on Windows has it was inferred when this was decided; the rehearsal recorded under 0.31.0 in [setup validation](../setup-validation.md#0310-handoff-worktree-store) observed that it does. The lock covers history mutations only: work-file writes take no lock, and one writer per work item stays the rule. A crash leaves the lock in place, which is reported rather than broken. Records written by 0.30.0 or by codex-feather inside a linked worktree are not moved automatically; they are listed, and the user moves them with `adopt`. The main worktree's store is not protected from `git clean -x`, manual deletion or the main worktree's own removal, and Delegation's Dispatch records under `.feather/dispatch/` keep their per-checkout location.
