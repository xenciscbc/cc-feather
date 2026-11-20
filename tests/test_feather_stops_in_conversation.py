"""Stops-in-conversation ticket 01 (docs/specs/stops-in-conversation.md, Testing Decisions): once a Plan's implementation
has started, main asks every question it waits on in the message that ends its turn, in the conversation, without a
question tool, listing what the user is to decide and the options, the user's own message being the answer. Review
state states the rule once, in Ticket status and user decisions before User decisions: when implementation has
started, the stops it names as examples, that the Review level question and the ask after READY keep AskUserQuestion
only before implementation has started, that it sets how main asks and not when it stops, and that it holds in off and
in auto. The light Plan's stop at the end and the resource-risk runs reference's The ask refer to it, and both READMEs
say, where they describe the decision at the end of a plan, that main asks it in the conversation, paired sentence for
sentence. Tests check which sentences the shipped documents state, not how main applies them.

The existing pin this ticket replaces, updated where it is: in test_feather_review_level, review state's The stop at the
end."""

from __future__ import annotations

import unittest

from tests import feather_support
from tests.feather_support import config

REFERENCES = config.ROOT / "skills" / "delegation" / "references"
REVIEW_STATE = REFERENCES / "review-state.md"
RESOURCE_RISK_RUNS = REFERENCES / "resource-risk-runs.md"
LABEL = "Asking in the conversation"


def bullet(path, label: str) -> str:
    return next(line for line in path.read_text(encoding="utf-8").splitlines() if line.startswith(f"- **{label}.**"))


def runtime_markdown() -> dict[str, str]:
    """Every runtime Markdown file under skills/, by repository path."""
    root = config.ROOT / "skills"
    return {path.relative_to(config.ROOT).as_posix(): path.read_text(encoding="utf-8")
            for path in sorted(root.rglob("*.md"))}


