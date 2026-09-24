---
name: model
description: "Inspect or change Claude Feather role models and effort, including Explore. Distinguish one-task/session preferences from permanent user or project configuration."
---

# Feather Model for Claude Code

Manage the native roles scout, analyst, mech-executor, executor, security-executor and Explore while preserving their responsibilities and tool permissions. Use [feather_config.py](../../scripts/feather_config.py) from the actual plugin installation with Python 3.11+. Never edit managed role files, ownership state or plugin cache manually.

## Resolve values and duration

Run `show --project <confirmed-absolute-root> --scope <project|user>` to read the intended owning installation. If scope is unclear, inspect the relevant scopes and ask only when ownership/target remains ambiguous. A user-scope change affects other projects using those roles. Permanent changes require the delegation component; handoff-only setup is insufficient. Installation or scope migration belongs to cc-feather:setup.

Resolve each field independently: explicit current task/child request > applicable session preference > saved role value > package default. An instruction “use Sonnet to review” selects analyst duties and Sonnet for that review, retaining the resolved analyst effort. It does not authorize editing persistent files. Preserve explicit full model IDs; do not replace them with a family alias. A main-session-only preference does not override children.

When a change is requested without duration, ask whether it is for the task/session or permanent. Reuse any choice already given. Show requested before/after model and effort, scope and paths. Check native/provider support and known overrides; the script's syntax check and rendered frontmatter cannot confirm model availability, effective effort or live execution. If a requested combination cannot be applied, explain before dispatch; do not silently substitute.

## Permanent change

```text
python -B <tool> model --project <root> --scope project --set analyst.model=opus --set analyst.effort=high
python -B <tool> model --project <root> --scope project --set analyst.model=opus --set analyst.effort=high --apply --expected-plan <plan_id>
python -B <tool> show --project <root> --scope project
```

Omitted fields remain unchanged. Use the preview's identifier with exactly the same arguments. If permanent scope and change are already authorized, apply the clean preview without another confirmation; conflicts/stale input require reconciliation. Report saved values and backup paths. Setup updates preserve these choices. Do not alter the main model, concurrency or all-subagent force variables.

## Task or session only

Keep the scoped preference in the conversation and preserve the native role. Apply a model override through the exposed native Agent model parameter when supported. An effort override also needs a supported native binding; prompt wording alone cannot enforce it. If the current Agent tool does not expose effort, do not pretend it changed: explain the limitation and offer the tool's read-only `session` export for a newly launched Claude session, or a permanent change only if chosen by the user.

`session --project <root> --scope <scope> --set ROLE.model=VALUE --set ROLE.effort=VALUE` exports definitions for Claude's native `--agents` launch option without installing them. Use the returned complete JSON in the launch context the user chose; do not automatically launch a second model session. The exported definitions keep role tool boundaries. Existing running children remain unchanged. Session-only choices are not written to handoff or configuration files just to persist them.

Confirm actual execution using native evidence when available (/tasks can display model and effort). Label unseen execution unconfirmed. Known managed/CLI/nested role definitions, environment force settings and availableModels policy can supersede saved choices. See [setup limits](../../docs/setup.md).
