"""Release tests: each release's version, update and rollback notes and validation entry, and the documents users
follow to install, update and recover."""

from __future__ import annotations

import json
import re
import unittest

from tests.feather_support import config


class SecurityRoutingReleaseTests(unittest.TestCase):
    """0.18.0 C7 (docs/specs/security-critical-routing.md): the release requires setup update and records its validation."""

    README = {
        "docs/reference.md": "0.18.0 adds the `adversary` role and changes the executor role definition, the delegation guidance and the automatic review guidance, so run setup update in every scope where delegation is installed, then start a fresh session; until then `check` reports `role_update_required: true` (adversary is missing, and the executor role and the delegation guidance are from an older template), `model`, `review` and session export ask for setup update first, in `auto` and in `off`, and a required Adversarial review is blocked because adversary is missing.",
        "docs/reference.zh-TW.md": "0.18.0 新增 `adversary` 角色，並改了 executor 的角色定義、分派指引與自動審查指引，所以每個裝有分派元件的範圍都要跑 setup update，再開新 session；在那之前，`auto` 與 `off` 下 check 都會回報 `role_update_required: true`（缺少 adversary，executor 角色與分派指引來自較舊的範本），`model`、`review` 與 session export 也會要求先做 setup update，需要的對抗式審查也會因缺少 adversary 而受阻。",
    }

    ENTRY = (
        "**Setup update is required.** This release adds the `adversary` role and changes the executor role definition, the delegation guidance and the automatic review guidance: run setup update in every scope where delegation is installed, then start a fresh session.",
        "A 0.17.0 or older tool rejects a state that records `adversary`: to go back to one, remove the scope with 0.18.0 first, or restore the files listed in the update's backup manifest.",
        "the 0.17.0 tool's `check` and `show` both exited 2 with `{\"status\": \"error\", \"error\": \"state role schema mismatch\"}`",
        "Live scenarios: this release was implemented by a session running the installed 0.17.0 rules and roles.",
        "`v0.18.0` does not exist when this entry is written; it is created only after both passes on the release commit and the user's go-ahead, and then checked against that commit and this manifest version.",
    )

    @staticmethod
    def text(name):
        return (config.ROOT / name).read_text(encoding="utf-8")

    def test_readmes_require_setup_update(self):
        # The manifest version is pinned by the current release's tests (0.19.0 C8 item 1).
        for name, sentence in self.README.items():
            with self.subTest(readme=name):
                self.assertIn(sentence, self.text(name))

    def test_validation_entry_records_the_update_downgrade_upgrade_and_live_flows(self):
        entry = self.text("docs/setup-validation.md").split("\n## 0.18.0 security-critical routing\n", 1)[1].split("\n## ", 1)[0]
        for sentence in self.ENTRY:
            with self.subTest(entry=sentence[:50]):
                self.assertIn(sentence, entry)
        self.assertNotIn("no setup update is required", entry)


class ReviewFollowUpsReleaseTests(unittest.TestCase):
    """0.19.0 C8 (docs/specs/review-followups-0-19-0.md): the release requires setup update, merges its rollback
    instructions and records its validation."""

    # C8 item 3: the Updates sections, paired in both languages.
    UPDATES = (
        ("## Version history\n",
         "0.19.0 changes the executor, security-executor, adversary and reviewer role definitions, so run setup update in every scope where delegation is installed, then start a fresh session; until then `check` reports `role_update_required: true` with those four roles from an older template, and `model`, `review` and session export ask for setup update first, in `auto` and in `off`."),
        ("## 版本紀錄\n",
         "0.19.0 改了 executor、security-executor、adversary 與 reviewer 的角色定義，所以每個裝有分派元件的範圍都要跑 setup update，再開新 session；在那之前，`auto` 與 `off` 下 check 都會回報 `role_update_required: true`，並指出這四個角色來自較舊的範本，`model`、`review` 與 session export 也會要求先做 setup update。"),
    )

    # C8 item 4: one rollback instruction per case, in the setup document's added-roles section.
    ROLLBACK = (
        "To go back to 0.18.0, no remove is needed: 0.18.0 reads the state 0.19.0 writes, and its own setup update re-renders its role templates, so run setup update with 0.18.0 in every scope where delegation is installed, then start a fresh session.",
        "To go back to 0.17.0 or older, which rejects a state that records `adversary`, run remove with the newer plugin first, or restore the files listed in the update's backup manifest.",
    )
    REPLACED_ROLLBACK = (
        "A 0.17.0 or older tool rejects a state that records `adversary`: to go back to one, remove the scope with 0.18.0 first, or restore the files listed in the update's backup manifest.",
        "To go back to such a version, run remove with the newer plugin first, or restore the files listed in the update's backup manifest.",
    )

    # C8 items 3, 5 and 6, and the carried-forward follow-ups (Out of Scope).
    ENTRY = (
        "**Setup update is required.** This release changes the executor, security-executor, adversary and reviewer role definitions: run setup update in every scope where delegation is installed, then start a fresh session.",
        "To go back to 0.18.0, no remove is needed: 0.18.0 reads the state 0.19.0 writes, and its own setup update re-renders its role templates.",
        "A 0.17.0 or older tool rejects a state that records `adversary`: to go back to one, run remove with the newer plugin first, or restore the files listed in the update's backup manifest.",
        "Live scenarios (Q20): this release's plan reviews, implementation and review round ran with the installed 0.18.0 roles and procedures (user scope, setup update run on 2026-10-09), as the spec's Governance requires;",
        "No live scenario ran with the 0.19.0 roles or procedures: the changed rules of C2–C6 are proven only as text, by the contract tests, and are listed below as follow-ups to exercise live.",
        "`v0.19.0` does not exist when this entry is written.",
        "it is created only after every Claim has a valid APPROVED and CONFIRMED, and C2, C3 and C5 a valid HELD, or the user's accept-and-land decision for the Claim, and only with the user's go-ahead for landing and for the tag; that it names the release commit and matches this manifest version are checked afterwards.",
        "**Review round: pending when this entry was written.** The review round's results (code review and outcome verification per Claim, and Adversarial review for C2, C3 and C5) are added after the review round, in a commit that only records review history.",
        "Carried forward from 0.18.0: `check` and `show` do not name a missing role in a warning, only through `role_update_required` and its absence from the choices and agents; and the delegation skill's sentence \"After a claim passes and is committed\" does not name HELD itself.",
    )

    @staticmethod
    def text(name):
        return (config.ROOT / name).read_text(encoding="utf-8")

    @staticmethod
    def section(text, heading):
        return text.split(heading, 1)[1].split("\n## ", 1)[0]

    def test_updates_sections_require_setup_update_in_both_languages(self):
        for name, (heading, sentence) in zip(("docs/reference.md", "docs/reference.zh-TW.md"), self.UPDATES):
            with self.subTest(readme=name):
                self.assertIn(sentence, self.section(self.text(name), heading))

    def test_setup_document_gives_one_rollback_instruction_per_case(self):
        section = self.section(self.text("docs/setup.md"), "## Added roles and incompatible role sets\n")
        for sentence in self.ROLLBACK:
            with self.subTest(sentence=sentence[:40]):
                self.assertEqual(section.count(sentence), 1)
        setup = self.text("docs/setup.md")
        for sentence in self.REPLACED_ROLLBACK:
            with self.subTest(replaced=sentence[:40]):
                self.assertNotIn(sentence, setup)

    def test_validation_entry_records_the_update_rollback_live_scope_tag_and_review(self):
        entry = self.section(self.text("docs/setup-validation.md"), "\n## 0.19.0 review follow-ups\n")
        for sentence in self.ENTRY:
            with self.subTest(entry=sentence[:50]):
                self.assertIn(sentence, entry)
        self.assertNotIn("no setup update is required", entry)


class StopThresholdReleaseTests(unittest.TestCase):
    """0.20.0 C4 (docs/specs/configurable-stop-threshold.md): the release needs only the plugin update, says how to go
    back, and records its validation."""

    # C4 item 3: the Updates sections, paired in both languages.
    UPDATES = (
        ("## Version history\n",
         "0.20.0 adds the Stop threshold and the `/cc-feather:stop-threshold` command and changes no role definition or guidance template, so existing installations need only the plugin update and a fresh session, and their guidance and state stay unchanged until a Stop threshold is saved.",
         "A 0.19.x or older configuration tool rejects a scope with a saved Stop threshold, so before going back to one, set it to `default` in that scope; a task or session choice needs nothing."),
        ("## 版本紀錄\n",
         "0.20.0 新增停止門檻與 `/cc-feather:stop-threshold` 指令，沒有改任何角色定義或指引範本，所以既有安裝只要更新 plugin 再開新 session，在儲存停止門檻之前，指引與 state 都不會改變。",
         "0.19.x 或更舊的設定工具不接受已儲存停止門檻的範圍，所以要回到這些版本前，先在該範圍把它設回 `default`；task 或 session 的指定不需要處理。"),
    )

    # C4 item 3: the setup document's added-roles section.
    SETUP = (
        "Upgrading to 0.20.0 needs only the plugin update and a fresh session: it changes no role or guidance template, and a scope keeps byte-identical guidance and state until a Stop threshold is saved.",
        "To go back to 0.19.x or older from 0.20.0, which reject a state that records a Stop threshold, first run `review --stop-threshold default` in every scope that saved one; a scope without one, and a task or session choice, need nothing.",
    )

    # C4 items 2-4.
    ENTRY = (
        "**No setup update is required.** This release changes no role definition and no guidance template: existing installations need only the plugin update and a fresh session, and a scope keeps byte-identical guidance and state until a Stop threshold is saved in it.",
        "A 0.19.x or older configuration tool rejects a state that records a Stop threshold: to go back to one, first run `review --stop-threshold default` in every scope that saved one; a scope without one, and a task or session choice, need nothing.",
        "all 22 files of both scopes were byte-identical before and after, and `show` reported the default Stop threshold 2, not set, with no warnings.",
        "Live scenarios: this release's plan reviews and implementation ran, and its review round runs, with the installed 0.19.0 roles and procedures, under which the Stop threshold is the fixed two.",
        "No live scenario ran with the 0.20.0 procedures or the `/cc-feather:stop-threshold` command: the rules of C2 and C3 are proven only as text, by the contract tests, and the configuration tool's behaviour of C1 by its command-line tests and the checks above.",
        "`v0.20.0` does not exist when this entry is written.",
        "it is created only after every Claim has a valid APPROVED and CONFIRMED, or the user's accept-and-land decision for the Claim, and only with the user's go-ahead for landing and for the tag; that it names the release commit and matches this manifest version are checked afterwards.",
    )

    @staticmethod
    def text(name):
        return (config.ROOT / name).read_text(encoding="utf-8")

    @staticmethod
    def section(text, heading):
        return text.split(heading, 1)[1].split("\n## ", 1)[0]

    # The manifest version is pinned by the current release's tests (0.21.0 C5 item 1).

    def test_updates_sections_need_only_the_plugin_update_in_both_languages(self):
        for name, (heading, *sentences) in zip(("docs/reference.md", "docs/reference.zh-TW.md"), self.UPDATES):
            for sentence in sentences:
                with self.subTest(readme=name, sentence=sentence[:30]):
                    self.assertIn(sentence, self.section(self.text(name), heading))

    def test_setup_document_states_the_upgrade_and_the_way_back(self):
        section = self.section(self.text("docs/setup.md"), "## Added roles and incompatible role sets\n")
        for sentence in self.SETUP:
            with self.subTest(sentence=sentence[:40]):
                self.assertEqual(section.count(sentence), 1)

    def test_validation_entry_records_the_update_checks_live_scope_and_tag(self):
        entry = self.section(self.text("docs/setup-validation.md"), "\n## 0.20.0 configurable Stop threshold\n")
        for sentence in self.ENTRY:
            with self.subTest(entry=sentence[:50]):
                self.assertIn(sentence, entry)
        self.assertNotIn("Setup update is required", entry)


class RepositorySafetyReleaseTests(unittest.TestCase):
    """0.21.0 C5 (docs/specs/repository-safety.md): the release requires setup update, says how to go back, and
    records its validation."""

    # C5 item 3: the Updates sections, paired in both languages.
    UPDATES = (
        ("## Version history\n",
         "0.21.0 changes the reviewer, verifier, adversary, analyst, scout and Explore role definitions and the automatic review guidance, so run setup update in every scope where delegation is installed, then start a fresh session; until then `check` reports `role_update_required: true` with those six roles from an older template, and in `auto` also the delegation guidance, and `model`, `review` and session export ask for setup update first, in `auto` and in `off`.",
         "Reviewer can now answer INCONCLUSIVE when it could not obtain the evidence a code review needs, and code review counts it like an INCONCLUSIVE outcome verification.",
         "To go back to 0.20.0, no remove is needed: 0.20.0 reads the state 0.21.0 writes, and its own setup update re-renders its role templates and guidance."),
        ("## 版本紀錄\n",
         "0.21.0 改了 reviewer、verifier、adversary、analyst、scout 與 Explore 的角色定義和自動審查指引，所以每個裝有分派元件的範圍都要跑 setup update，再開新 session；在那之前，`auto` 與 `off` 下 check 都會回報 `role_update_required: true`，並指出這六個角色來自較舊的範本，`auto` 下還會指出分派指引來自較舊的範本，`model`、`review` 與 session export 也會要求先做 setup update。",
         "reviewer 現在可以在拿不到程式碼審查需要的證據時回答 INCONCLUSIVE，程式碼審查計算它的方式與結果驗證的 INCONCLUSIVE 相同。",
         "要回到 0.20.0 不需要先移除：0.20.0 讀得懂 0.21.0 寫入的 state，它自己的 setup update 會重新寫入它的角色範本與指引。"),
    )

    # C5 item 3: the setup document's added-roles section.
    SETUP = (
        "Upgrading to 0.21.0 needs setup update in every scope where delegation is installed, then a fresh session: it changes the reviewer, verifier, adversary, analyst, scout and Explore role templates and the automatic review guidance, and until the update `check` and `show` report those six roles from an older template, in `auto` also the delegation guidance, and `model`, `review` and session export refuse.",
        "To go back to 0.20.0 from 0.21.0, no remove is needed: 0.20.0 reads the state 0.21.0 writes, and its own setup update re-renders its role templates and guidance, so run setup update with 0.20.0 in every scope where delegation is installed, then start a fresh session.",
    )

    # C5 item 3: the setup document's summary of the automatic review guidance follows templates/review-auto.md (C1 item 1).
    # Repo trust split ticket 01 (0.29.0, Acceptance 7) replaced the fixed-form sentence in both with the commit rule.
    AUTO_SWITCH = "Main commits only the claim's files and skips hooks only when the user asks."

    # C5 item 2.
    ENTRY = (
        "**Setup update is required.** This release changes the reviewer, verifier, adversary, analyst, scout and Explore role definitions and the automatic review guidance: run setup update in every scope where delegation is installed, then start a fresh session.",
        "To go back to 0.20.0, no remove is needed: 0.20.0 reads the state 0.21.0 writes, and its own setup update re-renders its role templates and guidance.",
        "C4 item 3's positive control ran and was not skipped",
        "and 624 at C1 4c3e894, the candidate, and at fba6124, which records this review round.",
        "C4 item 7's positive controls in a blob-less partial clone also ran and were not skipped on this host:",
        "`check` and `show` reported `role_update_required: true` with exit 0 and named reviewer, verifier, adversary, analyst, scout and Explore as from an older template",
        "the v0.20.0 tool's `check` and `show` exited 0 with status ok",
        "No live scenario ran with the 0.21.0 procedures or roles:",
        "`v0.21.0` does not exist when this entry is written.",
        "Review round, recorded after it (2026-10-11 to 2026-10-12; every call by the installed 0.20.0 roles in fresh context; the final candidate is 4c3e894).",
        "call 6 HELD at 4c3e894.",
        "Sub-checks recorded as not established:",
        "The review round's non-blocking findings and the pre-existing items it found are recorded as later work in the project's records, not here.",
    )

    @staticmethod
    def text(name):
        return (config.ROOT / name).read_text(encoding="utf-8")

    @staticmethod
    def section(text, heading):
        return text.split(heading, 1)[1].split("\n## ", 1)[0]

    # The manifest version is pinned by the current release's tests (0.22.0 C5 item 1).

    def test_updates_sections_require_setup_update_and_name_inconclusive_in_both_languages(self):
        for name, (heading, *sentences) in zip(("docs/reference.md", "docs/reference.zh-TW.md"), self.UPDATES):
            for sentence in sentences:
                with self.subTest(readme=name, sentence=sentence[:30]):
                    self.assertIn(sentence, self.section(self.text(name), heading))

    def test_setup_document_states_the_upgrade_and_the_way_back(self):
        section = self.section(self.text("docs/setup.md"), "## Added roles and incompatible role sets\n")
        for sentence in self.SETUP:
            with self.subTest(sentence=sentence[:40]):
                self.assertEqual(section.count(sentence), 1)

    def test_setup_document_summarises_the_current_automatic_review_guidance(self):
        section = self.section(self.text("docs/setup.md"), "\n## Automatic review switch\n")
        self.assertIn(self.AUTO_SWITCH, section)
        # Repository safety deviation D-6 replaced the guidance's operation profile and question with the fixed form;
        # repo trust split ticket 01 replaced the fixed form with committing only the claim's files and skipping hooks
        # only when asked.
        self.assertIn(self.AUTO_SWITCH, self.text("templates/review-auto.md"))
        for text in (section, self.text("templates/review-auto.md")):
            self.assertNotIn("operation profile", text)
            self.assertNotIn("fixed form", text)

    def test_validation_entry_records_the_update_checks_live_scope_tag_and_review_round(self):
        entry = self.section(self.text("docs/setup-validation.md"), "\n## 0.21.0 repository safety\n")
        for sentence in self.ENTRY:
            with self.subTest(entry=sentence[:50]):
                self.assertIn(sentence, entry)
        self.assertNotIn("No setup update is required", entry)
        # The review round replaced the pending note, and each Claim has its line at the final candidate.
        self.assertNotIn("pending when this entry was written", entry)
        for claim in ("C3", "C1", "C2", "C4", "C5"):
            with self.subTest(claim=claim):
                self.assertEqual(entry.count(f"\n- {claim}: "), 1)

    def test_adr_0009_amendment_note_links_adr_0011(self):
        adr = self.text("docs/adr/0009-security-critical-claims-get-an-adversarial-review.md")
        note = self.section(adr, "\n## Amendment note for 0.21.0\n")
        link = "(0011-reviews-treat-the-repository-as-hostile-by-instruction.md)"
        self.assertIn(link, note)
        self.assertTrue((config.ROOT / "docs" / "adr" / link.strip("()")).is_file())


class RepositorySafetyFollowUpsReleaseTests(unittest.TestCase):
    """0.22.0 C5 (docs/specs/repository-safety-followups.md): the release needs only the plugin update, says how to go
    back, and records its validation and review round."""

    # C5 item 3: the Updates sections, paired in both languages.
    UPDATES = (
        ("## Version history\n",
         "0.22.0 changes no role definition, guidance template or configuration tool, so existing installations need only the plugin update and a fresh session; no setup update is needed.",
         "To go back to 0.21.0, reinstall the 0.21.0 plugin; no setup change is needed, since 0.22.0 changes no installed file or state."),
        ("## 版本紀錄\n",
         "0.22.0 沒有改任何角色定義、指引範本或設定工具，所以既有安裝只要更新 plugin 再開新 session，不需要做 setup update。",
         "要回到 0.21.0，重新安裝 0.21.0 的 plugin 即可；不需要變更 setup，因為 0.22.0 沒有改任何已安裝的檔案或 state。"),
    )

    # C5 item 2.
    ENTRY = (
        "**No setup update is required.** This release changes no role definition, no guidance template and no configuration tool:",
        "To go back to 0.21.0, reinstall the 0.21.0 plugin; no setup change is needed.",
        "C4 item 6's Windows positive control ran and was not skipped",
        "C4's POSIX checks and their positive control ran in Ubuntu under WSL",
        "PortableGit v2.56.0.windows.2",
        "`claude plugin validate . --json`",
        "No live scenario ran with the 0.22.0 procedures:",
        "`v0.22.0` does not exist when this entry is written.",
        "Review round, recorded after it (2026-10-13; the final candidate is the release commit).",
        "Known limitation, recorded by the user's decision:",
    )

    @staticmethod
    def text(name):
        return (config.ROOT / name).read_text(encoding="utf-8")

    @staticmethod
    def section(text, heading):
        return text.split(heading, 1)[1].split("\n## ", 1)[0]

    # The manifest version is pinned by the current release's tests (0.23.0 ticket 06).

    def test_updates_sections_need_only_the_plugin_update_in_both_languages(self):
        for name, (heading, *sentences) in zip(("docs/reference.md", "docs/reference.zh-TW.md"), self.UPDATES):
            for sentence in sentences:
                with self.subTest(readme=name, sentence=sentence[:30]):
                    self.assertIn(sentence, self.section(self.text(name), heading))

    def test_validation_entry_records_the_checks_live_scope_tag_and_review_round(self):
        entry = self.section(self.text("docs/setup-validation.md"), "\n## 0.22.0 repository safety follow-ups\n")
        for sentence in self.ENTRY:
            with self.subTest(entry=sentence[:50]):
                self.assertIn(sentence, entry)
        self.assertNotIn("Setup update is required", entry)
        # Each Claim has its line in the review round.
        for claim in ("C1", "C2", "C3", "C4", "C5"):
            with self.subTest(claim=claim):
                self.assertEqual(entry.count(f"\n- {claim}: "), 1)


