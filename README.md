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
| scout | Bounded factual lookup: definitions, settings, references | Read-only locations and evidence; complex causal analysis goes elsewhere |
| Explore | Broad discovery of unfamiliar modules, entry points and calls | Read-only codebase map; deeper diagnosis goes to analyst |
| analyst | Root causes, impacts, security analysis, pre-implementation plan review | Read-only evidence, inferences and recommendations; READY/REVISE for plans |
| mech-executor | Repetitive edits with complete rules, scope and expected results | Writes only assigned files, for example applying an exact rename mapping |
| executor | Implementation requiring local design or engineering judgment | Writes and validates assigned files; returns missing architecture or requirements to Main |
| security-executor | Implementation affecting authorization, secrets, cryptography or trust boundaries | Writes assigned files and verifies both allowed behavior and abuse/denial cases |
| verifier | Independent check that completed work meets an exact claim | Runs checks and counterexamples without editing; CONFIRMED/REFUTED/INCONCLUSIVE |
| reviewer | Independent review of the code implementing one claim | Reads the diff itself from a base revision, runs non-modifying static checks, never edits or runs tests; APPROVED/CHANGES_REQUESTED |
| adversary | Trying to break one Security-critical claim against the disposable targets its brief names | Read, Glob, Grep and Bash only; never fixes the code; HELD/BROKEN/INCONCLUSIVE. It changes a project file only when the brief lists that file as a fixture with its reset, never in a gated call. Its safety limits (this fixture rule, only disposable targets with synthetic data the brief names, no external hosts) are instructions to the model, not a sandbox: Bash can still reach the network and write files, and main compares the workspace before and after each call. |

Main owns understanding, decisions, integration and acceptance. Small or context-coupled tasks stay direct. Independent children have scoped contracts and exclusive write ownership; all are leaves and leave handoff and progress records to main. Read-only security analysis belongs to analyst, while the implementation of Security-critical changes belongs to security-executor.

Resolve model and effort independently: **explicit task request > applicable session preference > saved role configuration > package default**. “Use Sonnet to review this plan” keeps analyst duties/tools but selects Sonnet, retaining analyst's high effort unless overridden. Apply real native bindings; never silently substitute or pretend prompt text changed the runtime. A task override does not rewrite saved settings.

