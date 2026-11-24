# Run configurations in test-speedup and runs stopped from outside

Label: `ready-for-agent`

Vocabulary follows [CONTEXT.md](../../CONTEXT.md), which defines Plan, Claim, Assignment, Unbounded probe, Unbounded run configuration, Observed resource risk and Runner. The decisions below were settled by the user on 2026-11-24 in the conversation that drafted this spec. This spec changes the user-invoked `/cc-feather:test-speedup` skill, the delegation skill's resource-risk runs reference, the verifier, adversary, executor and security-executor role definitions and the documents describing them, so it is release 0.45.0, after 0.44.0, and existing installations need `/cc-feather:setup update`.

## Problem Statement

On 2026-11-24 a session in another project ran its full vitest suite (vitest 4.1, 139 spec files, 2516 tests) on a machine with 24 logical cores and 47.6 GB of memory, 82% of it already in use. Claude Code stopped the command at once for lack of system memory. No test had failed. The project's vitest configuration set neither `pool` nor `maxWorkers`, so vitest 4's defaults applied: `forks`, with about as many workers as cores, each a separate Node process loading the Vite transform pipeline, happy-dom, the component libraries and the setup files, a few hundred megabytes each.

`/cc-feather:test-speedup` (0.36.0, 0.44.0) already reads that configuration: its scope includes the test runner configuration, test scripts and their flags. But it reads it only for speed. Its resource-risk section judges each existing test by the Unbounded probe criteria, which concern one test's own work, so nothing in it asks how many workers the whole run starts, how much memory each one holds, or whether a framework's default lets the run grow with the machine. One of its speed-ups, tests that can run in parallel, even points the other way.

When a run like that is stopped from outside, cc-feather has no rule for reading the result. Main's floor and each role's floor judge a run the Runner contained; an ordinary run, such as the final check's full suite, an acceptance check or a test-speedup measurement, that the host or the operating system stops for lack of memory is not covered. Main or a role may then report it as a failure, or run it again and exhaust the machine a second time.

## Solution

`/cc-feather:test-speedup` also checks the settings and run parameters that do not belong to the tests' code, above all those concerning concurrency, isolation, memory and time, and reports each Unbounded run configuration it finds in a section of its own. It judges the value in effect, a framework's default included, looks up defaults and known problems in the installed version, the official documentation and the official issue tracker, in that order, and says "unknown" when it cannot establish one. A speed-up that raises concurrency states its worker count and memory effect, and is never "as many as cores". Measurement caps a flagged run with a command-line override, or runs it inside the Runner, and says that its timings are not comparable with the ordinary run. The command stays report-only, and cc-feather still states no numbers.

Separately, a test run that the host or the operating system stops for lack of memory or another resource is inconclusive evidence, for main's every run and for each role that runs code: it is reported as not completed, never as a failure, and is not run again without the user.

## User Stories