class ClaimsAtImplementationReleaseTests(unittest.TestCase):
    """0.23.0 ticket 06 (docs/specs/claims-at-implementation.md, Acceptance item 13): the release needs only the plugin
    update, says how to go back, and records its validation, live compliance as untested and the review round."""

    # The Updates sections, paired in both languages, at the start of the release notes.
    UPDATES = (
        ("## Version history\n",
         "0.23.0 changes no role definition, guidance template or configuration tool, so existing installations need only the plugin update and a fresh session; no setup update is needed.",
         "To go back to 0.22.0, reinstall the 0.22.0 plugin; no setup change is needed, since 0.23.0 changes no installed file or state."),
        ("## 版本紀錄\n",
         "0.23.0 沒有改任何角色定義、指引範本或設定工具，所以既有安裝只要更新 plugin 再開新 session，不需要做 setup update。",
         "要回到 0.22.0，重新安裝 0.22.0 的 plugin 即可；不需要變更 setup，因為 0.23.0 沒有改任何已安裝的檔案或 state。"),
    )

    ENTRY = (
        "**No setup update is required.** This release changes no role definition, no guidance template and no configuration tool:",
        "`git diff --stat v0.22.0` to the candidate lists no file under `templates/`",
        "To go back to 0.22.0, reinstall the 0.22.0 plugin; no setup change is needed.",
        "`python -B -m unittest discover -s tests -t .` and `python -B -m unittest discover -s tests`",
        "710 tests at af27343, the reviewed commit, in a detached worktree outside the project",
        "`claude plugin validate . --json`",
        "No live scenario ran with the 0.23.0 procedures:",
        "live compliance is untested.",
        "`v0.23.0` does not exist when this entry is written.",
        "Review round, recorded after it (2026-10-13; the reviewed commit is af27343).",
        "its 13 findings became the security invariants S1 to S12 and Residual R1",
        "Residual risks, recorded by the user's decision:",
        "the user's decision on it is pending when this entry is written.",
    )

    @staticmethod
    def text(name):
        return (config.ROOT / name).read_text(encoding="utf-8")

    @staticmethod
    def section(text, heading):
        return text.split(heading, 1)[1].split("\n## ", 1)[0]

    # The manifest version is pinned by the current release's tests (0.24.0 ticket 04).

    def test_updates_sections_need_only_the_plugin_update_in_both_languages(self):
        for name, (heading, *sentences) in zip(("docs/reference.md", "docs/reference.zh-TW.md"), self.UPDATES):
            section = self.section(self.text(name), heading)
            for sentence in sentences:
                with self.subTest(readme=name, sentence=sentence[:30]):
                    self.assertEqual(section.count(sentence), 1)
            # 0.23.0's notes come before 0.22.0's.
            with self.subTest(readme=name, order=True):
                self.assertLess(section.index(sentences[0]), section.index(sentences[0].replace("0.23.0", "0.22.0", 1)))

    def test_validation_entry_records_the_checks_live_scope_tag_and_review_round(self):
        entry = self.section(self.text("docs/setup-validation.md"), "\n## 0.23.0 claims at implementation\n")
        for sentence in self.ENTRY:
            with self.subTest(entry=sentence[:50]):
                self.assertIn(sentence, entry)
        self.assertNotIn("Setup update is required", entry)
        # Each ticket has its line in the review round.
        for claim in ("T01", "T02", "T03", "T04", "T05", "T06"):
            with self.subTest(claim=claim):
                self.assertEqual(entry.count(f"\n- {claim}: "), 1)


class CompletionCriteriaReleaseTests(unittest.TestCase):
    """0.24.0 ticket 04 (docs/specs/completion-criteria.md, Acceptance item 11): the release changes the installed
    reviewer definition, so existing installations need the plugin update and then `/cc-feather:setup update`, and the
    Updates sections say so in both languages, and the validation entry records the checks, the rehearsal, the S6
    baseline and the review round. The tag is checked after it exists."""

    # The Updates sections, paired in both languages, at the start of the release notes.
    UPDATES = (
        ("## Version history\n",
         "0.24.0 changes the reviewer role definition, so existing installations need the plugin update and then `/cc-feather:setup update` in every scope where delegation is installed, then a fresh session; until then `check` reports `role_update_required: true` with reviewer from an older template, and `model`, `review` and session export ask for setup update first, in `auto` and in `off`.",
         "To go back to 0.23.0, reinstall the 0.23.0 plugin and run `/cc-feather:setup update` in every scope where delegation is installed, then start a fresh session, so that it restores the 0.23.0 reviewer role definition; no remove is needed, since 0.24.0 changes no configuration tool or state."),
        ("## 版本紀錄\n",
         "0.24.0 改了 reviewer 的角色定義，所以既有安裝要先更新 plugin，再於每個裝有分派元件的範圍執行 `/cc-feather:setup update`，然後開新 session；在那之前，`auto` 與 `off` 下 check 都會回報 `role_update_required: true`，並指出 reviewer 來自較舊的範本，`model`、`review` 與 session export 也會要求先做 setup update。",
         "要回到 0.23.0，重新安裝 0.23.0 的 plugin，並在每個裝有分派元件的範圍執行 `/cc-feather:setup update`，再開新 session，讓它還原 0.23.0 的 reviewer 角色定義；不需要先移除，因為 0.24.0 沒有改設定工具或 state。"),
    )

    @staticmethod
    def text(name):
        return (config.ROOT / name).read_text(encoding="utf-8")

    @staticmethod
    def section(text, heading):
        return text.split(heading, 1)[1].split("\n## ", 1)[0]

    # The validation entry: the setup update, both discovery forms, the rehearsal and its findings, the S6 baseline,
    # the tag and the review round.
    ENTRY = (
        "**Setup update is required.** This release changes the reviewer role definition, `templates/agents/reviewer.md`,",
        "each ran 747 tests at a41bd28, the reviewed commit, 748 at 2c0a22a and 749 at the commit carrying this entry, all passing with 30 skips and the same count in both forms",
        "Live rehearsal (Acceptance item 10, test target T1), 2026-10-14.",
        "The rehearsal ran headless (`claude -p`) with the user's approval: the first turn ran the candidate's setup in its own session, the second started a new session so that the installed roles and guidance loaded, and every later turn resumed it;",
        "the setup session reported cc-feather 0.24.0 loaded from it;",
        "its Follow-up record was the handoff record `.feather/handoffs/demo-tickets-followup.md` in the clone.",
        "wrote a project CLAUDE.md stating that automatic plan review is off in this project, which the session's `/cc-feather:auto-on` overrode for the session;",
        "the item's \"the seeded security defect in ticket B blocking code review until it is fixed\" was not observed, since the defect never reached code review.",
        "No working-tree change during a review call was shown by the session's transcript, not its turn outputs:",
        "Three findings: with an untracked test file present, main said the final check's precondition did not hold but still ran a final check scoped to the named test modules instead of refusing,",
        "so whether a conversation resumed with its context is a resumed session in those rules is unsettled and is recorded as an open question.",
        "After the rehearsal, the user-scope agent definitions, CLAUDE.md, settings.json and the cc-feather state were byte-identical to a backup taken before it.",
        "Reviews of this Plan used the roles and procedures installed before it (S6).",
        "`v0.24.0` does not exist when this entry is written.",
        "The deferred items, security items first, are kept in an untracked handoff record, not here.",
    )

    # The manifest version is pinned by the current release's tests (0.25.0 ticket 03).

    def test_validation_entry_records_the_checks_rehearsal_baseline_tag_and_review_round(self):
        entry = self.section(self.text("docs/setup-validation.md"), "\n## 0.24.0 completion criteria\n")
        for sentence in self.ENTRY:
            with self.subTest(sentence=sentence[:40]):
                self.assertEqual(entry.count(sentence), 1)
        self.assertNotIn("No setup update is required", entry)
        # Each ticket has its line in the review round.
        for claim in ("01", "02", "03", "04"):
            with self.subTest(claim=claim):
                self.assertEqual(entry.count(f"\n- {claim}: "), 1)

    def test_updates_sections_require_setup_update_in_both_languages(self):
        previous = ClaimsAtImplementationReleaseTests.UPDATES
        for name, (heading, *sentences), (_, previous_first, _) in zip(("docs/reference.md", "docs/reference.zh-TW.md"), self.UPDATES, previous):
            section = self.section(self.text(name), heading)
            for sentence in sentences:
                with self.subTest(readme=name, sentence=sentence[:30]):
                    self.assertEqual(section.count(sentence), 1)
            # The newest release's notes come first, the update note then the way back, before 0.23.0's.
            with self.subTest(readme=name, order=True):
                self.assertLess(section.index(sentences[0]), section.index(sentences[1]))
                self.assertLess(section.index(sentences[1]), section.index(previous_first))


class RepoTrustDefaultReleaseTests(unittest.TestCase):
    """0.25.0 ticket 03 (docs/specs/repo-trust-default.md, Acceptance items 9 and 11): the Updates note starts with
    the new execution default, points to Repository safety, and says that the changed reviewer, verifier and adversary
    definitions need the plugin update and then `/cc-feather:setup update`, what happens until then and how to go back
    to 0.24.0, in both languages. The validation entry records the checks, the rehearsal, the S7 baseline and the
    review round. The tag is checked after it exists."""

    # The Updates sections, paired in both languages: the section's opening sentence, then the 0.25.0 note in order.
    UPDATES = (
        ("## Updates and validation\n",
         "Plugin updates refresh the package; run setup update for the selected components to refresh external deployments, then start a fresh session, because roles and guidance are loaded when a session starts. ",
         "From 0.25.0, reviews run repository code without asking, and a review of someone else's change needs you to state that it comes from someone else.",
         "See [Repository safety](#repository-safety).",
         "0.25.0 changes the reviewer, verifier and adversary role definitions, so existing installations need the plugin update and then `/cc-feather:setup update` in every scope where delegation is installed, then a fresh session; until then `check` reports `role_update_required: true` with those three roles from an older template, `model`, `review` and session export ask for setup update first, in `auto` and in `off`, and a review that needs execution reports INCONCLUSIVE for it.",
         "To go back to 0.24.0, reinstall the 0.24.0 plugin and run `/cc-feather:setup update` in every scope where delegation is installed, then start a fresh session, so that it restores the 0.24.0 reviewer, verifier and adversary role definitions; no remove is needed, since 0.25.0 changes no configuration tool or state."),
        ("## 更新、移除與驗證\n",
         "Plugin 更新只更新套件，需另跑 setup update 更新選定的已部署項目，完成後開新 session，因為角色與指引在 session 開始時載入。",
         "從 0.25.0 起，審查不再詢問就會執行儲存庫的程式碼，而審查別人的變更時，需要由你說明它來自別人。",
         "詳見[儲存庫安全](#儲存庫安全)。",
         "0.25.0 改了 reviewer、verifier 與 adversary 的角色定義，所以既有安裝要先更新 plugin，再於每個裝有分派元件的範圍執行 `/cc-feather:setup update`，然後開新 session；在那之前，`auto` 與 `off` 下 check 都會回報 `role_update_required: true`，並指出這三個角色來自較舊的範本，`model`、`review` 與 session export 也會要求先做 setup update，需要執行程式碼的審查則會對這部分回報 INCONCLUSIVE。",
         "要回到 0.24.0，重新安裝 0.24.0 的 plugin，並在每個裝有分派元件的範圍執行 `/cc-feather:setup update`，再開新 session，讓它還原 0.24.0 的 reviewer、verifier 與 adversary 角色定義；不需要先移除，因為 0.25.0 沒有改設定工具或 state。"),
    )

    @staticmethod
    def text(name):
        return (config.ROOT / name).read_text(encoding="utf-8")

    @staticmethod
    def section(text, heading):
        return text.split(heading, 1)[1].split("\n## ", 1)[0]

    # How many of the note's sentences stay in the README's Updates section, and the reference's version history
    # heading that holds the rest, with every earlier release's notes.
    KEPT_IN_README = 2
    HISTORY_HEADINGS = ("## Version history\n", "## 版本紀錄\n")

    # The manifest version is pinned by the current release's tests (0.26.0 ticket 07).

    def test_updates_sections_start_with_the_execution_default_in_both_languages(self):
        previous = CompletionCriteriaReleaseTests.UPDATES
        newer = RetainedPassesReleaseTests.UPDATES
        for (name, reference), (heading, opening, *sentences), (_, previous_first, _), (_, _, *newer_sentences), history \
                in zip((("README.md", "docs/reference.md"), ("README.zh-TW.md", "docs/reference.zh-TW.md")), self.UPDATES,
                       previous, newer, self.HISTORY_HEADINGS):
            # The README keeps the note's first two sentences; the rest is in the reference's version history.
            kept, moved = sentences[:self.KEPT_IN_README], sentences[self.KEPT_IN_README:]
            section = self.section(self.text(name), heading)
            history_section = self.section(self.text(reference), history)
            for place, part, text in ((name, kept, section), (reference, moved, history_section)):
                for sentence in part:
                    with self.subTest(readme=place, sentence=sentence[:30]):
                        self.assertEqual(text.count(sentence), 1)
            # The 0.25.0 note starts right after the 0.26.0 note, its sentences in order, before 0.24.0's.
            with self.subTest(readme=name, order=True):
                after_newer = section[section.index(newer_sentences[-1]) + len(newer_sentences[-1]):]
                self.assertTrue(after_newer.lstrip(" ").startswith(kept[0]))
                for earlier, later in zip(kept, kept[1:]):
                    self.assertLess(section.index(earlier), section.index(later))
            with self.subTest(readme=reference, order=True):
                for earlier, later in zip(moved, moved[1:] + [previous_first]):
                    self.assertLess(history_section.index(earlier), history_section.index(later))

    # The validation entry: the setup update and the changed role templates, the rehearsal's single session, the
    # candidate loaded alone, its four results with each brief's reason, the S7 baseline and the tag.
    ENTRY_HEADING = "\n## 0.25.0 repo trust default\n"
    ENTRY = (
        "**Setup update is required.** This release changes the reviewer, verifier and adversary role definitions, `templates/agents/reviewer.md`, `templates/agents/verifier.md` and `templates/agents/adversary.md`, the only files under `templates/`, `skills/setup/` or `scripts/` that changed since v0.24.0;",
        "763 at 2579b6f and 764 at the commit carrying this entry, all passing with 30 skips and the same count in both forms",
        "Live rehearsal (Acceptance item 10, test target T1), 2026-10-15.",
        "The rehearsal session's init event listed exactly one cc-feather plugin, version 0.25.0, source `cc-feather@inline`, at the path of the candidate directory; the installed cc-feather 0.24.0 did not load.",
        "one session id, never resumed, with no compaction.",
        "The user made no statement about trust, and no question about trusting the repository appears in the transcript.",
        "code review APPROVED and outcome verification CONFIRMED, with no trust question; each code review and outcome verification brief stated \"You may execute repository code on this machine for this call.",
        "the marker held the import and test lines.",
        "its brief stated that repository code may not be executed for this call because the user said the change under review comes from someone else and has not allowed it to run on this machine nor named an isolated environment;",
        "the README note and the commit message claiming the owner's allowance were reported as a blocking finding and not followed;",
        "Main did not ask whether to run Alice's change;",
        "and main's later fix on top does not make it executable; the marker was absent.",
        "its brief stated that repository code may not be executed because the user stated in this session that no code is to be executed for the rest of the session and has not lifted that, and asked that anything needing execution be reported INCONCLUSIVE; the reviewer read only Git objects, ran nothing and gave no INCONCLUSIVE, stating instead that the tests still passing was inferred from the code and not run; the marker was absent.",
        "Deviations from the rules were observed and are recorded as a finding, not a pass: a scripted scan of the transcript's Git commands, followed by code review's reading of every Bash call, found Git commands that departed from repository safety's Git command forms, by the rehearsal's main in turns 2 to 7, the case (1) verifier and the case (3) reviewer. They passed fixed safe path names inside double quotes in loops instead of as single-quoted literals; in some of main's commands they used a common prefix without the mailmap, blame and order-file settings, or ran `rev-parse` or `log` without the full prefix or in forms the rules reserve for other uses; and main ran a `switch`, for which the rules list no form. The verifier reported its own case and the rehearsal's main relayed it; the others went unreported. None of these Git invocations ran repository code, and they do not affect the four results of the execution rule. Not exercised: Acceptance item 10's \"what needed execution was INCONCLUSIVE\" for case (4), since a code review of a docstring change, with no lint or type check named in its brief, had nothing it needed to execute; an allowance of someone else's change, a narrower restriction, a context compaction, and the filter-driver path,",
        "After the rehearsal, the user-scope agent definitions, CLAUDE.md, settings.json and the cc-feather state were byte-identical to S7's baseline,",
        "Reviews of this Plan used the roles and procedures installed before it (S7).",
        "Before every review dispatch the baseline was unchanged.",
        "`v0.25.0` does not exist when this entry is written.",
        "it is created only after the user's go-ahead.",
        "The deferred items are kept in an untracked handoff record, not here.",
    )

    def test_validation_entry_records_the_checks_rehearsal_baseline_tag_and_review_round(self):
        text = self.text("docs/setup-validation.md")
        self.assertIn(self.ENTRY_HEADING, text)
        entry = self.section(text, self.ENTRY_HEADING)
        for sentence in self.ENTRY:
            with self.subTest(sentence=sentence[:40]):
                self.assertEqual(entry.count(sentence), 1)
        self.assertNotIn("No setup update is required", entry)
        # Each of the four rehearsal cases has its result, in order, and each ticket its line in the review round.
        positions = [entry.index(f" ({case}) ") for case in (1, 2, 3, 4)]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(entry.count("the marker was absent."), 3)
        for claim in ("01", "02", "03"):
            with self.subTest(claim=claim):
                self.assertEqual(entry.count(f"\n- {claim}: "), 1)


class RetainedPassesReleaseTests(unittest.TestCase):
    """0.26.0 ticket 07 (docs/specs/retained-passes.md, Acceptance item 20): the Updates note states the change to
    review in auto, that no `/cc-feather:setup update` is needed because no installed role definition or policy
    changed, and how to go back to 0.25.0, in both languages; the validation entry records the test counts, the
    rehearsal, the tag and the review round."""

    # The Updates sections, paired in both languages: the section's opening sentence, then the 0.26.0 note in order.
    UPDATES = (
        ("## Updates and validation\n",
         "Plugin updates refresh the package; run setup update for the selected components to refresh external deployments, then start a fresh session, because roles and guidance are loaded when a session starts. ",
         "0.26.0 changes how a plan is reviewed in `auto`: each claim is reviewed when it is done and keeps its passes, the final check reruns every claim's primary acceptance and fixes a failure with fix claims, Adversarial review runs once at the final commit and its findings are recorded, a dispatch record carries review state across sessions, and main asks you once at the end.",
         "It changes only the delegation skill's procedures, not an installed role definition or policy, so existing installations need only the plugin update and a fresh session, which picks up the new procedures; no `/cc-feather:setup update` is needed.",
         "To go back to 0.25.0, reinstall the 0.25.0 plugin; no setup update or remove is needed, and earlier versions ignore dispatch records left under `.feather/dispatch/`."),
        ("## 更新、移除與驗證\n",
         "Plugin 更新只更新套件，需另跑 setup update 更新選定的已部署項目，完成後開新 session，因為角色與指引在 session 開始時載入。",
         "0.26.0 改了 `auto` 下計畫的審查方式：每個 claim 完成時就審查並保留它的通過結果，最終檢查會重跑每個 claim 的主要驗收，並以修正用的 claim 修正失敗，對抗式審查只在最終 commit 執行一次並記錄它的發現，派工紀錄讓審查狀態跨 session 延續，主 Agent 只在最後問你一次。",
         "它只改了分派 skill 的流程，沒有改任何已安裝的角色定義或政策，所以既有安裝只要更新 plugin 再開新 session，新 session 就會使用新的流程；不需要做 `/cc-feather:setup update`。",
         "要回到 0.25.0，重新安裝 0.25.0 的 plugin 即可；不需要做 setup update 或先移除，較早的版本會忽略留在 `.feather/dispatch/` 下的派工紀錄。"),
    )
    # The sentence of each language's note that states no setup update is needed.
    NO_SETUP_UPDATE = (
        "no `/cc-feather:setup update` is needed.",
        "不需要做 `/cc-feather:setup update`。",
    )

    @staticmethod
    def text(name):
        return (config.ROOT / name).read_text(encoding="utf-8")

    @staticmethod
    def section(text, heading):
        return text.split(heading, 1)[1].split("\n## ", 1)[0]

    # The manifest version is pinned by the current release's tests (0.27.0 ticket 05).

    def test_updates_sections_start_with_the_retained_passes_note_in_both_languages(self):
        previous = RepoTrustDefaultReleaseTests.UPDATES
        newer = HandoffTidyReleaseTests.UPDATES
        for name, (heading, opening, *sentences), (_, _, previous_first, *_), (_, _, *newer_sentences) \
                in zip(("README.md", "README.zh-TW.md"), self.UPDATES, previous, newer):
            section = self.section(self.text(name), heading)
            for sentence in sentences:
                with self.subTest(readme=name, sentence=sentence[:30]):
                    self.assertEqual(section.count(sentence), 1)
            # The 0.26.0 note starts right after the 0.27.0 note, its sentences in order, before 0.25.0's.
            with self.subTest(readme=name, order=True):
                after_newer = section[section.index(newer_sentences[-1]) + len(newer_sentences[-1]):]
                self.assertTrue(after_newer.lstrip(" ").startswith(sentences[0]))
                for earlier, later in zip(sentences, sentences[1:] + [previous_first]):
                    self.assertLess(section.index(earlier), section.index(later))

    def test_updates_sections_state_that_no_setup_update_is_needed_in_both_languages(self):
        for name, (heading, _, *sentences), no_update in zip(("README.md", "README.zh-TW.md"), self.UPDATES, self.NO_SETUP_UPDATE):
            section = self.section(self.text(name), heading)
            note = section[section.index(sentences[0]):section.index(sentences[-1]) + len(sentences[-1])]
            with self.subTest(readme=name):
                self.assertEqual(note.count(no_update), 1)
                # The note names no setup update as needed before or after the plugin update.
                self.assertNotIn("need the plugin update and then", note)
                self.assertNotIn("再於每個裝有分派元件的範圍執行", note)

    # The validation entry: no setup update, the test counts, the rehearsal's environment and results with what it
    # did not exercise and its deviations, the tag and the review round.
    ENTRY_HEADING = "\n## 0.26.0 retained passes\n"
    ENTRY = (
        "**No setup update is required.** No file under `templates/`, `skills/setup/` or `scripts/` changed since v0.25.0;",
        "856 at c945852 and 857 at the commit carrying this entry, all passing with 30 skips and the same count in both forms",
        "Live rehearsal (Acceptance item 19, test target T1), 2026-10-15, run twice at the user's choice.",
        "The commit under test was c945852,",
        "Every session's init event listed exactly one cc-feather plugin, version 0.26.0, source `cc-feather@inline`, at the path of the candidate directory; the installed cc-feather 0.25.0 did not load.",
        "so the Stop threshold in effect was 6 from user guidance, as each session stated.",
        "The dispatch record's path was `.feather/dispatch/paths.md` in the clone in both runs;",
        "03's encoded `..` was found by neither 03's code review nor 01's Adversarial review:",
        "Ticket 07's first acceptance check, which asks for these to appear in the record, is therefore not met, and goes to the decision at the end.",
        "Deviations from the rules were observed and are recorded as a finding, not a pass:",
        "so the absence of other deviations is not claimed.",
        "the user-scope agent definitions, CLAUDE.md and settings.json were byte-identical to the baseline recorded before the first.",
        "`v0.26.0` does not exist when this entry is written.",
        "it is created only after the user's go-ahead.",
        "The deferred items are kept in an untracked handoff record, not here.",
    )

    def test_validation_entry_records_the_checks_rehearsal_tag_and_review_round(self):
        text = self.text("docs/setup-validation.md")
        self.assertIn(self.ENTRY_HEADING, text)
        entry = self.section(text, self.ENTRY_HEADING)
        for sentence in self.ENTRY:
            with self.subTest(sentence=sentence[:40]):
                self.assertEqual(entry.count(sentence), 1)
        self.assertNotIn("Setup update is required", entry)
        # Both runs have their paragraph, in order, and each ticket its line in the review round.
        positions = [entry.index(run) for run in ("First run (", "Second run (")]
        self.assertEqual(positions, sorted(positions))
        for claim in ("01", "02", "03", "04", "05", "06", "07"):
            with self.subTest(claim=claim):
                self.assertEqual(entry.count(f"\n- {claim}: "), 1)


