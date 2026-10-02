---
name: handoff-resume
description: "Resume a Feather handoff: pick the named work, or the sole unfinished one, and continue its authorized next step."
disable-model-invocation: true
argument-hint: "[work name]"
---

# handoff-resume

Resume one Feather work item. Follow [Read or resume](../handoff/SKILL.md#read-or-resume) (the **Resume** step), [source baselines](../handoff/references/snapshots.md) and [the handoff file tool](../handoff/references/tool.md); this command adds no separate storage rules. Keep maintaining the same handoff afterward.

Select the work from the tool's `list` result:

1. **Argument given:** use the item whose work name (filename without `.md`) or title matches it. If nothing matches, report that and stop; do not substitute another item. If several titles match, ask using their work names.
2. **No argument:** use the work clearly implied by this conversation; otherwise the sole unfinished item, only when the list result is complete. A `partial` or uncertain-root result never auto-selects.
3. **Several unfinished, none implied:** ask which to resume. Use `AskUserQuestion` when available, one option per item labeled with its work name and described by status and the `進度` summary. With more than four items, show the list and ask the user to reply with a work name. Do not choose by update time.
4. **No unfinished work:** report it and stop; do not open history.

Unfinished means `進行中` or `受阻`. A `record_status: 完成待歸檔` item is completed work pending archival: never resume it, even when named; offer an archive retry under [Archive completed work](../handoff/SKILL.md#archive-completed-work) instead. A `格式待確認` item is never selected automatically; report it with its problems.
