"""Related-test acceptance ticket 01: the configuration tool saves, renders, shows, keeps and removes the setting per
scope, the rule lives once in its template, and the setup document describes the setting. Ticket 02: the
/cc-feather:related-tests command, its shared procedure under the setup skill, the pointers to it, the READMEs and
reference documents, and the packaged skill lists."""

from __future__ import annotations

import contextlib
import io
import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests import feather_support
from tests.feather_support import config

TEMPLATE = config.ROOT / "templates" / "related-tests.md"
USER_ON = "Related-test acceptance is on."
PROJECT_ON = "Related-test acceptance is on in this project; this overrides broader Feather guidance."
PROJECT_OFF = "Related-test acceptance is off in this project; this overrides broader Feather guidance."
STOP_LINE = {"user": "The Stop threshold for automatic review is {k}.",
             "project": "The Stop threshold in this project is {k}; this overrides broader Feather guidance."}
# The rule's decision-carrying sentences, as the spec's "The rule" states them.
RULE_SENTENCES = (
    "When main writes a Claim's acceptance in a spec, ticket or plan, it names the test modules related to the change instead of the full test suite: those that test or read the files the Claim changes, found by searching the tests for those files' paths and directory names.",
    "It names the full suite instead when the Claim changes shared test support or build configuration, when its related tests cannot be determined, and for a release unless the Plan's overall acceptance names the full suite.",
    "The named tests are a minimum: running more for a file the list does not cover does not change the acceptance.",
    "A Plan's overall acceptance keeps the full suite, which the final check runs.",
    "When main writes a Plan of several Claims that has no overall acceptance, it adds one that names the full suite where the Plan is written, in the spec for tickets of a spec.",
    "That overall acceptance states that it is the Plan's overall acceptance, which the final check runs for each commit to be landed or tagged, not for each Claim, and that it is not part of any Claim's acceptance; each ticket cites it.",
    "The only Claim of a Plan without overall acceptance keeps the full suite itself.",
    "Acceptance the user wrote, existing specs and tickets, and a fix Claim's acceptance keep their wording.",
)


def whole_sentence(sentence: str) -> str:
    return rf"(?:^|(?<=\s)){re.escape(sentence)}(?=\s|$)"


class RelatedTestsSettingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(os.path.realpath(self.temp.name))
        self.project = self.root / "project"
        self.home = self.root / "claude-home"
        self.project.mkdir()
        self.home.mkdir()

    # Helpers: the tool's command line, its JSON output and the files it writes.

    def call(self, command, scope="project", *extra):
        args = [command, "--project", str(self.project), "--scope", scope, "--claude-home", str(self.home), *extra]
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = config.main(args)
        return code, json.loads(output.getvalue())

    def apply(self, command, scope="project", *extra):
        code, preview = self.call(command, scope, *extra)
        self.assertEqual((code, preview["status"]), (0, "preview"), preview)
        code, result = self.call(command, scope, *extra, "--apply", "--expected-plan", preview["plan_id"])
        self.assertEqual((code, result["status"]), (0, "applied"), result)
        return result

    def files(self):
        return {str(path): path.read_bytes() for path in sorted(self.root.rglob("*")) if path.is_file()}

    def guidance(self, scope):
        return self.project / "CLAUDE.md" if scope == "project" else self.home / "CLAUDE.md"

    def state_path(self, scope):
        base = self.project / ".claude" if scope == "project" else self.home
        return base / "cc-feather" / "state.json"

    def record(self, scope):
        return json.loads(self.state_path(scope).read_bytes())["components"]["delegation"]

    def block(self, scope):
        return config._block_parts(self.guidance(scope).read_text(encoding="utf-8"))[1].replace("\r\n", "\n")

    def older_template_warnings(self, scope):
        return [w for w in self.call("check", scope)[1]["warnings"] if "older template" in w]

    @staticmethod
    def rule():
        return TEMPLATE.read_text(encoding="utf-8").replace("\r\n", "\n").strip()

    def on_paragraph(self, scope):
        return (PROJECT_ON if scope == "project" else USER_ON) + " " + self.rule()

    @staticmethod
    def release_0_33_0_block(mode, scope, stop_threshold=None):
        """The delegation block 0.33.0 renders without a role prefix, rebuilt from the templates."""
        template = (config.ROOT / "templates" / "CLAUDE.md").read_text(encoding="utf-8").replace("\r\n", "\n")
        auto = (config.ROOT / "templates" / "review-auto.md").read_text(encoding="utf-8").replace("\r\n", "\n").strip()
        if mode == "auto":
            middle = auto + "\n\n"
        else:
            middle = ("Automatic plan review is off in this project; this overrides broader Feather guidance.\n\n"
                      if scope == "project" else "")
        if stop_threshold is not None:
            middle += STOP_LINE[scope].format(k=stop_threshold) + "\n\n"
        return template.replace("{{auto_review}}", middle).replace("{{role_names}}", "").rstrip("\n")

    def expected_block(self, mode, scope, paragraph, stop_threshold=None):
        return self.release_0_33_0_block(mode, scope, stop_threshold).replace(
            config.END, paragraph + "\n\n" + config.END)

    def assert_reported(self, scope, value, saved):
        for command in ("show", "check"):
            code, shown = self.call(command, scope)
            self.assertEqual((code, shown["status"]), (0, "ok"), shown)
            self.assertEqual((shown["related_tests"], shown["related_tests_set"]), (value, saved), command)

    # The rule and its template.

    def test_the_template_holds_the_whole_rule_once(self):
        rule = self.rule()
        self.assertNotIn("\n\n", rule)
        self.assertNotIn("{{", rule)
        self.assertNotIn("<!--", rule)
        for sentence in RULE_SENTENCES:
            with self.subTest(sentence=sentence[:50]):
                self.assertRegex(rule, whole_sentence(sentence))
                self.assertEqual(rule.count(sentence), 1)
        # The tool renders the template rather than holding a second copy of the rule.
        source = (config.ROOT / "scripts" / "feather_config.py").read_text(encoding="utf-8")
        for sentence in RULE_SENTENCES:
            self.assertNotIn(sentence[:60], source)

    def test_on_renders_the_rule_after_the_review_paragraph_in_both_modes_and_scopes(self):
        for scope in ("project", "user"):
            for mode in ("auto", "off"):
                with self.subTest(scope=scope, mode=mode):
                    self.apply("install", scope, "--review-mode", mode)
                    self.apply("review", scope, "--related-tests", "on")
                    block = self.block(scope)
                    self.assertEqual(block, self.expected_block(mode, scope, self.on_paragraph(scope)))
                    paragraph = next(p for p in block.split("\n\n") if p.startswith("Related-test acceptance"))
                    self.assertRegex(paragraph, whole_sentence(PROJECT_ON if scope == "project" else USER_ON))
                    for sentence in RULE_SENTENCES:
                        self.assertRegex(paragraph, whole_sentence(sentence))
                    self.assertNotIn(PROJECT_OFF, block)
                    self.assertEqual(self.older_template_warnings(scope), [])
                    self.apply("remove", scope)

    def test_the_rule_follows_a_saved_stop_threshold_sentence(self):
        for scope in ("project", "user"):
            for mode in ("auto", "off"):
                with self.subTest(scope=scope, mode=mode):
                    self.apply("install", scope, "--review-mode", mode)
                    self.apply("review", scope, "--stop-threshold", "4", "--related-tests", "on")
                    self.assertEqual(self.block(scope), self.expected_block(mode, scope, self.on_paragraph(scope), 4))
                    self.assertEqual(self.older_template_warnings(scope), [])
                    self.apply("remove", scope)

    def test_project_off_renders_one_override_sentence_after_the_stop_threshold_sentence(self):
        for mode in ("auto", "off"):
            with self.subTest(mode=mode):
                self.apply("install", "project", "--review-mode", mode)
                self.apply("review", "project", "--related-tests", "off")
                self.assertEqual(self.record("project")["related_tests"], "off")
                self.assertEqual(self.block("project"), self.expected_block(mode, "project", PROJECT_OFF))
                self.apply("review", "project", "--stop-threshold", "5")
                self.assertEqual(self.block("project"), self.expected_block(mode, "project", PROJECT_OFF, 5))
                self.assertNotIn(RULE_SENTENCES[0], self.block("project"))
                self.assert_reported("project", "off", True)
                self.assertEqual(self.older_template_warnings("project"), [])
                self.apply("remove", "project")

    # Saving, reporting and removing.

    def test_review_saves_shows_and_removes_the_setting_in_each_scope(self):
        for scope in ("project", "user"):
            with self.subTest(scope=scope):
                self.apply("install", scope, "--review-mode", "auto")
                guidance_before = self.guidance(scope).read_bytes()
                state_before = self.state_path(scope).read_bytes()
                self.assert_reported(scope, "off", False)
                code, preview = self.call("review", scope, "--related-tests", "on")
                self.assertEqual(code, 0, preview)
                self.assertEqual((preview["related_tests"], preview["related_tests_set"]), ("on", True))
                self.assertEqual(self.guidance(scope).read_bytes(), guidance_before)
                self.apply("review", scope, "--related-tests", "on")
                self.assertEqual(self.record(scope)["related_tests"], "on")
                self.assertEqual(self.record(scope)["review_mode"], "auto")
                self.assertEqual(self.block(scope).count(self.on_paragraph(scope)), 1)
                self.assert_reported(scope, "on", True)
                self.assertEqual(self.older_template_warnings(scope), [])
                self.apply("review", scope, "--related-tests", "default")
                self.assertNotIn("related_tests", self.record(scope))
                self.assertEqual(self.guidance(scope).read_bytes(), guidance_before)
                self.assertEqual(self.state_path(scope).read_bytes(), state_before)
                self.assert_reported(scope, "off", False)
                code, preview = self.call("review", scope, "--related-tests", "default")
                self.assertEqual((code, preview["changes"]), (0, []), preview)

    def test_user_scope_off_saves_nothing_and_removes_a_saved_on(self):
        self.apply("install", "user", "--review-mode", "auto")
        guidance_before = self.guidance("user").read_bytes()
        state_before = self.state_path("user").read_bytes()
        code, preview = self.call("review", "user", "--related-tests", "off")
        self.assertEqual((code, preview["changes"]), (0, []), preview)
        self.assertEqual((preview["related_tests"], preview["related_tests_set"]), ("off", False))
        self.apply("review", "user", "--related-tests", "on")
        self.apply("review", "user", "--related-tests", "off")
        self.assertNotIn("related_tests", self.record("user"))
        self.assertNotIn("Related-test acceptance", self.guidance("user").read_text(encoding="utf-8"))
        self.assertEqual(self.guidance("user").read_bytes(), guidance_before)
        self.assertEqual(self.state_path("user").read_bytes(), state_before)
        self.assert_reported("user", "off", False)

    def test_project_off_and_default_and_on_switch_between_each_other(self):
        self.apply("install", "project", "--review-mode", "auto")
        before = self.guidance("project").read_bytes()
        self.apply("review", "project", "--related-tests", "off")
        self.apply("review", "project", "--related-tests", "on")
        self.assertEqual(self.block("project"), self.expected_block("auto", "project", self.on_paragraph("project")))
        self.apply("review", "project", "--related-tests", "off")
        self.assertEqual(self.block("project"), self.expected_block("auto", "project", PROJECT_OFF))
        self.apply("review", "project", "--related-tests", "default")
        self.assertEqual(self.guidance("project").read_bytes(), before)

    def test_guidance_without_a_saved_setting_is_byte_identical_to_0_33_0(self):
        for scope in ("project", "user"):
            for mode in ("auto", "off"):
                with self.subTest(scope=scope, mode=mode):
                    self.apply("install", scope, "--review-mode", mode)
                    self.assertEqual(self.block(scope), self.release_0_33_0_block(mode, scope))
                    before = self.guidance(scope).read_bytes()
                    self.assertNotIn("related_tests", self.record(scope))
                    self.apply("review", scope, "--related-tests", "on")
                    self.apply("review", scope, "--related-tests", "default")
                    self.assertEqual(self.guidance(scope).read_bytes(), before)
                    self.assertNotIn("related_tests", self.record(scope))
                    self.assertEqual(self.older_template_warnings(scope), [])
                    self.apply("remove", scope)

    def test_review_combines_all_three_settings_in_one_plan(self):
        self.apply("install", "project", "--review-mode", "off")
        before = self.files()
        code, error = self.call("review", "project")
        self.assertEqual(code, 2, error)
        self.assertIn("--related-tests", error["error"])
        self.assertEqual(self.files(), before)
        self.apply("review", "project", "--review-mode", "auto", "--stop-threshold", "5", "--related-tests", "on")
        record = self.record("project")
        self.assertEqual((record["review_mode"], record["stop_threshold"], record["related_tests"]), ("auto", 5, "on"))
        self.assertEqual(self.block("project"), self.expected_block("auto", "project", self.on_paragraph("project"), 5))
        self.apply("review", "project", "--review-mode", "off", "--related-tests", "default")
        self.assertEqual(self.block("project"), self.release_0_33_0_block("off", "project", 5))
        self.assertNotIn("related_tests", self.record("project"))

    # Refusals.

    def test_invalid_values_commands_and_scopes_are_refused_before_writing(self):
        self.apply("install", "project", "--review-mode", "auto")
        before = self.files()
        for value in ("", "On", "ON", "true", "yes", "1", "auto", " on", "on ", "none", "unset"):
            with self.subTest(value=value):
                code, error = self.call("review", "project", "--related-tests", value)
                self.assertEqual((code, error["status"]), (2, "error"), error)
                self.assertIn("--related-tests", error["error"])
                self.assertEqual(self.files(), before)
        for command, extra in (("install", ("--component", "handoff")), ("update", ()), ("remove", ()),
                               ("model", ("--set", "scout.model=sonnet")), ("check", ()), ("show", ()),
                               ("session", ())):
            with self.subTest(command=command):
                code, error = self.call(command, "project", *extra, "--related-tests", "on")
                self.assertEqual((code, error["status"]), (2, "error"), error)
                self.assertIn("--related-tests", error["error"])
                self.assertEqual(self.files(), before)
        code, error = self.call("review", "project", "--component", "handoff", "--related-tests", "on")
        self.assertEqual(code, 2, error)
        self.assertEqual(self.files(), before)
        # Delegation absent from the scope: nothing installed there, or only the handoff component.
        for value in ("on", "off", "default"):
            code, error = self.call("review", "user", "--related-tests", value)
            self.assertEqual(code, 2, error)
            self.assertIn("user delegation component is not installed", error["error"])
        self.apply("install", "user", "--component", "handoff")
        before = self.files()
        code, error = self.call("review", "user", "--related-tests", "on")
        self.assertEqual(code, 2, error)
        self.assertIn("user delegation component is not installed", error["error"])
        self.assertEqual(self.files(), before)

    def test_a_malformed_saved_setting_is_refused_on_load(self):
        for scope, bads in (("project", (True, False, "", "On", "default", "auto", None, 1, ["on"], {"on": 1})),
                            ("user", ("off", True, False, "default", None))):
            self.apply("install", scope, "--review-mode", "auto")
            self.apply("review", scope, "--related-tests", "on")
            path = self.state_path(scope)
            valid = json.loads(path.read_bytes())
            for bad in bads:
                with self.subTest(scope=scope, bad=bad):
                    state = json.loads(json.dumps(valid))
                    state["components"]["delegation"]["related_tests"] = bad
                    path.write_bytes(config.canonical(state) + b"\n")
                    before = self.files()
                    for command, extra in (("check", ()), ("show", ()), ("session", ()),
                                           ("review", ("--related-tests", "on")), ("update", ())):
                        code, error = self.call(command, scope, *extra)
                        self.assertEqual((code, error["status"]), (2, "error"), (command, error))
                        self.assertIn("invalid saved related-test acceptance", error["error"])
                    self.assertEqual(self.files(), before)
            path.write_bytes(config.canonical(valid) + b"\n")
            self.assertEqual(self.call("check", scope)[1]["status"], "ok")

    def test_older_template_guidance_is_not_changed_by_the_setting(self):
        legacy = ("<!-- cc-feather:begin -->\n# Feather delegation for Claude Code\n\nOlder rules.\n\n"
                  "Automatic plan review mode: {mode}\n\nOlder triggers.\n\n<!-- cc-feather:end -->")
        with mock.patch.object(config, "_policy", lambda mode, prefix="", *, scope="user": legacy.format(mode=mode)):
            self.apply("install", "project", "--review-mode", "off")
        before = self.files()
        for extra in (("--related-tests", "on"), ("--related-tests", "off"),
                      ("--review-mode", "auto", "--related-tests", "on")):
            with self.subTest(extra=extra):
                code, error = self.call("review", "project", *extra)
                self.assertEqual(code, 2, error)
                self.assertIn("installed guidance is from an older template; run setup update first", error["error"])
                self.assertEqual(self.files(), before)
        # Default where none is saved changes nothing, and setup update makes the scope editable.
        code, preview = self.call("review", "project", "--related-tests", "default")
        self.assertEqual((code, preview["changes"]), (0, []), preview)
        self.apply("update")
        self.apply("review", "project", "--related-tests", "on")
        self.assertEqual(self.block("project"), self.expected_block("off", "project", self.on_paragraph("project")))

    # Session export, preservation and rollback.

    def test_session_export_is_unchanged_by_a_saved_setting(self):
        for scope, value in (("project", "on"), ("project", "off"), ("user", "on")):
            with self.subTest(scope=scope, value=value):
                self.apply("install", scope, "--review-mode", "auto")
                code, exported = self.call("session", scope)
                self.assertEqual(code, 0, exported)
                self.apply("review", scope, "--related-tests", value)
                self.assertEqual(self.call("session", scope), (0, exported))
                self.apply("remove", scope)

    def test_other_changes_keep_the_setting_and_removing_delegation_drops_it(self):
        for scope, value in (("project", "on"), ("project", "off"), ("user", "on")):
            with self.subTest(scope=scope, value=value):
                paragraph = self.on_paragraph(scope) if value == "on" else PROJECT_OFF
                self.apply("install", scope, "--component", "delegation", "--review-mode", "auto")
                self.apply("review", scope, "--related-tests", value)
                steps = (("update", ("--component", "delegation")),
                         ("model", ("--set", "scout.model=sonnet")),
                         ("review", ("--review-mode", "off")),
                         ("review", ("--stop-threshold", "6")),
                         ("update", ("--component", "delegation")),
                         ("review", ("--review-mode", "auto")),
                         ("review", ("--stop-threshold", "default")),
                         ("install", ("--component", "handoff")),
                         ("update", ("--component", "both")),
                         ("remove", ("--component", "handoff")),
                         ("install", ("--component", "leases")),
                         ("remove", ("--component", "leases")))
                for command, extra in steps:
                    self.apply(command, scope, *extra)
                    self.assertEqual(self.record(scope)["related_tests"], value, (command, extra))
                    block = self.block(scope)
                    self.assertEqual(block.count(paragraph), 1, (command, extra))
                    self.assertTrue(block.endswith(paragraph + "\n\n" + config.END), (command, extra))
                    self.assert_reported(scope, value, True)
                    self.assertEqual(self.older_template_warnings(scope), [], (command, extra))
                self.assertEqual(self.call("show", scope)[1]["choices"]["scout"]["model"], "sonnet")
                self.apply("remove", scope, "--component", "delegation")
                self.assertFalse(self.state_path(scope).exists())
                self.assertNotIn("Related-test acceptance", self.guidance(scope).read_text(encoding="utf-8")
                                 if self.guidance(scope).exists() else "")
                shown = self.call("show", scope)[1]
                self.assertEqual((shown["related_tests"], shown["related_tests_set"]), ("off", False))
                # Removing delegation alongside handoff removes the saved setting too.
                self.apply("install", scope, "--component", "both", "--review-mode", "off")
                self.apply("review", scope, "--related-tests", value)
                self.apply("remove", scope, "--component", "delegation")
                self.assertNotIn("delegation", json.loads(self.state_path(scope).read_bytes())["components"])
                self.assertNotIn("Related-test acceptance", self.guidance(scope).read_text(encoding="utf-8"))
                self.apply("install", scope, "--component", "delegation")
                self.assertNotIn("related_tests", self.record(scope))
                self.apply("remove", scope, "--component", "both")

    def test_a_failed_write_rolls_back_state_and_guidance(self):
        self.apply("install", "project", "--review-mode", "auto")
        self.apply("review", "project", "--related-tests", "on")
        guidance, state_path = self.guidance("project"), self.state_path("project")
        for extra in (("--related-tests", "off"), ("--related-tests", "default"),
                      ("--review-mode", "off", "--stop-threshold", "4", "--related-tests", "off")):
            with self.subTest(extra=extra):
                original = (guidance.read_bytes(), state_path.read_bytes())
                _, preview = self.call("review", "project", *extra)
                real_replace = config._replace

                def fail_state(path, data):
                    if path == state_path:
                        raise OSError("injected state failure")
                    return real_replace(path, data)

                with mock.patch.object(config, "_replace", side_effect=fail_state):
                    code, result = self.call("review", "project", *extra, "--apply", "--expected-plan", preview["plan_id"])
                self.assertEqual(code, 2, result)
                self.assertIn("injected state failure", result["error"])
                self.assertEqual((guidance.read_bytes(), state_path.read_bytes()), original)
                self.assertEqual(self.call("show")[1]["related_tests"], "on")


