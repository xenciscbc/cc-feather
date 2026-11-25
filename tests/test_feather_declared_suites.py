"""Declared test suites ticket 01 (docs/specs/declared-test-suites.md, Testing Decisions): a project may keep a Test
suite catalogue at `.feather/test-suites.md`, tracked in Git, whose rules one delegation reference owns; with it, every
final check runs each Landing-required suite at the commit to be landed or tagged, at Final check scope `full` and
`related` alike, in off and in auto; a failure in a required check makes the run failed, and any other non-pass leaves
the final check not run at the needed scope, with no fix Claim and no Stop threshold count; each recorded final check
run has one line per suite; the decision at the end of the Plan lists the catalogue's gate changes since the Plan's base
revision; a suite's `Budget:` line counts as the project's resource guidance for it. The setup document and both
READMEs describe it. Tests check which sentences the shipped documents state, not how main applies them.

The existing pins this ticket replaces, updated where they are: in test_feather_final_check, ReleaseScopeTests'
release question in review state's Final check scope; in test_feather_resource_floor, the count of links to the
resource-risk runs reference."""

from __future__ import annotations

import re
import unittest

from tests import feather_support
from tests.feather_support import config

REFERENCES = config.ROOT / "skills" / "delegation" / "references"
OWNER = REFERENCES / "test-suites.md"
REVIEW_STATE = REFERENCES / "review-state.md"
RESOURCE_RISK_RUNS = REFERENCES / "resource-risk-runs.md"
SETUP = config.ROOT / "docs" / "setup.md"
POINTER = "read the [test-suites reference](test-suites.md) and follow it."


def bullet(path, label: str) -> str:
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.startswith(f"- **{label}.**")]
    assert len(lines) == 1, (path.name, label, len(lines))
    return lines[0]


def setup_section() -> str:
    text = SETUP.read_text(encoding="utf-8")
    # The section's example holds a `## <suite name>` line, so it ends at the next section's own heading.
    return text.split("\n## Test suite catalogue\n", 1)[1].split("\n## Auto land\n", 1)[0]


class Pinned:
    assert_whole_sentence = feather_support.stop_threshold_assert_whole_sentence

    def assert_bullet(self, path, label, *sentences):
        text = bullet(path, label)
        for sentence in sentences:
            with self.subTest(path=path.name, label=label, sentence=sentence[:60]):
                self.assert_whole_sentence(sentence, text)


