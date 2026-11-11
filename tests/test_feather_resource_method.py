"""Resource-risk runs ticket 04 (docs/specs/resource-risk-runs.md, Acceptance items 1, 2, 3, 4, 5 for a Resource-risk
claim's approved Execution method, 6, 7's last sentence, 9 for a refused environment, 13 for the Resource-risk claim
and Execution method entries, and 17): the plan-review item in analyst's role definition and plan review's pointers;
main's approval, the budget order, the binding, the carry, conditions and Execution, the Runner's refusal and main's
decisions after an INCONCLUSIVE about the method, in the resource-risk runs reference; the Resource-risk claim
sentences of the four role paragraphs; the Dispatch record's contents; and the two CONTEXT.md entries. These tests pin
the shipped text a model reads; they cannot show that a model always follows it."""

from __future__ import annotations

import unittest

from tests import feather_support
from tests.feather_support import config
from tests.test_feather_resource_floor import (AGENTS, FLOOR_ROLES, LINK, METHOD, METHOD_OUTCOME, OTHER_ROLES, REFERENCE,
                                               REFERENCES, bullet, normalised, paragraph, reference, role_text, section)

ROOT = config.ROOT
READ_REFERENCE = f"read the {LINK} and follow it."


def method_section() -> str:
    return section(reference(), "Execution method")


def plan_review_bullet() -> str:
    lines = [line for line in role_text("analyst").split("\n") if line.startswith("- Plan review:")]
    if len(lines) != 1:
        raise AssertionError(f"{len(lines)} plan-review bullets")
    return lines[0]


class PlanReviewItemTests(unittest.TestCase):
    """Acceptance item 1 and Implementation Decision "Plan review owns the judgement"."""

    assert_whole_sentence = feather_support.stop_threshold_assert_whole_sentence

    def test_the_analyst_item_judges_marks_estimates_and_proposes(self):
        text = plan_review_bullet()
        for sentence in (
            "For each claim, judge whether executing its implementation checks, acceptance checks or verification "
            "foreseeably risks exhausting memory, time or the machine, for example through unbounded recursion or graph "
            "walks, reference implementations without step limits, exhaustive or combinatorial generation, heavy "
            "parallel builds or race detectors, or whole-repository scanners; these are examples, and the list is not "
            "exhaustive.",
            # resource-risk-confirmation ticket 01: the mark is a proposal (tests/test_feather_resource_confirmation.py).
            "For a claim where it does, propose it as a Resource-risk claim with the reason, estimate its peak memory and "
            "time with the basis of the estimate, and propose an Execution method for the risky part: the experiment, its "
            "bounds and the memory and time limits it needs.",
            "A missing mark is not a statement that a claim is safe.",
            "This item adds no verdict of its own: a missing or weak Execution method is a finding like any other.",
        ):
            with self.subTest(sentence=sentence[:50]):
                self.assert_whole_sentence(sentence, text)
        # The item sits among the existing checks, before the verdict.
        self.assertLess(text.index("verified independently with its own acceptance."), text.index("For each claim, judge"))
        self.assertLess(text.index("A missing mark"), text.index("Return READY"))

    def test_the_analyst_item_renders_once_and_keeps_the_role_paragraph_out(self):
        for prefix in ("", config.ROLE_PREFIX):
            rendered = normalised(config._render("analyst", {"model": "sonnet", "effort": "high"}, prefix)
                                  .decode("utf-8"))
            with self.subTest(prefix=prefix):
                self.assertEqual(rendered.count("A missing mark is not a statement that a claim is safe."), 1)
        for role in OTHER_ROLES:
            with self.subTest(role=role):
                self.assertNotIn("For a Resource-risk claim, run its risky part", role_text(role))

    def test_plan_review_points_to_the_analyst_item_and_the_reference(self):
        text = normalised((REFERENCES / "plan-review.md").read_text(encoding="utf-8"))
        paragraphs = text.split("\n\n")
        self.assertTrue(paragraphs[1].startswith("This procedure governs main's orchestration."))
        pointer = paragraphs[2]
        for sentence in (
            "Analyst's role definition also governs the resource-risk item, which proposes a Resource-risk claim and "
            "its Execution method.",
            "The item runs wherever plan review runs, so in off an explicit plan-review request also judges it.",
            "For the user's decision on a proposed mark and main's approval of a proposed Execution method, "
            f"{READ_REFERENCE}",
        ):
            with self.subTest(sentence=sentence[:50]):
                self.assert_whole_sentence(sentence, pointer)

    def test_no_separate_command_or_skill_is_added(self):
        for path in sorted((ROOT / "skills").rglob("SKILL.md")):
            with self.subTest(path=path.parent.name):
                self.assertNotIn("resource-risk", path.parent.name)
                self.assertNotIn("resource risk", path.parent.name)


