# A command to create and maintain the Test suite catalogue

Label: `ready-for-agent`

Vocabulary follows [CONTEXT.md](../../CONTEXT.md), which defines Test suite catalogue, Declared test suite, Landing-required suite, Release-required suite, Uncatalogued test, Related-test acceptance, Plan and Claim; the Uncatalogued test entry was written with this spec. The decisions below were settled by the user on 2026-11-27 in a design interview, starting from the question of how a project would set up and keep its catalogue current, and reviewed by Codex (gpt-6-astra, high effort), whose adopted points are folded in. This spec adds a skill, changes the delegation skill's test-suites reference, the `test-design` skill and the installed delegation guidance, so existing installations need a setup update; it is release 0.51.0.

## Problem Statement

[The declared test suites spec](declared-test-suites.md) gave projects a Test suite catalogue but no help writing it: its Out of Scope excludes any tool that generates the catalogue, and it states that cc-feather never creates, edits or proposes edits to it on its own. Writing an entry well is not obvious. A pass condition that relies on the exit code, a command that misses a build tag, or a prerequisite left out lets a gated suite pass without running what it should. A project like cbc-go shows each case: `cbc/status/integration_test.go` carries `//go:build integration`, so a plain `go test ./...` never selects it, and `TestS3E2E_MinIO` skips when MinIO is unreachable, so a suite that selects it can pass with it skipped.

The catalogue also goes stale as work adds tests. A new test placed where no suite's command selects it, or one that needs a prerequisite no entry names, is never required by any gate, and nothing in the current rules notices. Acceptance with a catalogue is governed only while Related-test acceptance is on, which is off by default, so most projects get no check at all. And `test-design`, which proposes new tests, says nothing about which suite would run them.

## Solution

A user-invoked command, `/cc-feather:test-suites`, drafts a catalogue when the project has none and checks it when it has one. It proposes, the user confirms suite by suite and decides every gate, and only then does it write the file and any ignore-rule change; it never commits. Its check reports Uncatalogued tests, tests a suite selects but never activates, stale commands and prerequisites, weak pass conditions and invalid entries, and says what it could not establish.

Acceptance main writes in a project with a tracked catalogue then requires positive evidence that new tests ran and passed inside their suite, and main reports new tests no suite selects, pointing to the command. A sentence in the installed delegation guidance makes main read the catalogue rules before writing any acceptance in such a project, whether or not Related-test acceptance is on. `test-design` marks the suite expected to select each Recommended test, when the project has a catalogue. An ADR records that this overturns the earlier exclusion.

## User Stories

1. As a user, I want a command that drafts my project's catalogue from its test configuration, so that I do not write entries from scratch.
2. As a user, I want the command to run only when I invoke it, so that nothing changes the catalogue behind my back.
3. As a user, I want to confirm each suite before anything is written, and to decide every gate myself, so that the catalogue states my project's choices.
4. As a user, I want a gate recommended with its reason, so that I decide knowingly.
5. As a user, I want to be warned when declaring a `full` suite narrows what an overall acceptance runs, and shown the tests no `full` suite covers, so that a partial catalogue does not quietly reduce coverage.
6. As a user, I want existing catalogue content, tracked or not, never overwritten without my confirmation, and the file checked again just before writing, so that my own edits survive.
7. As a user, I want the ignore rules changed only as far as needed to track the catalogue, so that my other ignore rules stay.
8. As a user, I want the command to read files only, and to run a command that lists what a suite selects only after I agree, so that repository code does not run without my consent.
9. As a user, I want the check to report tests no suite selects, tests a suite selects but whose activation it never provides, commands that name paths, packages or tags that no longer exist, prerequisites that are missing or no longer used, pass conditions that rely only on the exit code, and invalid entries, so that a gated suite does not pass without running what it should.
10. As a user, I want anything the command could not establish reported as such, never as a clean result, so that I know where to look myself.
11. As a user, I want an exact test count in a pass condition reported as a maintenance note rather than an error, so that a strict condition is not weakened.
12. As a user, I want `Affected part:` drafted only where narrowing is mechanical, so that a wrong narrowing does not skip tests.
13. As a user, I want a Claim that adds tests to a suite to show, in its acceptance's output, that those tests ran and passed, so that a new test is not silently skipped or unselected.
14. As a user, I want main to tell me when new tests fall outside every suite or need a new prerequisite, so that I can update the catalogue.
15. As a user, I want these acceptance rules to apply whether or not Related-test acceptance is on, so that the default setting is covered.
16. As a user, I want `test-design` to say which suite is expected to run each Recommended test, when my project has a catalogue, so that I see the gap before the test is written.
17. As a user, I want nothing to change for a project without a catalogue, so that updating cc-feather costs nothing there.
18. As a maintainer, I want the change of the earlier decision recorded in an ADR, so that the reversal is not mistaken for an oversight.