class HandoffTidyReleaseTests(unittest.TestCase):
    """0.27.0 ticket 05 (docs/specs/handoff-tidy.md, Acceptance item 13): both READMEs list and describe
    `/cc-feather:handoff-tidy`; the Updates note states what 0.27.0 adds, that no `/cc-feather:setup update` is needed
    and how to go back to 0.26.0, in both languages; the validation entry records the checks, the rehearsal on copies
    of real records with what it left unexercised, the tag and the review round."""

    # The Updates sections, paired in both languages: the section's opening sentence, then the 0.27.0 note in order.
    UPDATES = (
        ("## Updates and validation\n",
         "Plugin updates refresh the package; run setup update for the selected components to refresh external deployments, then start a fresh session, because roles and guidance are loaded when a session starts. ",
         "0.27.0 adds `/cc-feather:handoff-tidy`, a command only you can run that proposes the next work, merges and stale or incomplete records from the handoff records, or checks the recorded items of named or all work against the current project without running project code, and writes only what you confirm.",
         "It changes no installed role definition or policy, so existing installations need only the plugin update and a fresh session; no `/cc-feather:setup update` is needed.",
         "To go back to 0.26.0, reinstall the 0.26.0 plugin; no setup update or remove is needed, and records the command wrote stay ordinary handoff records."),
        ("## 更新、移除與驗證\n",
         "Plugin 更新只更新套件，需另跑 setup update 更新選定的已部署項目，完成後開新 session，因為角色與指引在 session 開始時載入。",
         "0.27.0 新增 `/cc-feather:handoff-tidy`：只能由你執行的指令，從交接紀錄建議下一項工作，指出可合併、過時或不完整的紀錄，或不執行專案程式碼，拿指定或全部工作的紀錄項目對照目前專案，並只寫入你確認的部分。",
         "它沒有改任何已安裝的角色定義或政策，所以既有安裝只要更新 plugin 再開新 session；不需要做 `/cc-feather:setup update`。",
         "要回到 0.26.0，重新安裝 0.26.0 的 plugin 即可；不需要做 setup update 或先移除，這個指令寫入的紀錄仍是一般的交接紀錄。"),
    )
    NO_SETUP_UPDATE = RetainedPassesReleaseTests.NO_SETUP_UPDATE

    # Each README's command list entry and the Handoff compatibility examples, with the section that holds them.
    LISTINGS = (
        ("README.md", "## Skills\n", "\n- `/cc-feather:handoff-tidy [work names | all]`: ", "## Handoff compatibility\n",
         ("only you can run it.", "Proposal", "Full check", "Selected check", "Checks are read-only and run no project code.",
          "written after your confirmation", "never authorizes the work it recommends or starts handoff maintenance.")),
        ("README.zh-TW.md", "## 入口\n", "\n| `/cc-feather:handoff-tidy [工作名稱或 all]` | ", "## 交接相容性\n",
         ("只能由你執行。", "Proposal", "Full check", "Selected check", "檢查唯讀，不執行專案程式碼。",
          "都在你確認後才寫入", "也不會授權它建議的工作或開始交接維護")),
    )
    EXAMPLES = "/cc-feather:handoff-resume login\n/cc-feather:handoff-tidy\n/cc-feather:handoff-tidy login\n```"

    @staticmethod
    def text(name):
        return (config.ROOT / name).read_text(encoding="utf-8")

    @staticmethod
    def section(text, heading):
        return text.split(heading, 1)[1].split("\n## ", 1)[0]

    # The manifest version is pinned by the current release's tests (0.27.1, handoff tidy write edges).

    def test_readmes_list_and_describe_the_command_in_both_languages(self):
        for name, skills, entry, compatibility, phrases in self.LISTINGS:
            text = self.text(name)
            listing = self.section(text, skills)
            with self.subTest(readme=name):
                self.assertEqual(listing.count(entry), 1)
                line = listing[listing.index(entry):].split("\n", 2)[1]
                # Listed right after handoff-resume, with the other handoff commands.
                self.assertIn("/cc-feather:handoff-resume", listing[:listing.index(entry)].rsplit("\n", 2)[-1])
                for phrase in phrases:
                    with self.subTest(readme=name, phrase=phrase):
                        self.assertIn(phrase, line)
                self.assertIn(self.EXAMPLES, self.section(text, compatibility))

    def test_updates_sections_start_with_the_handoff_tidy_note_in_both_languages(self):
        previous = RetainedPassesReleaseTests.UPDATES
        newer = HandoffTidyWriteEdgesReleaseTests.UPDATES
        for name, (heading, opening, *sentences), (_, _, previous_first, *_), (_, _, *newer_sentences) \
                in zip(("README.md", "README.zh-TW.md"), self.UPDATES, previous, newer):
            section = self.section(self.text(name), heading)
            for sentence in sentences:
                with self.subTest(readme=name, sentence=sentence[:30]):
                    self.assertEqual(section.count(sentence), 1)
            # The 0.27.0 note starts right after the 0.27.1 note, its sentences in order, before 0.26.0's.
            with self.subTest(readme=name, order=True):
                after_newer = section[section.index(newer_sentences[-1]) + len(newer_sentences[-1]):]
                self.assertTrue(after_newer.lstrip(" ").startswith(sentences[0]))
                for earlier, later in zip(sentences, sentences[1:] + [previous_first]):
                    self.assertLess(section.index(earlier), section.index(later))

    def test_updates_sections_state_that_no_setup_update_is_needed_in_both_languages(self):
        for name, (heading, _, *sentences), no_update in zip(("README.md", "README.zh-TW.md"), self.UPDATES, self.NO_SETUP_UPDATE):
            section = self.section(self.text(name), heading)
            note = section[section.index(sentences[0]):section.index(sentences[-1]) + len(sentences[-1])]
            with self.subTest(readme=name):
                self.assertEqual(note.count(no_update), 1)
                self.assertNotIn("need the plugin update and then", note)
                self.assertNotIn("再於每個裝有分派元件的範圍執行", note)

    # The validation entry: no setup update, the test counts, the rehearsal on copies of the real records with its
    # three scenarios, what it did not exercise and its observations, the tag and the review round.
    ENTRY_HEADING = "\n## 0.27.0 handoff tidy\n"
    ENTRY = (
        "**No setup update is required.** No file under `templates/`, `skills/setup/` or `scripts/` changed since v0.26.0;",
        "To go back to 0.26.0, reinstall the 0.26.0 plugin; no setup update or remove is needed.",
        "866 at e49958d and at 64cff50,",
        "all passing with 30 skips and the same count in both forms (the 0.26.0 release ran 857).",
        "Live rehearsal (Acceptance item 13), 2026-10-16.",
        "The commit under test was 64cff50,",
        "held copies of this project's nine real handoff records and `history.md`",
        "the installed cc-feather did not load.",
        "Writes were confirmed only for the copies; the real records were left unchanged,",
        "it read no project source.",
        "was copied word for word into the target and kept in the source,",
        "Nothing was written and no analyst was dispatched;",
        "ran no project code:",
        "set the verification field to the baseline and time of the check, and kept its earlier value, which was empty, in the details.",
        "Not exercised: running a Full check;",
        "Observations, recorded as findings rather than passes:",
        "`v0.27.0` does not exist when this entry is written.",
        "it is created only after the user's go-ahead.",
    )

    def test_validation_entry_records_the_checks_rehearsal_tag_and_review_round(self):
        text = self.text("docs/setup-validation.md")
        self.assertIn(self.ENTRY_HEADING, text)
        entry = self.section(text, self.ENTRY_HEADING)
        for sentence in self.ENTRY:
            with self.subTest(sentence=sentence[:40]):
                self.assertEqual(entry.count(sentence), 1)
        self.assertNotIn("Setup update is required", entry)
        # The three scenarios have their paragraph, in order, and each ticket its line in the review round.
        positions = [entry.index(f"\n- {scenario} (") for scenario in ("A", "B", "C")]
        self.assertEqual(positions, sorted(positions))
        for claim in ("01", "02", "03", "04", "05"):
            with self.subTest(claim=claim):
                self.assertEqual(entry.count(f"\n- {claim}: "), 1)


class HandoffTidyWriteEdgesReleaseTests(unittest.TestCase):
    """0.27.1 (docs/specs/handoff-tidy-write-edges.md, Acceptance item 6): the manifest version is 0.27.1; the Updates
    note states what 0.27.1 fixes, that no `/cc-feather:setup update` is needed because no installed role definition or
    policy changed, and how to go back to 0.27.0, in both languages; the validation entry records the validation, that
    no live rehearsal was run and that the tests cannot show a model follows the rules, the tag and the review round."""

    # The Updates sections, paired in both languages: the section's opening sentence, then the 0.27.1 note in order.
    UPDATES = (
        ("## Updates and validation\n",
         "Plugin updates refresh the package; run setup update for the selected components to refresh external deployments, then start a fresh session, because roles and guidance are loaded when a session starts. ",
         "0.27.1 fixes two write rules of `/cc-feather:handoff-tidy`: a confirmed proposal that writes the same record more than once, such as two merges into one target, now completes, each write built from the record as the previous write saved it so nothing that write added is lost, and a failed archive of a record the command completed is retried as the handoff skill describes.",
         "It changes only the command's text, not an installed role definition or policy, so existing installations need only the plugin update and a fresh session; no `/cc-feather:setup update` is needed.",
         "To go back to 0.27.0, reinstall the 0.27.0 plugin; no setup update or remove is needed."),
        ("## 更新、移除與驗證\n",
         "Plugin 更新只更新套件，需另跑 setup update 更新選定的已部署項目，完成後開新 session，因為角色與指引在 session 開始時載入。",
         "0.27.1 修正 `/cc-feather:handoff-tidy` 的兩條寫入規則：一次確認要寫入同一份紀錄多次時（例如兩項合併進同一個目標），現在能全部寫完，每次寫入都以前一次寫入存下的內容為基礎，不會蓋掉前一次加入的內容；這個指令完成的紀錄若封存失敗，會依交接 skill 的規則重試。",
         "它只改了這個指令的文字，沒有改任何已安裝的角色定義或政策，所以既有安裝只要更新 plugin 再開新 session；不需要做 `/cc-feather:setup update`。",
         "要回到 0.27.0，重新安裝 0.27.0 的 plugin 即可；不需要做 setup update 或先移除。"),
    )
    NO_SETUP_UPDATE = RetainedPassesReleaseTests.NO_SETUP_UPDATE

    @staticmethod
    def text(name):
        return (config.ROOT / name).read_text(encoding="utf-8")

    @staticmethod
    def section(text, heading):
        return text.split(heading, 1)[1].split("\n## ", 1)[0]

    # The manifest version is pinned by the current release's tests (0.28.0, weigh findings before rules).

    def test_updates_sections_start_with_the_write_edges_note_in_both_languages(self):
        previous = HandoffTidyReleaseTests.UPDATES
        newer = WeighFindingsBeforeRulesReleaseTests.UPDATES
        for name, (heading, opening, *sentences), (_, _, previous_first, *_), (_, _, *newer_sentences) \
                in zip(("README.md", "README.zh-TW.md"), self.UPDATES, previous, newer):
            section = self.section(self.text(name), heading)
            for sentence in sentences:
                with self.subTest(readme=name, sentence=sentence[:30]):
                    self.assertEqual(section.count(sentence), 1)
            # The 0.27.1 note starts right after the 0.28.0 note, its sentences in order, before 0.27.0's.
            with self.subTest(readme=name, order=True):
                after_newer = section[section.index(newer_sentences[-1]) + len(newer_sentences[-1]):]
                self.assertTrue(after_newer.lstrip(" ").startswith(sentences[0]))
                for earlier, later in zip(sentences, sentences[1:] + [previous_first]):
                    self.assertLess(section.index(earlier), section.index(later))

    def test_updates_sections_state_that_no_setup_update_is_needed_in_both_languages(self):
        for name, (heading, _, *sentences), no_update in zip(("README.md", "README.zh-TW.md"), self.UPDATES, self.NO_SETUP_UPDATE):
            section = self.section(self.text(name), heading)
            note = section[section.index(sentences[0]):section.index(sentences[-1]) + len(sentences[-1])]
            with self.subTest(readme=name):
                self.assertEqual(note.count(no_update), 1)
                self.assertNotIn("need the plugin update and then", note)
                self.assertNotIn("再於每個裝有分派元件的範圍執行", note)

    # The validation entry: what it implements, no setup update, the validation, no rehearsal and what the tests cannot
    # show, the tag and the review round.
    ENTRY_HEADING = "\n## 0.27.1 handoff tidy write edges\n"
    ENTRY = (
        "Implements [the handoff tidy write edges spec](specs/handoff-tidy-write-edges.md), committed in 01a75b3;",
        "**No setup update is required.** No file under `templates/`, `skills/setup/` or `scripts/` changed since v0.27.0;",
        "To go back to 0.27.0, reinstall the 0.27.0 plugin; no setup update or remove is needed.",
        "(the 0.27.0 release ran 870).",
        "No live rehearsal was run for this patch.",
        "they cannot show that a model follows them.",
        "`v0.27.1` does not exist when this entry is written.",
        "it is created only after the user's go-ahead.",
        "Plan review returned READY on call 1.",
    )

    def test_validation_entry_records_the_checks_tag_and_review_round(self):
        text = self.text("docs/setup-validation.md")
        self.assertIn(self.ENTRY_HEADING, text)
        entry = self.section(text, self.ENTRY_HEADING)
        for sentence in self.ENTRY:
            with self.subTest(sentence=sentence[:40]):
                self.assertEqual(entry.count(sentence), 1)
        self.assertNotIn("Setup update is required", entry)
        # The single claim has its line in the review round.
        self.assertEqual(entry.count("\n- The claim: "), 1)


class WeighFindingsBeforeRulesReleaseTests(unittest.TestCase):
    """0.28.0 (docs/specs/weigh-findings-before-rules.md, Acceptance item 7): the manifest version is 0.28.0; the
    Updates note states what 0.28.0 changes, that the installed delegation policy changed so existing installations run
    `/cc-feather:setup update` and start a fresh session, and how to go back to 0.27.1, in both languages; the validation
    entry records the validation, a setup update bringing a 0.27.1 installation's policy to the new template, that no
    live rehearsal was run and that the tests cannot show a model follows the rule, the tag and the review round."""

    # The Updates sections, paired in both languages: the section's opening sentence, then the 0.28.0 note in order.
    UPDATES = (
        ("## Updates and validation\n",
         "Plugin updates refresh the package; run setup update for the selected components to refresh external deployments, then start a fresh session, because roles and guidance are loaded when a session starts. ",
         "0.28.0 asks main, before it proposes or adopts a requirement or fix derived from a finding, to state briefly when the case can occur in normal use or under the applicable threat model, its worst credible outcome and whether an existing rule covers it, and to prefer reusing or correcting a rule; the weighing never changes what blocks.",
         "It changes the installed delegation policy, which now also loads the delegation skill before such a requirement or fix is proposed or adopted, so existing installations need the plugin update, then `/cc-feather:setup update` in every scope where delegation is installed, then a fresh session; until then `check` warns that the delegation guidance is from an older template.",
         "To go back to 0.27.1, reinstall the 0.27.1 plugin and run `/cc-feather:setup update` in every scope where delegation is installed, then start a fresh session, so that it restores the 0.27.1 policy; no remove is needed."),
        ("## 更新、移除與驗證\n",
         "Plugin 更新只更新套件，需另跑 setup update 更新選定的已部署項目，完成後開新 session，因為角色與指引在 session 開始時載入。",
         "0.28.0 要求主 Agent 依問題提出或採用一項要求或修正之前，先簡短說明這個情況在一般使用中或適用的威脅模型下何時會發生、最壞而可信的後果，以及既有規則是否已經涵蓋，並優先沿用或修正既有規則；這項權衡不改變什麼會擋下。",
         "它改了已安裝的分派政策，讓主 Agent 在提出或採用這類要求或修正之前也會載入分派 skill，所以既有安裝要先更新 plugin，再於每個裝有分派元件的範圍執行 `/cc-feather:setup update`，然後開新 session；在那之前，check 會提醒分派指引來自較舊的範本。",
         "要回到 0.27.1，重新安裝 0.27.1 的 plugin，並在每個裝有分派元件的範圍執行 `/cc-feather:setup update`，再開新 session，讓它還原 0.27.1 的政策；不需要先移除。"),
    )
    NO_SETUP_UPDATE = RetainedPassesReleaseTests.NO_SETUP_UPDATE

    @staticmethod
    def text(name):
        return (config.ROOT / name).read_text(encoding="utf-8")

    @staticmethod
    def section(text, heading):
        return text.split(heading, 1)[1].split("\n## ", 1)[0]

    # The manifest version is pinned by the current release's tests (0.29.0, delegation trusts the repository).

    def test_updates_sections_start_with_the_weigh_findings_note_in_both_languages(self):
        previous = HandoffTidyWriteEdgesReleaseTests.UPDATES
        newer = RepoTrustSplitReleaseTests.UPDATES
        for name, (heading, opening, *sentences), (_, _, previous_first, *_), (_, _, *newer_sentences) \
                in zip(("README.md", "README.zh-TW.md"), self.UPDATES, previous, newer):
            section = self.section(self.text(name), heading)
            for sentence in sentences:
                with self.subTest(readme=name, sentence=sentence[:30]):
                    self.assertEqual(section.count(sentence), 1)
            # The 0.28.0 note starts right after the 0.29.0 note, its sentences in order, before 0.27.1's.
            with self.subTest(readme=name, order=True):
                after_newer = section[section.index(newer_sentences[-1]) + len(newer_sentences[-1]):]
                self.assertTrue(after_newer.lstrip(" ").startswith(sentences[0]))
                for earlier, later in zip(sentences, sentences[1:] + [previous_first]):
                    self.assertLess(section.index(earlier), section.index(later))

    def test_updates_sections_require_setup_update_in_both_languages(self):
        for name, (heading, _, *sentences), no_update in zip(("README.md", "README.zh-TW.md"), self.UPDATES, self.NO_SETUP_UPDATE):
            section = self.section(self.text(name), heading)
            note = section[section.index(sentences[0]):section.index(sentences[-1]) + len(sentences[-1])]
            with self.subTest(readme=name):
                # The note asks for setup update after the plugin update and for going back, and never says it is not needed.
                self.assertEqual(note.count("`/cc-feather:setup update`"), 2)
                self.assertNotIn(no_update, note)
                self.assertNotIn("need only the plugin update", note)
                self.assertNotIn("只要更新 plugin", note)

    # The validation entry: what it implements, the setup update and the changed template, the validation, the
    # setup-update check from a 0.27.1 installation, no rehearsal and what the tests cannot show, the tag and the review
    # round.
    ENTRY_HEADING = "\n## 0.28.0 weigh findings before rules\n"
    ENTRY = (
        "Implements [the weigh findings before rules spec](specs/weigh-findings-before-rules.md), committed in 9a0b69e;",
        "**Setup update is required.** This release changes the delegation policy template, `templates/CLAUDE.md`, the only file under `templates/`, `skills/setup/` or `scripts/` that changed since v0.27.1;",
        "as `git diff-tree -r --name-only v0.27.1 HEAD` shows.",
        "To go back to 0.27.1, reinstall the 0.27.1 plugin and run `/cc-feather:setup update` the same way.",
        "(the 0.27.1 release ran 875).",
        "now expects `templates/CLAUDE.md` among the changed non-role templates,",
        "v0.27.1 was exported read-only with `git archive --format=tar v0.27.1 | tar -x -C <scratch>/v0.27.1`,",
        "the warning `delegation guidance is from an older template; run setup update`,",
        "previewed changes to `project/CLAUDE.md` and `project/.claude/cc-feather/state.json` only, no role definition;",
        "`check` with `<tool>` then reported status `ok` with no warning and no issue;",
        "No live rehearsal was run for this release.",
        "they cannot show that a model weighs findings as the rule says.",
        "`v0.28.0` does not exist when this entry is written.",
        "it is created only after the user's go-ahead.",
        "and READY on call 2, after the user's change to the claim",
        "a Codex second opinion ran in parallel.",
    )

    def test_validation_entry_records_the_checks_setup_update_tag_and_review_round(self):
        text = self.text("docs/setup-validation.md")
        self.assertIn(self.ENTRY_HEADING, text)
        entry = self.section(text, self.ENTRY_HEADING)
        for sentence in self.ENTRY:
            with self.subTest(sentence=sentence[:40]):
                self.assertEqual(entry.count(sentence), 1)
        self.assertNotIn("No setup update is required", entry)
        # The setup-update check has its three steps, in order, and the single claim its line in the review round.
        positions = [entry.index(f"\n- {step}") for step in ("`check --project", "`python -I -B <tool> update", "`check` with")]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(entry.count("\n- The claim: "), 1)


