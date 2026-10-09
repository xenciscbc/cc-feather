# Auto's repository authority is disclosed and narrowed; acceptance has one explicit exception; gated claims stay gated until landed

ADR 0007 let main commit and push a gated Claim before its passes, but the always-loaded guidance and the toggle never said so, the push authority covered any non-default branch and, in off mode, any Claim an active handoff recorded. The user had no explicit way to accept a Claim without both passes, while a won't-do ticket value or a casual "done" could read as acceptance. A review of 0.16.0 also confirmed two defects in the rules themselves: in off mode one explicit pass removed the handoff note that kept a Claim gated, and a narrowed second review could follow a call that judged nothing.

The user decided (2026-10-08):

- **U1**: in auto, committing before the passes, pushing to working branches and opening pull requests stay on, and are disclosed in the always-loaded guidance, the toggle's Meaning, the auto-on description and both READMEs.
- **U2**: main pushes freely only to a branch it created for the current work and asks before pushing to a pre-existing remote branch it did not create; in a resumed session a branch counts as its own only when an active handoff records that.
- **U3**: a sixth user decision, accept and land, is the only way past the acceptance gate without both passes: explicit, recorded with the commit it accepts, the missing passes and the remaining risk, visible in reports and handoffs, and never a READY, APPROVED or CONFIRMED. A casual "done" counts only once main confirms and records it.
- **U4**: in off mode, a Claim gated only by an active handoff record gets the local commit a gated call needs; pushes and pull requests follow off-mode behaviour.
- **U5**: an accept-and-land decision recorded in an active handoff still holds in a resumed session until a relevant change follows the commit it names.
- **U6**: when the handoff tool's first Git probe cannot run Git or times out, a save is a partial `tracking-failed` result with `cause_code: git-unavailable` and a recovery that waits for Git.
- **U7**: the configuration tool reports an unedited managed role rendered from an older template as needing setup update; `model`, `review` and session export refuse until then.

The agreed corrections:

- **Gate lifetime.** A gated Claim stays gated after either single pass. A pass turns the handoff's unreviewed or unverified note into a pending-acceptance note, which is removed only when the Claim is landed, released or reported complete, or cancelled with its commits disposed of; an accept-and-land decision is recorded in it.
- **Retry coverage.** Only a completed call establishes coverage. A narrowed second review and the range from the previously judged commit follow only when the previous call completed; otherwise the next call reviews the full scope from the base, with earlier and partial findings as evidence. Budgets are unchanged.
- **Completion values.** The gate covers done values; a won't-do value is set only on a recorded cancellation and never counts as acceptance. Finished means not redone; only a done value set after valid passes or accept and land, with no relevant change since, counts as accepted. A waiver names what it waives and does not complete a gated Claim; a work-in-progress push satisfies neither release nor completion.

## Considered Options

- **Make pre-pass pushes and pull requests opt-in**: safer by default, but loses the reclaimed-environment protection ADR 0007 was made for; disclosure was chosen instead.
- **Keep push authority for any non-default branch**: exposes shared branches the user forgot to name.
- **No way to accept without both passes**: leaves a knowingly accepted Claim unable to land; a recorded decision keeps the risk visible instead.
- **Fold the closing check into one pass, or keep removing the note on a pass**: lets an approval alone, as from an explicit review in off, release a Claim unverified.
- **Narrow by call count**: a retry after a call that judged nothing could approve code nobody reviewed.
- **Rely on release notes for stale roles; add a session-start hook**: notes are missed and a hook is out of scope; the tool reports it instead.

## Consequences

This amends ADR 0007's push rule, its handoff-note lifetime and its rule that a finished ticket counts as accepted: the gate covers done values, finished means not redone, and only a done value set after valid passes or accept and land, with no relevant change since, counts as accepted. The reviewer and analyst role definitions and the automatic review guidance change, so every scope where delegation is installed needs setup update and a fresh session; until then `check` reports the stale roles and `model`, `review` and session export ask for the update. These remain model instructions rather than hook-enforced gates.

(Amended by ADR 0009: a Security-critical claim also needs a valid HELD from Adversarial review, or the user's accept-and-land decision, which may cover the missing HELD and then also names the known vulnerabilities; its pending-acceptance note names a missing Adversarial review.)
