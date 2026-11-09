---
name: worktrees
description: "List every checkout of this repository with its Checkout lease, Git worktree lock and the work left in it. Not read-only: the listing locks a lockless held lease again and removes orphan leases."
disable-model-invocation: true
---

# worktrees

List the checkouts of the current repository with [the lease tool](../leases/SKILL.md#tool)'s `list` command; this command adds no rules of its own.

- The listing is not read-only: it locks a held lease's linked worktree again when that worktree has no lock, and it removes orphan leases, whose checkout Git no longer registers. Report each worktree it locked again (`relocked`) and each orphan lease it removed or kept.
- It takes, renews, returns and takes over no lease, and it never parks, resets, cleans, switches or removes a checkout.
- For each checkout, main worktree first, show its path, branch or detached HEAD, whether its directory exists or Git marks it prunable, and its lease: for a held lease the session, purpose, start time, last reported activity and age. Show its lock with the reason as written and its holder, its uncommitted and untracked changes, its commits ahead of and behind the default branch with the ref compared, and the handoff records that name it. Show each part that is unknown with its reason.
- The listing reports facts and never calls a checkout usable, free or reusable; a checkout without a lease has no registered use. Last reported activity is reported activity, not liveness.
- When `complete` is false, say which parts could not be established; an incomplete listing cannot show that no other checkout is in use.
