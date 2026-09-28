---
name: handoff-save
description: "Save the current work's progress as a Feather handoff, creating or updating its record."
disable-model-invocation: true
argument-hint: "[work name]"
---

# handoff-save

Save progress for one work item. Follow [Save progress](../handoff/SKILL.md#save-progress), [Storage and write discipline](../handoff/SKILL.md#storage-and-write-discipline) and [the handoff file tool](../handoff/references/tool.md); this command adds no separate storage rules. When the saved status is `完成`, continue with [Archive completed work](../handoff/SKILL.md#archive-completed-work).

The operation is already known to be a save, so a bare invocation does not ask what to do.

- **Argument given:** save that work. Reuse its existing record when present (read it first and update with its version); otherwise create a new record under a legal basename derived from the name.
- **No argument:** save the work this conversation is carrying out. Reuse the record already created or resumed in this conversation. If none exists, create one named after the current work. Ask only when the conversation covers several distinct work items and none is clearly current, or when there is no identifiable work to record.

Report the saved path and status.
