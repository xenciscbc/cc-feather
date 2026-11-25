# Declared test suites

Label: `needs-triage`

Vocabulary follows [CONTEXT.md](../../CONTEXT.md). The decisions below were settled by the user on 2026-11-25 in a grilling session recorded in the handoff `.feather/handoffs/test-tiers.md`, after two Codex consultations and a read-only survey of three projects that use cc-feather (cbc-go, nfsys2 and tt-sys). The spec adds an optional, project-owned file and changes how the final check, the release question and Related-test acceptance use it. A project without the file keeps every rule as in 0.45.0. It is a minor release, 0.46.0 unless another release lands first.

## Problem Statement

Every project that uses cc-feather runs the same kind of check before every landing: a Plan's overall acceptance, normally "the full suite", plus every Claim's primary acceptance. Related-test acceptance (0.34.0) narrowed what each Claim runs, and Final check scope (0.37.0) lets the user skip the overall acceptance at the final check. Neither can say that some of a project's tests have a different status from the rest. Related-test acceptance decides which tests are related, not which are needed, which are needed only before a release, or which cannot run without an environment.

The survey found that all three projects already have such suites, though none is declared:

- **cbc-go.** `build/test-all.sh` is the final check's full suite, about 5 min 20 s and 1.4 GiB at peak. `build/pg-test.sh` runs against real backends behind `CBC_TEST_REAL_BACKENDS` and fails when nothing ran. The `-tags integration` tests of the status package are not in `test-all.sh`, so they may not have run for a long time. Playwright e2e tests sit beside these, and the MinIO tests skip silently when MinIO is unreachable.
- **nfsys2.** The Go suite takes 209–415 s at up to 1.9 GiB; vitest runs 3,448 tests at 5.6–6.2 GiB with `--maxWorkers=3`; the Playwright e2e suite takes 12–15 min and has an `@smoke` subset. The project's CLAUDE.md requires at least the smoke run before merging and the affected e2e tests for some changes. In one Plan the user decided by hand, at the final check, on "backend full plus e2e smoke". A known flaky test made one final check fail, which then needed Accept and land.
- **tt-sys.** HR's PostgreSQL tests take 1,602 s cold and about 233 s warm; they run only with `HR_TEST_PG_DSN`, and a `TestPG_` test must not report SKIP. The web suite of 2,516 tests ran out of memory with the default number of workers; that incident led to 0.45.0's run configuration rules. One smoke test falls back to a hard-coded development Oracle DSN when its environment variable is missing.

As a result, every Plan's acceptance copies the same commands, flags, environment prerequisites and "must not skip" conditions again. A suite whose prerequisites are missing can skip and still look green. A suite that should run only before a release either runs before every landing, or the user drops it by hand at each final check. A release on a `full` pass from a final check that never ran the release-only suites cannot tell that they were left out.

## Solution

A project may keep a **Test suite catalogue** at `.feather/test-suites.md`, a file tracked in Git with the code it tests. It lists the project's **Declared test suites**. Each entry gives:

- the command, with its working directory and the flags or environment variables it needs;
- its prerequisites;
- the condition its output must show for it to pass;
- its gates: `landing`, `full`, `release`, any combination of them, or none.

It may also give a resource budget, its known conflicts with other runs, and how to run the part of it that a change affects.

cc-feather uses the catalogue in three places:

1. **Acceptance writing.** While Related-test acceptance is on, a Claim whose related tests belong to a Declared test suite names the affected part of that suite, with one sentence on why that part covers the change. A Plan's overall acceptance that main adds names the suites whose gates include `full`.
2. **The final check.** At Final check scope `full` and `related` alike, the final check runs every **Landing-required suite** (gate `landing`). One that does not pass there means that the final check has not run at the scope landing needs.
3. **Release.** Before a release or tag, main runs every **Release-required suite** (gate `release`) that has not already passed at that commit. It does not run them only when the user, asked in the conversation as part of the release question, chooses to leave them out.

The catalogue is data the project writes; cc-feather never creates, edits or proposes edits to it on its own. A project without it, and acceptance written without it, keep working exactly as in 0.45.0.

## User Stories

