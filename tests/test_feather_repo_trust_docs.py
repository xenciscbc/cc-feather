"""Repo trust split ticket 03 (docs/specs/repo-trust-split.md, Acceptance items 14 to 16, Security invariants S1, S2
and S8): the decision record and the documents. ADR 0016 records the decision, its rejected options and its residual
risks; ADR 0011 and 0014 carry a superseded note and ADR 0009, 0013 and 0015 amended notes, with no earlier text
rewritten; the glossary's Trusted repository entry replaces Repository-chosen program; both READMEs and both references
open their Repository safety sections with the bold statement and list every residual risk, and their roles tables,
step table, design trade-offs and the references' commit and worktree sentences lose the repository safety wording.
Absence pins cover the READMEs, the references, docs/setup.md and CONTEXT.md outside their update sections, and
repo-check, which this release dropped, under skills/ and templates/ as well. Following the conventions of
tests/test_feather_repo_trust.py, every new presence pin fails on the text at tag v0.28.0 and every absence pin of
removed text matches it there."""

from __future__ import annotations

import re
import unittest

from tests.feather_support import config
from tests.test_feather_repo_trust import current_tree, normalised, tagged_blob

ROOT = config.ROOT
ADR = ROOT / "docs" / "adr"
ADR_0016 = "0016-delegation-trusts-the-repository.md"

DOCUMENTS = {
    "README.md": "\n## Updates and validation\n",
    "README.zh-TW.md": "\n## 更新、移除與驗證\n",
    "docs/reference.md": "\n## Version history\n",
    "docs/reference.zh-TW.md": "\n## 版本紀錄\n",
    "docs/setup.md": None,
    "CONTEXT.md": None,
}
SAFETY_HEADINGS = {
    "README.md": "### Repository safety",
    "README.zh-TW.md": "### 儲存庫安全",
    "docs/reference.md": "### Repository safety",
    "docs/reference.zh-TW.md": "### 儲存庫安全",
}
ENGLISH = ("README.md", "docs/reference.md")
CHINESE = ("README.zh-TW.md", "docs/reference.zh-TW.md")