Automatic review is off by default; turn it on or off with the [switch](#automatic-review-switch). When on, it covers **plan-driven work**: work done from a plan, spec, ticket or conversation plan you agreed to.

| Step | When | Role | Passes with |
| --- | --- | --- | --- |
| Plan review | Before implementation | analyst | READY |
| Code review | After main's primary acceptance passes | reviewer, reading the diff itself | APPROVED |
| Outcome verification | After APPROVED | verifier | CONFIRMED |
| Adversarial review | After APPROVED and CONFIRMED at the same commit, for a Security-critical claim | adversary | HELD |

- **Unplanned work** gets no automatic review, except that a Security-critical change, data migration or irreversible operation first needs a written plan that is reviewed and that you approve.
- **Budget:** each step counts consecutive automatic calls that do not pass, per plan for plan review and per claim for code review, verification and Adversarial review. An automatic pass resets the count; when the count reaches the [Stop threshold](#stop-threshold), 2 by default, the step stops, which never counts as passing, and the work waits for you. A step's next automatic call for the same work needs your request exactly while its count is at or above the Stop threshold, and runs without one while it is below. Failed, interrupted and protocol-failure calls count, and within a session renaming or switching reviewers or models never resets the count; a resumed session starts a new one. An Adversarial review that returns INCONCLUSIVE counts as not passing.
- **Re-review during implementation:** a plan is reviewed again only after a material deviation, a change to its outcome, scope or acceptance, or the discovery of a security control or invariant the plan lacks; touching boundary code the plan already covers is not one. Dependent work stops, and the revised plan must pass plan review and get your approval before that work continues; that plan review needs your request only while plan review's count is at or above the Stop threshold. Wording changes and adjustments within the approved outcome, scope and acceptance are not re-reviewed as a plan; the code they touch still goes through code review and verification with its claim.
- **Findings:** blocking ones (correctness, security, data loss, regression, deviation from the plan) must be fixed or rejected with evidence. Non-blocking ones are listed in the final report, or become separate follow-up work when a handoff is active.
- **Not passed:** a claim without APPROVED is unreviewed: it is not landed on the default branch, released or reported complete. A fix after REFUTED goes through code review again before the verifier rechecks it. A claim without a valid CONFIRMED is unverified and is not landed, released or reported complete either. A Security-critical claim without a valid HELD is not landed, released or reported complete either; the fix for a BROKEN goes through code review, verification and Adversarial review again, and when that step stops or a BROKEN stays unresolved, an active handoff records that the claim is pending acceptance with its Adversarial review missing, even if it had no note before. Verification keeps counting across fixes and resets only on an automatic CONFIRMED, so, with K the Stop threshold, a claim refuted K times in a row stops after K − 1 automatically rechecked fixes. An active handoff records what remains unresolved. After a pass, the note says the claim is pending acceptance and names what is still missing; it is removed only when the claim is landed, released or reported complete, or cancelled with its commits decided, so an approval alone, as from an explicit review in `off`, never lets the claim reach the default branch. A deferral keeps the note and a waiver stays recorded in it. Your accept-and-land decision is the only exception (see Your decisions).
- **Validity:** a pass holds only for what it judged. Changing a claim's files or what they depend on reopens its code review and verification; a change only to the environment reopens verification; for any other change main says why the pass still holds. For a Security-critical claim, HELD is reopened by a change to the claim's files or dependencies, to a test target's definition, start-up, version or configuration, or by another change sharing its security assumptions; a test target's reset and test-induced changes to its synthetic data are not an environment change and reopen neither HELD nor verification. When a change sharing those assumptions belongs to a new claim and the claim it shares them with is already accepted, the new claim owns the composed review and the accepted claim is not reopened; only that trigger is excepted, so a change to the accepted claim's own files or dependencies, or to a test target, still reopens its HELD. Updating a ticket's status does not reopen anything. A reopened step continues its count, which is zero after an automatic pass and unchanged after an explicit pass that cleared a stop; the reopened call needs your request again exactly while that count is at or above the Stop threshold.
- **Commit:** in auto, main may commit a claim of plan-driven work before its passes, push it to a branch it created for the work and open a pull request that lists the claims still unaccepted, without asking. It asks before pushing to a branch that already existed and that it did not create; in a resumed session a branch counts as its own only when an active handoff records that it created it for this work. Before a gated review or verification, main commits only when that call needs a commit. Opening a pull request is not permission to merge it, a pass is not a request to land or release, and your explicit instruction not to commit or not to push wins; a claim whose review or verification then lacks its commit is reported blocked. For a claim gated only because an active handoff records it as unreviewed, unverified or pending acceptance, main may make the local commit a review or verification needs without asking, and asks before pushes and pull requests, as in `off`. For all these claims, main lands the claim on the remote default branch, releases it, reports it complete or marks its ticket done only with a valid APPROVED and CONFIRMED, plus a valid HELD for a Security-critical claim, or with your accept-and-land decision. A cancelled claim's commits left on a branch stay listed as unaccepted until you decide to revert them, keep them off the default branch or accept and land them; a branch carrying them is not landed before that. Pushed history is never rewritten, so a fix is a new commit, and landing a branch lands every claim on it. Each review, verification and Adversarial review of such a claim judges a named commit with a clean workspace. The default branch is the one the remote's HEAD names, or a protected or shared branch you name. On the default branch, commits made before the passes are labelled unaccepted and pushed only after both passes, plus HELD for a Security-critical claim, or your accept-and-land decision, or with your explicit permission; until then main reminds you that a reclaimed environment would lose them. In `off`, nothing else changes.
- **Release checks:** an acceptance item that exists only after an authorised operation, such as a tag after its commit, is checked and reported by main after the operation; verification covers the rest before it.
- **Your decisions:** when a step waits for you, main records what you decide as one of re-review, deferral, cancellation, changed acceptance, waiver or accept and land, with its scope. A waiver names the finding or missing pass it waives, stays visible with its remaining risk and never counts as READY, APPROVED, CONFIRMED or HELD, so a waived claim the acceptance gate covers is landed on the default branch, released or reported complete only after a later pass or your accept-and-land decision. A work-in-progress push you allow can move its commits to the default branch, but it is neither a release nor completion. Accept and land is your explicit acceptance of a named claim without one or both passes, or of a Security-critical claim without its HELD: main records the commit it accepts, the missing passes and the remaining risk, and for a missing HELD the known vulnerabilities, keeps them visible in reports and any active handoff, and the acceptance gate then no longer holds back landing, release or completion of that claim; a later relevant change ends it, and one recorded in an active handoff still holds in a resumed session until such a change. Saying the work is done counts as acceptance only after main confirms it with you and records it as accept and land; saying "continue" or turning auto off does not accept a known defect.
- **Authority:** a pass grants no new authority. READY lets already authorized work continue without another routine confirmation.
- **Explicit requests** for a plan review, code review, verification or Adversarial review (including `/cc-feather:adversarial-review`) work in either mode, run only what you asked for and do not use the automatic budget; their verdicts never reset a step's count. In auto, when one passes a step the automatic flow had stopped, the automatic flow resumes from there.
- **After a stop:** if you explicitly request a stopped step again and it passes, it clears the stop and leaves the count unchanged, and in auto the automatic flow continues to the next step. Any later automatic call in that step for the same work, such as the review of a fix, needs your request exactly while the count is at or above the Stop threshold; that call is still part of the automatic flow, so a pass resets the count and a non-pass stops the step again. An explicit review or verification made before the automatic flow reached that step does not count as that step's pass.
- **Asking for a review:** in auto, a review you ask for is automatic when the flow is due to run that step, and explicit when the step has stopped or you ask outside the flow; main states which before dispatching. For implemented work whose plan has no plan review in this session, main first asks as under Implemented before plan review.
- **Implemented before plan review:** in auto, when work is already implemented but its plan has no plan review in this session (no automatic plan review and no decision of yours on it), for example because it was implemented in another session, outside Claude or while review was off, main asks before any review whether to run plan review first or go straight to code review. It names any record of an earlier plan review it found but does not treat it as a pass. Plan review first is an automatic call that covers the whole plan; going straight to code review records the missing READY as a waiver for the implemented claims. Claims not yet implemented still get plan review first. A plan already reviewed by the automatic flow, stopped or decided in this session follows the usual rules, without asking again.
- **Retries:** every attempted call counts, including a generic retry after a temporary failure, and a stopped step is never dispatched again as a retry. A missing role or fresh context found before dispatch is not a call.
- **Lost state:** when the count, verdicts or blockers cannot be established in the session, for example after context compaction, which does not start a new session, main treats the step as stopped and asks you. Each review result states the current count.
- **Cost:** in one uninterrupted attempt in a session, with K the Stop threshold, a plan with N claims, S of them Security-critical, makes at least 1 + 2N + S automatic calls and up to about K + K(K+1)N + K³S, since a claim makes at most K(K+1) (up to K verification calls, between which up to K − 1 fixes each get up to K code reviews, plus up to K code reviews before the first verification) and a Security-critical claim at most K³ + K² + K (also up to K Adversarial reviews, between which up to K − 1 fixes after a BROKEN each get up to K(K+1) code review and verification calls, whose counts restart after their passes). At the default K = 2 that is, in one uninterrupted attempt, at most 6 calls per claim, 14 per Security-critical claim and about 2 + 6N + 8S per plan; at K = 10 it is 110, 1110 and about 10 + 110N + 1000S. The bounds grow faster than K because each fix is reviewed and verified again. A plan with a Security-critical claim also gets one security analysis by analyst per plan or shared trust boundary before plan review; each reopened claim or material deviation you approve adds calls, including up to K plan reviews for each deviation; the default roles run on opus/high. To lower it, keep the Stop threshold low or change a role with `/cc-feather:model`, for example `verifier.effort=medium`; package defaults stay unchanged. How finely a plan is cut into claims is decided where the plan is written, such as a spec, planning or ticket-splitting skill, not by cc-feather.
- **Independence:** each review runs in a fresh context and gathers its own evidence, but usually on the same model as main. For model diversity, set a different model for analyst or reviewer with `/cc-feather:model`. cc-feather cannot see or guarantee main's model, and switching a role's model never resets a step's count. A second opinion from another vendor's model, if you have one, is an explicit request outside this flow.

**Which document is the plan.** The plan is what you name when you ask main to implement something; naming it is your agreement to it.

- **A spec, or some of its tickets:** the spec with those tickets is one plan, reviewed once. Each unfinished ticket in that scope is one claim, and its `Blocked by` lines are its dependencies.
- **A single ticket:** that ticket is the plan, with its spec given as context to plan review, code review and outcome verification.
- **A ticket that belongs to no spec** is its own plan. **A spec without tickets** keeps the claims it lists, or is one claim when it lists none.
- **Example:** `docs/specs/login.md` has unfinished tickets 01, 02 and 03, and 03 is `Blocked by` 02. "Implement the login spec" makes one plan with three claims: one plan review, and 03 waits for 02. "Implement ticket 02" in a fresh session makes ticket 02 the plan, with `login.md` as context.
- **Already covered:** if a plan in this session already covers the work you name, that plan continues with no new plan review, keeping its count, verdicts and blockers. Naming a ticket can neither repeat a review nor escape a stopped one.
- **Partial overlap:** a new plan that partly overlaps one in this session inherits its unresolved verdicts and blockers for the overlapping tickets. Where that plan had stopped, the overlapping work keeps its count and stop and gains no new automatic calls while that count is at or above the Stop threshold: an automatic READY of the new plan does not clear that stop, while an explicit pass covering the work does. Independent new work is counted on its own.
- **Resumed session:** an unresolved verdict that an active handoff records for a spec's plan applies to that spec's tickets when you name them; likewise, one recorded for a ticket's plan still restricts that ticket when you later name the whole spec. In either mode, each restriction lasts until a later review passes it or you cancel the work, change its acceptance or waive it; asking for a re-review lifts it only when that review passes, and a deferral keeps it. Counts and passing verdicts do not carry over: in auto, an unfinished plan is reviewed again, and in either mode finished tickets are not redone. Without an active handoff record, no restriction carries over. Before landing, release or completion, a claim that passed in an earlier session is reviewed and verified again, and a Security-critical claim gets Adversarial review again, unless its ticket was set to a done value after both passes (plus HELD for a Security-critical claim) or your accept-and-land decision and nothing relevant changed since. A claim whose handoff note says it is pending acceptance stays gated and needs both passes, plus HELD for a Security-critical claim, in the new session, unless the note records your accept-and-land decision and nothing relevant changed since, or its ticket was set to a done value as above. For a plan with an implemented claim, main first asks as under Implemented before plan review.
- **Nothing left:** when every ticket in the named scope is finished, main reports that nothing is left to implement.
- **Ticket status:** after a claim passes (both passes, plus HELD for a Security-critical claim) and is committed, and once any postcondition such as a release tag holds, main sets its ticket to the completion value your tracker convention defines for done work, such as `resolved`, noting the version or commit; without one, it reports which tickets it considers done. After an accept-and-land decision main does the same and notes the decision and its remaining risk. A ticket counts as finished when its status has one of the convention's completion values, such as one for work that will not be done, or you say it is done; without a defined value main asks. Finished only means it is not redone: a ticket counts as accepted only when it was set to a done value after both passes (plus HELD for a Security-critical claim) or your accept-and-land decision and nothing relevant changed since, and a value for work that will not be done, such as `wontfix`, is set only when you cancel and never counts as acceptance.
- **Finding the tickets:** main recognises a spec's tickets by an explicit link such as a `Spec:` line or parent reference, a shared feature directory, or you naming them. It looks first at your project's instructions (CLAUDE.md or AGENTS.md, and any file they point to) for where tickets live. Without such a note it searches, and because a repository-wide search can skip files that version control ignores and hidden directories, an empty result does not count as none: it also looks in likely ignored or hidden directories directly. It asks when what you name matches no plan or several, and states which tickets it used. When a spec's tickets still cannot be found, a spec that lists its own claims keeps that list; a spec that refers to its own tickets or claims without listing its claims makes main ask you, before plan review or implementation, whether to point to them or treat it as one claim; a spec that refers to none is one claim, provided it has its own acceptance. The preview flags a plan that refers to its own tickets or claims it cannot find.
- **Telling main where tickets live:** add a line to your project's CLAUDE.md or AGENTS.md, or a file it points to, saying where specs and tickets live, for example "Tickets: `.scratch/<feature>/issues/`, linked to specs in `docs/specs/` by a `Spec:` line". A planning tool's setup may write this note for you. If that instructions file is not committed, other checkouts do not have the note, and main falls back to searching.
- **Disagreement:** a spec that lists claims and also has tickets must agree with all of them, finished or not; a mismatch is a blocker for you to settle.
- **Claim changes:** main never edits a spec or ticket to add claims unless you authorise it: when a review needs claims added, split or changed, you or your planning step decide, and main edits only after your authorisation, keeping a mapping from old claims to new ones and their unresolved blockers.
- **Not yet a plan:** a spec with neither tickets nor scope and acceptance of its own, such as a spec template without an acceptance section, is not yet a plan; main completes it and confirms the completed version with you first.
- **Plan-mode and conversation plans:** their claims live in that plan's text, so another session cannot see them; this is an accepted limit. A new session uses such a plan only from its original text, an available record or a version you confirm.
- **Where files live:** cc-feather does not decide where specs live or whether tickets are committed; it uses what the implementing session has.

The full rules are in the [plan review](skills/delegation/references/plan-review.md), [code review](skills/delegation/references/code-review.md), [outcome verification](skills/delegation/references/outcome-verification.md) and [adversarial review](skills/delegation/references/adversarial-review.md) procedures; terms are defined in [CONTEXT.md](CONTEXT.md).

### Security-critical work

```text
/cc-feather:adversarial-review session token checks in src/auth, against the test server the plan names
/cc-feather:adversarial-review password reset flow HEAD~3..HEAD
```

A Security-critical claim is one whose outcome includes a Security-critical change: a change to a security guarantee at a trust boundary, or to the implementation or configuration of a security control, including where sensitive data goes and how untrusted data is interpreted downstream. Authentication, authorization, sessions and CSRF, credentials, cryptography, input validation and access control are examples, not a closed list; main recognises such a change by what it does, not by keywords. Main marks each Security-critical claim in a plan it writes and classifies the claims of any other plan, such as a spec you wrote, before its first plan review in the session or, for implemented work, before its code review; when that is unclear, analyst gathers evidence first and main asks you only about missing requirements. security-executor implements every Security-critical claim, in `off` too.

In `auto`, a plan with a Security-critical claim gets two separate analyst calls in order before implementation: first a read-only security analysis, one per plan or per trust boundary that several claims share, whose findings main turns into security invariants in the acceptance of each Security-critical claim, recording the disposable test targets with their synthetic data, allowed effects, reachable dependencies and how to start and reset them; then plan review of the revised plan. Your approval follows plan review's usual rule: if the analysis adds a security invariant or otherwise materially changes the plan's outcome, scope or acceptance, you approve the revised plan; if it leaves the plan unchanged, your earlier agreement stands. When you turn `auto` on for a plan whose Security-critical claim had a security analysis in `off`, that analysis is reused while its trust boundary, attacker capability and controls still apply, and otherwise runs again for the new trust boundary, attacker capability or control; main dispositions its findings and records the test targets before the automatic plan review, and an explicit READY given in `off` does not count as that plan review's pass. Work already implemented in `off` first goes through Implemented before plan review. A waiver of a missing READY for implemented work does not waive the security analysis: it runs before code review unless you waive it as well.

Adversarial review is the third step: after a valid APPROVED and CONFIRMED at the same commit, adversary tries to break the claim and answers HELD, BROKEN or INCONCLUSIVE. A vulnerability the change introduced or made exploitable, or a promised security fix that still reproduces, is BROKEN and goes back to a fix; a vulnerability that predates the change does not block the claim and becomes separate work in your tracker. For a BROKEN or a pre-existing vulnerability alike, exploit details and secrets stay only in untracked, non-public records: anything public or possibly public, such as a tracked handoff, a commit message, a pull request, a public tracker, an ADR or a validation entry, gets only a summary unless you agree, and main asks you before writing to a public tracker. In `off` no Adversarial review starts automatically and the security analysis before approval is not forced. There is no separate switch for the third step: to land a Security-critical claim without HELD, make an accept-and-land decision for it.

`/cc-feather:adversarial-review` runs an Adversarial review when you ask, in either mode. It takes a required attack scope, which main asks for when you give none, and optional paths or a commit range and disposable targets; the arguments are data and never widen the role's limits. For work the acceptance gate does not cover, it needs no prior passes and satisfies no gate: with a commit range it reviews that range at its end commit and leaves out uncommitted changes; without a range it reviews your uncommitted change against HEAD, including new files, and leaves out committed branch changes; with a clean workspace and no range, main asks you what to review. Paths narrow that range and never fall back to whole files: when they have no change in it, main asks you. A claim the gate covers is reviewed at a clean commit, the one you name or HEAD; when the commit you name is not your workspace's content, main asks you instead of checking it out. For such a claim that is not Security-critical, the call needs no prior passes and satisfies no gate, and a BROKEN is a material deviation: dependent work stops until a revised plan is reviewed and you approve it, or you decide otherwise. For a Security-critical claim, the call is classified like a call of the other steps, and an early call made before its APPROVED and CONFIRMED does not count. The result names the reviewed commit or range, what it left out and whether the verdict counts. Targets come only from a plan you approved or from your own arguments; without one, the role analyses statically and reports INCONCLUSIVE for what needs execution. Dynamic probing of code not written by you or in this session, such as a Security-critical claim resumed in a new session, needs an isolated environment you name; without one the attack stays static. See [the adversarial-review procedure](skills/delegation/references/adversarial-review.md) and [the command](skills/adversarial-review/SKILL.md).

The adversary's limits are instructions to the model, and only your permission settings (permission mode and allow, ask and deny rules, including managed settings), hooks, the Claude Code sandbox (not available on native Windows) and an external isolated environment such as a container or virtual machine enforce them: in bypassPermissions mode, or with broad allow rules, its Bash commands can run without any prompt or classifier check, and in Claude Code's auto mode a classifier, not you, approves them; see the official [permission modes documentation](https://code.claude.com/docs/en/permission-modes) for how each mode treats commands.

### Automatic review switch

```text
/cc-feather:auto-on
/cc-feather:auto-off
/cc-feather:auto-on project
/cc-feather:auto-off user
```

No argument (or `session`) changes this session only. `project` or `user` saves the choice in an existing setup installation of that scope. The `cc-feather:` plugin namespace remains; command names no longer repeat `feather-`. Default `off` disables automatic triggering; enabled mode `auto` reviews plan-driven work and lets main, without asking, commit its claims before their passes, push them to branches it created for the work and open pull requests that list the unaccepted claims; landing on the default branch, release, reporting complete and ticket completion still wait for both passes, plus HELD for a Security-critical claim, or your explicit accept-and-land decision (see Commit and Your decisions above). Explicit review requests work in both modes. Saved changes preserve any separate task/session override. Show/check report the saved mode; updates preserve it. Toggling never resets a step's count for an existing plan or claim.

Permanent modes are stored below. Use the commands to change them: manually editing managed blocks causes ownership conflicts.

| Scope | Policy loaded by Claude | Synchronized management state |
| --- | --- | --- |
| project | `<project>/CLAUDE.md`, `.claude/CLAUDE.md` or AGENTS.md (see below) | `<project>/.claude/cc-feather/state.json` |
| user | `<Claude config directory>/CLAUDE.md` | `<Claude config directory>/cc-feather/state.json` |

The Claude config directory defaults to `~/.claude`, or `CLAUDE_CONFIG_DIR` when set. In `auto`, the delegation block contains the automatic review rules; in `off`, they are removed, so neither main nor subagents load them. A project-scope `off` keeps one line stating that automatic plan review is off in this project, so it overrides a user-scope `auto`: a task/session choice wins, then project guidance, then user guidance. A project installed `off` by an earlier version gets that line on its next review or setup update. Installations from earlier versions keep an `Automatic plan review mode:` line until setup update. Persistent toggles require the delegation component in that scope; handoff-only setup is insufficient. Fresh sessions load the saved mode.

In project scope, setup writes into an existing CLAUDE.md, else `.claude/CLAUDE.md`. Claude Code reads AGENTS.md only while no CLAUDE file exists, so in a project that relies on AGENTS.md setup asks first: write into the AGENTS file, or create a CLAUDE.md that imports it so Claude keeps reading it. The choice is saved and reused. See [project instruction file](docs/setup.md#project-instruction-file).

### Stop threshold

The Stop threshold is how many consecutive automatic calls without a pass stop a step of the automatic flow: one number from 2 to 10 for plan review, code review, outcome verification and Adversarial review alike, 2 by default. Tell main a value for the current task or session, which writes nothing, or save one in project or user scope with the configuration tool's `review --stop-threshold` (see [Stop threshold](docs/setup.md#stop-threshold)), where `default` removes the saved value. Main uses your task or session choice, then the value the project guidance states, then the value the user guidance states, then 2, so a project's saved value overrides your user value. Main never changes it on its own and states it and its source whenever a review decision comes up; a session choice does not carry into a new or resumed session and is not written into a handoff. A guidance value outside 2–10 is skipped and reported; when main cannot tell whether you made a task or session choice, for example after context compaction, it treats the affected steps as stopped and asks you.

```text
/cc-feather:stop-threshold 4
/cc-feather:stop-threshold 4 project
/cc-feather:stop-threshold default user
```

`/cc-feather:stop-threshold` sets it, or asking main in your own words does the same. Without a scope (or with `session`) it applies to this session only and writes nothing, and main reminds you that a new or resumed session uses the saved value and that context compaction may drop the session value. `project` or `user` saves it in an existing delegation installation of that scope after a preview, without a further confirmation; it never installs delegation, and guidance from an older template needs setup update first. A value outside 2–10 or an unclear scope is refused or clarified before anything is applied or written.

Changing the Stop threshold never changes a count. A stopped step whose count is now below the new value resumes, a step whose count reaches or exceeds it stops at once, a step an explicit pass had cleared stays cleared, and main lists the steps that resumed or stopped. A value you save in project or user scope in this conversation replaces any earlier task or session choice in this conversation, and the Stop threshold is resolved again from the saved values, so this session uses what a new session would; a user value saved where the project states its own is reported as overridden by it. This is the reverse of the review mode, where a saved change keeps a separate task or session override. A higher value lets the flow keep trying longer without asking you, at the cost under Cost above, which grows faster than K.

### Delegation preview

```text
/cc-feather:delegation-preview docs/specs/my-feature.md
/cc-feather:delegation-preview TICKET-12 TICKET-13
/cc-feather:delegation-preview
```

Before implementing, see how main would split one or more plans or tickets, or a description of unplanned work: for each claim, every assignment and every part main keeps, with the role, model, effort and where each value comes from (task, session, saved or default). Plans and claims are identified as [above](#roles-and-routing), and the preview lists the tickets it used. A short note says what can run in parallel and what must wait. The plan review, code review and outcome verification roles, and for a plan with a Security-critical claim the security analysis and Adversarial review roles, are listed once at the end, with the number of plans, claims and Security-critical claims and when each step stops (the Stop threshold in effect and its source, at most K(K+1) calls per claim, or K³ + K² + K for a Security-critical claim, in one uninterrupted attempt, each reopened claim or approved material deviation adding calls); unplanned work is marked as outside that flow, and in `off` the preview says the flow will not run while explicit review requests remain available. It also flags roles that are not installed, an Explore of your own whose settings cc-feather cannot see, inputs that are not yet plans, a plan that refers to its own tickets or claims it cannot find or whose claim list disagrees with its tickets, claims without their own acceptance, in `auto` a plan with implemented claims and no plan review in this session (main will ask whether to run plan review first), unplanned work that makes a Security-critical change, migrates data or is irreversible and that in `auto` needs a reviewed plan first, and work that needs exploration first. Without an argument it previews the plan under discussion, and asks when there is none or several.

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

Plugin updates refresh the package; run setup update for the selected components to refresh external deployments, then start a fresh session, because roles and guidance are loaded when a session starts. 0.20.0 adds the Stop threshold and the `/cc-feather:stop-threshold` command and changes no role definition or guidance template, so existing installations need only the plugin update and a fresh session, and their guidance and state stay unchanged until a Stop threshold is saved. A 0.19.x or older configuration tool rejects a scope with a saved Stop threshold, so before going back to one, set it to `default` in that scope; a task or session choice needs nothing. 0.19.0 changes the executor, security-executor, adversary and reviewer role definitions, so run setup update in every scope where delegation is installed, then start a fresh session; until then `check` reports `role_update_required: true` with those four roles from an older template, and `model`, `review` and session export ask for setup update first, in `auto` and in `off`. 0.18.0 adds the `adversary` role and changes the executor role definition, the delegation guidance and the automatic review guidance, so run setup update in every scope where delegation is installed, then start a fresh session; until then `check` reports `role_update_required: true` (adversary is missing, and the executor role and the delegation guidance are from an older template), `model`, `review` and session export ask for setup update first, in `auto` and in `off`, and a required Adversarial review is blocked because adversary is missing. 0.17.0 changes the reviewer and analyst role definitions and the automatic review guidance, so run setup update in every scope where delegation is installed, then start a fresh session; until then `check` reports the roles from an older template, and `model`, `review` and session export ask for setup update first, in `auto` and in `off`. In addition, installations from earlier versions keep their older guidance format until setup update, and check warns that delegation guidance is from an older template. Removing the plugin alone leaves native roles/guidance. Remove selected setup scopes first if those should go too; handoff data remains. Modified owned files are preserved as conflicts.

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