class CatalogueReferenceTests(Pinned, unittest.TestCase):
    """Acceptance item 1: the test-suites reference owns the catalogue's rules."""

    def test_the_location_and_that_only_a_tracked_file_is_used(self):
        self.assert_bullet(
            OWNER, "Location",
            "A project may keep a Test suite catalogue at `.feather/test-suites.md` in the Working checkout, tracked in "
            "Git with the code it tests.",
            "Main reads it from the checkout at the commit it works on, not from the main worktree as with the Handoff "
            "store.")
        self.assert_bullet(
            OWNER, "Tracked at the commit",
            "Main uses the catalogue only when Git tracks it at the commit it works on.",
            "Main establishes this with `git cat-file -e <commit>:.feather/test-suites.md`, which shows it only by "
            "exiting 0; review state's Final check already requires the workspace to equal the commit to be landed or "
            "tagged, so the file main reads there is that commit's.",
            "When the file exists but is untracked or ignored, main reports that, does not use it and points the user "
            "to the setup document's Test suite catalogue section.",
            "A project without a tracked catalogue is not affected by this reference.")

    def test_the_entry_format_and_the_pass_condition(self):
        self.assert_bullet(
            OWNER, "Entry format",
            "The catalogue is markdown with one `## <suite name>` section for each Declared test suite.",
            "Each section has four required labelled lines: `Command:`, with its working directory, flags and "
            "environment variables; `Prerequisites:`; `Passes when:`; and `Gates:`.",
            "It may also have the optional lines `Budget:`, `Conflicts:` and `Affected part:`.",
            "Main reads the file as text, and no tool parses it.")
        self.assert_bullet(
            OWNER, "Passes when",
            "`Passes when:` states positive evidence that main can see in the run's output that the required selection "
            "ran, such as a marker line or a count above zero for a named group.",
            "An allowed-skip rule, such as no SKIP for a named pattern, may be added to that evidence but never "
            "replaces it.")

    def test_the_gates_and_the_optional_lines(self):
        self.assert_bullet(
            OWNER, "Gates",
            "`Gates:` lists any of `landing`, `full` and `release`, or `none`.",
            "`landing` runs the suite at every final check, whatever its Final check scope; `full` makes the suite part "
            "of the project's full run, which the overall acceptance names and the final check runs at scope `full`; "
            "`release` runs it before a release or tag.",
            "A suite whose gates include `landing` is a Landing-required suite, and one whose gates include `release` "
            "is a Release-required suite.")
        self.assert_bullet(
            OWNER, "Optional lines",
            "`Budget:` states the project's resource guidance for the suite, as the [resource-risk runs "
            "reference](resource-risk-runs.md)'s The budget states.")

    def test_an_unclear_entry_lets_no_check_through(self):
        self.assert_bullet(
            OWNER, "An unclear entry",
            "When main cannot read an entry unambiguously, it reports the entry to the user.",
            "Until the entry is corrected or the user decides Accept and land naming it, every final check and release "
            "whose requirements the entry could affect counts as not run at the scope it needs.",
            "Main never guesses a gate and never treats an unclear entry as absent.")

    def test_the_results_and_the_precedence_of_failure(self):
        self.assert_bullet(
            OWNER, "A pass",
            "A Declared test suite passes only when its command succeeds and its output shows the evidence its "
            "`Passes when:` line states.")
        self.assert_bullet(
            OWNER, "Results that are not a pass",
            "A run whose assertions failed is a failure.",
            "A run whose prerequisites are missing, or whose output does not show its pass condition, has not run.",
            "A run stopped from outside has not completed, and is judged as the [resource-risk runs "
            "reference](resource-risk-runs.md)'s Main's floor states.",
            "Main keeps these three results apart, in its reports and in any record, and retries none of them "
            "automatically.")
        self.assert_bullet(
            OWNER, "Failure first",
            "A run whose assertions failed is a failure even when its output also lacks the pass condition.",
            "A failure in one suite is not hidden by another suite that did not run, and a commit that has failed stays "
            "failed, as review state's Final check states.")
        self.assert_bullet(
            OWNER, "A suite nothing requires",
            "A suite that no gate and no acceptance requires satisfies nothing when it is not run, and blocks nothing.")

    def test_when_main_reads_it_and_which_version_counts(self):
        self.assert_bullet(
            OWNER, "Occasions",
            "Main reads the catalogue at the commit it works on before writing acceptance while Related-test "
            "acceptance is on, before every final check and before the release question.")
        self.assert_bullet(
            OWNER, "Which version counts",
            "Which suites are Landing-required suites and Release-required suites is resolved from the catalogue at the "
            "commit to be landed or tagged.")

    def test_the_reference_does_not_restate_the_stopped_run_rule_or_the_question_rule(self):
        text = OWNER.read_text(encoding="utf-8")
        for phrase in ("never as a failed run", "judged from what stopped it", "Asking in the conversation",
                       "in the message that ends its turn", "cc-feather states no numbers"):
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, text)

    def test_no_other_file_restates_the_catalogue_rules(self):
        # The phrases only the owner states; the other files point to it.
        owned = ("git cat-file -e", "may be added to that evidence but never replaces it", "Main never guesses a gate",
                 "satisfies nothing when it is not run", "A failure in one suite is not hidden",
                 "Which suites are Landing-required suites and Release-required suites is resolved")
        others = [*sorted((config.ROOT / "skills").rglob("*.md")), *sorted((config.ROOT / "templates").rglob("*.md")),
                  SETUP, config.ROOT / "README.md", config.ROOT / "README.zh-TW.md",
                  config.ROOT / "docs" / "reference.md", config.ROOT / "docs" / "reference.zh-TW.md"]
        for path in others:
            text = path.read_text(encoding="utf-8")
            for phrase in owned:
                with self.subTest(path=path.relative_to(config.ROOT).as_posix(), phrase=phrase):
                    if path == OWNER:
                        self.assertGreaterEqual(text.count(phrase), 1)
                    else:
                        self.assertEqual(text.count(phrase), 0)

    def test_the_pointers_to_the_reference_resolve(self):
        found = 0
        for path in sorted((config.ROOT / "skills").rglob("*.md")):
            for link in re.findall(r"\]\(([^)]*test-suites\.md)\)", path.read_text(encoding="utf-8")):
                with self.subTest(path=path.name, link=link):
                    self.assertEqual((path.parent / link).resolve(), OWNER.resolve())
                found += 1
        # Review state's Final check and the resource-risk runs reference's The budget.
        self.assertEqual(found, 2)


