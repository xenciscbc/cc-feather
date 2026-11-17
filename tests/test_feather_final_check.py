"""Final check reuse and Auto land ticket 01 (docs/specs/final-check-reuse-and-auto-land.md, security invariant S1): in
auto, main records every final check run in the Plan's dispatch record with its commit, scope, each Claim's reading-set
hash, result and time, written after its after-reads and before main acts on its result; a recorded pass makes its
commit passed only while HEAD is that commit, the workspace reads show no change, every Claim's reading set is unchanged
and the run's scope covers the scope now needed, a release or tag needing a `full` pass; a recorded failure, or one
observed in this session or shown in a compaction summary, keeps the commit failed; an Adversarial review gives a
Claim's result after a recorded pass only as an automatic call recorded after it; the residual risks are stated where
the rule is; off keeps the final check's state from this session only. The setup document, both READMEs and both
reference documents describe the reuse and its limits.

The existing pins this ticket replaces, updated where they are: in test_feather_completion_criteria, S8's three Final
check sentences on the state coming only from this session (now scoped to off, or naming the record in auto); in
test_feather_config, FOLLOW_UP_SENTENCES' whole Resumed sessions bullet and ACCEPTANCE_GATE_SENTENCES' whole What a
gated pass judged bullet; in test_feather_retained_passes, the Clearing a stop, What an explicit call runs and What a
gated pass judged sentences of S2, the Resumed sessions sentence of ACROSS_SESSIONS and the CONTEXT.md Dispatch record
entry's two sentences; in test_feather_delegation_dedupe, ONCE's R6.7 phrase and REPLACEMENTS' H13; in
test_feather_security_review, the Clearing a stop sentence of the stopped-Adversarial-review scenario.

Ticket 02 brings the Final check scope into review state and adds its pins to this module."""

from __future__ import annotations

import re
import subprocess
import unittest

from tests import feather_support
from tests.feather_support import config

TAG = "v0.36.0"
PATHS = {
    "review-state.md": "skills/delegation/references/review-state.md",
    "adversarial-review.md": "skills/delegation/references/adversarial-review.md",
    "CONTEXT.md": "CONTEXT.md",
    "setup.md": "docs/setup.md",
    "README.md": "README.md",
    "README.zh-TW.md": "README.zh-TW.md",
    "reference.md": "docs/reference.md",
    "reference.zh-TW.md": "docs/reference.zh-TW.md",
}
SETUP_PARAGRAPH = "In auto, main records each final check run in the plan's dispatch record"


def place_text(text: str, path: str, label: str) -> str:
    """'<file>#<label>' is a '- **<label>' bullet, a glossary entry in CONTEXT.md, the At the final commit paragraph of
    the Adversarial review procedure, or the setup document's paragraph on recorded final check runs."""
    if not label:
        return text
    if path == "CONTEXT.md":
        return feather_support.glossary_entries(text)[label]
    if label == "At the final commit":
        return next(line for line in text.splitlines() if line.startswith("**At the final commit.**"))
    if label == "recorded runs":
        return next(line for line in text.splitlines() if line.startswith(SETUP_PARAGRAPH))
    # The bullet's text after its bold label, so that a Chinese sentence right after the label starts the text.
    return next(line for line in text.splitlines() if line.startswith(f"- **{label}")).split("**", 2)[2].strip()


def source(name: str) -> str:
    path, _, label = name.partition("#")
    return place_text((config.ROOT / PATHS[path]).read_text(encoding="utf-8"), path, label)


def tagged(path: str) -> str:
    result = subprocess.run(["git", "-C", str(config.ROOT), "show", f"{TAG}:{PATHS[path]}"], capture_output=True,
                            check=False, timeout=60)
    if result.returncode != 0:
        raise unittest.SkipTest(f"{TAG} is not available: {result.stderr.decode('utf-8', 'replace').strip()}")
    return result.stdout.decode("utf-8")


