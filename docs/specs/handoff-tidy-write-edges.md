# Handoff tidy write edges

Label: `ready-for-agent`

Vocabulary follows [CONTEXT.md](../../CONTEXT.md), which defines Handoff tidy and Follow-up record. This spec amends [the handoff tidy spec](handoff-tidy.md) released in 0.27.0: it replaces that spec's Acceptance item 8 and narrows one sentence of the rules behind its Acceptance item 11. That spec is otherwise unchanged and stays as the record of 0.27.0. This spec is one claim: it lists no claims and has no tickets.

## Problem Statement

A Handoff tidy compares each record's version with the one it noted when proposing, and writes a record only when they match. A confirmed proposal often writes the same record more than once: two merges into one target, or a merge target that also receives a check's written-back results. After the first write the record's version has changed, so the rule as written refuses the second write and the confirmed proposal cannot be carried out. Comparing with the latest version instead would let the second write be built from the record's text at proposal time and overwrite what the first write added, losing moved items and their gate notes.

Separately, the command says it only offers an archive retry and runs none unless the user asks, while its write order hands a failed archive of a source it completed to the handoff skill, whose rule is to retry. A reader cannot tell which applies.

## Solution

Before each write, the tidy reads the record and checks that it is still exactly as the tidy last saw it: as read when proposing or, after the tidy's own write to it, as the tool reported that write saved it. It then builds the write from that current content, applying only the confirmed change. A record in any other state is not written, and its part of the proposal is proposed again. The sentence about only offering a retry or repair covers the abnormal records a tidy finds when reading; a failed archive of a source the tidy itself completed follows the handoff skill's Archive completed work.

Other edge cases found in the 0.27.0 review were weighed and are not changed; see Out of Scope.

## Acceptance

1. The command's version comparison states, replacing Acceptance item 8 of the handoff tidy spec: when proposing, the tidy notes each record's version as the handoff tool reports it; before each write to a record it reads the record again and compares its version with the version the tidy last saw, which is the one noted when proposing or, after the tidy's own write to that record, the version the tool reported as saved by that write; a record whose version differs is not written, and its part of the proposal is proposed again, while confirmed changes to other records proceed.
2. The command states that each write is built from the record's content as read for that comparison, applying only the confirmed change, so an earlier write of the same tidy, such as an earlier merge into the same target, is kept.
3. A version observed in a read-back that differs from the version the tool reported as saved by the tidy's write counts as a change the tidy did not make: the record is not written again and its remaining part is proposed again.
4. The command's statement that it only offers the archive retry and the reviewed repair, and runs neither unless the user asks, applies to abnormal records found when reading. A failed archive of a source the tidy itself completed is handled as the handoff skill's Archive completed work describes, with the tool's archive command and the result-specific rules that skill states.
5. Command contract tests pin the sentences of items 1 to 4. A tool scenario test drives the unchanged handoff tool through two merges into the same target: the second update, made with the version returned by the first and built from the content that write saved, keeps the first merge's items and gate note, while an update with the version noted before the first write is refused.
6. The version is 0.27.1. Both READMEs carry a 0.27.1 update note saying that it changes no installed role definition or policy, so only the plugin update and a fresh session are needed, and how to go back to 0.27.0. The `docs/setup-validation.md` entry for 0.27.1 records the validation, that no live rehearsal was run for this patch, and that the tests cannot show that a model follows these rules.
7. Nothing changes in the handoff tool, the record format, the handoff skill, the installed roles or the policy.

## User Stories

1. As a user, I want a confirmed proposal with two merges into one target to be written in full, so that I do not have to tidy again for the second merge.
2. As a user, I want a record that receives both a merge and written-back check results to get both, so that one confirmation covers what I confirmed.
3. As a user, I want each write built from the record as it is now, so that an earlier write of the same tidy is never overwritten.
4. As a user, I want moved items and their gate notes kept when a target receives a second write, so that nothing restricted is lost.
5. As a user, I want a record someone else changed during the tidy to be proposed again rather than written, so that concurrent work is not overwritten.
6. As a user, I want a read-back that shows an unexpected change treated as someone else's change, so that the tidy never builds on content it did not write.
7. As a user, I want to know whether the tidy retries a failed archive of a source it completed, so that I am not left guessing.
8. As a user, I want that retry to follow the handoff skill's existing archive rules, so that the tidy adds no rule of its own for it.
9. As a user, I want the "only offers" rule to keep covering abnormal records the tidy finds, so that it still never repairs what it only read.
10. As a user, I want the edge cases that were weighed and left alone to be stated with the reason, so that I can revisit them later.
11. As a user, I want the patch to need only the plugin update, so that I do not have to rerun setup.
12. As a user, I want to know how to go back to 0.27.0, so that I can undo the patch if needed.
13. As a maintainer, I want tests that fail if the new sentences are removed, so that the rules do not regress.
14. As a maintainer, I want a tool test of two sequential merges into one target, so that the rule is shown to be executable with the existing tool.
15. As a maintainer, I want the validation entry to say that no rehearsal was run, so that the release record is honest about what was checked.

## Implementation Decisions

- The version comparison subsection of the command's confirmation and writes rules is rewritten as one rule covering the comparison, the baseline after the tidy's own write, building from current content and the read-back case; the write order and gate note rules stay as they are.
- The baseline after a write is the version the handoff tool reports for the content that write saved; a version seen only in a later read is never adopted as a baseline.
- The sentence in the abnormal records rules is narrowed by scope only; the archive handling it hands over is the handoff skill's existing Archive completed work, not restated.
- The rules stay host-neutral; the Claude Code section is unchanged.
- The release is 0.27.1 and changes no installed role definition or policy.

## Testing Decisions

- Good tests check what users and hosts can observe: the shipped command text and the tool's behaviour on real files.
- Command contract: the existing handoff tidy command tests pin the sentences of Acceptance items 1 to 4 and drop only the pin of the replaced version-comparison sentences.
- Tool sufficiency: the existing handoff tidy merge scenario module gains the two-merges-into-one-target scenario of Acceptance item 5, in the same style as its other scenarios.
- Release: the existing release tests pin the version, the 0.27.1 update note in both READMEs and the validation entry.
- Not automated, and not rehearsed: whether a model follows these rules.

## Out of Scope

- A source that changed after the proposal while the target of its merge was already written, which leaves items in both records: it needs another writer of the same record within minutes, the handoff skill already allows one writer per work item, and the existing per-record comparison prevents an overwrite, so the result is duplication, not loss.
- A target written while the source update fails: it needs a concurrent write, an I/O error, a refused details format or an unavailable Git; the handoff skill's rule to retain recoverable data and report the actual state, and the tool's returned recovery, already cover it, including a source saved before tracking or archival failed.
- Bounds on the archive retry, such as waiting for another history writer, resolving the reported cause first or never retrying after `archived: true`: the handoff skill and tool already state them.
- Ordering or combining overlapping merges, and every other Follow-up record item of 0.27.0 not named above.
- Changes to the handoff tool, the record format, the handoff skill, the installed roles or the policy.
- A live rehearsal.

## Further Notes

- Origin: the `handoff-tidy-followups` Follow-up record of 0.27.0, items 1 to 4 of its write-rule group, and a Codex second opinion (gpt-6-astra) on 2026-10-16, whose finding that a later write could overwrite an earlier one with stale content led to Acceptance items 2 and 3. Its other findings are the Out of Scope items above, weighed by how often each case occurs and whether existing rules already cover it.
- For codex-feather: the changed command sentences are host-neutral and port as written.
