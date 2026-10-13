# Claims are decided when the user asks for implementation

Label: `ready-for-agent`

Vocabulary follows [CONTEXT.md](../../CONTEXT.md), whose Plan, Claim and Security-critical claim entries were already revised for this spec and are not yet committed. The decisions were settled in a grilling with the user on 2026-10-13; they amend [ADR 0005](../adr/0005-the-named-plan-and-its-tickets.md) and are recorded in ADR 0012, written as part of this work.

This spec has no Claims table, on purpose: under its own rule, a spec lists Claims only when the user asks. Implementing this spec makes it one Claim against the Acceptance below; cutting it into tickets first makes each ticket a Claim.

## Problem Statement

When main drafts a spec for the user, it reads plan review's "a plan lists its claims" and "main marks each Security-critical claim in a plan it writes" as instructions for the drafting step, and cuts the spec into its own Claims table. The user then cuts the same spec into tickets with a planning skill, and those tickets are the units the user means to implement and have reviewed. The two cuts are made independently, so they disagree, and plan review's rule that a spec's Claims and its tickets must agree turns the disagreement into a blocker. This project's own tracker note encourages the table ("A spec may also list its claims in a Claims table; its tickets then mirror that table"), so every spec so far has carried one.

A second problem is what reviews read. When a single ticket is the Plan, its whole spec is supplied as context to plan review, code review and outcome verification, so a review can judge the ticket against parts of the spec the ticket never adopted, and the implementer and the reviewers may each read a different amount of the spec. The planning skills in use write each ticket to be done alone in a fresh context, with its own outcome and acceptance; the spec is where it came from, not part of its contract.

## Solution

Claims are decided when the user asks for implementation, by what the user names:

- **A spec:** the spec is the Plan and is one Claim, unless it lists its own Claims, which then count as listed. When the named spec has unfinished tickets, main first asks whether to implement the spec as it stands or its tickets.
- **Tickets of a spec, all or some:** the Plan is those tickets. Each unfinished ticket is one Claim; its `Blocked by` lines are the dependencies. Plan review runs once over them and reads the spec only as a checklist for what the tickets must carry; the spec is not part of the Plan's content.
- **A single ticket:** the ticket is the Plan and its one Claim.

A review or an implementation of a Claim reads what the Claim is written in, plus the parts of a spec the Claim cites explicitly and, for a Claim a spec lists, the spec's parts that state they hold for every Claim. A ticket's `Spec:` line records where the ticket came from; it does not bring the whole spec in.

When main drafts a spec for the user, it lists no Claims and cuts nothing unless the user asks. A spec main drafts is not a plan main writes for Security-critical marking; its Claims are classified before the Plan's first plan review, as for any plan the user wrote.

During implementation, the existing deviation and claim-change rules apply. A re-review after a deviation covers the changed tickets and the tickets blocked by them, and goes back to the spec only when the change touches what the spec states. Once tickets are cut, they govern implementation; when an agreed change alters the spec's stated outcome, scope, decisions or invariants, main updates the spec as well, with the user's authorisation.

## Acceptance

1. **Claims at implementation.** Plan review states the three cases above (a named spec, named tickets of a spec, a single ticket), the question main asks when a named spec has unfinished tickets, and that a spec's own Claims list counts only when the spec has one. The rule that a Plan already covering the named work in this session continues with its count, verdicts and blockers, the partial-overlap rule, the resumed-session rule, ticket discovery, "nothing left to implement" and agreement between a spec's listed Claims and its tickets are kept.
2. **One Claim from a spec.** A spec without tickets and without a Claims list is one Claim, provided it has scope and acceptance of its own; otherwise it is not yet a Plan, as today. Main may say in one line that a spec looks separable into tickets, without stopping the flow.
3. **Plan review over tickets.** When the Plan is tickets of a spec, plan review receives the tickets and the spec, judges each ticket's outcome, acceptance and dependencies, checks the tickets against each other, and uses the spec only as a checklist: every named ticket stays within the spec's scope and Out of Scope and cites the spec's decisions and security invariants that apply to it, and, when the named tickets are all of the spec's unfinished tickets, the tickets together with the finished ones cover the spec's outcome. A missing coverage or citation is a blocker.
4. **What a Claim's reviews and implementation read.** Code review, outcome verification and Adversarial review receive the Claim's text and the spec parts it cites, and, for a Claim a spec lists, the spec parts that state they hold for every Claim; the whole spec is supplied only when the spec itself is the Claim. The brief of an Assignment that implements a Claim carries the same material. A citation names a section, item or identifier, such as `(C1 item 1)` or `D3`; a `Spec:` line, a parent reference or a shared directory is not a citation.
5. **Drafting a spec.** Plan review states that main, when it drafts a spec for the user, lists no Claims and cuts none unless the user asks; and that "main marks each Security-critical claim in a plan it writes" covers only a plan main proposes itself, such as one for Unplanned work, while a spec main drafts has its Claims classified before the Plan's first plan review.
6. **Security analysis unchanged.** Security analysis still runs before plan review against the named Plan, and its accepted controls still become security invariants in the acceptance of the Security-critical Claims they apply to, written into the named ticket or spec with the user's approval of the revised Plan.
7. **Deviations and the spec.** Review state states that, for a Plan of tickets, the review after a material deviation covers the changed tickets and the tickets they block, plus the spec checklist only when the change touches the spec's stated scope, decisions or invariants; and that, after an agreed change to the spec's stated outcome, scope, decisions or invariants, main updates the spec with the user's authorisation, so that later checklist checks and other sessions read the agreed version.
8. **Preview.** The Delegation preview applies the same rules, including the question for a named spec with unfinished tickets, which it reports as open rather than answers.
9. **Glossary and decision records.** `CONTEXT.md`'s Plan, Claim and Security-critical claim entries state the rules above (already revised; checked, not rewritten). ADR 0012 records the decision and its rejected options; ADR 0005 gains an "Amended by ADR 0012" note naming what changed (the single ticket's spec is no longer context; a named spec with tickets prompts a question; the spec is a checklist, not Plan content, when tickets are named) and is otherwise unchanged.
10. **Tracker note.** `docs/agents/issue-tracker.md` says a spec lists Claims in a Claims table only when the user asks, with its tickets then mirroring the table, and that a ticket's `Spec:` line records its origin and is not a citation of the whole spec.
11. **READMEs.** `README.md` and `README.zh-TW.md` explain the three cases with an example, what a review reads, the drafting rule and the deviation and spec-update rules, replacing the current single-ticket and Security-critical marking statements; both say the same thing and match the procedures.
12. **Tests.** Contract tests pin the new statements and fail on the 0.22.0 text; pins of the replaced statements are updated or turned into absence pins; the full suite passes in both discovery forms.
13. **Release 0.23.0.** `plugin.json` is 0.23.0; `claude plugin validate .` passes; `docs/setup-validation.md` gains a 0.23.0 entry with the test counts and skips, the validation, the review round and live compliance recorded as untested, and notes that only the plugin update is needed; the tag `v0.23.0` is created after the user's go-ahead, only after checking that it matches `plugin.json` at the tagged commit and does not already exist.

