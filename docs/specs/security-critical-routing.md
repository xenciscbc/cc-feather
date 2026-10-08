# Security-critical work routing

Label: `ready-for-agent`

Vocabulary follows [CONTEXT.md](../../CONTEXT.md): Security-critical change, Security-critical claim and Adversarial review were added there while this design was settled. The design builds on the 0.17.0 review rules ([ADR 0006](../adr/0006-review-state-validity-and-completion.md), [ADR 0007](../adr/0007-commit-before-acceptance.md), [ADR 0008](../adr/0008-repository-authority-acceptance-and-gate-lifetime.md)). Every decision below was made by the user on 2026-10-08 in four grilling rounds, cross-checked by four independent Codex opinions; the full record, with the options not taken, is in the gitignored ticket `.scratch/security-critical-routing/issues/01-security-critical-routing.md`.

## Problem Statement

Work that touches authentication, authorization, sessions, credentials, cryptography, input handling or access control gets the same review flow as any other Claim. Today a material security-boundary change is routed to a read-only analyst security analysis, but that analysis does not feed the plan, nothing records which Claims are security-critical, and after implementation nobody tries to break the change: code review reads the diff without running it, and outcome verification checks that the Claim holds, not whether an attacker can get around it. A change that passes both can still introduce a bypass, or make an old flaw reachable, and land. The user wants security-critical work reviewed before approval, implemented by the security role, and attacked before it lands, by a role whose model and effort they can choose, without turning off mode into something else.

## Solution

Ship 0.18.0 with:

- a behavioural definition of a Security-critical change, classified per Claim when the Plan is written;
- before approval, two separate analyst calls: a security analysis whose findings main turns into security invariants in each Claim's acceptance, with the disposable test targets recorded, then plan review, then the user's approval;
- implementation by security-executor;
- after code review and outcome verification, a third step, Adversarial review, by a new native role `adversary` that tries to break the Claim at the same commit and answers HELD, BROKEN or INCONCLUSIVE; BROKEN blocks the Acceptance gate and loops back to a fix, while pre-existing vulnerabilities become separate work;
- an explicit-only command, `/cc-feather:adversarial-review`, for attacks the user asks for directly;
- off mode unchanged: no automatic third step and no forced pre-approval sequence.

## Claims

Claims are committed separately in the order C1–C7. Each Claim's acceptance ends with: the full `unittest discover` suite passes after its commit, and any existing assertion the Claim changes is updated in the same commit with the reason in the commit message.

| Claim | Outcome | Depends on |
| --- | --- | --- |
| C1 Vocabulary and classification | Security-critical changes are defined behaviourally and classified per Claim at plan time; the procedures use the glossary terms | — |
| C2 Pre-approval security analysis | Security analysis feeds the Plan as security invariants and test targets before plan review and approval, including for already-implemented work | C1 |
| C3 Adversarial review in the review state | The third step has its own state, verdicts, coverage, attribution, invalidation and place in the Acceptance gate | C1 |
| C4 The adversary role | A new managed native role with safety limits is installed, configured and detected like the others | — |
| C5 Explicit adversarial-review command | The user can run an Adversarial review directly, inside or outside the flow | C3, C4 |
| C6 Decision record and documents | ADR 0009, both READMEs, the setup documents and the always-loaded guidance describe the new flow | C1–C5 |
| C7 Release 0.18.0 | 0.18.0 is validated, recorded with its setup-update step and tagged after both passes and the user's go-ahead | C1–C6 |

### C1 acceptance

1. The procedures define a Security-critical change as in CONTEXT.md: a change to a security guarantee at a trust boundary, or to a security control's implementation or configuration, including where sensitive data goes and how untrusted data is interpreted downstream; authentication, authorization, sessions and CSRF, credentials, cryptography, input validation and access control are examples, not a closed list. Input validation counts where untrusted data crosses a trust boundary.
2. When the Plan is written, main marks each Security-critical claim in the Plan. When classification is unclear, main has analyst gather evidence (asset, attacker-controlled input, boundary, changed control) and asks the user only about missing requirements.
3. A material deviation keeps its existing meaning (a material change to outcome, scope or acceptance); in addition, discovering a security control or invariant the Plan lacks is a material deviation. Touching boundary code the Plan already covers is not.
4. The delegation skill's existing rule that a material security-boundary change gets an analyst security analysis, and plan review's rule for unplanned security work, use the term Security-critical change, matching CONTEXT.md's Unplanned work.

### C2 acceptance

