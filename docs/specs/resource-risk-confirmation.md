# Resource-risk confirmation

Label: `ready-for-agent`

Vocabulary follows [CONTEXT.md](../../CONTEXT.md), which defines Claim, Plan, Plan review, Dispatch record, Active handoff, Resource-risk claim, Execution method, Unbounded probe and Observed resource risk. The decisions below were settled by the user on 2026-11-11 in a grilling session. This spec amends [ADR 0019](../adr/0019-resource-risk-is-marked-at-plan-review-and-contained-by-the-runner.md) and changes the analyst role definition, so it is release 0.35.0.

## Problem Statement

Plan review marks a Claim a Resource-risk claim, and from then on the mark binds: main must approve an Execution method, every role that may execute code for the Claim runs its risky part only inside the Runner, and main asks the user for a budget whenever no source states one. Nothing lets the user, or main, take back a mark that is wrong. The mark is not a blocker, since the resource-risk item adds no verdict of its own, so main cannot REJECT it as it rejects a blocker, and main's approval covers only the Execution method, not whether the Claim is a Resource-risk claim at all.

Marks are sometimes wrong. In the 0.34.0 review round plan review call 1 marked all three tickets, citing an earlier out-of-memory stop that had come from unrelated work; the user removed the marks by a decision the rules did not describe.

The user is also stopped in the middle of a Plan. Main approves a Resource-risk claim's Execution method before that Claim's first brief, so when the third Claim of a Plan is marked and no budget is stated, main stops after the second Claim to ask. The user wants a chain of Claims to run with as few stops for their decision as possible.

## Solution

Plan review's mark becomes a proposal that the user adopts or drops, asked once per Plan at the start of implementation:

- When the Plan's plan review returns READY and before main implements the Plan's first Claim, main asks the user, in one question, which of the Plan's proposed marks to adopt. Each proposal shows plan review's reason and estimate and main's own recommendation on its basis. A budget question is added to the same ask only when the existing budget rule requires main to ask the user: no source states a budget, or the Claim needs more than a stated default.
- An adopted Claim is a Resource-risk claim and runs exactly as today. A dropped Claim is an ordinary Claim: no Execution method and no Runner requirement, while the Unbounded probe floor still covers every new or modified test or probe it runs.
- During REVISE calls main lists the current proposals in its progress report and does not ask.
- After that one ask, a chain of Claims does not stop again for a mark or a budget, unless a later plan review proposes a new mark; that happens only when the Plan is reviewed again, and the question then joins the stop that review already makes.

The rule applies in auto and to an explicit plan review in off. Plans whose plan review proposes no mark, and work without plan review, behave as in 0.34.0.

## User Stories

1. As a user, I want to confirm each resource-risk mark plan review proposes, so that a mark plan review got wrong does not bind the Claim.
2. As a user, I want to drop a mark whose basis is wrong, so that a Claim is not forced through the Runner because of evidence from unrelated work.
3. As a user, I want to adopt a mark that is right, so that its risky part still runs only inside the Runner under an approved Execution method.
4. As a user, I want all of a Plan's proposed marks asked in one question, so that I decide them together instead of one at a time.
5. As a user, I want that question asked after the Plan's plan review returns READY, so that I decide marks on the Claims as they will be implemented, not on a draft a REVISE will change.
6. As a user, I want the question asked before the Plan's first Claim is implemented, so that a chain of Claims is not stopped in the middle for a mark.
7. As a user, I want a budget question for an adopted Claim in the same ask, so that a mark and its budget cost me one stop, not two.
8. As a user, I want no budget question when my guidance or the Plan already states a budget that covers the Claim, so that the ask is as short as possible.
9. As a user, I want the question to show the budget main will use and where it comes from, so that I can correct it in the same answer.
10. As a user, I want to see the current proposals during REVISE calls without being asked, so that I know what is coming without stopping the review loop.
11. As a user, I want main to check each mark's basis before asking, so that I get a recommendation, such as that the cited evidence belongs to other work.
12. As a user, I want the decision to stay mine, so that main never drops a mark on its own judgement.
13. As a user, I want a dropped Claim still covered by the Unbounded probe floor, so that dropping a mark never removes all protection from a run.
14. As a user, I want a dropped mark not to come back in later plan review calls without new evidence, so that I am not asked the same question again.
15. As a user, I want plan review to propose the mark again when the Claim changes or a new risk source appears, so that a real risk found later is still raised.
16. As a user, I want my decision on a mark kept while the Claim's reading set is unchanged, so that a resumed session or a later review does not ask again.
17. As a user, I want a renewed mark after a Deviation asked together with my approval of the revised Plan, so that it does not add a stop of its own.
18. As a user, I want an unanswered mark to hold back only its own Claim, so that the Plan's other Claims proceed while I decide.
19. As a user, I want the rule to apply to an explicit plan review in off as well, so that both modes treat marks the same way.
20. As a user, I want the marks gathered across every call of the Plan's plan review, so that a mark made on an early call and not restated on the READY call is still asked.
21. As a user, I want a mark a later call withdraws, or one on a Claim no longer in the Plan, left out of the question, so that I only decide marks that still apply.
22. As a user, I want my decisions recorded where Observed resource risks are kept and never written into a Claim's text, so that the Plan and its tickets keep their wording.
23. As a user, I want every dropped mark listed in the report at the end of the Plan, so that a later Observed resource risk on a dropped Claim can be traced back to my decision.
24. As a user, I want deciding a mark not to count as a plan-review call or reopen plan review, so that confirming marks never costs review budget.
25. As a user, I want a Plan with no proposed mark to start without any new question, so that the change costs nothing when there is nothing to decide.
26. As a user, I want the glossary to say that plan review proposes and I adopt, so that "Resource-risk claim" means only a Claim that runs through the Runner.
27. As a user, I want ADR 0019 to note the amendment, so that a reader of the original decision finds the change.