## Implementation Decisions

### The command

- **Name and invocation.** A new skill `test-suites` with `disable-model-invocation: true`, listed in the plugin manifest after `test-design`. Invocation arguments are data, never shell code. It changes no code, test or configuration other than the catalogue and the ignore rules it confirms, and commits nothing.
- **One command.** When `git cat-file -e HEAD:.feather/test-suites.md` fails and no file exists at that path, the command drafts a catalogue; otherwise it checks the existing content. A file that exists but is untracked, ignored or has uncommitted changes counts as existing content: the command reports its Git state and checks it, and a redraft happens only when the user asks for one in words. The command reports that a catalogue main has not committed does not take effect, as the test-suites reference's Tracked at the commit states.
- **Proposing and writing.** The command reports the whole draft or every proposed change first; the user confirms suite by suite. Before writing, main reads the catalogue and the ignore rules again; when either changed since the proposal, main proposes again and writes nothing until the user confirms the new proposal. Main then takes a Checkout lease and writes only the confirmed entries and, when Git would not track the file, the narrowest change to the actual ignore rules that lets it, such as replacing a `.feather/` rule with `/.feather/*` and `!/.feather/test-suites.md`, keeping every other rule. A suite the user did not confirm is not written; in a check, an existing entry without an answer stays as it is.
- **Gates.** For each suite the command recommends gates with a reason, such as its run time, its prerequisites and what a missing run would cost. A suite may have several gates; `none` is an explicit choice and never the default for an unanswered suite. The command never writes a gate the user did not choose, as the test-suites reference's An unclear entry forbids guessing one.
- **Coverage warning.** When the confirmed catalogue would contain a suite whose gates include `full`, the command states that an overall acceptance main writes from then on names only the `full` suites instead of the full run, and lists the test files or groups no `full` suite selects as far as it can establish them.
- **Static first.** The command reads test configuration, scripts, directories, build tags, markers and test-code conventions, and runs nothing. A command that lists what a suite selects, such as `pytest --collect-only`, `go test -list .` or `vitest list`, executes repository code: the command offers it, naming the exact command and conditions, and runs it only after the user agrees, within review state's Execution rules and the resource-risk runs reference's floor. A listing is evidence of selection only, never that a test ran or passed.
- **What the check reports.** Each finding with its location and evidence:
  - an Uncatalogued test: a test file, package, build tag or marker no suite's command selects;
  - a test a suite selects but whose activation the suite never provides, such as an environment switch, a service or a build tag its command and prerequisites leave out, so that it skips while the suite passes;
  - a suite command naming a path, package, tag or script that no longer exists;
  - a prerequisite tests read that `Prerequisites:` omits, or one listed that nothing uses;
  - a `Passes when:` that relies only on the exit code; an exact test count is reported as a maintenance note, not an error;
  - an invalid entry: a missing required line, an unknown or conflicting gate, a duplicate suite name, or conditions that contradict each other.
  Whatever static reading cannot settle, such as a wrapper script, dynamic registration, platform or build constraints, nested modules or generated tests, is reported as not established, with what would settle it, and never as clean. The check does not judge test quality or speed, which belong to `test-design` and `test-speedup`.