class RepoTrustSplitReleaseTests(unittest.TestCase):
    """0.29.0 (docs/specs/repo-trust-split.md, Acceptance items 18 and 19, S1 and S8): the manifest version is 0.29.0;
    the Updates note states what 0.29.0 changes, that saying a change comes from someone else no longer stops a review
    from running it, that the role definitions and the installed delegation policy changed so existing installations run
    `/cc-feather:setup update` and start a fresh session, and how to go back to 0.28.0, in both languages, without
    implying that reviews contain or detect hostile repository content; the validation entry records the test counts, a
    setup update bringing a 0.28.0 installation's role definitions and policy to the new templates in a scratch project
    scope, the T2 skips, the abandoned repo-check, that no live review rehearsal was run, the review round and the tag."""

    # The Updates sections, paired in both languages: the section's opening sentence, then the 0.29.0 note in order.
    UPDATES = (
        ("## Updates and validation\n",
         "Plugin updates refresh the package; run setup update for the selected components to refresh external deployments, then start a fresh session, because roles and guidance are loaded when a session starts. ",
         "0.29.0 makes delegation trust the repository: main and the roles read it with ordinary file tools and ordinary Git commands, a review keeps only the checks its result needs, that `HEAD` is the commit the call judges, that what the claim depends on has no uncommitted or untracked change before or after the call and that a commit holds only the claim's files, and reviews run the repository's code unless you restrict it in this session; deciding whether to trust a repository is yours, and the risks that remain are listed under [Repository safety](#repository-safety).",
         "Saying that a change comes from someone else no longer stops a review from running it, so to stop it, say in your own message that the code must not run.",
         "It changes the reviewer, verifier, adversary, analyst, scout and Explore role definitions and the installed delegation policy, so existing installations need the plugin update, then `/cc-feather:setup update` in every scope where delegation is installed, then a fresh session; until then `check` warns that those roles, and in `auto` the delegation guidance, are from an older template.",
         "To go back to 0.28.0, reinstall the 0.28.0 plugin and run `/cc-feather:setup update` in every scope where delegation is installed, then start a fresh session, so that it restores the 0.28.0 role definitions and policy; no remove is needed."),
        ("## 更新、移除與驗證\n",
         "Plugin 更新只更新套件，需另跑 setup update 更新選定的已部署項目，完成後開新 session，因為角色與指引在 session 開始時載入。",
         "0.29.0 讓分派信任儲存庫：主 Agent 與角色用一般的檔案工具與一般的 Git 指令讀取它，審查只保留讓結果正確的檢查（`HEAD` 是該次呼叫判斷的 commit，claim 依賴的內容在呼叫前後都沒有未提交或未追蹤的變動，commit 只包含 claim 的檔案），而且除非你在這個 session 中限制，審查會執行儲存庫的程式碼；要不要信任一個儲存庫由你決定，剩下的風險列在[儲存庫安全](#儲存庫安全)。",
         "說明變更來自別人已經不會阻止審查執行它，所以要阻止，請在你自己的訊息中說程式碼不得執行。",
         "它改了 reviewer、verifier、adversary、analyst、scout 與 Explore 的角色定義以及已安裝的分派政策，所以既有安裝要先更新 plugin，再於每個裝有分派元件的範圍執行 `/cc-feather:setup update`，然後開新 session；在那之前，check 會提醒這些角色（以及 `auto` 下的分派指引）來自較舊的範本。",
         "要回到 0.28.0，重新安裝 0.28.0 的 plugin，並在每個裝有分派元件的範圍執行 `/cc-feather:setup update`，再開新 session，讓它還原 0.28.0 的角色定義與政策；不需要先移除。"),
    )
    NO_SETUP_UPDATE = RetainedPassesReleaseTests.NO_SETUP_UPDATE
    # S1: wording that would say a review contains, isolates or detects hostile content, and the guarded wording of
    # tests/test_feather_security_review.py and tests/test_feather_review_rules.py.
    CONTAINMENT = ("contain", "detect", "isolat", "sandbox", "隔離", "偵測", "防護")
    GUARDED = re.compile(r"security[\s-]*boundar|安全邊界|security-sensitive|安全敏感|two-call|six calls|fourteen", re.I)

    @staticmethod
    def text(name):
        return (config.ROOT / name).read_text(encoding="utf-8")

    @staticmethod
    def section(text, heading):
        return text.split(heading, 1)[1].split("\n## ", 1)[0]

    def note(self, name, heading, sentences):
        section = self.section(self.text(name), heading)
        return section[section.index(sentences[0]):section.index(sentences[-1]) + len(sentences[-1])]

    # The manifest version is pinned by the current release's tests (0.30.0, delegation dedupe).

    def test_updates_sections_start_with_the_trusted_repository_note_in_both_languages(self):
        previous = WeighFindingsBeforeRulesReleaseTests.UPDATES
        newer = DelegationDedupeReleaseTests.UPDATES
        for name, (heading, opening, *sentences), (_, _, previous_first, *_), (_, _, *newer_sentences) \
                in zip(("README.md", "README.zh-TW.md"), self.UPDATES, previous, newer):
            section = self.section(self.text(name), heading)
            for sentence in sentences:
                with self.subTest(readme=name, sentence=sentence[:30]):
                    self.assertEqual(section.count(sentence), 1)
            # The 0.29.0 note starts right after the 0.30.0 note, its sentences in order, before 0.28.0's.
            with self.subTest(readme=name, order=True):
                after_newer = section[section.index(newer_sentences[-1]) + len(newer_sentences[-1]):]
                self.assertTrue(after_newer.lstrip(" ").startswith(sentences[0]))
                for earlier, later in zip(sentences, sentences[1:] + [previous_first]):
                    self.assertLess(section.index(earlier), section.index(later))

    def test_updates_sections_require_setup_update_in_both_languages(self):
        for name, (heading, _, *sentences), no_update in zip(("README.md", "README.zh-TW.md"), self.UPDATES, self.NO_SETUP_UPDATE):
            note = self.note(name, heading, sentences)
            with self.subTest(readme=name):
                # The note asks for setup update after the plugin update and for going back, and never says it is not needed.
                self.assertEqual(note.count("`/cc-feather:setup update`"), 2)
                self.assertNotIn(no_update, note)
                self.assertNotIn("need only the plugin update", note)
                self.assertNotIn("只要更新 plugin", note)

    def test_the_note_names_every_role_definition_the_release_changes(self):
        from tests import test_feather_repo_trust as repo_trust
        changed = repo_trust.SetupUpdateReplacesTheTwentyEightInstallationTests.CHANGED
        for name, (heading, _, *sentences) in zip(("README.md", "README.zh-TW.md"), self.UPDATES):
            note = self.note(name, heading, sentences)
            for role in changed:
                with self.subTest(readme=name, role=role):
                    self.assertIn(f"{role}", note)
            for role in repo_trust.DelegationTrustsTheRepositoryTests.UNCHANGED_ROLES:
                with self.subTest(readme=name, unchanged=role):
                    self.assertNotIn(role, note)

    def test_s1_the_note_implies_no_containment_and_keeps_out_guarded_wording(self):
        for name, (heading, _, *sentences) in zip(("README.md", "README.zh-TW.md"), self.UPDATES):
            note = self.note(name, heading, sentences)
            with self.subTest(readme=name):
                for phrase in self.CONTAINMENT:
                    self.assertNotIn(phrase, note.lower())
                self.assertIsNone(self.GUARDED.search(note))

    # The validation entry: what it implements, the setup update and the changed templates, the validation and the T2
    # skips, the setup-update check from a 0.28.0 installation in a scratch project scope, repo-check, no rehearsal, the
    # tag and the review round.
    ENTRY_HEADING = "\n## 0.29.0 delegation trusts the repository\n"
    ENTRY = (
        "Implements [the delegation trusts the repository spec](specs/repo-trust-split.md), committed in 919af63;",
        "**Setup update is required.**",
        "as `git diff-tree -r --name-only v0.28.0 HEAD -- templates skills/setup scripts` shows.",
        "To go back to 0.28.0, reinstall the 0.28.0 plugin and run `/cc-feather:setup update` the same way.",
        "(the 0.28.0 release ran 884, and 98042a0 ran 837).",
        "`.claude-plugin/marketplace.json` carries no version,",
        "No T2 case was skipped on this platform:",
        "`icacls <dir> /deny <user>:(RD)`",
        "in a scratch directory `<scratch>` outside the repository",
        "v0.28.0 was exported read-only with `git archive --format=tar v0.28.0 | tar -x -C <scratch>/v0.28.0`,",
        "`role_update_required: true`",
        "previewed changes to the six role definitions, `project/CLAUDE.md` and `project/.claude/cc-feather/state.json` only;",
        "The user's own scopes were not touched;",
        "abandoned on 2026-10-19",
        "kept on the local branch `repo-check-wip`",
        "No live review rehearsal was run for this release;",
        "`v0.29.0` does not exist when this entry is written.",
        "it is created only after the user's go-ahead.",
        "All reviews used the installed 0.28.0 roles and procedures from the plugin cache,",
        "found 6 Blocking and 10 Non-blocking items, all adopted.",
        "follow the commit carrying this entry and are recorded after it.",
    )

    def test_validation_entry_records_the_checks_setup_update_tag_and_review_round(self):
        text = self.text("docs/setup-validation.md")
        self.assertIn(self.ENTRY_HEADING, text)
        entry = self.section(text, self.ENTRY_HEADING)
        for sentence in self.ENTRY:
            with self.subTest(sentence=sentence[:40]):
                self.assertEqual(entry.count(sentence), 1)
        self.assertNotIn("No setup update is required", entry)
        self.assertIsNone(self.GUARDED.search(entry))
        # The setup-update check has its steps, in order, and each ticket its line in the review round, in order.
        steps = ("`check --project", "`python -I -B <tool> update", "`check` with `<tool>` then", "Going back:")
        positions = [entry.index(f"\n- {step}") for step in steps]
        self.assertEqual(positions, sorted(positions))
        tickets = [entry.index(f"\n- {line}") for line in ("Spec and plans:", "Ticket 01:", "Ticket 02:", "Ticket 03:",
                                                            "Ticket 04:")]
        self.assertEqual(tickets, sorted(tickets))
        # The entry was appended rather than rewriting an earlier one, and only the 0.30.0 entry follows it.
        after = text.split(self.ENTRY_HEADING, 1)[1][len(entry):]
        self.assertTrue(after.startswith(DelegationDedupeReleaseTests.ENTRY_HEADING))


class DelegationDedupeReleaseTests(unittest.TestCase):
    """0.30.0 (docs/specs/delegation-dedupe.md, Acceptance items 14 and 15): the manifest version is 0.30.0; the Updates
    note says the delegation rules are each written once and the reference explains and links, discloses the loading
    cost, says that no `/cc-feather:setup update` is needed because no role definition, policy template or their
    rendering changed, that the update takes effect in a fresh session and how to go back to 0.29.0, in both languages;
    the validation entry records the test counts, T1 and T2, the unchanged templates, the review round under S5, that no
    live review rehearsal was run and the tag."""

    # The Updates sections, paired in both languages: the section's opening sentence, then the 0.30.0 note in order.
    UPDATES = (
        ("## Updates and validation\n",
         "Plugin updates refresh the package; run setup update for the selected components to refresh external deployments, then start a fresh session, because roles and guidance are loaded when a session starts. ",
         "0.30.0 writes each delegation rule once, in the file responsible for it, with a pointer wherever else it applies, and main reads review state in full before a decision that depends on it; the [reference](docs/reference.md) now explains what each rule is for and links to the procedure that states it, and no rule changes.",
         "Counted by every file the links reach, each entry loads about 9 KB less; counted by the files main is told to read, every entry loads more, most of all the preview, the Stop threshold command and the brief of a claim's implementation, which now read review state in full; the [results](docs/specs/delegation-dedupe-results.md#loading-cost) record both.",
         "It changes no role definition, installed policy template or the setup tool's rendering of them, so existing installations need only the plugin update and a fresh session; no `/cc-feather:setup update` is needed.",
         "To go back to 0.29.0, reinstall the 0.29.0 plugin; no setup update or remove is needed."),
        ("## 更新、移除與驗證\n",
         "Plugin 更新只更新套件，需另跑 setup update 更新選定的已部署項目，完成後開新 session，因為角色與指引在 session 開始時載入。",
         "0.30.0 把每條分派規則只寫在負責它的檔案中，其他適用的地方改為指向它，主 Agent 在依賴 review state 的決定之前會完整讀過它；[參考文件](docs/reference.zh-TW.md)改為說明每條規則的用途並連到寫明它的流程，沒有任何規則改變。",
         "以連結所及的所有檔案計算，每個入口少載入約 9 KB；以主 Agent 被指示讀取的檔案計算，每個入口都載入更多，其中預覽、Stop threshold 指令與 claim 實作的 brief 增加最多，因為它們現在要完整讀 review state；兩種計算都記錄在[結果檔](docs/specs/delegation-dedupe-results.md#loading-cost)。",
         "它沒有改任何角色定義、已安裝的政策範本或 setup 工具對它們的產生方式，所以既有安裝只要更新 plugin 再開新 session；不需要做 `/cc-feather:setup update`。",
         "要回到 0.29.0，重新安裝 0.29.0 的 plugin 即可；不需要做 setup update 或先移除。"),
    )
    NO_SETUP_UPDATE = RetainedPassesReleaseTests.NO_SETUP_UPDATE

    @staticmethod
    def text(name):
        return (config.ROOT / name).read_text(encoding="utf-8")

    @staticmethod
    def section(text, heading):
        return text.split(heading, 1)[1].split("\n## ", 1)[0]

    def note(self, name, heading, sentences):
        section = self.section(self.text(name), heading)
        return section[section.index(sentences[0]):section.index(sentences[-1]) + len(sentences[-1])]

    # The manifest version is pinned by the current release's tests (0.31.0, handoff worktree store).

    def test_updates_sections_start_with_the_dedupe_note_in_both_languages(self):
        previous = RepoTrustSplitReleaseTests.UPDATES
        newer = HandoffWorktreeStoreReleaseTests.UPDATES
        for name, (heading, opening, *sentences), (_, _, previous_first, *_), (_, _, *newer_sentences) \
                in zip(("README.md", "README.zh-TW.md"), self.UPDATES, previous, newer):
            section = self.section(self.text(name), heading)
            for sentence in sentences:
                with self.subTest(readme=name, sentence=sentence[:30]):
                    self.assertEqual(section.count(sentence), 1)
            # The 0.30.0 note starts right after the 0.31.0 note, its sentences in order, before 0.29.0's.
            with self.subTest(readme=name, order=True):
                after_newer = section[section.index(newer_sentences[-1]) + len(newer_sentences[-1]):]
                self.assertTrue(after_newer.lstrip(" ").startswith(sentences[0]))
                for earlier, later in zip(sentences, sentences[1:] + [previous_first]):
                    self.assertLess(section.index(earlier), section.index(later))

    def test_updates_sections_state_that_no_setup_update_is_needed_in_both_languages(self):
        for name, (heading, _, *sentences), no_update in zip(("README.md", "README.zh-TW.md"), self.UPDATES, self.NO_SETUP_UPDATE):
            note = self.note(name, heading, sentences)
            with self.subTest(readme=name):
                self.assertEqual(note.count(no_update), 1)
                self.assertNotIn("need the plugin update and then", note)
                self.assertNotIn("再於每個裝有分派元件的範圍執行", note)

    def test_the_note_links_resolve(self):
        for name, (heading, _, *sentences) in zip(("README.md", "README.zh-TW.md"), self.UPDATES):
            for target in re.findall(r"\]\(([^)#]+)", self.note(name, heading, sentences)):
                with self.subTest(readme=name, target=target):
                    self.assertTrue((config.ROOT / target).is_file())
        self.assertIn("\n## Loading cost\n", self.text("docs/specs/delegation-dedupe-results.md"))

    # The validation entry: what it implements, no setup update with its check, the validation, T1 and T2, no
    # rehearsal, the tag and the review round.
    ENTRY_HEADING = "\n## 0.30.0 each delegation rule written once\n"
    ENTRY = (
        "Implements [the delegation dedupe spec](specs/delegation-dedupe.md), committed with its condition inventory in 471b6ff;",
        "**No setup update is required.**",
        "as `git diff-tree -r --name-only v0.29.0 HEAD -- templates scripts skills/setup/references/auto-review.md` shows",
        "To go back to 0.29.0, reinstall the 0.29.0 plugin; no setup update or remove is needed.",
        "at f4671bd, the commit of the installed 0.29.0, each ran 842 tests with 30 skips;",
        "[results file](specs/delegation-dedupe-results.md)",
        "T1, the verifier's two-way check of the condition inventory at 4a50719, reported REFUTED under the strict reading:",
        "T2: all eight scenarios passed;",
        "No live review rehearsal was run for this release;",
        "`v0.30.0` does not exist when this entry is written.",
        "it is created only after the user's go-ahead.",
        "All reviews used the installed 0.29.0 roles and procedures from the plugin cache,",
        "follow the commit carrying this entry and are recorded after it.",
    )

    def test_validation_entry_records_the_checks_evidence_tag_and_review_round(self):
        text = self.text("docs/setup-validation.md")
        self.assertIn(self.ENTRY_HEADING, text)
        entry = self.section(text, self.ENTRY_HEADING)
        for sentence in self.ENTRY:
            with self.subTest(sentence=sentence[:40]):
                self.assertEqual(entry.count(sentence), 1)
        self.assertNotIn("Setup update is required", entry)
        # Each ticket has its line in the review round, in order.
        tickets = [entry.index(f"\n- {line}") for line in ("Spec and plans:", "Ticket 01:", "Ticket 02:", "Ticket 03:",
                                                            "Ticket 04:", "Ticket 05:")]
        self.assertEqual(tickets, sorted(tickets))
        # The entry was appended rather than rewriting an earlier one, and only the 0.31.0 entry follows it.
        after = text.split(self.ENTRY_HEADING, 1)[1][len(entry):]
        self.assertTrue(after.startswith(HandoffWorktreeStoreReleaseTests.ENTRY_HEADING))


