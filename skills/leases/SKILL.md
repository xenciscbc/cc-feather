---
name: leases
description: "Checkout leases: take, renew, take over, return and list cooperative records of which session uses which checkout (the main worktree or a linked worktree) of a Git repository, and the main Agent's rules for when to take, renew and return them."
---

# Feather Checkout leases

A Checkout lease is a cooperative record that one session is using one checkout of a repository to change it. It states a claim of use and when it began, never proof that its holder is still running, and taking one never authorises changing, resetting or removing what the checkout already holds.

## Tool

Resolve the bundled launcher relative to this loaded skill: `scripts/leases.py`. When installed as a plugin, its path is `${CLAUDE_PLUGIN_ROOT}/skills/leases/scripts/leases.py`; use the actual loaded skill directory if the variable is unavailable. The tool needs Python 3.11+ and the handoff skill beside this one (`../handoff/scripts`), whose helpers it imports; keep the plugin's `skills/` directory together. Pass any checkout of the repository with `--project`; `--exact-root` uses that path without Git top-level discovery. Every checkout reads and writes the same leases, whatever its handoff tracking choice or explicit root.

Each command prints one JSON object. A handled result exits 0, whether its `status` is `ok`, `held`, `locked`, `refused`, `changed`, `changed-hands`, `busy` or `unknown`; status `error` exits 2.

