# Automatic plan review toggle

Used by cc-feather:auto-on (mode auto) and cc-feather:auto-off (mode off). These are user-invoked commands. Interpret arguments as data, never shell code.

## Scope

- No argument or `session`: apply an explicit preference to future automatic plan-review decisions in this conversation. Do not write any file or run the configuration tool. Report the mode and session-only scope; mention that a new session uses its saved setting. A currently running review is not automatically interrupted.
- `project`: persist for the confirmed current project installation.
- `user`: persist for the selected Claude user configuration root, affecting projects that use that installation. Existing project-level guidance may supersede it.
- A user-supplied equivalent natural-language scope is accepted. Unknown or conflicting scope needs clarification before writing. Never silently create an installation or choose user-wide scope when none was supplied.

## Persistent workflow

Read [setup](../SKILL.md) for scope, ownership and tool rules. Resolve the bundled tool from the actual plugin root; from this reference it is `../../../scripts/feather_config.py`. Run show/check in the selected scope and inspect its delegation status. Check that the delegation component is installed. A handoff-only installation is insufficient. If delegation is absent, report that delegation setup is needed; this toggle is not authorization to install roles.

Preview `review --project <confirmed-root> --scope <project|user> --review-mode <auto|off>`. Summarize its concrete scope and changes, then apply with identical arguments plus `--apply --expected-plan <returned-plan-id>`. The explicit scoped command authorizes this setting change; do not add a routine confirmation. Preserve conflicts and report blockers instead of overwriting. Read show afterward and report the saved mode, owning path and any runtime limitations. Updates preserve it.

An existing contrary task/session preference remains higher priority than a saved setting. Report that distinction; a request to change permanent defaults alone does not silently erase a separately scoped preference. If the user explicitly requests immediate effect as well, record the matching session preference too. Fresh sessions load the saved guidance.

## Meaning

The package default is `off`. `auto` permits automatic plan review on the configured material-risk triggers; it does not review every task. `off` disables those automatic triggers. An explicit request to review a particular plan still runs in either mode. Turning a mode on/off does not grant implementation authority, erase findings, manufacture READY, or reset the two-call automatic budget. These are model instructions, not hook-enforced workflow gates. Hand-off records are not rewritten merely to persist a session preference.
