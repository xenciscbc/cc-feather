# Each delegation rule is written once

Until 0.29.0 the delegation skill restated its rules across files: the reading-set paragraph appeared almost word for word in the delegation skill, review state, code review, outcome verification and Adversarial review, and the dispatch record, Resumed sessions, per-claim timing, completion criteria, the Follow-up record and the Adversarial review premise were each restated in two to seven places. The reference documents, `docs/reference.md` and `docs/reference.zh-TW.md`, promised to state every rule in full, a third copy in two languages. The copies drifted: most of the findings the review rounds of 0.19.0 to 0.29.0 left open were one copy saying something slightly different from another, and every rule change had to find and update every copy.

The user decided (2026-10-20, in two grilling rounds, each checked by a Codex second opinion; the [spec](../specs/delegation-dedupe.md) carries the acceptance and its security invariants):

- **One owner per rule.** Each runtime delegation rule is written once, with its conditions, in the file responsible for it: state that more than one step keeps in review state, a rule of one procedure in that procedure, and routing, dispatch and the Security-critical definition in the delegation skill.
- **Pointers elsewhere.** Every other place keeps one sentence that says what main does at that point and points to the owner by name, carrying no condition or exception of the rule. A pointer to a procedure other than review state tells main to read the named part and follow it before acting.
- **An explicit read of review state.** Main reads review state in full before any decision or brief that depends on a rule it owns, in off and in auto, and again after context compaction, at the start of a new or resumed session and whenever it cannot quote the sentence it is about to apply.
- **Briefs keep what a role must be told.** Where a role must receive an instruction, such as following a citation only to the cited part, the procedure that writes the brief keeps that requirement; role definitions do not change.
- **The reference explains and links.** The reference documents explain what each rule is for and when it applies, and link to the procedure or review state item that states it, instead of restating the rules with their conditions. They keep every limit and residual risk they documented, as explanation, and the READMEs no longer promise that they state every rule in full.

## Considered Options

- **Keep the restatements**: each copy has to be found and updated on every rule change, and the copies keep drifting, which most open review findings showed.
- **Keep the reference as a full restatement**: a third copy in two languages, checked against the procedures by hand on every change, with the same drift.
- **Read only named sections of review state**: main would load less text, but a rule applied without the conditions stated elsewhere in review state is the drift this decision removes, and which sections a decision needs is itself a judgement that can miss one.

## Consequences

A reader of the reference follows one more link to reach a rule's exact conditions, and a reader of a procedure follows a pointer to its owner. Briefs still repeat what a role must be told, since a role reads only its brief. Main loads review state in full where it used to read restatements, which the spec's results file measures per entry. No rule changes; the condition inventory and the scenario comparison are the evidence that the contracts are preserved, not proof that a model behaves identically.