class ApprovalTests(unittest.TestCase):
    """Acceptance items 2, 3, 4, 6, 7's last sentence and 9's refused environment, and Implementation Decisions "One
    fresh call per run" and "One owner on main's side"."""

    assert_whole_sentence = feather_support.stop_threshold_assert_whole_sentence

    def assert_bullet(self, label, *sentences):
        text = bullet(method_section(), label)
        for sentence in sentences:
            with self.subTest(label=label, sentence=sentence[:50]):
                self.assert_whole_sentence(sentence, text)

    def test_the_section_opens_with_the_proposed_method(self):
        # resource-risk-confirmation ticket 01 moves plan review's proposal to Proposed marks.
        self.assertTrue(method_section().lstrip("\n").startswith(
            "A Resource-risk claim's Execution method is the one plan review proposed for its risky part, approved by "
            "main as this section states.\n"))

    def test_main_approves_the_method(self):
        self.assert_bullet(
            "Approving it",
            "Before the first brief of a Resource-risk claim for a role that may execute code, and before main's own "
            "first run for it, main reviews the proposed Execution method and approves it, changes it, or asks the user.",
            "An approved Execution method names the experiment for the risky part, its bounds, the memory and time "
            "limits, that it runs inside the Runner, and the source of the budget.")

    def test_the_budget_order_the_default_and_asking_the_user(self):
        self.assert_bullet(
            "The budget",
            "The budget comes, in order, from the user's own statement in this session, the Plan's execution "
            "conditions, the project's resource guidance, then the user's resource guidance; guidance may state a "
            "default budget.",
            "When the needed budget exceeds that default or no source states one, main asks the user.",
            "cc-feather states no numbers.")
        # Main's floor points to the budget order instead of stating its own.
        unbounded = bullet(section(reference(), "Main's floor"), "What is unbounded")
        self.assert_whole_sentence(
            "Main does not run a test or probe it cannot judge against a budget: it takes the budget, and asks the user "
            "when no source states one, as Execution method's The budget states.", unbounded)
        self.assertNotIn("it asks the user.", unbounded)

    def test_the_binding_and_what_invalidates_it(self):
        self.assert_bullet(
            "What it is bound to",
            "An approved Execution method is bound to its Claim, the Claim's recorded reading set, the experiment it "
            "describes, its budget and the budget's source.",
            "It stops being valid when the Claim's reading set changes, when the Plan gets a new plan review, or when "
            "its record is missing or does not match what it was recorded for; main then approves it again before the "
            "Claim's next run, asking the user where the budget's source requires it.")
        self.assert_bullet(
            "Where it is kept",
            "Main records each approval where an Observed resource risk is kept, as that section's Where it is kept "
            "states, and never writes it into the Claim's text.")

    def test_the_carry_into_every_brief_and_mains_own_runs(self):
        self.assert_bullet(
            "Carrying the conditions",
            "A Claim's execution conditions are its approved Execution method and its Observed resource risks.",
            "Main carries them verbatim into every brief of a role that may execute code for the Claim: its "
            "implementation, outcome verification and Adversarial review, reopened calls and later sessions included.",
            "Main applies them to its own runs for the Claim, such as reruns, reproductions and the final check's rerun "
            "of its primary acceptance.")

    def test_the_conditions_add_to_execution(self):
        self.assert_bullet(
            "Conditions and Execution",
            "A review's run, and main's own run, needs both the Execution determination [review state](review-state.md)'s "
            "Execution describes and the Claim's execution conditions.",
            "For an implementation by executor or security-executor, which get no Execution determination, the "
            "execution conditions add limits to what the Assignment allows and add no Execution determination.")

    def test_no_restriction_is_lifted_and_the_runner_is_never_a_named_isolated_environment(self):
        self.assert_whole_sentence(
            "It adds to [review state](review-state.md)'s Execution and never replaces it: nothing here, an approved "
            "Execution method included, allows a run that Execution does not, lifts a restriction the user stated, or "
            "makes the Runner an isolated environment the user named.", reference())

    def test_mains_own_runs_for_a_resource_risk_claim_use_the_runner(self):
        self.assert_whole_sentence(
            "Main's own runs for a Resource-risk claim use the Runner, with the limits of its approved Execution "
            "method.", bullet(section(reference(), "Main's floor"), "A Resource-risk claim"))

    def test_a_refusal_stops_the_claim_for_the_user(self):
        self.assert_bullet(
            "When the Runner refuses",
            "When the Runner refuses a run of a Resource-risk claim, the Claim stops for the user to decide: provide a "
            "tool that meets the Runner's contract, or accept that Claim's run without a hard limit in their own words.",
            "Main does not run the risky part another way meanwhile.")

    def test_mains_decisions_after_an_inconclusive_about_the_method(self):
        self.assert_bullet(
            "After an INCONCLUSIVE about the method",
            "When a role reports the approved Execution method insufficient or wrong, main either approves the role's "
            "proposed method, or another, and dispatches a new, fresh, normally counted call, asking the user where the "
            "new budget requires it; or keeps the method only together with new evidence or a changed condition that "
            "addresses the named gap.",
            "Without either, the Claim is reported unverified and the user decides.",
            "A call stopped by a limit closes as a completed call without a pass; a larger budget means a new call.",
            "A newly approved method is the changed prerequisite a call after INCONCLUSIVE needs: read the "
            "[outcome-verification procedure](outcome-verification.md)'s step 5, or for an Adversarial review the "
            "[Adversarial review procedure](adversarial-review.md)'s step 5, and follow it.",
            "Counting, the Stop threshold and what counts as a call are unchanged.")

    def test_the_pointed_steps_hold_the_rule_for_a_call_after_inconclusive(self):
        def step(path, number):
            lines = [line for line in normalised((REFERENCES / path).read_text(encoding="utf-8")).splitlines()
                     if line.startswith(f"{number}. ")]
            self.assertEqual(len(lines), 1, path)
            return lines[0]
        self.assertIn("On INCONCLUSIVE, use the next call only after the named missing evidence, prerequisite or "
                      "environment has changed; otherwise report the claim unverified.", step("outcome-verification.md", 5))
        self.assertIn("After any INCONCLUSIVE", step("adversarial-review.md", 5))

    def test_the_rules_are_stated_only_in_the_reference(self):
        # ADR 0017: the pointers carry no condition of the rules they point to.
        owned = ("cc-feather states no numbers", "the budget's source", "without a hard limit",
                 "a larger budget means a new call", "add no Execution determination", "verbatim into every brief")
        for path in sorted((ROOT / "skills" / "delegation").rglob("*.md")):
            text = normalised(path.read_text(encoding="utf-8"))
            for phrase in owned:
                with self.subTest(path=path.name, phrase=phrase):
                    self.assertEqual(text.count(phrase) >= 1, path == REFERENCE)