1. For a Plan with a Security-critical claim, before approval: one analyst security analysis per Plan or shared trust boundary (read-only, findings only); main dispositions every finding into the Plan, turning accepted controls into security invariants in each Security-critical claim's acceptance and recording the disposable test targets with how to start and reset them, their synthetic data, their allowed effects and the dependencies they can reach; then plan review receives the revised Plan; then the user approves. Security analysis and plan review stay separate assignments.
2. Security analysis reopens only for a new trust boundary, a changed attacker capability or a materially revised control, and then covers only what changed, before plan review runs again.
3. For implemented work reaching review without plan-review state (the existing Implemented before plan review rule), a waiver of the missing READY does not waive security analysis: before code review of an implemented Security-critical claim, the security analysis and its dispositions run, or the user explicitly waives them, and either is recorded.
4. In off mode the pre-approval sequence is not forced, but the existing security-analysis rule for material security-boundary changes still applies.

### C3 acceptance

1. **Position.** In auto, a Security-critical claim gets Adversarial review after a valid APPROVED and a valid CONFIRMED, at the same unchanged commit. The Acceptance gate for a Security-critical claim requires a valid HELD as well, or the user's accept-and-land decision.
2. **Verdicts.** HELD: a bounded, adequate attempt found no violation. BROKEN: a vulnerability the change introduced or made exploitable (through a new route, permission or data flow, even if the vulnerable code is outside the diff), or a promised security fix that still reproduces; an evidenced violation may be BROKEN without running an unsafe exploit. INCONCLUSIVE: insufficient coverage, missing targets or uncertain attribution. A pre-existing vulnerability does not change the verdict.
3. **Coverage.** Each call reports the coverage it examined and the gaps it left. HELD requires no open gap. A call after BROKEN covers the fix and every open gap; a narrowed follow-up never closes a gap it did not examine.
4. **State.** The step keeps the shared review state: its own consecutive non-pass count (two stop it), INCONCLUSIVE after dispatch counts as a non-pass, a missing role found before dispatch is not a call and blocks the step with no substitute role, explicit and automatic calls are classified as for the other steps, and HELD does not cross sessions.
5. **Fixes.** A BROKEN fix goes through code review, outcome verification and Adversarial review again.
6. **Invalidation.** HELD is reopened by a change to the Claim's files or dependencies, to a test target's definition, start-up, version or configuration, or by another change that shares its security assumptions. The brief's reset procedure and test-induced changes to synthetic data do not reopen it, and do not reopen CONFIRMED.
7. **Composition.** Per Claim; when changes share security assumptions, the review covers the composed revision, including later fixes, separate landings and interactions across boundaries. When a new change shares assumptions with an already accepted Claim, the new Claim owns the composed review and its count, the accepted Claim is not reopened, a break attributed to the new change is its BROKEN, and a break unrelated to it is pre-existing work.
8. **Pre-existing vulnerabilities.** They become separate work in the project's tracker; when the tracker is public, main records only a summary and asks the user first.
9. **Decisions.** Accept and land may cover a missing HELD, naming per commit the missing review, known vulnerabilities and remaining risk. The pending-acceptance note names a missing Adversarial review. Off mode starts no automatic Adversarial review; existing notes, counts and obligations persist. There is no separate switch for the third step.
10. **Two-pass wording.** Every rule, glossary entry and guidance sentence that says landing, release or completion waits for "both passes" also covers HELD for Security-critical claims: the Acceptance gate, Commits before the passes, Pending acceptance, Ticket status and Resumed sessions in the review state; outcome verification's continuation after CONFIRMED; the delegation preview's review section and call estimate; the always-loaded automatic-review paragraph; CONTEXT.md's Automatic flow, Pending-acceptance claim, Acceptance gate and Accept and land; both READMEs.

### C4 acceptance

1. A managed native role `adversary`, routed in the delegation skill's table, tries to break one Claim and reports HELD, BROKEN or INCONCLUSIVE with examined coverage, open gaps and evidence; it never fixes.
2. Safety limits in its definition: it acts only on disposable, explicitly scoped targets with synthetic data named in the brief, within the effects and reachable dependencies the brief allows, and stops before a probe would leave that scope; no staging or production, no external hosts, no tool installation, no project edits (scratch outside the project); destructive actions only against the named synthetic fixtures; with no target it analyses statically and reports INCONCLUSIVE for what needs execution.
3. The configuration tool treats it like the other managed roles: default model and effort opus/high, configurable with the model command, installed by install and by setup update for installations that predate it, reported by show/check as needing update when missing, prefixed when the prefix applies, exported by session export, and covered by stale-template detection.

### C5 acceptance

