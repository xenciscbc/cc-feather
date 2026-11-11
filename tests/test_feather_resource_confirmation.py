"""Resource-risk confirmation ticket 01 (docs/specs/resource-risk-confirmation.md, Implementation Decisions "The mark is
a proposal" through "Not affected"): the analyst's resource-risk item as a proposal and its re-proposal rule; main's side
in the resource-risk runs reference's Proposed marks and Execution method's Approving it; the plan-review procedure's
pointers, step 5's one exception included; review state's Dispatch record; the Resource-risk claim entry in CONTEXT.md;
and ADR 0019's amendment note. The rule is written once (ADR 0017), so the pointers are checked not to restate it. These
tests pin the shipped text a model reads; they cannot show that a model always follows it."""

from __future__ import annotations

import unittest

from tests import feather_support
from tests.feather_support import config
from tests.test_feather_resource_floor import (AGENTS, DELEGATION, LINK, REFERENCE, REFERENCES, bullet, normalised,
                                               reference, section)
from tests.test_feather_resource_method import method_section, plan_review_bullet

ROOT = config.ROOT
ADR = ROOT / "docs" / "adr" / "0019-resource-risk-is-marked-at-plan-review-and-contained-by-the-runner.md"
PROPOSED_MARKS = f"as the resource-risk runs reference's Proposed marks states: read the {LINK} and follow it."


def marks_section() -> str:
    return section(reference(), "Proposed marks")


def text_of(path) -> str:
    return normalised(path.read_text(encoding="utf-8"))


class AnalystProposalTests(unittest.TestCase):
    """Implementation Decisions "The mark is a proposal" and "Later plan review calls" (the analyst's side)."""

    assert_whole_sentence = feather_support.stop_threshold_assert_whole_sentence

    def test_the_item_proposes_and_binds_only_once_adopted(self):
        text = plan_review_bullet()
        for sentence in (
            "For a claim where it does, propose it as a Resource-risk claim with the reason, estimate its peak memory "
            "and time with the basis of the estimate, and propose an Execution method for the risky part: the "
            "experiment, its bounds and the memory and time limits it needs.",
            "The proposal binds only once the user adopts it.",
            "A missing mark is not a statement that a claim is safe.",
            "This item adds no verdict of its own: a missing or weak Execution method is a finding like any other.",
            "When the brief carries the user's decision dropping a proposal, propose that claim again only with "
            "evidence the decision did not consider, such as a change to the claim or a risk source not in the earlier "
            "proposal, and state that evidence.",
        ):
            with self.subTest(sentence=sentence[:50]):
                self.assert_whole_sentence(sentence, text)
        self.assertNotIn("mark it a Resource-risk claim", text)
        self.assertLess(text.index("The proposal binds only"), text.index("A missing mark"))
        self.assertLess(text.index("When the brief carries the user's decision"), text.index("Return READY"))

    def test_the_rendered_role_keeps_each_kept_sentence_once(self):
        for prefix in ("", config.ROLE_PREFIX):
            rendered = normalised(config._render("analyst", {"model": "sonnet", "effort": "high"}, prefix)
                                  .decode("utf-8"))
            for sentence in ("A missing mark is not a statement that a claim is safe.",
                             "This item adds no verdict of its own",
                             "The proposal binds only once the user adopts it.",
                             "propose that claim again only with evidence the decision did not consider"):
                with self.subTest(prefix=prefix, sentence=sentence[:40]):
                    self.assertEqual(rendered.count(sentence), 1)


