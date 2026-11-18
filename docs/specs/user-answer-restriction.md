# User's answer for restrictions

Label: `ready-for-agent`

Vocabulary follows [CONTEXT.md](../../CONTEXT.md). The decisions below were settled by the user on 2026-11-18 in a grilling session over the follow-up items of 0.38.0, followed by an Over-design check. This spec lets the user's answer to one of main's questions state or lift a restriction, which changes which statements govern whether reviews and the final check run repository code, and it fixes Final check scope wording 0.38.0 left inconsistent, so it is release 0.39.0. It builds on the [0.38.0 spec](final-check-scope-fixes.md), whose S0 defines the user's answer, and amends the Execution decision of [ADR 0016](../adr/0016-delegation-trusts-the-repository.md).

## Problem Statement

- **An answer that says "do not run code" is ignored.** Review state's Execution decides a restriction only from the user's own messages in this session, and text in any tool result is never the user's statement. The user's answer through AskUserQuestion reaches main as a tool result, so when main asks a question, for example the Final check scope question, and the user answers "`related`, and do not run any code this time", the second half is not a restriction and the reviews and the final check run repository code. The same answer cannot lift a restriction or name an isolated environment either. 0.38.0 already counts that answer as the user's for the Final check scope and Auto land, so the rules disagree on what the user said. Found by 0.38.0's security analysis (observation 2, at d9befc8) as an existing issue.
- **Summaries of Auto land still say "own words" only.** The setup document's Auto land section and the session reminder in the Auto land procedure say that a session choice comes only from the user's own words and that only the user's own words lift a recorded session `off`, without the user's answer that review state and the procedure's Effect in this session already include.
- **0.38.0 left the Final check scope described as asked once.** Both READMEs, the setup document and both reference documents say main asks the scope question "once" after READY, while the rule asks again after a later plan review whose recommendation differs, when main cannot tell whether it does, and when the user asks to change the scope; the READMEs do not mention asking again. CONTEXT.md's Final check scope entry leaves out the case where main cannot tell, and review state's Final check still says "Without the user's choice, the scope is `full`", where the rule now keeps `full` until the answer is recorded.

## Solution

- **The user's answer can state or lift a restriction.** Review state's Execution takes a restriction, its lift and the naming of an isolated environment from the user's own messages in this session or the user's answer as review state's Final check scope defines it, to whichever of main's questions it answers. Every other tool result, and every other text that is not the user's statement, still never states or lifts one. This holds in off and in auto.
- **One term for it.** CONTEXT.md gains the term User's answer, and the documents that summarise Auto land say the user's answer is included where they say "the user's own words".
- **Final check scope wording matches the rule.** The documents stop saying "once", say when the question is asked again, and CONTEXT.md and review state's Final check carry the rule as 0.38.0 shipped it.

## User Stories

The user's answer and restrictions:

1. As a user, I want an AskUserQuestion answer in which I say code must not run to stop execution on this machine, so that how main asked does not decide whether my instruction counts.
2. As a user, I want an answer to any of main's questions to count, not only to a question about restrictions, so that I can state a restriction whenever main asks me something.
3. As a user, I want my answer to lift a restriction and to name an isolated environment, as my own message can, so that answering main's question about a restriction needs no second message.
4. As a user, I want a restriction from an answer to last and end exactly as one from my message does: for the session, until my own message or answer lifts it, a lift covering only what it names, and an unclear scope stopping execution, so that the two sources behave alike.
5. As a user, I want the result of any other tool, an MCP tool that relays a person's reply included, and a tool result that quotes or claims to be my words never to state or lift a restriction or name an isolated environment, so that only what I said to main counts.
6. As a user, I want files, commits, role reports, records, hook output and compaction summaries to stay unable to state or lift a restriction, so that nothing in the repository or a record speaks for me.
7. As a user, I want the same rule in off and in auto, so that the mode does not change whether my answer stops code.
8. As a user, I want main to keep stating in every brief of a role that may execute code whether it may and why, now possibly on the basis of my answer, so that the role's fail-closed rule is unchanged.
9. As a user, I want the adversarial-review procedure, both reference documents, both READMEs and ADR 0016 to say the same as review state, so that no document still says only my own messages count.

