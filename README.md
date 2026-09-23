# cc-feather

**English** | [繁體中文](README.zh-TW.md)

A Claude Code plugin for codex-feather-compatible handoffs, scoped delegation, native Explore routing, setup and role model configuration. Requires Python 3.11+ and the standard library only.

## Install

After publishing this version to [GitHub](https://github.com/xenciscbc/cc-feather):

```text
/plugin marketplace add xenciscbc/cc-feather
/plugin install cc-feather@cc-feather
```

For a local checkout, add its absolute path as the marketplace instead. For development, run `claude --plugin-dir /absolute/path/to/cc-feather`. Start a fresh session after installation. See the [official plugin guide](https://code.claude.com/docs/en/plugins).

## Skills

- `/cc-feather:handoff`: save, list, read or resume work; inspect, clear or seal completed history; capture source baselines.
- `/cc-feather:setup`: inspect status first, then independently manage handoff maintenance rules, delegation policy plus native agents, or both.
- `/cc-feather:model`: inspect or configure model/effort, distinguishing task/session preferences from permanent settings.
- `/cc-feather:auto-on`: enable risk-triggered automatic plan review.
- `/cc-feather:auto-off`: disable automatic plan review.

Handoff commands work after plugin installation. Setup can install handoff maintenance rules, delegation (policy plus agents), or both. For example:

```text
/cc-feather:setup Install only delegation policy and agents for this project
/cc-feather:model Show this project's role settings
/cc-feather:model Permanently set this project's executor effort to high
```

Setup inspects status first, asks only for missing operation/component/scope choices, previews changes, checks ownership/conflicts and keeps backups. It does not modify the main model, concurrency, settings.json or handoff records. Model changes update native frontmatter outside the plugin cache; setup updates preserve saved choices. See [setup and lifecycle](docs/setup.md).

## Setup: inspect status, then select components

A bare `/cc-feather:setup` first checks project and user installation status, reporting each component as installed, absent, conflicted or requiring migration. It then asks what to install, update, remove or inspect, and in which scope. If a scope was already specified, it checks only that scope. Choices already supplied are reused.

| Component | Installed content | Removal behavior |
| --- | --- | --- |
| handoff | An independent CLAUDE.md maintenance policy | Removes the reminder only; records and the plugin handoff command remain |
| delegation | A separate delegation policy plus six native agents; automatic plan review defaults off | Removes intact owned roles and delegation guidance while preserving handoff rules |
| both | Both components | Applies the selected operation together; preserves records and unrelated settings |

Specify the full request to avoid unnecessary questions:

```text
/cc-feather:setup Install only handoff maintenance rules for this project
/cc-feather:setup Install only delegation policy and agents for this project
/cc-feather:setup Install both components for this project
/cc-feather:setup Update only this project's handoff rules
/cc-feather:setup Remove only this project's delegation, keeping handoff
/cc-feather:setup Show user-scope installation status
```

Installing both adds missing components without resetting installed ones. Updating both refreshes installed components only; removing both removes installed components only.

Each component has its own managed CLAUDE.md block, with independent ownership recorded in the scope's cc-feather/state.json. Handoff rules do not start a record automatically: after a user requests creation or continuation, maintain that work at milestones, blockers and completion. Reading/listing alone does not activate maintenance.

Legacy installations combined both policies in one block. Migration checks ownership and splits them while preserving models and review mode. Removing delegation alone must retain the existing handoff reminder. Modified owned files and occupied names are preserved for the user's decision.

## Everyday workflow

1. Open Claude Code in the target project and install the plugin. Handoffs are immediately available.
2. For delegation, run `/cc-feather:setup Install only delegation policy and agents for this project`. Explicitly request user scope to share the installation across projects. Start a fresh session afterward.
3. Describe the work normally. Main chooses a suitable role, or you can name a role/model. Small tasks stay with Main.
4. Save progress with `/cc-feather:handoff Save this work`, then resume in another session with `/cc-feather:handoff Resume the named work`.

These are natural-language requests to Claude, not additional slash commands:

```text
Use scout to locate the login route and its tests; return locations only.
Use Explore to map the modules and call relationships in the login flow.
Use analyst to diagnose the login failure without changing code.
Use analyst to review authorization and session security in the login flow.
Use executor to implement the agreed login error-handling plan.
Use mech-executor to apply this exact rename mapping without changing behavior.
Use security-executor to fix the confirmed authorization bypass and verify allowed and denied cases.
Use Sonnet to review this implementation plan.
```

## Configure models and effort

```text
/cc-feather:setup Check this project's installation and automatic review mode
/cc-feather:model Show this project's role models and effort
/cc-feather:model For this session, use Sonnet for analyst and keep high effort
/cc-feather:model Permanently set this project's executor to Opus with medium effort
/cc-feather:model Permanently set user-scope Explore to Haiku with low effort
```

A task-specific request takes precedence over session preferences and saved settings; omitted fields retain the role setting. Task/session overrides need native Claude support. If the current tool cannot override effort, the skill explains the limitation and offers configuration export for a new session, or a permanent change if you choose it. Prompt text alone does not bind a model or effort.

## Roles and routing

| Role | Native name | Model | Effort |
| --- | --- | --- | --- |
| Factual lookup | scout | haiku | low |
| Broad exploration | Explore | haiku | low |
| Analysis, security analysis, plan review | analyst | opus | high |
| Mechanical implementation | mech-executor | sonnet | medium |
| General implementation | executor | opus | medium |
| Security-sensitive implementation | security-executor | opus | high |

| Role | When to use | Deliverable and permissions |
| --- | --- | --- |
| scout | Bounded factual lookup: definitions, settings, references | Read-only locations and evidence; complex causal analysis goes elsewhere |
| Explore | Broad discovery of unfamiliar modules, entry points and calls | Read-only codebase map; deeper diagnosis goes to analyst |
| analyst | Root causes, impacts, security analysis, pre-implementation plan review | Read-only evidence, inferences and recommendations; READY/REVISE for plans |
| mech-executor | Repetitive edits with complete rules, scope and expected results | Writes only assigned files, for example applying an exact rename mapping |
| executor | Implementation requiring local design or engineering judgment | Writes and validates assigned files; returns missing architecture or requirements to Main |
| security-executor | Implementation affecting authorization, secrets, cryptography or trust boundaries | Writes assigned files and verifies both allowed behavior and abuse/denial cases |

Main owns understanding, decisions, integration and acceptance. Small or context-coupled tasks stay direct. Independent children have scoped contracts and exclusive write ownership; all are leaves. Read-only security analysis belongs to analyst, while security implementation belongs to security-executor.

Resolve model and effort independently: **explicit task request > applicable session preference > saved role configuration > package default**. “Use Sonnet to review” keeps analyst duties/tools but selects Sonnet, retaining analyst's high effort unless overridden. Apply real native bindings; never silently substitute or pretend prompt text changed the runtime. A task override does not rewrite saved settings.

Automatic plan review can be explicitly enabled or disabled for a task/session. It is disabled by default. After enabling it, material risk triggers fresh-context review; explicit review requests work in either mode. Its default automatic budget is two calls including the initial review. Unresolved blockers after the second stop automatic submission; this never means automatic approval. Renaming, switching reviewers/models or starting a new session does not reset the count. Preserve it in an active handoff. Explicit user direction is required for another round. READY plus existing authority proceeds without a routine additional confirmation.

### Automatic review switch

```text
/cc-feather:auto-on
/cc-feather:auto-off
/cc-feather:auto-on project
/cc-feather:auto-off user
```

No argument (or `session`) changes this session only. `project` or `user` saves the choice in an existing setup installation of that scope. The `cc-feather:` plugin namespace remains; command names no longer repeat `feather-`. Default `off` disables automatic triggering; enabled mode `auto` triggers only on material risk. Explicit review requests work in both modes. Saved changes preserve any separate task/session override. Show/check report the saved mode; updates preserve it. Toggling never resets an existing plan's call budget.

Permanent modes are stored below. Use the commands to change them: manually editing managed blocks causes ownership conflicts.

| Scope | Policy loaded by Claude | Synchronized management state |
| --- | --- | --- |
| project | `<project>/CLAUDE.md` | `<project>/.claude/cc-feather/state.json` |
| user | `<Claude config directory>/CLAUDE.md` | `<Claude config directory>/cc-feather/state.json` |

The Claude config directory defaults to `~/.claude`, or `CLAUDE_CONFIG_DIR` when set. The managed line `Automatic plan review mode: off` disables review; `auto` enables it. Persistent toggles require the delegation component in that scope; handoff-only setup is insufficient. Project settings may supersede user settings; fresh sessions load the saved mode. Enabled review targets material risks such as security boundaries, data migration, irreversible operations and complex cross-module plans, rather than every task.

### Explore

Built-in Explore inherits the main model. A namespaced plugin scout alone cannot prevent its use, so setup deploys an exact-name native `Explore` with haiku/low. An existing custom Explore is a conflict, never silently overwritten.

Saved settings do not prove execution: CLI/managed/nested definitions, force-model environment settings, provider restrictions or invocation arguments can change selection. Use a fresh session and `/tasks` to inspect actual model/effort. This avoids unintended expensive-model use; it does not guarantee fewer tokens. See [official subagent documentation](https://code.claude.com/docs/en/sub-agents).

## Handoff compatibility

```text
/cc-feather:handoff Save the current work
/cc-feather:handoff List handoffs
/cc-feather:handoff Read the login handoff
/cc-feather:handoff Resume the login work
/cc-feather:handoff Search completed history for login
```

Use existing `.feather/handoffs/<work>.md`, `history.md` and `archive/<batch>.md` without conversion. Read only summarizes; resume checks sources before authorized work. Completion archives with recoverable retries; history clearing/sealing needs an explicit selection. Baselines cover selected files and do not prove tests passed. Claude memory lookup is explicitly selected and read-only.

Claude and Codex must use the same project directory and coordinate one writer. There is no cross-session transaction lock or automatic worktree synchronization. Existing tracking choices and handoff ignore behavior are preserved.

## Updates and validation

Plugin updates refresh the package; run setup update for the selected components to refresh external deployments. Removing the plugin alone leaves native roles/guidance. Remove selected setup scopes first if those should go too; handoff data remains. Modified owned files are preserved as conflicts.

```text
/cc-feather:setup Update this project's installed roles and guidance, retaining models and review mode
/cc-feather:setup Remove this project's cc-feather-managed roles and guidance
```

For a user-scope installation, explicitly request user-scope update/removal. After removing the desired deployments, uninstall the package through Claude's plugin management interface.

See [handoff compatibility](docs/compatibility.md) and [setup validation](docs/setup-validation.md). Configuration/policy checks are not proof of a live Claude dispatch. Review-count and routing rules are model instructions, not hook-enforced workflow gates.

## Unprefixed role names and migration

Native names are scout, analyst, mech-executor, executor, security-executor and Explore. During setup, report existing same-name roles (including different filenames or subdirectories), preserve their files and ask the user how to resolve the conflict. Options include keeping the existing configuration, renaming the existing role, or backing it up and replacing it after explicit authorization. Do not automatically adopt or overwrite a role. Check applicable user/project precedence when definitions exist in different scopes.

For an owned legacy installation, run setup update in its owning scope. It previews migration from feather-* names, retains saved model/effort and review mode, and removes only intact owned legacy files. Occupied target names or modified owned files block migration until resolved by the user. Restart the session afterward. Model/review mutations and session export require migration first; removal of an intact legacy installation remains supported. Use the managed tool for migration, not manual edits to ownership state.