- **Affected part.** The command drafts `Affected part:` only where narrowing is mechanical, by package, directory or file list. An entry without it still allows narrowing where the affected part can be determined, as the test-suites reference's The affected part states.
- **Who analyses.** As `test-speedup`: when delegation is installed and the repository is not small, main dispatches the read-only analyst in one or more Assignments by test area, each brief carrying the shared commands, configuration and current catalogue, and integrates the results; otherwise main does it.
- **No record.** The command keeps no record of its own. Each report states the scope it inspected and what it could not establish. A confirmation not given in this conversation since the proposal is asked again.
- **Lookups.** Defaults and known behaviour of the test frameworks in scope are looked up only for discovery, selection, activation, skips, output format and result caching, in the order of `test-speedup`'s Lookups paragraph: the installed version's own files, read and never run, then the official documentation and changelog, then the official issue tracker. A query sent outside carries only the framework's name, its version and the setting's name.
- **Acceptance already written.** The report states that changing the catalogue does not change acceptance already written: a suite's command and `full` membership copied into acceptance stay as written, while `landing` and `release` membership are resolved at the commit to be landed or tagged.

### The catalogue rules

- **Reading the reference before acceptance.** The test-suites reference's When it applies changes so that its new-test rules apply to acceptance main writes in a project whose Working checkout tracks the catalogue, whether or not Related-test acceptance is on, while the affected-part and full-suite rules stay tied to Related-test acceptance being on. Its Occasions add writing any acceptance in such a project. The installed delegation guidance, `templates/CLAUDE.md`, gains one sentence after its paragraph on reading cc-feather:delegation: when main writes a Claim's acceptance and the Working checkout tracks `.feather/test-suites.md`, it reads the delegation skill's test-suites reference first and follows it. The Related-test acceptance template keeps its own pointer.
- **New tests in a suite.** A Claim that adds tests a Declared test suite is expected to select gets, in its primary acceptance, that suite's command, narrowed to the affected part where the narrowing rules allow, with a condition that its output shows the new tests executed and passed, such as per-test result lines or a report file, and which skips, if any, are allowed. A test name in a listing, a skip line or cached output is not that evidence.
- **Evidence the command cannot show.** When the suite's command cannot show that evidence without changing it, such as a quiet runner without per-test output, main reports the gap and proposes either a confirmed change to the catalogue entry or a separately stated acceptance check that does show it; main never adds flags to a catalogue command on its own and never accepts the exit code alone.
- **Gaps reported.** When the tests a Claim adds are expected to be selected by no suite, or need a prerequisite no entry names, main lists them in its report, pointing to `/cc-feather:test-suites`; the user decides whether to change the catalogue.
- **Wording kept.** Acceptance the user wrote, existing specs and tickets, and a fix Claim's acceptance keep their wording; the new-test rules apply only to acceptance main writes from now on.
- **Residual risk.** Unplanned edits and acceptance the user wrote get no automatic check. Running `/cc-feather:test-suites` shows whether the catalogue and the tests agree; it does not show that any test ran, and no report says so.

### test-design

- **Expected suite.** Only when the target's Working checkout tracks a catalogue, each Recommended test's statement names the Declared test suite or suites expected to select it, or that this cannot be established, reading the catalogue as the test-suites reference describes. A Recommended test expected to be an Uncatalogued test, or to need a prerequisite no entry names, is listed under Decisions for the user. Without a catalogue, `test-design` does not change and does not suggest creating one.

### Records, documents and release

- **Glossary.** CONTEXT.md gains Uncatalogued test, written with this spec. The Test suite catalogue entry gains that `/cc-feather:test-suites` drafts and checks it on the user's request. No other entry changes.
- **Decision record.** ADR 0025 records that a user-invoked command that writes only after the user's confirmation overturns the declared-test-suites spec's exclusion of a generating tool, that "never creates, edits or proposes edits on its own" becomes "never creates or edits on its own; it reports gaps and proposes edits when asked or when a Claim adds tests", that acceptance main writes in a project with a catalogue reads the catalogue rules whether or not Related-test acceptance is on, and how the command differs from an automatic editor, a parser or a configuration setting, none of which it is. The declared-test-suites spec as shipped does not change.
- **Documents.** Both READMEs list the command after `test-design`; both reference documents' Design and test checks section gains a Test suites subsection; `docs/setup.md`'s Test suite catalogue section points to the command and its count of packaged skills becomes twenty-three. Sentences are paired in English and Traditional Chinese.
- **Release.** 0.51.0. Installed delegation guidance changes, so existing installations need `/cc-feather:setup update` in each scope where delegation is installed; until then main does not read the catalogue rules before acceptance while Related-test acceptance is off, and nothing else changes. The validation entry records the determination with `git diff v0.50.0 HEAD -- templates skills/setup scripts`, the way back and the live pilot below.
- **Not affected.** The final check, Final check scope, Recorded final check runs and the release question; the catalogue's entry format, gates and results; `test-speedup`; plan review and every review procedure; the role definitions; the Related-test acceptance template; the declared-test-suites spec as shipped.

