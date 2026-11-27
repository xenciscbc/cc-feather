# Release 0.50.0

Label: `ready-for-agent`

Vocabulary follows [CONTEXT.md](../../CONTEXT.md). This spec releases two changes the user accepted for implementation on 2026-11-27 and that are committed on the branch `test-design-review-fixes`: [the test design and speed-up review fixes](test-design-review-fixes.md), in 81ffd40, and [recommending light by content](review-level-content-condition.md), in 32b868e. Both were implemented at Review level `light`, with code review APPROVED. The user chose Review level `standard` for this release, since creating a tag is an irreversible operation.

## Problem Statement

0.49.0 is on `main` and tagged, so the two changes need a new version before they are released, as the project's CLAUDE.md requires. Users reading the Updates sections need to know what changed and whether a setup update is needed, and the validation document needs the release's entry.

## Solution

Release 0.50.0: the manifest version, the Updates notes in both languages, the validation entry and the release tests, then the tag on the user's instruction.

## Implementation Decisions

- **Version.** The `version` in `.claude-plugin/plugin.json` becomes 0.50.0. `.claude-plugin/marketplace.json` carries no version.
- **Updates notes.** Each README's Updates section opens with a 0.50.0 note, in English and Traditional Chinese, before the 0.49.0 note, which stays. It says: `/cc-feather:test-design` numbers its decisions for the user, a test that depends on one names it and stays out of the Lean set, a result the spec states is not a decision, and the integration-point and decision-table guidelines choose cases by the defects they catch; `/cc-feather:test-speedup` measures past test result caches, such as Go's with `-count=1`, calls a difference from one run on each side an observation, repeats runs only when the user asks, and says that kept results do not follow changes to the code under test; because the measurement command changes, the first Go measurement after the update has no comparable earlier measurement; and main recommends Review level `light` by the content of a Plan's Claims, not by their number. It then says that existing installations need the plugin update and a fresh session but no setup update, determined from `git diff v0.49.0 HEAD -- templates skills/setup scripts`, which shows no change, and that going back to 0.49.0 means reinstalling the 0.49.0 plugin, with no setup update or remove. It links to the reference's Design and test checks section, as the 0.49.0 note does.
- **Validation entry.** `docs/setup-validation.md` gets a `## 0.50.0 Review fixes` entry after the 0.49.0 entry and any sections for work landed on main after it. It records: the two specs and this one, each ticket and its commit, and that the two changes ran at Review level `light` with code review APPROVED (ticket 01 of the review fixes on its second call, after a wording fix) and no outcome verification; the no-setup-update determination with `git diff` and `git diff-tree -r --name-only` from v0.49.0 over `templates skills/setup scripts`; that the setup document and its count of packaged skills do not change; the way back; the full suite's result on the release's working tree; that the pins show the text, not that a model follows it, and that no live run was made; the first Go measurement without a comparable earlier one; and the tag, as earlier entries do. The review round is recorded after it, on `main` after the tag, as earlier entries do.
- **Release tests.** In `tests/test_feather_releases.py`, the 0.49.0 tests that pin 0.49.0 as the latest release move to 0.50.0 as earlier releases moved them: the manifest version test moves to the new 0.50.0 class, the 0.49.0 note is checked to follow the 0.50.0 note, and the 0.49.0 entry is checked to be followed only by sections for work landed on main after 0.49.0 and then the 0.50.0 entry; earlier releases' evidence is unchanged. A 0.50.0 release test class pins the manifest version, the notes' sentences in both languages in order, the no-setup-update and way-back statements, the note's link and the validation entry's statements above, and that the entry is the file's last release entry.
- **Tag.** `v0.50.0` is created only on the user's instruction, after the Plan's passes and final check, after checking that the manifest version at the tagged commit is 0.50.0 and that no `v0.50.0` exists; no existing tag is moved.
- **Not affected.** Every file the two released changes own, every skill, role definition, template, setup procedure and script, `CONTEXT.md` and `docs/setup.md`.

## Testing Decisions

- The release tests pin the notes and the entry as whole statements, as the 0.49.0 release tests do, with the earlier releases' tests as prior art.
- The ticket changes the plugin manifest's version, the plugin's packaging configuration, so its related tests are the full suite.

## Out of Scope

- A live run of `/cc-feather:test-design` or `/cc-feather:test-speedup`: the released changes reword existing rules, the pins show the wording, and 0.49.0's live run already exercised the command's report shape, which this release does not change.
- Any change to the released wording or to the specs of the two changes.
- Deleting the work branch, which follows landing as the user's practice states.

## Further Notes

- **Tickets.** One ticket, `.scratch/release-0-50-0/issues/01-release.md`.
- **Limits.** The two changes got no outcome verification, as `light` gives it up; the final check at the commit to be landed runs the full suite over them.

## Overall acceptance

This is the Plan's overall acceptance, which the final check runs once for each commit to be landed or tagged, not once for each Claim; it is not part of any Claim's acceptance, and each ticket cites it.

- The full `unittest discover` suite passes at the commit to be landed or tagged.
