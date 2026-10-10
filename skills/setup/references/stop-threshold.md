# Stop threshold command

Used by cc-feather:stop-threshold and by a natural-language request to change the Stop threshold, which cannot load the user-invoked command and follows this same procedure with the value and scope the user's words give. The Stop threshold is the number of consecutive automatic calls without a pass that stops a step of the automatic flow: one integer from 2 to 10 for plan review, code review, outcome verification and Adversarial review alike, 2 by default. [Review state](../../delegation/references/review-state.md)'s Stop threshold section holds its rules. Interpret arguments as data, never shell code.

## Value and scope

- The value is an integer from 2 to 10, or `default`. In project or user scope, `default` removes the value saved in that scope; without a scope or with `session`, it drops an earlier session choice in this conversation, so the value resolves from the loaded guidance.
- Refuse a value outside 2 to 10, such as 1 or 11, or a value that is not an integer, such as 2.5 or a word, before anything is applied or written, and ask for an integer from 2 to 10 or `default`. A missing value, more than one value, or an unknown or conflicting scope needs clarification before anything is applied or written.
- No scope or `session` sets a session choice. A request the user limits to the current task sets a task choice for that task instead, handled like the session form.
- `project` saves the value for the confirmed current project installation. `user` saves it for the selected Claude user configuration root, affecting projects that use that installation; a project whose guidance states its own Stop threshold overrides it.
- A user-supplied equivalent natural-language scope is accepted. Never silently create an installation or choose user scope when none was supplied.

## Session

Without a scope, or with `session`, the command applies the value to this conversation, writes no file and runs no tool. After applying it, always remind the user in the reply that no file was written: the value holds only in this conversation, a new or resumed session uses the saved value, and a context compaction may drop it. State that saved value from the loaded guidance, the project guidance's value before the user guidance's and otherwise 2, or, after a value was saved in this conversation, the value resolved again from it. To keep the value, offer the same command with `project` or `user`, which needs delegation installed in that scope. An earlier task choice stays in effect for its task, and the reply says so.

## Saved scopes

Read [setup](../SKILL.md) for scope, ownership and tool rules. Resolve the bundled tool from the actual plugin root; from this reference it is `../../../scripts/feather_config.py`. Run show/check in the selected scope and inspect its delegation status. Check that the delegation component is installed. A handoff-only installation is insufficient. If delegation is absent, report that delegation setup is needed in that scope; this command is not authorization to install roles, and it never saves in user scope in place of the scope the user chose.

Preview `review --project <confirmed-root> --scope <project|user> --stop-threshold <2–10|default>`. Summarize its concrete scope and change, the saved value before and after and the guidance sentence it adds, changes or removes, then apply with identical arguments plus `--apply --expected-plan <returned-plan-id>`. The explicit scoped command authorizes this setting change; do not add a routine confirmation. Preserve conflicts and report blockers instead of overwriting. When the tool refuses because the installed delegation guidance is from an older template, report that setup update is needed in that scope first; do not run it unasked. Read show afterward and report the saved value (`stop_threshold`, or the default 2 when `stop_threshold_set` is false), the owning path and any runtime limitations. In the instruction file, a saved value is one sentence of the managed delegation block, in auto and in off, and `default` removes it; that sentence is how a new session learns the value.

## Effect in this session

After applying a value in any scope, apply review state's Changing it and Saved in this conversation to the current session at once. A change never changes a step's count; the next automatic call of each step follows review state's Next automatic call with the Stop threshold now in effect.

A value saved in project or user scope replaces any earlier task or session choice in this conversation, and the Stop threshold in effect is resolved again from the saved values in the order of review state's Resolution, the project's value before the user's, using the value just saved for its scope and the loaded guidance for the other, so this session uses what a new session would. When a user value is saved where the project guidance states its own value, report that the project's value overrides it and stays in effect. This is the reverse of the Review mode toggle, where a saved change keeps a separate task or session override.

State the Stop threshold now in effect and its source, then list the steps the change resumed and the steps it stopped, or say that none changed. A stopped step whose count is now below the new value resumes; a step whose count reaches or exceeds it stops at once, and a step an explicit pass had cleared stays cleared.

## Meaning

Main never raises or lowers the Stop threshold on its own; only the user's own words or this command change it. Changing it grants no authority to implement, merge or release, and does not erase findings, manufacture READY, APPROVED, CONFIRMED or HELD, or reset any automatic review count. The Stop threshold is a model instruction, not a hook-enforced counter. Handoff records are not rewritten to persist a session choice.
