# Related-test acceptance

Label: `ready-for-agent`

Vocabulary follows [CONTEXT.md](../../CONTEXT.md). The decisions below were settled by the user on 2026-11-10 in a grilling session recorded in the handoff `.feather/handoffs/per-claim-test-scope.md`. This spec adds one optional delegation setting; it changes no review procedure, no final check rule and no existing ADR, so it is release 0.34.0.

## Problem Statement

In this repository every ticket's acceptance ends with "The full suite passes.", so each Claim runs the whole test suite before its code review, again after every fix, and once more for each Claim when the final check reruns every Claim's primary acceptance at the commit to be landed. The suite drives tools as subprocesses against real Git repositories; on Windows it takes about 439 seconds for 1191 tests, and one run was stopped half-way when the machine ran out of memory. A seven-ticket Plan therefore spends close to an hour on full-suite runs at its final commit alone, most of them repeating the same check.

Nothing in delegation asks for this. Review state's Final check runs the Plan's overall acceptance, "such as the full test suite"; code review and outcome verification run each Claim's primary acceptance, whatever its acceptance names. The full suite is in every Claim only because whoever cut the tickets wrote it there, since neither the spec nor the tickets said which tests a Claim should run. A user who wants each Claim to run only its related tests, with the full suite left to the final check, has no way to tell main to write acceptance that way, for one session or as a standing preference.

## Solution

A new optional delegation setting, **Related-test acceptance**, off by default. While it is on, main writes each new Claim's acceptance in a spec, ticket or plan with the tests related to the change instead of the full test suite, and keeps the full suite in the Plan's overall acceptance, which the final check runs. Because the final check is part of delegation, the setting exists only where delegation is installed, like the Review mode and the Stop threshold.

The user can turn it on or off:

- for the current session, with `/cc-feather:related-tests on|off` without a scope or by saying so; nothing is written;
- for a project or for their user configuration, with `/cc-feather:related-tests on|off|default project|user`, which saves it through the configuration tool and writes the rule into the managed delegation guidance; a project's choice overrides the user's, and `default` removes the saved choice.

It changes only acceptance written while it is on. Acceptance the user wrote, specs and tickets that already exist, a fix Claim's acceptance and the final check keep working as they do today. An installation where nobody turns it on behaves exactly as 0.33.0.

## User Stories

1. As a user whose test suite is slow, I want each Claim to run only the tests related to its change, so that implementing a Plan does not spend most of its time rerunning the whole suite.
2. As a user, I want the full suite to still run once before landing or release, so that a Claim that breaks something outside its related tests is caught before it reaches the default branch.
3. As a user, I want the setting off by default, so that updating cc-feather does not change how my existing projects write acceptance.
4. As a user, I want to turn the setting on for one session, so that I can try it without saving anything.
5. As a user, I want to save the setting for one project, so that only the project with a slow suite uses it.
6. As a user, I want to save the setting for my user configuration, so that every project where I use delegation writes acceptance this way.
7. As a user who saved it for my user configuration, I want to turn it off for one project, so that a project whose suite is fast, or whose dependencies are hard to trace, keeps the full suite in every Claim.
8. As a user, I want the setting to exist only where delegation is installed, so that no installation narrows each Claim's tests without a final check that runs the full suite.
9. As a user, I want acceptance I wrote myself to keep its wording, so that the setting never overrides my own choice of checks.
10. As a user, I want existing specs and tickets to keep their wording, so that turning the setting on does not change the acceptance of Claims already reviewed and reopen their passes.
11. As a user, I want a fix Claim's acceptance unchanged, so that a final check failure is still fixed against the check that failed.
12. As a user, I want the related tests found by searching the tests for the changed files' paths and directory names, so that tests that read a file without importing it, such as text pins and tools run as subprocesses, are included.
13. As a user, I want a Claim that changes shared test support or build configuration to name the full suite, so that a change most tests depend on is not checked by a guess.
14. As a user, I want a Claim whose related tests cannot be determined to name the full suite, so that uncertainty falls back to the safe choice.
15. As a user, I want the release Claim to name the full suite, so that a release is always validated by the whole suite.
16. As a user, I want the only Claim of a Plan without its own overall acceptance to keep the full suite, so that a one-ticket Plan's final check still runs the whole suite.
17. As a user, I want the named tests treated as a minimum, so that main can run more when the implementation touches a file the list did not foresee without changing the Claim's acceptance.
18. As a user, I want to see whether the setting is on and where it comes from, so that I know how main will write the next Claim's acceptance.
19. As a user, I want `show` and `check` to report the saved setting, so that I can inspect it without reading the guidance file.
20. As a user, I want removing delegation to remove the setting as well, so that no rule is left behind without the delegation it depends on.
21. As a user, I want setup update, model changes, Review mode changes and Stop threshold changes to keep the setting, so that I do not have to set it again.
22. As a user, I want a downgrade note, so that I know to remove the saved setting before going back to a version that does not understand it.
23. As a user, I want the setting to apply in off and in auto alike, so that the final check's full suite protects both modes.
24. As a user, I want the rule stated in the guidance that is always loaded, so that it applies when main writes a spec or tickets even though no review is running then.

