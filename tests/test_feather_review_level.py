"""Review level ticket 01 (docs/specs/review-level.md, Testing Decisions): in auto, the user chooses a Review level,
`standard`, `light` or `off`, for each Plan of Plan-driven work before its first Claim is implemented. Review state
defines it once: its three values; that `light` and `off` make the review mode off for that Plan's work; what `light`
adds to off, with its Code review counted as automatic calls, stopped at the Stop threshold and fixed after
CHANGES_REQUESTED; that a level in a ticket or spec is never the user's choice; the recommendation conditions; the stops
that ask for the level again; `standard` while the choice is unknown, except a level an Active handoff records; and that
main never changes the level on its own. Plan review's procedure asks it after classifying the Claims and after any
spec-or-tickets question, before plan review, and an instruction naming the level is the choice. The toggle's meaning
refers to review state. The glossary, both READMEs and both reference documents describe it, the READMEs and the
reference documents paired sentence for sentence. Tests check which sentences the shipped documents state, not how
main applies them.

Since docs/specs/review-level-content-condition.md, ticket 01, main recommends `light` by the content of a
Plan's Claims rather than for one Claim: the recommendation pins move to the new wording, the glossary carries it, ADR
0023 records its amendment by ADR 0024 and the one-Claim wording is gone.

The existing pins this ticket replaces, updated where they are: in test_feather_security_review, plan review's full
review flow sentence, the toggle's Meaning sentence on what `auto` gives plan-driven work, the glossary's Automatic
flow entry and the `/cc-feather:auto-on` lines of both READMEs; in test_feather_review_rules, both READMEs' switch
sentences on what enabled mode `auto` does."""

from __future__ import annotations

import unittest

from tests import feather_support
from tests.feather_support import config

REVIEW_STATE = config.ROOT / "skills" / "delegation" / "references" / "review-state.md"
PLAN_REVIEW = config.ROOT / "skills" / "delegation" / "references" / "plan-review.md"
# The Review level sections of the READMEs and the reference documents, by heading.
SECTIONS = {
    "README.md": ("README.md", "\n### Review level\n"),
    "README.zh-TW.md": ("README.zh-TW.md", "\n### 審查等級\n"),
    "reference.md": ("docs/reference.md", "\n### Review level\n"),
    "reference.zh-TW.md": ("docs/reference.zh-TW.md", "\n### 審查等級\n"),
}


def text(path) -> str:
    return (config.ROOT / path).read_text(encoding="utf-8")


def source(name: str) -> str:
    """'review-state.md#<label>' is review state's '- **<label>.**' bullet; 'plan-review.md' the procedure;
    'auto-review.md#Meaning' the toggle's Meaning section; 'CONTEXT.md#<term>' a glossary entry; '<README or
    reference>#section' its Review level section; a README name alone the whole README."""
    path, _, label = name.partition("#")
    if label == "section":
        document, heading = SECTIONS[path]
        return text(document).split(heading, 1)[1].split("\n#", 1)[0]
    return feather_support.review_rules_source(name)


def runtime_markdown() -> dict[str, str]:
    """Every runtime Markdown file under skills/, by repository path."""
    root = config.ROOT / "skills"
    return {path.relative_to(config.ROOT).as_posix(): path.read_text(encoding="utf-8")
            for path in sorted(root.rglob("*.md"))}


