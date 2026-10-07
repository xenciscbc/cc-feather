# Delegation preview

This procedure runs only through cc-feather:delegation-preview. It forecasts how main would carry out the given work, using the same rules as real dispatch: routing and dispatch from [delegation](../SKILL.md), model and effort resolution from [model](../../model/SKILL.md) and the Review mode from [plan review](plan-review.md). It cites those rules; where they change, the preview follows them.

## Boundaries

Main produces the preview alone. It may read the Plans, the relevant code and the saved role settings through the configuration tool's read-only `show`. It dispatches no child, including scout or Explore, starts no review, counts toward no review budget and writes no file, handoff or configuration. When part of the work cannot be judged without exploration, say so in the preview and leave the choice to dispatch Explore to the user.

## Inputs

Take one or more Plans or tickets, or a description of Unplanned work. With no argument, preview the Plan currently under discussion; ask when there is none or several are candidates. Identify each Plan and its Claims as [plan review](plan-review.md) does, including a spec's tickets in the named scope searched as plan review does, ignored directories included and hidden ones too, and list the tickets used; a Plan that lists none is one Claim. Do not re-cut, merge or resize Claims.

## Values

- **Model and effort:** resolve each field by the model skill's order. A task instruction already given in the conversation for the previewed work counts as the task source; a session preference counts only when it applies to children and has a native binding. An override inside the preview request itself is not applied: point the user to cc-feather:model, then a new preview.
- **Review mode:** resolve it as the plan-review procedure does: a task or session choice, then project guidance, then user guidance, with project guidance stating off overriding user-scope auto. A session choice takes precedence over the saved mode reported by `show`, because a session toggle writes no file.
- **Role names:** show the native names dispatch would use, including a `cc-` prefix when the installed policy lists one.
- Label every model and effort as configured and unconfirmed at execution.

## Output

1. For each Plan, each Claim, one row per Assignment and per piece of work main keeps:

   | Work | Role | Model | Effort | Source |
   | --- | --- | --- | --- | --- |

   Use `main` as the role for work main keeps. Source is task, session, saved or default. Give a reason only when the routing is not obvious, such as a security-boundary change going to security-executor or tightly coupled work staying with main.
2. One short note on which Assignments can run in parallel and which wait for another or share files.
3. One review section, listed once rather than under each Claim: plan review by analyst, code review by reviewer and outcome verification by verifier, each with model, effort and source. State the number of Plans and Claims covered and that each step stops after two consecutive automatic calls without a pass, per Plan for plan review and per Claim for code review and outcome verification, an automatic pass resetting the count; under the [code review](code-review.md) and [outcome verification](outcome-verification.md) procedures this comes to at most six automatic calls per Claim in one uninterrupted attempt, and each reopened Claim or Material deviation adds calls. Note any step that has already stopped in this session. In off mode, state that the Automatic flow will not run and that Explicit requests remain available. Mark Unplanned work as outside the Automatic flow.

## Flags

Mark each affected row or Plan:

- a role that is not installed, shown with its package default;
- an external Explore, whose model and effort are unknown;
- an input that is not yet a Plan because it lacks scope or acceptance;
- a Plan whose text refers to its own tickets or Claims that cannot be found, or whose listed Claims disagree with its tickets; when it lists no Claims, show the one-Claim reading and note that main will ask before plan review or implementation;
- a Claim without its own verifiable acceptance;
- in auto, Unplanned work that changes a security boundary, migrates data or is irreversible, which needs a reviewed Plan the user approves first; in off, note it only;
- work that needs exploration before it can be judged.

## After the preview

The preview is main's dispatch basis only in the session that made it. When implementation follows in that session, dispatch according to it; if new facts change an Assignment, role, model or effort, report each difference and its reason. A preview from another session is a reference; dispatch may differ from it without being reported as a difference.