class FinalCheckTests(Pinned, unittest.TestCase):
    """Acceptance items 2, 3 and 5: review state's Final check, Final check scope and the decision at the end."""

    def test_every_final_check_runs_the_landing_required_suites(self):
        self.assert_bullet(
            REVIEW_STATE, "Final check",
            "When Git tracks a Test suite catalogue at the commit to be landed or tagged, every final check, at Final "
            "check scope `full` and `related` alike and in off and in auto, also runs each Landing-required suite at "
            "that commit, after main reads the catalogue there: " + POINTER,
            "A suite with both `landing` and `full` runs once per final check.",
            "Declared test suites run one at a time.")

    def test_the_required_checks_and_their_results(self):
        self.assert_bullet(
            REVIEW_STATE, "Final check",
            "The required checks of a final check are then a Landing-required suite at either scope, a suite the plan's "
            "overall acceptance names at `full`, and a suite a claim's primary acceptance names.",
            "Any failure in a required check makes the run failed, whatever else in the run did not run, and it is "
            "fixed as any final check failure is.",
            "A required check that has not passed without a failure, because its prerequisites are missing, its output "
            "does not show its pass condition or its run was stopped before it completed, leaves the final check not "
            "run at the scope the operation needs: main adds no fix claim for it, it does not count toward the "
            "failures at different commits in a row that stop the final check at the Stop threshold, and main reports "
            "it and waits for the user, who provides what is missing so that main runs it again, or decides accept and "
            "land naming the suite and its result.")

    def test_coverage_at_full_and_off(self):
        self.assert_bullet(
            REVIEW_STATE, "Final check",
            "At `full`, the command-by-command coverage above also applies to a claim's command that a suite's run "
            "covers.",
            "In off, the final check runs the Landing-required suites as part of its overall acceptance checks under "
            "off's rules, and still takes no pass from another session; neither the review mode nor Related-test "
            "acceptance switches the catalogue on or off.")

    def test_the_stopped_run_rule_stays_a_single_pointer(self):
        final = bullet(REVIEW_STATE, "Final check")
        self.assertEqual(final.count("stopped from outside"), 1)
        self.assertNotIn("in the message that ends its turn", final)

    def test_final_check_scope_runs_them_at_related(self):
        self.assert_bullet(
            REVIEW_STATE, "Final check scope",
            "When Git tracks a Test suite catalogue at the commit to be landed or tagged, a run at `related` also runs "
            "every Landing-required suite, as a run at `full` does, as Final check describes.",
            "Otherwise main asks the user the release question, a scope question for that commit: whether to run "
            "`full` or to tag on a `related` run at that commit, stating that `related` leaves out the plan's overall "
            "acceptance checks and reruns only this plan's claims' primary acceptance and, when Git tracks a Test suite "
            "catalogue at that commit, every Landing-required suite.")
        text = REVIEW_STATE.read_text(encoding="utf-8")
        self.assertEqual(text.count("stating that `related` leaves out the plan's overall acceptance checks"), 1)

    def test_the_decision_at_the_end_lists_gate_changes(self):
        self.assert_bullet(
            REVIEW_STATE, "Accept and land at the end of the plan",
            "When the Test suite catalogue at the commit to be landed differs from the one at the plan's base "
            "revision, the list also states its gate changes: suites added, removed, or with gates added or dropped, "
            "the plan's base revision taken as Evidence for a regression states.",
            "In off, main's report before landing lists the gate changes of the Test suite catalogue between the plan's "
            "base revision and the commit to be landed in the same way, from the plan's base revision main establishes "
            "itself from Git in this session.")


class RecordedRunTests(Pinned, unittest.TestCase):
    """Acceptance item 4: one line per suite in each recorded final check run, and what a suite's recorded pass
    covers."""

    def test_each_suite_line_and_its_coverage(self):
        self.assert_bullet(
            REVIEW_STATE, "Recorded final check runs",
            "The entry also has one line for every Declared test suite the run ran, giving the command as run, whether "
            "it ran the whole suite or a narrowed part and which part, the conditions that decide what runs and how, "
            "the evidence of its pass condition, and its result: passed, failed, not run with the reason, or stopped.",
            "A suite's recorded pass covers that suite at that commit only under the conditions below for a recorded "
            "pass, and a narrowed run covers only its part, never the whole suite.",
            "A suite that passed inside a run that was otherwise incomplete still covers that suite, but a suite's "
            "recorded pass never makes a failed commit passed.")