class RelatedTestsSetupDocumentTests(unittest.TestCase):
    def test_setup_document_describes_the_setting(self):
        setup = (config.ROOT / "docs" / "setup.md").read_text(encoding="utf-8")
        section = " ".join(setup.split("\n## Related-test acceptance\n", 1)[1].split("\n## ", 1)[0].split())
        for sentence in (
                "Related-test acceptance is a delegation setting that changes how main writes a Claim's acceptance in a spec, ticket or plan: with it on, the acceptance names the test modules related to the change instead of the full test suite, and the Plan's overall acceptance keeps the full suite, which the final check runs.",
                "It is off by default.",
                "`review --related-tests <on|off|default>` saves it in project or user scope, alone or together with `--review-mode` and `--stop-threshold`, through the usual preview and `--apply --expected-plan` steps; it needs the delegation component installed in that scope, and `default` removes the saved setting.",
                "A project can save `off` to override a user `on`; in user scope `off` is the default and saves nothing.",
                "The configuration tool refuses any other value, `--related-tests` on another command, and a scope without delegation before it writes anything.",
                "A scope saved `on` carries the whole rule in its managed delegation block, after the automatic review paragraph and after a saved Stop threshold sentence, in auto and in off; project scope says it is on in this project and that this overrides broader Feather guidance.",
                "A project saved `off` states in one sentence in the same place that Related-test acceptance is off in this project and that this overrides broader Feather guidance.",
                "The rule is written once, in `templates/related-tests.md`, which the configuration tool renders; this document describes it without restating it.",
                "That guidance text is how main learns a saved choice: main writes acceptance while writing a spec, tickets or a plan, when the delegation skill is not necessarily loaded, so the loaded guidance carries the whole rule.",
                "A scope without a saved setting has no such text, so its guidance and state stay byte-identical to what 0.33.0 writes.",
                "Delegation guidance from a template older than the one the tool can edit is not changed: `--related-tests` asks for setup update first.",
                "`show` and `check` report `related_tests`, which is the saved setting or `off`, and `related_tests_set`, which is false when none is saved; session export is unchanged.",
                "Setup update, `model`, switching the review mode, changing the Stop threshold and installing or removing the handoff or leases component keep the saved setting and its rule; removing the delegation component removes both.",
                "A 0.33.x or older configuration tool rejects a scope with a saved setting, so a downgrade first sets it back to `default` there.",
                "In a session, the setting in effect is the user's session choice, then the project guidance, then the user guidance, then off; a session choice comes only from the user's own words in this conversation and is not written into a handoff.",
                "A choice saved in project or user scope during a conversation replaces an earlier session choice, and the setting in effect is resolved again from the saved choices, as for the Stop threshold.",
                "The setting changes how main writes acceptance, not how any review or the final check runs.",
                "A Claim that breaks a test its acceptance does not name passes its own reviews; the break is found only at the final check.",
                "In auto, a failure attributed with evidence to that Claim is then fixed by that Claim with its code review and outcome verification again, and an unattributed one becomes a fix Claim; in off, the failure reopens the Claims it affects.",
                "The final check runs before landing and release, so work that main never lands or releases does not get the full suite from this setting.",
                "Finding related tests by searching for paths and directory names can miss a test that reaches a file only through a path built at run time from parts that are not searched for.",
                "The rule binds how main writes acceptance in sessions where the guidance or a session choice turns it on; acceptance written elsewhere, or by the user, is taken as written."):
            with self.subTest(sentence=sentence[:50]):
                self.assertRegex(section, whole_sentence(sentence))
        # The setup document describes the rule without restating it.
        for sentence in RULE_SENTENCES:
            self.assertNotIn(sentence, section)


