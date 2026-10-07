# Delegation preview

Label: `ready-for-agent`

Vocabulary follows [CONTEXT.md](../../CONTEXT.md), which defines Assignment and Delegation preview. Claim sizing stays with whatever produced the Plan, as recorded in [ADR 0003](../adr/0003-review-cost-and-independence-stay-user-configured.md).

## Problem Statement

A user about to implement one Plan or several (for example a batch of tickets) cannot see in advance how the main agent will divide the work. They learn which parts go to which native role, on which model and effort, and which parts main keeps for itself only as dispatch happens. By then cost and routing are already decided. A missing role, a Claim that cannot be verified on its own, or a risky piece of Unplanned work only becomes visible after the work has started. Users have no way to check the routing and cost before saying "go".

## Solution

A new explicit command, `/cc-feather:delegation-preview`, asks main to produce a Delegation preview for the given Plans, tickets or work description, or for the Plan currently under discussion when no argument is given. Main produces it alone, from the Plans, the relevant code and the role settings currently in effect. It dispatches nothing, starts no review and writes nothing.

The preview groups the work by Plan and Claim. Under each Claim it lists every Assignment and every piece of work main keeps, each with its role, model, effort and the source of those values. A short note follows that says what can run in parallel and what must wait. Last comes one section, listed once, for the roles that perform the Automatic flow, with the number of Plans and Claims they will cover. The preview flags problems it can see: roles that are not installed, inputs that are not yet Plans, Claims without their own acceptance, and Unplanned work that must first become a reviewed Plan.

When implementation follows, main dispatches according to the preview and reports any differences. The command is the only way to get a preview; natural-language requests do not trigger one.

## User Stories

1. As a user, I want to preview how a Plan will be delegated before implementation starts, so that I can check routing and cost first.
2. As a user, I want to preview several Plans or tickets at once, so that I can see the delegation for a whole batch of work.
3. As a user, I want to preview a plain work description that is not yet a Plan, so that I can see the delegation for Unplanned work too.
4. As a user, I want a bare command to preview the Plan currently under discussion, so that I do not have to repeat it.
5. As a user, I want to be asked which work I mean when the bare command has no clear target or several candidates, so that the preview does not guess.
6. As a user, I want a preview only when I invoke the command, so that asking about delegation in conversation never produces an unrequested preview.
7. As a user, I want the preview grouped by Plan and then by Claim, so that it follows the structure of my Plans.
8. As a user, I want each Assignment shown with its role, model and effort, so that I know who does each part and at what cost.
9. As a user, I want the work main keeps for itself listed alongside the Assignments, so that I can see what is not delegated.
10. As a user, I want a Claim that needs several Assignments shown as several rows, so that a lookup followed by implementation is visible as two dispatches.
11. As a user, I want each model and effort value labelled with its source (an earlier task instruction, session preference, saved setting or package default), so that I know why it applies.
12. As a user, I want a reason shown only when a routing choice is not obvious, such as a security-boundary change going to security-executor or tightly coupled work staying with main, so that the preview stays short.
13. As a user, I want a short note on which Assignments can run in parallel and which must wait for another or share files, so that I understand the order of work.
14. As a user, I want plan review, code review and outcome verification roles listed once at the end with their model and effort, so that the same three rows are not repeated under every Claim.
15. As a user, I want that final section to state how many Plans and Claims will be reviewed and that each step has at most two automatic calls, so that I can estimate the maximum review cost. (Amended by ADR 0004: each step stops after two consecutive calls without a pass, and a Claim makes at most six automatic calls.)
16. As a user in off mode, I want the final section to say the Automatic flow will not run and that I can still make Explicit requests, so that I do not expect reviews that will not happen.
17. As a user, I want Unplanned work marked as outside the Automatic flow, so that I know it will not be reviewed automatically.
18. As a user, I want Unplanned work that changes a security boundary, migrates data or is irreversible flagged as needing a reviewed Plan first in auto mode, so that I know it cannot start as it is.
19. As a user, I want an input that lacks scope or acceptance still previewed and flagged as not yet a Plan, so that I see the problem before implementation instead of being refused.
20. As a user, I want a Claim without its own verifiable acceptance flagged, so that I can fix the Plan before review depends on it.
21. As a user, I want the preview not to re-cut my Claims, so that Claim sizing stays where my Plan was written.
22. As a user, I want a role that is not installed shown as not installed with its package default, so that I know that part would be blocked.
23. As a user whose own Explore replaces cc-feather's, I want Explore shown as an external role with unknown settings, so that the preview does not invent values.
24. As a user, I want model and effort labelled as configured and unconfirmed at execution, so that I do not read the preview as proof of what will run.
25. As a user, I want the preview to use only the settings already in effect, so that it shows what dispatch would actually do.
26. As a user who includes a model or effort override in the preview request, I want to be told to set it first with cc-feather:model and preview again, so that the preview never shows a value dispatch would not use.
27. As a user, I want a session preference I set earlier in the session reflected in the preview, so that the preview matches this session's dispatch.
28. As a user, I want the preview to dispatch no child, including scout or Explore, so that previewing costs nothing beyond main's own reading.
29. As a user, I want the preview not to start plan review or count toward any review budget, so that previewing never uses up review calls.
30. As a user, I want the preview not to write a handoff, configuration or any other file, so that it has no lasting side effects.
31. As a user, I want main to flag work too large to judge without exploration rather than explore on its own, so that I decide whether to spend on discovery.
32. As a user who proceeds to implementation, I want main to dispatch according to the preview and report any differences with their reason, so that the preview stays meaningful.
33. As a user, I want the routing and model rules used by the preview to be the same ones used by real dispatch, so that preview and dispatch cannot drift apart.
34. As a user, I want the command documented in both READMEs, so that I can find it without it appearing in the installed policy.
35. As a user with an existing installation, I want the preview available after a plugin update alone, so that I do not need to rerun setup update.
36. As a user who turned automatic review on or off for this session only, I want the preview to reflect that session choice, so that it matches what dispatch will do even though no file records it.
37. As a user whose installation prefixes role names, I want the preview to show the names dispatch will use, so that I can match it with what runs.

