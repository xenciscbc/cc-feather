---
name: delegation
description: "Coordinate Feather delegation: dispatch independent work, accept child results, recover blocked assignments, and conduct security analysis, plan reviews, code reviews or outcome verification, including automatic review of plan-driven work when enabled through saved guidance or a task/session preference."
---

# Feather delegation

Run this workflow in the main conversation. Main owns decisions and final acceptance; children complete assigned work as leaves. Loading this skill neither installs roles nor grants authority. Use the required managed native role; if unavailable, report the limitation and keep the affected delegation or required review blocked. Installation belongs to cc-feather:setup.

## Select and prepare

Keep small or tightly coupled work with main. Select a bounded independent responsibility and route by its actual work:

| Native role | Responsibility |
| --- | --- |
| scout | Bounded factual lookup |
| Explore | Broad read-only discovery; use the installed Explore, whether cc-feather or the user provides it |
| analyst | Causal/impact analysis, security analysis or plan review |
| mech-executor | Repetition with a complete specification |
| executor | Scoped implementation requiring engineering judgment |
| security-executor | Authorized Security-critical changes, including the implementation of every Security-critical claim |
| verifier | Independent verification of a completed implementation claim |
| reviewer | Independent code review of one implemented claim |
| adversary | Independent attempt to break one Security-critical claim; reports HELD, BROKEN or INCONCLUSIVE and never fixes |

Route delegated work only to these roles. Built-in general-purpose and Plan agents run on the main model and bypass this routing; use them only when the user asks for them.

The table uses role ids. When the installed delegation policy lists native role names, such as `cc-scout`, dispatch each role to its listed name.

Use configured role models and effort. For task/session overrides, persistent changes or uncertain bindings, read [model](../model/SKILL.md) before dispatch or configuration changes. Main-only preferences do not override children. Distinguish configured settings from native execution evidence; label unseen execution unconfirmed.

A Security-critical change is a change to a security guarantee at a trust boundary, or to the implementation or configuration of a security control, including where sensitive data goes and how untrusted data is interpreted downstream. Authentication, authorization, sessions and CSRF, credentials, cryptography, input validation and access control are typical examples, not a closed list; input validation counts where untrusted data crosses a trust boundary. Recognise it by what the change does, not by keywords. A Security-critical claim is a claim whose outcome includes a Security-critical change; classify claims as [plan review](references/plan-review.md) describes, in off mode too, before dispatching their implementation.

For requested security analysis or a Security-critical change, give analyst a read-only brief identifying paths, trust boundaries, evidence questions and excluded scope. Evaluate findings before assigning authorized fixes to security-executor, and route the implementation of every Security-critical claim to security-executor. Security analysis and plan review are separate assignments; a security analysis neither replaces nor triggers plan review, which follows its own rules. In auto, for a plan with a Security-critical claim, the security analysis runs before plan review and its findings become security invariants and test targets in the plan, as [plan review](references/plan-review.md) describes.

## Dispatch

Give the child a goal, relevant context, scope/exclusions, constraints, expected deliverable and acceptance checks. Assign exclusive file ownership for writes and capture the relevant pre-dispatch state for later comparison. Tell every child to complete its own assignment without delegating; writers must preserve other contributors' changes.

Parallelize only independent work without shared mutable conflicts. Isolate overlapping checkout risks in separate worktrees or serialize writers. Wait for the previous owner to stop before taking over or reassigning its files; pass its findings and current state to the next owner.

## Accept or recover

Compare the child's report with its brief. Verify cited evidence, actual changes against the pre-dispatch state and remaining acceptance checks, including unchanged sources for read-only roles. Preserve unexpected changes. Reuse a verdict only while it is valid, as [review state](references/review-state.md) describes; a child's completed status does not establish whole-task completion.

Classify a blocker as temporary failure, missing specification, role mismatch or out-of-scope dependency. Retry the same operation at most once, only for a recoverable temporary cause; a retried review or verification counts as a call of that step and is never used on a stopped step. Changing child, model or error wording does not reset this limit. Otherwise main reclaims the task, preserves the evidence and resolves or reports the blocker while independent authorized work continues. Missing authorization or unknown requirements remain unresolved until established.

When the automatic flow requires them, follow [the code-review procedure](references/code-review.md) and then [the outcome-verification procedure](references/outcome-verification.md) before reporting completion. An explicit request runs only what was requested: explicit code review follows the code-review procedure without starting verification, and explicit verification follows the outcome-verification procedure without code review first. In auto, when an explicit pass clears a step the automatic flow had stopped, the automatic flow resumes from there, as [review state](references/review-state.md) describes. After a claim passes and is committed, and any postcondition holds, update its ticket as [review state](references/review-state.md) describes. Report the integrated result and remaining limitations. Update an active handoff through cc-feather:handoff when required by its maintenance policy.

When the user asks for a "review" without naming one, review the plan if the work is not yet implemented and review the code if it is; in auto, when implemented work's plan has no plan-review state in this session, first ask as [review state](references/review-state.md)'s Implemented before plan review describes. In auto, classify it as [review state](references/review-state.md) describes and state the classification before dispatching.

## Plan review

When the installed policy, a session preference that turns automatic review on (cc-feather:auto-on without a scope, which writes no file) or an explicit user request requires plan review, read and follow [the plan-review procedure](references/plan-review.md) before dispatch, revision or resuming the reviewed plan. Keep the review count and unresolved verdicts across mode changes within a session; a resumed session starts a new count, while unresolved verdicts recorded in an active handoff still apply. In auto, plan-driven work also needs code review and then outcome verification once implemented; in off, an explicit plan-review request does not imply them. For a request to turn automatic review on or off, follow [the toggle procedure](../setup/references/auto-review.md).

## Code review

When the installed policy, a session preference that turns automatic review on or an explicit user request requires code review, read and follow [the code-review procedure](references/code-review.md) after the primary acceptance passes and before outcome verification. Keep its call count and open findings across mode changes within a session.

## Outcome verification

For automatic verification of plan-driven work or an explicit verification request, read and follow [the outcome-verification procedure](references/outcome-verification.md).