class RoleMethodTests(unittest.TestCase):
    """Acceptance item 5's Resource-risk claim bullets and Implementation Decision "Role placement"."""

    assert_whole_sentence = feather_support.stop_threshold_assert_whole_sentence

    def test_each_floor_role_carries_the_method_sentences_in_its_paragraph(self):
        for role in FLOOR_ROLES:
            block = METHOD.format(outcome=METHOD_OUTCOME[role])
            lines = [line for line in role_text(role).split("\n") if line.startswith("**Resources.** ")]
            with self.subTest(role=role):
                self.assertEqual(len(lines), 1)
                self.assertIn(block, lines[0])
                self.assertEqual(lines[0], paragraph(role))
                # The sentences follow the opening and come before the floor's Unbounded probe test.
                self.assertLess(lines[0].index(block), lines[0].index("Before you run a new or modified test"))

    def test_the_sentences_state_each_decision(self):
        text = METHOD.format(outcome=METHOD_OUTCOME["verifier"])
        for sentence in (
            "For a Resource-risk claim, run its risky part only as the approved Execution method in your brief "
            "describes and only inside the Runner with the brief's limits, and never change it: no raised limit, no "
            "larger or different experiment.",
            "Still judge whether the claim holds, ordinary acceptance checks and counterexample probes included, and "
            "whether the approved Execution method can establish it.",
            "When you judge the method insufficient or wrong, do not work around it: report INCONCLUSIVE with your "
            "proposed method and the reason.",
        ):
            with self.subTest(sentence=sentence[:50]):
                self.assert_whole_sentence(sentence, text)

    def test_the_outcome_words_match_each_role(self):
        for role in ("verifier", "adversary"):
            self.assertEqual(METHOD_OUTCOME[role], "report INCONCLUSIVE")
        for role in ("executor", "security-executor"):
            self.assertEqual(METHOD_OUTCOME[role], "report the task partial or blocked")
        self.assertEqual(set(METHOD_OUTCOME), set(FLOOR_ROLES))

    def test_the_installed_roles_render_the_sentences(self):
        for role in FLOOR_ROLES:
            block = METHOD.format(outcome=METHOD_OUTCOME[role])
            for prefix in ("", config.ROLE_PREFIX):
                rendered = normalised(config._render(role, {"model": "sonnet", "effort": "high"}, prefix).decode("utf-8"))
                with self.subTest(role=role, prefix=prefix):
                    self.assertEqual(rendered.count(block), 1)


