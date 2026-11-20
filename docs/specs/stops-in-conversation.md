# Stops in the conversation

Label: `ready-for-agent`

Vocabulary follows [CONTEXT.md](../../CONTEXT.md). The decisions below were settled by the user on 2026-11-20 in the conversation that followed the 0.42.1 release; they extend the reason [ADR 0023](../adr/0023-a-plans-review-level-is-the-users-choice.md) gives for a light Plan's stop at the end to every stop after implementation has started. This spec changes review state and the READMEs, so it is release 0.43.0.

## Problem Statement

When main stops to wait for the user after a Plan's implementation has started, the user is usually away: the stop comes after a long run of implementation, reviews and checks, and by the time the user answers, the prompt cache has often expired. If main asked with a question tool, the pending question holds the turn open; a user who wants to leave first, with `/clear` or a new session, has to dismiss it, and the dismissal returns a tool result that makes the model run once more at full, uncached context cost. A stop that ends the turn in the conversation lets the user leave without that call.

Today only a light Plan's stop at the end is required to be made in the conversation. The decision at the end of a `standard` Plan, and the stops in the middle of one, may use a question tool at main's discretion.

## Solution

Once a Plan's implementation has started, every stop where main waits for the user is made in the conversation, ending the turn, without a question tool. The questions main asks before a Plan's implementation starts, the Review level question and the ask after READY about resource-risk marks and the Final check scope, keep AskUserQuestion: the user has just asked for the work and is usually present, and their options are fixed.

The rule is written once, in review state, and the light Plan's stop at the end refers to it.

## User Stories

1. As a user, I want the decision at the end of a Plan made in the conversation, so that I can leave with `/clear` or a new session without paying for another model call.
2. As a user, I want a stop at the Stop threshold after implementation has started made in the conversation, for the same reason.
3. As a user, I want a stop for a Deviation, for Unknown state, for Implemented before plan review or for an accept-and-land decision made in the conversation, for the same reason.
4. As a user, I want the stop to list what I need to decide and the options I have, so that I can answer in my own words.
5. As a user, I want my own message answering the stop to count as my answer, as it already does under the definition of the user's answer.
6. As a user, I want the Review level question and the ask after READY to keep AskUserQuestion, so that the fixed choices I answer while present stay one click.
7. As a user, I want the light Plan's stop at the end to follow the same rule, stated once.
8. As a maintainer, I want the rule stated once in review state and referred to elsewhere, as ADR 0017 requires.

## Implementation Decisions

- **Owner.** Review state states the rule once, in its Ticket status and user decisions section: once a Plan's implementation has started, main makes every stop where it waits for the user in the conversation, ending the turn, without a question tool, listing what the user is to decide and the options; the user's own message is the answer, as the user's answer is defined. It names, as examples, the decision at the end of the Plan, an accept-and-land decision, a stop at the Stop threshold, a Deviation, Unknown state and Implemented before plan review. It states that the Review level question and the ask after READY keep AskUserQuestion.
- **Light.** Review level's The stop at the end keeps its content and refers to the rule instead of saying "without a question tool" itself.
- **Unchanged.** What each stop decides, who may answer, what counts as the user's answer, what is recorded, the Review level question, the ask after READY, Auto land and every other rule.
- **Documents.** Both READMEs say, where they describe the decision at the end of a plan, that main asks in the conversation, paired in both languages.

## Testing Decisions

- One seam, existing: the shipped model-instruction documents. Tests pin each decision-carrying sentence as a whole sentence in the document and section that state it, README sentences paired in both languages.
- Tests check external behaviour only: which rule sentences the shipped documents state.
- The new sentences are pinned in a new test module using the shared test support; existing pins of sentences this spec changes, such as the light Plan's stop at the end, are updated where they are.
- Prior art: the Review level tests.

## Out of Scope

- The Review level question and the ask after READY: they keep AskUserQuestion.
- Any change to what a stop decides or records, to Auto land, or to the definition of the user's answer.
- Stops outside a Plan's implementation, such as Unplanned work.

## Further Notes

- Automatic plan review is on, so this spec's ticket gets plan review before implementation; this work changes review rules, so it runs at `standard`.

## Overall acceptance

This is the Plan's overall acceptance, which the final check runs once for each commit to be landed or tagged, not once for each Claim; it is not part of any Claim's acceptance, and each ticket cites it.

- The full `unittest discover` suite passes at the commit to be landed or tagged.
- `.claude-plugin/plugin.json` states version 0.43.0, and `docs/setup-validation.md` records the release's validation under its version heading.