BOLD = {
    "en": ("**Delegation assumes that the repository is trusted, and reviews run its code on this machine. Saying where a "
           "change comes from, such as that it is another person's pull request, branch or patch, no longer stops that: "
           "to stop it, say in your own message that the code must not run, or name what must not run. cc-feather "
           "offers no check of a repository before you trust it, so deciding whether to trust one, for example after "
           "downloading or copying someone else's, is yours.**"),
    "zh": ("**分派假設儲存庫是受信任的，審查會在這台機器上執行它的程式碼。說明變更從哪裡來（例如它是別人的 pull request、branch 或 "
           "patch）已經不會阻止這件事：要阻止，請在你自己的訊息中說程式碼不得執行，或指出哪些不得執行。cc-feather 不提供在你信任"
           "儲存庫之前檢查它的功能，所以要不要信任一個儲存庫（例如下載或複製別人的儲存庫之後）由你決定。**"),
}
# Acceptance 16's residual risks, in its order, in both languages.
RISKS = {
    "en": (
        "Repository content can steer main and the roles, by its `CLAUDE.md`, comments, commit messages or anything "
        "else they read: a role can be led to report a change's security problem as pre-existing or as inference, and "
        "main can be led to run code a restriction covers, since a restriction is itself an instruction to main.",
        "Reviews and the final check run the repository's code on this machine, and main's and the roles' Git commands "
        "(`git status` before and after every call, the roles' reads, `git add`, commit and push) run the programs the "
        "repository's Git configuration, attributes and hooks select, including hooks in a tracked directory and the "
        "filters `git status` runs, whether or not a restriction is in force. That code can change anything you can, "
        "including your own Git configuration, other worktrees and Feather's own records.",
        "A restriction governs reviews and the final check, not implementation: executor and security-executor may run "
        "the repository's code while implementing, also while fixing someone else's change.",
        "Nothing in cc-feather asks before code runs; what remains is Claude Code's folder trust and your permission "
        "settings.",
        "An isolated environment you named stays available under a general restriction unless the restriction says "
        "otherwise; if it holds secrets, such as a CI runner, the code runs there.",
        "Ignored files, and files marked assume-unchanged or skip-worktree, are not part of the workspace check, so such "
        "a file can affect a review or the final check.",
        "Claude Code loads the project's `CLAUDE.md` and `.claude` settings, and runs the hooks in those settings, when "
        "a session starts in the project, so a repository can act before any review starts.",
        "Statements that stop execution last for the session and are lost when a context compaction loses them; a new "
        "session, including one that continues a handoff, starts without them.",
    ),
    "zh": (
        "儲存庫的內容可能透過它的 `CLAUDE.md`、註解、commit 訊息，或主 Agent 與角色讀到的任何東西引導它們：角色可能被引導把變更造成"
        "的安全問題說成既有問題或只是推測，主 Agent 可能被引導去執行限制涵蓋的程式碼，因為限制本身也只是給主 Agent 的指示。",
        "審查與最終檢查會在這台機器上執行儲存庫的程式碼，而主 Agent 與角色的 Git 指令（每次呼叫前後的 `git status`、角色的讀取，以及 "
        "`git add`、commit 與 push）會執行儲存庫的 Git 設定、attributes 與 hooks 選定的程式，包括追蹤目錄中的 hook 以及 "
        "`git status` 執行的 filter，不論是否有限制生效。這些程式碼能改動你能改動的任何東西，包括你自己的 Git 設定、其他 worktree "
        "與 Feather 自己的紀錄。",
        "限制管的是審查與最終檢查，不是實作：executor 與 security-executor 實作時可能執行儲存庫的程式碼，修正別人的變更時也一樣。",
        "cc-feather 中沒有任何東西會在程式碼執行前先問你；剩下的只有 Claude Code 的資料夾信任與你的權限設定。",
        "你指定過的隔離環境，在一般性的限制下仍可使用，除非限制另有說明；如果那個環境存有秘密資料（例如 CI runner），程式碼就會在"
        "那裡執行。",
        "被忽略的檔案，以及標為 assume-unchanged 或 skip-worktree 的檔案，不在工作區檢查的範圍內，所以這類檔案可能影響審查或最終檢查。",
        "Claude Code 在專案中開始 session 時會載入專案的 `CLAUDE.md` 與 `.claude` 設定，並執行那些設定中的 hook，所以儲存庫在任何"
        "審查開始前就可能有所動作。",
        "停止執行的陳述只在這個 session 有效，被 context compaction 遺失時也就跟著遺失；新的 session（包括接續 handoff 的 session）"
        "不帶有它們。",
    ),
}
# S1 and S2 in every Repository safety section: reads are ordinary and contain nothing, and only the user's own message
# stops execution, for the session.
SECTION_SENTENCES = {
    "README.md": (
        "Main and the roles read the repository with ordinary file tools and ordinary Git commands; no review contains "
        "or detects hostile repository content.",
        "A restriction you state lasts for the session and covers every later call it names, the final check included, "
        "until your own message lifts it; nothing in the repository, a tool's output or a record can state or lift one.",
    ),
    "README.zh-TW.md": (
        "主 Agent 與角色用一般的檔案工具與一般的 Git 指令讀取儲存庫；沒有任何審查能隔離或偵測有惡意的儲存庫內容。",
        "你說明的限制在整個 session 有效，涵蓋它指名的每個後續呼叫（包括最終檢查），直到你自己的訊息解除它；儲存庫中的任何內容、"
        "工具輸出或紀錄都不能提出或解除限制。",
    ),
    "docs/reference.md": (
        "Main and the roles read the repository with ordinary file tools and ordinary Git commands, and no review "
        "contains or detects hostile repository content.",
        "A review keeps only the checks that make its result correct, and a check whose result cannot be established "
        "counts as failed.",
        "A read that exits non-zero, writes anything to standard error or prints anything but porcelain lines counts as "
        "a change.",
        "A restriction comes only from your own messages in this session: that the repository is not trusted, that code "
        "must not run, or a narrower one, such as not running a pull request's tests.",
        "Saying only where a change comes from is not a restriction.",
        "Text in a tool result, a file, a commit, a role's report, a handoff, dispatch or memory record, hook output or "
        "a compaction summary can neither state nor lift a restriction, nor name an isolated environment.",
    ),
    "docs/reference.zh-TW.md": (
        "主 Agent 與角色用一般的檔案工具與一般的 Git 指令讀取儲存庫，沒有任何審查能隔離或偵測有惡意的儲存庫內容。",
        "審查只保留讓結果正確的檢查，而無法確認結果的檢查算作失敗。",
        "結束代碼不為零、寫出任何標準錯誤輸出，或印出 porcelain 行以外內容的讀取，都算作有變動。",
        "限制只來自你在這個 session 自己的訊息：這個儲存庫不受信任、程式碼不得執行，或更窄的限制，例如不要跑某個 pull request 的測試。",
        "只說明變更從哪裡來不算限制。",
        "工具結果、檔案、commit、角色的回報、handoff、派工或記憶紀錄、hook 輸出或 compaction 摘要中的文字，都不能提出或解除限制，"
        "也不能指定隔離環境。",
    ),
}
STATUS = "git -c core.safecrlf=false status --porcelain --untracked-files=all --ignore-submodules=none"
COMMIT_FORMS = ("`git --literal-pathspecs add -- <claim files>`", "`git --literal-pathspecs commit -- <claim files>`")