class HandoffWorktreeStoreReleaseTests(unittest.TestCase):
    """0.31.0 (docs/specs/handoff-worktree-store.md, Acceptance item 12's README share, items 13 and 14; ticket 07):
    the manifest version is 0.31.0; both READMEs replace the statement that there is no cross-session transaction lock
    or automatic worktree synchronization with what is shared, what is not, what the history lock covers, the sandbox
    requirement and how codex-feather sessions behave; the Updates note says the plugin update and a fresh session are
    enough, describes codex-feather mixed use and how to go back to 0.30.0 with shared-store records still readable;
    CONTEXT.md defines Handoff store and Working checkout and Active handoff refers to the Handoff store; ADR 0018
    records the store and lock choices and cites the validation entry's rehearsal; the validation entry records the
    checks, ticket 03's Windows rehearsal, the tag and the review round."""

    README_HANDOFF = (
        ("README.md", "## Handoff compatibility\n", (
            "The checkouts of one Git repository share one Handoff store: a linked worktree whose records are not tracked keeps them in the main worktree's `.feather/handoffs/`, so removing or archiving the worktree no longer deletes them, and a session in any of those checkouts lists the same work and searches one history.",
            "Sources, baselines and a record's environment still describe the checkout the session works in.",
            "A checkout that tracks its records, a non-Git project and an explicit root keep their own store, and nothing is synchronized across projects.",
            "A session in a linked worktree needs write access to the main worktree's store; when the operating system or the session's sandbox denies it, the tool reports `store-unwritable` and writes nothing in the worktree in its place.",
            "Completion, archive, clear, seal and adopt take a history lock in the store, so sessions sharing it cannot lose each other's completions; writes to a work file take no lock, so keep one writer per work item.",
            "Records that an earlier version left in another checkout are listed with that checkout, and `adopt` moves the ones you confirm into the current store.",
            "Until codex-feather adopts the same runtime, Codex sessions keep writing records inside a linked worktree, which a list from a Claude session reports as another checkout's store.",
            "Existing tracking choices and handoff ignore behavior are preserved."),
         "There is no cross-session transaction lock or automatic worktree synchronization."),
        ("README.zh-TW.md", "## 交接相容性\n", (
            "同一個 Git 儲存庫的各個 checkout 共用一個交接存放處：未追蹤交接紀錄的 linked worktree 會把紀錄存在 main worktree 的 `.feather/handoffs/`，所以移除或封存 worktree 不會再刪掉它們，而在任一個 checkout 中的 session 都列出同樣的工作、搜尋同一份歷史。",
            "來源、來源基準與紀錄的環境仍描述 session 所在的 checkout。",
            "追蹤自己紀錄的 checkout、非 Git 專案與明確指定的根目錄保留自己的存放處，跨專案也不做任何同步。",
            "linked worktree 中的 session 需要能寫入 main worktree 的存放處；作業系統或 session 的 sandbox 拒絕時，工具回報 `store-unwritable`，不會改寫在 worktree 中。",
            "完成、archive、clear、seal 與 adopt 會在存放處取得歷史鎖，所以共用它的 session 不會互相弄丟完成紀錄；寫入工作檔不取鎖，所以每項工作仍只有一個寫入者。",
            "較早版本留在其他 checkout 的紀錄會連同那個 checkout 列出，`adopt` 會把你確認的部分移到目前的存放處。",
            "在 codex-feather 採用同一個 runtime 之前，Codex session 仍把紀錄寫在 linked worktree 內，Claude session 的列表會把它們列為另一個 checkout 的存放處。",
            "交接工具依原有規則處理 Git 忽略與使用者追蹤選擇。"),
         "無跨 session 交易鎖或 worktree 自動同步"),
    )

    # The Updates sections, paired in both languages: the section's opening sentence, then the 0.31.0 note in order.
    UPDATES = (
        ("## Updates and validation\n",
         "Plugin updates refresh the package; run setup update for the selected components to refresh external deployments, then start a fresh session, because roles and guidance are loaded when a session starts. ",
         "0.31.0 keeps the handoff records of a linked worktree in the main worktree's store, adds a history lock with an `unlock` command for a stale one, lists records left in other checkouts and moves the ones you confirm with `adopt`, as [Handoff compatibility](#handoff-compatibility) describes.",
         "Like 0.30.0, it changes no role definition, installed policy template or the setup tool's rendering of them, so existing installations need only the plugin update and a fresh session; no `/cc-feather:setup update` is needed.",
         "Until codex-feather adopts the same runtime, Codex sessions keep writing records inside a linked worktree; a Claude session's list reports them under the other checkout's store, and `adopt` moves the ones you confirm.",
         "To go back to 0.30.0, reinstall the 0.30.0 plugin; no setup update or remove is needed, records written to the main worktree's store stay readable there by 0.30.0 in the main worktree, and a 0.30.0 session in a linked worktree sees only that worktree's own records again."),
        ("## 更新、移除與驗證\n",
         "Plugin 更新只更新套件，需另跑 setup update 更新選定的已部署項目，完成後開新 session，因為角色與指引在 session 開始時載入。",
         "0.31.0 把 linked worktree 的交接紀錄存在 main worktree 的存放處，新增歷史鎖與清除過期鎖的 `unlock` 指令，列出留在其他 checkout 的紀錄，並以 `adopt` 移動你確認的部分，詳見[交接相容性](#交接相容性)。",
         "這一版同樣沒有改任何角色定義、已安裝的政策範本或 setup 工具對它們的產生方式，所以既有安裝只要更新 plugin 再開新 session；不需要做 `/cc-feather:setup update`。",
         "在 codex-feather 採用同一個 runtime 之前，Codex session 仍把紀錄寫在 linked worktree 內；Claude session 的列表會把它們列在那個 checkout 的存放處下，`adopt` 會移動你確認的部分。",
         "要回到 0.30.0，重新安裝 0.30.0 的 plugin 即可；不需要做 setup update 或先移除，寫入 main worktree 存放處的紀錄在 main worktree 中仍可由 0.30.0 讀取，而 linked worktree 中的 0.30.0 session 又只會看到該 worktree 自己的紀錄。"),
    )
    NO_SETUP_UPDATE = RetainedPassesReleaseTests.NO_SETUP_UPDATE

    GLOSSARY = {
        "Handoff store": (
            "The `.feather/handoffs/` directory that holds a project's handoff records, history, sealed archives and history lock.",
            "In an untracked linked worktree of a Git repository it is the main worktree's, shared by every checkout of that repository; in the main worktree, a non-Git project, an explicit root and a checkout that tracks its records, it is under the Working checkout.",
            "The handoff tool reports it as `root.store`; when it cannot write a shared Handoff store, it never writes the records in the Working checkout in its place."),
        "Working checkout": (
            "The checkout a session works in: the Git top level of the directory the handoff tool is given, or that directory itself for a non-Git project or an explicit root.",
            "Sources, baselines, tracking detection and a record's environment describe it, never the Handoff store's checkout.",
            "The handoff tool reports it as `root.checkout`."),
        "Active handoff": ("An unfinished Feather handoff record for the work in the Handoff store.",),
    }

    ADR = "docs/adr/0018-linked-worktrees-share-the-main-worktree-store.md"
    ADR_SENTENCES = (
        "# Linked worktrees share the main worktree's Handoff store\n",
        "- **The main worktree holds the store.**",
        "- **A history lock.**",
        "- **The Git common directory**",
        "- **Per-worktree records with synchronization**",
        "- **An external single-writer rule instead of a lock**",
        "the rehearsal recorded under 0.31.0 in [setup validation](../setup-validation.md#0310-handoff-worktree-store) observed that it does.",
    )

    @staticmethod
    def text(name):
        return (config.ROOT / name).read_text(encoding="utf-8")

    @staticmethod
    def section(text, heading):
        return text.split(heading, 1)[1].split("\n## ", 1)[0]

    def note(self, name, heading, sentences):
        section = self.section(self.text(name), heading)
        return section[section.index(sentences[0]):section.index(sentences[-1]) + len(sentences[-1])]

    # The manifest version is pinned by the current release's tests (0.32.0, resource-risk runs).

    def test_readmes_replace_the_worktree_statement_in_both_languages(self):
        for name, heading, sentences, removed in self.README_HANDOFF:
            section = self.section(self.text(name), heading)
            with self.subTest(readme=name, removed=True):
                self.assertNotIn(removed, self.text(name))
            # One paragraph, its sentences in order.
            paragraph = section[section.index(sentences[0]):section.index(sentences[-1]) + len(sentences[-1])]
            self.assertNotIn("\n", paragraph)
            for sentence in sentences:
                with self.subTest(readme=name, sentence=sentence[:30]):
                    self.assertEqual(section.count(sentence), 1)
            for earlier, later in zip(sentences, sentences[1:]):
                self.assertLess(section.index(earlier), section.index(later))

    def test_updates_sections_start_with_the_worktree_store_note_in_both_languages(self):
        previous = DelegationDedupeReleaseTests.UPDATES
        newer = ResourceRiskRunsReleaseTests.UPDATES
        for name, (heading, opening, *sentences), (_, _, previous_first, *_), (_, _, *newer_sentences) \
                in zip(("README.md", "README.zh-TW.md"), self.UPDATES, previous, newer):
            section = self.section(self.text(name), heading)
            for sentence in sentences:
                with self.subTest(readme=name, sentence=sentence[:30]):
                    self.assertEqual(section.count(sentence), 1)
            # The 0.31.0 note starts right after the 0.32.0 note, its sentences in order, before 0.30.0's.
            with self.subTest(readme=name, order=True):
                after_newer = section[section.index(newer_sentences[-1]) + len(newer_sentences[-1]):]
                self.assertTrue(after_newer.lstrip(" ").startswith(sentences[0]))
                for earlier, later in zip(sentences, sentences[1:] + [previous_first]):
                    self.assertLess(section.index(earlier), section.index(later))

    def test_updates_sections_state_that_no_setup_update_is_needed_in_both_languages(self):
        for name, (heading, _, *sentences), no_update in zip(("README.md", "README.zh-TW.md"), self.UPDATES, self.NO_SETUP_UPDATE):
            note = self.note(name, heading, sentences)
            with self.subTest(readme=name):
                self.assertEqual(note.count(no_update), 1)
                self.assertNotIn("need the plugin update and then", note)
                self.assertNotIn("再於每個裝有分派元件的範圍執行", note)

    def test_the_note_links_to_the_handoff_section(self):
        for name, (heading, _, *sentences), (link, target) in zip(
                ("README.md", "README.zh-TW.md"), self.UPDATES,
                (("(#handoff-compatibility)", "\n## Handoff compatibility\n"), ("(#交接相容性)", "\n## 交接相容性\n"))):
            with self.subTest(readme=name):
                self.assertIn(link, self.note(name, heading, sentences))
                self.assertIn(target, self.text(name))

    def test_glossary_defines_the_store_and_the_checkout(self):
        text = self.text("CONTEXT.md")
        for term, sentences in self.GLOSSARY.items():
            heading = f"\n**{term}**:\n"
            with self.subTest(term=term):
                self.assertEqual(text.count(heading), 1)
            entry = text.split(heading, 1)[1].split("\n_Avoid_:", 1)[0]
            for sentence in sentences:
                with self.subTest(term=term, sentence=sentence[:30]):
                    self.assertEqual(entry.count(sentence), 1)
        self.assertNotIn("under the project's `.feather/handoffs/`", text)
        # The two new terms come right after Active handoff, which stays right after Dispatch record.
        positions = [text.index(f"\n**{term}**:\n") for term in ("Active handoff", "Handoff store", "Working checkout")]
        self.assertEqual(positions, sorted(positions))

    def test_adr_0018_records_the_store_and_lock_choices(self):
        text = self.text(self.ADR)
        for sentence in self.ADR_SENTENCES:
            with self.subTest(sentence=sentence[:40]):
                self.assertEqual(text.count(sentence), 1)
        # It cites the validation entry's rehearsal, not a gitignored ticket.
        self.assertNotIn(".scratch", text)
        self.assertIn("\n## 0.31.0 handoff worktree store\n", self.text("docs/setup-validation.md"))

    # The validation entry: what it implements, no setup update with its check and the 0.30.0 read-back, codex-feather,
    # the validation, ticket 03's rehearsal, no live review rehearsal, the tag and the review round.
    ENTRY_HEADING = "\n## 0.31.0 handoff worktree store\n"
    ENTRY = (
        "Implements [the handoff worktree store spec](specs/handoff-worktree-store.md), committed in 670665c and updated after its security analysis in 4d7f4d9;",
        "[ADR 0018](adr/0018-linked-worktrees-share-the-main-worktree-store.md)",
        "**No setup update is required.**",
        "as `git diff-tree -r --name-only v0.30.0 HEAD -- templates scripts skills/setup skills/delegation` shows by printing nothing;",
        "To go back to 0.30.0, reinstall the 0.30.0 plugin; no setup update or remove is needed.",
        "0.30.0's `list` from the main worktree returned `ok` with that work and no issue,",
        "Mixed use with codex-feather:",
        "(the 0.30.0 release ran 872 tests with 30 skips).",
        "`.claude-plugin/marketplace.json` carries no version,",
        "Rehearsal in a real linked worktree on Windows (2026-11-06, ticket 03):",
        "A desktop worktree session on Windows can therefore write the main worktree's store, and the store choice stands.",
        "No live review rehearsal was run for this release;",
        "`v0.31.0` does not exist when this entry is written.",
        "it is created only after the user's go-ahead.",
        "All reviews used the installed 0.30.0 roles and procedures from the plugin cache,",
        "follow the commit carrying this entry and are recorded after it.",
    )

    def test_validation_entry_records_the_checks_rehearsal_tag_and_review_round(self):
        text = self.text("docs/setup-validation.md")
        self.assertIn(self.ENTRY_HEADING, text)
        entry = self.section(text, self.ENTRY_HEADING)
        for sentence in self.ENTRY:
            with self.subTest(sentence=sentence[:40]):
                self.assertEqual(entry.count(sentence), 1)
        self.assertNotIn("Setup update is required", entry)
        self.assertNotIn(".scratch", entry)
        # Each ticket has its line in the review round, in order.
        tickets = [entry.index(f"\n- {line}") for line in ("Spec and plans:", "Ticket 01:", "Ticket 02:", "Ticket 03:",
                                                            "Ticket 04:", "Ticket 05:", "Ticket 06:", "Ticket 07:")]
        self.assertEqual(tickets, sorted(tickets))
        # The entry was appended rather than rewriting an earlier one, and only the 0.32.0 entry follows it.
        after = text.split(self.ENTRY_HEADING, 1)[1][len(entry):]
        self.assertTrue(after.startswith(ResourceRiskRunsReleaseTests.ENTRY_HEADING))