1. `/cc-feather:adversarial-review` is an explicit-only command (model invocation disabled) listed in the plugin manifest, taking a required attack scope and optional paths or commit range and optional disposable targets; with no scope main asks.
2. Outside the automatic flow it reviews the workspace change or the named commit range, needs no prior passes and satisfies no gate. When it asks for the step the automatic flow is due to run, it is an automatic call and must meet C3's prerequisites. It works in off mode.
3. Its results follow C3's verdicts, coverage and pre-existing-vulnerability handling.

### C6 acceptance

1. A new ADR 0009 records the decisions above with the options not taken, and amends ADR 0008 by note.
2. Both READMEs describe the flow, the role, the command and the setup update; the setup documents list the new role and its defaults; the always-loaded automatic-review paragraph names the third step for Security-critical claims.

### C7 acceptance

1. The manifest version is 0.18.0; the validation entry and both READMEs say setup update is required in every scope where delegation is installed, followed by a fresh session, because a role is added and guidance changed.
2. The suite and both `claude plugin validate` commands pass on Windows; an upgrade from a 0.17.0 installation is exercised; the entry records which flows ran live and which did not.
3. The tag `v0.18.0` is created only after both passes and the user's go-ahead, after checking the manifest version and that the tag does not exist; it is then checked against the release commit and manifest.

## User Stories

1. As a user, I want security-critical work recognised by what it changes rather than by a keyword list, so that a log change that leaks tokens is not missed.
2. As a user, I want main to mark Security-critical claims in the Plan, so that I see before approval which Claims get the extra steps.
3. As a user, I want main to gather evidence before asking me whether something is security-critical, so that I am asked only what only I can answer.
4. As a user, I want a security analysis before I approve the Plan, so that I approve a plan that already accounts for the attack surface.
5. As a user, I want the analysis turned into explicit security invariants in each Claim's acceptance, so that verification and the attack check against them.
6. As a user, I want security analysis and plan review kept separate, so that each has a clear output and its own review state.
7. As a user, I want the analysis done once per Plan or shared boundary, so that I do not pay for it per Claim.
8. As a user, I want the test targets and how to reset them recorded in the Plan, so that the attack runs against something safe and repeatable.
9. As a user, I want discovering a missing control mid-implementation to count as a deviation, so that the Plan is reviewed again before work continues.
10. As a user, I want touching already-planned boundary code not to count as a deviation, so that ordinary work is not stalled.
11. As a user, I want security-critical Claims implemented by security-executor, so that the role with security-specific instructions does the change.
12. As a user, I want an independent role to try to break each Security-critical claim after review and verification, so that a bypass is found before it lands.
13. As a user, I want to choose that role's model and effort, so that I can spend more on the attack where it matters.
14. As a user, I want the attack to run on the same commit that passed review and verification, so that what was attacked is what lands.
15. As a user, I want a vulnerability the change introduced or made exploitable to block the Claim, so that the change never lands with a hole it created.
16. As a user, I want a promised security fix that still reproduces to block the Claim, so that "fixed" means fixed.
17. As a user, I want pre-existing vulnerabilities recorded as separate work instead of blocking, so that unrelated debt does not stall this change.
18. As a user with a public tracker, I want only a summary recorded and to be asked first, so that exploit details are not published.
19. As a user, I want HELD to mean an adequate attempt with no open gap, so that a limited attempt never reads as a pass.
20. As a user, I want missing targets or uncertain attribution reported as INCONCLUSIVE, so that I know what was not covered.
21. As a user, I want the rerun after a fix to cover every open gap, so that nothing slips through a narrowed retry.
22. As a user, I want two non-passes in a row to stop the attack step and wait for me, so that cost stays bounded as for the other steps.
23. As a user, I want resets and test data changes not to invalidate passes, so that the attack does not loop on its own side effects.
24. As a user, I want a change to the target's definition or version to invalidate HELD, so that the pass matches the target that was attacked.
25. As a user, I want related Claims attacked together when they share security assumptions, so that a combination exploit is found.
26. As a user, I want an accepted Claim left closed when a later change shares its assumptions, with the new Claim owning the composed attack, so that landed work is not reopened.
27. As a user, I want to accept and land a Claim without HELD when I must, with the known vulnerabilities and risk recorded, so that an emergency mitigation can ship knowingly.
28. As a user, I want the handoff to say an Adversarial review is still missing, so that a resumed session does not land the Claim unattacked.
29. As a user in off mode, I want no automatic attack and no forced pre-approval sequence, so that off still means off.
30. As a user in off mode, I want the existing security-analysis rule kept, so that turning auto off does not drop all security attention.
31. As a user, I want a command to attack code directly, so that I can audit an existing module that is not in any Plan.
32. As a user, I want that command to need an attack scope, so that it never guesses what to attack.
33. As a user, I want that command to count as the automatic step only when it is the step the flow is due to run, so that budgets stay consistent.
34. As a user, I want the attack role limited to disposable targets with synthetic data and no external hosts, so that it cannot harm real systems.
35. As a user, I want the role to stop before a probe leaves the allowed scope, so that a local target that reaches a real service is not used to attack it.
36. As a user upgrading, I want setup update to add the new role and check to tell me it is missing, so that the attack step does not silently fail.
37. As a user, I want the attack step to block rather than fall back to another role when the role is not installed, so that a weaker substitute never passes.
38. As a maintainer, I want the decisions and the options not taken in an ADR, so that the gate's shape is explained later.