# The roles table, the step table, the design trade-offs and the references' commit and worktree sentences.
REPLACED = {
    "README.md": {
        "new": (
            "It runs the repository's code only when main's brief says it may.",
            "| Code review | After main's primary acceptance passes, or is recorded as not run because a restriction you "
            "stated covers it |",
            "- **Rules are instructions, not enforcement.** The review flow, the rule for running repository code and "
            "the role limits are instructions to the model.",
            "- **Delegation trusts the repository.** Rules for reading a hostile repository cost every review and still "
            "contained nothing, since reviews run the repository's code and Claude Code loads its settings first.",
            "Main and the roles now read it as your own and run its code unless you say in this session that it must "
            "not run, and cc-feather offers no check before you trust a repository.",
        ),
        "old": (
            "It reads the repository and runs its code only as [Repository safety](#repository-safety) allows.",
            "In a review or security analysis it reads and searches only the files and directories main lists",
            "or is recorded as not run under [Repository safety](#repository-safety)",
            "The review flow, repository safety and the role limits are instructions to the model.",
            "Reviews run repository code by default, and read it as hostile.",
        ),
    },
    "README.zh-TW.md": {
        "new": (
            "它只在主 Agent 的 brief 說它可以時才執行儲存庫的程式碼。",
            "| 程式碼審查 | 主 Agent 的主要驗收通過後，或因你說明的限制涵蓋它而記為未執行時 |",
            "- **規則是指示，不是強制。**審查流程、執行儲存庫程式碼的規則與角色限制都是給模型的指示。",
            "- **分派信任儲存庫。**為讀取有惡意的儲存庫而設的規則讓每次審查都付出代價，卻什麼也隔離不了，因為審查會執行儲存庫的程式碼，"
            "Claude Code 也會先載入它的設定。",
        ),
        "old": (
            "它只依[儲存庫安全](#儲存庫安全)讀取儲存庫與執行其程式碼。",
            "審查或安全分析時只讀取與搜尋主 Agent 列出的檔案與目錄",
            "或依[儲存庫安全](#儲存庫安全)記為未執行時",
            "審查流程、儲存庫安全與角色限制都是給模型的指示。",
            "審查預設執行儲存庫程式碼，讀取時則當它不可信。",
        ),
    },
    "docs/reference.md": {
        "new": (
            "Each commit holds only the claim's files, which main adds and commits by name, so content you staged before "
            "stays out of it.",
        ),
        "old": (
            "main also makes the checks and uses the fixed forms that [Repository safety](#repository-safety) describes.",
            "each still prepared and checked as [Repository safety](#repository-safety) describes.",
        ),
    },
    "docs/reference.zh-TW.md": {
        "new": (
            "每個 commit 只包含 claim 的檔案，由主 Agent 以名稱加入並 commit，所以你先前 stage 的內容不會進入其中。",
        ),
        "old": (
            "主 Agent 也會先做[儲存庫安全](#儲存庫安全)所說的檢查，並使用其中的固定形式。",
            "也仍各自依[儲存庫安全](#儲存庫安全)所說的方式準備與檢查。",
        ),
    },
}