## Implementation Decisions

- **The mark is a proposal.** The analyst's resource-risk item proposes a Resource-risk claim with its reason, estimated peak memory and time with the basis, and an Execution method, as today; the proposal binds only once the user adopts it. "A missing mark is not a statement that a claim is safe" stays, and so does "This item adds no verdict of its own".
- **When main asks.** After the call that returns READY for a Plan and before main implements the Plan's first Claim, main asks the user once about every undecided proposal of that Plan, in one AskUserQuestion: a multiple-choice question listing each proposed Claim with its reason, estimate, main's recommendation and the budget main would use with its source, where the Claims the user selects are adopted and the rest dropped, and one budget question only when the budget rule in the resource-risk runs reference requires main to ask the user for an adopted Claim, that is when no source states a budget or the Claim needs more than a stated default. This is the one exception to plan review's step 5 rule that READY continues already authorized work without another routine confirmation, and it arises only when a proposal is undecided.
- **Where it applies.** The rule applies in auto and after an explicit plan review in off. A Plan whose plan review proposes no mark, and work without plan review, behave exactly as in 0.34.0: no new question is asked.
- **During REVISE.** Main does not ask about proposals on a REVISE call; it lists the Plan's current proposals in its progress report.
- **Which proposals.** The proposals asked are gathered from every call of the Plan's plan review, each Claim at its latest state: a proposal a later call withdrew is left out, and a Claim that was split, merged or removed is judged by the latest version of the Plan.
- **Main checks the basis.** Before asking, main checks each proposal's basis, such as whether its cited evidence belongs to this work, and states a recommendation, adopt or drop with the reason. Main never drops or adopts a proposal itself; only the user's answer decides.
- **Approval moves to the same point.** Main approves the Execution method of each adopted Claim at the same point, before the Plan's first Claim, using the budget order in the resource-risk runs reference, so no Execution method approval stops the chain later. The existing rule that an approval is needed before a Resource-risk claim's first brief and main's own first run stays as the guarantee; the ask above is where it is met.
- **A dropped Claim.** A dropped Claim is not a Resource-risk claim: it has no Execution method and no Runner requirement. Main's floor and each role's floor for Unbounded probes apply to it as to any Claim, and an Observed resource risk is recorded on it as on any Claim.
- **Later plan review calls.** Every later plan-review brief for the Plan carries the user's decision on each proposal, with its reason. Analyst proposes a dropped Claim again only with evidence the decision did not consider, such as a change to the Claim or a risk source not in the earlier proposal, and states that evidence; main then asks the user again.
- **A later plan review.** A proposal that a later plan review of the same Plan makes, after a Deviation or in a resumed session, is asked together with the user's approval that review already needs. When that review needs no approval of the user, the proposal is asked before the affected Claim's next run. A later plan review also ends the validity of each adopted Claim's approved Execution method, as the reference's binding rule states; main approves it again at the same point, and any budget question it needs joins the same ask.
- **Binding.** A decision is bound to its Claim and the Claim's recorded reading set. It stays valid while the reading set is unchanged; when the reading set changes and plan review proposes the mark again, main asks again.
- **While unanswered.** An undecided proposal holds back its own Claim: no brief to a role that may execute code for it and no run of main's own for it. Other Claims proceed, subject to their own dependencies.
- **Where decisions are kept.** Main records each decision, adopted or dropped with its reason and the reading set it is bound to, where Observed resource risks are kept: in auto, in the Plan's Dispatch record; in off, in the Active handoff when one exists, and otherwise in the session's state. It is never written into the Claim's text. Review state's Dispatch record lists the user's decisions on proposed marks among what the record holds.
- **Kind of decision.** A decision on a proposal is recorded as adopted or dropped. It is not one of the kinds review state's User decisions names (re-review, deferral, cancellation, changed acceptance, waiver or accept and land); in particular a dropped proposal is not a waiver.
- **Not a review event.** Deciding a proposal is not a plan-review call, does not change any count or verdict, does not reopen plan review and is not a Deviation.
- **End of the Plan.** The decision or completion report at the end of the Plan lists each dropped proposal, one line each: the Claim, plan review's reason and the user's reason, next to the Plan's Observed resource risks.
- **Glossary.** CONTEXT.md's Resource-risk claim entry changes from "Plan review marks it" to: plan review proposes the mark and the user adopts it; a dropped proposal leaves an ordinary Claim, still covered by the Unbounded probe floor. Execution method and Observed resource risk keep their entries.
- **ADR.** ADR 0019 gets an amendment note, in the form ADR 0006 uses, pointing to this spec: the mark is a proposal the user adopts or drops, asked once per Plan before its first Claim.
- **Documents.** Both reference documents and both READMEs describe the confirmation where they describe Resource-risk claims, sentences paired in both languages. The rule itself is written once, as ADR 0017 requires: in the resource-risk runs reference for main's side, with the plan-review procedure pointing to it, and in the analyst definition for the proposal and its brief.
- **Release.** 0.35.0 changes the analyst role definition, so existing installations need setup update; the validation entry, the setup document's upgrade note and both READMEs say so, together with how to go back to 0.34.0. Each README gets a new 0.35.0 note at the start of its Updates section, and earlier releases' notes stay unchanged. The release tests that pin 0.34.0 as the latest release (the manifest version, the Updates section starting with the 0.34.0 note, the 0.34.0 validation entry being the last) move to 0.35.0 as earlier releases moved them.
- **Not affected.** The Runner and its contract; the Unbounded probe floor; Observed resource risk recording; the budget order and its sources; the Security-critical classification and its passes; review counting and the Stop threshold; code review, outcome verification and Adversarial review; handoff and lease records and their runtimes.