1. As a user, I want test-speedup to check my test runner configuration, test scripts and their flags for resource risk, not only for speed, so that a suite that would exhaust my machine is found before it runs.
2. As a user, I want the check to cover settings and run parameters that do not belong to the tests' code, so that problems no single test shows are found.
3. As a user, I want concurrency, isolation, memory and time to be what the check looks at, so that the report stays on what can exhaust a machine.
4. As a user, I want concurrency that follows the machine's core count flagged, so that a default like vitest 4's worker count is found even when my configuration never mentions it.
5. As a user, I want the check to judge the value in effect, a framework's default included, so that an unset option is not treated as safe.
6. As a user, I want a default or value the check cannot establish to count as unbounded, so that "unknown" is never read as "fine".
7. As a user, I want worker pool and isolation modes known to grow memory, such as vitest `vmThreads` or `vmForks`, flagged, so that a pool chosen for speed does not exhaust memory over a long run.
8. As a user, I want per-worker heap settings, such as a raised Node heap limit, considered, so that the per-worker part of the peak is not ignored.
9. As a user, I want multipliers of the run's work, such as retry counts or `go test -count`, considered, so that a run that repeats itself is not mistaken for a short one.
10. As a user, I want heavy instrumentation, such as `-race` or coverage, considered together with uncapped concurrency, so that a multiplied per-worker cost is seen.
11. As a user, I want a limit switched off or absent, such as a timeout of zero, a test script in watch mode or a framework with no default timeout, flagged, so that a run that never ends is found.
12. As a user, I want these kinds listed as examples, not as a closed list, so that a setting of the same nature that the list does not name is still found.
13. As a user, I want output volume left out, so that the check does not report what the tests' own code decides.
14. As a user, I want services outside the run, such as a container runtime or a database, left out, so that the report covers only what the test configuration controls.
15. As a user, I want each flagged setting weighed by when it occurs and its worst outcome, as the delegation skill weighs findings, so that a frequent but harmless flag, such as a framework without a default timeout, does not read like a crash waiting to happen.
16. As a user, I want the flags reported in a section of their own, with the setting's location, its kind, whether it affects memory or time, why it is unbounded and the direction of a fix, so that I can decide each one.
17. As a user, I want that section to be information that holds nothing back, so that it never stops other work.
18. As a user, I want cc-feather to state no cap of its own, so that the number comes from my project's or my own resource guidance, or from a measured per-worker peak, and not from a guess.
19. As a user, I want defaults and known problems looked up in the installed version first, then the official documentation and changelog, then the official issue tracker, so that the answer fits the version I actually run.
20. As a user, I want every looked-up conclusion to name its source and version, so that I can check it.
21. As a user, I want a fact the lookup cannot find reported as unknown, so that missing evidence is not reported as safety.
22. As a user, I want outside lookups to carry only the framework's name, its version and the setting's name, so that nothing about my project leaves the session.
23. As a user, I want analyst to do the lookups when delegation is installed and the check is not small, and main otherwise, so that the reading follows the command's existing split.
24. As a user, I want a speed-up that raises concurrency to state the worker count it leads to and its memory effect, so that a speed-up never trades a slow suite for an exhausted machine.
25. As a user, I want "as many workers as cores" never offered, so that the check does not recommend the very setting that caused the problem.
26. As a user, I want measurement of a flagged run to cap it with a command-line override, such as `--maxWorkers` or `-p`, without changing any file, so that measuring stays report-only and does not exhaust the machine.
27. As a user, I want the cap's number taken as the budget rules take one, and main to ask me when no source states it, so that measurement never invents a number.
28. As a user, I want the choice of running a flagged run inside the Runner instead, so that a hard limit covers it when an override is not enough.
29. As a user, I want measurement to say that timings taken at a different concurrency are not comparable with my ordinary run, so that I do not misread the gains.
30. As a user, I want a test run the host or the operating system stops for lack of memory or another resource reported as not completed, so that a machine limit is never read as a failing test.
31. As a user, I want such a run never repeated without my agreement, so that the machine is not exhausted twice.
32. As a user, I want this to hold for every run main makes, the final check, acceptance checks and measurement included, so that it does not depend on whether a test is new.
33. As a user, I want a final check stopped that way treated as a final check that did not complete, so that a plan does not land on it.
34. As a user, I want verifier, adversary, executor and security-executor to treat such a run the same way and report it with their own outcome words, so that a role never turns a stopped run into a REFUTED, a BROKEN or a finished task.
35. As a user, I want each role to name in its report every run the host stopped, with the reason, so that main can record it.
36. As a user, I want a run stopped that way during a Claim recorded as an Observed resource risk, so that later briefs and the end of the Plan carry it.
37. As a user, I want no memory check before every full run and no configuration review before every final check, so that no new gate slows ordinary work.
38. As a user, I want the reference documents to describe the new check, the new section and the stopped-run rule in English and Traditional Chinese, so that both readers learn the change.
39. As a user updating cc-feather, I want the update note to say that role definitions changed and that I need `/cc-feather:setup update` and a fresh session, so that installed roles get the new rule.
40. As a user going back, I want the note to say how to return to 0.44.0, so that I can undo the update.

## Implementation Decisions

