"""Related-test acceptance ticket 01: the configuration tool saves, renders, shows, keeps and removes the setting per
scope, the rule lives once in its template, and the setup document describes the setting."""

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


if __name__ == "__main__":
    unittest.main()