## Testing Decisions

- No executable seam beyond the documents: the skills and references are model instructions. Following the project's practice, tests pin each decision-carrying sentence as a whole sentence where it is stated, README and reference sentences paired in both languages.
- The skill's pins go in a new test class beside the `test-design` and `test-speedup` command tests; the catalogue-rule pins beside the existing declared-suites tests; the guidance sentence beside the existing template tests, with a check that the rendered delegation guidance carries it and a check of what `check` reports for an installation rendered from the older template.
- Pinned rule interactions: Related-test acceptance off and on; a catalogue with some `full` suites; overlapping suites; an unclear entry; skipped, listed or cached output not counting as evidence; a fix Claim's and user-written acceptance unchanged; a project without a catalogue unchanged, for the acceptance rules and for `test-design`.
- Packaging: the manifest lists the skill and `docs/setup.md` counts twenty-three skills.
- Prior art: `tests/test_feather_design_checks.py`, `tests/test_feather_declared_suites.py`, `tests/test_feather_related_tests.py` and the release tests.
- Live pilot, in the release ticket: a `git archive` export of cbc-go's tracked files at its HEAD into a new directory under `J:\gotmp\`, a new Git repository there with every exported file committed, headless Claude Code in the default permission mode with `--plugin-dir` naming a copy of the candidate, inside cc-feather's Runner, in three runs:
  1. invoke the command with no catalogue; expected to propose a draft with gate recommendations and stop without writing;
  2. resume the same session with `--resume` and a message confirming every proposed suite and gate; expected to take a lease, write the catalogue and the ignore change, and not commit;
  3. after main commits run 2's result in the copy and adds two fixtures, a test file with a build tag no suite selects and a test that a suite selects but that skips without a service its prerequisites omit, invoke the command again; expected to report both.
  For each run the entry records the transcript's tool calls, separating a write not attempted from a write the permission mode denied, the hashes of the copy's files before and after, token use where reported, and what the report showed; it states that the Runner limits resources and does not isolate the file system or the network, and that only the places checked were checked. The copy is removed afterwards.

## Out of Scope

- Running the command, or a check of the catalogue, automatically at the final check or at any other point.
- A record of the command's own, a parser or validator tool, a configuration key or a setup command for the catalogue.
- A glossary term for a test a suite selects but never activates.
- Changing the final check, the release question, the catalogue's entry format or gates, or `test-speedup`.
- Checking unplanned edits or acceptance the user wrote.
- Writing a catalogue for this repository or for cbc-go outside the pilot's copy.
- Rewriting the declared-test-suites spec or existing tickets.

## Further Notes

- **Tickets.** Three tickets under `.scratch/test-suites-skill/issues/`: 01 the command; 02 the catalogue rules, the guidance sentence, `test-design` and ADR 0025, blocked by 01 because its reports point to the command; 03 the pilot and the 0.51.0 release, blocked by 01 and 02.
- **Review level.** The user chose `standard` for the Plan.
- **Limits.** Pins show the text, not that a model follows it; the pilot shows one model on one project. Codex's review left open the inventory boundary for nested modules, platform-specific and generated tests; the command reports such cases as not established rather than deciding them.

## Overall acceptance

This is the Plan's overall acceptance, which the final check runs once for each commit to be landed or tagged, not once for each Claim; it is not part of any Claim's acceptance, and each ticket cites it.

- The full `unittest discover` suite passes at the commit to be landed or tagged.