class BudgetTests(Pinned, unittest.TestCase):
    """Acceptance item 6: a suite's `Budget:` line in the resource-risk runs reference's budget order."""

    def test_the_budget_line_counts_as_project_guidance(self):
        self.assert_bullet(
            RESOURCE_RISK_RUNS, "The budget",
            "A Declared test suite's `Budget:` line counts as the project's resource guidance for that suite: it never "
            "overrides the user's statement in this session, the Plan's execution conditions or an approved Execution "
            "method, and when other project guidance states a different budget for the same suite, main asks the user.",
            "For the Test suite catalogue, " + POINTER,
            "cc-feather states no numbers.")


class GlossaryTests(unittest.TestCase):
    """Acceptance item 7: the Final check scope entry and the four catalogue entries, each defined once."""

    assert_whole_sentence = feather_support.stop_threshold_assert_whole_sentence

    PINS = {
        "Final check scope": (
            "In a project with a Test suite catalogue, both scopes also run every Landing-required suite.",),
        "Test suite catalogue": (
            "A project's optional list of its Declared test suites, kept in `.feather/test-suites.md` of the Working "
            "checkout and tracked in Git with the code it tests.",),
        "Declared test suite": (
            "It passes only when the command succeeds and its output shows positive evidence that the required tests "
            "ran.",
            "A run whose assertions failed is a failure."),
        "Landing-required suite": (
            "A Declared test suite whose gates include `landing`.",
            "Every final check runs it at the commit to be landed or tagged, at Final check scope `full` and `related` "
            "alike; when it has not passed there, the final check has not run at the scope the operation needs, so "
            "landing with it needs Accept and land that names it."),
        "Release-required suite": ("A Declared test suite whose gates include `release`.",),
    }

    def test_each_entry_is_defined_once_and_pinned(self):
        text = (config.ROOT / "CONTEXT.md").read_text(encoding="utf-8")
        entries = feather_support.glossary_entries(text)
        for term, sentences in self.PINS.items():
            with self.subTest(term=term):
                self.assertEqual(text.count(f"**{term}**:"), 1)
            for sentence in sentences:
                with self.subTest(term=term, sentence=sentence[:60]):
                    self.assert_whole_sentence(sentence, entries[term])


class DocumentTests(unittest.TestCase):
    """Acceptance item 8: the setup document's section and the paired README sentence."""

    assert_whole_sentence = feather_support.stop_threshold_assert_whole_sentence

    def test_the_setup_section_points_to_the_reference_and_shows_the_ignore(self):
        section = setup_section()
        for sentence in (
                "Landing-required suites, those whose gates include `landing`, run at every final check at Final check "
                "scope `full` and `related` alike, in auto and in off, so `related` never leaves them out.",
                "The rules for the catalogue, such as what counts as a pass and when main reads the file, are in the "
                "delegation skill's test-suites reference (`skills/delegation/references/test-suites.md`); this section "
                "describes them without restating them."):
            with self.subTest(sentence=sentence[:60]):
                self.assert_whole_sentence(sentence, " ".join(section.split()))
        self.assertIn("```gitignore\n/.feather/*\n!/.feather/test-suites.md\n```", section)

    def test_the_setup_section_has_one_example_entry(self):
        section = setup_section()
        example = section.split("```markdown\n", 1)[1].split("```", 1)[0]
        self.assertEqual(len(re.findall(r"^## ", example, re.M)), 1)
        for label in ("Command:", "Prerequisites:", "Passes when:", "Gates:"):
            with self.subTest(label=label):
                self.assertEqual(len(re.findall(rf"^{re.escape(label)} ", example, re.M)), 1)
        self.assertEqual(section.count("```markdown\n"), 1)

    def test_both_readmes_mention_it_in_a_paired_sentence(self):
        english = feather_support.review_rules_source("README.md#Final check scope")
        chinese = feather_support.review_rules_source("README.zh-TW.md#最終檢查範圍")
        self.assert_whole_sentence(
            "In a project that tracks a Test suite catalogue in `.feather/test-suites.md`, both scopes also run every "
            "suite whose gates include `landing`, as the [setup document](docs/setup.md#test-suite-catalogue) "
            "describes.", english)
        self.assert_whole_sentence(
            "在用 Git 追蹤 `.feather/test-suites.md` 測試套件目錄的專案中，兩種範圍也都會執行每個 gates 含 `landing` 的套件，"
            "如 [setup 文件](docs/setup.md#test-suite-catalogue)所述。", chinese)


if __name__ == "__main__":
    unittest.main()