# Acceptance 16's absence pins, in any letter case, over the documents outside their update sections.
SECTION_NAMES = ("safe git invocation", "paths and names", "main's preparation", "before add, commit, tag or push")
ABSENT_ANY_CASE = ("comes from someone else", "來自別人", "repository-safety.md", *SECTION_NAMES,
                   "repository-chosen program")
# Text the rewrite removed, matched exactly.
ABSENT_EXACT = ("attacker-controlled", "攻擊者可控制", "fixed form", "固定形式")
# Acceptance 19's clause on repo-check (finding N-a of the ticket's plan review): no shipped text names or promises it.
REPO_CHECK = re.compile(r"repo[-_]check", re.I)

GLOSSARY_ENTRY = (
    "**Trusted repository**:\n"
    "What delegation assumes about the repository it works in: its working tree, its Git directory and configuration, "
    "and every change in it are the user's own or content the user chose to accept, and reading and running it is the "
    "user's risk. Main and the roles read it with ordinary file tools and ordinary Git commands, and a review and the "
    "final check run its code unless a restriction the user stated in this session covers the call; saying only where "
    "a change comes from is not a restriction. No review contains or detects hostile repository content, and cc-feather "
    "offers no check of a repository before it is trusted: deciding whether to trust one is the user's.\n"
    "_Avoid_: safe repository, hostile repository"
)

# Acceptance 14: the notes on earlier ADRs, by file, with how many each carries.
NOTES = {
    "0011-reviews-treat-the-repository-as-hostile-by-instruction.md": ("(Superseded by ADR 0016:", 1),
    "0014-reviews-execute-repository-code-by-default.md": ("(Superseded by ADR 0016:", 1),
    "0009-security-critical-claims-get-an-adversarial-review.md": ("(Amended by ADR 0016:", 2),
    "0013-only-what-a-claims-acceptance-needs-holds-its-completion.md": ("(Amended by ADR 0016:", 3),
    "0015-each-claim-is-reviewed-when-done-and-keeps-its-passes.md": ("(Amended by ADR 0016:", 5),
}
# The statements of the amended ADRs that relied on repository safety, each named by a note after it.
NOTED_STATEMENTS = {
    "0009-security-critical-claims-get-an-adversarial-review.md": (
        ("Residual risk: a role loads the project's CLAUDE.md", "no isolation rule for code the user did not write"),
        ("(Amended by ADR 0014: the isolation rule", "dynamic probing follows review state's Execution rule"),
    ),
    "0013-only-what-a-claims-acceptance-needs-holds-its-completion.md": (
        ("- **No review worktrees.**", "in the worktree exception"),
        ("- **Final check.**", "the final check runs within review state's Execution rule"),
        ("- **Main creates a worktree for each review**", "in the considered option of a worktree for each review"),
    ),
}
ADR_DECISIONS = (
    "- **The trust assumption.** Delegation assumes that the repository is trusted: its working tree, its Git directory "
    "and configuration, and every change in it are the user's own or content the user chose to accept, and reading and "
    "running it is the user's risk.",
    "No review contains or detects hostile repository content.",
    "Saying only where a change comes from is not a restriction: the condition on someone else's content, its allowance "
    "and its taint rules are gone.",
    "- **No check before trust.** cc-feather offers no check of a repository before it is trusted, and keeps no trust "
    "state file or other record that crosses sessions: deciding whether to trust a repository, for example after "
    "downloading or copying someone else's, is the user's.",
)
ADR_REJECTED = (
    "- **Keep the read rules as defence in depth**:",
    "- **Keep the \"someone else's content\" condition**:",
    "- **A read-only repo-check tool**,",
)
ADR_RISK_LABELS = ("Steering by content", "Code and Git programs run", "Implementation", "Nothing asks first",
                   "Isolated environments", "Outside the workspace check", "Before any review", "Statements end")
