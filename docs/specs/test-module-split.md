# Test module split

Label: `ready-for-agent`

Vocabulary follows [CONTEXT.md](../../CONTEXT.md). The decisions below were settled by the user on 2026-10-10 in two grilling rounds (Q1–Q9) and a confirmation of the test seams. This is the first stage of the per-Claim review schedule work recorded in the handoff `.feather/handoffs/review-schedule-per-claim.md`; the second stage, the mixed review schedule, changes review rules and gets its own spec and ADR. This spec changes no review rule, no shipped file and no assertion.

No Claim is Security-critical: the work moves test code between modules of the repository's own test suite. It changes no shipped skill, template, role, script or document a user follows, no security guarantee and no place sensitive data goes; the tests keep running exactly the commands they run today.

## Problem Statement

Every Claim of the last releases edited one test module of about 8,780 lines and 365 tests in 24 classes. Under review state, a later Claim's commit to a file an earlier Claim changed reopens the earlier Claim's passes, so Claims could not be reviewed as each was finished: in 0.20.0 code review waited until C1–C4 were all done, a defect in C3 was found only after C4, and the C3 fix sent C1, C2 and C4 back to review. The single module is also slow to navigate and makes it unclear where a new test belongs.

## Solution

The module is split by feature into five test modules plus one support module that holds no tests. Whole classes move; no class is split, no test is renamed and no assertion changes, so the suite runs the same tests with the same results. A Claim that changes the configuration tool, a review procedure, a command or a release then edits a different test module from the others. Each module states its scope at the top, so a new test has an obvious home.

The split is landed on main without a version change or tag; the next release carries it. Its validation, with a table of where each class moved, is recorded in the validation document under its own heading.

## Claims