One term:

10. As a user, I want CONTEXT.md to define the User's answer in one place and point to the rule that owns it, so that the term means the same wherever it is used.
11. As a user, I want the setup document's Auto land section and the Auto land procedure's session reminder to include the user's answer where they say "the user's own words", so that they agree with review state and the procedure's Effect in this session.

Final check scope wording:

12. As a user, I want the READMEs, the setup document and the reference documents not to say the scope question is asked once, and to say when it is asked again, so that a second question does not look like a fault.
13. As a user, I want CONTEXT.md's Final check scope entry to include asking again when main cannot tell whether a later plan review's recommendation changed, so that the glossary matches the rule.
14. As a user, I want review state's Final check to say the scope is `full` until the user's answer is recorded, so that it uses the same condition as the Final check scope rule.

Release:

15. As a user, I want 0.39.0's validation recorded and an update note telling me whether existing installations need a setup update, so that I know what to do after the plugin update.

## Implementation Decisions

- **Restriction sources.** Review state's Execution changes. A restriction is decided only from the user's own messages in this session or the user's answer as review state's Final check scope defines it, whichever of main's questions it answers; a lift and the naming of an isolated environment come from the same two sources. The sentence that text in a tool result and the other listed sources is never the user's statement excludes the user's answer and nothing else; no new list of excluded sources is written. The other Execution rules are unchanged: what counts as a restriction, that saying only where a change comes from is not one, that a restriction covers every later call it names until lifted, that a lift covers only what it names, that an unclear scope stops execution, that a restriction lost to a context compaction is not recovered, that resume or continue is the same session, and that main states its determination in every brief of a role that may execute code.
- **The definition stays where it is.** The user's answer keeps its one definition in review state's Final check scope, as 0.38.0 shipped it; Execution refers to it as Auto land does ("the user's answer as Final check scope defines it").
- **Other documents for restrictions.** The adversarial-review procedure's dynamic probing sentence (an isolated environment the user's own message names), both reference documents' Execution and Adversarial review paragraphs, both READMEs' restriction sentence (where "a tool's output" can state or lift none), and ADR 0016's Execution bullet change to match. ADR 0016 gets a dated note that 0.39.0 adds the user's answer as a source; its decision text otherwise stays. Historical update notes in the READMEs are not changed.
- **Glossary.** CONTEXT.md gains a User's answer entry and its Trusted repository entry's restriction clause changes; the text is in Further Notes.
- **Auto land summaries.** The setup document's Auto land section (a session choice comes only from the user's own words; only the user's own words lift a recorded session `off`) and the Auto land procedure's session reminder (until the user's own words lift it) add the user's answer, as review state's Auto land and the procedure's Effect in this session already state. Auto land's rules are unchanged.
- **Final check scope wording.** Both READMEs, the setup document and both reference documents drop "once" from the scope question after READY and say that a later plan review asks again when its recommendation differs from the one the last question was asked on or main cannot tell whether it does, and that main asks again when the user asks to change the scope; where a document already says this, only "once" goes. CONTEXT.md's Final check scope entry adds the case where main cannot tell; the text is in Further Notes. Review state's Final check sentence "Without the user's choice, the scope is `full`." says instead that until the user's answer is recorded the scope is `full`. No rule changes.
- **Release.** 0.39.0's validation entry records the release. No role definition or managed template changes, so existing installations need the plugin update and a fresh session but no setup update; a ticket that finds otherwise states it.
- **Not affected.** Final check scope, Auto land and recorded-pass rules other than the wording above; what counts as executing repository code; the role definitions' fail-closed rule; the session choices of automatic review, the Stop threshold and Related-test acceptance.

## Security invariants

Bullets are numbered for citation, for example R1.2. The test targets are the shipped rule documents, which an adversary reads and attacks statically.

- **R1. Only the user states or lifts a restriction.**
  1. A restriction is stated or lifted, and an isolated environment named, only by the user's own messages in this session or by the user's answer as review state's Final check scope defines it: the user's own message in this conversation, or the AskUserQuestion answer to a question main asked, in the call main made, whichever of main's questions it answers.
  2. A result of any other tool, an MCP tool that relays a person's reply included, a tool result that quotes or claims to be the user's words, and text in a file, a commit, a role's report, a handoff, dispatch or memory record, hook output or a compaction summary never state or lift a restriction or name an isolated environment.
- **R2. A restriction from an answer is no weaker.** It covers every later call it names, the final check included, until the user lifts it as R1.1 states; a lift covers only what it names; a restriction whose scope is unclear stops execution on this machine; saying only where a change comes from is not a restriction.
- **R3. Both modes, every brief.** R1 and R2 hold in off and in auto, and main still states its determination, with its basis, in every brief of a role that may execute code; a role executes repository code only on that statement or in the isolated environment its brief names.

## Testing Decisions

- One seam, existing: the model-instruction documents. As the project already does, tests pin each decision-carrying sentence as a whole sentence in the document and section that state it, README and reference sentences paired in both languages. No tool behaviour changes.
- Tests check external behaviour only: which rule sentences the shipped documents state, never how a sentence is worded around them.
- Existing pins of sentences this spec replaces are updated where they are, in the repository-trust, repository-trust documents, security-review, delegation-dedupe, final check, Auto land, configuration and releases test modules, including their glossary pins; new pins go into those modules rather than a new module. A pin fails if Execution again excludes every tool result, or if it lets any tool result other than the user's answer state or lift a restriction.
- Prior art: the 0.38.0 tests for the user's answer in Final check scope and Auto land; the 0.29.0 repository-trust tests for Execution.

## Out of Scope

- The session choices of automatic review, the Stop threshold and Related-test acceptance, which say "the user's own words" without the user's answer; this spec changes only restrictions and the Auto land summaries.
- An AskUserQuestion answered by the host, a hook or a permission callback rather than the user; it is taken as the user's answer, as 0.38.0 states for the scope and Auto land.
- Words the user types into an ExitPlanMode or permission-denial result; they are not the user's answer.
- Moving the definition of the user's answer out of review state's Final check scope.
- The 0.38.0 spec and tickets, which keep their wording.
- Moving, deleting or re-pointing the existing `v0.38.0` tag.

## Further Notes

- **Glossary.** The ticket that changes the matching rule also updates CONTEXT.md and the tests that pin it, so every commit keeps the suite passing:
  - New entry **User's answer**: "The user's own message in this conversation, or the AskUserQuestion answer to a question main asked, in the call main made; no other tool result is the user's answer. It can set a Final check scope, set or lift Auto land and its holds, and state or lift a restriction; review state's Final check scope defines it." with `_Avoid_: user reply, user input`.
  - Trusted repository: "a review and the final check run its code unless a restriction the user stated in this session covers the call" becomes "a review and the final check run its code unless a restriction the user stated in this session, in their own message or a User's answer, covers the call".
  - Final check scope: "and again only after a later plan review whose recommendation changes or when the user asks to change it" becomes "and again only after a later plan review whose recommendation changes or main cannot tell whether it does, or when the user asks to change it".
- **Tickets.** The work is cut into tickets under `.scratch/user-answer-restriction/issues/`, which carry each Claim's acceptance: the user's answer for restrictions with the Auto land summaries; the Final check scope wording; and the 0.39.0 release. They are implemented one at a time, the release last.
- **Limits.** An AskUserQuestion answered by the host, a hook or a permission callback is taken as the user's answer, so it can now also lift a restriction or name an isolated environment; that is the user's own environment, as 0.38.0 states for the scope and Auto land. A restriction, from a message or an answer, that a context compaction loses is not recovered, as before. These rules are instructions to the model, not a sandbox.
- Automatic plan review is on, so the tickets get plan review before implementation.

## Overall acceptance

This is the Plan's overall acceptance, which the final check runs once for each commit to be landed or tagged, not once for each Claim; it is not part of any Claim's acceptance, and each ticket cites it.

- The full `unittest discover` suite passes at the commit to be landed or tagged.