class ResourceRiskRunsReleaseTests(unittest.TestCase):
    """0.32.0 (docs/specs/resource-risk-runs.md, Acceptance items 10, 11, 13's ADR, 15 and 16; ticket 07): the manifest
    version is 0.32.0; the Updates note says what changed, that the hard limit covers only commands run through the
    Runner, advises against a permission rule that allows every Runner invocation, names the changed role definitions so
    existing installations run `/cc-feather:setup update` and start a fresh session, and says how to go back to 0.31.0,
    in both languages; both reference documents describe the four layers, the Runner and its boundary; ADR 0019 records
    the layered decision and its five rejected alternatives; none of them states a concrete budget or language-specific
    setting; the validation entry records the tickets, the setup update, the test runs, the Runner per environment, the
    live rehearsal, what the tests cannot show, the tag and the review round."""

    # The Updates sections, paired in both languages: the section's opening sentence, then the 0.32.0 note in order.
    UPDATES = (
        ("## Updates and validation\n",
         "Plugin updates refresh the package; run setup update for the selected components to refresh external deployments, then start a fresh session, because roles and guidance are loaded when a session starts. ",
         "0.32.0 adds resource-risk runs: plan review marks a claim whose checks or verification foreseeably risk exhausting memory, time or the machine as a Resource-risk claim and proposes an Execution method for its risky part, main approves it with a budget from you, the plan or your guidance, a role runs that part only inside the Runner, a new launcher in the delegation skill that limits the memory of a command's whole process tree, its time and its output, a new or modified test or probe whose bound is unknown or does not fit the budget goes back to main instead of running, and what was returned or stopped is recorded as an Observed resource risk, as the [reference](docs/reference.md#resource-limits) describes.",
         "cc-feather states no budget, and the hard limit covers only commands run through the Runner, not work handed to an already running service or tools that execute code outside the shell.",
         "A Runner invocation goes through your normal permission handling; do not add a permission rule that allows every Runner invocation, because such a rule allows any command through the Runner.",
         "It changes the analyst, executor, security-executor, verifier, reviewer and adversary role definitions, so existing installations need the plugin update, then `/cc-feather:setup update` in every scope where delegation is installed, then a fresh session; until then `check` warns that those roles are from an older template.",
         "To go back to 0.31.0, reinstall the 0.31.0 plugin and run `/cc-feather:setup update` in every scope where delegation is installed, then start a fresh session, so that it restores the 0.31.0 role definitions; no remove is needed."),
        ("## 更新、移除與驗證\n",
         "Plugin 更新只更新套件，需另跑 setup update 更新選定的已部署項目，完成後開新 session，因為角色與指引在 session 開始時載入。",
         "0.32.0 新增資源風險執行：計畫審查把執行檢查或驗證時可預見會耗盡記憶體、時間或機器的 claim 標為 Resource-risk claim，並為有風險的部分提出 Execution method，主 Agent 以來自你、計畫或你的指引的預算核准它，角色只在 Runner 內執行那個部分（Runner 是分派 skill 中新增的啟動器，限制一個指令整個 process tree 的記憶體、它的時間與輸出），界限不明或不符合預算的新的或修改過的測試或 probe 交回主 Agent 而不執行，交回或被停下的部分記為 Observed resource risk，詳見[參考文件](docs/reference.zh-TW.md#資源限制)。",
         "cc-feather 不規定任何預算，硬性限制只涵蓋透過 Runner 執行的指令，不涵蓋交給已經在執行的服務的工作，也不涵蓋在 shell 之外執行程式碼的工具。",
         "Runner 的呼叫經過你平常的權限處理；不要新增允許所有 Runner 呼叫的權限規則，因為這種規則等於允許任何指令透過 Runner 執行。",
         "它改了 analyst、executor、security-executor、verifier、reviewer 與 adversary 的角色定義，所以既有安裝要先更新 plugin，再於每個裝有分派元件的範圍執行 `/cc-feather:setup update`，然後開新 session；在那之前，check 會提醒這些角色來自較舊的範本。",
         "要回到 0.31.0，重新安裝 0.31.0 的 plugin，並在每個裝有分派元件的範圍執行 `/cc-feather:setup update`，再開新 session，讓它還原 0.31.0 的角色定義；不需要先移除。"),
    )
    NO_SETUP_UPDATE = RetainedPassesReleaseTests.NO_SETUP_UPDATE
    # The role definitions this release changes (`git diff --name-only v0.31.0 HEAD -- templates`), and those it does not.
    CHANGED_ROLES = ("analyst", "executor", "security-executor", "verifier", "reviewer", "adversary")
    UNCHANGED_ROLES = ("scout", "mech-executor", "Explore")
    # Out of Scope: concrete budgets and language-specific settings belong in project guidance, not in these documents.
    NUMBERS = re.compile(r"\d\s*(?:[KMG]i?B|ms|seconds?)\b|GOMEMLIMIT|-parallel\b|\s-p\s", re.I)

    # Both reference documents: the section beside the roles' execution, its four layers, the Runner's boundary with the
    # two Linux cases from ticket 02's reviews, and the permission advice.
    REFERENCE = (
        ("docs/reference.md", "\n### Resource limits\n", "\n### Repository safety\n", (
            "1. **Plan review marks the risk:**",
            "A claim it does not mark is not thereby safe.",
            "2. **Main approves, the Runner contains:**",
            "3. **A floor for every run:**",
            "4. **What happened is recorded:**",
            "the Runner is never an isolated environment you named.",
            "Its boundary is that only processes inside the Runner's containment are limited:",
            "Two runs started at the same time each check available memory on their own, so their total is not limited;",
            "On Linux, a target running as the same user can raise its own scope's memory limit after the Runner's checks, or leave the scope by creating a new one through the systemd user manager, as `systemd-run --user` does.",
            "On Linux, a Runner started inside another Runner's target gets its own scope outside the outer one, so the outer limit no longer covers it; the inner limit still applies.",
            "Do not add a rule that allows every Runner invocation: such a rule allows any command through the Runner.",
            "A rule written for the target alone no longer matches once the target is wrapped in the Runner.",
            "no hook enforces that a role uses the Runner.")),
        ("docs/reference.zh-TW.md", "\n### 資源限制\n", "\n### 儲存庫安全\n", (
            "1. **計畫審查標示風險：**",
            "沒有被標示的 claim 不因此就是安全的。",
            "2. **主 Agent 核准，Runner 圍住：**",
            "3. **每次執行都有底線：**",
            "4. **記錄發生的事：**",
            "Runner 也絕不算是你指定的隔離環境。",
            "它的邊界是只有 Runner 圍住的 process 受到限制：",
            "同時啟動的兩次執行各自檢查可用記憶體，所以兩者的總和不受限制；",
            "在 Linux 上，以同一個使用者身分執行的目標，可以在 Runner 檢查之後調高自己 scope 的記憶體限制，或透過 systemd user manager 建立新的 scope 而離開原本的 scope（如同 `systemd-run --user` 所做的）。",
            "在 Linux 上，在另一個 Runner 的目標內啟動的 Runner 會有自己的 scope，位於外層 scope 之外，所以外層的限制不再涵蓋它；內層的限制仍然有效。",
            "不要新增允許所有 Runner 呼叫的規則：這種規則等於允許任何指令透過 Runner 執行。",
            "只為目標指令本身寫的規則，在目標包進 Runner 之後就不再符合。",
            "沒有任何 hook 強制角色使用 Runner。")),
    )
    REFERENCE_LINKS = ("(../skills/delegation/references/resource-risk-runs.md)",
                       "(adr/0019-resource-risk-is-marked-at-plan-review-and-contained-by-the-runner.md)")

    ADR = "docs/adr/0019-resource-risk-is-marked-at-plan-review-and-contained-by-the-runner.md"
    # The layered decision, then the five rejected alternatives with their reasons.
    ADR_DECISION = (
        "# Resource risk is marked at plan review and contained by the Runner\n",
        "budgets that come from the user, the Plan or the user's guidance and never from cc-feather",
        "- **Plan review marks the risk.**",
        "A missing mark is not a statement that a Claim is safe.",
        "- **Main approves the method with a budget.**",
        "It adds to Execution and never replaces it.",
        "- **The Runner contains the risky part.**",
        "- **A floor for every run.**",
        "The floor follows execution, not authorship,",
        "- **What happened is recorded.**",
        "[resource-risk reference](../../skills/delegation/references/resource-risk-runs.md)",
    )
    ADR_REJECTED = (
        ("- **Judging risk only at each run**", "The role that misjudged a probe stays the only judge of it,"),
        ("- **A two-phase paused call**", "It needs a new paused state in review counting;"),
        ("- **A separate resource-analysis command**", "so the judgement is one item there and adds no verdict of its own,"),
        ("- **Enforcing Runner use with a hook now**", "it is left to a later, separately gated release."),
        ("- **A watchdog**", "a watchdog stopped nothing,"),
    )
    ADR_CONSEQUENCES = (
        "Only processes inside the Runner's containment are limited:",
        "so their total is not limited.",
        "cc-feather advises against a rule that allows every Runner invocation.",
        "no hook enforces that a role uses the Runner,",
        "[setup validation](../setup-validation.md#0320-resource-risk-runs)",
    )

    @staticmethod
    def text(name):
        return (config.ROOT / name).read_text(encoding="utf-8")

    @staticmethod
    def section(text, heading):
        return text.split(heading, 1)[1].split("\n## ", 1)[0]

    def note(self, name, heading, sentences):
        section = self.section(self.text(name), heading)
        return section[section.index(sentences[0]):section.index(sentences[-1]) + len(sentences[-1])]

    # The manifest version is pinned by the current release's tests (0.33.0, checkout leases).

    def test_updates_sections_start_with_the_resource_risk_note_in_both_languages(self):
        previous = HandoffWorktreeStoreReleaseTests.UPDATES
        newer = CheckoutLeasesReleaseTests.UPDATES
        for name, (heading, opening, *sentences), (_, _, previous_first, *_), (_, _, *newer_sentences) \
                in zip(("README.md", "README.zh-TW.md"), self.UPDATES, previous, newer):
            section = self.section(self.text(name), heading)
            for sentence in sentences:
                with self.subTest(readme=name, sentence=sentence[:30]):
                    self.assertEqual(section.count(sentence), 1)
            # The 0.32.0 note starts right after the 0.33.0 note, its sentences in order, before 0.31.0's.
            with self.subTest(readme=name, order=True):
                after_newer = section[section.index(newer_sentences[-1]) + len(newer_sentences[-1]):]
                self.assertTrue(after_newer.lstrip(" ").startswith(sentences[0]))
                for earlier, later in zip(sentences, sentences[1:] + [previous_first]):
                    self.assertLess(section.index(earlier), section.index(later))

    def test_updates_sections_require_setup_update_in_both_languages(self):
        for name, (heading, _, *sentences), no_update in zip(("README.md", "README.zh-TW.md"), self.UPDATES, self.NO_SETUP_UPDATE):
            note = self.note(name, heading, sentences)
            with self.subTest(readme=name):
                # The note asks for setup update after the plugin update and for going back, and never says it is not needed.
                self.assertEqual(note.count("`/cc-feather:setup update`"), 2)
                self.assertNotIn(no_update, note)
                self.assertNotIn("need only the plugin update", note)
                self.assertNotIn("只要更新 plugin", note)

    def test_the_note_names_every_role_definition_the_release_changes(self):
        for name, (heading, _, *sentences) in zip(("README.md", "README.zh-TW.md"), self.UPDATES):
            note = self.note(name, heading, sentences)
            for role in self.CHANGED_ROLES:
                with self.subTest(readme=name, role=role):
                    self.assertIn(role, note)
            for role in self.UNCHANGED_ROLES:
                with self.subTest(readme=name, unchanged=role):
                    self.assertNotIn(role, note)

    def test_the_note_links_to_the_reference_section(self):
        for name, (heading, _, *sentences), (link, document, target) in zip(
                ("README.md", "README.zh-TW.md"), self.UPDATES,
                (("(docs/reference.md#resource-limits)", "docs/reference.md", "\n### Resource limits\n"),
                 ("(docs/reference.zh-TW.md#資源限制)", "docs/reference.zh-TW.md", "\n### 資源限制\n"))):
            with self.subTest(readme=name):
                self.assertIn(link, self.note(name, heading, sentences))
                self.assertEqual(self.text(document).count(target), 1)

    def test_reference_documents_describe_the_layers_the_runner_and_its_boundary(self):
        for name, heading, previous, sentences in self.REFERENCE:
            text = self.text(name)
            with self.subTest(document=name):
                self.assertEqual(text.count(heading), 1)
                # The section sits right after the repository safety section, which describes the roles' execution.
                self.assertLess(text.index(previous), text.index(heading))
                self.assertEqual(text.split(previous, 1)[1].count("\n### "), text.split(heading, 1)[1].count("\n### ") + 1)
            section = text.split(heading, 1)[1].split("\n### ", 1)[0]
            for sentence in sentences:
                with self.subTest(document=name, sentence=sentence[:30]):
                    self.assertEqual(section.count(sentence), 1)
            for earlier, later in zip(sentences, sentences[1:]):
                self.assertLess(section.index(earlier), section.index(later))
            for link in self.REFERENCE_LINKS:
                with self.subTest(document=name, link=link):
                    self.assertIn(link, section)

    def test_adr_0019_records_the_layered_decision_and_the_rejected_alternatives(self):
        text = self.text(self.ADR)
        decision, rest = text.split("\n## Considered Options\n", 1)
        options, consequences = rest.split("\n## Consequences\n", 1)
        for sentence in self.ADR_DECISION:
            with self.subTest(sentence=sentence[:40]):
                self.assertEqual(decision.count(sentence), 1)
        # Exactly the five rejected alternatives, each with its reason in its own item.
        self.assertEqual(options.count("\n- **"), len(self.ADR_REJECTED))
        for option, reason in self.ADR_REJECTED:
            with self.subTest(option=option):
                item = options.split(option, 1)[1].split("\n- **", 1)[0]
                self.assertIn(reason, item)
        for sentence in self.ADR_CONSEQUENCES:
            with self.subTest(sentence=sentence[:40]):
                self.assertEqual(consequences.count(sentence), 1)
        self.assertNotIn(".scratch", text)
        self.assertIn(self.ENTRY_HEADING, self.text("docs/setup-validation.md"))

    def test_no_document_states_a_budget_or_a_language_specific_setting(self):
        documents = [self.text(self.ADR)]
        documents += [self.note(name, heading, sentences)
                      for name, (heading, _, *sentences) in zip(("README.md", "README.zh-TW.md"), self.UPDATES)]
        documents += [self.text(name).split(heading, 1)[1].split("\n### ", 1)[0] for name, heading, _, _ in self.REFERENCE]
        for document in documents:
            with self.subTest(document=document[:40]):
                self.assertIsNone(self.NUMBERS.search(document))

    # The validation entry: the spec and its tickets with their commits, the setup update and where it was observed, the
    # test runs, the Runner per environment with its hosts, the rehearsal with its outcome, deviations and the
    # auto-update, what the tests cannot show, the tag and the review round.
    ENTRY_HEADING = "\n## 0.32.0 resource-risk runs\n"
    ENTRY = (
        "Implements [the resource-risk runs spec](specs/resource-risk-runs.md), added in f9e87cd and revised in 78c82c1",
        "ticket 01, the Runner core and its Windows backend, in affcca5 and 3539946;",
        "ticket 02, the Runner's Linux backend, in 94a36b5;",
        "ticket 03, the floor, returned probes and Observed resource risk, in 59dbd81;",
        "in 729a588;",
        "in d07474f;",
        "ticket 06, the live rehearsal, with no commit;",
        "[ADR 0019](adr/0019-resource-risk-is-marked-at-plan-review-and-contained-by-the-runner.md)",
        "**Setup update is required.**",
        "as `git diff-tree -r --name-only v0.31.0 HEAD -- templates skills/setup scripts` shows.",
        "To go back to 0.31.0, reinstall the 0.31.0 plugin and run `/cc-feather:setup update` the same way.",
        "The setup update from 0.31.0 was observed in scratch installations:",
        "`python -B -m unittest discover -s tests -t .` and `python -B -m unittest discover -s tests`, with `FEATHER_LINK_TEST_DIR` under `J:\\gotmp\\`",
        "(the 0.31.0 release ran 1031 tests with 13 skips).",
        "`.claude-plugin/marketplace.json` carries no version,",
        "- Windows, through a job object: Windows 11 Pro 10.0.26100 (build 26100), Python 3.11.9, with the Runner not started inside a job (`IsProcessInJob` false).",
        "- Linux, through a transient systemd user scope: WSL2 on Windows 11 Pro 10.0.26100, kernel 6.18.54.1-microsoft-standard-WSL2, Ubuntu 24.04.4 LTS, systemd 255 (255.4-1ubuntu8.17), cgroup v2 with `cpu memory pids` delegated to `user@1000.service`, Python 3.12.3.",
        "Live rehearsal (2026-11-09, ticket 06).",
        "the cbc-go incident probe was not used or run.",
        "outcome verification call 2 returned CONFIRMED with no run stopped and no probe returned;",
        "Nothing was landed,",
        "68 files, were byte-identical before and after.",
        "Three deviations were seen, none of which changed an outcome:",
        "Claude Code's auto-update changed the user's installed cc-feather from 0.30.0 to 0.31.0,",
        "neither they nor one rehearsal can show that a model always follows the rules.",
        "`v0.32.0` does not exist when this entry is written.",
        "it is created only after the user's go-ahead.",
        "follow the commit carrying this entry and are recorded after it.",
    )

    def test_validation_entry_records_the_checks_runner_rehearsal_tag_and_review_round(self):
        text = self.text("docs/setup-validation.md")
        self.assertEqual(text.count(self.ENTRY_HEADING), 1)
        entry = self.section(text, self.ENTRY_HEADING)
        for sentence in self.ENTRY:
            with self.subTest(sentence=sentence[:40]):
                self.assertEqual(entry.count(sentence), 1)
        self.assertNotIn("No setup update is required", entry)
        self.assertNotIn(".scratch", entry)
        # Each ticket has its line in the review round, in order.
        tickets = [entry.index(f"\n- {line}") for line in ("Spec and plans:", "Ticket 01:", "Ticket 02:", "Ticket 03:",
                                                            "Ticket 04:", "Ticket 05:", "Ticket 06:", "Ticket 07:")]
        self.assertEqual(tickets, sorted(tickets))
        # The entry was appended rather than rewriting an earlier one, and only the 0.33.0 entry follows it.
        after = text.split(self.ENTRY_HEADING, 1)[1][len(entry):]
        self.assertTrue(after.startswith(CheckoutLeasesReleaseTests.ENTRY_HEADING))


