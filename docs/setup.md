# Claude Feather setup and model configuration

The plugin packages five skills. Handoff works immediately after plugin installation; delegation is deployed explicitly with `/cc-feather:setup`. No runtime hooks or model session is started by setup. This supports Windows as well as ordinary Python installations on other hosts; only the tested hosts are reported in validation notes.

## Native deployment

| Scope | Roles | Main-session policy | Ownership/settings |
| --- | --- | --- | --- |
| project | `<project>/.claude/agents/` | `<project>/CLAUDE.md` | `<project>/.claude/cc-feather/state.json` |
| user | `<claude-home>/agents/` | `<claude-home>/CLAUDE.md` | `<claude-home>/cc-feather/state.json` |

`claude-home` defaults to `CLAUDE_CONFIG_DIR`, otherwise the current user's `.claude`. Override it explicitly with `--claude-home`; use a confirmed absolute project root. The packaged templates remain in the plugin; native role files live outside its cache, so upgrades do not erase saved choices. Setup update is required after upgrading templates. Model changes update native frontmatter and ownership metadata together.

The native roles are `scout`, `analyst`, `mech-executor`, `executor`, `security-executor`, and exact-case `Explore`. Role names have no Feather prefix. Setup reports existing same-name roles as conflicts and asks the user how to resolve them; it never adopts or overwrites them automatically. Explore intentionally has the built-in name to override it. Roles are not additionally loaded from a plugin agents directory, avoiding duplicate definitions.

## Explore and actual model selection

Claude Code's official documentation states that built-in Explore has inherited the main model since 2.1.198. A user/project agent named Explore overrides that built-in; a namespaced plugin scout by itself does not do so. Setup therefore includes Explore with explicit haiku/low defaults.

A role file proves requested configuration only. CLI/managed definitions, nearer nested project definitions, duplicate names, invocation model arguments, environment force variables and provider allowlists may affect the live model. `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` is particularly important: it forces the environment's subagent model, or the main model if no environment model is set. Current documentation says the ordinary SUBAGENT_MODEL variable alone is lower priority than explicit frontmatter, whereas older versions behaved differently. Settings-file environment overrides and launch flags may not be visible to the configuration script. Resolve known conflicts and check native execution; never claim all of these have been ruled out by a filesystem check.

Use a fresh Claude session after setup, then inspect `/tasks` during a delegated exploration. It displays the actual model and, on supported versions, explicitly configured effort. CLI syntax/manifest validation is not a live model run. Model aliases are provider-resolved; this package does not guarantee quota access or that every backend honors every effort.

