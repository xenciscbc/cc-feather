# cc-feather

**English** | [繁體中文](README.zh-TW.md)

A Claude Code plugin for codex-feather-compatible handoffs, scoped delegation, native Explore routing, setup and role model configuration. Requires Python 3.11+ and the standard library only.

## Install

After publishing this version to [GitHub](https://github.com/xenciscbc/cc-feather):

```text
/plugin marketplace add xenciscbc/cc-feather
/plugin install cc-feather@cc-feather
```

For a local checkout, add its absolute path as the marketplace instead. For development, run `claude --plugin-dir /absolute/path/to/cc-feather`. Start a fresh session after installation. See the [official plugin guide](https://code.claude.com/docs/en/plugins). After a later plugin update, run setup update for the components you installed and then start a fresh session; see [Updates and validation](#updates-and-validation).

## Skills

- `/cc-feather:handoff`: save, list, read or resume work; inspect, clear or seal completed history; capture source baselines.
- `/cc-feather:handoff-list`: list handoff work summaries (read-only, never resumes).
- `/cc-feather:handoff-save [work]`: save progress for the named work, or the current work when omitted.
- `/cc-feather:handoff-resume [work]`: resume the named work, or the sole unfinished one; asks when several remain.
- `/cc-feather:setup`: inspect status first, then independently manage handoff maintenance rules, delegation policy plus native agents, or both.
- `/cc-feather:delegation`: load the main-agent workflow for dispatch, review, acceptance and recovery when needed.
- `/cc-feather:model`: inspect or configure model/effort, distinguishing task/session preferences from permanent settings.
- `/cc-feather:auto-on`: enable automatic plan review, code review and outcome verification of plan-driven work.
- `/cc-feather:auto-off`: disable automatic review.

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
| handoff | An independent maintenance policy in the instruction file | Removes the reminder only; records and the plugin handoff command remain |
| delegation | A separate delegation policy plus eight native agents; automatic plan review defaults off | Removes intact owned roles and delegation guidance while preserving handoff rules |
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

Each component has its own managed block in the scope's instruction file, with independent ownership recorded in the scope's cc-feather/state.json. Handoff rules do not start a record automatically: after a user requests creation or continuation, maintain that work at milestones, blockers and completion. Reading/listing alone does not activate maintenance.

Legacy installations combined both policies in one block. Migration checks ownership and splits them while preserving models and review mode. Removing delegation alone must retain the existing handoff reminder. Modified owned files and occupied names are preserved for the user's decision.

## Everyday workflow

1. Open Claude Code in the target project and install the plugin. Handoffs are immediately available.
2. For delegation, run `/cc-feather:setup Install only delegation policy and agents for this project`. Explicitly request user scope to share the installation across projects. Start a fresh session afterward. Before installing, remove or disable any other delegation or orchestration rules and agents in the instruction files Claude loads, including the user-scope CLAUDE.md: cc-feather does not detect them, and two sets of rules would both apply and can conflict.
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
| Factual lookup | scout | sonnet | low |
| Broad exploration | Explore | sonnet | low |
| Analysis, security analysis, plan review | analyst | opus | high |
| Mechanical implementation | mech-executor | sonnet | medium |
| General implementation | executor | opus | medium |
| Security-sensitive implementation | security-executor | opus | high |
| Post-implementation verification | verifier | opus | high |
| Post-implementation code review | reviewer | opus | high |

| Role | When to use | Deliverable and permissions |
| --- | --- | --- |
| scout | Bounded factual lookup: definitions, settings, references | Read-only locations and evidence; complex causal analysis goes elsewhere |
| Explore | Broad discovery of unfamiliar modules, entry points and calls | Read-only codebase map; deeper diagnosis goes to analyst |
| analyst | Root causes, impacts, security analysis, pre-implementation plan review | Read-only evidence, inferences and recommendations; READY/REVISE for plans |
| mech-executor | Repetitive edits with complete rules, scope and expected results | Writes only assigned files, for example applying an exact rename mapping |
| executor | Implementation requiring local design or engineering judgment | Writes and validates assigned files; returns missing architecture or requirements to Main |
| security-executor | Implementation affecting authorization, secrets, cryptography or trust boundaries | Writes assigned files and verifies both allowed behavior and abuse/denial cases |
| verifier | Independent check that completed work meets an exact claim | Runs checks and counterexamples without editing; CONFIRMED/REFUTED/INCONCLUSIVE |
| reviewer | Independent review of the code implementing one claim | Reads the diff itself from a base revision, runs non-modifying static checks, never edits or runs tests; APPROVED/CHANGES_REQUESTED |

Main owns understanding, decisions, integration and acceptance. Small or context-coupled tasks stay direct. Independent children have scoped contracts and exclusive write ownership; all are leaves and leave handoff and progress records to main. Read-only security analysis belongs to analyst, while security implementation belongs to security-executor.

Resolve model and effort independently: **explicit task request > applicable session preference > saved role configuration > package default**. “Use Sonnet to review this plan” keeps analyst duties/tools but selects Sonnet, retaining analyst's high effort unless overridden. Apply real native bindings; never silently substitute or pretend prompt text changed the runtime. A task override does not rewrite saved settings.

Automatic review is off by default; turn it on or off with the [switch](#automatic-review-switch). When on, it covers **plan-driven work**: work done from a plan, spec, ticket or conversation plan you agreed to.

| Step | When | Role | Passes with |
| --- | --- | --- | --- |
| Plan review | Before implementation | analyst | READY |
| Code review | After main's primary acceptance passes | reviewer, reading the diff itself | APPROVED |
| Outcome verification | After APPROVED | verifier | CONFIRMED |

- **Unplanned work** gets no automatic review, except that a security-boundary change, data migration or irreversible operation first needs a written plan that is reviewed and that you approve.
- **Budget:** each step makes at most two automatic calls per plan or claim. Running out never counts as passing; the work stops and waits for you. Within a session, renaming or switching reviewers or models does not reset the count; a resumed session starts a new one.
- **Findings:** blocking ones (correctness, security, data loss, regression, deviation from the plan) must be fixed or rejected with evidence. Non-blocking ones are listed in the final report, or become separate follow-up work when a handoff is active.
- **Not passed:** a claim without APPROVED is unreviewed: it is not reported complete or committed. A fix after REFUTED goes straight to the verifier recheck and is reported as not code-reviewed. An active handoff records what remains unresolved until it is resolved.
- **Authority:** a pass grants no new authority. READY lets already authorized work continue without another routine confirmation.
- **Explicit requests** for a plan review, code review or verification work in either mode, run only what you asked for and do not use the automatic budget.

The full rules are in the [plan review](skills/delegation/references/plan-review.md), [code review](skills/delegation/references/code-review.md) and [outcome verification](skills/delegation/references/outcome-verification.md) procedures; terms are defined in [CONTEXT.md](CONTEXT.md).

### Automatic review switch

```text
/cc-feather:auto-on
/cc-feather:auto-off
/cc-feather:auto-on project
/cc-feather:auto-off user
```

No argument (or `session`) changes this session only. `project` or `user` saves the choice in an existing setup installation of that scope. The `cc-feather:` plugin namespace remains; command names no longer repeat `feather-`. Default `off` disables automatic triggering; enabled mode `auto` reviews plan-driven work. Explicit review requests work in both modes. Saved changes preserve any separate task/session override. Show/check report the saved mode; updates preserve it. Toggling never resets an existing plan's call budget.

Permanent modes are stored below. Use the commands to change them: manually editing managed blocks causes ownership conflicts.

| Scope | Policy loaded by Claude | Synchronized management state |
| --- | --- | --- |
| project | `<project>/CLAUDE.md`, `.claude/CLAUDE.md` or AGENTS.md (see below) | `<project>/.claude/cc-feather/state.json` |
| user | `<Claude config directory>/CLAUDE.md` | `<Claude config directory>/cc-feather/state.json` |

The Claude config directory defaults to `~/.claude`, or `CLAUDE_CONFIG_DIR` when set. In `auto`, the delegation block contains the automatic review rules; in `off`, they are removed, so neither main nor subagents load them. A project-scope `off` keeps one line stating that automatic plan review is off in this project, so it overrides a user-scope `auto`: a task/session choice wins, then project guidance, then user guidance. A project installed `off` by an earlier version gets that line on its next review or setup update. Installations from earlier versions keep an `Automatic plan review mode:` line until setup update. Persistent toggles require the delegation component in that scope; handoff-only setup is insufficient. Fresh sessions load the saved mode.

In project scope, setup writes into an existing CLAUDE.md, else `.claude/CLAUDE.md`. Claude Code reads AGENTS.md only while no CLAUDE file exists, so in a project that relies on AGENTS.md setup asks first: write into the AGENTS file, or create a CLAUDE.md that imports it so Claude keeps reading it. The choice is saved and reused. See [project instruction file](docs/setup.md#project-instruction-file).

### Explore

Built-in Explore inherits the main model. A namespaced plugin scout alone cannot prevent its use, so setup deploys an exact-name native `Explore` with sonnet/low. If you already have an agent named Explore, it already overrides the built-in: setup installs none of its own, leaves yours untouched and warns that cc-feather does not manage its model (without a `model` field it uses the main model). Remove yours and setup update installs cc-feather's again.

Built-in general-purpose and Plan agents also run on the main model and cannot be overridden the same way, so the delegation policy tells main to delegate only to the cc-feather roles unless you ask for a built-in agent.

Saved settings do not prove execution: CLI/managed/nested definitions, force-model environment settings, provider restrictions or invocation arguments can change selection. Use a fresh session and `/tasks` to inspect actual model/effort. This avoids unintended expensive-model use; it does not guarantee fewer tokens. See [official subagent documentation](https://code.claude.com/docs/en/sub-agents).

## Handoff compatibility

```text
/cc-feather:handoff Save the current work
/cc-feather:handoff List handoffs
/cc-feather:handoff Read the login handoff
/cc-feather:handoff Resume the login work
/cc-feather:handoff Search completed history for login
/cc-feather:handoff-list
/cc-feather:handoff-save login
/cc-feather:handoff-resume login
```

Use existing `.feather/handoffs/<work>.md`, `history.md` and `archive/<batch>.md` without conversion. Read only summarizes; resume checks sources before authorized work. Completion archives with recoverable retries; history clearing/sealing needs an explicit selection. Baselines cover selected files and do not prove tests passed. Claude memory lookup is explicitly selected and read-only.

Claude and Codex must use the same project directory and coordinate one writer. There is no cross-session transaction lock or automatic worktree synchronization. Existing tracking choices and handoff ignore behavior are preserved.

## Updates and validation

Plugin updates refresh the package; run setup update for the selected components to refresh external deployments, then start a fresh session, because roles and guidance are loaded when a session starts. Until then, installations from earlier versions keep their older guidance format, and check warns that delegation guidance is from an older template. Removing the plugin alone leaves native roles/guidance. Remove selected setup scopes first if those should go too; handoff data remains. Modified owned files are preserved as conflicts.

```text
/cc-feather:setup Update this project's installed roles and guidance, retaining models and review mode
/cc-feather:setup Remove this project's cc-feather-managed roles and guidance
```

For a user-scope installation, explicitly request user-scope update/removal. After removing the desired deployments, uninstall the package through Claude's plugin management interface.

See [handoff compatibility](docs/compatibility.md) and [setup validation](docs/setup-validation.md). Configuration/policy checks are not proof of a live Claude dispatch. Review-count and routing rules are model instructions, not hook-enforced workflow gates.

## Unprefixed role names and migration

Native names are scout, analyst, mech-executor, executor, security-executor, verifier, reviewer and Explore. When another agent already uses one of these names, setup installs every role except Explore with a `cc-` prefix (for example `cc-scout`) and lists the names in the delegation policy; the prefix then stays. Other agents' files are never adopted or overwritten. Explore keeps its exact name, and your own Explore is used instead of cc-feather's. A conflict on a `cc-` name still stops for your decision. Check applicable user/project precedence when definitions exist in different scopes.

For an owned legacy installation, run setup update in its owning scope. It previews migration from feather-* names, retains saved model/effort and review mode, and removes only intact owned legacy files. Occupied target names or modified owned files block migration until resolved by the user. Restart the session afterward. Model/review mutations and session export require migration first; removal of an intact legacy installation remains supported. Use the managed tool for migration, not manual edits to ownership state.

## Acknowledgements

The agent roles and the way they work together draw on [pilotfish](https://github.com/Nanako0129/pilotfish) by Nanako0129.