## User Stories

1. As a user who drafts a spec with main, I want main not to cut it into Claims on its own, so that the spec does not compete with the tickets I cut later.
2. As a user, I want main to cut Claims into a spec when I ask, so that a small spec I will not split into tickets can still have several Claims.
3. As a user who says "implement this spec" for a spec without tickets, I want the spec to be one Claim, so that what I named is what is reviewed.
4. As a user, I want main to tell me in one line when a spec looks separable, without stopping, so that I can choose to cut tickets first.
5. As a user who says "implement this spec" for a spec that has unfinished tickets, I want main to ask whether I mean the spec or its tickets, so that the review granularity is my choice.
6. As a user who names all of a spec's tickets, I want each unfinished ticket to be one Claim and one plan review to cover them, so that splitting into tickets does not multiply plan reviews.
7. As a user who names some of a spec's tickets, I want the same rule for those tickets, so that I can implement a spec in parts.
8. As a user who names a single ticket, I want that ticket to be the Plan and its Claim, so that a fresh session reviews only what it will build.
9. As a user, I want a ticket's reviews to read the ticket and the spec parts it cites, not the whole spec, so that the ticket is judged against its own contract.
10. As a user, I want the implementer of a ticket to get the same material its reviewers read, so that the reviews judge what the implementer was given.
11. As a user, I want plan review over tickets to check them against the spec once, so that a decision, an Out of Scope line or a security invariant lost while cutting tickets is caught before implementation.
12. As a user, I want that check to block when a ticket goes outside the spec's scope or misses a decision or invariant that applies to it, so that narrow per-ticket reviews stay safe.
13. As a user whose spec lists its own Claims, I want each listed Claim to read its own part plus the parts the spec says hold for every Claim, so that shared decisions still apply.
14. As a user, I want a `Spec:` line not to count as citing the whole spec, so that narrowing what reviews read has an effect.
15. As a user, I want security analysis to keep running before plan review and its invariants to be written into the ticket or spec I named, with my approval, so that the security guarantees live in the documents and survive sessions.
16. As a user, I want a spec main drafts not to count as a plan main wrote, so that Security-critical classification happens before the first plan review instead of during drafting.
17. As a user whose implementation needs a change, I want only the changed tickets and the tickets they block re-reviewed, so that a small change does not re-review the whole Plan.
18. As a user, I want the spec updated, with my authorisation, when an agreed change alters what it states, so that later checks and sessions do not read an outdated spec.
19. As a user, I want the Delegation preview to apply the same rules and show the open question for a spec with tickets, so that the preview does not guess.
20. As a user reading either README, I want these rules explained with an example, so that I know what will be reviewed and what each review reads.
21. As a maintainer, I want the decision and its rejected options in an ADR that amends ADR 0005, so that later readers know why the rules changed.
22. As a user of this repository, I want the tracker note to stop implying that every spec carries a Claims table, so that new specs follow the new rule.
23. As a user with an existing installation, I want the change from the plugin update alone, so that I do not need to rerun setup update.

## Implementation Decisions

