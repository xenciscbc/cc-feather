---
name: leases
description: "Checkout leases: take, return and list cooperative records of which session uses which checkout (the main worktree or a linked worktree) of a Git repository."
---

# Feather Checkout leases

A Checkout lease is a cooperative record that one session is using one checkout of a repository to change it. It states a claim of use and when it began, never proof that its holder is still running, and taking one never authorises changing, resetting or removing what the checkout already holds.

## Tool

Resolve the bundled launcher relative to this loaded skill: `scripts/leases.py`. When installed as a plugin, its path is `${CLAUDE_PLUGIN_ROOT}/skills/leases/scripts/leases.py`; use the actual loaded skill directory if the variable is unavailable. The tool needs Python 3.11+ and the handoff skill beside this one (`../handoff/scripts`), whose helpers it imports; keep the plugin's `skills/` directory together. Pass any checkout of the repository with `--project`; `--exact-root` uses that path without Git top-level discovery. Every checkout reads and writes the same leases, whatever its handoff tracking choice or explicit root.

Each command prints one JSON object. A handled result exits 0, whether its `status` is `ok`, `held`, `changed-hands`, `busy` or `unknown`; status `error` exits 2.

- `acquire [--checkout <dir>] --session <label> --purpose <text> [--runtime <name>]` takes the lease on the checkout whose top-level directory is `<dir>` (default: the project's root). On a free checkout it returns `ok` with the new lease and its `lease_id`. A held lease returns `held` with its holder, purpose, start time, last reported activity and age, and acquires nothing; an unreadable lease returns `unknown`.
- `release [--checkout <dir>] --lease-id <id>` returns the lease only when it carries that `lease_id`; otherwise it returns `changed-hands` and changes nothing.
- `list` reports every worktree `git worktree list` registers, the main worktree first, with its path, branch or detached HEAD and lease state: `held` with the lease, `absent` ("no registered use"), or `unknown` with the reason.

Acquire and release change a lease inside a short critical section. One that is already held returns `busy` with its holder and age at once; it is never waited on or broken.

## Records

Leases live in `.feather/leases/` under the main worktree, one `<key>.json` per checkout, keyed by Git's per-worktree administration identity, with the reserved key `.main` for the main worktree; the checkout's path is kept for display only. The directory ignores itself with its own `.gitignore` holding `*`. When the main worktree or that directory cannot be established or written, the tool reports `unknown` or an error and never stores a lease elsewhere. A lease records its schema version, the checkout key and display path, a `lease_id` that differs on every acquisition, the session label, the host and runtime, the zoned start time, the purpose and the zoned last reported activity; its `diagnostic_pid` is the short-lived tool process's and never shows that the holder is alive. A held lease is never reclaimed automatically. Lease records are trusted like other `.feather/` records.
