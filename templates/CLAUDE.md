<!-- cc-feather:begin -->
# Feather delegation for Claude Code

Apply to the main session only when the installed roles are available. Children complete their assigned work as leaves and ignore main-session dispatch rules. This policy does not grant new authorization or require delegation for every task. The main Agent owns understanding, decisions, integration and final acceptance.

## Routing and ownership

Use native `scout` for bounded factual lookup, `Explore` for broader read-only discovery, `analyst` for causal/impact analysis, `mech-executor` for fully specified repetition, `executor` for scoped implementation with local engineering judgment, and `security-executor` for security-sensitive implementation. Both scout and Explore have explicit inexpensive model defaults; use the managed Explore definition, not an assumed built-in default. Keep small tasks and tightly coupled evolving diagnosis in the main session. Delegate only an independent responsibility with clear benefit.

Before dispatch, provide the objective, relevant context, exclusive file ownership for writes, scope/non-goals, constraints, expected output, completion criteria and one-level delegation rule. Explain the chosen role briefly. Parallelize independent work only; use separate worktrees for overlapping checkout risks, or serialize writers. Tell writers they are not alone and must preserve others' changes. Wait for the owner to stop or finish before taking over its files. Never launch another child merely to repeat a blocked operation unchanged.

## Model and effort precedence

Resolve model and effort independently: explicit instruction for this task/child > applicable session preference > saved role configuration > packaged default. A request such as “use Sonnet to review this plan” changes that review's model while preserving the analyst role and its tools; omitted effort retains the resolved analyst effort. A preference only for the main model does not change child settings. A single task override does not modify permanent configuration. Preserve exact user-specified IDs and scope; ask only when the requested model or scope cannot be established.

For ordinary dispatch, use the named native role and its model/effort frontmatter; do not accidentally inherit the main model. Apply explicit task/session overrides through supported native parameters. An Agent `model` parameter overrides frontmatter unless a force setting or provider restriction supersedes it. Effort overrides require an actual supported native binding, not a sentence in the prompt. If the current tool lacks one, explain the limitation before dispatch and use cc-feather:model's supported session-launch or permanent configuration workflow only within the user's chosen scope. Never silently substitute a model or drop the named role to retain a convenient context mode.

Check known global force settings, managed/CLI/nested role overrides and provider model restrictions when they affect routing. Saved values describe requested configuration, not proof of the live model. Use actual native execution evidence (for example Claude /tasks model/effort display) when available; otherwise mark execution unconfirmed. Do not call a configuration check proof that all exploration will use Haiku.

## Security analysis

Use the same analyst role with an explicit security brief when the user requests a security review or a change materially affects a concrete security boundary. Specify paths, trust boundaries, risk questions, evidence requirements and excluded scope. Keep analysis read-only; distinguish confirmed issues, hypotheses and uncovered surfaces. Main adjudicates findings before delegating authorized fixes. Security analysis and plan review are separate tasks; one does not automatically require the other. Analyst defaults to opus/high; security-sensitive implementation routes to security-executor (opus/high), while ordinary executor work remains opus/medium. Route by the actual security boundary affected, not merely a filename or a security-related word. Explicit task model/effort requests still take precedence, and high effort is not a security guarantee.

## Pre-implementation plan review

Automatic plan review mode: {{review_mode}}

Use cc-feather:auto-on or cc-feather:auto-off to toggle automatic review. No argument (or session) sets only this session; project/user persists in the selected existing installation. Follow the command skill for scope and ownership checks. An explicit task/session choice overrides the saved mode above. In auto mode, trigger a fresh analyst plan review for material security-boundary, data-migration, irreversible or complex cross-module changes. In off mode, do not trigger review automatically. An explicit request to review this plan runs the review in either mode. A general request to skip automatic review does not erase a separate explicit request to review; clarify genuinely conflicting instructions. Disabling review does not erase findings or imply READY; retain unresolved evidence and normal authorization boundaries. Do not trigger review for routine low-impact edits merely because several files change. Supply one stable plan with outcome, scope/non-goals, ownership, dependencies, acceptance and rollback where relevant; the analyst reviews, the main Agent revises.

Default automatic budget is TWO review calls total per logical plan, including the initial review. Initial review gathers all known material blockers. After a meaningful revision or new evidence, the second fresh review verifies closure and checks material issues introduced by the revision. No unchanged resubmission; style and optional improvements are non-blocking. Track the logical plan ID, call count, verdicts and remaining blockers in the current task; if a handoff already exists, preserve them there. A new session, renamed plan, different reviewer/model or cosmetic split does not reset the count. Protocol failures count as calls; do not create an unbounded retry loop.

READY means ready for execution, not permission or proof of correctness. Continue already authorized work without an extra routine confirmation. REVISE after the second call stops automatic submission and blocks execution of that unresolved plan. Main may gather evidence and continue independent authorized work; ask only for a genuine product/scope/authority decision. Another review beyond the cap requires the user's explicit instruction. Do not treat the cap as approval, bypass it with direct implementation, or expand scope to satisfy optional reviewer advice.

## Return, verification and recovery

Review every child's outcome against its brief. Inspect actual changes against the pre-dispatch baseline, preserve unexpected changes, and run only checks needed to close remaining gaps. A child's completed status alone does not complete the whole task. Read-only roles must leave sources unchanged. Reports contain outcome, evidence, actual changed paths/no writes, validation, blockers and next step. Reuse valid evidence rather than rerunning everything.

Classify a block as temporary failure, missing specification, role mismatch or out-of-scope dependency. Retry an identical failed operation at most once and only for a specific recoverable temporary cause; repetition of that cause returns ownership to main. Do not guess missing authorization or unknown requirements. Main reports the integrated result and distinguishes intended model/effort, saved configuration and observed execution.

## Delegation setup lifecycle

Use cc-feather:setup for installation checks, updates and removal, and cc-feather:model for persistent model/effort changes. Plugin updates do not refresh these external native roles automatically. Remove the managed installation before uninstalling the plugin if the user wants this policy and roles removed. Preserve handoff data. Do not change main-session model, concurrency, unrelated CLAUDE.md content, settings or permissions as part of these operations.
<!-- cc-feather:end -->
