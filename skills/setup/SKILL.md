---
name: setup
description: "Inspect and independently install, update or remove Feather handoff maintenance rules and agent delegation (policy plus native roles). Use for setup status, component selection, scope and ownership changes."
---

# Feather Setup for Claude Code

Manage two independent components in a project or user scope:

- `handoff`: persistent handoff maintenance rules in a marked block of the scope's instruction file. It installs no agents and does not touch handoff records. The plugin's handoff skill is usable without this setup component.
- `delegation`: a concise instruction-file entry for cc-feather:delegation plus all eight native agents (scout, analyst, mech-executor, executor, security-executor, verifier, reviewer and exact-name Explore). Includes model configuration and optional automatic plan review, code review and outcome verification of plan-driven work, default off; the automatic review rules appear in the instruction file only while the mode is auto.
- `both`: operate on both selected components in one preview/apply transaction.

Use [the bundled tool](../../scripts/feather_config.py) from this skill's loaded installation, not the target project's working directory. Python 3.11+ and the standard library are sufficient. Use it for all managed writes; do not hand-edit ownership state, role files or policy blocks.

## Inspect before asking

1. Establish the target project from the workspace/request and resolve its absolute root. A plugin cache is not the target project. If the project itself is ambiguous, ask for it before proceeding. Project scope refuses a directory whose writes would land in the user configuration (the home directory, the Claude configuration directory or `~/.claude`); offer user scope instead. A project reached through a linked ancestor is resolved once and the preview reports `resolved_paths`; links inside the project's `.claude` or the Claude configuration directory are refused.
2. Inspect installation status before asking what to do: `check --project <root> --scope project` and, when no scope was specified, also `check --project <root> --scope user`. If the user specified one scope, inspect that scope only. User scope uses CLAUDE_CONFIG_DIR or ~/.claude; an explicit --claude-home selects another configuration root. An unreadable or malformed state is unknown/conflicted, not uninstalled.
3. Briefly report each inspected scope's handoff and delegation status, conflicts/migration needs, warnings (such as delegation guidance from an older template, which setup update refreshes), and saved review mode when delegation is installed. Use a small table when useful. Existing user/project definitions may shadow each other; do not call a saved setting proof of live loading.
4. Reuse all choices in the request. A bare setup invocation asks, after the status report, which operation (install/update/remove/check), component (handoff/delegation/both) and scope is intended. Ask only for missing choices, preferably together. If the user says “install handoff only in this project,” select handoff/project and proceed; do not ask whether to install agents. Check-only requests finish after reporting status without asking for an installation.

## Preview and apply the selected operation

Always pass the selected component explicitly. For example:

```text
python -B <tool> install --project <root> --scope project --component handoff
python -B <tool> install --project <root> --scope project --component handoff --apply --expected-plan <plan_id>
python -B <tool> check --project <root> --scope project
```

Use delegation or both for the other selections. Update and remove operate on the selected components; leave unselected policies, roles and settings intact. For both, install adds missing components without resetting installed ones, update refreshes only installed components, and remove skips absent components. When selected components have different installation states, explain the actual preview rather than silently expanding the user's selection. If the tool requires a separate operation, report the status and use the user's chosen intent to select the next authorized operation. When check/show reports `role_update_required`, the installation predates a newly packaged role; delegation update adds it while keeping saved choices, and model/review changes and session export wait for that update.

In project scope the managed blocks go into the instruction file Claude reads: an existing CLAUDE.md, else .claude/CLAUDE.md. When the project relies on AGENTS.md instead, the tool stops with `guidance target choice required`. Ask whether to write into the existing AGENTS file or create a CLAUDE.md that imports it; when the message offers only `--guidance claude` (only ancestor directories have AGENTS.md), offer only the importing CLAUDE.md. Mention that AGENTS.md is shared with other coding agents, and that creating a CLAUDE.md without the import would stop Claude reading AGENTS.md. Pass `--guidance agents` or `--guidance claude`; the tool records the choice and reuses it. User scope always uses CLAUDE.md.

Summarize concrete paths and changes before apply. Use the preview's exact plan identifier with matching arguments. An explicit request for that operation/component/scope authorizes a clean apply without another routine confirmation. Stale input needs a fresh preview and reconciliation. After apply, run check/show and verify both the selected outcome and preservation of the other component. Report backups, remaining conflicts and actual saved state.

Removing handoff removes its persistent reminder only. It neither deletes .feather records nor disables the plugin's handoff command. Removing delegation removes its intact managed roles and policy while retaining independently installed handoff rules. Neither operation changes main model, concurrency, settings.json, permissions or unrelated instruction-file content. Removal deletes an instruction file only when setup created it and nothing else remains: no content at all, or only the imports of a CLAUDE.md created to import AGENTS.md.

## Conflicts and migration

Read [lifecycle and runtime limits](../../docs/setup.md) for legacy installs, conflicting names, shadowing, settings overrides or recovery. When another agent already uses a role name, even under another filename or subdirectory, the tool moves the other roles to the `cc-` prefix; check/show report it as `pending_role_prefix`, and report the prefixed names from the preview before applying. An installation keeps its prefix after the other agent goes away; dropping it takes remove and reinstall. Other agents' files are never overwritten or adopted. When another agent is named Explore, cc-feather installs no Explore and uses that one (`external_roles`, or `pending_external_roles` before install/update); tell the user its model is not managed by cc-feather. A conflict on a `cc-` name still stops: preserve the files and ask whether the user wants to keep the existing configuration, rename the existing role, or explicitly back it up and replace it. Handoff-only operations do not require resolving unrelated agent collisions.

Legacy installations had handoff and delegation in one block. Preserve the existing handoff reminder when splitting that block into separately owned components; migration must not make delegation-only removal erase handoff behavior. The tool checks ownership and preserves model/effort and review choices. Modified managed files or occupied target role names remain conflicts. Show the split in the preview and use the tool's migration path; never fake ownership metadata. A removal or update must respect the user's selected components.

## Models and review

Use cc-feather:model for model/effort changes in the delegation component. Automatic review defaults off. Dedicated auto-on/auto-off follow [the toggle procedure](references/auto-review.md): no argument/session is a conversation preference, while project/user persists only when delegation is installed. Never install delegation just because a review toggle was requested. Explicit plan review, code review and verification requests still work when automatic review is off; changing the mode does not reset any two-call automatic budget.

Use fresh sessions to load installed guidance and roles reliably. When available, /tasks provides native evidence of actual model/effort; CLI/managed/nested definitions, force-model settings and provider restrictions may affect selection. Setup checks and policy instructions are not live dispatch verification or hook-enforced gates.

Plugin updates refresh the package, not external deployments. Update the desired installed components explicitly. Before plugin uninstall, remove each component/scope the user wants cleaned up; plugin removal alone leaves external guidance and roles.
