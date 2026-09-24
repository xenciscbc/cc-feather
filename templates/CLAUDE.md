<!-- cc-feather:begin -->
# Feather delegation for Claude Code

Apply to the main session when the managed roles are available. Only main delegates; children are leaves. Main owns decisions, integration and acceptance. Delegation grants no additional authority.

## Dispatch

Keep small or tightly coupled work with main. Delegate independent work through the named native roles: scout for facts, managed Explore for broad discovery, analyst for analysis/review, mech-executor for specified repetition, executor for implementation judgment, and security-executor for security-boundary implementation.

Give each child the goal, context, scope, constraints and acceptance checks. Assign exclusive write ownership; isolate checkout conflicts or serialize writers, and wait for the owner to stop before taking over. Preserve others' changes.

Use configured role models and effort. For task/session overrides, persistent changes or uncertain bindings, read cc-feather:model before dispatch or configuration changes. Main-only preferences do not override children. Distinguish configured settings from observed execution.

For requested security analysis or material security-boundary changes, assign analyst a read-only brief identifying boundaries and evidence questions. Main evaluates findings before authorized fixes.

## Plan review

Automatic plan review mode: {{review_mode}}

Task/session choices override the saved mode. Explicit plan-review requests apply in either mode. In auto, obtain analyst review in fresh native context before material security-boundary changes, data migrations, irreversible operations or complex cross-module changes. In off, review only on request. Supply a stable plan with scope, ownership, dependencies, acceptance checks and relevant rollback.

Allow two automatic calls per logical plan, including failures. Revise material blockers before the second call; never resubmit unchanged. Track plan identity, count, verdicts and blockers in the task and any active handoff; reconstruct them before resuming. Mode/session/reviewer changes do not reset the count or clear blockers. When review is required, execute only after READY and within existing authorization; after two calls without READY, stop dependent implementation. Further review requires an explicit user request. Follow cc-feather:auto-on or cc-feather:auto-off for mode changes.

## Accept and recover

Verify returned evidence and acceptance checks against the brief and pre-dispatch state, including unchanged sources for read-only roles. Preserve unexpected changes. Retry the same operation at most once, only for a recoverable temporary cause; otherwise main resolves or reports the blocker. A child's completion does not establish whole-task completion.

For installation, updates or removal, read and follow cc-feather:setup.
<!-- cc-feather:end -->