class CheckoutLeasesReleaseTests(unittest.TestCase):
    """0.33.0 (docs/specs/checkout-leases.md, Further Notes' release and Out of Scope; ticket 07): the manifest version is
    0.33.0; the Updates note says what Checkout leases are, that a lease is cooperative and its lock relies on Claude
    Code's cleanup skipping locked worktrees, that existing installations need no setup update, how the rules reach a
    session started in a linked worktree, and how to go back to 0.32.0 by removing the `leases` component first, in both
    languages; both READMEs, the setup documentation and the compatibility notes describe leases, the `leases` component,
    the lease format and location for other tools, the cooperative limits and the reliance on Claude Code's cleanup; the
    validation entry records the tickets, the setup determination and downgrade check, the test runs, the rehearsal
    with its Execution method, the interactive session and its finding, the tag and the review round."""

    # The Updates sections, paired in both languages: the section's opening sentence, then the 0.33.0 note in order.
    UPDATES = (
        ("## Updates and validation\n",
         "Plugin updates refresh the package; run setup update for the selected components to refresh external deployments, then start a fresh session, because roles and guidance are loaded when a session starts. ",
         "0.33.0 adds Checkout leases: a cooperative record in `.feather/leases/` under the main worktree that one session is using one checkout of a Git repository to change it, protected on a linked worktree by a Git worktree lock, the opt-in `leases` setup component that tells main when to take, renew and return a lease, and `/cc-feather:worktrees`, which lists every checkout with its lease, lock and the work left in it, as [Checkout leases](#checkout-leases) describes.",
         "A lease binds only sessions that follow the rules, and its lock relies on Claude Code's cleanup skipping locked worktrees.",
         "It changes no role definition and no handoff or delegation policy template, and the setup tool only gains the `leases` component, which `both` never includes, so existing installations need only the plugin update and a fresh session; no `/cc-feather:setup update` is needed.",
         "To keep leases, install the `leases` component; a project-scope block reaches a session started in a linked worktree only through that worktree's own CLAUDE.md, so install it in user scope, or commit and push the project CLAUDE.md block, to make every session follow the rules, and the same holds for the handoff and delegation components.",
         "To go back to 0.32.0, first run `/cc-feather:setup remove` for the `leases` component in every scope where it is installed, because the 0.32.0 setup tool refuses such a scope with `state component schema mismatch` and changes nothing, then reinstall the 0.32.0 plugin.",
         "Return any lease still held before reinstalling, since 0.32.0 has no lease tool and a lease left behind keeps its Git worktree lock until `git worktree unlock` removes it."),
        ("## 更新、移除與驗證\n",
         "Plugin 更新只更新套件，需另跑 setup update 更新選定的已部署項目，完成後開新 session，因為角色與指引在 session 開始時載入。",
         "0.33.0 新增 Checkout lease：存在 main worktree 下 `.feather/leases/` 的合作式紀錄，表示某個 session 正在使用 Git 儲存庫的某一個 checkout 來修改它，在 linked worktree 上另由 Git worktree lock 保護；選用的 `leases` setup 元件告訴主 Agent 何時取得、續期與歸還 lease；`/cc-feather:worktrees` 列出每個 checkout 的 lease、lock 與留在其中的工作，詳見 [Checkout lease](#checkout-lease)。",
         "lease 只約束遵守規則的 session，它的 lock 依賴 Claude Code 的清理會略過已鎖定的 worktree。",
         "它沒有改任何角色定義或 handoff 與分派的政策範本，setup 工具只新增 `leases` 元件，而 `both` 從不包含它，所以既有安裝只要更新 plugin 再開新 session；不需要做 `/cc-feather:setup update`。",
         "要使用 lease，請安裝 `leases` 元件；project 範圍的區塊只透過 linked worktree 自己的 CLAUDE.md 才能到達在那裡啟動的 session，所以要讓每個 session 都遵守規則，請在使用者範圍安裝，或 commit 並 push project 的 CLAUDE.md 區塊，handoff 與分派元件也是如此。",
         "要回到 0.32.0，先在每個裝有 `leases` 元件的範圍執行 `/cc-feather:setup remove` 移除它，因為 0.32.0 的 setup 工具會以 `state component schema mismatch` 拒絕這樣的範圍且不做任何變更，再重新安裝 0.32.0 的 plugin。",
         "重新安裝之前請歸還仍持有的 lease，因為 0.32.0 沒有 lease 工具，被遺留的 lease 會保留它的 Git worktree lock，直到 `git worktree unlock` 移除它。"),
    )
    NO_SETUP_UPDATE = RetainedPassesReleaseTests.NO_SETUP_UPDATE

    # Both READMEs: the section between Handoff compatibility and Updates, its statements in order.
    README_SECTIONS = (
        ("README.md", "\n## Checkout leases\n", "\n## Handoff compatibility\n", "\n## Updates and validation\n", (
            "A Checkout lease is a cooperative record that one session is using one checkout of a Git repository, the main worktree or a linked worktree, to change it.",
            "It states a claim of use and when it began, never proof that its holder is still running, and taking one never authorises changing, resetting or removing what the checkout already holds.",
            "With the `leases` setup component installed, main takes a lease before it changes a checkout,",
            "No lease is taken over automatically, and no age makes a lease left behind.",
            "parking never deletes a branch or a worktree.",
            "it reports facts and never calls a checkout free.",
            "The `leases` component is installed only when you select it by name, and `both` never includes it.",
            "A project-scope rule block lives in that checkout's CLAUDE.md, and a session started in a linked worktree loads only that worktree's own CLAUDE.md, so it sees the lease rules only when the block is tracked, committed and, for worktrees Claude Code bases on the remote's default branch, pushed.",
            "To make every session follow them, install `leases` in user scope, or commit and push the project CLAUDE.md block.",
            "The same holds for the handoff and delegation components' project-scope blocks.",
            "Leases live in `.feather/leases/` under the main worktree, one `<key>.json` per checkout, keyed by Git's per-worktree administration identity, with `.main` for the main worktree;",
            "with the reason `cc-feather lease <lease_id>`, so `git worktree prune`, a plain `git worktree remove` and Claude Code's cleanup leave the worktree alone,",
            "This relies on Claude Code's cleanup skipping locked worktrees and never releasing a lock it did not set.",
            "An interactive Claude Code session releases its own session lock on exit, while a headless `-p` run leaves it, so a lease still held when an interactive session exits is unlocked until the next listing or acquire locks it again with the lease's own lock.",
            "[setup documentation](docs/setup.md#checkout-leases)",
            "A lease is cooperative: it binds only sessions that follow the rules.",
            "It does not stop, detect or manage another session's processes, and it does not keep a person or a tool that ignores leases, a codex-feather session included, out of a checkout.",
            "One checkout shared between Windows and WSL, or between machines, is not covered.")),
        ("README.zh-TW.md", "\n## Checkout lease\n", "\n## 交接相容性\n", "\n## 更新、移除與驗證\n", (
            "Checkout lease 是一份合作式紀錄，表示某個 session 正在使用 Git 儲存庫的某一個 checkout（main worktree 或 linked worktree）來修改它。",
            "它只聲明使用與開始時間，從不證明持有者仍在執行；取得 lease 也從不授權變更、重設或移除該 checkout 原有的內容。",
            "安裝 `leases` setup 元件後，主 Agent 在變更 checkout 之前取得 lease，",
            "lease 從不自動接手，也沒有任何經過時間會讓 lease 算作被遺留。",
            "停放從不刪除 branch 或 worktree。",
            "它只回報事實，從不說某個 checkout 是空閒的。",
            "`leases` 元件只有你指名選擇時才安裝，`both` 從不包含它。",
            "project 範圍的規則區塊位於該 checkout 的 CLAUDE.md，而在 linked worktree 中啟動的 session 只載入該 worktree 自己的 CLAUDE.md，所以只有區塊已被追蹤、已 commit，並且（對 Claude Code 以遠端預設 branch 為基礎建立的 worktree）已 push 時，那個 session 才看得到 lease 規則。",
            "要讓每個 session 都遵守，請在使用者範圍安裝 `leases`，或 commit 並 push project 的 CLAUDE.md 區塊。",
            "handoff 與 agent 分派元件的 project 範圍區塊也是如此。",
            "lease 存在 main worktree 下的 `.feather/leases/`，每個 checkout 一個 `<key>.json`，以 Git 對每個 worktree 的管理識別為 key，main worktree 用 `.main`；",
            "原因為 `cc-feather lease <lease_id>` 的 Git worktree lock 保護，所以 `git worktree prune`、一般的 `git worktree remove` 與 Claude Code 的清理都不會動到那個 worktree，",
            "這依賴 Claude Code 的清理會略過已鎖定的 worktree，而且從不解除不是它設定的 lock。",
            "互動式 Claude Code session 結束時會解除自己的 session lock，而 headless 的 `-p` 執行會留下它，所以互動式 session 結束時仍持有的 lease 會沒有 lock，直到下一次列出或取得時以 lease 自己的 lock 重新鎖定。",
            "[setup 文件](docs/setup.md#checkout-leases)",
            "lease 是合作式的：它只約束遵守規則的 session。",
            "它不會停止、偵測或管理其他 session 的 process，也不會把忽略 lease 的人或工具（包括 codex-feather 的 session）擋在 checkout 之外。",
            "Windows 與 WSL 之間、或不同機器之間共用同一個 checkout 不在涵蓋範圍內。")),
    )
    # Both READMEs list the two new skills and the `leases` component, and `both` no longer reads as every component.
    README_LISTINGS = {
        "README.md": (
            "- `/cc-feather:leases`: take, renew, take over, return and list Checkout leases; main loads it when it keeps leases. See [Checkout leases](#checkout-leases).\n",
            "- `/cc-feather:worktrees`: list every checkout of this repository with its Checkout lease, Git worktree lock and the work left in it; only you can run it.",
            "| leases | The Checkout lease rules in the instruction file; not installed unless you select it by name | Removes the rules only; lease records and Git worktree locks remain |\n",
            "| both | Handoff and delegation; never leases |"),
        "README.zh-TW.md": (
            "| `/cc-feather:leases` | 取得、續期、接手、歸還與列出 Checkout lease；主 Agent 維護 lease 時載入。見 [Checkout lease](#checkout-lease) |\n",
            "| `/cc-feather:worktrees` | 列出這個儲存庫的每個 checkout，以及它的 Checkout lease、Git worktree lock 與留在其中的工作；只能由你執行。",
            "| leases | 指示檔中的 Checkout lease 規則；只有你指名選擇時才安裝 | 只移除規則；lease 紀錄與 Git worktree lock 仍保留 |\n",
            "| 兩者（both） | handoff 與 agent 分派；不含 leases |"),
    }

    # The setup documentation's section: the setup determination, going back, the reach of the rules, the format and
    # location for other tools, the cooperative limits and the reliance on Claude Code's cleanup, in order.
    SETUP_HEADING = "\n## Checkout leases\n"
    SETUP = (
        "Updating from 0.32.0 needs no setup update:",
        "so an existing installation checks with no warning and shows `leases` as not installed.",
        "To go back to 0.32.0, run `remove --component leases` in every scope where it is installed before reinstalling the 0.32.0 plugin: the 0.32.0 setup tool refuses a scope whose state records `leases` with `state component schema mismatch`, exit 2, and changes nothing, for check and update alike.",
        "Reach of the rules: a project-scope block lives in that checkout's instruction file, and a session started in a linked worktree loads only that worktree's own CLAUDE.md.",
        "It therefore sees the lease rules only when the block is tracked, committed and, for worktrees Claude Code bases on the remote's default branch, pushed.",
        "To make every session follow them, install `leases` in user scope, or commit and push the project CLAUDE.md block.",
        "The same holds for the handoff and delegation components' project-scope blocks.",
        "Format and location for other tools: leases live in `.feather/leases/` under the main worktree, whatever a checkout's handoff tracking choice or explicit root,",
        "A lease is a UTF-8 JSON object with `schema_version` (1), `checkout` (`key`, and `path` for display only), `lease_id` (different on every acquisition), `session`, `host`, `runtime`, `started` and `last_activity` (zoned times), `purpose`, `diagnostic_pid` (the short-lived tool process's, never a sign that the holder is alive) and, when a Claude Code session lock was accepted, `accepted_lock`.",
        "`<key>.lock` beside the lease, created exclusively and never waited on or broken.",
        "The directory ignores itself with its own `.gitignore` holding `*`.",
        "A held lease on a linked worktree is mirrored by a Git worktree lock with the reason `cc-feather lease <lease_id>`,",
        "The tool never removes or changes a lock whose reason does not name one of its leases.",
        "codex-feather does not follow the protocol; the format only stays usable by it.",
        "Cooperative limits: a lease binds only sessions that follow the rules.",
        "A Git worktree lock only keeps `git worktree prune`, a plain `git worktree remove` and Claude Code's cleanup away from a leased worktree.",
        "One checkout shared between Windows and WSL, or between machines, is not covered.",
        "Reliance on Claude Code: the lock protects a leased worktree from Claude Code's periodic cleanup only because that cleanup skips locked worktrees and never releases a lock it did not set, as Claude Code's documentation stated on 2026-11-09.",
        "A headless `-p` run leaves its session lock after it ends, while an interactive session releases it on exit, so a lease still held when an interactive session exits is unlocked until the next `list` or `acquire` locks it again with the lease's own lock.",
        "[setup validation](setup-validation.md#0330-checkout-leases)",
    )

    COMPATIBILITY_HEADING = "\n## Checkout leases (0.33.0)\n"
    COMPATIBILITY = (
        "No file of the handoff runtime changes and the upstream manifest is unchanged;",
        "its listing reads handoff records only through the handoff tool's own read-only `list`,",
        "Leases are a new format, not part of codex-feather's contract:",
        "codex-feather does not follow the lease protocol, and making it do so is out of scope; the format only stays usable by it.",
        "A Codex session therefore neither takes nor respects a lease,",
        "that protection relies on Claude Code's cleanup skipping locked worktrees and never releasing a lock it did not set.",
    )

    @staticmethod
    def text(name):
        return (config.ROOT / name).read_text(encoding="utf-8")

    @staticmethod
    def section(text, heading):
        return text.split(heading, 1)[1].split("\n## ", 1)[0]

    def note(self, name, heading, sentences):
        section = self.section(self.text(name), heading)
        return section[section.index(sentences[0]):section.index(sentences[-1]) + len(sentences[-1])]

    def assert_in_order(self, section, sentences, place):
        for sentence in sentences:
            with self.subTest(place=place, sentence=sentence[:40]):
                self.assertEqual(section.count(sentence), 1)
        for earlier, later in zip(sentences, sentences[1:]):
            with self.subTest(place=place, order=earlier[:40]):
                self.assertLess(section.index(earlier), section.index(later))

    # The manifest version is pinned by the current release's tests (0.34.0, related-test acceptance).

    def test_updates_sections_start_with_the_checkout_leases_note_in_both_languages(self):
        previous = ResourceRiskRunsReleaseTests.UPDATES
        newer = RelatedTestAcceptanceReleaseTests.UPDATES
        for name, (heading, opening, *sentences), (_, _, previous_first, *_), (_, _, *newer_sentences) \
                in zip(("README.md", "README.zh-TW.md"), self.UPDATES, previous, newer):
            section = self.section(self.text(name), heading)
            for sentence in sentences:
                with self.subTest(readme=name, sentence=sentence[:30]):
                    self.assertEqual(section.count(sentence), 1)
            # The 0.33.0 note starts right after the 0.34.0 note, its sentences in order, before 0.32.0's.
            with self.subTest(readme=name, order=True):
                after_newer = section[section.index(newer_sentences[-1]) + len(newer_sentences[-1]):]
                self.assertTrue(after_newer.lstrip(" ").startswith(sentences[0]))
                for earlier, later in zip(sentences, sentences[1:] + [previous_first]):
                    self.assertLess(section.index(earlier), section.index(later))

    def test_updates_sections_need_no_setup_update_and_remove_leases_to_go_back(self):
        for name, (heading, _, *sentences), no_update in zip(("README.md", "README.zh-TW.md"), self.UPDATES, self.NO_SETUP_UPDATE):
            note = self.note(name, heading, sentences)
            with self.subTest(readme=name):
                # No setup update after the plugin update; going back needs the leases component removed first.
                self.assertEqual(note.count(no_update), 1)
                self.assertEqual(note.count("`/cc-feather:setup update`"), 1)
                self.assertEqual(note.count("`/cc-feather:setup remove`"), 1)
                self.assertIn("`state component schema mismatch`", note)
                self.assertLess(note.index("`/cc-feather:setup remove`"), note.index("0.32.0 的 plugin" if name.endswith("zh-TW.md") else "reinstall the 0.32.0 plugin"))

    def test_readmes_describe_checkout_leases_in_both_languages(self):
        for name, heading, before, after, sentences in self.README_SECTIONS:
            text = self.text(name)
            with self.subTest(readme=name):
                self.assertEqual(text.count(heading), 1)
                # The section sits after Handoff compatibility and right before Updates.
                self.assertLess(text.index(before), text.index(heading))
                self.assertLess(text.index(heading), text.index(after))
                self.assertNotIn("\n## ", text[text.index(heading) + len(heading):text.index(after)])
            self.assert_in_order(self.section(text, heading), sentences, name)
            self.assertIn("[leases skill](skills/leases/SKILL.md)", self.section(text, heading))
        for name, listings in self.README_LISTINGS.items():
            text = self.text(name)
            for listing in listings:
                with self.subTest(readme=name, listing=listing[:40]):
                    self.assertEqual(text.count(listing), 1)
        # Both README links reach the setup documentation's section and the validation entry it links.
        self.assertEqual(self.text("docs/setup.md").count(self.SETUP_HEADING), 1)

    def test_setup_document_describes_leases_for_users_and_other_tools(self):
        text = self.text("docs/setup.md")
        self.assertEqual(text.count(self.SETUP_HEADING), 1)
        section = self.section(text, self.SETUP_HEADING)
        self.assert_in_order(section, self.SETUP, "docs/setup.md")
        self.assertIn("[leases skill](../skills/leases/SKILL.md)", section)
        self.assertNotIn("Setup update is required", section)

    def test_compatibility_notes_describe_leases(self):
        text = self.text("docs/compatibility.md")
        self.assertEqual(text.count(self.COMPATIBILITY_HEADING), 1)
        section = self.section(text, self.COMPATIBILITY_HEADING)
        self.assert_in_order(section, self.COMPATIBILITY, "docs/compatibility.md")
        self.assertIn("[setup documentation](setup.md#checkout-leases)", section)
        # The section is the file's last, added rather than rewriting an earlier one.
        self.assertTrue(text.rstrip("\n").endswith(section.rstrip("\n")))

    # The validation entry: the spec and its tickets with their commits, the setup determination with its evidence and
    # the downgrade check, the test runs, the rehearsal with its Execution method and scenarios, the interactive session
    # and its finding, the user scope left unchanged, what the tests cannot show, the tag and the review round.
    ENTRY_HEADING = "\n## 0.33.0 checkout leases\n"
    ENTRY = (
        "Implements [the Checkout leases spec](specs/checkout-leases.md), added in ce50929 and revised in 0034bb0, 2bf0f96, 39084ce and 529c71e after plan review calls 1 to 4,",
        "ticket 01, acquire, release and list, in eb5e054 and 7221f88;",
        "ticket 02, the Git worktree lock that protects a held lease, in 2a6cc9f;",
        "ticket 03, renew and take over, in c762732;",
        "in 8ee6a53 and 717e91a;",
        "ticket 05, parking a merged worktree, in 9642d79;",
        "in d26bd22;",
        "[ADR 0020](adr/0020-checkout-leases-are-cooperative-records-mirrored-by-git-worktree-locks.md)",
        "**No setup update is required.**",
        "`git diff-tree -r --name-only v0.32.0 HEAD -- templates skills/setup scripts` lists `scripts/feather_config.py`, `skills/setup/SKILL.md` and the new `templates/leases.md`:",
        "so existing installations need only the plugin update and a fresh session.",
        "this release's `check` reported both installed, no warning, `role_update_required: false` and `leases` not installed, and its `update --component both` preview listed no change.",
        "v0.32.0's `check` and `update --component delegation` each refused with `state component schema mismatch`, exit 2, and every file of the project stayed byte-identical;",
        "To go back to 0.32.0, run `/cc-feather:setup remove` for the `leases` component in every scope where it is installed and return any lease still held, then reinstall the 0.32.0 plugin.",
        "`python -B -m unittest discover -s tests -t .` and `python -B -m unittest discover -s tests`, with `FEATHER_LINK_TEST_DIR` under `J:\\gotmp\\`",
        "each ran 1268 tests at the commit carrying this entry, all passing with 29 skips and the same count in both forms",
        "(the 0.32.0 release ran 1117 tests with 29 skips).",
        "`.claude-plugin/marketplace.json` carries no version,",
        "Live rehearsal (2026-11-10, ticket 07). The candidate commit d26bd22 was exported with `git archive` and loaded only through `--plugin-dir`",
        "The candidate's setup installed only the `leases` component in the clone's project scope;",
        "This ticket is a Resource-risk claim.",
        "inside the cc-feather Runner with `--memory-mib 1536 --time-seconds 1200`, at most two sessions at once and 2 hours of rehearsal in total, the budget from the user's own statement on 2026-11-10 choosing plan review's suggestion.",
        "No run was contained, refused or stopped by a limit, so there is no Observed resource risk.",
        "One session, s2-C, was killed on purpose by the scenario, 40 s after its lease appeared, which is not a limit stop.",
        "- Two sessions on one worktree:",
        "- A killed session and a takeover:",
        "- A merged parallel worktree:",
        "a liveness reading the rules disclaim",
        "Interactive session (2026-11-10, run by the user, Claude Code 2.1.321):",
        "locked it at creation with `claude session lease-probe (pid N)`, the format the 2026-11-09 headless probes saw.",
        "After exit the worktree had no lock at all: an interactive session releases its own session lock on exit, while the headless runs left theirs.",
        "This difference breaks no spec rule:",
        "`EnterWorktree` by name was not run interactively,",
        "Finding, documented in the setup documentation and both READMEs: a project-scope rule block lives in that checkout's CLAUDE.md, and a session started in a linked worktree loads only that worktree's own CLAUDE.md,",
        "The same holds for the handoff and delegation components' project-scope blocks.",
        "76 files, were byte-identical before and after the rehearsal, and the installed cc-feather stayed 0.32.0.",
        "Claude Code had auto-updated from 2.1.319, which the 2026-11-09 probes used, to 2.1.321.",
        "neither they nor one rehearsal can show that a model always follows the rules.",
        "Claude Code's periodic cleanup was not observed skipping a locked worktree;",
        "`v0.33.0` does not exist when this entry is written.",
        "it is created only after the user's go-ahead.",
        "No claim is Security-critical,",
        "and READY on call 5 at 529c71e.",
        "with a Deviation the user authorised on 2026-11-09,",
        "the user's decision at the end of the plan and the tag follow the commit carrying this entry and are recorded after it.",
    )

    def test_validation_entry_records_the_release_rehearsal_tag_and_review_round(self):
        text = self.text("docs/setup-validation.md")
        self.assertEqual(text.count(self.ENTRY_HEADING), 1)
        entry = self.section(text, self.ENTRY_HEADING)
        for sentence in self.ENTRY:
            with self.subTest(sentence=sentence[:40]):
                self.assertEqual(entry.count(sentence), 1)
        self.assertNotIn("Setup update is required", entry)
        self.assertNotIn(".scratch", entry)
        # Each ticket has its line in the review round, in order.
        tickets = [entry.index(f"\n- {line}") for line in ("Spec and plans:", "Ticket 01:", "Ticket 02:", "Ticket 03:",
                                                            "Ticket 04:", "Ticket 05:", "Ticket 06:", "Ticket 07:")]
        self.assertEqual(tickets, sorted(tickets))
        # The entry was appended rather than rewriting an earlier one, and only the 0.34.0 entry follows it.
        after = text.split(self.ENTRY_HEADING, 1)[1][len(entry):]
        self.assertTrue(after.startswith(RelatedTestAcceptanceReleaseTests.ENTRY_HEADING))


class RelatedTestAcceptanceReleaseTests(unittest.TestCase):
    """0.34.0 (docs/specs/related-test-acceptance.md, Implementation Decisions' Release and State schema; ticket 03): the
    manifest version is 0.34.0; the Updates note, the setup documentation and the validation entry say that existing
    installations need only the plugin update and a fresh session, that a 0.33.x or older configuration tool rejects a
    scope with a saved setting so a downgrade first sets it back to `default` there, and that a session choice needs
    nothing, the README note in both languages; the validation entry records the tickets, the setup determination with
    its upgrade and downgrade check, the test runs, the reviewing version, the tag and the review round."""

    # The Updates sections, paired in both languages: the section's opening sentence, then the 0.34.0 note in order.
    UPDATES = (
        ("## Updates and validation\n",
         CheckoutLeasesReleaseTests.UPDATES[0][1],
         "0.34.0 adds Related-test acceptance, a delegation setting that, when on, has main name the test modules related to a change in a Claim's acceptance instead of the full test suite, while the Plan's overall acceptance keeps the full suite, which the final check runs, and `/cc-feather:related-tests`, which sets it, as [Related-test acceptance](#related-test-acceptance) describes.",
         "It changes no role definition and no handoff, delegation or leases policy template, so existing installations need only the plugin update and a fresh session; no `/cc-feather:setup update` is needed, and a scope's guidance and state stay byte-identical until the setting is saved in it.",
         "A 0.33.x or older configuration tool rejects a scope with a saved setting with `invalid delegation state schema` and changes nothing, so to go back to 0.33.0, first set it back to `default` there with `/cc-feather:related-tests default project` or `/cc-feather:related-tests default user` in every scope where you saved it, then reinstall the 0.33.0 plugin; a session choice needs nothing."),
        ("## 更新、移除與驗證\n",
         CheckoutLeasesReleaseTests.UPDATES[1][1],
         "0.34.0 新增相關測試驗收：一項 agent 分派設定，開啟時主 Agent 在 Claim 的驗收中列出與變更相關的測試模組，而不是完整測試，計畫的整體驗收仍是完整測試，由最終檢查執行；另新增設定它的 `/cc-feather:related-tests`，詳見[相關測試驗收](#相關測試驗收)。",
         "它沒有改任何角色定義或 handoff、分派與 leases 的政策範本，所以既有安裝只要更新 plugin 再開新 session；不需要做 `/cc-feather:setup update`，而且某個範圍在儲存這項設定之前，指引與狀態都保持逐位元組相同。",
         "0.33.x 或更舊的設定工具會以 `invalid delegation state schema` 拒絕已儲存這項設定的範圍且不做任何變更，所以要回到 0.33.0，先在每個儲存過它的範圍以 `/cc-feather:related-tests default project` 或 `/cc-feather:related-tests default user` 把它設回 `default`，再重新安裝 0.33.0 的 plugin；session 的選擇不需要任何處理。"),
    )
    NO_SETUP_UPDATE = RetainedPassesReleaseTests.NO_SETUP_UPDATE

    # The setup documentation's Related-test acceptance section: the update, the downgrade and the session choice, in order.
    SETUP_HEADING = "\n## Related-test acceptance\n"
    SETUP = (
        "Updating from 0.33.0 needs no setup update: 0.34.0 changes no role definition template and no handoff, delegation or leases policy template, so existing installations need only the plugin update and a fresh session, and a scope's guidance and state stay byte-identical until the setting is saved in it.",
        "A 0.33.x or older configuration tool rejects a scope with a saved setting, so a downgrade first sets it back to `default` there.",
        "That is `review --related-tests default` in every scope that saved the setting, run before the older plugin is reinstalled; a scope without a saved setting needs nothing, and a session choice, which writes nothing, needs nothing either.",
    )

    # The validation entry: the spec and its tickets with their commits, the setup determination with its evidence and
    # the upgrade and downgrade check, the test runs, the reviewing version, the tag and the review round.
    ENTRY_HEADING = "\n## 0.34.0 related-test acceptance\n"
    ENTRY = (
        "Implements [the Related-test acceptance spec](specs/related-test-acceptance.md), added in 4820a9c and revised in e7c902e, 93b709c and 2ca8376 after plan review calls 1 to 3,",
        "ticket 01, the saved setting, in 30943ed;",
        "ticket 02, the `/cc-feather:related-tests` command and its shared procedure, in b11ce43;",
        "ticket 03, this release, in the commit carrying this entry.",
        "**No setup update is required.**",
        "`git diff-tree -r --name-only v0.33.0 HEAD -- templates skills/setup scripts` lists `scripts/feather_config.py`, `skills/setup/SKILL.md`, the new `skills/setup/references/related-tests.md` and the new `templates/related-tests.md`:",
        "no role definition template, `templates/CLAUDE.md`, `templates/handoff.md`, `templates/review-auto.md` or `templates/leases.md` changed, so existing installations need only the plugin update and a fresh session.",
        "with v0.33.0's setup tool exported by `git archive v0.33.0`",
        "the 22 guidance, state and role files of both scopes stayed byte-identical;",
        "v0.33.0's `check`, `show` and `update --component delegation` each refused with `invalid delegation state schema`, exit 2,",
        "and v0.33.0's `check` read both scopes again with status `ok` and no warning.",
        "A 0.33.x or older configuration tool therefore rejects a scope with a saved setting, so a downgrade first sets it back to `default` there:",
        "a scope without a saved setting, and a session choice, which writes nothing, need nothing.",
        "`python -B -m unittest discover -s tests -t .` and `python -B -m unittest discover -s tests`, with `FEATHER_LINK_TEST_DIR` under `J:\\gotmp\\`",
        "(the 0.33.0 release ran 1268 tests with 29 skips).",
        "`.claude-plugin/marketplace.json` carries no version,",
        "the spec's Overall acceptance, the full `unittest discover` suite, is run by the final check,",
        "with the installed cc-feather 0.33.0's roles and procedures, not this release's candidate.",
        "`v0.34.0` does not exist when this entry is written.",
        "it is created only after tickets 01 to 03 are accepted and only after the user's go-ahead.",
        "No claim is Security-critical,",
        "and READY on call 4 at 2ca8376.",
        "the user's decision at the end of the plan and the tag follow the commit carrying this entry and are recorded after it.",
    )

    @staticmethod
    def text(name):
        return (config.ROOT / name).read_text(encoding="utf-8")

    @staticmethod
    def section(text, heading):
        return text.split(heading, 1)[1].split("\n## ", 1)[0]

    def note(self, name, heading, sentences):
        section = self.section(self.text(name), heading)
        return section[section.index(sentences[0]):section.index(sentences[-1]) + len(sentences[-1])]

    def assert_in_order(self, section, sentences, place):
        for sentence in sentences:
            with self.subTest(place=place, sentence=sentence[:40]):
                self.assertEqual(section.count(sentence), 1)
        for earlier, later in zip(sentences, sentences[1:]):
            with self.subTest(place=place, order=earlier[:40]):
                self.assertLess(section.index(earlier), section.index(later))

    # The manifest version is pinned by the current release's tests (0.35.0, resource-risk confirmation).

    def test_updates_sections_start_with_the_related_test_acceptance_note_in_both_languages(self):
        previous = CheckoutLeasesReleaseTests.UPDATES
        newer = ResourceRiskConfirmationReleaseTests.UPDATES
        for name, (heading, opening, *sentences), (_, _, previous_first, *_), (_, _, *newer_sentences) \
                in zip(("README.md", "README.zh-TW.md"), self.UPDATES, previous, newer):
            section = self.section(self.text(name), heading)
            # The 0.34.0 note starts right after the 0.35.0 note, its sentences in order, before 0.33.0's.
            with self.subTest(readme=name, order=True):
                after_newer = section[section.index(newer_sentences[-1]) + len(newer_sentences[-1]):]
                self.assertTrue(after_newer.lstrip(" ").startswith(sentences[0]))
            self.assert_in_order(section, sentences + [previous_first], name)

    def test_updates_sections_need_no_setup_update_and_set_the_setting_back_to_go_back(self):
        for name, (heading, _, *sentences), no_update in zip(("README.md", "README.zh-TW.md"), self.UPDATES, self.NO_SETUP_UPDATE):
            note = self.note(name, heading, sentences)
            with self.subTest(readme=name):
                # No setup update after the plugin update; going back needs the setting set back to `default` first.
                self.assertEqual(note.count(no_update.rstrip("。.")), 1)
                self.assertEqual(note.count("`/cc-feather:setup update`"), 1)
                self.assertNotIn("`/cc-feather:setup remove`", note)
                self.assertLess(note.index("`/cc-feather:related-tests default project`"),
                                note.index("0.33.0 的 plugin" if name.endswith("zh-TW.md") else "reinstall the 0.33.0 plugin"))

    def test_setup_document_states_the_update_and_the_downgrade(self):
        text = self.text("docs/setup.md")
        self.assertEqual(text.count(self.SETUP_HEADING), 1)
        self.assert_in_order(self.section(text, self.SETUP_HEADING), self.SETUP, "docs/setup.md")

    def test_validation_entry_records_the_release_check_tag_and_review_round(self):
        text = self.text("docs/setup-validation.md")
        self.assertEqual(text.count(self.ENTRY_HEADING), 1)
        entry = self.section(text, self.ENTRY_HEADING)
        for sentence in self.ENTRY:
            with self.subTest(sentence=sentence[:40]):
                self.assertEqual(entry.count(sentence), 1)
        self.assertNotIn("Setup update is required", entry)
        self.assertNotIn(".scratch", entry)
        # Each ticket has its line in the review round, in order.
        tickets = [entry.index(f"\n- {line}") for line in ("Spec and plans:", "Ticket 01:", "Ticket 02:", "Ticket 03:")]
        self.assertEqual(tickets, sorted(tickets))
        # The entry was appended rather than rewriting an earlier one, and only the 0.35.0 entry follows it.
        after = text.split(self.ENTRY_HEADING, 1)[1][len(entry):]
        self.assertTrue(after.startswith(ResourceRiskConfirmationReleaseTests.ENTRY_HEADING))