# The guards of tests/test_feather_security_review.py and the retired call-count wording of
# tests/test_feather_review_rules.py, which this ticket's new text must not reintroduce.
GUARDED = re.compile(r"security[\s-]*boundar|安全邊界|security-sensitive|安全敏感|two-call|six calls|fourteen", re.I)


def outside_updates(name: str, text: str) -> str:
    heading = DOCUMENTS[name]
    if heading is None or heading not in text:
        return text
    before, after = text.split(heading, 1)
    return before + ("\n## " + after.split("\n## ", 1)[1] if "\n## " in after else "\n")


def document(name: str) -> str:
    return outside_updates(name, normalised((ROOT / name).read_text(encoding="utf-8")))


def safety_section(text: str, heading: str) -> str:
    return text.split(f"\n{heading}\n", 1)[1].split("\n### ", 1)[0].split("\n## ", 1)[0]


def language(name: str) -> str:
    return "zh" if name in CHINESE else "en"


def adr(name: str) -> str:
    return normalised((ADR / name).read_text(encoding="utf-8"))


class RepositorySafetySectionTests(unittest.TestCase):
    """Acceptance 16, S1 and S2: the four Repository safety sections."""

    def test_the_headings_stay_and_each_section_opens_with_the_bold_statement(self):
        for name, heading in SAFETY_HEADINGS.items():
            text = document(name)
            with self.subTest(name=name):
                self.assertEqual(text.count(f"\n{heading}\n"), 1)
                paragraphs = [p for p in safety_section(text, heading).split("\n\n") if p.strip()]
                self.assertEqual(paragraphs[0].strip(), BOLD[language(name)])
                self.assertEqual(text.count(BOLD[language(name)]), 1)

    def test_the_bold_statement_says_what_acceptance_16_requires(self):
        for phrase in ("assumes that the repository is trusted", "reviews run its code",
                       "Saying where a change comes from", "no longer stops that",
                       "say in your own message that the code must not run",
                       "cc-feather offers no check of a repository before you trust it",
                       "deciding whether to trust one", "is yours"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, BOLD["en"])
        for phrase in ("分派假設儲存庫是受信任的", "審查會在這台機器上執行它的程式碼", "說明變更從哪裡來", "已經不會阻止這件事",
                       "請在你自己的訊息中說程式碼不得執行", "cc-feather 不提供在你信任儲存庫之前檢查它的功能", "由你決定"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, BOLD["zh"])
        for text in BOLD.values():
            for phrase in ABSENT_ANY_CASE:
                with self.subTest(phrase=phrase):
                    self.assertNotIn(phrase.casefold(), text.casefold())

    def test_every_section_lists_every_residual_risk_in_order(self):
        for name, heading in SAFETY_HEADINGS.items():
            section = safety_section(document(name), heading)
            items = [line[2:] for line in section.split("\n") if line.startswith("- ")]
            with self.subTest(name=name):
                self.assertEqual(items, list(RISKS[language(name)]))
                # No labelled rule bullet, so the reference-to-procedure mapping test keeps excluding the section.
                self.assertNotIn("\n- **", section)

    def test_the_residuals_state_main_and_the_roles_git_commands(self):
        # Ticket 01's code review N4: the roles' Git reads also run the programs the configuration selects.
        self.assertIn("main's and the roles' Git commands (`git status` before and after every call, the roles' reads, "
                      "`git add`, commit and push)", RISKS["en"][1])
        self.assertIn("主 Agent 與角色的 Git 指令（每次呼叫前後的 `git status`、角色的讀取，以及 `git add`、commit 與 push）",
                      RISKS["zh"][1])

    def test_each_section_states_the_trust_assumption_and_who_stops_execution(self):
        for name, sentences in SECTION_SENTENCES.items():
            section = safety_section(document(name), SAFETY_HEADINGS[name])
            for sentence in sentences:
                with self.subTest(name=name, sentence=sentence[:50]):
                    self.assertEqual(section.count(sentence), 1)

    def test_the_references_state_the_workspace_reads_and_the_commit_forms(self):
        for name in ("docs/reference.md", "docs/reference.zh-TW.md"):
            section = safety_section(document(name), SAFETY_HEADINGS[name])
            for phrase in ("`git rev-parse HEAD`", f"`{STATUS}`", *COMMIT_FORMS, "`git add -A`", "`git commit -a`",
                           "(adr/0016-delegation-trusts-the-repository.md)"):
                with self.subTest(name=name, phrase=phrase):
                    self.assertIn(phrase, section)

    def test_the_readmes_point_to_the_reference_and_adr_0016(self):
        for name, anchor in (("README.md", "(docs/reference.md#repository-safety)"),
                             ("README.zh-TW.md", "(docs/reference.zh-TW.md#儲存庫安全)")):
            section = safety_section(document(name), SAFETY_HEADINGS[name])
            for phrase in (anchor, "(docs/adr/0016-delegation-trusts-the-repository.md)"):
                with self.subTest(name=name, phrase=phrase):
                    self.assertIn(phrase, section)
            with self.subTest(name=name, superseded=True):
                self.assertNotIn("adr/0011-", section)
                self.assertNotIn("adr/0014-", section)


