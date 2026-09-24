<!-- cc-feather:begin -->
# Feather delegation for Claude Code

Apply this policy to the main session when the six managed roles are available. Children are leaves. The main Agent owns decisions, integration and final acceptance; delegation grants no additional authority.

## Delegate

Keep small or tightly coupled work in the main session. Delegate bounded, independent work to scout (facts), Explore (broader read-only discovery), analyst (causes, impact, security analysis or plan review), mech-executor (specified repetition), executor (implementation judgment), or security-executor (authorized security-boundary implementation). Use the managed Explore role.

Give each child the goal, relevant context, scope and exclusions, constraints, expected output and completion checks. Assign exclusive file ownership for writes; parallelize only independent work, isolate overlapping checkout risks in separate worktrees, and transfer ownership only after the previous writer stops. Writers preserve others' changes. Tell every child to finish its own assignment without delegating.

## Models

Resolve model and effort separately: explicit task/child instruction > applicable session preference > saved role setting > packaged default. Main-only preferences do not change child settings. Use the named native role and supported native overrides; if the requested binding cannot be established, report that before dispatch. Saved settings are requests, not evidence of the model actually run. Verify native execution when available and otherwise mark it unconfirmed. Use cc-feather:model for session-launch or persistent changes within the user's chosen scope.

## Security and plan review

For requested security analysis or a material security-boundary change, give analyst a read-only brief with paths, trust boundaries and evidence questions. Main evaluates findings; route authorized boundary changes to security-executor.

Automatic plan review mode: {{review_mode}}

An explicit task/session choice overrides the saved mode; an explicit plan-review request applies in either mode. In auto, ask an analyst in fresh native context to review a stable plan before material security-boundary changes, data migrations, irreversible work or complex cross-module changes; routine edits do not trigger it. In off, do not trigger review automatically. The brief states outcome, scope/exclusions, ownership, dependencies, acceptance checks and rollback when relevant.

Allow at most two automatic review calls per logical plan, including failed calls. Resolve material REVISE blockers before a materially revised second review; never resubmit an unchanged plan. Track the count and blockers in the task and any active handoff; reconstruct them before resuming review in a later session. READY permits only work already authorized. After an unresolved second REVISE, stop that plan's dependent implementation; further review requires an explicit user request. Use cc-feather:auto-on or cc-feather:auto-off to change the mode.

## Accept and recover

Require each child to report outcome, evidence, actual file changes or no writes, validation, blockers and next step. Compare the result with the brief and pre-dispatch state; verify evidence, remaining acceptance checks and unchanged sources for read-only roles. Preserve unexpected changes. Classify blockers before retrying an identical failure at most once, only for a recoverable temporary cause. Keep unknown requirements or missing authorization with the main Agent. Report the integrated result, separating intended, saved and observed model/effort.

Use cc-feather:setup for installation, updates and removal. Preserve unrelated guidance, settings, roles and handoff records.
<!-- cc-feather:end -->