## Implementation Decisions

- **One rule set, two parts.** The preview procedure is a new reference document under the delegation skill. It cites the delegation skill's routing table and dispatch rules and the model skill's value resolution instead of copying them. A new thin command skill, `delegation-preview`, loads that reference. It sets `disable-model-invocation: true` and takes an optional argument hint for Plans, tickets or a work description, following the pattern of the existing handoff command skills.
- **Explicit entry only.** The delegation skill's description and body do not mention preview, so that loading delegation for real dispatch never triggers one.
- **Manifest.** The plugin manifest lists the new skill.
- **Inputs.** One or more Plans or tickets, or a work description. With no argument, main uses the Plan currently under discussion and asks when there is none or several. Each Plan is expanded to its Claims.
- **Production.** Main produces the preview alone. It may read the Plans, the relevant code and the saved role settings through the configuration tool's read-only `show`, which is one source among those below, not the whole answer. It dispatches no child, starts no plan review, counts toward no review budget and writes no file.
- **Values.** Each model and effort field resolves as real dispatch would, by the model skill's order: a task instruction already given in the conversation for the work being previewed, then an applicable session preference, then the saved role value, then the package default. The preview names the source. An override inside the preview request itself is not applied; main points the user to cc-feather:model and a new preview. Values are labelled configured and unconfirmed at execution.
- **Review mode.** The preview resolves the active Review mode by the plan-review procedure's order (a task or session choice, then project guidance, then user guidance, with a project-scope off overriding a user-scope auto), by citing that procedure rather than copying it. A session auto-on or auto-off, which writes no file, therefore changes the preview even though `show` does not report it.
- **Role names.** The role column uses the native names dispatch would use, including a `cc-` prefix when the installed policy lists one.
- **Output.**
  1. Per Plan, per Claim: rows of `work | role | model | effort | source`, with main-kept work as role `main`. A reason is given only when the routing is not obvious.
  2. A one-line parallel and dependency note, including file-ownership conflicts.
  3. One final review section: plan review by analyst, code review by reviewer and outcome verification by verifier, each with model and effort, plus Plan and Claim counts and the two-call limit per step (amended by ADR 0004: two consecutive calls without a pass, at most six per Claim). Off mode shows that the flow will not run and that Explicit requests remain available; Unplanned work is shown as outside it.
- **Flags.** Not installed (with package default), external Explore with unknown settings, input not yet a Plan, Claim without its own acceptance, Unplanned security-boundary, data-migration or irreversible work needing a reviewed Plan first (in auto; in off only noted, since off mode does not enforce it), and work needing exploration before it can be judged. No Claim is re-cut.
- **Relation to dispatch.** The preview is main's dispatch basis. Actual dispatch may differ when new facts appear, and main reports the differences.
- **Installed policy unchanged.** The managed delegation policy block is not edited, so existing installations get the command from the plugin update without setup update.
- **Documentation.** Both READMEs list the command among the skills and explain its purpose, read-only nature and output.
- **Release.** The work ships as 0.11.0: the manifest version is bumped, the tag `v0.11.0` matches it, and the validation is recorded under its version heading in the setup validation log. Order: the release changes pass code review and outcome verification before they are committed; the local tag is created on that commit afterwards and is not pushed. Rollback before the tag exists reverts the commit; once the tag exists it is never moved or reused, and a needed correction ships as 0.11.1.

## Testing Decisions

- Good tests assert the published contract a user or the plugin loader observes: the manifest entry, the command's frontmatter and the rule statements in the shipped text. They do not test wording beyond the key invariants.
- The seam is the existing configuration test module, which already checks skill text, with `test_explicit_reviews_are_outside_every_automatic_budget` as prior art. New cases:
  - the manifest lists `delegation-preview`;
  - the command skill sets `disable-model-invocation: true` and points to the preview reference;
  - the delegation skill's description and body do not mention preview;
  - the preview reference states that it dispatches nothing, starts no review and writes nothing, that review roles are listed once, and that overrides in the request are not applied;
  - the preview reference links the plan-review procedure for the Review mode and states that a session choice takes precedence over saved settings.
- Release checks: the full `unittest discover` suite and `claude plugin validate` for the plugin root and the manifest.
- Live model compliance with the preview procedure is not tested and is recorded as untested in the validation log. No skill-creator eval is run, because the preview is read-only and a wrong preview has low impact.

## Out of Scope

- Natural-language triggering of a preview.
- Applying model or effort overrides from the preview request, or changing role settings from the preview.
- Exploring the codebase through scout or Explore to improve the preview.
- Persisting a preview to a handoff or any other file, or carrying it into another session.
- Re-cutting, merging or sizing Claims.
- Editing the installed delegation policy, setup or the configuration tool.
- Turning the preview into an approval gate that binds dispatch.
- Estimating tokens or money; the preview gives roles, models, efforts and call counts only.

## Further Notes

- No setup update is required: the command is a plugin skill and the installed policy is unchanged.
- In auto mode, this spec is a Plan the user agreed to, so its implementation goes through plan review, code review and outcome verification.