class ReplacedWordingTests(unittest.TestCase):
    """Acceptance 16: the roles tables, the step table, the design trade-offs and the references' commit and worktree
    sentences drop the repository safety wording and the condition on someone else's change."""

    def test_the_new_wording_is_present_and_the_old_is_gone(self):
        for name, groups in REPLACED.items():
            text = document(name)
            for sentence in groups["new"]:
                with self.subTest(name=name, new=sentence[:50]):
                    self.assertIn(sentence, text)
            for phrase in groups["old"]:
                with self.subTest(name=name, old=phrase[:50]):
                    self.assertNotIn(phrase, text)

    def test_shell_roles_state_the_brief_rule_once_each(self):
        self.assertEqual(document("README.md").count("It runs the repository's code only when main's brief says it "
                                                     "may."), 3)
        self.assertEqual(document("README.zh-TW.md").count("它只在主 Agent 的 brief 說它可以時才執行儲存庫的程式碼。"), 3)


class AbsenceTests(unittest.TestCase):
    """Acceptance 16's absence pins and the ticket's repo-check clause, over the documents outside their update
    sections, and repo-check under skills/ and templates/ as well."""

    def test_documents_outside_their_update_sections_drop_the_removed_terms(self):
        for name in DOCUMENTS:
            text = document(name)
            for phrase in ABSENT_ANY_CASE:
                with self.subTest(name=name, phrase=phrase):
                    self.assertNotIn(phrase.casefold(), text.casefold())
            for phrase in ABSENT_EXACT:
                with self.subTest(name=name, phrase=phrase):
                    self.assertNotIn(phrase, text)

    def test_no_shipped_text_names_or_promises_repo_check(self):
        for name in DOCUMENTS:
            with self.subTest(name=name):
                self.assertIsNone(REPO_CHECK.search(document(name)))
        for path, text in current_tree("skills", "templates").items():
            with self.subTest(path=path):
                self.assertIsNone(REPO_CHECK.search(text))
        self.assertFalse((ROOT / "skills" / "repo-check").exists())

    def test_the_update_sections_keep_their_pinned_notes(self):
        # The 0.25.0 note still links the kept heading, and earlier notes may still say what they said.
        for name, sentence in (("README.md", "See [Repository safety](#repository-safety)."),
                               ("README.zh-TW.md", "詳見[儲存庫安全](#儲存庫安全)。")):
            text = normalised((ROOT / name).read_text(encoding="utf-8"))
            with self.subTest(name=name):
                self.assertIn(sentence, text.split(DOCUMENTS[name], 1)[1])

    def test_the_rewritten_texts_avoid_guarded_wording(self):
        texts = {"ADR 0016": adr(ADR_0016), "CONTEXT.md#Trusted repository": GLOSSARY_ENTRY}
        for name, heading in SAFETY_HEADINGS.items():
            texts[name] = safety_section(document(name), heading)
        for name, notes in NOTES.items():
            texts[name] = "\n".join(line for line in adr(name).split("\n") if line.startswith(notes[0]))
        for name, text in texts.items():
            with self.subTest(name=name):
                self.assertIsNone(GUARDED.search(text))