## Implementation Decisions

- **A delegation setting, not a setup component.** The setting relies on the final check, which only delegation provides, so it is saved in the delegation record and rendered in the delegation block, and only a scope with delegation installed can save it. A separate component was rejected because installing it without delegation would narrow each Claim's tests with nothing guaranteed to run the full suite. A repository-only convention in the issue tracker document was rejected because every repository would have to write and maintain its own.
- **The rule lives in the guidance text.** Main writes acceptance while writing a spec, tickets or a plan, when the delegation skill is not necessarily loaded, so the rendered guidance carries the whole rule rather than a pointer to a delegation reference. The rule is written once, in the template the tool renders, as ADR 0017 requires; the setup document and READMEs describe it without restating it as a second rule.
- **The rule.** With `on`, the rendered guidance says, in substance (the final wording is pinned by tests):
  - Related-test acceptance is on (in project scope: in this project; this overrides broader Feather guidance).
  - When main writes a Claim's acceptance in a spec, ticket or plan, it names the test modules related to the change instead of the full test suite: those that test or read the files the Claim changes, found by searching the tests for those files' paths and directory names.
  - It names the full suite instead when the Claim changes shared test support or build configuration, when its related tests cannot be determined, and for a release.
  - The named tests are a minimum: running more for a file the list does not cover does not change the acceptance.
  - A Plan's overall acceptance keeps the full suite, which the final check runs, and so does the only Claim of a Plan without overall acceptance.
  - Acceptance the user wrote, existing specs and tickets, and a fix Claim's acceptance keep their wording.
