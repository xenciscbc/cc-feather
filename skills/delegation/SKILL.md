---
name: delegation
description: "Coordinate Feather delegation: dispatch independent work, accept child results, recover blocked assignments, and conduct security analysis, plan reviews, code reviews, outcome verification or Adversarial review, including automatic review of plan-driven work when enabled through saved guidance or a task/session preference."
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

A Security-critical change is a change to a security guarantee at a trust boundary, or to the implementation or configuration of a security control, including where sensitive data goes and how untrusted data is interpreted downstream. Authentication, authorization, sessions and CSRF, credentials, cryptography, input validation and access control are typical examples, not a closed list; input validation counts where untrusted data crosses a trust boundary. Recognise it by what the change does, not by keywords. A Security-critical claim is a claim whose outcome includes a Security-critical change; classify claims as [plan review](references/plan-review.md) describes, in off mode too, before dispatching or starting their implementation, main's own work included.

For requested security analysis or a Security-critical change, give analyst a read-only brief identifying paths, trust boundaries, evidence questions and excluded scope. Evaluate findings before assigning authorized fixes to security-executor, and route the implementation of every Security-critical claim to security-executor. In off mode too, a Security-critical change an executor reports goes to security-executor. Security analysis and plan review are separate assignments; a security analysis neither replaces nor triggers plan review, which follows its own rules. In auto, for a plan with a Security-critical claim, the security analysis runs before plan review and its findings become security invariants and test targets in the plan, as [plan review](references/plan-review.md) describes. Main and analyst follow [repository safety](references/repository-safety.md) for every repository read a security analysis makes, and main prepares the brief, including analyst's allowlist, as it describes.

## Dispatch

Give the child a goal, relevant context, scope/exclusions, constraints, expected deliverable and acceptance checks. Assign exclusive file ownership for writes and capture the relevant pre-dispatch state for later comparison. Tell every child to complete its own assignment without delegating; writers must preserve other contributors' changes.

The brief of an Assignment that implements a claim carries the claim's reading set, as [review state](references/review-state.md)'s Reading set describes: the text the claim is written in and the parts of a spec it cites, an Out of Scope line that limits what the claim may change included, and, only for a claim a spec lists, the spec's parts that state they hold for every claim; no other part of a spec is supplied, and the whole spec only when the spec itself is the claim, except for a ticket of a spec implemented or reviewed without a READY for its plan in this session, as [review state](references/review-state.md)'s Reading set describes. For a claim of a plan that is neither a spec nor tickets of a spec, such as a plan file, a plan-mode plan or a conversation plan with several claims, the text the claim is written in is the whole plan: the whole plan is supplied to the claim's implementation and every review of it, as before cc-feather 0.23.0, and main records and compares it, with any part of a spec the claim cites, as the claim's reading set, so a change to another claim's part of that plan is a change to the reading set. Citations are as [plan review](references/plan-review.md) defines them. This is the same material the claim's code review, outcome verification and Adversarial review read; main confirms it unchanged before dispatch and supplies only the reading set it recorded. For a Security-critical claim, the brief carries exactly the security invariants and test targets written in the claim's own text, which for a claim of a plan that is neither a spec nor tickets of a spec is its own part of that plan, the parts it cites and, for a claim a spec or other plan lists, the parts stated to hold for every claim, never another claim's, and any finding or disposition main gives the implementer also goes to the claim's code review, outcome verification and Adversarial review.

Parallelize only independent work without shared mutable conflicts. Isolate overlapping checkout risks in separate worktrees or serialize writers. Wait for the previous owner to stop before taking over or reassigning its files; pass its findings and current state to the next owner.

Reviews are serial within a working tree, as [review state](references/review-state.md)'s Serial within a working tree describes. While a code review, outcome verification or Adversarial review call runs, main does not change the working tree it judges, its own handoff records inside the project included, which it updates only between calls, and implementation in that working tree waits until the call ends. Before dispatching such a call, main confirms that no Assignment or background process it started that may write the working tree is still running, and at most one gated call that executes code runs in a working tree at a time. Main does not create a worktree for a review on its own. Work the user runs in separate worktrees may proceed in parallel, each worktree serial in itself and still prepared and checked under [repository safety](references/repository-safety.md). Shared test resources stay governed by each brief's target start and reset.