class ReviewLevelTests(unittest.TestCase):
    assert_whole_sentence = feather_support.stop_threshold_assert_whole_sentence

    def assert_pinned(self, pins):
        for place, sentences in pins.items():
            body = source(place)
            for sentence in sentences:
                with self.subTest(place=place, sentence=sentence[:60]):
                    self.assert_whole_sentence(sentence, body)

    # Review state's owner rule, one bullet per decision.
    OWNER = {
        "review-state.md#Levels": (
            "In auto, each Plan of Plan-driven work has a Review level that the user chooses before its first Claim is "
            "implemented, as plan review asks it: `standard`, `light` or `off`.",
            "At `standard` the Plan runs the Automatic flow.",
            "A choice of `light` or `off` is a task choice that makes the review mode off for that Plan's work, so the "
            "rules that hold only in auto, such as Classifying a request, Dispatch record, Per-claim timing, Commits "
            "before the passes and Auto land, do not apply to it, and every rule that holds in off does, including the "
            "classification of Security-critical claims, their security analysis and their routing to "
            "security-executor.",
            "`off` adds nothing to off mode, and `light` adds what Light adds below states.",
            "A level written in a ticket or spec is never the user's choice; it only informs main's recommendation.",
        ),
        "review-state.md#Light adds": (
            "At `light`, main does three things on its own.",
            "First, once a Claim is implemented, main requests its Code review from reviewer.",
            "Main's requests for it are automatic calls of that Claim's Code review under Call source, an exception to "
            "What an explicit call runs, where in off main runs code review only on an explicit request: they are "
            "counted under Consecutive non-pass count and Transitions, the Code review stops at the Stop threshold in "
            "effect, and its next call is made as Next automatic call states.",
            "After a CHANGES_REQUESTED, read the [code-review procedure](code-review.md)'s step 4 and follow it, then "
            "request the Code review again.",
            "An APPROVED does not start outcome verification.",
            "When the Code review stops at the Stop threshold without APPROVED, the Claim is unreviewed and the stop at "
            "the end lists it so; main writes no handoff note for it under the code-review procedure's step 6, and the "
            "acceptance gate covers it only when an Active handoff records it, as in off.",
            "Second, main runs every item of the Claim's acceptance as Execution allows and reports each observed "
            "result; an item it did not run is reported as not run, never as passed.",
            "Third, main makes the stop at the end below.",
            "`light` runs no final check of the Automatic flow; the final check that Final check requires in off before "
            "a landing or release the acceptance gate does not cover still runs.",
        ),
        # Stops-in-conversation ticket 01: the stop refers to review state's Asking in the conversation instead of saying
        # "without a question tool" itself.
        "review-state.md#The stop at the end": (
            "Once every Claim of a Plan at `light` has finished its Code review, with APPROVED or stopped, and its "
            "acceptance run, main stops in the conversation, as Asking in the conversation describes, listing for each "
            "Claim the Code "
            "review's verdict, the acceptance results and the open findings, then what is left, landing included, and "
            "that the ticket stays unfinished until the user accepts it or says it is done, as Ticket status and User "
            "decisions describe.",
            "Main lands a Plan at `light` only on the user's instruction.",
        ),
        "review-state.md#Recommending light": (
            # docs/specs/review-level-content-condition.md, ticket 01: by content, not by the number of Claims.
            "Main recommends `light` only for a Plan whose Claims each have a known cause, a small scope and "
            "acceptance that shows its outcome directly, none of which builds on another's design, as a Claim that "
            "lists another under `Blocked by` does, and none of which is a Security-critical claim, and that migrates "
            "no data, performs no irreversible operation, has no foreseeable resource risk and changes no shared test "
            "support or build configuration.",
            "The number of Claims does not decide it.",
        ),
        "review-state.md#Leaving light": (
            "When a Plan at `light` turns out to need a Security-critical change, or has a material Deviation, main "
            "stops the work and the user chooses the Plan's level again, with main recommending `standard`.",
            "A change of level is a change of review mode, so counts, verdicts and open findings carry over as What "
            "does not reset a count describes.",
        ),
        "review-state.md#Unknown level": (
            "Until the user's choice is known in the session, the level is `standard`.",
            "The exception is a level the user chose that an Active handoff records, which counts as known in a resumed "
            "session and after a context compaction; no other record, ticket, spec or compaction summary makes a level "
            "known.",
            "With an Active handoff, main records the chosen level in it.",
            "Without one, a context compaction that drops the choice returns the Plan to `standard`, and its "
            "implemented Claims follow Implemented before plan review.",
            "Main never raises or lowers a Plan's Review level on its own.",
        ),
    }

    # Plan review's ask, at the sentence where main states whether the work is plan-driven, and its full-flow sentence.
    STATED = ("Before implementing in auto, state in the reply whether the work is plan-driven and therefore reviewed, "
              "with a one-line reason; a skipped review is then a visible decision rather than a silent one.")
    ASK = ("For plan-driven work in auto, main then asks the user once for the plan's Review level, before its first "
           "claim is implemented: after classifying the plan's claims as below and after the user's answer to any "
           "question whether to implement a spec or its tickets, and before the plan's security analysis and plan "
           "review, main asks with AskUserQuestion, its recommended level as the first option with a one-line reason, "
           "as [review state](review-state.md)'s Review level describes.")
    NAMED = "A user instruction that already names the plan's level is the choice, and no question is asked."
    FULL_FLOW = ("In auto, plan-driven work gets the full review flow at Review level `standard`: plan review before "
                 "implementation, then [code review](code-review.md), then [outcome verification]"
                 "(outcome-verification.md), and for a Security-critical claim then [Adversarial review]"
                 "(adversarial-review.md).")

    # The toggle's meaning, referring to review state.
    MEANING = (
        "At Review level `standard`, `auto` gives plan-driven work, meaning work done from a plan, spec or ticket the "
        "user agreed to, automatic plan review, code review, outcome verification and then, for a Security-critical "
        "claim, Adversarial review before it is reported complete.",
        "In `auto`, the user chooses a Review level, `standard`, `light` or `off`, for each plan of plan-driven work "
        "before its first claim is implemented, as [review state](../../delegation/references/review-state.md)'s "
        "Review level describes.",
    )

    # The glossary entries that say the Automatic flow runs at `standard`.
    GLOSSARY = {
        "CONTEXT.md#Plan-driven work": (
            "In auto mode it is the only work that gets the automatic review flow, which it gets at Review level "
            "`standard`.",
        ),
        "CONTEXT.md#Automatic flow": (
            "The sequence plan review, then code review, then outcome verification, and for a Security-critical claim "
            "then Adversarial review, that auto mode applies to Plan-driven work at Review level `standard`.",
        ),
    }

    def test_review_state_defines_the_review_level(self):
        self.assert_pinned(self.OWNER)

    def test_review_level_is_a_section_of_review_state_after_the_transitions(self):
        body = REVIEW_STATE.read_text(encoding="utf-8")
        self.assertEqual(body.count("\n## Review level\n"), 1)
        self.assertLess(body.index("\n## Transitions\n"), body.index("\n## Review level\n"))
        self.assertLess(body.index("\n## Review level\n"), body.index("\n## Completion criteria\n"))
        section = body.split("\n## Review level\n", 1)[1].split("\n## ", 1)[0]
        for label in self.OWNER:
            with self.subTest(label=label):
                self.assertIn(f"- **{label.partition('#')[2]}.**", section)

    def test_the_explicit_call_rule_it_is_an_exception_to_is_unchanged(self):
        self.assert_whole_sentence(
            "In off, main runs code review or outcome verification only on an explicit request, and may offer it.",
            source("review-state.md#What an explicit call runs"))

    def test_no_other_runtime_file_restates_the_rule(self):
        # Phrases only the owner states; every other runtime file under skills/ refers to review state.
        owner = REVIEW_STATE.relative_to(config.ROOT).as_posix()
        files = runtime_markdown()
        self.assertIn(owner, files)
        for phrase in ("Main recommends `light` only for", "is never the user's choice", "without a question tool",
                       "Until the user's choice is known in the session", "Main never raises or lowers a Plan's Review "
                       "level", "Main lands a Plan at `light` only", "with main recommending `standard`"):
            for path, body in files.items():
                with self.subTest(phrase=phrase, path=path):
                    self.assertEqual(body.count(phrase), 1 if path == owner else 0)

    def test_plan_review_asks_the_level_where_main_states_the_work_is_plan_driven(self):
        body = PLAN_REVIEW.read_text(encoding="utf-8")
        for sentence in (self.STATED, self.ASK, self.NAMED, self.FULL_FLOW):
            with self.subTest(sentence=sentence[:60]):
                self.assert_whole_sentence(sentence, body)
                self.assertEqual(body.count(sentence), 1)
        # The ask follows the statement directly, and the named level follows the ask.
        self.assertIn(self.STATED + " " + self.ASK + " " + self.NAMED, body)
        # It comes after the spec-or-tickets question and the classification, and before plan review.
        self.assertIn("after classifying the plan's claims", self.ASK)
        self.assertIn("after the user's answer to any question whether to implement a spec or its tickets", self.ASK)
        self.assertIn("before the plan's security analysis and plan review", self.ASK)
        self.assertIn("its recommended level as the first option with a one-line reason", self.ASK)

    def test_the_toggle_meaning_refers_to_review_state(self):
        body = source("auto-review.md#Meaning")
        for sentence in self.MEANING:
            with self.subTest(sentence=sentence[:60]):
                self.assert_whole_sentence(sentence, body)

    def test_the_glossary_says_the_automatic_flow_runs_at_standard(self):
        self.assert_pinned(self.GLOSSARY)
        self.assertIn("**Review level**", text("CONTEXT.md"))

    # Both READMEs, paired sentence for sentence: what auto covers, then the Review level section.
    README_PAIRS = (
        ("README.md",
         "- `/cc-feather:auto-on`: enable automatic plan review, code review, outcome verification and, for "
         "Security-critical claims, Adversarial review of plan-driven work, the Automatic flow, which runs at [Review "
         "level](#review-level) `standard` unless you choose another level for a plan.",
         "| `/cc-feather:auto-on` | 開啟依計畫施工的自動計畫審查、程式碼審查、結果驗證，以及安全關鍵 claim 的對抗式審查，也就是自動流程，"
         "除非你為某份計畫選了其他等級，它都以[審查等級](#審查等級) `standard` 執行；"),
        ("README.md",
         "The steps below are the Automatic flow, which runs at [Review level](#review-level) `standard`, the level a "
         "plan has unless you choose another for it.",
         "下面的步驟就是自動流程，以[審查等級](#審查等級) `standard` 執行，這是計畫在你沒有另選等級時的等級。"),
        ("README.md",
         "enabled mode `auto` runs the Automatic flow on plan-driven work at [Review level](#review-level) `standard`, "
         "unless you choose another level for a plan, and at that level lets main, without asking, commit its claims "
         "before their passes,",
         "開啟後的 `auto` 以[審查等級](#審查等級) `standard` 對依計畫施工的工作執行自動流程（除非你為某份計畫選了其他等級），並在這個"
         "等級下讓主 Agent 不經詢問，在 claim 通過前先 commit、"),
    )

    README_SECTION = (
        ("In auto, before the first claim of a plan is implemented, main recommends a Review level for that plan with a "
         "one-line reason and asks you to choose one, its recommendation first.",
         "在 auto 下，計畫的第一個 claim 實作之前，主 Agent 會為這份計畫建議一個審查等級（Review level）並附上一行理由，請你選擇，"
         "建議的選項排在第一個。"),
        ("`standard` runs the Automatic flow above.",
         "`standard` 執行上面的自動流程。"),
        ("`light` turns automatic review off for that plan and adds three things main does on its own: once a claim is "
         "implemented, it asks reviewer for the claim's code review, fixes the findings of a CHANGES_REQUESTED and asks "
         "again, until the review passes or stops at the [Stop threshold](#stop-threshold); it runs every item of the "
         "claim's acceptance and reports each observed result, an item it did not run as not run; and it then stops in "
         "the conversation, without a question, listing the review's verdict, the acceptance results, the open findings "
         "and what is left, landing included.",
         "`light` 對這份計畫關閉自動審查，並加上三件主 Agent 自行做的事：claim 實作完後，請 reviewer 審查這個 claim 的程式碼，"
         "收到 CHANGES_REQUESTED 就修正發現的問題再請它審查，直到審查通過或在[停止門檻](#停止門檻)停下；執行 claim 驗收的每一項並"
         "回報每項實際觀察到的結果，沒執行的項目回報為未執行；之後在對話中停下，不用提問，列出審查結論、驗收結果、未解決的發現與剩下的"
         "工作，包括合併。"),
        ("`off` turns automatic review off for that plan.",
         "`off` 對這份計畫關閉自動審查。"),
        # docs/specs/review-level-content-condition.md, ticket 01.
        ("Main recommends `light` only for a plan whose claims each have a known cause, a small scope and acceptance "
         "that shows its outcome directly, none of which builds on another's design, as a claim blocked by another "
         "does, and none of which is Security-critical, and that migrates no data, performs no irreversible "
         "operation, has no foreseeable resource risk and changes no shared test support or build configuration.",
         "主 Agent 只在計畫的每個 claim 都原因已知、範圍小、驗收能直接顯示結果，沒有任何 claim 建立在另一個 claim 的設計上（例如被另一個 "
         "claim 阻擋的 claim），也沒有任何 claim 是安全關鍵，而且整份計畫不遷移資料、沒有不可逆操作、沒有可預見的資源風險，也不改共用的"
         "測試支援或建置設定時，才建議 `light`。"),
        ("A plan at `light` carries across sessions only through an active handoff, its ticket stays unfinished until "
         "you accept it or say it is done, and it lands only on your instruction.",
         "`light` 的計畫只透過進行中的交接跨 session 延續，它的 ticket 在你接受或說它完成之前都維持未完成，而且只在你下令時才合併。"),
        ("Every rule `off` keeps still holds, including the security analysis of Security-critical work and its routing "
         "to security-executor.",
         "`off` 保有的每條規則仍然適用，包括安全關鍵工作的安全分析與交給 security-executor。"),
    )
    # Sentences of the README section that do not end at a Chinese full stop in their pair are pinned as substrings.
    README_SECTION_PARTS = (
        ("A level you name yourself, as in \"implement ticket 03 at light\", is your choice and no question is asked; a "
         "level written in a ticket or spec only informs the recommendation.",
         "你自己指定的等級，例如「用 light 實作 ticket 03」，就是你的選擇，不會再問；寫在 ticket 或 spec 裡的等級只作為建議的參考。"),
        ("`light` gives up what `off` gives up: plan review, outcome verification, the final check as a recorded gate, "
         "the dispatch record, Auto land and the acceptance gate, which covers a claim at `light` only when an active "
         "handoff records it.",
         "`light` 放棄的與 `off` 相同：計畫審查、結果驗證、作為記錄關卡的最終檢查、派工紀錄、自動合併，以及把關；`light` 下的 claim 只有"
         "在進行中的交接記錄它時才受把關。"),
        ("Main never raises or lowers the level on its own: while your choice is not known in the session, for example "
         "after a context compaction when no active handoff records it, the level is `standard`, and when a plan at "
         "`light` turns out to need a Security-critical change or has a material deviation, main stops and you choose "
         "its level again.",
         "主 Agent 絕不自行調高或調低等級：在這個 session 還不知道你的選擇時，例如 context 壓縮後沒有進行中的交接記錄它，等級就是 "
         "`standard`；`light` 的計畫若發現需要安全關鍵變更或出現重大偏離，主 Agent 會停下，由你重新選擇它的等級。"),
        ("The rule is review state's Review level, and the [reference](docs/reference.md#review-level) explains why.",
         "規則是審查狀態規則的 Review level，[參考文件](docs/reference.zh-TW.md#審查等級)說明原因。"),
    )

    def test_readmes_say_auto_runs_the_automatic_flow_at_standard_in_both_languages(self):
        for _, english, chinese in self.README_PAIRS:
            with self.subTest(sentence=english[:60]):
                self.assertEqual(text("README.md").count(english), 1)
                self.assertEqual(text("README.zh-TW.md").count(chinese), 1)

    def test_readmes_explain_the_three_levels_in_both_languages(self):
        english, chinese = source("README.md#section"), source("README.zh-TW.md#section")
        for en, zh in self.README_SECTION:
            with self.subTest(sentence=en[:60]):
                self.assert_whole_sentence(en, english)
                self.assert_whole_sentence(zh, chinese)
        for en, zh in self.README_SECTION_PARTS:
            with self.subTest(sentence=en[:60]):
                self.assert_whole_sentence(en, english)
                self.assertEqual(chinese.count(zh), 1)
        # The section sits with the automatic review rules, before Security-critical work, in both languages.
        for name, heading, after in (("README.md", "\n### Review level\n", "\n### Security-critical work\n"),
                                     ("README.zh-TW.md", "\n### 審查等級\n", "\n### 安全關鍵工作\n")):
            with self.subTest(readme=name):
                body = text(name)
                self.assertEqual(body.count(heading), 1)
                self.assertLess(body.index(heading), body.index(after))

    # Both reference documents, paired sentence for sentence.
    REFERENCE = (
        ("In auto, each plan of plan-driven work gets a Review level that you choose before its first claim is "
         "implemented: `standard`, the Automatic flow; `light`; or `off`, automatic review off for that plan.",
         "在 auto 下，每份依計畫施工的計畫都有一個審查等級（Review level），由你在它的第一個 claim 實作之前選擇：`standard` 是自動流程；"
         "`light`；或 `off`，也就是對這份計畫關閉自動審查。"),
        ("A small fix with a known cause, once written as a ticket, would otherwise wait for every step of the "
         "Automatic flow, so `light` lets it finish with one independent check while the choice stays yours.",
         "原因已知的小修正一旦寫成 ticket，原本就得等自動流程的每一步，所以 `light` 讓它只經過一次獨立檢查就能完成，而選擇權仍在你手上。"),
        ("Main recommends a level with a one-line reason and asks with its recommendation first; a level you name in "
         "your own instruction is your choice, while a level written in a ticket or spec only informs the "
         "recommendation, so a document cannot lower the review of your work on its own.",
         "主 Agent 會建議一個等級並附上一行理由，提問時把建議放在第一個；你在自己的指示中指定的等級就是你的選擇，寫在 ticket 或 spec "
         "裡的等級只作為建議的參考，所以文件無法自行降低你工作的審查。"),
        ("`light` is `off` for that plan plus three things main does on its own: it asks reviewer for each implemented "
         "claim's code review, counted as automatic calls so that a review that keeps failing stops at the [Stop "
         "threshold](#stop-threshold), fixing the findings of a CHANGES_REQUESTED before asking again; it runs every "
         "item of the claim's acceptance and reports each observed result, an item it did not run as not run; and it "
         "then stops in the conversation without a question tool, listing the review's verdict, the acceptance "
         "results, the open findings and what is left, landing included.",
         "`light` 就是對這份計畫用 `off`，再加上三件主 Agent 自行做的事：它請 reviewer 審查每個實作完的 claim 的程式碼，這些呼叫算作"
         "自動呼叫，所以一直沒通過的審查會在[停止門檻](#停止門檻)停下，收到 CHANGES_REQUESTED 時先修正發現的問題再請它審查；它執行 "
         "claim 驗收的每一項並回報每項實際觀察到的結果，沒執行的項目回報為未執行；之後它在對話中停下，不用提問工具，列出審查結論、驗收"
         "結果、未解決的發現與剩下的工作，包括合併。"),
        ("It stops without a question tool because a pending question you dismiss still makes the model run again, "
         "while a turn that ends in the conversation lets you leave with `/clear` or a new session.",
         "它不用提問工具停下，是因為你略過的待回答問題仍會讓模型再跑一次，而在對話中結束的回合讓你可以用 `/clear` 或新的 session 離開。"),
        # docs/specs/review-level-content-condition.md, ticket 01.
        ("Main recommends `light` only for a plan whose claims each have a known cause, a small scope and acceptance "
         "that shows its outcome directly, none of which builds on another's design, as a claim blocked by another "
         "does, and none of which is Security-critical, and that migrates no data, performs no irreversible "
         "operation, has no foreseeable resource risk and changes no shared test support or build configuration, "
         "since those are the fixes whose failure is cheap.",
         "主 Agent 只在計畫的每個 claim 都原因已知、範圍小、驗收能直接顯示結果，沒有任何 claim 建立在另一個 claim 的設計上（例如被另一個 "
         "claim 阻擋的 claim），也沒有任何 claim 是安全關鍵，而且整份計畫不遷移資料、沒有不可逆操作、沒有可預見的資源風險，也不改共用的"
         "測試支援或建置設定時，才建議 `light`，因為這些是失敗代價小的修正。"),
        ("The number of claims does not decide it.", "計畫有幾個 claim 不是判斷依據。"),
        ("`light` gives up plan review, outcome verification, the final check as a recorded gate, the dispatch record, "
         "Auto land and the acceptance gate beyond a claim an active handoff records, exactly as `off` does, and keeps "
         "every rule `off` keeps, including the security analysis of Security-critical work and its routing to "
         "security-executor.",
         "`light` 放棄計畫審查、結果驗證、作為記錄關卡的最終檢查、派工紀錄、自動合併，以及進行中的交接所記錄的 claim 以外的把關，與 "
         "`off` 完全相同，並保有 `off` 保有的每條規則，包括安全關鍵工作的安全分析與交給 security-executor。"),
        ("The rule is [review state](../skills/delegation/references/review-state.md)'s Review level, and the "
         "[plan-review procedure](../skills/delegation/references/plan-review.md) asks the question; see [ADR "
         "0023](adr/0023-a-plans-review-level-is-the-users-choice.md).",
         "規則是[審查狀態規則](../skills/delegation/references/review-state.md)的 Review level，由[計畫審查流程]"
         "(../skills/delegation/references/plan-review.md)提問；見 [ADR 0023](adr/0023-a-plans-review-level-is-the-users-choice.md)。"),
    )
    REFERENCE_PARTS = (
        ("Main never raises or lowers the level on its own: while your choice is not known in the session the level is "
         "`standard`, unless an active handoff records your choice, so losing the answer costs reviews but never "
         "removes them, and a plan at `light` that turns out to need a Security-critical change or has a material "
         "deviation stops for you to choose its level again.",
         "主 Agent 絕不自行調高或調低等級：在這個 session 還不知道你的選擇時，等級就是 `standard`，除非進行中的交接記錄了你的選擇，"
         "所以遺失回答只會多花審查，絕不會少掉審查；`light` 的計畫若發現需要安全關鍵變更或出現重大偏離，會停下來由你重新選擇它的等級。"),
    )

    def test_reference_documents_explain_the_three_levels_in_both_languages(self):
        english, chinese = source("reference.md#section"), source("reference.zh-TW.md#section")
        for en, zh in self.REFERENCE:
            with self.subTest(sentence=en[:60]):
                self.assert_whole_sentence(en, english)
                self.assert_whole_sentence(zh, chinese)
        for en, zh in self.REFERENCE_PARTS:
            with self.subTest(sentence=en[:60]):
                self.assert_whole_sentence(en, english)
                self.assertEqual(chinese.count(zh), 1)
        # The section sits in the Automatic review part, before Security-critical work, in both languages.
        for name, heading, after in (("docs/reference.md", "\n### Review level\n", "\n### Security-critical work\n"),
                                     ("docs/reference.zh-TW.md", "\n### 審查等級\n", "\n### 安全關鍵工作\n")):
            with self.subTest(reference=name):
                body = text(name)
                self.assertEqual(body.count(heading), 1)
                self.assertLess(body.index(heading), body.index(after))

    def test_light_is_recommended_by_content_not_by_the_number_of_claims(self):
        """docs/specs/review-level-content-condition.md, ticket 01: the glossary carries the owner's condition, ADR
        0023 records its amendment by ADR 0024, and the one-Claim wording is gone."""
        glossary = source("CONTEXT.md#Review level")
        for sentence in self.OWNER["review-state.md#Recommending light"]:
            with self.subTest(sentence=sentence[:60]):
                self.assert_whole_sentence(sentence, glossary)
        self.assertIn("(Amended by ADR 0024: main recommends `light` by the content of a Plan's Claims, each with a "
                      "known cause, a small scope and acceptance that shows its outcome directly, none building on "
                      "another's design and none Security-critical, under the same Plan-wide conditions; the number of "
                      "Claims does not decide it.)",
                      text("docs/adr/0023-a-plans-review-level-is-the-users-choice.md"))
        self.assertTrue((config.ROOT / "docs" / "adr" / "0024-light-is-recommended-by-content-not-by-claim-count.md")
                        .is_file())
        for path, old in (("skills/delegation/references/review-state.md", "a Plan of one Claim"),
                          ("CONTEXT.md", "a Plan of one Claim"), ("README.md", "a plan of one claim"),
                          ("docs/reference.md", "a plan of one claim"), ("README.zh-TW.md", "只有一個 claim"),
                          ("docs/reference.zh-TW.md", "只有一個 claim")):
            with self.subTest(path=path):
                self.assertNotIn(old, text(path))

    def test_every_link_from_the_level_sections_resolves(self):
        targets = {
            "README.md": (("#review-level", "\n### Review level\n", "docs/reference.md"),),
            "README.zh-TW.md": (("#審查等級", "\n### 審查等級\n", "docs/reference.zh-TW.md"),),
        }
        for readme, ((anchor, heading, reference),) in targets.items():
            with self.subTest(readme=readme):
                self.assertIn(anchor, source(f"{readme}#section"))
                self.assertEqual(text(reference).count(heading), 1)
        for name in ("reference.md", "reference.zh-TW.md"):
            for link in ("../skills/delegation/references/review-state.md",
                         "../skills/delegation/references/plan-review.md",
                         "adr/0023-a-plans-review-level-is-the-users-choice.md"):
                with self.subTest(reference=name, link=link):
                    self.assertIn(f"]({link})", source(f"{name}#section"))
                    self.assertTrue((config.ROOT / "docs" / link).resolve().is_file(), link)


if __name__ == "__main__":
    unittest.main()