## Testing Decisions

- No executable seam: every change is model instructions. Following the project's practice, tests pin each decision-carrying sentence as a whole sentence in the document and section that state it, README and reference sentences paired in both languages.
- The pins go in a new test module for this feature that uses the shared test support, following the test module split. Existing pins whose sentences change, such as the Execution method approval sentence and the CONTEXT.md entry for Resource-risk claim in the resource-method tests, are updated where they are.
- A good test checks a whole sentence in its owning section, and checks that a rule written once is not restated elsewhere, as the existing single-owner tests do.
- Prior art: the resource-method and resource-floor test modules (the plan-review item, main's approval, the floor, the Observed resource risk record, the glossary entries) and the release tests' version and validation checks.
- No live rehearsal: the validation entry states that the pins show the text, not that a model always follows it.

## Out of Scope

- A setup command or saved setting for a default budget; budgets stay free-form guidance as in 0.32.0. Recorded as possible follow-up work.
- Letting main or the user add a mark plan review did not propose.
- Changing the Runner, the Unbounded probe floor, the budget order or Observed resource risk recording.
- Asking about marks on Unplanned work or work without plan review.
- Hook enforcement of any of these rules.
- Rewriting the acceptance or text of existing specs and tickets.

## Further Notes

- **Limits.** The rules are instructions to the model; the tests cannot show that a model always asks at the stated point. A dropped Claim runs without the Runner requirement, so a risk that plan review saw correctly and the user dropped is caught only by the floor, which covers new or modified tests and probes, not unchanged checks the Plan lists.
- **Fewer stops with a default budget.** A default budget stated in project or user guidance removes the budget question from the ask whenever it covers the Claim, and also lets main run a returned Unbounded probe within it without asking; this spec changes neither.
- **Glossary timing.** The CONTEXT.md change is made with the rule, not with this spec, because existing tests pin the current entry.
- **Tickets.** The work is cut into tickets under `.scratch/resource-risk-confirmation/issues/`, which carry each Claim's acceptance. The rule files, the glossary and the ADR note share the new test module, so they are implemented before the documents and release, the release last.
- Automatic plan review is on, so the tickets get plan review before implementation.

## Overall acceptance

This is the Plan's overall acceptance, which the final check runs once for each commit to be landed or tagged, not once for each Claim; it is not part of any Claim's acceptance, and each ticket cites it.

- The full `unittest discover` suite passes at the commit to be landed or tagged.