1. As a user whose projects have suites that need an environment, I want to declare each suite's command, prerequisites and pass condition once per project, so that Plans stop copying them.
2. As a user, I want the catalogue kept in cc-feather's own directory and not in CLAUDE.md or AGENTS.md, so that the agent instructions stay readable and the catalogue has one place.
3. As a user, I want the catalogue tracked in Git with the code, so that a branch that adds or changes a suite carries its declaration with it.
4. As a user, I want a project without a catalogue to behave as today, so that updating cc-feather changes nothing until I write one.
5. As a user, I want a suite whose prerequisites are missing to count as not run, never as passed, so that a silent skip cannot land as green.
6. As a user, I want a suite to pass only when its output shows its own pass condition, such as a marker line or no SKIP of a required test, so that "exit status 0 with nothing run" is not a pass.
7. As a user, I want a failure, a missing prerequisite and a run stopped from outside recorded as three different results, so that I know whether to fix code, provide an environment or change a budget.
8. As a user, I want suites that must run before every landing to run at Final check scope `related` too, so that choosing `related` cannot drop a check the project requires before merging.
9. As a user, I want the suites that make up the project's full run named in the Plan's overall acceptance, so that there is no question what "full" contains.
10. As a user, I want suites needed only before a release to stay out of every landing's final check, so that daily work does not wait for them.
11. As a user, I want main to ask me in the conversation, at release time, whether to run the release-only suites not yet run at that commit, so that I decide each time and the question survives a resumed session.
12. As a user, I want an unanswered release question to run those suites, so that silence never leaves a release unchecked.
13. As a user, I want a release that left a suite out to say so in its report, so that what the release did not check is visible.
14. As a user, I want a release to reuse a suite's pass already recorded at the same commit, so that the release does not run it twice.
15. As a user, I want a Claim whose related tests live in a large suite to run only the affected part of that suite, with a reason, so that the Claim's reviews do not run the whole e2e suite every time.
16. As a user, I want the verifier to keep rerunning the Claim's primary acceptance itself, so that independent verification is unchanged and only the size of each run shrinks.
17. As a user, I want a budget written in the catalogue to count as the project's resource guidance for that suite, so that I do not write it twice.
18. As a user, I want declared suites run one at a time, so that two suites that share a database or memory do not run together.
19. As a user, I want acceptance that already exists, and acceptance I wrote myself, kept as written, so that the catalogue never reinterprets an earlier "full suite".

## Decisions

These record the user's answers; all were confirmed on 2026-11-25.