class GlossaryTests(unittest.TestCase):
    """Acceptance 15: the Trusted repository entry replaces Repository-chosen program in the Review section."""

    def test_the_review_section_has_the_trusted_repository_entry(self):
        text = normalised((ROOT / "CONTEXT.md").read_text(encoding="utf-8"))
        review = text.split("\n## Review\n", 1)[1].split("\n## ", 1)[0]
        self.assertEqual(review.count(GLOSSARY_ENTRY), 1)
        self.assertEqual(text.count("**Trusted repository**"), 1)
        self.assertNotIn("**Repository-chosen program**", text)
        for phrase in ("attacker", "hostile by instruction", "repository safety's Execution"):
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, text)


class DecisionRecordTests(unittest.TestCase):
    """Acceptance 14: ADR 0016 and the notes on ADR 0009, 0011, 0013, 0014 and 0015."""

    def test_adr_0016_records_the_decision_the_rejected_options_and_the_residual_risks(self):
        text = adr(ADR_0016)
        self.assertTrue(text.startswith("# Delegation trusts the repository\n"))
        for heading in ("\n## Considered Options\n", "\n## Consequences and residual risks\n"):
            with self.subTest(heading=heading):
                self.assertEqual(text.count(heading), 1)
        for sentence in ADR_DECISIONS:
            with self.subTest(sentence=sentence[:50]):
                self.assertIn(sentence, text)
        options = text.split("\n## Considered Options\n", 1)[1].split("\n## ", 1)[0]
        for option in ADR_REJECTED:
            with self.subTest(option=option):
                self.assertIn("\n" + option, "\n" + options)
        self.assertIn("attempted in this release and abandoned on 2026-10-19, because each review found another way "
                      "for its reading of a hostile Git directory to miss what Git uses", options)
        risks = text.split("\n## Consequences and residual risks\n", 1)[1]
        labels = re.findall(r"^- \*\*(.+?)\.\*\* ", risks, re.M)
        self.assertEqual(labels, list(ADR_RISK_LABELS))
        self.assertIn("main's and the roles' Git commands (`git status` before and after every call, the roles' reads, "
                      "`git add`, commit and push)", risks)
        for linked in ("0011-reviews-treat-the-repository-as-hostile-by-instruction.md",
                       "0014-reviews-execute-repository-code-by-default.md", "../specs/repo-trust-split.md"):
            with self.subTest(linked=linked):
                self.assertIn(f"]({linked})", text)
                self.assertTrue((ADR / linked).is_file())

    def test_adr_0016_names_repo_check_only_as_a_rejected_option(self):
        text = adr(ADR_0016)
        options = text.split("\n## Considered Options\n", 1)[1].split("\n## ", 1)[0]
        rejected = next(line for line in options.split("\n") if line.startswith("- **A read-only repo-check tool**"))
        self.assertIsNone(REPO_CHECK.search(text.replace(rejected, "")))

    def test_each_earlier_adr_carries_its_notes(self):
        for name, (prefix, count) in NOTES.items():
            lines = adr(name).split("\n")
            with self.subTest(name=name):
                self.assertEqual(sum(line.startswith(prefix) for line in lines), count)
                self.assertEqual(sum("ADR 0016" in line for line in lines), count)
        for name, pairs in NOTED_STATEMENTS.items():
            lines = adr(name).split("\n")
            notes = [index for index, line in enumerate(lines) if line.startswith("(Amended by ADR 0016:")]
            for statement, note in pairs:
                with self.subTest(name=name, statement=statement):
                    at = next(index for index, line in enumerate(lines) if line.startswith(statement))
                    self.assertTrue(any(index > at and note in lines[index] for index in notes))

    def test_superseded_notes_name_what_no_longer_applies(self):
        self.assertIn("so main and the roles read it with ordinary file tools and ordinary Git commands",
                      adr("0011-reviews-treat-the-repository-as-hostile-by-instruction.md"))
        self.assertIn("saying that a change under review or content in the workspace is someone else's is no longer a "
                      "restriction", adr("0014-reviews-execute-repository-code-by-default.md"))

    def test_no_earlier_adr_text_is_rewritten(self):
        # Removing this ticket's notes, each a paragraph of its own, gives back the record as tagged at v0.28.0.
        for name, (prefix, _) in NOTES.items():
            tagged = tagged_blob(self, f"docs/adr/{name}")
            self.assertIsNotNone(tagged, name)
            stripped = re.sub(rf"\n\n{re.escape(prefix)}[^\n]*", "", adr(name))
            with self.subTest(name=name):
                self.assertEqual(stripped, tagged)