- `acquire [--checkout <dir>] --session <label> --purpose <text> [--runtime <name>] [--accept-session-lock <reason>]` takes the lease on the checkout whose top-level directory is `<dir>` (default: the project's root). On a free checkout it returns `ok` with the new lease and its `lease_id`. A held lease returns `held` with its holder, purpose, start time, last reported activity and age, and acquires nothing; an unreadable lease returns `unknown`.
- `renew [--checkout <dir>] --lease-id <id> [--purpose <text>]` records the last reported activity now and, when given, the new purpose, only when the lease carries that `lease_id`; it returns `ok` with the lease and its new `version`. Otherwise, or when the checkout has no lease, it returns `changed-hands` with the current lease (or none) and changes nothing; renew never acquires and never changes a lock.
- `release [--checkout <dir>] --lease-id <id> [--park [--continue-in <dir>]]` returns the lease only when it carries that `lease_id`; otherwise it returns `changed-hands` and changes nothing.
- `--park` parks the worktree before the lease is returned, inside the same critical section and only with the holder's own `lease_id` (with another one nothing is parked or changed). It detaches the HEAD of a linked worktree that is on a branch, is clean (no uncommitted or untracked changes) and whose branch commit the local default branch contains, at the local default branch's commit; otherwise, when `--continue-in <dir>` names the checkout the work continues in and its branch contains it, at that branch's commit. The tool checks the containment itself. The result's `park` is `parked` true with the `branch`, the commit it was `detached_at`, the ref it was `contained_in` and its `target` (`default-branch` or `continuing-checkout`), or `parked` false with a `condition` and the `reason`: `main-worktree`, `no-branch`, `dirty`, `default-branch-unknown` (parking is skipped), `local-default-branch` (the default branch exists only on the remote, or only the remote one contains the branch: the local default branch may need creating or updating), `not-contained`, `continuing-checkout` (the named checkout is the returned one or is not on a branch), `state-unknown`, `detach-failed` (Git refused, for example because an ignored file would be overwritten) or `not-released`. When a condition fails the worktree is left as it is and the lease is still returned. Parking never deletes a branch or a worktree, never resets or cleans files and never overwrites an ignored file; a parked worktree's branch can then be deleted by the user.
- `take-over [--checkout <dir>] --version <version> --session <label> --purpose <text> [--runtime <name>]` takes over, on the user's choice, a lease the user judges left behind. `<version>` is the lease's `version` the user was shown, as `list` or a refused acquire returned it. While the lease is still that version, it writes a new lease with a new `lease_id` and start time and returns `ok` with it, its `version` and the old lease as `previous`. A changed lease returns `changed` with the current lease and its version, and a checkout without a lease returns `changed` with none; nothing is taken over or acquired. A worktree whose directory is missing or that Git marks prunable is `refused`.
- After a takeover, the old holder's renew and release return `changed-hands` and its take-over with the old version returns `changed`; none of them overwrites or returns the new lease. A session that finds its lease changed hands stops using that checkout and reports.
- `list` reports every worktree `git worktree list` registers, the main worktree first, with its path, branch or detached HEAD and lease state: `held` with the lease, `absent` ("no registered use"), or `unknown` with the reason, whether its directory exists, whether Git marks it prunable, and its `lock` (below). Next to each lease it shows the work left in the checkout, each part `known` with its facts or `unknown` with the reason:
  - `changes`: the uncommitted changes (`status` as `git status --porcelain` writes it, and `path`) and the untracked files, with their counts (at most 100 paths of each are listed; `truncated` says so).
  - `commits`: how many commits HEAD is `ahead` of and `behind` the default branch, and which ref it was `compared_with`: the local default branch when it exists, otherwise the remote one (`kind` `local` or `remote`). The result's `default_branch` is the branch `origin/HEAD` names; without it, the one of `main` and `master` that exists when exactly one does; otherwise it is unknown, and so is every checkout's `commits`.
  - `handoff_records`: the handoff records whose environment field names the checkout's whole path (the longest checkout path a record names wins), read through the handoff tool's own `list` from the main worktree and, for each store it reports under `other_stores`, through `list` with that checkout as explicit root. An uncertain root or an unreadable main worktree's store makes this unknown for every checkout; a failed enumeration of the other checkouts, for every linked worktree; an unreadable store of one checkout or its missing directory, for that checkout only.
- The listing reports facts only: it never calls a checkout usable, free or reusable, and a checkout without a lease has "no registered use". `complete` is false when any part, or any orphan lease, could not be established or removed.
- Orphan leases: `list` and `acquire` remove, each inside its own critical section, a lease whose checkout `git worktree list` no longer reports, and report each one under `orphans` (`removed` with the lease, or kept with the reason, or `busy`). An unreadable orphan lease is kept. While any checkout's key is unknown, no lease is removed and `orphans` is unknown. A lease whose worktree Git marks prunable, or whose directory is missing while Git still registers it, is kept and listed as unknown.

Acquire, renew, release, take-over and the re-locking below change a lease and its lock inside a short critical section, never by holding a lock for a whole session. One that is already held returns `busy` with its holder and age at once; it is never waited on or broken.

## Records

Leases live in `.feather/leases/` under the main worktree, one `<key>.json` per checkout, keyed by Git's per-worktree administration identity, with the reserved key `.main` for the main worktree; the checkout's path is kept for display only. The directory ignores itself with its own `.gitignore` holding `*`. When the main worktree or that directory cannot be established or written, the tool reports `unknown` or an error and never stores a lease elsewhere. A lease records its schema version, the checkout key and display path, a `lease_id` that differs on every acquisition, the session label, the host and runtime, the zoned start time, the purpose and the zoned last reported activity; its `diagnostic_pid` is the short-lived tool process's and never shows that the holder is alive. A held lease is never reclaimed automatically: no age or time threshold reclaims it, and the tool offers no automatic takeover. Lease records are trusted like other `.feather/` records.

## Git worktree locks

A held lease on a linked worktree is protected by a Git worktree lock, so `git worktree prune`, a plain `git worktree remove` and Claude Code's cleanup leave the worktree alone and tools that do not read leases see it as in use. Git cannot lock the main worktree; its lease has no lock (`lock.state` `not-lockable`). The lease stays the authority; the lock only protects it.

- The lease's own lock has the reason `cc-feather lease <lease_id>`. Acquire on an unlocked linked worktree creates the lease and then sets that lock; when locking fails, the lease is withdrawn and acquire returns error `lock-failed`. A worktree whose directory is missing or that Git marks prunable is not acquired: `refused` with code `directory-missing` or `prunable`; when it has a lease, the result carries that lease and its `version`, and the lease is kept as it is.
- `--accept-session-lock <reason>` attests the Claude Code session lock (`claude session <name> (pid N)`) the caller observed right after this session itself created the worktree. Acquire accepts that lock in place of its own only when the worktree's current reason is exactly the attested one; it records it in the lease as `accepted_lock` and never changes the lock. A reason that is not a session lock reason is an input error. Do not attest a lock found on a worktree only entered or reused: it counts as another holder's.
- Any other lock blocks acquisition: `locked` with the lock and its reason, and nothing is acquired; treat it like a held lease.
- Release, after any parking, removes the lock only when its reason names the releasing lease, then removes the lease; an accepted session lock and every other lock stay, and the result says so under `lock`.
- Take over replaces only a lock whose reason names the old lease with one naming the new lease (`lock.replaced` gives the old reason), and locks a worktree that has no lock at all for the new lease. Any other lock, an accepted Claude Code session lock included, stays as it is and the result says so (`lock.kept`, with the lock's `previous_holder` for the old lease); the new lease does not accept it. When the new lease cannot be locked, `lock.lock_failed` says why and the next list or acquire locks it again.
- List and acquire lock a held lease's linked worktree again with the lease's own reason when it has no lock at all, and report `relocked`. They skip a worktree whose directory is missing or that Git marks prunable: its lease is shown `unknown` with the lease kept, and its lock `unlocked` with `unprotected`.
- Each lock is shown with its reason as written, its parsed process ID (`pid`, display only; whether the process exists is never probed) and its `holder`: `lease` (the lease's own), `accepted-session`, `cc-feather` (a cc-feather lock that does not name the checkout's lease, reported as a `mismatch`) or `other`.
- The tool never removes or changes a lock whose reason does not name one of its leases.

## Main Agent rules

These rules apply while the installed guidance or the user asks the main Agent to keep Checkout leases. `cc-feather:setup` installs that guidance as its `leases` component. Only the main Agent takes, renews, takes over and returns leases. Pass `--session` a label naming this session and `--purpose` the current ticket or task, and keep the returned `lease_id` for renew and release.

### Taking a lease

- The main Agent takes a lease on a checkout when it starts implementing the first Claim of a Plan there, at the first change of Unplanned work there, and before it runs a writing test or a review that needs a stable checkout there.
- Reading a checkout takes no lease. Opening or entering a worktree (`EnterWorktree` by name or path, `claude --worktree`) is not taking its lease, and neither is starting a session in the main worktree's directory.
- Writing cc-feather's own records under the main worktree's `.feather/` (leases, handoff records, Dispatch records) is not changing a checkout and needs no lease.
- Merging into a branch inside the main worktree changes it, so the main Agent takes the main worktree's lease for the merge and returns it afterwards; landing by a push or a pull request does not touch the main worktree and needs none.
- Taking a lease never authorises changing, resetting or removing what the checkout already holds.

### Locks

- A held lease on a linked worktree is protected by its own lock or by the session lock of a worktree the session itself created.
- Right after creating a worktree itself (`EnterWorktree` by name, or `claude --worktree` with a new name), the main Agent reads that worktree's lock reason from `git worktree list --porcelain -z` and passes exactly that reason with `--accept-session-lock`; without `-z` Git quotes a reason with special characters and the reason no longer matches.
- A lock found on a worktree the session only entered or reused (`EnterWorktree` by path, `claude --worktree` with an existing name) counts as another holder's: the main Agent never attests it, and acquire returns `locked`.
- A lockless held lease is locked again with its own lock by `list` and `acquire`.
- Only the lease's own lock is ever removed: an accepted session lock and every other lock stay. After a takeover, a Claude Code session lock the old lease had accepted stays and counts as another holder's lock.

### Serial and parallel work

- A serial Plan holds one lease in its checkout, and its purpose follows the ticket being worked on: the main Agent renews it with `--purpose` when the ticket changes.
- Parallel Claims hold one lease per worktree. Once a parallel worktree's work is merged back and the worktree is no longer used, the main Agent returns its lease after parking: `release --park`, with `--continue-in` naming the checkout the work continues in when the branch was merged there rather than into the default branch.
- Subagents never take, renew or return leases. Delegated work runs under the main Agent's lease, and the main Agent decides which checkout each Assignment uses. A subagent's isolated worktree needs no lease while the subagent runs under Claude Code's agent lock; when it is kept with changes, the main Agent takes a lease on it, with the lease's own lock, until the changes are integrated.

### Renewing and returning

- The main Agent renews its lease at milestones, at blockers, before stopping to wait for the user and at completion, whether or not a handoff is active.
- It returns a lease when it stops using the checkout; completing a handoff record does not return it. Returning a lease never resets, cleans or switches the checkout.
- Parking detaches a linked worktree's HEAD only when the worktree is clean (no uncommitted or untracked changes) and its branch is contained in the local default branch, or in the branch of the checkout `--continue-in` names; otherwise the worktree stays as it is, the reason is reported and the lease is still returned. Parking never applies to the main worktree and never deletes a branch or a worktree.

### When a lease cannot be taken

- When acquire returns `held` or `locked`, the main Agent stops and shows the holder, purpose, start time, last reported activity and age, or the lock and its reason, and the user chooses: work in the main worktree, use an idle worktree, open a new worktree, or take over a lease the user judges left behind.
- No lease is taken over automatically: the main Agent runs `take-over` only on the user's choice, with the `version` the user was shown. Last reported activity is the activity the holder reported, not proof that the holder is still running, and no age makes a lease left behind.
- On `refused`, `busy` or `unknown` the main Agent acquires nothing, reports the result and does not change that checkout until it holds the lease or the user decides otherwise.
- A session that finds on renew or release that its lease changed hands (`changed-hands`) stops using that checkout and reports.

### Reusing a parked worktree

- A parked commit can be far behind, so the main Agent starts new work in a reused parked worktree on a new branch from the latest default branch (the remote's default branch when one exists), never from the parked commit itself, unless the user names another base.
- The listing (`/cc-feather:worktrees`) reports facts and never calls a checkout usable; which idle worktree to use is the user's choice.

### Cooperative limits

A lease is cooperative: it binds only sessions that follow these rules. It does not stop, detect or manage another session's processes, and it does not keep a person or a tool that ignores leases out of a checkout. A Git worktree lock only keeps `git worktree prune`, a plain `git worktree remove` and Claude Code's cleanup away from a leased worktree. One checkout shared between Windows and WSL, or between machines, is not covered.