class RecordedFinalCheckTests(unittest.TestCase):
    """Whole-sentence pins of the recorded final check, its reuse under S1, its limits and off's kept rules."""

    assert_whole_sentence = feather_support.stop_threshold_assert_whole_sentence

    def assert_pinned(self, pins):
        for place, sentences in pins.items():
            text = source(place)
            for sentence in sentences:
                with self.subTest(place=place, sentence=sentence[:60]):
                    self.assert_whole_sentence(sentence, text)

    RUNS = "review-state.md#Recorded final check runs"

    # Acceptance item 1 and S1: what is recorded for each run, when it is written, and the reuse conditions.
    RECORDED = {
        RUNS: (
            "In auto, main records every final check run in the plan's dispatch record: the commit it ran at, its "
            "scope, each claim's reading-set hash, passed or failed with a one-line summary, and the time the run ended.",
            "The scope is the plan's Final check scope the run used, and a run without a chosen scope is recorded as "
            "`full`.",
            "Main writes a run's entry between calls, as Dispatch record describes, after the reads that follow the run "
            "and before it acts on the run's result.",
            "A recorded pass is a pass main takes from the dispatch record rather than from its own run in this session, "
            "as in a resumed session or after a context compaction.",
            "A recorded pass makes its commit passed only while all of these hold: HEAD is that commit, and the "
            "workspace reads What a gated pass judged states show no change; every claim's reading set is unchanged "
            "from the hash recorded with the run; and the run's scope covers the scope now needed, a `full` pass "
            "covering `full` and `related` and a `related` pass only `related`, while a release or tag needs a `full` "
            "pass at that commit.",
            "Main checks these conditions each time it relies on a recorded pass: before the Adversarial reviews at the "
            "final commit, before the decision at the end of the plan and before landing, release or tagging.",
            "A commit without a recorded run, or with a recorded failure, is never passed by a record, and a failure "
            "main observed in this session, or that a compaction summary shows, keeps that commit failed whatever the "
            "record holds, as Final check describes for a failed commit.",
            "Where the record holds no run for the commit, or no recorded pass meets these conditions, main runs the "
            "final check.",
            "A pass comes only from main's own run in this session or from a recorded pass under these conditions, never "
            "from a handoff, a ticket, the Follow-up record, a role's report or a compaction summary.",
        ),
        "review-state.md#Final check": (
            "In auto, its state comes from main's own run in this session at that commit, or from a run the plan's "
            "dispatch record holds for that commit only as Recorded final check runs describes.",
            "When main cannot establish from this session, or in auto from the plan's dispatch record as Recorded final "
            "check runs describes, that the commit has not failed, it treats the commit as failed, and a decision states "
            "that state as \"failed (presumed: not established as unfailed in this session)\", with the reason and this "
            "session's outputs.",
            "Once it has failed at a commit, that commit's state is failed, and a later pass at the same commit lets "
            "landing proceed only through an accept-and-land decision that names the failure.",
        ),
    }

    # Acceptance item 2 and S1: the Dispatch record records each Adversarial review call's time and source, and an
    # Adversarial review gives a result after a recorded pass only as an automatic call recorded after it.
    ADVERSARIAL = {
        "review-state.md#Dispatch record": (
            "It also holds each final check run, as Recorded final check runs describes, and, for each Adversarial "
            "review call, the time main dispatched it and its source, automatic or explicit.",
        ),
        "adversarial-review.md#At the final commit": (
            "When that pass is a recorded pass, as [review state](review-state.md)'s Recorded final check runs "
            "describes, a call gives the claim's result only when it was an automatic call and the plan's dispatch "
            "record shows it dispatched after the time recorded for that pass; an explicit call, or one the record does "
            "not show dispatched after that pass, counts as not run.",
            "Only a call made after the final check passed at the commit to be landed, with the workspace equal to it, "
            "gives the claim's result; a result from an earlier or another commit, and an explicit call made before "
            "then, count as not run, so the claim needs accept and land or a new call.",
        ),
        RUNS: (
            "For an Adversarial review after a recorded pass, read the [Adversarial review "
            "procedure](adversarial-review.md)'s At the final commit and follow it.",
        ),
        # Acceptance item 5: the sentences that required the final check to have passed accept a recorded pass in auto.
        "review-state.md#What a gated pass judged": (
            "In auto, an Adversarial review gives the claim's result only when it is made after the final check passed "
            "at the commit to be landed, with the workspace equal to it, and judges that commit, and after a recorded "
            "pass, as Recorded final check runs describes, only when it is an automatic call that the plan's dispatch "
            "record shows dispatched after that pass; the claim's APPROVED and CONFIRMED are a record of the commits "
            "they judged, and a result from an earlier or another commit, or an explicit call made before then, counts "
            "as not run: read the [Adversarial review procedure](adversarial-review.md)'s At the final commit and "
            "follow it.",
        ),
        "review-state.md#Clearing a stop": (
            "In auto, an explicit HELD obtained before the final check passed at the commit to be landed, with the "
            "workspace equal to it, or obtained after a recorded pass, as Recorded final check runs describes, does not "
            "clear a stop either, since it counts as not run: read the [Adversarial review "
            "procedure](adversarial-review.md)'s At the final commit and follow it.",
        ),
        "review-state.md#What an explicit call runs": (
            "In auto, an explicit Adversarial review made before the final check passed at the commit to be landed, "
            "with the workspace equal to it, or made after a recorded pass, as Recorded final check runs describes, "
            "counts as not run even after the claim's valid APPROVED and CONFIRMED: read the [Adversarial review "
            "procedure](adversarial-review.md)'s At the final commit and follow it.",
        ),
    }

    # Acceptance item 3: a reused pass is named, with the run's time, in the decision and the completion report.
    REPORTED = {
        RUNS: (
            "When main reuses a recorded pass, the decision at the end of the plan and the completion report say that "
            "the pass is reused, with the run's time.",
        ),
    }

    # Acceptance item 1: a resumed session and main after a compaction take the final check's state as Recorded final
    # check runs describes.
    RESUMED = {
        "review-state.md#Resumed sessions": (
            "Counts still restart in each session, and the Stop threshold in effect comes only from this session.",
            "The final check's state comes from this session, or from a run the dispatch record holds only as Recorded "
            "final check runs describes, so main runs the final check again before landing unless a recorded pass meets "
            "the conditions stated there.",
        ),
    }

    # Acceptance item 6: the residual risks, where the rule is.
    LIMITS = {
        RUNS: (
            "A reused pass has limits this flow does not check: an environment change after the run, such as an "
            "upgraded tool or changed external state, is not detected; files outside the workspace reads, such as "
            "ignored files, can change between the run and its reuse, as they can within a session; and main takes the "
            "dispatch record as written, so an edit to it can let a commit land on a pass that would not hold now.",
        ),
    }

    # Acceptance item 4 and S1's last bullet: off keeps the final check's state from this session only.
    OFF = {
        "review-state.md#Final check": (
            "In off, its state comes only from main's own run in this session at that commit, never passed from a "
            "record or an earlier session, and after a context compaction main runs it again.",
            "In off, a record can only make the state failed, never passed.",
        ),
        RUNS: (
            "In off, main records no run, and a record never makes a commit passed, as Final check describes.",
        ),
        "review-state.md#Dispatch record": (
            "Off mode writes none, and in off the cross-session rules of Resumed sessions hold without it.",
        ),
        "review-state.md#Resumed sessions": (
            "In off, passing verdicts do not cross sessions either.",
        ),
    }

    # Acceptance item 8 and the glossary's Adversarial review entry (item 5).
    CONTEXT = {
        "CONTEXT.md#Dispatch record": (
            "It holds the Plan, its base revision and READY; each Claim's classification, reading set hash and base "
            "revision, and each review call's judged commit and verdict with a one-line summary; each fix Claim with its "
            "problem and a summary of the fix; each final check run with its commit, scope, each Claim's reading set "
            "hash, result with a one-line summary and time; each Adversarial review call's time and source; the "
            "branches main created for the work; and the user's decisions with their scope; never counts, exploit "
            "details or secrets.",
            "A resumed session, and main after a context compaction, take the Plan's READY, reading sets, passes, "
            "Adversarial review results and the user's decisions from it as if received in this session, while counts "
            "and the Stop threshold in effect still come only from this session.",
            "A recorded final check pass makes its commit passed only while HEAD is that commit, the workspace reads "
            "show no change, every Claim's reading set is unchanged from the hash recorded with the run and the run's "
            "scope covers the scope now needed, a release or tag needing a `full` pass; a recorded failure keeps its "
            "commit failed, and without a recorded run for the commit main runs the final check.",
            "Main takes it as written, so an edit to it changes what main believes.",
            "Off mode writes none.",
        ),
        "CONTEXT.md#Adversarial review": (
            "When that final check pass is a recorded pass the Plan's Dispatch record holds, only an automatic call the "
            "record shows made after it gives the Claim's result.",
        ),
    }

    # Acceptance item 9: the setup document, both READMEs (paired) and both reference documents.
    DOCUMENTS = {
        "setup.md#recorded runs": (
            "In auto, main records each final check run in the plan's dispatch record under `.feather/dispatch/`, with "
            "its commit, scope, each claim's reading-set hash, result and time.",
            "A resumed session, or main after a context compaction, reuses a recorded pass instead of running the final "
            "check again only while `HEAD` is that commit, the workspace reads show no change, every claim's reading set "
            "is unchanged and the run's scope covers the scope now needed, a release or tag needing a `full` pass; a "
            "recorded failure keeps its commit failed.",
            "The decision at the end of the plan and the completion report name a reused pass with its run's time.",
            "An environment change after the run, such as an upgraded tool, is not detected, and the dispatch record is "
            "taken as written, so an edit to it can let a commit land on a pass that would not hold now.",
            "In `off`, nothing is recorded, and the final check runs again in each session and after a context "
            "compaction.",
        ),
        "reference.md#Dispatch record": (
            "It also records each final check run with its commit, scope, each claim's reading-set hash, result and "
            "time, and main reuses a recorded pass only while `HEAD` is that commit, the workspace reads show no change, "
            "every claim's reading set is unchanged and the run's scope covers the scope now needed, a release or tag "
            "needing a `full` pass; a recorded failure keeps its commit failed, and otherwise main runs the final check "
            "again before landing.",
            "When main reuses a recorded pass, the decision at the end of the plan and the completion report say so "
            "with the run's time.",
            "A reused pass does not detect an environment change after its run, such as an upgraded tool, and the "
            "record is taken as written.",
            "In `off`, main writes none, and the final check runs again in each session.",
        ),
        "reference.zh-TW.md#派工紀錄": (
            "它也記錄每次最終檢查的執行，包括 commit、範圍、每個 claim 閱讀範圍的雜湊、結果與時間；主 Agent 只在 `HEAD` "
            "仍是那個 commit、工作區的讀取沒有變動、每個 claim 的閱讀範圍都沒有改變，且那次執行的範圍涵蓋現在需要的範圍時，"
            "才沿用記錄下來的通過，release 或 tag 需要 `full` 的通過；記錄下來的失敗讓那個 commit 維持失敗，其他情況主 "
            "Agent 會在進入預設 branch 前重新執行最終檢查。",
            "主 Agent 沿用記錄下來的通過時，計畫結束時的決定與完成報告會說明這一點，並附上那次執行的時間。",
            "沿用的通過偵測不到執行之後的環境變動（例如工具升級），紀錄也照所寫的內容採信。",
            "在 `off` 下，主 Agent 不寫派工紀錄，每個 session 都會重新執行最終檢查。",
        ),
        "reference.md#Final check": (
            "It is not a review step and adds no verdict; in auto, a pass recorded in the plan's dispatch record is "
            "reused across sessions and context compaction under the conditions the Dispatch record bullet below "
            "states, and in `off` the check runs again in each session.",
        ),
        "reference.zh-TW.md#最終檢查": (
            "它不是審查步驟，也不產生結論；在 auto 下，記錄在計畫派工紀錄中的通過，可依下方派工紀錄一項所說的條件，跨 session "
            "與 context 壓縮沿用，在 `off` 下則每個 session 都重新執行。",
        ),
    }

    # The README pair: each English sentence with its Chinese counterpart, in the same bullet of each README.
    README_PAIRS = (
        ("Counts stay in their session", "次數只屬於自己的 session",
         "A resumed session starts new counts.", "接續的 session 重新計數。"),
        ("Counts stay in their session", "次數只屬於自己的 session",
         "In auto, passes, Adversarial review results, final check runs and your decisions carry over in the plan's "
         "dispatch record, which main trusts as written, so an edit to it changes what main believes.",
         "在 auto 下，通過結果、對抗式審查結果、最終檢查的執行紀錄與你的決定透過計畫的派工紀錄延續，主 Agent 照紀錄所寫的內容採信，"
         "所以改動紀錄就會改變主 Agent 的認知。"),
        ("Counts stay in their session", "次數只屬於自己的 session",
         "A recorded final check pass is reused only while `HEAD` is the commit it ran at, the workspace and every "
         "claim's reading set are unchanged and its scope still covers what is needed; otherwise main runs the final "
         "check again, and an environment change after the run, such as an upgraded tool, is not detected.",
         "記錄下來的最終檢查通過，只在 `HEAD` 仍是它執行時的 commit、工作區與每個 claim 的閱讀範圍都沒有變動，且它的範圍仍涵蓋"
         "所需時才沿用；否則主 Agent 重跑最終檢查，而執行之後的環境變動（例如工具升級）不會被偵測到。"),
        ("Counts stay in their session", "次數只屬於自己的 session",
         "In `off`, a resumed session runs the final check again, and a claim that passed in an earlier session is "
         "reviewed again before landing.",
         "在 `off` 下，接續的 session 會重跑最終檢查，先前 session 通過的 claim 在合併前會再審一次。"),
    )

    # Sentences pinned above that this ticket keeps unchanged, so they also read so at the tag.
    KEPT = (
        "Once it has failed at a commit, that commit's state is failed, and a later pass at the same commit lets "
        "landing proceed only through an accept-and-land decision that names the failure.",
        "Only a call made after the final check passed at the commit to be landed, with the workspace equal to it, "
        "gives the claim's result; a result from an earlier or another commit, and an explicit call made before "
        "then, count as not run, so the claim needs accept and land or a new call.",
        "Main takes it as written, so an edit to it changes what main believes.",
        "Off mode writes none.",
    )

    def new_pins(self):
        return (self.RECORDED, self.ADVERSARIAL, self.REPORTED, self.RESUMED, self.LIMITS, self.CONTEXT, self.DOCUMENTS,
                {"review-state.md#Final check": self.OFF["review-state.md#Final check"],
                 self.RUNS: self.OFF[self.RUNS]})

    def test_each_run_is_recorded_after_its_reads_and_reused_only_under_s1(self):
        self.assert_pinned(self.RECORDED)

    def test_adversarial_review_after_a_recorded_pass_needs_a_later_automatic_call(self):
        self.assert_pinned(self.ADVERSARIAL)

    def test_a_reused_pass_is_named_with_its_time_in_the_decision_and_the_report(self):
        self.assert_pinned(self.REPORTED)

    def test_a_resumed_session_reuses_only_a_recorded_pass_that_meets_the_conditions(self):
        self.assert_pinned(self.RESUMED)

    def test_the_residual_risks_are_stated_where_the_rule_is(self):
        self.assert_pinned(self.LIMITS)

    def test_off_keeps_the_final_checks_state_from_this_session_only(self):
        # Fails if off loses the session-only state, the rerun after a compaction or the record that can only fail a
        # commit, or if any of them stops being scoped to off.
        self.assert_pinned(self.OFF)
        text = source("review-state.md#Final check")
        for unscoped in ("Its state comes only from main's own run in this session",
                         "A record can only make the state failed, never passed."):
            with self.subTest(unscoped=unscoped[:40]):
                self.assertNotRegex(text, rf"(?:^|(?<=\s)){re.escape(unscoped)}")

    def test_the_glossary_states_the_recorded_runs_and_the_reuse_condition(self):
        self.assert_pinned(self.CONTEXT)
        self.assertNotIn("the final check's state still come only from this session",
                         source("CONTEXT.md#Dispatch record"))

    def test_the_documents_describe_the_reuse_and_its_limits(self):
        self.assert_pinned(self.DOCUMENTS)

    def test_both_readmes_describe_the_reuse_in_paired_sentences(self):
        english = (config.ROOT / "README.md").read_text(encoding="utf-8")
        chinese = (config.ROOT / "README.zh-TW.md").read_text(encoding="utf-8")
        for label, label_zh, sentence, sentence_zh in self.README_PAIRS:
            with self.subTest(sentence=sentence[:40]):
                self.assert_whole_sentence(sentence, place_text(english, "README.md", label))
                self.assert_whole_sentence(sentence_zh, place_text(chinese, "README.zh-TW.md", label_zh))

    def test_the_recorded_runs_bullet_follows_the_final_check(self):
        text = source("review-state.md")
        validity = text.split("\n## Validity and completion\n", 1)[1].split("\n## ", 1)[0]
        bullets = [line.split("**")[1] for line in validity.splitlines() if line.startswith("- **")]
        self.assertEqual(bullets[bullets.index("Final check.") + 1], "Recorded final check runs.")

    def test_the_replaced_auto_statements_are_gone(self):
        # In auto, the final check's state no longer comes only from this session, and a resumed session no longer
        # runs the final check again whatever the record holds.
        for place, phrase in (
                ("review-state.md", "the Stop threshold in effect and the final check's state"),
                ("review-state.md", "so main runs the final check again in the new session before landing"),
                ("CONTEXT.md", "the Stop threshold in effect and the final check's state still come only from this "
                               "session"),
                ("README.md", "A resumed session starts new counts and runs the final check again."),
                ("README.zh-TW.md", "接續的 session 重新計數，並重跑最終檢查。"),
                ("reference.md", "Counts still restart in each session, and main runs the final check again before "
                                 "landing."),
                ("reference.zh-TW.md", "次數仍在每個 session 重新計算，主 Agent 也會在進入預設 branch 前重新執行最終檢查。")):
            with self.subTest(place=place, phrase=phrase[:40]):
                self.assertNotIn(phrase, source(place))

    def test_no_sentence_lets_a_pass_come_from_another_record(self):
        # S1: a pass comes only from main's own run or a recorded pass under its conditions; review state names the
        # records that never give one, and no shipped rule says a handoff, ticket, Follow-up record, role report or
        # compaction summary passes a final check.
        self.assertIn("never from a handoff, a ticket, the Follow-up record, a role's report or a compaction summary",
                      source(self.RUNS))
        pattern = re.compile(r"(?:handoff|ticket|Follow-up record|report|compaction summary)[^.]*\bmakes? (?:its|the|a) "
                             r"commit passed", re.I)
        for path in ("review-state.md", "adversarial-review.md", "CONTEXT.md"):
            with self.subTest(path=path):
                self.assertIsNone(pattern.search(source(path)))

    def test_every_new_pin_fails_on_the_v0_36_0_text(self):
        for pins in self.new_pins():
            for place, sentences in pins.items():
                path, _, label = place.partition("#")
                text = tagged(path)
                try:
                    text = place_text(text, path, label)
                except (KeyError, StopIteration):
                    continue
                for sentence in sentences:
                    with self.subTest(place=place, sentence=sentence[:60]):
                        if sentence in self.KEPT:
                            self.assertIn(sentence, text)
                        else:
                            self.assertNotIn(sentence, text)

    def test_every_off_pin_but_the_new_ones_matches_the_v0_36_0_text(self):
        # The off rules kept without change still read as they did at the tag.
        for place in ("review-state.md#Dispatch record", "review-state.md#Resumed sessions"):
            path, _, label = place.partition("#")
            text = place_text(tagged(path), path, label)
            for sentence in self.OFF[place]:
                with self.subTest(place=place, sentence=sentence[:60]):
                    self.assertIn(sentence, text)


if __name__ == "__main__":
    unittest.main()
