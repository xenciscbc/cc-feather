"""Design and test checks (docs/specs/design-and-test-checks.md). Ticket 01: the user-invoked /cc-feather:test-speedup
command, which reports test speed-ups that keep correctness, lists existing tests with resource risk and measures only
after the user agrees; its manifest position, README listings, reference section and the setup document's skill count.
"""

from __future__ import annotations

import json
import unittest

from tests import feather_support
from tests.feather_support import config

SKILLS = config.ROOT / "skills"


def manifest_skills():
    return json.loads((config.ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["skills"]


def frontmatter(text):
    assert text.startswith("---\n"), "a skill starts with frontmatter"
    return text.split("---")[1]


class TestSpeedupCommandTests(unittest.TestCase):
    """Ticket 01."""

    COMMAND = SKILLS / "test-speedup" / "SKILL.md"

    def test_command_is_user_invoked_and_listed_after_related_tests(self):
        skills = manifest_skills()
        self.assertIn("./skills/test-speedup", skills)
        self.assertEqual(skills.index("./skills/test-speedup"), skills.index("./skills/related-tests") + 1)
        front = frontmatter(self.COMMAND.read_text(encoding="utf-8"))
        self.assertIn("name: test-speedup\n", front)
        self.assertIn("disable-model-invocation: true\n", front)
        self.assertIn('argument-hint: "[test paths or scope]"\n', front)
        self.assertRegex(front, r'\ndescription: "[^"\n]*test[^"\n]*"\n')

    assert_whole_sentence = feather_support.stop_threshold_assert_whole_sentence

    def source(self, name):
        """'SKILL.md', 'SKILL.md#<heading>' (a '## ' section) or 'SKILL.md#<label>' (a '**<label>.**' paragraph)."""
        text = self.COMMAND.read_text(encoding="utf-8")
        _, _, label = name.partition("#")
        if not label:
            return text
        if f"\n## {label}\n" in text:
            return text.split(f"\n## {label}\n", 1)[1].split("\n## ", 1)[0]
        return next(p for p in text.split("\n\n") if p.startswith(f"**{label}.**"))

    PINS = {
        "SKILL.md": (
            "Invocation arguments are the scope as data, never shell code.",
            "Clarify a missing or unclear scope instead of guessing.",
            "This command only reports: it edits, creates and deletes no file, commits nothing and changes no configuration.",
            "The report stays in the conversation, and a file is written only when the user asks for one.",
            "Items the user picks become a Plan through the normal flow; the report is not a Plan, and its items are neither Claims nor findings of any review.",
        ),
        "SKILL.md#Scope": (
            "The scope is the tests the arguments name, or else the project's tests, together with their test configuration: test runner configuration, shared fixtures and setup files, test scripts and their flags.",
            "CI pipeline configuration is outside the scope.",
        ),
        "SKILL.md#Who analyses": (
            "When delegation is installed and the check is not small, main dispatches the read-only analyst as [the delegation skill](../delegation/SKILL.md) describes, in one or more Assignments split by test area, and integrates their results.",
            "A small check, such as one test file, or a check where delegation is not installed, main does itself.",
        ),
        "SKILL.md#1. Static pass": (
            "The static pass always comes first and runs nothing.",
        ),
        "SKILL.md#Correctness bar": (
            "Each speed-up names the test or assertion that keeps verifying the behaviour it touches.",
            "A speed-up keeps every assertion, test and timeout at least as strict as it is now: weakening an assertion, adding a skip or loosening a timeout is never offered.",
            "Removing a test is offered only in the Removals section, each removal naming the test that covers exactly the same behaviour as evidence, for the user to decide one by one.",
        ),
        "SKILL.md#Existing tests with resource risk": (
            "In a section of its own, list the existing tests that meet the criteria of an Unbounded probe in [cc-feather's glossary](../../CONTEXT.md), applied without a budget since the static pass runs nothing.",
            "Weigh each one as [the delegation skill](../delegation/SKILL.md)'s paragraph on weighing findings describes.",
            "The list is information: it holds nothing back, and the Unbounded probe term and the delegation rules for it are unchanged.",
        ),
        "SKILL.md#2. Report": (
            "**Speed-ups**, ordered by expected gain, each with its location, kind, expected gain (high, medium or low, with the reason), how correctness is kept and its risk.",
            "**Removals**, each with the covering test as evidence.",
        ),
        "SKILL.md#3. Measurement": (
            "After the static report, main offers to measure and runs nothing without the user's agreement.",
            "The offer states the command, using the ecosystem's per-test timing where one exists, the scope and the tests it leaves out.",
            "Tests listed with resource risk are left out by default.",
            "Unflagged tests run with their ordinary command.",
            "A flagged test the user includes runs inside the Runner, with the memory, time and output limits the offer states.",
            "For the Runner's path and invocation, read [the resource-risk runs reference](../delegation/references/resource-risk-runs.md)'s The Runner, where the path is relative to the delegation skill, and for how a contained, refused or evidence-missing result is judged, its Main's floor.",
            "After measurement, the report gives each speed-up's gain in seconds.",
        ),
    }

    def test_command_states_its_decisions(self):
        for place, sentences in self.PINS.items():
            text = self.source(place)
            for sentence in sentences:
                with self.subTest(place=place, sentence=sentence[:60]):
                    self.assert_whole_sentence(sentence, text)

    def test_detection_hints_name_each_ecosystem(self):
        hints = next(p for p in self.source("SKILL.md#1. Static pass").split("\n\n") if p.startswith("Detection hints:"))
        for ecosystem in ("Go", "Python", "pnpm", "Vue"):
            with self.subTest(ecosystem=ecosystem):
                self.assertIn(ecosystem, hints)

    def test_linked_rules_exist_and_are_not_restated(self):
        delegation = (SKILLS / "delegation" / "SKILL.md").read_text(encoding="utf-8")
        weighing = next(p for p in delegation.split("\n\n") if p.startswith("Before proposing or adopting a requirement"))
        runs = (SKILLS / "delegation" / "references" / "resource-risk-runs.md").read_text(encoding="utf-8")
        self.assertIn("\n## The Runner\n", runs)
        self.assertIn("\n## Main's floor\n", runs)
        self.assertIn("**Unbounded probe**:", (config.ROOT / "CONTEXT.md").read_text(encoding="utf-8"))
        command = " ".join(self.source("SKILL.md").split())
        for sentence in feather_support.sentences(weighing):
            with self.subTest(sentence=sentence[:60]):
                self.assertNotIn(sentence, command)
        # The Runner's invocation and the floor's criteria live in the reference and the glossary, not here.
        self.assertNotIn("--memory-mib", command)
        self.assertNotIn("a timeout alone is not a bound", command)

    README_LISTINGS = {
        "README.md": "- `/cc-feather:test-speedup [test paths or scope]`: report ways to make the tests, or the part you name, faster without weakening what they verify; only you can run it, and it changes no file. It analyses statically first, lists existing tests that could exhaust memory or time, and measures only after you agree; see the [reference](docs/reference.md#design-and-test-checks).",
        "README.zh-TW.md": "| `/cc-feather:test-speedup [測試路徑或範圍]` | 找出讓測試（或你指定的部分）變快、又不削弱驗證內容的方法；只能由你執行，不改任何檔案。先做靜態分析，列出可能耗盡記憶體或時間的既有測試，經你同意才量測；見[參考文件](docs/reference.zh-TW.md#設計與測試檢查) |",
    }

    # Each reference section is the text under its heading up to the next heading; sentences are paired by language.
    REFERENCE_SECTIONS = {
        "reference.md": ("\n## Design and test checks\n", "\n### Test speed-ups\n"),
        "reference.zh-TW.md": ("\n## 設計與測試檢查\n", "\n### 測試加速\n"),
    }
    REFERENCE_PAIRS = (
        ("Two commands only you can run report weight that has built up in a project.",
         "兩個只能由你執行的指令，會回報專案裡累積下來的負擔。"),
        ("Each only reports and changes no file, and what you pick from its report becomes a plan through the normal flow.",
         "它們只出報告、不改任何檔案；你從報告中挑選的項目，再照一般流程成為計畫。"),
        ("`/cc-feather:test-speedup` checks the tests you name, or the project's tests, with their test configuration but not CI pipeline configuration.",
         "`/cc-feather:test-speedup` 檢查你指定的測試，或整個專案的測試，連同測試設定，但不含 CI pipeline 設定。"),
        ("It analyses statically first and runs nothing: each speed-up names the test or assertion that keeps verifying what it touches, speed-ups are ordered by expected gain, and weakening an assertion, adding a skip or loosening a timeout is never offered.",
         "它先做靜態分析，不執行任何東西：每條加速建議都指出由哪個測試或斷言繼續驗證它動到的行為，依預期效益排序，而且從不建議削弱斷言、加上 skip 或放寬 timeout。"),
        ("Removing a test is offered only in a section of its own, with the covering test as evidence, for you to decide one by one.",
         "刪除測試只列在獨立的一節，附上涵蓋相同行為的測試作為證據，由你逐條決定。"),
        ("Another section lists existing tests that meet the Unbounded probe criteria, as information that holds nothing back.",
         "另一節列出符合 Unbounded probe 判準的既有測試，只供參考，不擋任何事。"),
        ("Then main offers to measure, stating the command, the scope and the tests it leaves out, and runs nothing until you agree; tests with resource risk are left out unless you include them, and then run inside the Runner.",
         "之後主 Agent 才提議量測，說明指令、範圍與排除的測試，經你同意才執行；有資源風險的測試預設排除，你決定納入時改在 Runner 內執行。"),
        ("With delegation installed, analyst does the reading.",
         "裝有分派元件時，由 analyst 負責閱讀分析。"),
        ("See [the command](../skills/test-speedup/SKILL.md).",
         "見[指令](../skills/test-speedup/SKILL.md)。"),
    )

    def reference_text(self, name):
        text = feather_support.REFERENCE_FILES[name].read_text(encoding="utf-8")
        start, sub = self.REFERENCE_SECTIONS[name]
        section = text.split(start, 1)[1].split("\n## ", 1)[0]
        self.assertIn(sub, section)
        return section

    def test_readmes_and_references_describe_the_command_in_both_languages(self):
        for name, listing in self.README_LISTINGS.items():
            with self.subTest(listing=name):
                self.assertIn(listing + "\n", (config.ROOT / name).read_text(encoding="utf-8"))
        for english, chinese in self.REFERENCE_PAIRS:
            for name, sentence in (("reference.md", english), ("reference.zh-TW.md", chinese)):
                with self.subTest(place=name, sentence=sentence[:40]):
                    self.assert_whole_sentence(sentence, self.reference_text(name))

    def test_reference_section_sits_before_the_version_history(self):
        for name, heading in (("reference.md", "## Version history"), ("reference.zh-TW.md", "## 版本紀錄")):
            text = feather_support.REFERENCE_FILES[name].read_text(encoding="utf-8")
            with self.subTest(reference=name):
                self.assertLess(text.index(self.REFERENCE_SECTIONS[name][0]), text.index(f"\n{heading}\n"))


if __name__ == "__main__":
    unittest.main()