class ProposedMarksTests(unittest.TestCase):
    """Main's side in the resource-risk runs reference: Implementation Decisions "When main asks" through "End of the
    Plan"."""

    assert_whole_sentence = feather_support.stop_threshold_assert_whole_sentence

    def assert_bullet(self, label, *sentences):
        text = bullet(marks_section(), label)
        for sentence in sentences:
            with self.subTest(label=label, sentence=sentence[:50]):
                self.assert_whole_sentence(sentence, text)

    def test_the_section_comes_before_execution_method_and_opens_with_the_proposal(self):
        text = reference()
        self.assertLess(text.index("\n## Proposed marks\n"), text.index("\n## Execution method\n"))
        opening = marks_section().lstrip("\n").split("\n\n", 1)[0]
        for sentence in (
            "Plan review proposes a Resource-risk claim with an Execution method for its risky part, as analyst's role "
            "definition states.",
            "A Claim is a Resource-risk claim only once the user adopts the proposal; this section states main's side "
            "of that decision.",
        ):
            with self.subTest(sentence=sentence[:50]):
                self.assert_whole_sentence(sentence, opening)

    def test_where_it_applies(self):
        self.assert_bullet(
            "Where it applies",
            "This section applies in auto and after an explicit plan review in off.",
            "A Plan whose plan review proposes no mark, and work without plan review, get no question from this "
            "section.")

    def test_which_proposals(self):
        self.assert_bullet(
            "Which proposals",
            "The proposals main asks about are gathered from every call of the Plan's plan review, each Claim at its "
            "latest state: a proposal a later call withdrew is left out, and a Claim that was split, merged or removed "
            "is judged by the latest version of the Plan.",
            "A proposal stays undecided until the user's answer decides it.")

    def test_during_revise_main_only_lists(self):
        self.assert_bullet(
            "During REVISE",
            "Main does not ask about proposals after a REVISE call; it lists the Plan's current proposals in its "
            "progress report.")

    def test_main_checks_the_basis_and_only_the_user_decides(self):
        self.assert_bullet(
            "Checking the basis",
            "Before asking, main checks each proposal's basis, such as whether its cited evidence belongs to this work, "
            "and states a recommendation, adopt or drop, with the reason.",
            "Main never adopts or drops a proposal itself; only the user's answer decides.")

    def test_the_ask(self):
        self.assert_bullet(
            "The ask",
            "After the call that returns READY for the Plan and before main implements the Plan's first Claim, main "
            "asks the user once about every undecided proposal of the Plan, in one AskUserQuestion.",
            "Its multiple-choice question lists each proposed Claim with plan review's reason and estimate, main's "
            "recommendation, and the budget main would use with its source; the Claims the user selects are adopted and "
            "the rest are dropped.",
            "One budget question joins the same ask only when Execution method's The budget requires main to ask the "
            "user for a proposed Claim, and its answer applies to the Claims the user adopts.",
            "This ask is the one exception to the rule in the [plan-review procedure](plan-review.md)'s step 5 that "
            "READY continues work already authorized without another routine confirmation, and it arises only when a "
            "proposal is undecided.")

    def test_the_budget_question_points_to_the_budget_rule(self):
        # The order and conditions stay in Execution method's The budget.
        text = marks_section()
        for phrase in ("exceeds that default", "no source states", "in order", "the Plan's execution conditions",
                       "resource guidance", "cc-feather states no numbers"):
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, text)

    def test_a_dropped_claim(self):
        self.assert_bullet(
            "A dropped Claim",
            "A dropped Claim is not a Resource-risk claim: it has no Execution method and no Runner requirement.",
            "Main's floor and each role's floor for Unbounded probes apply to it as to any Claim, and an Observed "
            "resource risk is recorded on it as on any Claim.")

    def test_later_briefs_carry_the_decisions(self):
        self.assert_bullet(
            "Later plan-review briefs",
            "Every later plan-review brief for the Plan carries the user's decision on each proposal, with its reason.",
            "When analyst proposes a dropped Claim again with evidence the decision did not consider, main asks the "
            "user again.")

    def test_a_later_plan_review(self):
        self.assert_bullet(
            "A later plan review",
            "A proposal that a later plan review of the same Plan makes, after a Deviation or in a resumed session, is "
            "asked together with the user's approval that review already needs; when that review needs no approval of "
            "the user, main asks it before the affected Claim's next run.",
            "A later plan review also ends each adopted Claim's approved Execution method, as Execution method's What "
            "it is bound to states, so main approves each again at that same point, and any budget question it needs "
            "joins the same ask.")

    def test_binding_and_while_unanswered(self):
        self.assert_bullet(
            "Binding",
            "A decision is bound to its Claim and the Claim's recorded reading set.",
            "It stays valid while the reading set is unchanged; when the reading set changes and plan review proposes "
            "the mark again, main asks again.")
        self.assert_bullet(
            "While unanswered",
            "An undecided proposal holds back only its own Claim: no brief to a role that may execute code for it and "
            "no run of main's own for it.",
            "Other Claims proceed, subject to their own dependencies.")

    def test_where_decisions_are_kept_and_their_kind(self):
        self.assert_bullet(
            "Where decisions are kept",
            "Main records each decision, adopted or dropped with its reason and the reading set it is bound to, where "
            "an Observed resource risk is kept, as Observed resource risk's Where it is kept states, and never writes "
            "it into the Claim's text.")
        self.assert_bullet(
            "Kind of decision",
            "A decision on a proposal is recorded as adopted or dropped.",
            "It is none of the kinds [review state](review-state.md)'s User decisions names, and a dropped proposal is "
            "not a waiver.")
        self.assertIn("- **User decisions.**", text_of(REFERENCES / "review-state.md"))

    def test_deciding_is_not_a_review_event(self):
        self.assert_bullet(
            "Not a review event",
            "Deciding a proposal is not a plan-review call, changes no count or verdict, does not reopen plan review "
            "and is not a Deviation.")

    def test_the_end_of_the_plan_lists_dropped_proposals(self):
        self.assert_bullet(
            "At the end of the Plan",
            "The decision or completion report at the end of the Plan lists each dropped proposal, one line each: the "
            "Claim, plan review's reason and the user's reason, next to the Plan's Observed resource risks.")

    def test_approval_moves_to_the_ask_and_the_guarantee_stays(self):
        text = bullet(method_section(), "Approving it")
        for sentence in (
            "Before the first brief of a Resource-risk claim for a role that may execute code, and before main's own "
            "first run for it, main reviews the proposed Execution method and approves it, changes it, or asks the "
            "user.",
            "Main meets this rule at the ask Proposed marks describes: it approves the Execution method of each Claim "
            "the user adopts there, before the Plan's first Claim, using the budget order below, so no approval stops "
            "the chain of Claims later.",
        ):
            with self.subTest(sentence=sentence[:50]):
                self.assert_whole_sentence(sentence, text)


