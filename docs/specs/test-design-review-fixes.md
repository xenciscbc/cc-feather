# Test design and speed-up review fixes

Label: `ready-for-agent`

Vocabulary follows [CONTEXT.md](../../CONTEXT.md), which defines Test design, Speed-up record, Plan and Claim. The decisions below were settled by the user on 2026-11-27, starting from a review that a codex-feather session sent after porting cc-feather 0.49.0 (commit 8064721), with a case rehearsal of `test-design`. Main checked each of its five points against the current text and the user chose which to adopt. This spec changes the `test-design` skill, its guideline reference, the `test-speedup` skill and the reference documents; it changes no installed guidance, role definition, template or script.

## Problem Statement

In the rehearsal, a `test-design` report listed "an empty queue raises KeyError" as a contract to confirm and still put the test relying on it in the Lean set. The skill already leaves such tests out of the Lean set, but main's integration has no step that checks it, and nothing lets a test name which decision it depends on. Nothing says either that a result a spec already states is not an open decision when the current code has not been checked against it, so a report can hold back a test that only verifies a stated requirement.

Two guidelines invite under-testing. One integration test per point reads as a limit, so different failures at one boundary, such as error mapping, rollback or serialization, can collapse into one success case. Decision tables give one case per combination "that leads to a distinct outcome", which reads as one case per outcome: with A OR B, only-A and only-B both give true, yet each catches a different missed condition.

`test-speedup`'s measurement can report a false gain. Go's test result cache makes a cached package take almost no time, and a single run on each side is reported as a gain in seconds although run-to-run noise can explain it. The incremental static pass keeps the results of unchanged test files even when the code under test changed; that is a decision of [the Speed-up record spec](test-speedup-record.md), but the report does not tell the user so, nor how to re-check a part.

## Solution

Decisions for the user are numbered, a dependent test names its number, a stated requirement is not a decision, and main's integration checks the Lean set against the decisions. The two guidelines are reworded so that they choose cases by the defects they catch. Measurement bypasses result caches, calls a single-run difference an observation and repeats runs only when the user asks. The Since the last run section says what kept results do not follow and how to re-check a scope. Every change rewrites or extends an existing sentence; no new section, process or script change is added.

## User Stories

1. As a user, I want each decision for me numbered and each test that depends on one to name its number, so that I can see what my answer unblocks.
2. As a user, I want main to check the Lean set against the decisions before reporting, so that the Lean set never assumes my answer.
3. As a user, I want a test whose expected result the spec states not held back because the current code was not checked, so that stated requirements still get their tests.
4. As a user, I want an integration point to get a case for each failure that can cross it on its own, so that error mapping, rollback and serialization are not collapsed into one success case.
5. As a user, I want decision-table cases chosen so that each condition is shown to change the outcome on its own, so that combinations with the same outcome are not merged when they catch different defects.
6. As a user, I want measurement to bypass a cache of earlier test results, so that a cached package is never reported as a speed-up.
7. As a user, I want a difference from one run on each side called an observation, and repeated runs only when I ask, with their median and range, so that noise is not reported as a gain and no run is repeated without my agreement.
8. As a user, I want the report to say that kept results do not follow changes to the code under test or imported libraries, and that `--full` with a scope analyses it again, so that I know when and how to re-check.

## Implementation Decisions

- **Numbered decisions.** In the `test-design` skill's Decisions for the user item, the sentence "A test that depends on an open decision names it." becomes: each decision is numbered, and a test that depends on an open decision names its number. A sentence follows it: a test whose expected result a spec or acceptance passage states depends on no decision, even where the current implementation has not been checked against that result.
- **Main's integration check.** The Main's integration paragraph adds that main checks each Lean set entry against the numbered Decisions for the user and leaves out of the Lean set any test that depends on one. The Lean set item's own exclusion sentence stays.
- **Integration points.** The guideline One integration test per point is renamed Focused cases per integration point: each integration point gets the fewest focused integration cases that check both sides agree while catching each failure that can cross that boundary on its own, such as error mapping, transaction rollback or serialization. Its applies and does-not-apply sentences stay.
- **Decision tables.** The Decision tables guideline chooses its combinations so that each condition is shown to change the outcome on its own, with impossible combinations left out, and states that two combinations with the same outcome are not alike when each would catch a different wrong or missing condition. Its applies and does-not-apply sentences stay.
- **Result caches.** The `test-speedup` measurement offer's command bypasses any cache of earlier test results, such as Go's with `-count=1`, so that every selected test runs.
- **Observations.** In `test-speedup`'s measurement, a difference between one run on each side, a speed-up's gain or a change in the comparison with the last measurement, is reported as an observation, not a confirmed gain. When the user asks to confirm one, a new offer states how many runs to repeat, the runs take place only after the user agrees and under the same rules as the rest of measurement, and the report gives their median and range.
- **Kept results.** `test-speedup`'s Since the last run section also says that the results kept for files not analysed again do not follow changes to the code under test or to the libraries the tests import, and that `--full` with a scope analyses that scope again. The incremental static pass itself does not change.
- **Documents.** In both reference documents, the Test design section adds that decisions for you are numbered, that a test depending on one names it and stays out of the Lean set, and that a test whose expected result the spec states depends on none; the Test speed-ups section adds the result-cache bypass and the observation rule. Sentences are paired in English and Traditional Chinese. The READMEs do not change.
- **Not affected.** The judging rule, grades, report sections and their order, the Lean set item, the other guidelines, the shared test criteria, the Speed-up record script and its comparison key, the incremental static pass, the delegation skill, plan review, every review procedure, the role definitions, setup and CONTEXT.md.

## Testing Decisions

- No executable seam: the skills are model instructions. Following the project's practice, tests pin each decision-carrying sentence as a whole sentence where it is stated, reference sentences paired in both languages.
- The pins go in the existing design checks test module. The pin of the replaced Decisions for the user sentence moves to the new wording; new pins cover the stated-requirement sentence, the Main's integration check, both reworded guidelines under their labels, the result-cache sentence, the observation sentences, the kept-results sentence and the new reference pairs.
- Old wording: a check shows that "One integration test per point", "one case per combination that leads to a distinct outcome" and "A test that depends on an open decision names it." no longer appear.
- The guideline reference keeps passing the existing check that it carries no source labels, citations or digits, and the check that each guideline states where it applies.
- Prior art: the `TestSpeedupCommandTests` and `TestDesignCommandTests` pins in `tests/test_feather_design_checks.py`.

## Out of Scope

- Tracking the code under test or imported libraries in the incremental static pass, which [the Speed-up record spec](test-speedup-record.md) excludes.
- Adding the host, the tool versions or the cache state to the measurement's comparison key.
- Storing the test runner versions with each measurement so that a comparison can name a version difference as a limit; it needs a script change and is left for a later plan.
- Warm-up runs, or any rule on cold and warm caches other than the result cache.
- A threshold for noise, or a default number of repeated runs.

## Further Notes

- **Tickets.** One ticket, `.scratch/test-design-review-fixes/issues/01-review-fixes.md`, implements every Implementation Decision. The release is a separate step after it, with its own ticket.
- **Review level.** The user chose the `light` Review level for the Plan of ticket 01.
- **Limits.** The pins cannot show that a model numbers decisions or checks the Lean set; the rehearsal that found the gap ran under codex-feather.

## Overall acceptance

This is the Plan's overall acceptance, which the final check runs once for each commit to be landed or tagged, not once for each Claim; it is not part of any Claim's acceptance, and each ticket cites it.

- The full `unittest discover` suite passes at the commit to be landed or tagged.