- **Where the rules live.** The Claim rules, the drafting rule and the plan-review checklist go into the plan-review procedure, replacing the current named-Plan paragraph's spec-with-tickets and single-ticket sentences and the "plan it writes" sentence. Code review, outcome verification and Adversarial review replace "its spec as context when the plan is a single ticket" with what a Claim's reviews read. The delegation skill states the same material for an implementing Assignment's brief. Review state carries the deviation scope and the spec-update rule beside its claim-change rule. The preview applies the plan-review rules by reference, as it does today.
- **The question for a spec with tickets.** It is asked only when the named spec has at least one unfinished ticket and no Plan in this session already covers the named work. Answering "the spec" makes the spec one Claim, or its listed Claims; answering "the tickets" makes those unfinished tickets the Plan. When the spec lists Claims and has tickets, they must still agree, as today.
- **The checklist.** Plan review reads the spec, but the spec is not a Claim's acceptance: a ticket's reviews after plan review do not read uncited parts. The coverage part of the checklist runs only when the named tickets are all of the spec's unfinished tickets; the scope, Out of Scope and citation parts run for any named tickets of a spec.
- **Citations.** A citation is explicit: a named section or heading, a numbered item or an identifier such as `C1 item 1`, `D3` or `S2`. A reviewer may follow a citation to the cited part only. A ticket that needs a whole section cites the section.
- **Deviation scope.** The narrowed re-review follows the existing completed-call and coverage rules: it is narrowed only after a completed review, and a call that did not complete is followed by a review of the whole Plan.
- **Unchanged.** Claim sizing stays with the planning step (ADR 0003). Counts and passing verdicts stay per session (ADR 0002). Security analysis, its timing and its approval step, the Stop threshold, the acceptance gate and ticket status rules are unchanged. Installed role definitions, the installed policy, the handoff skill and the configuration tool are unchanged.
- **ADR 0012** records: Claims are decided at implementation by what the user names; a ticket's Plan is its own content; the spec is a checklist for plan review; reviews and implementation read the Claim and its citations; main does not cut Claims while drafting. Rejected: asking at drafting time whether to list Claims (the decision belongs to the moment the user names the work); main writing a Claims table into specs it drafts (the cause of the conflict); each ticket its own Plan when several are named (multiplies plan reviews, and no review sees cross-ticket dependencies; ADR 0005's rejection stands); the whole spec as context for a single ticket (judges the ticket against parts it never adopted); plan review reading only the tickets (nothing would catch what cutting tickets lost); security invariants kept only in briefs and handoffs (lost across sessions and checkouts); the implementer reading the whole spec while reviewers read the ticket (reviews would not judge what the implementer used).
- **Release** as 0.23.0, after 0.22.0. If the release order changes, the version follows the project rules: a version already pushed to main is never reused.

## Testing Decisions

- The seam is the existing contract tests that check shipped text: key-phrase pins in the procedures and paired pins in both READMEs, with absence pins for removed wording. Prior art: the claim-source, ticket-discovery and Security-critical routing tests in the configuration and security-review test modules.
- New pins assert: the three named-Plan cases; the question for a spec with unfinished tickets; the checklist and its blocker; what a Claim's reviews read and that a `Spec:` line is not a citation; the implementing brief's material; the drafting rule; the narrowed "plan it writes" rule; the deviation scope; the spec-update rule; the preview's open question. Each fails on the 0.22.0 text.
- The pins of replaced statements (the single ticket's spec as context, in the procedures and the READMEs, and "Main marks each Security-critical claim in a plan it writes") are updated to the new wording or become absence pins. Kept rules (one Claim fallback, agreement between listed Claims and tickets, existing-Plan rule) keep or gain pins that fail if they are removed.
- READMEs, the tracker note, `CONTEXT.md` and the ADRs are checked at outcome verification against the procedures.
- Release checks: the full suite in both discovery forms and `claude plugin validate .`.
- Text tests show that the shipped contract is consistent, not that a live model follows it; live compliance is recorded as untested.

## Out of Scope

- Changing how planning skills write specs or tickets, or adding a `Spec:` line convention to cc-feather.
- Rewriting earlier specs or their Claims tables; they keep working under the listed-Claims rule.
- Re-cutting the 0.22.0 spec: `repository-safety-followups.md` is cut into tickets matching its C1 to C5 one to one, under the current rules.
- Claim sizing, the Stop threshold, counts across sessions, the acceptance gate, security analysis rules and the review schedule (the per-claim schedule work follows this spec and touches the same files, so it is not run in parallel).
- Changing installed role definitions, the installed policy or the handoff skill.

## Further Notes

- Security-critical classification of this spec's Claims happens before its first plan review, under its own rule. It changes what code review and Adversarial review read for a Security-critical Claim, so it may be classified as Security-critical, which would bring a security analysis before plan review.
- The `CONTEXT.md` revision was made during the grilling and should be committed with this spec's implementation, not alone, since until then it states rules the procedures do not yet follow.
- The grilling's decisions and the facts it relied on are recorded in the handoff `claims-at-implementation`.
- Rollback: before anything is pushed, the unpushed commits can be dropped with the user's agreement; after the release, a user reinstalls 0.22.0.