- **Glossary.** CONTEXT.md gains Unbounded run configuration at the end of Resource-risk runs, after Runner: a setting of how a test run is executed, in its test runner configuration, its test scripts or its flags rather than in the tests' code, under which the whole run's peak memory or total time has no bound the configuration establishes, or one that does not fit the project's resource guidance; judged by the value in effect, a framework's default included, an unestablished value counting as none; examples that are not a closed list; output volume and services outside the run left out; information that holds nothing back. The entry is written with this spec. The Observed resource risk entry widens to cover a run the host or the operating system stopped for lack of a resource.
- **The check's principle.** test-speedup's static pass also checks the settings and run parameters within its scope that do not belong to the tests' code, above all those concerning concurrency, isolation, memory and time, for each Unbounded run configuration. Its scope is unchanged: CI pipeline configuration stays outside it.
- **Detection hints.** The hints name, as examples, concurrency that is uncapped or follows the core count (vitest `pool` and `maxWorkers`, `go test -p`, pytest-xdist `-n auto`), pool and isolation modes known to grow memory (vitest `vmThreads` and `vmForks`), per-worker heap settings, multipliers of work (retries, `go test -count`), heavy instrumentation on uncapped concurrency (`-race`, coverage) and limits switched off or absent (a zero timeout, a watch-mode script, a framework without a default timeout).
- **Lookups.** Defaults and known problems of the frameworks in scope, only for settings concerning concurrency, isolation, memory and time, are looked up in order: the installed version itself, such as its bundled documentation, type definitions or `go help testflag`; the official documentation and changelog; the official issue tracker. A query sent outside carries only the framework's name, its version and the setting's name. Each conclusion names its source and the version it applies to; what cannot be found is reported as unknown, which counts as no bound. The lookups follow the command's Who analyses split: analyst in its Assignments when delegation is installed and the check is not small, main otherwise.
- **Weighing.** Each flagged setting is weighed as the delegation skill's paragraph on weighing findings describes, as the resource-risk section already does.
- **Parallel speed-ups.** A speed-up that raises concurrency states the worker count it leads to and its memory effect, and a worker count that follows the machine's core count is never offered.
- **Report.** The report gains a fourth section, Run configurations with resource risk: each flagged setting with its location, its kind, whether it affects memory or time, why it is unbounded, its weighing and the direction of a fix. A cap's number is never stated by cc-feather; the direction says where it comes from, the project's or the user's resource guidance or a measured per-worker peak. The section is information and holds nothing back.
- **Measurement.** When a run in the offer's scope has a flagged setting, the offer states how it is bounded: by default a command-line override of that setting, such as `--maxWorkers=N` or `-p N`, which changes no file, with N taken as the resource-risk runs reference's budget order takes a budget and asked of the user when no source states it; or the run inside the Runner. The offer and the report say that timings taken at a different concurrency are not comparable with the ordinary run.
- **A run stopped from outside, main.** The resource-risk runs reference's Main's floor gains a bullet that applies to every test run main makes, the final check, acceptance checks, reruns, reproductions and test-speedup's measurement included, not only to a new or modified test or probe: a run the host, the operating system or another tool stops for lack of memory or another resource is inconclusive evidence judged from what stopped it, not from its exit code; main reports it as not completed, never as a failure, tells the user what stopped it and does not run it again without the user's agreement. A final check stopped that way did not complete and counts as a final check that was not run. During a Claim, main records it as an Observed resource risk.
- **A run stopped from outside, roles.** The verifier, adversary, executor and security-executor definitions' Resources paragraph gains the same rule in the shared body: a run the host or the operating system stops for lack of memory or another resource is inconclusive evidence, not a failure, and is not run again. The existing outcome sentence for a stopped run then covers it with each role's own words (INCONCLUSIVE; INCONCLUSIVE or a gap left open; partial or blocked), and the report sentence widens to every run a limit or the host stopped, with the reason. The paragraph stays identical across the four roles apart from the opening and the outcome words.
- **Not added.** No memory check before a full run, no configuration review before a final check, no ADR.
- **Documents.** Both reference documents' Test speed-ups section gains paired English and Traditional Chinese sentences for the run-configuration check, its lookups, the parallel speed-up condition, the fourth section and the bounded measurement; their resource-limits section's floor item gains the stopped-run rule. The README listings stay as they are.
- **Release.** 0.45.0, after 0.44.0. The four role definitions change, so existing installations need the plugin update, then `/cc-feather:setup update` in every scope where delegation is installed, then a fresh session; until then `check` reports those roles from an older template. To go back to 0.44.0, reinstall the 0.44.0 plugin and run `/cc-feather:setup update` in every scope where delegation is installed, then start a fresh session; no remove is needed, since 0.45.0 changes no configuration tool or state. Each README gets the 0.45.0 note at the start of its Updates section, the 0.44.0 note moving after it as earlier notes moved; `docs/setup-validation.md` gets the 0.45.0 entry; the release tests that pin 0.44.0 as the latest release move to 0.45.0.
- **Not affected.** The Unbounded probe term and its criteria, the Runner and its contract, Resource-risk claims and Execution methods, plan review, the analyst definition, the other role definitions, the policy templates, setup, handoff, leases, overdesign-check and every review procedure apart from the floor bullet.

