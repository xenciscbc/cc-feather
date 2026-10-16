# Weigh findings before rules

Label: `ready-for-agent`

Vocabulary follows [CONTEXT.md](../../CONTEXT.md), which defines Blocking finding, Non-blocking finding, Follow-up record and Plan. This spec adds one rule to the delegation skill and one loading trigger to the installed delegation policy. It is one claim: it lists no claims and has no tickets.

## Problem Statement

Reviews, security analyses and second opinions keep producing edge cases, and main tends to turn each one into another rule. Planning 0.27.1, nine findings from a code review and a Codex second opinion became a proposed list of seven rule changes; the user stopped it with 「應該先想一下，何時會發生，會不會過度防御」 ("first think about when it happens and whether it is over-defensive"). Weighed by when each case occurs, what it can cause at worst and whether an existing rule already covers it, the patch shrank to one rule rewrite and one wording fix, and the rest went to its Out of Scope with reasons. Nothing in cc-feather asks main to make that weighing; it lives only in one user's memory, so other projects and later sessions keep adding defensive rule text, which the user has asked to stop.

Findings become requirements or fixes along many paths: main drafts a plan from a Follow-up record or recommends which findings to fix, turns a security analysis's accepted controls into security invariants, revises a plan after REVISE or a deviation, and fixes CHANGES_REQUESTED, REFUTED and BROKEN findings and final-check failures. Some of these happen before any delegation is dispatched, when the installed policy does not yet ask main to load the delegation skill.

## Solution

One rule in the delegation skill, placed with main's ownership of decisions, applies whenever main proposes or adopts a requirement or a fix derived from any finding. Before doing so, main states briefly when the case can occur in normal use or under the applicable threat model, its worst credible outcome, and whether an existing rule covers it, and prefers reusing or correcting a rule. For optional work it recommends fixes for what normal use encounters, for data loss and for security problems under that threat model, and normal-use rarity alone never discounts a security problem. The weighing selects remedies and recommendations only: the existing blocking conditions, rejection evidence, security-disposition procedures and the user's decisions still govern, and rarity or a minor outcome alone is never rejection evidence.

The installed delegation policy gains one loading trigger, so main loads the delegation skill before proposing or adopting a requirement or fix derived from a finding, including planning it does alone before any dispatch. Existing installations get the trigger through setup update.

## Acceptance

1. The delegation skill states, as its own paragraph directly after the paragraph on main's ownership of decisions and acceptance, that before proposing or adopting a requirement or fix derived from any finding, main briefly states when the case can occur in normal use or under the applicable threat model, its worst credible outcome, and whether an existing rule covers it, preferring to reuse or correct a rule.
2. The same paragraph states that for optional work main recommends fixes for cases normal use encounters, data loss, or security problems under that threat model, and that normal-use rarity alone never justifies discounting such a security problem.
3. The same paragraph states that the weighing selects remedies and recommendations only, that existing blocking conditions, rejection evidence, security-disposition procedures and user decisions still govern, and that rarity or a minor outcome alone is not rejection evidence for a Blocking finding or a plan-review blocker. It lists no paths, defines no new attacker model and adds no approval step.
4. The installed delegation policy template's sentence listing when main also uses the delegation skill gains "before proposing or adopting a requirement or fix derived from a finding"; nothing else in the policy changes.
5. Both reference documents, in English and Traditional Chinese, describe the rule in one sentence beside their description of findings and the Follow-up record.
6. Contract tests pin the sentences of items 1 to 3 and the paragraph's position, the new policy trigger (updating the existing test that pins the policy's loading sentence) and the sentence in both reference documents.
7. The version is 0.28.0. Both READMEs carry a 0.28.0 update note saying what changed, that the installed delegation policy changed so existing installations run `/cc-feather:setup update` and start a fresh session, and that going back to 0.27.1 means reinstalling the 0.27.1 plugin and running setup update again. The `docs/setup-validation.md` entry for 0.28.0 records the validation, including a setup update that brings an existing 0.27.1 installation's policy to the new template, that no live rehearsal was run, that the tests cannot show that a model follows the rule, the review round, and that no `v0.28.0` tag exists when the entry is written.
8. Nothing changes in the role definitions, the delegation skill's references, the handoff skill, the handoff tool or the handoff-tidy command.

## User Stories