| Claim | Outcome | Acceptance | Depends on |
| --- | --- | --- | --- |
| C1 Shared test support | Every helper, constant and the loaded configuration tool that a class takes from another class or from the module level, where the two would land in different modules, comes from a support module that holds no tests; only those references change | [C1](#c1-acceptance) | — |
| C2 Feature test modules | The classes move unchanged into five feature modules, each stating its scope; the validation document's reproduce commands run the whole suite and a new entry records the split's validation and move table | [C2](#c2-acceptance) | C1 |

**Schedule.** C2 rewrites the file C1 changes, so C2's commit would reopen C1's passes under review state. The Claims are therefore implemented and committed one at a time, C1 then C2, each commit labelled as unaccepted as review state's Commits before the passes describes. C1's base revision is the commit that adds this spec; the full suite is run there in both discovery forms and its results kept as the baseline before C1 starts. C2's base revision is C1's last commit. Once C2 is committed, that commit is the candidate, and each Claim gets code review and then outcome verification in the order C1, C2 at the candidate: code review judges the Claim's own range, later commits being context only, and verification checks the Claim's full acceptance. A fix is a new commit and a new candidate, and each Claim whose passes it reopens gets its reopened steps again. A commit that only records the review history in C2's validation entry reopens C2 alone, and main states why it does not affect C1. Nothing is pushed until both Claims are accepted.

Each commit leaves the full suite passing in both discovery forms.

### C1 acceptance

1. **Support module.** The test directory gains one support module whose name does not match the test discovery pattern, so discovery never loads it as a test module. It defines no `TestCase` subclass and imports none. It loads the configuration tool script once, and holds the module-level helpers (the directory-link helpers), the script path, and every class-level helper or constant that C2 would otherwise leave borrowed across modules.
2. **Import form.** Test code imports the support module with the package form the existing handoff tests use for shared test code, so one module object serves both discovery forms run from the repository root. The configuration tool stays one loaded module object for the whole suite.
3. **Borrowing inventory.** Main lists every reference from one test class to another class's attribute (methods, static helpers, constants, borrowed `setUp` or test methods) and every use of a module-level name, with its target module under C2's grouping. A reference whose class and target end up in the same C2 module may stay as it is; every other one is moved to the support module. The inventory goes in C1's commit message or brief and is the list the method comparison allows.
4. **Only borrowed references change.** Compared with the base revision, the set of test classes and their test methods is the same, and every test method's body is identical except for references in the inventory, which now reach the support module. A class that kept a borrowed helper as a class attribute may refer to the support module's version instead. No assertion, literal or control flow changes.
5. **Suite equivalence.** In the same environment, both `python -B -m unittest discover -s tests -t .` and `python -B -m unittest discover -s tests` run the same set of tests as at the base revision, identified by class and method name, with the same count, the same outcome for each and the same skips with the same reasons.
6. **No other file.** Only the test module and the new support module change.

### C2 acceptance

1. **Grouping.** Each class moves whole into exactly one module:

   | Module | Classes |
   | --- | --- |
   | configuration tool (keeps the current module name) | `FeatherConfigTests`, `SavedStopThresholdTests` |
   | review rules | `ReviewRulesFollowUpTests`, `PostFixReviewTests`, `StopThresholdProceduresTests` |
   | security review | `SecurityCriticalVocabularyTests`, `PreApprovalSecurityAnalysisTests`, `PreApprovalApprovalRuleTests`, `AdversaryRoleTests`, `AdversarialReviewTests`, `AdversarialReviewRetriesTests`, `AdversaryLimitsTests`, `SecurityCriticalWordingTests`, `DecisionRecordAndDocumentsTests` |
   | commands | `AdversarialReviewCommandTests`, `CommandScopeTests`, `StopThresholdCommandTests` |
   | releases | `SecurityRoutingReleaseTests`, `ReviewFollowUpsReleaseTests`, `StopThresholdReleaseTests`, `InstallDocumentTests`, `UpstreamManifestTests` |

   The new modules are named `test_feather_review_rules`, `test_feather_security_review`, `test_feather_commands` and `test_feather_releases`. Classes that borrow a test method or each other's helpers share a module, as the grouping already provides.
2. **Pure move.** Every class body, including its docstring, class attributes and every method, is identical to its body at C1's last commit. No module imports a `TestCase` class from another test module, so discovery loads each class once.
3. **Module scope.** Each of the five modules opens with a docstring stating the feature it covers, so a new test has an evident home. Each keeps the `__main__` entry the current module has, and imports what its classes use.
4. **Suite equivalence.** C1 item 5 holds against the base revision of C1.
5. **Reproduce commands.** The validation document's Reproduce section runs the whole suite with `python -B -m unittest discover -s tests -t .` instead of naming modules. Earlier specs and earlier validation entries are history and are not changed.
6. **Validation entry.** The validation document gains a heading for the split on main after 0.20.0, recording the environment, both discovery results with their counts and skips, the result of the method comparison for C1 and C2, and a table of each class and the module it moved to. The next release's entry refers to it.
7. **No other file.** Only the test modules, the support module and the validation document change.

## User Stories

1. As the maintainer, I want each feature's tests in their own module, so that Claims touching different features no longer edit one shared test file.
2. As the maintainer, I want the split to run exactly the tests that run today, so that no coverage is lost in the move.
3. As the maintainer, I want every assertion unchanged, so that a passing suite after the split means what it meant before.
4. As a reviewer, I want helper changes and pure moves in separate Claims, so that I can read the small content change carefully and check the large move with a tool.
5. As a reviewer, I want a list of every borrowed reference that changed, so that I can check C1's diff against it rather than search eight thousand lines.
6. As a verifier, I want a comparison of every test method's body before and after, so that equal counts and passes cannot hide a weakened assertion.
7. As a verifier, I want the comparison to identify tests by class and method, so that module renames do not count as differences.
8. As a verifier, I want the suite compared in both discovery forms, so that the split works however the suite is started.
9. As the maintainer, I want skips compared item by item with their reasons, so that a test that silently stopped running is caught.
10. As the maintainer, I want the configuration tool loaded once for the whole suite, so that tests do not drift between copies of it.
11. As the maintainer, I want no test module to import another module's test class, so that no class is run twice.
12. As the maintainer, I want the shared helpers in one module without tests, so that discovery never mistakes it for a test module.
13. As the maintainer, I want the configuration tool's tests to keep the current module name, so that its history stays easy to follow.
14. As a contributor, I want each module to say what it covers, so that I know where a new test goes.
15. As the maintainer, I want the reproduce commands to run the whole suite, so that they stay right however the tests are arranged.
16. As the maintainer, I want earlier specs and validation entries left as they are, so that the record of past releases is not rewritten.
17. As the maintainer, I want a table of where each class went, so that someone following an old reference can find the test.
18. As the maintainer, I want the split landed without a release, so that users are not asked to update for a change that does not affect them.
19. As the maintainer, I want the split kept apart from any rule change, so that its equivalence check stays meaningful.
20. As the maintainer, I want this stage done before the mixed review schedule, so that the second stage is reviewed against the smaller modules.

## Implementation Decisions

- The configuration tool's tests keep the current module; four new feature modules and one support module are added beside it.
- Whole classes move. `FeatherConfigTests` stays one class of about 4,100 lines; splitting it is left for when its size causes conflicts.
- The support module follows the existing package import form for shared test code, which works under both discovery forms when run from the repository root.
- Helpers that are only shared within a C2 module stay where they are; the support module takes only what would cross modules, plus the module-level helpers and the loaded configuration tool.
- Test IDs change with the module names; nothing outside the test suite refers to them.
- No version change, tag or `plugin.json` change; the next release carries the split.

## Testing Decisions

- The seam is the existing one: the whole test directory run through `unittest discover` in both forms. Results are compared as sets of class and method names with each test's outcome and skip reason, in the same environment before and after.
- A one-off comparison script, kept in the session scratchpad and not committed, parses the base and changed test code and compares every test class's methods and class attributes as syntax trees: identical for C2, identical except the inventoried references for C1. Its output is recorded in C2's validation entry. The baseline can be regenerated from C1's base revision when the work spans sessions.
- No new test is committed. A future module that imports another module's test class would run that class twice, which the test count in the next release's validation shows.
- Prior art: the existing handoff test modules that share code through the package import, and the validation entries for 0.19.0 and 0.20.0 that compare both discovery forms.

## Out of Scope

- Splitting `FeatherConfigTests` or any other class, or renaming classes or tests.
- Changing, adding or removing any assertion, including the non-blocking follow-ups from the 0.19.0 and 0.20.0 review rounds.
- The handoff and plugin portability test modules.
- Any review rule, procedure, ADR or glossary change; the mixed review schedule is the second stage.
- A release, version change or tag.
- A committed guard test for the module layout.

## Further Notes

- Automatic plan review is on, so this spec gets plan review before implementation once the user agrees to it.
- The handoff `.feather/handoffs/review-schedule-per-claim.md` records the grilling decisions and the borrowing count found while grilling: about 69 cross-class references in 11 classes, including the shipped-files scan that the Stop threshold procedure tests borrow from the Security-critical vocabulary tests.
