---
name: delegation
description: "Coordinate Feather delegation: dispatch independent work, accept child results, recover blocked assignments, and conduct security analysis, triggered plan reviews or outcome verification."
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
| security-executor | Authorized changes to security boundaries |
| verifier | Independent verification of a completed implementation claim |

Route delegated work only to these roles. Built-in general-purpose and Plan agents run on the main model and bypass this routing; use them only when the user asks for them.

The table uses role ids. When the installed delegation policy lists native role names, such as `cc-scout`, dispatch each role to its listed name.

Use configured role models and effort. For task/session overrides, persistent changes or uncertain bindings, read [model](../model/SKILL.md) before dispatch or configuration changes. Main-only preferences do not override children. Distinguish configured settings from native execution evidence; label unseen execution unconfirmed.

For requested security analysis or material security-boundary changes, give analyst a read-only brief identifying paths, trust boundaries, evidence questions and excluded scope. Evaluate findings before assigning authorized fixes to security-executor. Security analysis and plan review are separate assignments; apply the review trigger independently.

## Dispatch

Give the child a goal, relevant context, scope/exclusions, constraints, expected deliverable and acceptance checks. Assign exclusive file ownership for writes and capture the relevant pre-dispatch state for later comparison. Tell every child to complete its own assignment without delegating; writers must preserve other contributors' changes.

Parallelize only independent work without shared mutable conflicts. Isolate overlapping checkout risks in separate worktrees or serialize writers. Wait for the previous owner to stop before taking over or reassigning its files; pass its findings and current state to the next owner.

## Accept or recover

Compare the child's report with its brief. Verify cited evidence, actual changes against the pre-dispatch state and remaining acceptance checks, including unchanged sources for read-only roles. Preserve unexpected changes. Reuse valid verification; a child's completed status does not establish whole-task completion.

Classify a blocker as temporary failure, missing specification, role mismatch or out-of-scope dependency. Retry the same operation at most once, only for a recoverable temporary cause. Changing child, model or error wording does not reset this limit. Otherwise main reclaims the task, preserves the evidence and resolves or reports the blocker while independent authorized work continues. Missing authorization or unknown requirements remain unresolved until established.

When outcome verification is required, follow [the outcome-verification procedure](references/outcome-verification.md) before reporting completion. Report the integrated result and remaining limitations. Update an active handoff through cc-feather:handoff when required by its maintenance policy.

## Plan review

When the installed policy or an explicit user request requires plan review, read and follow [the plan-review procedure](references/plan-review.md) before dispatch, revision or resuming the reviewed plan. Keep the review count and unresolved verdicts across mode and session changes. In auto, work that met a review trigger also needs outcome verification once implemented; in off, an explicit plan-review request does not imply verification. For a request to turn automatic review on or off, follow [the toggle procedure](../setup/references/auto-review.md).
