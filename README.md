# cc-feather

**English** | [繁體中文](README.zh-TW.md)

A Claude Code plugin for codex-feather-compatible handoffs, scoped delegation, native Explore routing, setup and role model configuration. Requires Python 3.11+ and the standard library only.

## Install

Install from [GitHub](https://github.com/xenciscbc/cc-feather) in Claude Code:

```text
/plugin marketplace add xenciscbc/cc-feather
/plugin install cc-feather@cc-feather
```

Update an installed plugin from a shell, or through the `/plugin` interface in Claude Code:

```text
claude plugin update cc-feather@cc-feather
```

For a local checkout, add its absolute path as the marketplace instead. For development, run `claude --plugin-dir /absolute/path/to/cc-feather`. Start a fresh session after installation. See the [official plugin guide](https://code.claude.com/docs/en/plugins). After a later plugin update, run setup update for the components you installed and then start a fresh session; see [Updates and validation](#updates-and-validation).

## Skills

- `/cc-feather:handoff`: save, list, read or resume work; inspect, clear or seal completed history; capture source baselines.
- `/cc-feather:handoff-list`: list handoff work summaries (read-only, never resumes).
- `/cc-feather:handoff-save [work]`: save progress for the named work, or the current work when omitted.
- `/cc-feather:handoff-resume [work]`: resume the named work, or the sole unfinished one; asks when several remain.
- `/cc-feather:handoff-tidy [work names | all]`: tidy the existing handoff records; only you can run it. Without an argument it asks for a mode: Proposal (from the records alone, propose the next work and which records to merge and which are stale or incomplete), Full check (check every record against the current project, after stating its cost and waiting for your confirmation) or Selected check (check the named work), or you describe what you want in your own words. Work names run a Selected check and `all` a Full check. Checks are read-only and run no project code. It only proposes: merges, moved items and updated progress are written after your confirmation, and it never authorizes the work it recommends or starts handoff maintenance.
- `/cc-feather:setup`: inspect status first, then independently manage handoff maintenance rules, delegation policy plus native agents, or both.
- `/cc-feather:delegation`: load the main-agent workflow for dispatch, review, acceptance and recovery when needed.
- `/cc-feather:delegation-preview [plans, tickets or work]`: preview how the work would be delegated, without dispatching anything; see [Delegation preview](#delegation-preview).
- `/cc-feather:adversarial-review <attack scope> [paths or commit range] [disposable targets]`: run an Adversarial review you ask for, in either mode; see [Security-critical work](#security-critical-work).
- `/cc-feather:model`: inspect or configure model/effort, distinguishing task/session preferences from permanent settings.
- `/cc-feather:auto-on`: enable automatic plan review, code review, outcome verification and, for Security-critical claims, Adversarial review of plan-driven work. Main may then, without asking, commit such work before its passes, push it to branches it created for the work and open pull requests; landing on the default branch, release, reporting complete and ticket completion still wait for both passes, plus HELD for a Security-critical claim, or your accept-and-land decision.
- `/cc-feather:auto-off`: disable automatic review.
- `/cc-feather:stop-threshold <2–10|default> [session|project|user]`: set the [Stop threshold](#stop-threshold) of automatic review for this session, or save it in project or user scope.

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
| delegation | A separate delegation policy plus nine native agents; automatic plan review defaults off | Removes intact owned roles and delegation guidance while preserving handoff rules |
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
| Security-critical implementation | security-executor | opus | high |
| Post-implementation verification | verifier | opus | high |
| Post-implementation code review | reviewer | opus | high |
| Adversarial review | adversary | opus | high |

| Role | When to use | Deliverable and permissions |
| --- | --- | --- |
| scout | Bounded factual lookup: definitions, settings, references | Read-only locations and evidence; complex causal analysis goes elsewhere. In a review or security analysis it reads and searches only the files and directories main lists, and reports a missing list instead of reading. |
| Explore | Broad discovery of unfamiliar modules, entry points and calls | Read-only codebase map; deeper diagnosis goes to analyst. In a review or security analysis it reads and searches only the files and directories main lists, and reports a missing list instead of reading. |
| analyst | Root causes, impacts, security analysis, pre-implementation plan review | Read-only evidence, inferences and recommendations; READY/REVISE for plans. In a review or security analysis it reads and searches only the files and directories main lists, and reports a missing list instead of reading. |
| mech-executor | Repetitive edits with complete rules, scope and expected results | Writes only assigned files, for example applying an exact rename mapping |
| executor | Implementation requiring local design or engineering judgment | Writes and validates assigned files; returns missing architecture or requirements to Main |
| security-executor | Implementation affecting authorization, secrets, cryptography or trust boundaries | Writes assigned files and verifies both allowed behavior and abuse/denial cases |
| verifier | Independent check that completed work meets an exact claim | Runs checks and counterexamples without editing; CONFIRMED/REFUTED/INCONCLUSIVE. It reads the repository and runs its code only as [Repository safety](#repository-safety) allows. |
| reviewer | Independent review of the code implementing one claim | Compares commits from a base revision and reads the uncommitted files main lists, runs only the lint and type checks its brief names, never edits or runs tests; APPROVED/CHANGES_REQUESTED/INCONCLUSIVE. It reads the repository and runs its code only as [Repository safety](#repository-safety) allows. |
| adversary | Trying to break one Security-critical claim against the disposable targets its brief names | Read, Glob, Grep and Bash only; never fixes the code; HELD/BROKEN/INCONCLUSIVE. It changes a project file only when the brief lists that file as a fixture with its reset, never in a gated call. Its safety limits (this fixture rule, only disposable targets with synthetic data the brief names, no external hosts) are instructions to the model, not a sandbox: Bash can still reach the network and write files, and main compares the workspace before and after each call. It reads the repository and runs its code only as [Repository safety](#repository-safety) allows. |

Main owns understanding, decisions, integration and acceptance. Small or context-coupled tasks stay direct. Independent children have scoped contracts and exclusive write ownership; all are leaves and leave handoff and progress records to main. Read-only security analysis belongs to analyst, while the implementation of Security-critical changes belongs to security-executor.

Resolve model and effort independently: **explicit task request > applicable session preference > saved role configuration > package default**. “Use Sonnet to review this plan” keeps analyst duties/tools but selects Sonnet, retaining analyst's high effort unless overridden. Apply real native bindings; never silently substitute or pretend prompt text changed the runtime. A task override does not rewrite saved settings.

Automatic review is off by default; turn it on or off with the [switch](#automatic-review-switch). When on, it covers **plan-driven work**: work done from a plan, spec, ticket or conversation plan you agreed to.

| Step | When | Role | Passes with |
| --- | --- | --- | --- |
| Plan review | Before implementation | analyst | READY |
| Code review | After main's primary acceptance passes, or is recorded as not run under [Repository safety](#repository-safety) | reviewer, reading the diff itself | APPROVED |
| Outcome verification | After APPROVED | verifier | CONFIRMED |
| Adversarial review | For a Security-critical claim: in auto, once at the end, after the final check passes at the final commit; in `off`, after APPROVED and CONFIRMED at the same commit | adversary | HELD |

In brief; the [reference](docs/reference.md#automatic-review) states every rule in full:

- **Unplanned work** gets no automatic review, except that a Security-critical change, data migration or irreversible operation first needs a written plan that is reviewed and that you approve.
- **The plan is what you name.** Naming a plan, spec or ticket when you ask main to implement it is your agreement to it, and what you name decides its claims: a spec is one claim unless it lists its own, tickets of a spec are one plan with one claim per unfinished ticket, and a single ticket is its own plan and claim. A claim's implementer and reviewers read the claim and the spec parts it cites, not the whole spec.
- **Per-claim timing:** in auto, each claim gets its code review and then its verification as soon as it is implemented and committed, and a claim that depends on another starts only after that claim has a valid APPROVED and CONFIRMED. Those passes stay fixed when another claim of the plan changes the claim's files within what that other claim's own passing reviews judged.
- **What blocks a claim:** its acceptance as written is not met, existing behaviour is shown broken by a failing test or a reproduction, it introduces a security problem or data loss, or it deviates from the plan. Every other finding goes to the work's Follow-up record, and you decide whether a later plan fixes it.
- **Budget:** each step stops after as many consecutive automatic calls without a pass as the [Stop threshold](#stop-threshold), 2 by default, and waits for you. Counts belong to one session; in auto, passes, Adversarial review results and your decisions cross sessions in the plan's dispatch record under `.feather/dispatch/`, which main takes as written.
- **Final check and landing:** in auto, main may commit claims before their passes, push them to a branch it created for the work and open a pull request. Before landing, main runs the plan's overall acceptance checks and every claim's primary acceptance at the commit to be landed, and fixes a failure in the claim that caused it or in a fix claim. In auto, main then asks you once, at the end of the plan, listing each claim's passes, what is missing and what this flow does not check. Landing on the default branch, release, reporting complete and ticket completion wait for both passes, plus HELD for a Security-critical claim, or your accept-and-land decision.
- **Explicit requests** for any review work in either mode, run only what you asked for and use no automatic budget.
- **Cost:** at the default Stop threshold, one uninterrupted attempt makes at most 6 automatic calls per claim and 8 per Security-critical claim, and each reopened claim, final-check fix or approved deviation adds calls; the reference gives the formula for other values and how to lower the cost.

The full rules are in the [plan review](skills/delegation/references/plan-review.md), [code review](skills/delegation/references/code-review.md), [outcome verification](skills/delegation/references/outcome-verification.md) and [adversarial review](skills/delegation/references/adversarial-review.md) procedures; terms are defined in [CONTEXT.md](CONTEXT.md).

### Security-critical work

```text
/cc-feather:adversarial-review session token checks in src/auth, against the test server the plan names
/cc-feather:adversarial-review password reset flow HEAD~3..HEAD
```

A Security-critical claim changes a security guarantee at a trust boundary or a security control, such as authentication, authorization, sessions, credentials, cryptography or input validation; main recognises it by what it does, not by keywords. security-executor implements it, in `off` too. In `auto`, its plan first gets a read-only security analysis whose findings become security invariants in the claim's acceptance, then plan review. adversary tries to break the claim against disposable targets and answers HELD, BROKEN or INCONCLUSIVE. In `auto` it runs once, at the final commit after the final check passes there, and a BROKEN is recorded and listed for your decision at the end of the plan rather than fixed in the plan; in `off` it runs after a valid APPROVED and CONFIRMED at the same commit, and a BROKEN goes back to a fix. A vulnerability that predates the change becomes separate work in your tracker, and exploit details stay out of public records. `/cc-feather:adversarial-review` runs an Adversarial review whenever you ask, in either mode. The adversary's limits are instructions to the model: only your permission settings, hooks, the Claude Code sandbox or an isolated environment enforce them. See [Security-critical work](docs/reference.md#security-critical-work) in the reference.

### Repository safety

**When you review someone else's change, such as another person's pull request, branch or patch, say in your own message that it comes from someone else: a review runs your repository's code by default, and a change whose origin you do not state is run like your own.**

Reviews read the reviewed repository as attacker-controlled: their Git commands run in fixed forms that run no program the repository chose, a file is read only after link and location checks, and main compares the workspace before and after every call. Reviews do run the repository's code, such as tests, builds, linters and probes, on this machine by default. They stop only when you say in your own message that a change comes from someone else, or that code must not run, and then run it only in an isolated environment you name. For `git add`, commit, tag and push, main uses the programs your own Git configuration sets, hooks included. These rules are instructions to the model, not a sandbox; the [reference](docs/reference.md#repository-safety) lists every rule and the residual risks. See [ADR 0011](docs/adr/0011-reviews-treat-the-repository-as-hostile-by-instruction.md) and [ADR 0014](docs/adr/0014-reviews-execute-repository-code-by-default.md).

### Automatic review switch

```text
/cc-feather:auto-on
/cc-feather:auto-off
/cc-feather:auto-on project
/cc-feather:auto-off user
```

No argument (or `session`) changes this session only. `project` or `user` saves the choice in an existing setup installation of that scope. The `cc-feather:` plugin namespace remains; command names no longer repeat `feather-`. Default `off` disables automatic triggering; enabled mode `auto` reviews plan-driven work and lets main, without asking, commit its claims before their passes, push them to branches it created for the work and open pull requests that list the unaccepted claims; landing on the default branch, release, reporting complete and ticket completion still wait for both passes, plus HELD for a Security-critical claim, or your explicit accept-and-land decision (see Commit and Your decisions in the [reference](docs/reference.md#automatic-review)). Explicit review requests work in both modes. Saved changes preserve any separate task/session override. Show/check report the saved mode; updates preserve it. Toggling never resets a step's count for an existing plan or claim.

Permanent modes are stored below. Use the commands to change them: manually editing managed blocks causes ownership conflicts.

| Scope | Policy loaded by Claude | Synchronized management state |
| --- | --- | --- |
| project | `<project>/CLAUDE.md`, `.claude/CLAUDE.md` or AGENTS.md (see below) | `<project>/.claude/cc-feather/state.json` |
| user | `<Claude config directory>/CLAUDE.md` | `<Claude config directory>/cc-feather/state.json` |

The Claude config directory defaults to `~/.claude`, or `CLAUDE_CONFIG_DIR` when set. In `auto`, the delegation block contains the automatic review rules; in `off`, they are removed, so neither main nor subagents load them. A project-scope `off` keeps one line stating that automatic plan review is off in this project, so it overrides a user-scope `auto`: a task/session choice wins, then project guidance, then user guidance. A project installed `off` by an earlier version gets that line on its next review or setup update. Installations from earlier versions keep an `Automatic plan review mode:` line until setup update. Persistent toggles require the delegation component in that scope; handoff-only setup is insufficient. Fresh sessions load the saved mode.

In project scope, setup writes into an existing CLAUDE.md, else `.claude/CLAUDE.md`. Claude Code reads AGENTS.md only while no CLAUDE file exists, so in a project that relies on AGENTS.md setup asks first: write into the AGENTS file, or create a CLAUDE.md that imports it so Claude keeps reading it. The choice is saved and reused. See [project instruction file](docs/setup.md#project-instruction-file).

### Stop threshold

The Stop threshold is how many consecutive automatic calls without a pass stop a step of the automatic flow: one number from 2 to 10 for every step, 2 by default.

```text
/cc-feather:stop-threshold 4
/cc-feather:stop-threshold 4 project
/cc-feather:stop-threshold default user
```

Without a scope (or with `session`) it applies to this session only and writes nothing; `project` or `user` saves it in an existing delegation installation of that scope. Main uses your task or session choice, then the project's saved value, then the user's, then 2, and never changes it on its own. Changing it never changes a count. A higher value lets the flow keep trying longer without asking you, at a cost that grows faster than the value. See [Stop threshold](docs/reference.md#stop-threshold) in the reference.

### Delegation preview

```text
/cc-feather:delegation-preview docs/specs/my-feature.md
/cc-feather:delegation-preview TICKET-12 TICKET-13
/cc-feather:delegation-preview
```

Before implementing, see how main would split plans, tickets or unplanned work into claims and assignments: each role, model and effort with where the value comes from, what can run in parallel, the review steps with when each stops, and anything that would hold the work, such as a missing role or an input that is not yet a plan. The preview is read-only: it dispatches nothing, uses no review budget and writes no file, and it guides dispatch only in the session that made it. See [Delegation preview](docs/reference.md#delegation-preview) in the reference.

### Explore

Built-in Explore inherits the main model. A namespaced plugin scout alone cannot prevent its use, so setup deploys an exact-name native `Explore` with sonnet/low. If you already have an agent named Explore, it already overrides the built-in: setup installs none of its own, leaves yours untouched and warns that cc-feather does not manage its model (without a `model` field it uses the main model). Remove yours and setup update installs cc-feather's again.

Built-in general-purpose and Plan agents also run on the main model and cannot be overridden the same way, so the delegation policy tells main to delegate only to the cc-feather roles unless you ask for a built-in agent.

Saved settings do not prove execution: CLI/managed/nested definitions, force-model environment settings, provider restrictions or invocation arguments can change selection. Use a fresh session and `/tasks` to inspect actual model/effort. This avoids unintended expensive-model use; it does not guarantee fewer tokens. See [official subagent documentation](https://code.claude.com/docs/en/sub-agents).

## Design trade-offs

cc-feather prefers reviews that are bounded and predictable over reviews that try to check everything. Each choice below gives something up on purpose; the linked ADR records why. In auto, main also lists what the flow does not check when it asks you at the end of a plan.

- **Rules are instructions, not enforcement.** The review flow, repository safety and the role limits are instructions to the model. Tests keep the shipped texts consistent, but no hook or tool enforces them; hard limits come only from your permission settings, hooks, the sandbox or an isolated environment. ([ADR 0011](docs/adr/0011-reviews-treat-the-repository-as-hostile-by-instruction.md))
- **Reviews read a narrow reading set.** Each review judges one claim and reads only the claim and the spec parts it cites, so it is not judged against parts the claim never adopted and does not drown in unrelated findings. In exchange, a later claim's reviewer may not know an earlier claim's design intent; intent that spans tickets belongs in the spec, where plan review checks that each ticket cites what applies to it. ([ADR 0012](docs/adr/0012-claims-are-decided-by-what-the-user-names.md))
- **Each claim is reviewed when it is done, and keeps its passes.** A problem in an early claim is found before later claims build on it, and a later claim's reviewed change to a shared file no longer restarts the reviews of every earlier claim. In exchange, a property of an earlier claim that no rerun acceptance check covers can be broken without the final check noticing. ([ADR 0015](docs/adr/0015-each-claim-is-reviewed-when-done-and-keeps-its-passes.md#fixed-passes))
- **The final check reruns primary acceptance, not every item.** At the commit to be landed, main reruns the plan's overall checks and every claim's primary acceptance and fixes a failure once, in the claim that caused it or in a fix claim, instead of reopening every claim. Other acceptance items, and checks that cannot be rerun such as a manual check, are not repeated there. ([ADR 0015](docs/adr/0015-each-claim-is-reviewed-when-done-and-keeps-its-passes.md#the-final-check-and-fix-claims))
- **An attack step only for Security-critical claims, once at the end.** Code review reads the diff and outcome verification checks that the claim holds; neither tries to get around it, so Security-critical claims alone get a security analysis before plan review and an Adversarial review. In auto it runs once, at the final commit, instead of after every fix. In exchange, the commit it attacks was not judged as a whole by the claim's own code review and verification, a BROKEN is recorded for your decision instead of being fixed in the plan, and a Security-critical fix claim gets no Adversarial review. ([ADR 0009](docs/adr/0009-security-critical-claims-get-an-adversarial-review.md), [ADR 0015](docs/adr/0015-each-claim-is-reviewed-when-done-and-keeps-its-passes.md#adversarial-review-at-the-final-commit))
- **Only what the acceptance needs holds completion, except security.** A correctness problem outside the acceptance, or a regression that is only inferred, is recorded for a later plan instead of starting fix after fix; a security problem or data loss the change introduced still blocks. ([ADR 0013](docs/adr/0013-only-what-a-claims-acceptance-needs-holds-its-completion.md))
- **A bounded budget, not retrying until it passes.** Each step stops at the Stop threshold and waits for you, so a disagreement between main and a reviewer reaches you instead of spending more calls. ([ADR 0004](docs/adr/0004-consecutive-failure-review-budget.md), [ADR 0010](docs/adr/0010-the-stop-threshold-is-one-configurable-number.md))
- **Counts stay in their session; review state crosses sessions in a record taken as written.** A resumed session starts new counts and runs the final check again. In auto, passes, Adversarial review results and your decisions carry over in the plan's dispatch record, which main trusts as written, so an edit to it changes what main believes; in `off`, a claim that passed in an earlier session is reviewed again before landing. ([ADR 0002](docs/adr/0002-session-scoped-review-counts.md), [ADR 0015](docs/adr/0015-each-claim-is-reviewed-when-done-and-keeps-its-passes.md#the-dispatch-record))
- **Commit early, decide once at landing.** Main may commit and open pull requests before the passes, so a reclaimed environment loses nothing and every review judges a fixed commit; landing, release and completion still wait for the passes or your accept-and-land decision, which in auto you make once, at the end of the plan. ([ADR 0007](docs/adr/0007-commit-before-acceptance.md), [ADR 0008](docs/adr/0008-repository-authority-acceptance-and-gate-lifetime.md), [ADR 0015](docs/adr/0015-each-claim-is-reviewed-when-done-and-keeps-its-passes.md#the-decision-at-the-end))
- **Reviews run repository code by default, and read it as hostile.** A trust prompt in every session held up work continued from a handoff, so reviews now run its code unless you say a change comes from someone else; a change whose origin you do not state runs like your own. ([ADR 0014](docs/adr/0014-reviews-execute-repository-code-by-default.md))
- **Fresh context, usually the same model.** Each review gathers its own evidence in a fresh context but usually runs on main's model. Cost and model diversity are role settings you choose with `/cc-feather:model`, and how finely a plan is cut into claims stays with the planning step. ([ADR 0003](docs/adr/0003-review-cost-and-independence-stay-user-configured.md))

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
/cc-feather:handoff-tidy
/cc-feather:handoff-tidy login
```

Use existing `.feather/handoffs/<work>.md`, `history.md` and `archive/<batch>.md` without conversion. Read only summarizes; resume checks sources before authorized work. Completion archives with recoverable retries; history clearing/sealing needs an explicit selection. Baselines cover selected files and do not prove tests passed. Claude memory lookup is explicitly selected and read-only. Handoff tidy writes what you confirm through the same handoff tool and record format.

Claude and Codex must use the same project directory and coordinate one writer. There is no cross-session transaction lock or automatic worktree synchronization. Existing tracking choices and handoff ignore behavior are preserved.

## Updates and validation

Plugin updates refresh the package; run setup update for the selected components to refresh external deployments, then start a fresh session, because roles and guidance are loaded when a session starts. 0.27.0 adds `/cc-feather:handoff-tidy`, a command only you can run that proposes the next work, merges and stale or incomplete records from the handoff records, or checks the recorded items of named or all work against the current project without running project code, and writes only what you confirm. It changes no installed role definition or policy, so existing installations need only the plugin update and a fresh session; no `/cc-feather:setup update` is needed. To go back to 0.26.0, reinstall the 0.26.0 plugin; no setup update or remove is needed, and records the command wrote stay ordinary handoff records. 0.26.0 changes how a plan is reviewed in `auto`: each claim is reviewed when it is done and keeps its passes, the final check reruns every claim's primary acceptance and fixes a failure with fix claims, Adversarial review runs once at the final commit and its findings are recorded, a dispatch record carries review state across sessions, and main asks you once at the end. It changes only the delegation skill's procedures, not an installed role definition or policy, so existing installations need only the plugin update and a fresh session, which picks up the new procedures; no `/cc-feather:setup update` is needed. To go back to 0.25.0, reinstall the 0.25.0 plugin; no setup update or remove is needed, and earlier versions ignore dispatch records left under `.feather/dispatch/`. From 0.25.0, reviews run repository code without asking, and a review of someone else's change needs you to state that it comes from someone else. See [Repository safety](#repository-safety). In addition, installations from earlier versions keep their older guidance format until setup update, and check warns that delegation guidance is from an older template. Removing the plugin alone leaves native roles/guidance. Remove selected setup scopes first if those should go too; handoff data remains. Modified owned files are preserved as conflicts.

```text
/cc-feather:setup Update this project's installed roles and guidance, retaining models and review mode
/cc-feather:setup Remove this project's cc-feather-managed roles and guidance
```

For a user-scope installation, explicitly request user-scope update/removal. After removing the desired deployments, uninstall the package through Claude's plugin management interface.

See [handoff compatibility](docs/compatibility.md) and [setup validation](docs/setup-validation.md). Configuration/policy checks are not proof of a live Claude dispatch. Review-count and routing rules are model instructions, not hook-enforced workflow gates.

## Unprefixed role names and migration

Native names are scout, analyst, mech-executor, executor, security-executor, verifier, reviewer, adversary and Explore. When another agent already uses one of these names, setup installs every role except Explore with a `cc-` prefix (for example `cc-scout`) and lists the names in the delegation policy; the prefix then stays. Other agents' files are never adopted or overwritten. Explore keeps its exact name, and your own Explore is used instead of cc-feather's. A conflict on a `cc-` name still stops for your decision. Check applicable user/project precedence when definitions exist in different scopes.

For an owned legacy installation, run setup update in its owning scope. It previews migration from feather-* names, retains saved model/effort and review mode, and removes only intact owned legacy files. Occupied target names or modified owned files block migration until resolved by the user. Restart the session afterward. Model/review mutations and session export require migration first; removal of an intact legacy installation remains supported. Use the managed tool for migration, not manual edits to ownership state.

## Acknowledgements

The agent roles and the way they work together draw on [pilotfish](https://github.com/Nanako0129/pilotfish) by Nanako0129.