## Testing Decisions

- No executable seam: the skill, the reference and the role definitions are model instructions. Following the project's practice, tests pin each decision-carrying sentence as a whole sentence in the document that states it, reference sentences paired in both languages. The tests show the text, not that a model always follows it.
- **test-speedup.** In the design-checks tests, beside the existing test-speedup command pins: the principle, the detection hints, the lookup order and its privacy and unknown rules, the parallel speed-up condition, the fourth report section, the bounded measurement and its comparability sentence, and the reference pairs. Unchanged pins stay; the report's section count moves from three to four.
- **Floor.** In the resource-floor tests: the shared body of the four roles' Resources paragraph gains the stopped-run sentence and the widened report sentence, and the existing checks that the paragraph appears once in each of the four roles, beside the same paragraph, identical apart from the opening and the outcome words, and absent from the other roles keep passing on the new text; the Main's floor bullet and its scope sentence get a reference test; the glossary tests pin the Unbounded run configuration entry and the widened Observed resource risk entry, each defined once.
- **Setup.** The existing setup tests that show a changed role template is stale until setup update keep passing; no new setup test.
- **Release.** The release tests pin the 0.45.0 version, the 0.45.0 update notes and the validation entry, following their conventions for the previous release.
- **Single owner.** The Unbounded probe criteria, the Runner's invocation, the budget order and the weighing sentences stay stated once, in their owning documents; test-speedup points to them.
- Prior art: `TestSpeedupCommandTests` (0.36.0, 0.44.0), the 0.32.0 resource-floor tests (`RoleFloorTests`, `ReferenceTests`, `GlossaryTests`) and the release tests' version and validation checks.

## Out of Scope

- Changing any project's test configuration; picked items go through the normal Plan flow.
- Output volume and services outside the run, such as a container runtime or a database.
- A memory check before every full run, and a configuration review before every final check or acceptance run.
- Numbers of cc-feather's own for any cap or budget.
- CI pipeline configuration.
- Changes to the Unbounded probe criteria, the Runner, Resource-risk claims, Execution methods or plan review.
- Memory leaks in the tests' own code, which the existing per-test checks cover.

## Further Notes

- **Origin.** The problem came from another session's report, relayed by the user's request; its facts are recorded here as that session observed them and were not reproduced.
- **Frequency.** The check is information inside a command only the user runs, and the stopped-run rule changes how an existing outcome is read, so neither adds a gate to ordinary work. A framework without a default timeout will be flagged in many projects; the weighing keeps that from reading like a defect.
- **Tickets.** Two tickets under `.scratch/test-run-configuration/issues/`: 01, the test-speedup change, its reference sentences and the glossary entry; 02, the stopped-run rule for main and the four roles, its reference sentence, the Observed resource risk entry and the 0.45.0 release, blocked by 01. Each ticket's acceptance names its related tests, as Related-test acceptance states.
- Automatic plan review is on, so the tickets get plan review before implementation; ticket 02 changes role definitions and review rules.

## Overall acceptance

This is the Plan's overall acceptance, which the final check runs once for each commit to be landed or tagged, not once for each Claim; it is not part of any Claim's acceptance, and each ticket cites it.

- The full `unittest discover` suite passes at the commit to be landed or tagged.
