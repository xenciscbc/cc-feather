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
- `/cc-feather:delegation-preview [plans, tickets or work]`: preview how the work would be delegated, without dispatching anything; see [Delegation preview](#delegation-preview).
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
- **Budget:** each step counts consecutive automatic calls that do not pass, per plan for plan review and per claim for code review and verification. An automatic pass resets the count; two in a row without a pass stop the step, which never counts as passing, and the work waits for you. Failed, interrupted and protocol-failure calls count, and within a session renaming or switching reviewers or models never resets the count; a resumed session starts a new one.
- **Re-review during implementation:** a plan is reviewed again only after a material deviation, a change to its outcome, scope or acceptance. Dependent work stops, and the revised plan must pass plan review and get your approval before that work continues. Wording changes and adjustments within the approved outcome, scope and acceptance are not re-reviewed as a plan; the code they touch still goes through code review and verification with its claim.
- **Findings:** blocking ones (correctness, security, data loss, regression, deviation from the plan) must be fixed or rejected with evidence. Non-blocking ones are listed in the final report, or become separate follow-up work when a handoff is active.
- **Not passed:** a claim without APPROVED is unreviewed: it is not landed on the default branch, released or reported complete. A fix after REFUTED goes through code review again before the verifier rechecks it. A claim without a valid CONFIRMED is unverified and is not landed, released or reported complete either. Verification keeps counting across fixes and resets only on an automatic CONFIRMED, so a claim refuted twice in a row stops after one rechecked fix. An active handoff records what remains unresolved until it is resolved; a deferral keeps it recorded and a waiver stays recorded.
- **Validity:** a pass holds only for what it judged. Changing a claim's files or what they depend on reopens its code review and verification; a change only to the environment reopens verification; for any other change main says why the pass still holds. Updating a ticket's status does not reopen anything. A reopened step continues its count, which is zero after an automatic pass; after an explicit pass that cleared a stop, the reopened call needs your request again.
- **Commit:** in the automatic flow, and for any claim an active handoff records as unreviewed or unverified, main may commit a claim before its passes and push it to any branch other than the default branch, and may open a pull request that lists the claims still unaccepted; it lands the claim on the remote default branch, releases it, reports it complete or marks its ticket done only with a valid APPROVED and CONFIRMED. Pushed history is never rewritten, so a fix is a new commit, and landing a branch lands every claim on it. Each review and verification of such a claim judges a named commit with a clean workspace. The default branch is the one the remote's HEAD names, or a protected or shared branch you name. On the default branch, commits made before the passes are labelled unaccepted and pushed only after both passes or with your explicit permission; until then main reminds you that a reclaimed environment would lose them. In `off`, nothing else changes.
- **Release checks:** an acceptance item that exists only after an authorised operation, such as a tag after its commit, is checked and reported by main after the operation; verification covers the rest before it.
- **Your decisions:** when a step waits for you, main records what you decide as one of re-review, deferral, cancellation, changed acceptance or waiver, with its scope. A waiver stays visible with its remaining risk and never counts as READY, APPROVED or CONFIRMED, so a waived claim the acceptance gate covers is landed on the default branch, released or reported complete only after a later pass, or pushed to the default branch as a work-in-progress push you allow; saying "continue" or turning auto off does not accept a known defect.
- **Authority:** a pass grants no new authority. READY lets already authorized work continue without another routine confirmation.
- **Explicit requests** for a plan review, code review or verification work in either mode, run only what you asked for and do not use the automatic budget; their verdicts never reset a step's count. In auto, when one passes a step the automatic flow had stopped, the automatic flow resumes from there.
- **After a stop:** if you explicitly request a stopped step again and it passes, it clears the stop and leaves the count unchanged, and in auto the automatic flow continues to the next step. Because the count stays where it stopped, any later automatic call in that step for the same work, such as the review of a fix, needs your request; that call is still part of the automatic flow, so a pass resets the count and a non-pass stops the step again. An explicit review or verification made before the automatic flow reached that step does not count as that step's pass.
- **Asking for a review:** in auto, a review you ask for is automatic when the flow is due to run that step, and explicit when the step has stopped or you ask outside the flow; main states which before dispatching. For implemented work whose plan has no plan review in this session, main first asks as under Implemented before plan review.
- **Implemented before plan review:** in auto, when work is already implemented but its plan has no plan review in this session (no automatic plan review and no decision of yours on it), for example because it was implemented in another session, outside Claude or while review was off, main asks before any review whether to run plan review first or go straight to code review. It names any record of an earlier plan review it found but does not treat it as a pass. Plan review first is an automatic call that covers the whole plan; going straight to code review records the missing READY as a waiver for the implemented claims. Claims not yet implemented still get plan review first. A plan already reviewed by the automatic flow, stopped or decided in this session follows the usual rules, without asking again.
- **Retries:** every attempted call counts, including a generic retry after a temporary failure, and a stopped step is never dispatched again as a retry. A missing role or fresh context found before dispatch is not a call.
- **Lost state:** when the count, verdicts or blockers cannot be established in the session, for example after context compaction, which does not start a new session, main treats the step as stopped and asks you. Each review result states the current count.
- **Cost:** in one uninterrupted attempt in a session, a plan with N claims makes at least 1 + 2N automatic calls and up to about 2 + 6N, since a claim makes at most six (code review twice before and twice after a fix, verification twice); each reopened claim or material deviation you approve adds calls, including up to two plan reviews for each deviation; the default roles run on opus/high. To lower it, change a role with `/cc-feather:model`, for example `verifier.effort=medium`; package defaults stay unchanged. How finely a plan is cut into claims is decided where the plan is written, such as a spec, planning or ticket-splitting skill, not by cc-feather.
- **Independence:** each review runs in a fresh context and gathers its own evidence, but usually on the same model as main. For model diversity, set a different model for analyst or reviewer with `/cc-feather:model`. cc-feather cannot see or guarantee main's model, and switching a role's model never resets a step's count. A second opinion from another vendor's model, if you have one, is an explicit request outside this flow.

**Which document is the plan.** The plan is what you name when you ask main to implement something; naming it is your agreement to it.

- **A spec, or some of its tickets:** the spec with those tickets is one plan, reviewed once. Each unfinished ticket in that scope is one claim, and its `Blocked by` lines are its dependencies.
- **A single ticket:** that ticket is the plan, with its spec given as context to plan review, code review and outcome verification.
- **A ticket that belongs to no spec** is its own plan. **A spec without tickets** keeps the claims it lists, or is one claim when it lists none.
- **Example:** `docs/specs/login.md` has unfinished tickets 01, 02 and 03, and 03 is `Blocked by` 02. "Implement the login spec" makes one plan with three claims: one plan review, and 03 waits for 02. "Implement ticket 02" in a fresh session makes ticket 02 the plan, with `login.md` as context.
- **Already covered:** if a plan in this session already covers the work you name, that plan continues with no new plan review, keeping its count, verdicts and blockers. Naming a ticket can neither repeat a review nor escape a stopped one.
- **Partial overlap:** a new plan that partly overlaps one in this session inherits its unresolved verdicts and blockers for the overlapping tickets. Where that plan had stopped, the overlapping work keeps its count and stop and gains no new automatic calls: an automatic READY of the new plan does not clear that stop, while an explicit pass covering the work does. Independent new work is counted on its own.
- **Resumed session:** an unresolved verdict that an active handoff records for a spec's plan applies to that spec's tickets when you name them; likewise, one recorded for a ticket's plan still restricts that ticket when you later name the whole spec. In either mode, each restriction lasts until a later review passes it or you cancel the work, change its acceptance or waive it; asking for a re-review lifts it only when that review passes, and a deferral keeps it. Counts and passing verdicts do not carry over: in auto, an unfinished plan is reviewed again, and in either mode finished tickets are not redone. Without an active handoff record, no restriction carries over. Before landing, release or completion, a claim that passed in an earlier session is reviewed and verified again, unless its ticket is finished. For a plan with an implemented claim, main first asks as under Implemented before plan review.
- **Nothing left:** when every ticket in the named scope is finished, main reports that nothing is left to implement.
- **Ticket status:** after a claim passes and is committed, and once any postcondition such as a release tag holds, main sets its ticket to the completion value your tracker convention defines for done work, such as `resolved`, noting the version or commit; without one, it reports which tickets it considers done. A ticket counts as finished when its status has one of the convention's completion values, such as one for work that will not be done, or you say it is done; without a defined value main asks.
- **Finding the tickets:** main recognises a spec's tickets by an explicit link such as a `Spec:` line or parent reference, a shared feature directory, or you naming them. It looks first at your project's instructions (CLAUDE.md or AGENTS.md, and any file they point to) for where tickets live. Without such a note it searches, and because a repository-wide search can skip files that version control ignores and hidden directories, an empty result does not count as none: it also looks in likely ignored or hidden directories directly. It asks when what you name matches no plan or several, and states which tickets it used. When a spec's tickets still cannot be found, a spec that lists its own claims keeps that list; a spec that refers to its own tickets or claims without listing its claims makes main ask you, before plan review or implementation, whether to point to them or treat it as one claim; a spec that refers to none is one claim, provided it has its own acceptance. The preview flags a plan that refers to its own tickets or claims it cannot find.
- **Telling main where tickets live:** add a line to your project's CLAUDE.md or AGENTS.md, or a file it points to, saying where specs and tickets live, for example "Tickets: `.scratch/<feature>/issues/`, linked to specs in `docs/specs/` by a `Spec:` line". A planning tool's setup may write this note for you. If that instructions file is not committed, other checkouts do not have the note, and main falls back to searching.
- **Disagreement:** a spec that lists claims and also has tickets must agree with all of them, finished or not; a mismatch is a blocker for you to settle.
- **Claim changes:** main never edits a spec or ticket to add claims unless you authorise it: when a review needs claims added, split or changed, you or your planning step decide, and main edits only after your authorisation, keeping a mapping from old claims to new ones and their unresolved blockers.
- **Not yet a plan:** a spec with neither tickets nor scope and acceptance of its own, such as a spec template without an acceptance section, is not yet a plan; main completes it and confirms the completed version with you first.
- **Plan-mode and conversation plans:** their claims live in that plan's text, so another session cannot see them; this is an accepted limit. A new session uses such a plan only from its original text, an available record or a version you confirm.
- **Where files live:** cc-feather does not decide where specs live or whether tickets are committed; it uses what the implementing session has.

The full rules are in the [plan review](skills/delegation/references/plan-review.md), [code review](skills/delegation/references/code-review.md) and [outcome verification](skills/delegation/references/outcome-verification.md) procedures; terms are defined in [CONTEXT.md](CONTEXT.md).

### Automatic review switch

```text
/cc-feather:auto-on
/cc-feather:auto-off
/cc-feather:auto-on project
/cc-feather:auto-off user
```

No argument (or `session`) changes this session only. `project` or `user` saves the choice in an existing setup installation of that scope. The `cc-feather:` plugin namespace remains; command names no longer repeat `feather-`. Default `off` disables automatic triggering; enabled mode `auto` reviews plan-driven work. Explicit review requests work in both modes. Saved changes preserve any separate task/session override. Show/check report the saved mode; updates preserve it. Toggling never resets a step's count for an existing plan or claim.

Permanent modes are stored below. Use the commands to change them: manually editing managed blocks causes ownership conflicts.

| Scope | Policy loaded by Claude | Synchronized management state |
| --- | --- | --- |
| project | `<project>/CLAUDE.md`, `.claude/CLAUDE.md` or AGENTS.md (see below) | `<project>/.claude/cc-feather/state.json` |
| user | `<Claude config directory>/CLAUDE.md` | `<Claude config directory>/cc-feather/state.json` |

The Claude config directory defaults to `~/.claude`, or `CLAUDE_CONFIG_DIR` when set. In `auto`, the delegation block contains the automatic review rules; in `off`, they are removed, so neither main nor subagents load them. A project-scope `off` keeps one line stating that automatic plan review is off in this project, so it overrides a user-scope `auto`: a task/session choice wins, then project guidance, then user guidance. A project installed `off` by an earlier version gets that line on its next review or setup update. Installations from earlier versions keep an `Automatic plan review mode:` line until setup update. Persistent toggles require the delegation component in that scope; handoff-only setup is insufficient. Fresh sessions load the saved mode.

In project scope, setup writes into an existing CLAUDE.md, else `.claude/CLAUDE.md`. Claude Code reads AGENTS.md only while no CLAUDE file exists, so in a project that relies on AGENTS.md setup asks first: write into the AGENTS file, or create a CLAUDE.md that imports it so Claude keeps reading it. The choice is saved and reused. See [project instruction file](docs/setup.md#project-instruction-file).

### Delegation preview

```text
/cc-feather:delegation-preview docs/specs/my-feature.md
/cc-feather:delegation-preview TICKET-12 TICKET-13
/cc-feather:delegation-preview
```

Before implementing, see how main would split one or more plans or tickets, or a description of unplanned work: for each claim, every assignment and every part main keeps, with the role, model, effort and where each value comes from (task, session, saved or default). Plans and claims are identified as [above](#roles-and-routing), and the preview lists the tickets it used. A short note says what can run in parallel and what must wait. The plan review, code review and outcome verification roles are listed once at the end, with the number of plans and claims and when each step stops (two consecutive automatic calls without a pass, at most six calls per claim in one uninterrupted attempt, each reopened claim or approved material deviation adding calls); unplanned work is marked as outside that flow, and in `off` the preview says the flow will not run while explicit review requests remain available. It also flags roles that are not installed, an Explore of your own whose settings cc-feather cannot see, inputs that are not yet plans, a plan that refers to its own tickets or claims it cannot find or whose claim list disagrees with its tickets, claims without their own acceptance, in `auto` a plan with implemented claims and no plan review in this session (main will ask whether to run plan review first), unplanned security-boundary, data-migration or irreversible work that in `auto` needs a reviewed plan first, and work that needs exploration first. Without an argument it previews the plan under discussion, and asks when there is none or several.

The preview is read-only: main produces it alone, dispatches no subagent, starts no review, uses no review budget and writes no file. It runs only through this command; asking in conversation does not trigger it. It shows the settings already in effect, including a session `auto-on`/`auto-off`; to try another model or effort, change it with `/cc-feather:model` and preview again. The preview guides dispatch only in the session that made it: when implementation follows there, main dispatches according to it and reports each difference with its reason. A preview from another session is a reference; dispatch there may differ from it without being reported. Model and effort values are configured, not confirmed at execution. The command ships with the plugin, so after a plugin update it needs only a fresh session, not a setup update. See [the preview procedure](skills/delegation/references/preview.md).

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