class PointerTests(unittest.TestCase):
    """Implementation Decisions "When main asks", "Later plan review calls", "Where decisions are kept" and
    "Documents": the plan-review procedure and review state point to the reference without restating it."""

    assert_whole_sentence = feather_support.stop_threshold_assert_whole_sentence

    def plan_review(self) -> str:
        return text_of(REFERENCES / "plan-review.md")

    def step(self, number: int) -> str:
        lines = [line for line in self.plan_review().splitlines() if line.startswith(f"{number}. ")]
        self.assertEqual(len(lines), 1)
        return lines[0]

    def test_plan_review_names_the_ask_as_step_5s_one_exception(self):
        self.assert_whole_sentence(
            "The one exception is the user's decision on proposed resource-risk marks, " + PROPOSED_MARKS, self.step(5))
        self.assertTrue(self.step(5).startswith(
            "5. With READY, continue work already authorized without another routine confirmation. The one exception"))

    def test_plan_review_briefs_carry_the_decisions(self):
        self.assert_whole_sentence(
            "A later call's brief also carries the user's decisions on proposed resource-risk marks, " + PROPOSED_MARKS,
            self.step(2))

    def test_plan_review_points_at_the_resource_risk_paragraph(self):
        pointer = self.plan_review().split("\n\n")[2]
        self.assert_whole_sentence(
            "For the user's decision on a proposed mark and main's approval of a proposed Execution method, read the "
            f"{LINK} and follow it.", pointer)

    def test_the_dispatch_record_holds_the_decisions(self):
        record = bullet(text_of(REFERENCES / "review-state.md"), "Dispatch record")
        self.assert_whole_sentence(
            "It also holds the user's decisions on proposed resource-risk marks; what such a decision names, and when "
            f"main records it, are as the resource-risk runs reference's Proposed marks states: read the {LINK} and "
            "follow it.", record)

    def test_the_rule_is_stated_only_in_the_reference(self):
        # ADR 0017: main's side is written once, in the reference; the analyst's side once, in its role definition.
        owned = ("one AskUserQuestion", "the budget main would use with its source", "judged by the latest version of "
                 "the Plan", "current proposals in its progress report", "no Execution method and no Runner "
                 "requirement", "holds back only its own Claim", "a dropped proposal is not a waiver",
                 "does not reopen plan review", "lists each dropped proposal", "only the user's answer decides",
                 "when that review needs no approval of the user")
        paths = sorted(DELEGATION.rglob("*.md")) + sorted(AGENTS.glob("*.md"))
        for path in paths:
            text = text_of(path)
            for phrase in owned:
                with self.subTest(path=path.name, phrase=phrase):
                    self.assertEqual(text.count(phrase), 1 if path == REFERENCE else 0)
        analyst_owned = ("The proposal binds only once the user adopts it.",
                         "propose that claim again only with evidence the decision did not consider")
        for path in paths:
            text = text_of(path)
            for phrase in analyst_owned:
                with self.subTest(path=path.name, phrase=phrase[:40]):
                    self.assertEqual(text.count(phrase), 1 if path == AGENTS / "analyst.md" else 0)