## Accept or recover

Compare the child's report with its brief. Verify cited evidence, actual changes against the pre-dispatch state and remaining acceptance checks, including unchanged sources for read-only roles. Preserve unexpected changes. Reuse a verdict only while it is valid, as [review state](references/review-state.md) describes; a child's completed status does not establish whole-task completion.

Classify a blocker as temporary failure, missing specification, role mismatch or out-of-scope dependency. Retry the same operation at most once, only for a recoverable temporary cause; a retried review or verification counts as a call of that step and is never used on a stopped step. Changing child, model or error wording does not reset this limit. Otherwise main reclaims the task, preserves the evidence and resolves or reports the blocker while independent authorized work continues. Missing authorization or unknown requirements remain unresolved until established.

When the automatic flow requires them, follow [the code-review procedure](references/code-review.md), then [the outcome-verification procedure](references/outcome-verification.md) and, for a Security-critical claim, then [the adversarial-review procedure](references/adversarial-review.md) before reporting completion. An explicit request runs only what was requested: explicit code review follows the code-review procedure without starting verification, and explicit verification follows the outcome-verification procedure without code review first. In auto, when an explicit pass clears a step the automatic flow had stopped, the automatic flow resumes from there, as [review state](references/review-state.md) describes. After a claim passes and is committed, and any postcondition holds, update its ticket as [review state](references/review-state.md) describes. Report the integrated result and remaining limitations. Update an active handoff through cc-feather:handoff when required by its maintenance policy.

When the user asks for a "review" without naming one, review the plan if the work is not yet implemented and review the code if it is; in auto, when implemented work's plan has no plan-review state in this session, first ask as [review state](references/review-state.md)'s Implemented before plan review describes. In auto, classify it as [review state](references/review-state.md) describes and state the classification before dispatching.

## Plan review

When the installed policy, a session preference that turns automatic review on (cc-feather:auto-on without a scope, which writes no file) or an explicit user request requires plan review, read and follow [the plan-review procedure](references/plan-review.md) before dispatch, revision or resuming the reviewed plan. Keep the review count and unresolved verdicts across mode changes within a session; a resumed session starts a new count, while unresolved verdicts recorded in an active handoff still apply. In auto, plan-driven work also needs code review and then outcome verification once implemented, and a Security-critical claim then Adversarial review; in off, an explicit plan-review request does not imply them. Each step of the automatic flow stops at the Stop threshold, which main resolves, states and applies to a change as [review state](references/review-state.md) describes and never changes on its own. For a request to turn automatic review on or off, follow [the toggle procedure](../setup/references/auto-review.md). For a request to change the Stop threshold, follow [the Stop threshold procedure](../setup/references/stop-threshold.md), as `/cc-feather:stop-threshold` does.

## Code review

When the installed policy, a session preference that turns automatic review on or an explicit user request requires code review, read and follow [the code-review procedure](references/code-review.md) after the primary acceptance passes, or is recorded as not run under [repository safety](references/repository-safety.md)'s Execution, and before outcome verification. Keep its call count and open findings across mode changes within a session.

## Outcome verification

For automatic verification of plan-driven work or an explicit verification request, read and follow [the outcome-verification procedure](references/outcome-verification.md).

## Adversarial review

For automatic Adversarial review of a Security-critical claim, read and follow [the adversarial-review procedure](references/adversarial-review.md). For an explicit Adversarial review, including `/cc-feather:adversarial-review`, follow the same procedure and classify the call as [the adversarial-review command](../adversarial-review/SKILL.md) describes.

## Repository safety

For every repository read that a plan review, code review, outcome verification, Adversarial review or security analysis makes, for main's preparation of each call and its comparison of the workspace after it, and before main adds, commits, tags or pushes, read and follow [repository safety](references/repository-safety.md).