class RelatedTestsCommandTests(unittest.TestCase):
    """Ticket 02: /cc-feather:related-tests is a user-invoked command whose procedure lives in one reference under
    the setup skill, which the delegation and setup skills point to, and which reaches the rule only through its
    template; the READMEs, the reference documents and the setup document describe it."""

    COMMAND = config.ROOT / "skills" / "related-tests" / "SKILL.md"
    PROCEDURE = config.ROOT / "skills" / "setup" / "references" / "related-tests.md"
    SECTIONS = {"README.md": "\n### Related-test acceptance\n", "README.zh-TW.md": "\n### 相關測試驗收\n",
                "reference.md": "\n### Related-test acceptance\n", "reference.zh-TW.md": "\n### 相關測試驗收\n",
                "setup.md": "\n## Related-test acceptance\n"}

    @classmethod
    def source(cls, name: str) -> str:
        """'<file>', '<file>#section' for the README, reference and setup sections, or 'related-tests.md#<heading>'
        for a '## <heading>' section of the shared procedure."""
        path, _, label = name.partition("#")
        files = {
            "related-tests SKILL.md": cls.COMMAND,
            "related-tests.md": cls.PROCEDURE,
            "delegation SKILL.md": config.ROOT / "skills" / "delegation" / "SKILL.md",
            "setup SKILL.md": config.ROOT / "skills" / "setup" / "SKILL.md",
            "setup.md": config.ROOT / "docs" / "setup.md",
            "README.md": config.ROOT / "README.md",
            "README.zh-TW.md": config.ROOT / "README.zh-TW.md",
            **feather_support.REFERENCE_FILES,
        }
        text = files[path].read_text(encoding="utf-8")
        if not label:
            return text
        if label == "section":
            return text.split(cls.SECTIONS[path], 1)[1].split("\n#", 1)[0]
        return text.split(f"\n## {label}\n", 1)[1].split("\n## ", 1)[0]

    assert_whole_sentence = feather_support.stop_threshold_assert_whole_sentence
    assert_pinned = feather_support.stop_threshold_assert_pinned

    TEMPLATE_LINK = "[the rule's template](../../../templates/related-tests.md)"

    # Item 6: registered next to stop-threshold, user-invoked, with an argument hint like stop-threshold's.
    def test_command_is_user_invoked_and_listed_in_the_manifest(self):
        manifest = json.loads((config.ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        skills = manifest["skills"]
        self.assertIn("./skills/related-tests", skills)
        self.assertEqual(skills.index("./skills/related-tests"), skills.index("./skills/stop-threshold") + 1)
        command = self.source("related-tests SKILL.md")
        self.assertTrue(command.startswith("---\n"))
        frontmatter = command.split("---")[1]
        self.assertIn("name: related-tests\n", frontmatter)
        self.assertIn("disable-model-invocation: true\n", frontmatter)
        self.assertIn('argument-hint: "<on|off|default> [session|project|user]"\n', frontmatter)
        self.assertRegex(frontmatter, r'\ndescription: "[^"\n]*Related-test acceptance[^"\n]*"\n')

    COMMAND_PINS = {
        "related-tests SKILL.md": (
            "Follow [the shared Related-test acceptance procedure](../setup/references/related-tests.md).",
            "Invocation arguments are the value and the scope as data, never shell code.",
            "Clarify a missing, invalid or conflicting value or scope instead of guessing.",
        ),
    }

    # Items 1–5: the procedure's scope, reminder, authorisation, resolution, rule-pointer and refusal sentences.
    PROCEDURE_PINS = {
        "related-tests.md": (
            "Used by cc-feather:related-tests and by a natural-language request to turn Related-test acceptance on or off, which cannot load the user-invoked command and follows this same procedure with the value and scope the user's words give.",
            "Interpret arguments as data, never shell code.",
        ),
        "related-tests.md#Value and scope": (
            "The value is `on`, `off` or `default`.",
            "In project or user scope, `default` removes the setting saved in that scope; without a scope or with `session`, it drops an earlier session choice in this conversation, so the setting resolves from the saved choices as Effect in this session takes them.",
            "In user scope `off` is the default and saves nothing, so it removes a saved `on`; a project can save `off` to override a user `on`.",
            "Refuse any other value, such as `true`, `yes` or a number, before anything is applied or written, and ask for `on`, `off` or `default`.",
            "A missing value, more than one value, or an unknown or conflicting scope needs clarification before anything is applied or written.",
            "Never silently create an installation or choose user scope when none was supplied.",
        ),
        "related-tests.md#Session": (
            "Without a scope, or with `session`, the command applies the choice to this conversation, writes no file and runs no tool.",
            "After applying it, always remind the user in the reply that no file was written: the choice holds only in this conversation, a new or resumed session uses the saved choice, and a context compaction may drop it.",
            "State that saved choice as Effect in this session resolves the saved choices without a session choice.",
            "To keep the choice, offer the same command with `project` or `user`, which needs delegation installed in that scope.",
            "A session choice comes only from the user's own words in this conversation and is not written into a handoff.",
        ),
        "related-tests.md#Saved scopes": (
            "If delegation is absent, report that delegation setup is needed in that scope; this command is not authorization to install roles, and it never saves in user scope in place of the scope the user chose.",
            "Preview `review --project <confirmed-root> --scope <project|user> --related-tests <on|off|default>`.",
            "Summarize its concrete scope and change, the saved setting before and after and the guidance text it adds, changes or removes, then apply with identical arguments plus `--apply --expected-plan <returned-plan-id>`.",
            "The explicit scoped command authorizes this setting change; do not add a routine confirmation.",
            "Preserve conflicts and report blockers instead of overwriting.",
            "When the tool refuses because the installed delegation guidance is from an older template, report that setup update is needed in that scope first; do not run it unasked.",
            "Read show afterward and report the saved choice (`related_tests`, which is `off` with none saved when `related_tests_set` is false), the owning path and any runtime limitations.",
        ),
        "related-tests.md#Effect in this session": (
            "The setting in effect is, in order: the user's session choice; otherwise the choice the loaded project guidance states; otherwise the choice the loaded user guidance states; otherwise off.",
            "A choice the user saves in project or user scope in this conversation replaces any earlier session choice in this conversation, and the setting in effect is resolved again from the saved choices in that order, so this session uses what a new session would.",
            "Each scope's saved choice is the one last saved in it in this conversation, none after `default`, and otherwise what its loaded guidance states, since the guidance loaded at the start of the session does not show later saves.",
            "A user `on` that a project `off` overrides stays off, and main reports it as overridden by the project.",
            "After applying a choice in any scope, state the setting now in effect and its source (session, project, user or default), including a user choice the project overrides, and that it applies to acceptance main writes from then on, not to acceptance already written.",
        ),
        "related-tests.md#The rule": (
            "Whenever the setting in effect is `on` while the loaded guidance carries no rule, from a session choice or from a choice saved earlier in this conversation, main reads and follows " + TEMPLATE_LINK + ", which the configuration tool renders the rule from.",
            "While `on` is in effect, main applies that rule as if the guidance stated that Related-test acceptance is on.",
            "Whenever the setting in effect is off, main does not apply the rule, even where the loaded guidance carries it.",
            "After a context compaction, main establishes the saved choices again with the tool's `show` in project and user scope and rereads the template before applying the rule.",
        ),
        "related-tests.md#Meaning": (
            "Main never changes the setting on its own.",
            "The setting changes how main writes acceptance, not how any review or the final check runs.",
            "Related-test acceptance is a model instruction, not a hook-enforced check.",
        ),
    }

    # Item 4: the delegation skill and the setup skill point to the shared procedure; the setup document names it.
    POINTER_PINS = {
        "delegation SKILL.md": (
            "For a request to turn Related-test acceptance on or off, follow [the Related-test acceptance procedure](../setup/references/related-tests.md), as `/cc-feather:related-tests` does.",
        ),
        "setup SKILL.md": (
            "Also includes an optional saved Related-test acceptance setting, default off, rendered in the instruction file only while one is saved.",
            "Dedicated related-tests follows [the Related-test acceptance procedure](references/related-tests.md): no scope/session is a conversation choice, while project/user saves the setting only when delegation is installed, and a request for it never installs delegation.",
        ),
        "setup.md#section": (
            "`/cc-feather:related-tests <on|off|default> [session|project|user]` is the command for it, and a natural-language request follows the same procedure (`skills/setup/references/related-tests.md`).",
            "Without a scope, or with `session`, it sets the session choice, writes no file and runs no tool.",
            "`project` and `user` run the preview and apply above in an existing delegation installation of that scope, without a routine confirmation, then read show and report the saved choice and owning path; they do not install missing roles and never choose user scope unasked.",
            "A value other than `on`, `off` or `default`, or an unknown or conflicting scope, is refused or clarified before anything is applied or written.",
            "Because a session choice, or a choice saved during the conversation, is not in the guidance the session loaded, the procedure has main read and follow the rule from `templates/related-tests.md` while the setting in effect is on.",
        ),
    }

    # Item 6: the README and reference sentences, paired in both languages.
    README_PAIRS = (
        ("Related-test acceptance changes how main writes a Claim's acceptance in a spec, ticket or plan: with it on, the acceptance names the test modules related to the change instead of the full test suite, and the Plan's overall acceptance keeps the full suite, which the final check runs.",
         "相關測試驗收（Related-test acceptance）改變主 Agent 在 spec、ticket 或計畫中撰寫 Claim 驗收的方式：開啟時，驗收列出與變更相關的測試模組，而不是完整測試；計畫的整體驗收仍是完整測試，由最終檢查執行。"),
        ("It is off by default.",
         "預設關閉。"),
        ("Without a scope (or with `session`) it applies to this session only and writes nothing; `project` or `user` saves it in an existing delegation installation of that scope, and it never installs delegation.",
         "不帶範圍（或加 `session`）時只用於這個 session，不寫入任何檔案；加 `project` 或 `user` 時，會儲存到該範圍既有的 agent 分派安裝，它絕不會安裝 agent 分派。"),
        ("Main uses your session choice, then the project's saved choice, then the user's, then off, so a project's `off` overrides a user's `on`; main never changes it on its own.",
         "主 Agent 依序採用你在這個 session 的選擇、專案儲存的選擇、使用者儲存的選擇，最後才是關閉，所以專案的 `off` 會覆蓋使用者的 `on`；主 Agent 絕不自行更改。"),
        ("It changes how main writes acceptance, not how any review or the final check runs, and a change applies to acceptance main writes from then on, not to acceptance already written.",
         "它只改變主 Agent 撰寫驗收的方式，不改變任何審查或最終檢查的執行方式；變更只適用於之後撰寫的驗收，不改動已寫好的驗收。"),
    )
    REFERENCE_PAIRS = (
        ("`/cc-feather:related-tests` sets it, or asking main in your own words does the same.",
         "用 `/cc-feather:related-tests` 設定，或用自己的話請主 Agent 設定，效果相同。"),
        ("A session choice does not carry into a new or resumed session and is not written into a handoff, and context compaction may drop it.",
         "session 選擇不會帶到新的或恢復的 session，也不會寫進交接，而且 context 壓縮可能讓它遺失。"),
        ("The rule itself is written once, in the [template](../templates/related-tests.md) the configuration tool renders into the delegation guidance; how a choice is applied, saved and resolved is the [setup Related-test acceptance procedure](../skills/setup/references/related-tests.md).",
         "規則本身只寫在設定工具渲染進分派指引的[範本](../templates/related-tests.md)中；選擇如何套用、儲存與決定，寫在[setup 的相關測試驗收流程](../skills/setup/references/related-tests.md)。"),
    )
    README_LISTINGS = {
        "README.md": ("- `/cc-feather:stop-threshold <2–10|default> [session|project|user]`: set the [Stop threshold](#stop-threshold) of automatic review for this session, or save it in project or user scope.\n"
                      "- `/cc-feather:related-tests <on|off|default> [session|project|user]`: turn [Related-test acceptance](#related-test-acceptance) on or off for this session, or save it in project or user scope.\n"),
        "README.zh-TW.md": ("| `/cc-feather:stop-threshold <2–10 或 default> [範圍]` | 設定自動審查的[停止門檻](#停止門檻)：只用於這個 session（不帶範圍或 `session`），或儲存在 `project` 或 `user` 範圍 |\n"
                            "| `/cc-feather:related-tests <on、off 或 default> [範圍]` | 開啟或關閉[相關測試驗收](#相關測試驗收)：只用於這個 session（不帶範圍或 `session`），或儲存在 `project` 或 `user` 範圍 |\n"),
    }
    EXAMPLES = ("```text\n/cc-feather:related-tests on\n/cc-feather:related-tests off project\n"
                "/cc-feather:related-tests default user\n```")

    def test_command_points_to_the_shared_procedure(self):
        self.assert_pinned(self.COMMAND_PINS)
        self.assertTrue(self.PROCEDURE.is_file())

    def test_shared_procedure_states_scope_reminder_authorisation_resolution_and_refusals(self):
        self.assert_pinned(self.PROCEDURE_PINS)

    def test_delegation_and_setup_point_to_the_shared_procedure(self):
        self.assert_pinned(self.POINTER_PINS)

    def test_the_procedure_points_to_the_template_that_holds_the_rule(self):
        procedure = self.source("related-tests.md")
        self.assertIn(self.TEMPLATE_LINK, procedure)
        target = (self.PROCEDURE.parent / "../../../templates/related-tests.md").resolve()
        self.assertEqual(target, TEMPLATE.resolve())
        self.assertTrue(target.is_file())
        template = target.read_text(encoding="utf-8")
        for sentence in RULE_SENTENCES:
            with self.subTest(sentence=sentence[:50]):
                self.assertRegex(template, whole_sentence(sentence))

    # The rule is written once (ADR 0017): the command, its procedure and the documents describing it hold none of
    # the rule's decision-carrying sentences or their distinctive clauses.
    RULE_CLAUSES = (
        "found by searching the tests for those files' paths and directory names",
        "shared test support or build configuration",
        "when its related tests cannot be determined",
        "The named tests are a minimum",
        "running more for a file the list does not cover",
        "keeps the full suite itself",
        "keep their wording",
        "in the spec for tickets of a spec",
    )

    def test_the_command_and_its_descriptions_do_not_restate_the_rule(self):
        for place in ("related-tests SKILL.md", "related-tests.md", "README.md#section", "reference.md#section",
                      "setup.md#section", "delegation SKILL.md", "setup SKILL.md"):
            text = " ".join(self.source(place).split())
            for phrase in (*RULE_SENTENCES, *self.RULE_CLAUSES):
                with self.subTest(place=place, phrase=phrase[:50]):
                    self.assertNotIn(phrase, text)

    def test_guidance_templates_are_unchanged_by_the_command(self):
        # Item 4: the command adds no guidance text, and no template names the command or its procedure.
        for path in sorted((config.ROOT / "templates").rglob("*.md")):
            with self.subTest(template=path.relative_to(config.ROOT).as_posix()):
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("cc-feather:related-tests", text)
                self.assertNotIn("references/related-tests.md", text)

    def test_readmes_list_and_describe_the_command_in_both_languages(self):
        for name, listing in self.README_LISTINGS.items():
            with self.subTest(listing=name):
                self.assertIn(listing, self.source(name))
        for name in ("README.md", "README.zh-TW.md", "reference.md", "reference.zh-TW.md"):
            with self.subTest(examples=name):
                self.assertIn(self.EXAMPLES, self.source(f"{name}#section"))
        for english, chinese in self.README_PAIRS:
            self.assert_pinned({"README.md#section": (english,), "README.zh-TW.md#section": (chinese,)})
        for english, chinese in (*self.README_PAIRS, *self.REFERENCE_PAIRS):
            self.assert_pinned({"reference.md#section": (english,), "reference.zh-TW.md#section": (chinese,)})

    def test_the_section_follows_the_stop_threshold_section(self):
        for name, stop, related in (("README.md", "\n### Stop threshold\n", "Related-test acceptance\n"),
                                    ("README.zh-TW.md", "\n### 停止門檻\n", "相關測試驗收\n"),
                                    ("reference.md", "\n### Stop threshold\n", "Related-test acceptance\n"),
                                    ("reference.zh-TW.md", "\n### 停止門檻\n", "相關測試驗收\n")):
            with self.subTest(name=name):
                after_stop = self.source(name).split(stop, 1)[1]
                self.assertTrue(after_stop.split("\n### ", 1)[1].startswith(related))


if __name__ == "__main__":
    unittest.main()