class StopsInConversationTests(unittest.TestCase):
    assert_whole_sentence = feather_support.stop_threshold_assert_whole_sentence

    # Review state's owner rule, sentence by sentence.
    RULE = (
        "Once a Plan's implementation has started, main asks every question it waits on in the message that ends its "
        "turn, in the conversation, without a question tool, listing what the user is to decide and the options; the "
        "user's own message is the answer, as Final check scope defines the user's answer.",
        "A Plan's implementation has started once main starts implementing its first Claim, or once main finds it "
        "implemented in part or whole, as Implemented before plan review describes; a resumed session whose Plan is "
        "implemented in part counts as started.",
        "Examples are the decision at the end of the Plan, an accept-and-land decision, a stop at the Stop threshold, a "
        "Deviation, Unknown state, Implemented before plan review, the ask a later plan review makes after a Deviation "
        "or, after implementation has started, in a resumed session, merge-upstream's Final check scope question and "
        "its approval of the Integration report, choosing the level again under Leaving light, the release question, "
        "and the ask after READY when plan review runs on implemented work.",
        "The Review level question, which the [plan-review procedure](plan-review.md) asks, and the ask after READY, "
        "which the resource-risk runs reference's The ask states, keep AskUserQuestion only while the Plan's "
        "implementation has not started.",
        "The rule sets how main asks, not when it stops: work that may continue, such as an independent Claim, still "
        "continues first, and several pending questions are listed together in that one message.",
        "It holds in off and in auto, since a Plan at `light` runs in off.",
        "A command the user invokes outside a Plan's implementation, such as handoff-tidy or handoff-resume, keeps its "
        "own way of asking.",
    )

    STOP_AT_THE_END = (
        "Once every Claim of a Plan at `light` has finished its Code review, with APPROVED or stopped, and its "
        "acceptance run, main stops in the conversation, as Asking in the conversation describes, listing for each "
        "Claim the Code review's verdict, the acceptance results and the open findings, then what is left, landing "
        "included, and that the ticket stays unfinished until the user accepts it or says it is done, as Ticket status "
        "and User decisions describe."
    )

    THE_ASK = (
        "When plan review returns READY after the Plan's implementation has started, main makes this ask in the "
        "conversation instead, as [review state](review-state.md)'s Asking in the conversation states."
    )

    # Both READMEs' Final check and landing bullets, paired sentence for sentence.
    README_PAIRS = (
        ("Main asks that decision in the conversation, ending its turn without a question tool, as it asks every "
         "question it stops on once a plan's implementation has started, so you can leave with `/clear` or a new "
         "session without another model call.",
         "主 Agent 在對話中提出這個決定，不用提問工具並結束它的回合，計畫開始實作後它停下來等你回答的每個問題都是如此，讓你可以用 "
         "`/clear` 或新的 session 離開，不必多一次模型呼叫。"),
        ("The Review level question and the question after READY, asked before implementation starts, still use a "
         "question tool.",
         "審查等級的提問與 READY 之後的提問在實作開始前提出，仍使用提問工具。"),
    )
    # The sentence each README pair follows: the decision at the end of the plan.
    END_OF_PLAN = (
        "In auto, main then asks you once, at the end of the plan, listing each claim's passes, what is missing and "
        "what this flow does not check.",
        "在 auto 下，主 Agent 接著只在計畫結束時問你一次，列出每個 claim 的通過結果、缺少的部分，以及這套流程沒有檢查的事。",
    )

    def test_review_state_states_the_rule(self):
        body = bullet(REVIEW_STATE, LABEL)
        for sentence in self.RULE:
            with self.subTest(sentence=sentence[:60]):
                self.assert_whole_sentence(sentence, body)
        self.assertEqual(len(feather_support.sentences(body.split("**", 2)[2])), len(self.RULE))

    def test_the_rule_sits_in_ticket_status_and_user_decisions_before_user_decisions(self):
        text = REVIEW_STATE.read_text(encoding="utf-8")
        section = text.split("\n## Ticket status and user decisions\n", 1)[1].split("\n## ", 1)[0]
        labels = [line.split("**", 2)[1] for line in section.splitlines() if line.startswith("- **")]
        self.assertEqual(labels.count(f"{LABEL}."), 1)
        self.assertEqual(labels[labels.index(f"{LABEL}.") + 1], "User decisions.")
        self.assertEqual(text.count(f"- **{LABEL}.**"), 1)

    def test_the_light_stop_at_the_end_refers_to_the_rule(self):
        body = bullet(REVIEW_STATE, "The stop at the end")
        self.assert_whole_sentence(self.STOP_AT_THE_END, body)
        self.assertNotIn("without a question tool", body)
        self.assert_whole_sentence("Main lands a Plan at `light` only on the user's instruction.", body)

    def test_the_ask_refers_to_the_rule_and_keeps_its_question_tool(self):
        body = bullet(RESOURCE_RISK_RUNS, "The ask")
        self.assert_whole_sentence(self.THE_ASK, body)
        self.assertEqual(body.count("one AskUserQuestion"), 1)
        self.assertTrue(body.rstrip().endswith(self.THE_ASK))

    def test_no_other_runtime_file_restates_the_rule(self):
        # Phrases only the owner states (ADR 0017); every other runtime file under skills/ refers to review state.
        owner = REVIEW_STATE.relative_to(config.ROOT).as_posix()
        files = runtime_markdown()
        self.assertIn(owner, files)
        for phrase in ("in the message that ends its turn", "keep AskUserQuestion only while",
                       "A Plan's implementation has started once", "The rule sets how main asks, not when it stops",
                       "listing what the user is to decide and the options"):
            for path, body in files.items():
                with self.subTest(phrase=phrase, path=path):
                    self.assertEqual(body.count(phrase), 1 if path == owner else 0)
        # Every other mention names the rule by its label.
        for path, body in files.items():
            if path == owner:
                continue
            with self.subTest(path=path):
                self.assertEqual(body.count(LABEL), 1 if path.endswith("resource-risk-runs.md") else 0)

    def test_readmes_describe_it_with_the_decision_at_the_end_of_a_plan(self):
        english = feather_support.review_rules_source("README.md#Final check and landing")
        chinese = feather_support.review_rules_source("README.zh-TW.md#最終檢查與合併")
        for en, zh in self.README_PAIRS:
            with self.subTest(sentence=en[:60]):
                self.assert_whole_sentence(en, english)
                self.assert_whole_sentence(zh, chinese)
        # The pair follows the decision at the end of the plan, in the same order in both languages.
        for body, end, (first, second) in ((english, self.END_OF_PLAN[0], [p[0] for p in self.README_PAIRS]),
                                           (chinese, self.END_OF_PLAN[1], [p[1] for p in self.README_PAIRS])):
            with self.subTest(order=end[:20]):
                self.assertLess(body.index(end), body.index(first))
                self.assertLess(body.index(first), body.index(second))


if __name__ == "__main__":
    unittest.main()
