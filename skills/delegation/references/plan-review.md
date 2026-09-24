# Plan review

This procedure governs main's orchestration. Analyst's role definition governs review criteria and its READY/REVISE report.

Resolve the active review mode from task/session choices, then the installed policy; default off. Explicit plan-review requests apply in either mode. In auto, review before material security-boundary changes, data migrations, irreversible operations or complex cross-module changes. Routine edits do not trigger review merely because several files change.

1. Identify the logical plan and recover its prior call count, verdicts and blockers from the task and any active handoff. If prior state is unknown, establish it before another automatic call. Mode changes, new sessions, renamed plans, different reviewers/models or cosmetic splits do not reset the count or clear blockers.
2. Supply a stable plan with outcome, scope/exclusions, ownership, dependencies, acceptance checks and relevant rollback. Use analyst in fresh native context. If fresh context is unavailable, report the limitation and keep the required review blocked.
3. Allow at most two automatic calls total per logical plan, including failed or interrupted calls. Count each attempted review. Missing verdicts and protocol failures never imply READY.
4. On REVISE, address every material blocker before a materially revised second review. Include prior findings, changes and closure evidence. Never resubmit an unchanged plan. Style preferences and optional improvements are non-blocking.
5. With READY, continue work already authorized without another routine confirmation. READY grants no new authority. While required review remains unresolved, stop dependent implementation; gather evidence or continue independent authorized work.
6. After two calls without READY, stop automatic submission. Further review requires an explicit user request. Preserve plan identity, count, verdicts and unresolved blockers in the task and any existing active handoff; do not create a handoff solely for bookkeeping.

Follow cc-feather:auto-on or cc-feather:auto-off for mode changes. Turning review off does not erase an unresolved verdict or manufacture approval.
