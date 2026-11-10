# Related-test acceptance command

Used by cc-feather:related-tests and by a natural-language request to turn Related-test acceptance on or off, which cannot load the user-invoked command and follows this same procedure with the value and scope the user's words give. Related-test acceptance is a delegation setting that changes how main writes a Claim's acceptance in a spec, ticket or plan; its rule is written once, in the template that The rule below names, and this procedure does not restate it. Interpret arguments as data, never shell code.

## Value and scope

- The value is `on`, `off` or `default`. In project or user scope, `default` removes the setting saved in that scope; without a scope or with `session`, it drops an earlier session choice in this conversation, so the setting resolves from the saved choices as Effect in this session takes them. In user scope `off` is the default and saves nothing, so it removes a saved `on`; a project can save `off` to override a user `on`.
- Refuse any other value, such as `true`, `yes` or a number, before anything is applied or written, and ask for `on`, `off` or `default`. A missing value, more than one value, or an unknown or conflicting scope needs clarification before anything is applied or written.
- No scope or `session` sets a session choice. `project` saves the setting for the confirmed current project installation. `user` saves it for the selected Claude user configuration root, affecting projects that use that installation; a project whose guidance states its own setting overrides it.
- A user-supplied equivalent natural-language scope is accepted. Never silently create an installation or choose user scope when none was supplied.

## Session

Without a scope, or with `session`, the command applies the choice to this conversation, writes no file and runs no tool. After applying it, always remind the user in the reply that no file was written: the choice holds only in this conversation, a new or resumed session uses the saved choice, and a context compaction may drop it. State that saved choice as Effect in this session resolves the saved choices without a session choice. To keep the choice, offer the same command with `project` or `user`, which needs delegation installed in that scope. A session choice comes only from the user's own words in this conversation and is not written into a handoff.

## Saved scopes

Read [setup](../SKILL.md) for scope, ownership and tool rules. Resolve the bundled tool from the actual plugin root; from this reference it is `../../../scripts/feather_config.py`. Run show/check in the selected scope and inspect its delegation status. Check that the delegation component is installed. A handoff-only installation is insufficient. If delegation is absent, report that delegation setup is needed in that scope; this command is not authorization to install roles, and it never saves in user scope in place of the scope the user chose.

Preview `review --project <confirmed-root> --scope <project|user> --related-tests <on|off|default>`. Summarize its concrete scope and change, the saved setting before and after and the guidance text it adds, changes or removes, then apply with identical arguments plus `--apply --expected-plan <returned-plan-id>`. The explicit scoped command authorizes this setting change; do not add a routine confirmation. Preserve conflicts and report blockers instead of overwriting. When the tool refuses because the installed delegation guidance is from an older template, report that setup update is needed in that scope first; do not run it unasked. Read show afterward and report the saved choice (`related_tests`, which is `off` with none saved when `related_tests_set` is false), the owning path and any runtime limitations. In the instruction file, a saved `on` is the rule in the managed delegation block and a project `off` is one sentence there, in auto and in off, and `default` removes it; that text is how a new session learns the saved choice.

## Effect in this session

The setting in effect is, in order: the user's session choice; otherwise the choice the loaded project guidance states; otherwise the choice the loaded user guidance states; otherwise off. A choice the user saves in project or user scope in this conversation replaces any earlier session choice in this conversation, and the setting in effect is resolved again from the saved choices in that order, so this session uses what a new session would. Each scope's saved choice is the one last saved in it in this conversation, none after `default`, and otherwise what its loaded guidance states, since the guidance loaded at the start of the session does not show later saves. A user `on` that a project `off` overrides stays off, and main reports it as overridden by the project.

After applying a choice in any scope, state the setting now in effect and its source (session, project, user or default), including a user choice the project overrides, and that it applies to acceptance main writes from then on, not to acceptance already written.

## The rule

Whenever the setting in effect is `on` while the loaded guidance carries no rule, from a session choice or from a choice saved earlier in this conversation, main reads and follows [the rule's template](../../../templates/related-tests.md), which the configuration tool renders the rule from. While `on` is in effect, main applies that rule as if the guidance stated that Related-test acceptance is on. Whenever the setting in effect is off, main does not apply the rule, even where the loaded guidance carries it. After a context compaction, main establishes the saved choices again with the tool's `show` in project and user scope and rereads the template before applying the rule.

## Meaning

Main never changes the setting on its own. The setting changes how main writes acceptance, not how any review or the final check runs. Changing it grants no authority to implement, merge or release. Related-test acceptance is a model instruction, not a hook-enforced check.
