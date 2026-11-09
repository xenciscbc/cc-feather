<!-- cc-feather:leases:begin -->
# Feather checkout leases

Before changing a checkout of a Git repository, take a Checkout lease on it, then renew and return it, following cc-feather:leases. If unavailable, report the limitation.

Take the lease when starting to implement the first Claim of a Plan in a checkout, at the first change of Unplanned work, and before a writing test or a review that needs a stable checkout. Reading a checkout, opening or entering a worktree, and writing cc-feather's own records under `.feather/` take none. Renew it at milestones, blockers, before stopping to wait for the user and at completion, whether or not a handoff is active, and return it when the session stops using the checkout. When a lease cannot be taken, stop and let the user choose; never take a lease over automatically.

Only the main Agent takes, renews and returns leases. Subagents never do; delegated work runs under the main Agent's lease.
<!-- cc-feather:leases:end -->
