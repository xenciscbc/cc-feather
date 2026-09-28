---
name: handoff-list
description: "List this project's Feather handoff work summaries without selecting or resuming any item."
disable-model-invocation: true
argument-hint: "[optional filter, e.g. in-progress | blocked | keyword]"
---

# handoff-list

List Feather handoff work in the current project. Follow the list rules in [Read or resume](../handoff/SKILL.md#read-or-resume) and use [the handoff file tool](../handoff/references/tool.md) `list` command; this command adds no separate storage rules.

- This is read-only: do not write records or Git rules, compare sources, select, resume or execute any next step. Exclude `history.md` and `archive/`.
- For each item show its work name (filename without `.md`), title, status and the recorded `進度` summary. The work name is what `/cc-feather:handoff-resume <work>` accepts.
- An optional argument filters the displayed items by status or keyword; state the filter applied. Without an argument, list everything.
- Report `partial` or uncertain-root results with their affected files; an incomplete list cannot establish that no other pending work exists. Report an empty list as no pending work only when the result is complete.
