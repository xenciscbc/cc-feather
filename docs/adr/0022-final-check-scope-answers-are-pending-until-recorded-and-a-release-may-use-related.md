# Final check scope answers are pending until recorded, an overall run can cover primary acceptance, and a release may use `related`

[ADR 0021](0021-final-check-passes-are-recorded-and-clean-plans-may-land-themselves.md) let the user choose a Plan's Final check scope and kept the choice in the Plan's Dispatch record, but stated no point at which the answer is written. An Adversarial review of 0.37.0 broke S2 with that gap: when a later plan review after a Deviation asks again and the user widens `related` to `full`, a context compaction before main writes the new answer leaves the record's stale `related`, the final check passes at it, and with Auto land on the Plan lands without the overall acceptance. ADR 0021 also had the final check at `full` run each Claim's primary acceptance again besides the overall acceptance, even when the overall run had already run those tests, and made every release or tag run `full`.

The user decided (2026-11-18, in a grilling session with a second opinion from Codex; the [spec](../specs/final-check-scope-fixes.md) carries the acceptance), for the Automatic flow only:

- **A scope question is pending until its answer is recorded.** Before asking a Final check scope question, main writes it into the Plan's Dispatch record as pending, replacing any earlier answer; the user's answer to that question replaces the mark at the next point between review calls. A pending question means `full`. A correction of a recorded answer goes through a new pending question. A compaction summary still never sets the scope.
- **The overall run can stand for a primary acceptance rerun.** At `full`, a Claim's primary acceptance counts as rerun when the overall acceptance's own run, at the commit to be landed, ran it with the same tool and the same conditions that decide which tests run and how, differing only in that the primary acceptance names part of what the overall run selects, and that run's output shows each named test unit ran and passed. Otherwise it runs separately. The rule names no language or test runner.
- **A release or tag may use `related`, on the user's answer for that commit.** A `full` pass valid at the commit to be tagged is used without asking. Otherwise main asks, for that commit, whether to run `full` or tag on the `related` pass, with the question pending first and `full` while it is. The answer chooses only what the final check runs; tagging still needs the user's instruction.

This amends ADR 0021's "a release always runs `full`" and its rerun of every Claim's primary acceptance at `full`. Off mode is unchanged.

## Considered Options

- **Write the answer at the first gap and let a compaction summary only widen the scope**: the fix first discussed. It leaves an answer lost before the write and absent from the summary unrecoverable, and it makes a summary a source of the scope; the pending mark closes the gap without either.
- **Rerun primary acceptance only when its command equals the overall acceptance's**: needs no judgement, but saves nothing when a Claim names part of the suite, which is the common case under Related-test acceptance.
- **Keep every release at `full`**: the strongest release check, but it reruns the whole suite at a commit whose Plan the user already chose to check at `related`.

## Consequences

A widened answer can no longer be lost into a narrower scope, and a stale `related` cannot land a Plan. The final check at `full` can be shorter, and the decision at the end of the Plan and the report name the Claims the overall run covered. A release can be tagged without the overall acceptance having run at that commit when the user says so for that commit; the tag report states it. Whether an overall run covered a primary acceptance is main's judgement from the commands and the run's output, which repository code controls, as it already controls the final check's output.