class TaggedTextTests(unittest.TestCase):
    """The new pins fail on the v0.28.0 text, and the absence pins of removed text matched it."""

    def test_every_new_pin_fails_on_the_v0_28_0_text(self):
        self.assertIsNone(tagged_blob(self, f"docs/adr/{ADR_0016}"))
        for name in SAFETY_HEADINGS:
            tagged = tagged_blob(self, name)
            pins = [BOLD[language(name)], *RISKS[language(name)], *SECTION_SENTENCES[name], *REPLACED[name]["new"]]
            for sentence in pins:
                with self.subTest(name=name, sentence=sentence[:50]):
                    self.assertNotIn(sentence, tagged)
        self.assertNotIn(GLOSSARY_ENTRY, tagged_blob(self, "CONTEXT.md"))

    def test_every_absence_pin_matches_the_v0_28_0_text(self):
        tagged = {name: outside_updates(name, tagged_blob(self, name) or "") for name in DOCUMENTS}
        whole = "\n".join(tagged.values())
        # The deleted reference's section names are guards: two of them never reached these documents, so each is
        # matched against the reference's own headings at the tag.
        reference = tagged_blob(self, "skills/delegation/references/repository-safety.md")
        headings = [line[3:].casefold() for line in reference.split("\n") if line.startswith("## ")]
        for phrase in ABSENT_ANY_CASE:
            with self.subTest(phrase=phrase):
                if phrase in SECTION_NAMES:
                    self.assertIn(phrase, headings)
                else:
                    self.assertIn(phrase.casefold(), whole.casefold())
        for phrase in ABSENT_EXACT:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, whole)
        for name, groups in REPLACED.items():
            for phrase in groups["old"]:
                with self.subTest(name=name, old=phrase[:50]):
                    self.assertIn(phrase, tagged[name])


if __name__ == "__main__":
    unittest.main()