## Implementation Decisions

- **Review state procedure** gains the Adversarial review step: its place after CONFIRMED, its verdicts, coverage and gaps, attribution, invalidation (target definition versus fixture changes), composition and ownership, pre-existing-vulnerability handling, accept-and-land coverage and the off-mode rule; the Acceptance gate, Pending acceptance, Ticket status and Resumed sessions include HELD for Security-critical claims. The step reuses the shared state model rather than a parallel one.
- **Plan review procedure and delegation skill** gain the classification rule, the supplemented deviation trigger, the pre-approval sequence and the implemented-work rule; security analysis and plan review remain separate assignments.
- **A new adversarial-review procedure** (beside code review and outcome verification) governs main's orchestration of the step: brief contents (Claim, commit, security invariants, targets with reset, allowed effects and reachable dependencies, open gaps from earlier calls), counting and stop, fixes and recalls.
- **Role templates**: a new adversary template with the safety limits; analyst's security-analysis mode is unchanged; reviewer and verifier templates are unchanged (their briefs carry the security invariants).
- **Configuration tool**: `adversary` joins the managed roles, the roles added after older installations, the default choices (opus/high), naming with prefix, session export and stale-template detection; a missing installation blocks the step.
- **Command**: a new explicit-only skill for `/cc-feather:adversarial-review`, following the delegation-preview precedent.
- **Glossary**: Unplanned work, Security-critical change, Security-critical claim and Adversarial review are already in CONTEXT.md; Automatic flow, Pending-acceptance claim, Acceptance gate and Accept and land are updated for the third step.
- **ADR 0009** records the decisions and amends ADR 0008 by note.

## Testing Decisions

- Tests check what ships, not internals: the text of procedures, templates, guidance, glossary and READMEs, and what the configuration tool installs and reports.
- **S1, procedure contracts (existing seam).** Whole-sentence pins of each new rule in the document that states it, README rules paired in both languages, absence checks for replaced two-pass wording, and a scenario table mapping each scenario to its deciding sentences: Security-critical classification at plan time; a newly found control as deviation; implemented work with a READY waiver still getting security analysis; BROKEN from an introduced flaw, from a flaw made exploitable, and from a promised fix that still reproduces; a pre-existing flaw becoming separate work; INCONCLUSIVE with open gaps and the rerun covering them; a reset not invalidating; a target version change invalidating; composition across Claims and with an accepted Claim; accept and land without HELD; off mode starting no automatic step; the explicit command inside and outside the flow; a missing role blocking. The command's frontmatter (explicit-only, listed in the manifest) is tested like the delegation preview's. Prior art: the 0.17.0 review-rule follow-up tests.
- **S2, configuration tool (existing seam).** In-process tests: adversary installed and rendered with opus/high in user and project scope, with and without the role prefix; an installation from the 0.17.0 templates reports the missing role, refuses model and session until setup update, and gains the role with existing choices kept; model and session export cover the new role; stale-template detection includes it. Prior art: the 0.17.0 stale-template upgrade tests.
- Each new or changed assertion fails in a copy outside the repository with its phrase removed or its replaced phrase restored.
- Whether the role actually breaks a target is model behaviour that tests cannot prove; the release's validation entry records whether the flow ran live.

## Out of Scope

- A setting that forces the flow in off mode, or a switch that disables only the third step.
- Changes to reviewer, verifier or analyst templates.
- Access to staging or production, or tool installation by the role.
- Hook-enforced gates; these remain model instructions.
- An integrated whole-repository security audit beyond the Claims' changes and their composition.

## Further Notes

- The 0.17.0 rules for passes, counts, the Acceptance gate and accept and land carry over; this spec extends them with a third step for Security-critical claims only.
- Adding a role requires setup update in every delegation-owning scope and a fresh session; an installation without it blocks the step rather than skipping it.
- The two glossary commits that introduced the terms are on local main and not yet pushed.