1. As a user, I want main to say when a finding's case happens before it adds a rule for it, so that rare cases do not grow the rules.
2. As a user, I want main to say what the case can cause at worst, so that I can tell loss from duplication or a safe stop.
3. As a user, I want main to say whether an existing rule already covers the case, so that rules are not restated.
4. As a user, I want main to prefer reusing or correcting a rule, so that the rule text stays small.
5. As a user, I want the weighing for any finding, whichever review, analysis or record produced it, so that it does not depend on the path.
6. As a user, I want it when main plans from a Follow-up record on its own, before anything is dispatched, so that I choose what to fix with the weighing in front of me.
7. As a user, I want security problems weighed under the applicable threat model, not by how often normal use meets them, so that an attacker-reachable problem is never dismissed as rare.
8. As a user, I want optional fixes recommended for what normal use encounters, data loss and security problems, so that recommendations match real risk.
9. As a user, I want the weighing never to change what blocks, so that a real defect is never skipped as rare.
10. As a user, I want rarity or a minor outcome never to count as rejection evidence, so that rejections stay grounded.
11. As a user, I want existing security dispositions to stand, so that the weighing neither forces every security finding into the current plan nor drops one without the existing procedure.
12. As a user, I want my earlier decisions to stand, so that the weighing does not reopen them.
13. As a user, I want no new approval step, so that the rule does not itself grow the process.
14. As a user, I want the reference documents to describe the rule in both languages, so that I know main will weigh findings this way.
15. As a user, I want the update note to tell me to run setup update, so that my installation gets the new loading trigger.
16. As a user, I want to know how to go back to 0.27.1, policy included, so that I can undo the change.
17. As a maintainer, I want tests that fail if the rule, its limits or the trigger are removed, so that they do not regress.
18. As a maintainer, I want the validation entry to show that setup update deploys the trigger and that the tests cannot show the model follows the rule, so that the release record is honest.

## Implementation Decisions

- The rule is one paragraph in the delegation skill, directly after the ownership paragraph, because main loads that skill before dispatching, accepting, recovering and reviewing, and every path by which a finding becomes a requirement or fix runs through those; no reference or procedure repeats it.
- The installed policy gains a loading trigger in its existing sentence, so main also loads the skill when it plans from findings on its own; setup update deploys it, and setup's existing check reports an installation whose policy differs from the template.
- Main owns the weighing; no role definition, report format or plan-review criterion changes.
- Security problems are weighed under the applicable threat model, such as the one the repository safety reference states for repository content; the rule defines no attacker model of its own and keeps the existing security-disposition procedures, including recorded residual risk and separate work for pre-existing vulnerabilities.
- Starting wording, from a Codex second opinion, to be refined in implementation: "Before proposing or adopting a requirement or fix derived from any finding, main briefly states when the case can occur in normal use or under the applicable threat model, its worst credible outcome, and whether an existing rule covers it, preferring to reuse or correct a rule. For optional work, recommend fixes for cases normal use encounters, data loss, or security problems under that threat model. Normal-use rarity alone never justifies discounting such a security problem. This weighing selects remedies and recommendations only: existing blocking conditions, rejection evidence, security-disposition procedures and user decisions still govern, and rarity or a minor outcome alone is not rejection evidence for a Blocking finding or REVISE blocker."
- The release is 0.28.0, a minor version because main's behaviour and the installed policy change.

## Testing Decisions

- Good tests check the shipped text a model reads, the policy template setup deploys and the release documents, not wording that carries no decision.
- Rule contract: a new test class in the completion criteria test module, following its existing tests, pins the paragraph's sentences and position in the delegation skill and the sentence in both reference documents.
- Policy: the existing test that pins the policy's loading sentence is updated to the sentence with the new trigger; the existing setup tests continue to cover outdated-policy detection and update.
- Release: the existing release tests pin the version, the 0.28.0 update notes and the validation entry, following their conventions for the previous release's pins.
- Not automated and not rehearsed: whether a model weighs findings as the rule says.

## Out of Scope

- A plan-review criterion for the analyst, a field in role reports, or a ranking in the handoff-tidy Proposal; none is the place where main decides what to fix.
- Changes to what blocks, to rejection evidence, to how security findings are dispositioned, or to any recorded user decision.
- Any other change to the installed policy or to role definitions.
- Revisiting earlier Follow-up records with the new rule; that happens when the user starts the plan that uses them.
- A live rehearsal.

## Further Notes

- Origin: the user's remark while planning 0.27.1 on 2026-10-16, the 0.27.1 spec's Out of Scope as the worked example, and Codex second opinions (gpt-6-astra) on where to place the check: findings become rules on many paths; the weighing must not override any blocking condition or add an approval step; security problems are weighed under the threat model; and planning before dispatch needs a policy trigger, which the user allowed with a setup update.
- Plan review call 1 returned REVISE on the security limits, on the claim that every path read the completion criteria, and on an incomplete path list; this revision moves the rule to the delegation skill, adds the policy trigger, drops the path list and states the security limits under the threat model.
- Next: the security patch for the 0.23.0 to 0.26.0 Follow-up records, recorded in `claims-at-implementation-followups`, is planned to use this rule when the user chooses its scope.
- For codex-feather: not affected; the rule lives in cc-feather's delegation skill and policy.