- **Values and resolution.** `on`, `off` and `default`, as for the Review mode: a project can save `off` to override a user `on`, mirroring the project off line for automatic review; user-scope `off` equals the default and saves nothing. The setting in effect is the user's session choice, then the project guidance, then the user guidance, then off. A session choice comes only from the user's own words in this conversation and is not written into a handoff.
- **Rendering.** The rule is rendered only for a scope with a saved setting, after the automatic review paragraph and the Stop threshold sentence, in both Review modes, so guidance without one stays byte-identical to 0.33.0.
- **State schema.** The delegation record's fixed key set gains one optional key, present only while a setting is saved. Older tools reject a record that carries it; this is accepted and documented, following the precedent of the Stop threshold in 0.20.0.
- **Configuration interface.** The `review` command gains `--related-tests`; it combines with `--review-mode` and `--stop-threshold` in one plan. No other command accepts it.
- **Command.** A new user-invoked skill mirrors the Stop threshold command's procedure for scopes, reminders and authorisation. Without a scope, or with `session`, it applies the choice to the conversation, writes nothing and reminds the user that a new or resumed session uses the saved choice; with `project` or `user` it previews, applies and reads back through the configuration tool, and never installs delegation or chooses user scope unasked. Its procedure lives in a reference under the setup skill that the delegation skill also points to, so a natural-language request follows it too.
- **Reporting and preservation.** `show` and `check` report a scope's saved setting, or off with an indication that none is saved; the `session` export is unchanged. Setup update, `model`, Review mode and Stop threshold changes and installing or removing the handoff or leases component keep a saved setting; removing delegation removes it; a failed write rolls back as for the other settings. Delegation guidance from a template older than the one this release can edit is not changed by the setting, as for the Stop threshold.
- **Documents.** The setup document describes the setting, its scopes, default, effect and limits, and that it changes how main writes acceptance, not how any review or the final check runs; both READMEs list the command next to `stop-threshold` and describe the setting in both languages; the packaged skill count and the setup skill's component and command lists include the command.
- **Release.** 0.34.0's validation entry, the setup document and both READMEs say that existing installations need only the plugin update and a fresh session, that a 0.33.x or older configuration tool rejects a scope with a saved setting so a downgrade first sets it back to `default` there, and that a session choice needs nothing.
- **Not affected.** Review state, including its Final check and its rerun of each Claim's primary acceptance; the plan review, code review, outcome verification and Adversarial review procedures; the Acceptance gate; fix Claims; role definitions and their tools; handoff and lease records and their runtimes; the issue tracker document's conventions.

## Testing Decisions

- One seam: the configuration tool's command line, run as the existing `--review-mode` and `--stop-threshold` tests run it, reading its JSON output. Tests check external behaviour: results, `show` and `check` output, the bytes of state and guidance files, and refusals that leave files unchanged.
- The rule, the command and its procedure, the setup document, the READMEs and the glossary are model instructions without an executable seam. Following the project's existing practice, tests pin each decision-carrying sentence as a whole sentence in the document and section that state it, README sentences paired in both languages.
- The tests go in a new test module for this feature that uses the shared test support, following the test module split. Tests that count or list the shipped skills are updated where they are.
- Prior art: the Stop threshold tests (saved value lifecycle, project override sentence, rendering in off mode, older-template refusal, boolean in state, rollback, preservation across update and `model`), the guidance byte-equality tests and the role-template compatibility data for older versions.

## Out of Scope

- Changing review state, the final check, the rerun of each Claim's primary acceptance, fix Claims or any review procedure.
- Rewriting the acceptance of existing specs and tickets, including this repository's.
- A mapping of files to tests, or any tool that computes related tests; main finds them by searching when it writes the acceptance.
- Plan review checking that a Claim's related tests are complete; plan review judges the acceptance as written, as today.
- A setting outside delegation, or a setup component of its own.
- Running the test suite faster, for example in parallel; that is separate work the user has not yet decided on.
- Setting it through `install`, the `session` export or `/cc-feather:model`.

## Further Notes

- **Limits.** A Claim that breaks a test its acceptance does not name passes its own reviews; the break is found only at the final check. In auto, a failure attributed with evidence to that Claim is then fixed by that Claim with its code review and outcome verification again, and an unattributed one becomes a fix Claim; in off, the failure reopens the Claims it affects. The final check runs before landing and release, so work that main never lands or releases does not get the full suite from this setting. Finding related tests by searching for paths and directory names can miss a test that reaches a file only through a path built at run time from parts that are not searched for.
- **Who it binds.** The rule binds how main writes acceptance in sessions where the guidance or a session choice turns it on; acceptance written elsewhere, or by the user, is taken as written.
- `CONTEXT.md` defines **Related-test acceptance**; that glossary entry was written with this spec and is committed with it.
- **Tickets.** The work is cut into tickets under `.scratch/related-test-acceptance/issues/`, which carry each Claim's acceptance. The saved setting and the command share the setup document, the READMEs and the new test module, so they are implemented one at a time, the release last. Their acceptance names the full suite: they change the configuration tool, which most test modules use, and the packaged skill list, so this spec's own rule would name the full suite for them as well.
- Automatic plan review is on, so the tickets get plan review before implementation.