class GlossaryAndAdrTests(unittest.TestCase):
    """Implementation Decisions "Glossary" and "ADR"."""

    assert_whole_sentence = feather_support.stop_threshold_assert_whole_sentence

    def test_the_resource_risk_claim_entry_says_plan_review_proposes_and_the_user_adopts(self):
        text = (ROOT / "CONTEXT.md").read_text(encoding="utf-8")
        entries = feather_support.glossary_entries(text)
        entry = entries["Resource-risk claim"]
        for sentence in (
            "Plan review proposes the mark, with the reason, its estimated peak memory and time and the basis of the "
            "estimate, and proposes an Execution method for the risky part; the Claim is a Resource-risk claim only "
            "once the user adopts the proposal.",
            "A dropped proposal leaves an ordinary Claim, still covered by the Unbounded probe floor.",
            "An unmarked Claim is not thereby safe: a missing mark is not a statement that a Claim is safe.",
        ):
            with self.subTest(sentence=sentence[:50]):
                self.assert_whole_sentence(sentence, entry)
        self.assertNotIn("Plan review marks it", entry)
        for term in ("Execution method", "Observed resource risk"):
            with self.subTest(term=term):
                self.assertEqual(text.count(f"**{term}**:"), 1)

    def test_adr_0019_carries_the_amendment_note(self):
        text = text_of(ADR)
        decision = text.split("\n## Considered Options\n", 1)[0]
        note = ("(Amended in 0.35.0 by the [Resource-risk confirmation spec](../specs/resource-risk-confirmation.md): "
                "plan review's mark is a proposal that the user adopts or drops, asked once per Plan after its plan "
                "review returns READY and before its first Claim is implemented; only an adopted Claim is a "
                "Resource-risk claim, and a dropped one is an ordinary Claim still covered by the floor.)")
        self.assertEqual(decision.count(note), 1)
        self.assertIn(f"\n\n{note}\n", decision)
        self.assertTrue((ROOT / "docs" / "specs" / "resource-risk-confirmation.md").is_file())
        # The original decision stays as written; the note does not repeat it.
        self.assertEqual(decision.count("A missing mark is not a statement that a Claim is safe."), 1)
        # The note follows the form ADR 0006 uses.
        adr_0006 = text_of(ROOT / "docs" / "adr" / "0006-review-state-validity-and-completion.md")
        self.assertIn("\n(Amended in 0.15.0 by the [review follow-ups spec](../specs/review-followups-0-15-0.md): ",
                      adr_0006)


if __name__ == "__main__":
    unittest.main()