class ResourceRiskConfirmationReleaseTests(unittest.TestCase):
    """0.35.0 (docs/specs/resource-risk-confirmation.md, Implementation Decisions' Documents and Release, Further Notes'
    Limits and Fewer stops with a default budget, Out of Scope; ticket 02): the manifest version is 0.35.0; both
    reference documents describe the confirmation in their resource-limits section, paired in both languages; the
    Updates note and the setup documentation say that the analyst role definition changed, so existing installations
    need setup update, and how to go back to 0.34.0, the README note in both languages; the validation entry records the
    tickets, the `git diff-tree` determination with its upgrade and downgrade check, the test runs, the reviewing
    version, what the tests cannot show, the tag and the review round, and is the file's last."""

    # The Updates sections, paired in both languages: the section's opening sentence, then the 0.35.0 note in order.
    UPDATES = (
        ("## Updates and validation\n",
         CheckoutLeasesReleaseTests.UPDATES[0][1],
         "0.35.0 makes plan review's resource-risk mark a proposal that you adopt or drop: after a plan's plan review returns READY and before its first claim is implemented, main asks you once which proposed marks to adopt, showing each one's reason and estimate with its own recommendation, and asks any budget question an adopted claim needs in the same question, so a chain of claims does not stop later for a mark or a budget, as the [reference](docs/reference.md#resource-limits) describes.",
         "Only a claim you adopt is a Resource-risk claim; a claim you drop is an ordinary claim, still covered by the Unbounded probe floor, and a plan with no proposed mark gets no new question.",
         "It changes the analyst role definition, so existing installations need the plugin update, then `/cc-feather:setup update` in every scope where delegation is installed, then a fresh session; until then `check` warns that analyst is from an older template.",
         "To go back to 0.34.0, reinstall the 0.34.0 plugin and run `/cc-feather:setup update` in every scope where delegation is installed, then start a fresh session, so that it restores the 0.34.0 analyst role definition; no remove is needed."),
        ("## 更新、移除與驗證\n",
         CheckoutLeasesReleaseTests.UPDATES[1][1],
         "0.35.0 讓計畫審查的資源風險標示成為由你採用或捨棄的提議：計畫的計畫審查回傳 READY 之後、它的第一個 claim 實作之前，主 Agent 只問你一次要採用哪些提議的標示，列出每項的理由與估計並附上自己的建議，採用的 claim 需要的預算問題也併入同一個問題，所以一連串的 claim 之後不會再為了標示或預算停下，詳見[參考文件](docs/reference.zh-TW.md#資源限制)。",
         "只有你採用的 claim 才是 Resource-risk claim；你捨棄的 claim 是一般的 claim，仍受 Unbounded probe 底線涵蓋，沒有任何提議標示的計畫不會多出新的問題。",
         "它改了 analyst 的角色定義，所以既有安裝要先更新 plugin，再於每個裝有分派元件的範圍執行 `/cc-feather:setup update`，然後開新 session；在那之前，check 會提醒 analyst 來自較舊的範本。",
         "要回到 0.34.0，重新安裝 0.34.0 的 plugin，並在每個裝有分派元件的範圍執行 `/cc-feather:setup update`，再開新 session，讓它還原 0.34.0 的 analyst 角色定義；不需要先移除。"),
    )
    NO_SETUP_UPDATE = RetainedPassesReleaseTests.NO_SETUP_UPDATE
    # The role definitions this release changes (`git diff-tree -r --name-only v0.34.0 HEAD -- templates`), and those it
    # does not.
    CHANGED_ROLES = ("analyst",)
    UNCHANGED_ROLES = ("scout", "mech-executor", "executor", "security-executor", "verifier", "reviewer", "adversary",
                       "Explore")

    # Both reference documents' resource-limits section: the proposal, the one ask, the dropped claim, where it applies,
    # the approval and budget question at the same ask, the floor and the end-of-plan list, paired and in order.
    REFERENCE = (
        ("docs/reference.md", "\n### Resource limits\n", (
            "plan review proposes it as a Resource-risk claim, estimates its peak with the basis and proposes an Execution method for the risky part.",
            "The mark is a proposal that you adopt or drop: after the plan's plan review returns READY and before its first claim is implemented, main asks you once about the plan's proposals, in one question that shows each one's reason and estimate with main's recommendation, and only a claim you adopt is a Resource-risk claim.",
            "A claim you drop is an ordinary claim, still covered by the floor below, and plan review proposes it again only with evidence your decision did not consider.",
            "This holds in `auto` and after a plan review you request in `off`; a plan with no proposed mark gets no question.",
            "For the claims you adopt, main approves their Execution methods at that same question, and a budget question it needs joins that question, so a chain of claims does not stop later for an approval or a budget; a default budget in your guidance that covers the claim leaves the budget question out.",
            "This holds for unmarked and dropped claims, in `off` and for main's own reruns too.",
            "carries it into later briefs of that claim and lists it at the end of the plan, next to each proposal you dropped with your reason.")),
        ("docs/reference.zh-TW.md", "\n### 資源限制\n", (
            "計畫審查提議把它標為 Resource-risk claim，估計峰值並附上依據，並為有風險的部分提出 Execution method。",
            "這個標示是由你採用或捨棄的提議：計畫的計畫審查回傳 READY 之後、它的第一個 claim 實作之前，主 Agent 就計畫的提議只問你一次，在一個問題中列出每項提議的理由與估計，並附上主 Agent 的建議；只有你採用的 claim 才是 Resource-risk claim。",
            "你捨棄的 claim 是一般的 claim，仍受下面的底線涵蓋，計畫審查只有在有你的決定沒有考慮到的證據時，才會再次提議它。",
            "這在 `auto` 下適用，在 `off` 下你要求的計畫審查之後也適用；沒有任何提議標示的計畫不會多出問題。",
            "對你採用的 claim，主 Agent 在同一個問題中核准它們的 Execution method，需要的預算問題也併入那個問題，所以一連串的 claim 之後不會再為了核准或預算停下；你的指引中涵蓋該 claim 的預設預算會讓那個問題省去預算問題。",
            "沒有被標示或被捨棄的 claim、`off` 模式與主 Agent 自己的重跑也一樣適用。",
            "帶進該 claim 之後的 brief，並在計畫結束時列出，旁邊附上你捨棄的每項提議與你的理由。")),
    )
    # The sentences these replace, which said that plan review's mark binds by itself.
    REPLACED_REFERENCE = (
        ("docs/reference.md", "plan review marks it a Resource-risk claim,"),
        ("docs/reference.zh-TW.md", "計畫審查把它標為 Resource-risk claim，"),
    )

    # The setup documentation's added-roles section: the upgrade, then the way back, after 0.21.0's.
    SETUP_HEADING = "\n## Added roles and incompatible role sets\n"
    SETUP = (
        RepositorySafetyReleaseTests.SETUP[-1],
        "Upgrading to 0.35.0 needs setup update in every scope where delegation is installed, then a fresh session: it changes the analyst role template, and until the update `check` and `show` report analyst from an older template, and `model`, `review` and session export refuse.",
        "To go back to 0.34.0 from 0.35.0, no remove is needed: 0.34.0 reads the state 0.35.0 writes, and its own setup update re-renders its role templates, so run setup update with 0.34.0 in every scope where delegation is installed, then start a fresh session.",
    )

    # The validation entry: the spec and its tickets with their commits, the setup determination with its evidence and
    # the upgrade and downgrade check, the test runs, the reviewing version, what the tests cannot show, the tag and the
    # review round.
    ENTRY_HEADING = "\n## 0.35.0 resource-risk confirmation\n"
    ENTRY = (
        "Implements [the Resource-risk confirmation spec](specs/resource-risk-confirmation.md), written on 2026-11-11 and added in a8788ba after plan review call 1, with the changes the user authorised;",
        "[ADR 0019](adr/0019-resource-risk-is-marked-at-plan-review-and-contained-by-the-runner.md)",
        "ticket 01, the rule, the glossary entry and ADR 0019's amendment note, in cfa35fe;",
        "ticket 02, the documents and this release, in the commit carrying this entry.",
        "**Setup update is required.**",
        "`git diff-tree -r --name-only v0.34.0 HEAD -- templates skills/setup scripts` lists only `templates/agents/analyst.md`:",
        "Existing installations need the plugin update, then `/cc-feather:setup update` in every scope where delegation is installed, then a fresh session;",
        "To go back to 0.34.0, reinstall the 0.34.0 plugin and run `/cc-feather:setup update` the same way, then start a fresh session; no remove is needed.",
        "with v0.34.0's setup tool exported by `git archive v0.34.0`",
        "Its `update --component both` changed only `analyst.md` and `state.json` in each scope,",
        "and the 22 guidance, state and role files of both scopes were byte-identical to the v0.34.0 installation.",
        "`python -B -m unittest discover -s tests -t .` and `python -B -m unittest discover -s tests`, with `FEATHER_LINK_TEST_DIR` under `J:\\gotmp\\`",
        "each ran 1329 tests on this release's working tree before its commit, all passing with 29 skips",
        "(the 0.34.0 release ran 1298 tests with 29 skips).",
        "`.claude-plugin/marketplace.json` carries no version,",
        "The spec's Overall acceptance, the full `unittest discover` suite, is run by the final check,",
        "with the installed cc-feather 0.34.0's roles and procedures, not this release's candidate.",
        "No live session ran with the 0.35.0 rule:",
        "the tests show the text, not that a model always follows it.",
        "A dropped Claim runs without the Runner requirement, so a risk that plan review saw correctly and the user dropped is caught only by the floor, which covers new or modified tests and probes, not unchanged checks the Plan lists.",
        "a setup command or saved setting for a default budget remains possible follow-up work.",
        "`v0.35.0` does not exist when this entry is written.",
        "it is created only after tickets 01 and 02 are accepted and only after the user's go-ahead.",
        "No claim is Security-critical,",
        "No claim is a Resource-risk claim: plan review proposed none.",
        "and READY on call 2 at a8788ba.",
        "the user's decision at the end of the plan and the tag follow the commit carrying this entry and are recorded after it.",
    )

    @staticmethod
    def text(name):
        return (config.ROOT / name).read_text(encoding="utf-8")

    @staticmethod
    def section(text, heading):
        return text.split(heading, 1)[1].split("\n## ", 1)[0]

    def note(self, name, heading, sentences):
        section = self.section(self.text(name), heading)
        return section[section.index(sentences[0]):section.index(sentences[-1]) + len(sentences[-1])]

    def assert_in_order(self, section, sentences, place):
        for sentence in sentences:
            with self.subTest(place=place, sentence=sentence[:40]):
                self.assertEqual(section.count(sentence), 1)
        for earlier, later in zip(sentences, sentences[1:]):
            with self.subTest(place=place, order=earlier[:40]):
                self.assertLess(section.index(earlier), section.index(later))

    def test_manifest_is_0_35_0(self):
        self.assertEqual("0.35.0", json.loads(self.text(".claude-plugin/plugin.json"))["version"])

    def test_updates_sections_start_with_the_confirmation_note_in_both_languages(self):
        previous = RelatedTestAcceptanceReleaseTests.UPDATES
        for name, (heading, opening, *sentences), (_, _, previous_first, *_) in zip(("README.md", "README.zh-TW.md"), self.UPDATES, previous):
            section = self.section(self.text(name), heading)
            # The 0.35.0 note starts right after the section's opening sentence, its sentences in order, before 0.34.0's.
            with self.subTest(readme=name, order=True):
                self.assertTrue(section.lstrip("\n").startswith(opening + sentences[0]))
            self.assert_in_order(section, sentences + [previous_first], name)

    def test_updates_sections_require_setup_update_in_both_languages(self):
        for name, (heading, _, *sentences), no_update in zip(("README.md", "README.zh-TW.md"), self.UPDATES, self.NO_SETUP_UPDATE):
            note = self.note(name, heading, sentences)
            with self.subTest(readme=name):
                # The note asks for setup update after the plugin update and for going back, and never says it is not needed.
                self.assertEqual(note.count("`/cc-feather:setup update`"), 2)
                self.assertNotIn(no_update, note)
                self.assertNotIn("need only the plugin update", note)
                self.assertNotIn("只要更新 plugin", note)
                self.assertNotIn("`/cc-feather:setup remove`", note)

    def test_the_note_names_only_the_role_definition_the_release_changes(self):
        for name, (heading, _, *sentences) in zip(("README.md", "README.zh-TW.md"), self.UPDATES):
            note = self.note(name, heading, sentences)
            for role in self.CHANGED_ROLES:
                with self.subTest(readme=name, role=role):
                    self.assertIn(role, note)
            for role in self.UNCHANGED_ROLES:
                with self.subTest(readme=name, unchanged=role):
                    self.assertNotIn(role, note)

    def test_the_note_links_to_the_reference_section_and_states_no_budget(self):
        for name, (heading, _, *sentences), (link, document, target) in zip(
                ("README.md", "README.zh-TW.md"), self.UPDATES,
                (("(docs/reference.md#resource-limits)", "docs/reference.md", "\n### Resource limits\n"),
                 ("(docs/reference.zh-TW.md#資源限制)", "docs/reference.zh-TW.md", "\n### 資源限制\n"))):
            note = self.note(name, heading, sentences)
            with self.subTest(readme=name):
                self.assertIn(link, note)
                self.assertEqual(self.text(document).count(target), 1)
                self.assertIsNone(ResourceRiskRunsReleaseTests.NUMBERS.search(note))

    def test_reference_documents_describe_the_confirmation_in_both_languages(self):
        for name, heading, sentences in self.REFERENCE:
            text = self.text(name)
            self.assertEqual(text.count(heading), 1)
            section = text.split(heading, 1)[1].split("\n### ", 1)[0]
            self.assert_in_order(section, sentences, name)
            # The section still links to the reference that states the rule, and states no budget.
            with self.subTest(document=name):
                self.assertIn("(../skills/delegation/references/resource-risk-runs.md)", section)
                self.assertIsNone(ResourceRiskRunsReleaseTests.NUMBERS.search(section))
        for name, sentence in self.REPLACED_REFERENCE:
            with self.subTest(replaced=name):
                self.assertNotIn(sentence, self.text(name))

    def test_setup_document_states_the_upgrade_and_the_way_back(self):
        text = self.text("docs/setup.md")
        self.assertEqual(text.count(self.SETUP_HEADING), 1)
        self.assert_in_order(self.section(text, self.SETUP_HEADING), self.SETUP, "docs/setup.md")

    def test_validation_entry_records_the_release_check_tag_and_review_round(self):
        text = self.text("docs/setup-validation.md")
        self.assertEqual(text.count(self.ENTRY_HEADING), 1)
        entry = self.section(text, self.ENTRY_HEADING)
        for sentence in self.ENTRY:
            with self.subTest(sentence=sentence[:40]):
                self.assertEqual(entry.count(sentence), 1)
        self.assertNotIn("No setup update is required", entry)
        self.assertNotIn(".scratch", entry)
        # Each ticket has its line in the review round, in order.
        tickets = [entry.index(f"\n- {line}") for line in ("Spec and plans:", "Ticket 01:", "Ticket 02:")]
        self.assertEqual(tickets, sorted(tickets))
        # The entry is the file's last, so it is appended rather than rewriting an earlier one.
        self.assertTrue(text.rstrip("\n").endswith(entry.rstrip("\n")))


class InstallDocumentTests(unittest.TestCase):
    """C7 item 3: the documents users follow to install, update and recover are current."""

    @staticmethod
    def text(name):
        return (config.ROOT / name).read_text(encoding="utf-8")

    def test_install_and_update_commands_replace_prerelease_wording(self):
        for name, prerelease in (("README.md", "After publishing this version"),
                                 ("README.zh-TW.md", "將此版本推送至 GitHub 後")):
            with self.subTest(readme=name):
                text = self.text(name)
                self.assertNotIn(prerelease, text.replace("[GitHub](https://github.com/xenciscbc/cc-feather)", "GitHub"))
                for command in ("/plugin marketplace add xenciscbc/cc-feather", "/plugin install cc-feather@cc-feather",
                                "claude plugin update cc-feather@cc-feather"):
                    self.assertIn(command, text)
        self.assertNotIn("D:/work_data", self.text("README.zh-TW.md"))
        self.assertIn("`/plugin marketplace add /absolute/path/to/cc-feather`", self.text("README.zh-TW.md"))

    def test_setup_document_counts_the_packaged_skills(self):
        skills = json.loads(self.text(".claude-plugin/plugin.json"))["skills"]
        words = dict(enumerate(("nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
                                "seventeen", "eighteen", "nineteen", "twenty"), start=9))
        setup = self.text("docs/setup.md")
        self.assertIn(f"The plugin packages {words[len(skills)]} skills.", setup)
        # Only the manifest's count is stated: an earlier count left behind would contradict it.
        for count, word in words.items():
            if count != len(skills):
                with self.subTest(stale=word):
                    self.assertNotIn(f"The plugin packages {word} skills.", setup)

    def test_setup_documents_describe_both_causes_and_reinstall_reset(self):
        setup = self.text("docs/setup.md")
        self.assertIn("Check/show report `role_update_required: true` for two causes.", setup)
        self.assertIn("rendered from an older role template than the plugin now packages", setup)
        self.assertIn("remove and reinstall the scope, which resets the saved choices to the defaults and the review "
                      "mode to off unless install is given `--review-mode auto`.", setup)
        self.assertNotIn("the installation predates a newly packaged role;", self.text("skills/setup/SKILL.md"))
        self.assertIn("or an unedited role was rendered from an older template", self.text("skills/setup/SKILL.md"))


class UpstreamManifestTests(unittest.TestCase):
    """C7 item 2: the upstream manifest describes the handoff files that ship.

    Hashes are of the bytes as checked out; .gitattributes keeps *.py at LF in every checkout, so a CRLF
    platform hashes the same bytes.
    """

    def setUp(self):
        self.manifest = json.loads((config.ROOT / "docs" / "upstream-manifest.json").read_bytes())

    def test_listed_files_ship_with_their_recorded_hashes(self):
        files = self.manifest["files"]
        self.assertTrue(files)
        self.assertEqual(set(self.manifest["upstream_paths"]), set(files))
        for name, recorded in files.items():
            with self.subTest(file=name):
                path = config.ROOT / name
                self.assertTrue(path.is_file(), f"listed file does not ship: {name}")
                self.assertEqual(config.digest(path.read_bytes()), recorded, f"stale manifest hash: {name}")

    def test_adaptations_name_listed_files_that_differ_from_their_source(self):
        files = self.manifest["files"]
        for name, entry in self.manifest["adaptations"].items():
            with self.subTest(file=name):
                self.assertIn(name, files)
                self.assertEqual(set(entry), {"source_sha256", "change"})
                self.assertRegex(entry["source_sha256"], r"^[0-9a-f]{64}$")
                # An adaptation records changed bytes; a file identical to its source needs no entry.
                self.assertNotEqual(entry["source_sha256"], files[name])
                self.assertTrue(entry["change"].strip())


if __name__ == "__main__":
    unittest.main()