Sources checked 2026-09-23: [built-in agents and Explore](https://code.claude.com/docs/en/sub-agents#built-in-subagents), [native frontmatter](https://code.claude.com/docs/en/sub-agents#frontmatter-reference), [model precedence](https://code.claude.com/docs/en/sub-agents#choose-a-model), [force model](https://code.claude.com/docs/en/sub-agents#run-every-subagent-on-one-model).

## Preview-based configuration

From the plugin checkout, for a confirmed target project:

```text
python -B scripts/feather_config.py check --project /absolute/project --scope project
python -B scripts/feather_config.py install --project /absolute/project --scope project
python -B scripts/feather_config.py install --project /absolute/project --scope project --apply --expected-plan <returned-plan-id>
python -B scripts/feather_config.py show --project /absolute/project --scope project
```

Mutating operations preview by default; applying requires the same operation/arguments and expected plan ID. `update` refreshes owned templates while retaining model choices. `remove` removes only intact managed roles, state and the marked policy block. Unrelated file content and handoff records remain. Existing unowned Explore or Feather role files, malformed policy markers and edited managed files are conflicts; the tool will not adopt or replace them automatically. Reconcile custom content explicitly instead of bypassing ownership checks.

Change one field without resetting the others:

```text
python -B scripts/feather_config.py model --project /absolute/project --scope project --set executor.effort=high
```

Use the returned plan ID with `--apply --expected-plan` to persist. Models/efforts are configuration values, not runtime availability promises. Per-task explicit model instructions win over role defaults; persistent settings change only when requested. `session` exports native `--agents` definitions for a new session with requested overrides and performs no installation. It cannot change an already running child's effort.

## Updates, conflicts and removal

Plugin update refreshes templates/skills; run setup update in each owning scope to deploy them. Removing the plugin alone leaves external roles and CLAUDE.md policy. Remove the desired managed scopes first when removing delegation. User-wide and project installs are distinct; inspect both when a nearer project may shadow a user setting. Do not silently migrate or remove another scope.

Backups and conflict checks protect managed writes. Serialize setup/model operations; a sequence of filesystem changes is not a cross-process atomic transaction or a substitute for coordinating other editors. Inspect the returned state and recovery paths after a failure. Never remove unrelated user data to recover.

Project scope writes versionable project files but does not stage or commit them or add ignore rules. Decide whether to share `.claude/agents`, CLAUDE.md and managed configuration according to project policy; backup directories should remain local and may contain prior CLAUDE.md text. Setup does not modify Git rules automatically.

The policy's two-call automatic plan review limit is an agent instruction, not a hook-enforced counter. Preserve it in an active handoff across sessions; an explicit user request can authorize another review. Security/plan analysts have a read-only tool allowlist. Executors have Bash and write capabilities under normal Claude permission controls; no additional sandbox is created by this plugin.

## Automatic plan review switch

Default `off` disables automatic triggering; enabled mode `auto` performs risk-triggered review. Explicitly asking to review a plan works in either mode. Task/session instructions override the saved setting without changing files. The two-call automatic budget is separate; changing modes does not reset a logical plan's count or convert an unresolved verdict into READY.

```text
/cc-feather:auto-off project
/cc-feather:auto-on project
```

Without arguments (or with `session`), these commands set only the current conversation preference and write no files. `project` and `user` persist to an existing owned installation; they do not install missing roles. A separate task/session override still takes precedence over a saved change.

The corresponding scoped preview is:

```text
python -B scripts/feather_config.py review --project /absolute/project --scope project --review-mode off
```

Apply using the returned plan ID and matching arguments. Install accepts `--review-mode auto|off`; show/check report the saved mode and updates preserve it. A session-only instruction such as “disable automatic plan review for this session” does not invoke the configuration writer. The toggle is implemented in managed CLAUDE.md instructions, not a deterministic runtime gate.

## CLI details and diagnostics

Mutations require an explicit `--scope`; read-only show/check/session default to project and do not silently select the user installation. `show/check` include owning paths, `review_mode`, requested role choices, issues and warnings. Session export returns only the native agents object so it can be supplied to `--agents`; it does not install the policy or switch an already running session.

The script accepts model aliases/identifiers composed of letters, digits, dot, underscore, colon or hyphen, optionally followed by a numeric `[1m]`-style suffix. Effort syntax accepts low, medium, high, xhigh and max; backend support is a separate check. Unsupported identifier syntax is rejected rather than substituted.

An install/update/model/review/remove preview returns `plan_id`; applying requires that ID. Review and model changes preserve the installed role bodies/policy except the selected setting. Updating templates is the explicit update operation. Existing native-name collisions are reported even when declared in other Markdown filenames under the selected agents tree. Unsupported declaration syntax is treated as an inspection problem rather than assumed safe.

## Unprefixed role names and migration

Native names are scout, analyst, mech-executor, executor, security-executor and Explore. During setup, report existing same-name roles (including different filenames or subdirectories), preserve their files and ask the user how to resolve the conflict. Options include keeping the existing configuration, renaming the existing role, or backing it up and replacing it after explicit authorization. Do not automatically adopt or overwrite a role. Check applicable user/project precedence when definitions exist in different scopes.

For an owned legacy installation, run setup update in its owning scope. It previews migration from feather-* names, retains saved model/effort and review mode, and removes only intact owned legacy files. Occupied target names or modified owned files block migration until resolved by the user. Restart the session afterward. Model/review mutations and session export require migration first; removal of an intact legacy installation remains supported. Use the managed tool for migration, not manual edits to ownership state.