class DispatchRecordTests(unittest.TestCase):
    """Implementation Decision "One owner on main's side": the Dispatch record holds approved Execution methods."""

    def test_the_dispatch_record_lists_approved_execution_methods(self):
        record = bullet(normalised((REFERENCES / "review-state.md").read_text(encoding="utf-8")), "Dispatch record")
        self.assertIn("each claim's approved Execution method and Observed resource risks;", record)
        self.assertIn("What an approved Execution method and an Observed resource risk name, and when main records "
                      f"them, are as the resource-risk runs reference states: {READ_REFERENCE}", record)


class GlossaryTests(unittest.TestCase):
    """Acceptance item 13: the Resource-risk claim and Execution method entries."""

    def setUp(self):
        self.text = (ROOT / "CONTEXT.md").read_text(encoding="utf-8")
        self.entries = feather_support.glossary_entries(self.text)

    def test_the_two_entries_are_defined_once_at_the_start_of_the_section(self):
        for term in ("Resource-risk claim", "Execution method"):
            with self.subTest(term=term):
                self.assertIn(term, self.entries)
                self.assertEqual(self.text.count(f"**{term}**:"), 1)
        terms = list(self.entries)
        start = terms.index("Resource-risk claim")
        self.assertEqual(terms[start:start + 5],
                         ["Resource-risk claim", "Execution method", "Unbounded probe", "Observed resource risk", "Runner"])
        section_text = normalised(self.text).split("\n## Resource-risk runs\n", 1)[1]
        self.assertTrue(section_text.lstrip("\n").startswith("**Resource-risk claim**:"))

    def test_the_entries_carry_their_decisions(self):
        pins = {
            # resource-risk-confirmation ticket 01: plan review proposes the mark and the user adopts it.
            "Resource-risk claim": ("Plan review proposes the mark", "An unmarked Claim is not thereby safe",
                                    "the basis of the estimate", "proposes an Execution method for the risky part"),
            "Execution method": ("that it runs inside the Runner", "the source of the budget",
                                 "bound to the Claim, its reading set, the experiment and the budget",
                                 "carries it into every brief of a role that may execute code for the Claim and into its "
                                 "own runs", "never changes it", "with its own proposed method",
                                 "It never lifts a restriction the user stated."),
        }
        for term, phrases in pins.items():
            for phrase in phrases:
                with self.subTest(term=term, phrase=phrase[:40]):
                    self.assertIn(phrase, self.entries[term])


if __name__ == "__main__":
    unittest.main()