- **D1 – Shape.** An opt-in, project-owned catalogue whose entries have four required attributes: command, prerequisites, pass condition and gates. A budget is optional. No registry, discovery mechanism, setup command, configuration key or scheduler. Rules change in three places only: acceptance writing, the final check and the release question.
- **D2 – Verifier.** The verifier still reruns a Claim's primary acceptance itself. The saving comes from a smaller primary acceptance, not from fewer runs of it.
- **D3 – Overall acceptance (revised by the user to option (a) below).** In a project with a catalogue, the overall acceptance main writes names the suites whose gates include `full`, not "the full suite". When the catalogue has no suite whose gates include `full`, main names the full suite as it would without a catalogue (user decision, 2026-11-25, after claim 03's code review). Existing acceptance that says "the full suite" keeps its meaning.
- **D4 – `related` and Landing-required suites.** Final check scope `related` does not waive a Landing-required suite.
- **D5 – Results.** A failure, a missing prerequisite (or a pass condition the output does not show) and a run stopped from outside are recorded apart, and none is retried automatically.
  - Failure takes precedence. A run whose assertions failed is a failure even when its output also lacks the pass condition. A failure in one suite is not hidden by another suite that did not run. A commit that has failed stays failed, as review state already says.
  - A required check that has not passed means that the final check has not run at the scope the operation needs, so landing needs Accept and land that names the suite and its result. Required checks are a Landing-required suite at either scope, a suite the overall acceptance names at `full`, and a suite a Claim's primary acceptance names.
  - A suite that no gate and no acceptance requires satisfies nothing when it is not run, and blocks nothing.
- **D6 – Release (revised by the user and confirmed).** Main asks in the conversation, with no question tool, as part of the release question for that commit, whether to run the Release-required suites that have not passed at that commit, and lists their prerequisites.
  - The user may choose to leave them out. Main asks, ends its turn and waits for the answer. Only when the user then instructs the release while the question is still unanswered or unclear does main apply the default, which is to run them.
  - The suites part and the existing `full`/`related` part are independent decisions in one message. Either may be needed without the other, and each is recorded separately.
  - Leaving a suite out waives only its `release` gate. It does not waive a `landing` gate or an acceptance that also requires the suite. It waives no failure, and the release report names every suite it left out.
  - The suites part is not asked when every Release-required suite has already passed at that commit.
- **D7 – Affected part of a suite.** While Related-test acceptance is on, a Claim whose related tests belong to a Declared test suite names that suite's command narrowed to the affected part, with one sentence on why it covers the change. When the part cannot be determined, the Claim names the whole suite. A Claim does not add unrelated Landing-required suites; the final check runs them.
- **D8 – Location (revised by the user and confirmed).** `.feather/test-suites.md` in the Working checkout, tracked in Git.
  - main reads it from the checkout at the commit it works on, not from the main worktree as with the Handoff store.
  - Writing it is a change to the checkout. Where Checkout leases are kept, it needs a lease like any other change. The exemption for cc-feather's own records (leases, handoff records, Dispatch records) does not cover it.
  - All three surveyed projects ignore only `.feather/handoffs/` and `.feather/dispatch/` (and `.feather/leases/` ignores itself), so the file is trackable there. This repository ignores all of `.feather/`.
  - Main uses the catalogue only when Git tracks it at the commit it works on. If the file exists but is untracked or ignored, main reports that, does not use it, and points the user to the setup document. The setup document shows how to track it under a broad ignore, `/.feather/*` together with `!/.feather/test-suites.md`.
- **D9 – Names.** Test suite catalogue, Declared test suite, Landing-required suite, Release-required suite. The names avoid "tier", "heavy", "light" and "quick", because the distinctions the projects need are prerequisites and gates, not weight.

### D3 against D4 (the user chose (a))

D3 as asked said the overall acceptance names the Landing-required suites. With D4, a Landing-required suite already runs at both scopes. An overall acceptance made of exactly those suites therefore makes `related` and `full` run the same checks. Review state already handles a plan whose scopes run the same checks: no scope is asked. So this is not a contradiction, but it decides whether the catalogue can express nfsys2's case: the backend full suite and vitest at `full`, and e2e smoke at both scopes. Two options:

- **(a) Three gates. Chosen.**
  - `landing`: runs at every final check, whatever the scope.
  - `full`: the suite is part of the project's full run, which the overall acceptance names and the final check runs at scope `full`.
  - `release`: runs before a release or tag.

  A suite may have several gates, and a suite with both `landing` and `full` runs once per final check. This revises D3: the overall acceptance names the suites with gate `full`, not the Landing-required ones.
- **(b) D3 as answered.** Only the `landing` and `release` gates exist, and the overall acceptance names the Landing-required suites. A project that wants a broader run at `full` keeps it out of the catalogue and writes it in its acceptance as today. Its scopes then often run the same checks.

The user chose (a); the rest of this spec is written for it.

## Implementation Decisions

- **One owner for the catalogue rules.** A new delegation reference, `skills/delegation/references/test-suites.md`, owns the file's location, its entry format, what counts as a pass, the three results, the gates and when main reads the file. Review state, the resource-risk runs reference, the Related-test acceptance template and the setup document point to it and do not restate it.
- **Entry format.** The file is markdown with one `## <suite name>` section for each suite and labelled lines:
  - `Command:` with its working directory, flags and environment variables;
  - `Prerequisites:`;
  - `Passes when:`, stated as positive evidence main can see in the run's output that the required selection ran, such as a marker line or a count above zero for a named group. Any allowed-skip rule may be added to that evidence, such as no SKIP for a named pattern, but never replaces it. A narrowed run used as a Claim's acceptance states evidence for its own selection.
  - `Gates:`, with any of `landing`, `full` and `release`, or `none`;
  - optional `Budget:`, `Conflicts:` and `Affected part:` lines.

  Main reads it as text and no tool parses it. If main cannot read an entry unambiguously, it reports the entry to the user. Until the entry is corrected or the user decides Accept and land naming it, every final check and release whose requirements the entry could affect counts as not run at the scope it needs. Main never guesses a gate and never treats an unclear entry as absent.
- **When main reads it, and which version counts.** Main reads the catalogue at the commit it works on:
  - before writing acceptance while Related-test acceptance is on;
  - before every final check;
  - before the release question.

  Two things are resolved at different times:
  - **`full` membership** is resolved when main writes the overall acceptance. The acceptance names the suites, with their commands and pass conditions, in its own text. A later change to which suites have gate `full` does not change an overall acceptance already written; changing it is a change to the acceptance, made as acceptance changes are today.
  - **`landing` and `release` membership** is resolved from the catalogue at the commit to be landed or tagged.

  A Claim's acceptance that uses a suite carries the entry's command, prerequisites, pass condition and budget in its own text. The Claim's reading set therefore holds them, and the Reading set rule does not change.
- **Changes to the catalogue during a Plan.** A Claim that changes the catalogue changes a tracked file, which its code review sees in the diff like any other. If the catalogue at the commit to be landed differs from the one at the Plan's base revision, the decision at the end of the Plan lists the gate changes: suites added, removed or with gates added or dropped. The user then sees a weakened gate before landing. This needs no new protection, because the repository is trusted.
- **Final check (review state).**
  - With a catalogue, the final check at both scopes runs every Landing-required suite at the commit to be landed or tagged, in addition to what it runs today. At `full`, the existing command-by-command coverage also applies to a Claim command that a suite's run covers.
  - Any failure in a required check makes the run failed, whatever else in the run did not run, and it is fixed as any final check failure is.
  - Some required checks may not pass without any failing: prerequisites missing, the pass condition not shown, or a run stopped from outside. These leave the final check not run at the needed scope. Main does not add a fix Claim for them. They do not count toward the Stop threshold's consecutive failures. Main reports them and waits for the user, who then provides the prerequisite so that main runs them again, or decides Accept and land naming them. This holds for every required check named in D5, at `full` for the suites the overall acceptance names too.
  - Declared test suites run one at a time.
  - In off, the final check runs the Landing-required suites as part of its overall acceptance checks under off's rules. Off still reuses no pass across sessions, and Related-test acceptance off still leaves acceptance writing as it is. These are two separate settings, and neither switches the catalogue on or off.
- **Recorded final check runs.** Each recorded run also has one line for every Declared test suite it ran. The line gives:
  - the command as run;
  - whether it ran the whole suite or a narrowed part, and which part;
  - the conditions that decide what runs and how;
  - the evidence of its pass condition;
  - its result: passed, failed, not run with the reason, or stopped.

  A release-only run of suites at a commit is recorded as its own entry at that commit, in the same form. A suite's recorded pass covers that suite at that commit only under the existing conditions for a recorded pass. A narrowed run covers only its part, never the whole suite. A suite that passed inside a run that was otherwise incomplete still covers that suite, but it never makes a failed commit passed.
- **Release question (review state).** At the commit to be released or tagged, main finds the Release-required suites that have no pass at that commit, from its own runs in this session or from a recorded pass that meets the existing conditions.
  - If there are any, the release question for that commit also asks whether to run them, listing each suite and its prerequisites. This happens even when a valid `full` pass would otherwise let main skip the question. The existing `full`/`related` part is asked only when today's rule asks it. The two parts are recorded separately in the release question's entry.
  - Main asks in the message that ends its turn, as Asking in the conversation states, and waits. Only the user's answer, in the conversation, chooses to leave a suite out. A pending, unanswered or unclear question runs every listed suite.
  - Leaving a suite out removes only its `release` gate at that commit. A suite that is also Landing-required, or that an acceptance names, still has to pass.
  - The suites the answer keeps run at that commit before the release or tag. A failure there keeps the commit failed; a missing prerequisite or stopped run blocks the release until the user decides, as above.
  - The release report names each Release-required suite it left out. In off, main asks the same question in the conversation before a release or tag, and nothing is recorded.
- **Related-test acceptance template.** One sentence is added. When the Working checkout has a Test suite catalogue at `.feather/test-suites.md` tracked in Git, main reads the delegation skill's test-suites reference before writing acceptance and follows it. The sentence names the path so that main can recognise the catalogue without the delegation skill loaded. The template stays the rule's single rendered text.
- **What the reference states for each existing full-suite case.** These apply only to acceptance main writes while Related-test acceptance is on, in a project with a catalogue. In each case where the template names "the full suite", that means the suites with gate `full`, named with their commands and pass conditions:
  - a Claim that changes shared test support or build configuration;
  - a Claim whose related tests cannot be determined;
  - the release Claim, unless the overall acceptance names those suites;
  - the only Claim of a Plan without overall acceptance;
  - the overall acceptance main adds.

  When the catalogue has no suite whose gates include `full`, each of these cases names the full suite as it would without a catalogue. A Claim whose related tests are in a Declared test suite names that suite narrowed to the affected part, or the whole suite, as D7 states. Release-required suites are never put into a Claim's acceptance only because of the release. They run through the release question, so the user can still leave them out.
- **Upgrade.** A scope that saved Related-test acceptance `on` renders the new sentence only after setup update. The configuration tool is not changed. It already handles guidance rendered by an older template, and 0.45.0's guidance behaves as follows:
  - `check` reports the warning that the delegation guidance is from an older template and to run setup update;
  - setup update replaces the managed block with the new rendering;
  - `review` that changes a saved setting refuses and asks for setup update first, as the setup document already states.

  The release notes in both READMEs and the setup document say this, together with how to downgrade. A scope without a saved setting is byte-identical to 0.45.0.
- **Budget.** In the resource-risk runs reference's budget order, a `Budget:` line of a Declared test suite counts as the project's resource guidance for that suite.
  - It never overrides the user's statement in the session, the Plan's execution conditions or an Execution method already approved.
  - When other project guidance states a different budget for the same suite, main asks the user.
  - A Claim whose acceptance uses the suite carries the budget in its acceptance text, so a role that runs it receives the budget in its brief through the existing execution conditions.
  - cc-feather still states no numbers and never raises a budget on its own.
- **Documents.** The setup document gains a short section describing the catalogue, with one example entry, and points to the reference. Both READMEs mention it in one paired sentence. The glossary entries were written with this spec.
- **Not affected.**
  - Plan review, code review, outcome verification and Adversarial review procedures, and role definitions.
  - The Acceptance gate, Accept and land's content, fix Claims and the Stop threshold's value.
  - Handoff and lease records and their tools. The configuration tool and its state.
  - test-speedup, which still only reports.
  - A project without a catalogue.

## Testing Decisions

- The rules are model instructions without an executable seam. Following the project's practice, tests pin each decision-carrying sentence as a whole sentence in the document and section that state it, and README sentences in both languages.
- If the Related-test acceptance template changes, the configuration tool's rendering tests and the byte-equality tests for guidance with a saved `on` are updated, along with the template compatibility data for older versions, as earlier template changes did.
- The tests go in a new test module for this feature that uses the shared test support, following the test module split.

## Out of Scope

- Any tool that parses, validates or generates the catalogue. A setup command or a configuration key for it.
- Running suites in parallel, a scheduler, or retries of a flaky suite.
- main or the verifier skipping a rerun of a Claim's primary acceptance because another role already ran it.
- Rewriting existing specs, tickets or guidance in this or another project. Writing a catalogue for this repository or for cbc-go, nfsys2 or tt-sys.
- Plan review checking a catalogue or a Claim's choice of affected part.
- Changing what acceptance that says "the full suite" runs.
- codex-feather. The file format is plain markdown, so codex-feather can adopt it later without conversion.

## Further Notes

- **Limits.** The pass condition is shown by output the repository's own code writes, so code can still fake it, as review state already says of any check. A suite left out at release is checked only by later runs. A suite with no gate is run only when some acceptance names it, so a suite nobody names can go unrun indefinitely, as cbc-go's integration-tag tests do today. Declaring it with a gate is how a project prevents that.
- **Side findings outside this repository, not changed.** cbc-go's `-tags integration` tests are not in `build/test-all.sh`; cbc-go's MinIO tests skip silently when MinIO is unreachable; a tt-sys smoke test falls back to a hard-coded development Oracle DSN. These are the user's to decide on in those projects.
- **Tickets.** The spec is cut into tickets under `.scratch/declared-test-suites/issues/` with to-tickets, quizzing the breakdown first. Automatic plan review is on, so the tickets get plan review before implementation.

## Overall acceptance

This is the Plan's overall acceptance. The final check runs it once for each commit to be landed or tagged, not once for each Claim. It is not part of any Claim's acceptance, and each ticket cites it.

- The full `unittest discover` suite passes at the commit to be landed or tagged.
