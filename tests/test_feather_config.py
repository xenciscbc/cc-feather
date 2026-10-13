"""Configuration tool tests: scripts/feather_config.py's install, update, removal, review, model and Stop threshold
settings, the state and guidance it writes, and the README rules it shares with the procedures."""

from __future__ import annotations

import contextlib
import errno
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from tests import feather_support
from tests.feather_support import SCRIPT, config, make_directory_link, remove_directory_link, remove_link_base


class FeatherConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        # Setup reports and writes resolved paths, so expected paths start from the canonical temp root
        # even when TEMP itself is reached through a link.
        self.root = Path(os.path.realpath(self.temp.name))
        self.project = self.root / "project"
        self.home = self.root / "claude-home"
        self.project.mkdir()
        self.home.mkdir()

    def call(self, command, scope="project", *extra):
        args = [command, "--project", str(self.project), "--scope", scope,
                "--claude-home", str(self.home), *extra]
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = config.main(args)
        return code, json.loads(output.getvalue())

    def apply(self, command, scope="project", *extra):
        code, preview = self.call(command, scope, *extra)
        self.assertEqual(code, 0, preview)
        self.assertEqual(preview["status"], "preview")
        code, result = self.call(command, scope, *extra, "--apply", "--expected-plan", preview["plan_id"])
        self.assertEqual(code, 0, result)
        self.assertEqual(result["status"], "applied")
        return result

    def test_both_update_remove_skip_absent_unowned_handoff(self):
        self.apply("install", "project", "--component", "delegation")
        guidance = self.project / "CLAUDE.md"
        unowned = b"\n<!-- cc-feather:handoff:begin -->\nUser policy\n<!-- cc-feather:handoff:end -->\n"
        guidance.write_bytes(guidance.read_bytes() + unowned)
        self.apply("update", "project", "--component", "both")
        self.assertTrue(guidance.read_bytes().endswith(unowned))
        self.apply("remove", "project", "--component", "both")
        self.assertEqual(guidance.read_bytes(), unowned)

    def test_both_install_preserves_skipped_delegation_drift(self):
        self.apply("install", "project", "--component", "delegation")
        guidance = self.project / "CLAUDE.md"
        changed = guidance.read_bytes().replace(b"# Feather delegation for Claude Code", b"# Feather delegation, edited")
        guidance.write_bytes(changed)
        role = self.project / ".claude" / "agents" / "analyst.md"
        role.write_bytes(role.read_bytes() + b"\nUser changes\n")
        role_before = role.read_bytes()
        state_path = self.project / ".claude" / "cc-feather" / "state.json"
        record = json.loads(state_path.read_bytes())["components"]["delegation"]
        self.apply("install", "project", "--component", "both")
        self.assertTrue(guidance.read_bytes().startswith(changed))
        self.assertEqual(role.read_bytes(), role_before)
        self.assertEqual(json.loads(state_path.read_bytes())["components"]["delegation"], record)
        inspected = self.call("check")[1]
        self.assertEqual(inspected["components"]["handoff"]["status"], "ok")
        self.assertEqual(inspected["components"]["delegation"]["status"], "conflict")

    def test_both_update_does_not_load_absent_delegation_templates(self):
        self.apply("install", "project", "--component", "handoff")
        with mock.patch.object(config, "_render", side_effect=AssertionError("unused role template")), \
             mock.patch.object(config, "_policy", side_effect=AssertionError("unused policy template")):
            self.apply("update", "project", "--component", "both")

    def test_project_install_exact_explore_and_remove_preserves_other_data(self):
        guidance = self.project / "CLAUDE.md"
        guidance.write_text("User guidance without final newline", encoding="utf-8")
        settings = self.project / ".claude" / "settings.json"
        settings.parent.mkdir()
        settings.write_text('{"model":"leave-me"}', encoding="utf-8")
        handoff = self.project / ".feather" / "handoffs" / "keep.md"
        handoff.parent.mkdir(parents=True)
        handoff.write_text("keep", encoding="utf-8")
        preview_code, preview = self.call("install")
        self.assertEqual(preview_code, 0)
        self.assertFalse((self.project / ".claude" / "agents").exists())
        self.assertEqual(self.call("show")[1]["review_mode"], "off")
        self.assertEqual(preview["review_mode"], "off")
        self.apply("install")
        self.assertEqual(self.call("show")[1]["review_mode"], "off")
        self.assertIn("cc-feather:delegation", guidance.read_text(encoding="utf-8"))
        self.assertIn(config.PROJECT_REVIEW_OFF, guidance.read_text(encoding="utf-8"))
        self.assertNotIn("Automatic plan review is on.", guidance.read_text(encoding="utf-8"))
        explore = self.project / ".claude" / "agents" / "Explore.md"
        self.assertIn("name: Explore", explore.read_text(encoding="utf-8"))
        self.assertIn("model: sonnet", explore.read_text(encoding="utf-8"))
        self.assertIn("effort: low", explore.read_text(encoding="utf-8"))
        self.assertNotIn("{{model}}", explore.read_text(encoding="utf-8"))
        self.assertEqual(self.call("check")[1]["status"], "ok")
        self.apply("remove")
        self.assertFalse(explore.exists())
        self.assertEqual(guidance.read_text(encoding="utf-8"), "User guidance without final newline")
        self.assertEqual(settings.read_text(encoding="utf-8"), '{"model":"leave-me"}')
        self.assertEqual(handoff.read_text(encoding="utf-8"), "keep")

    def test_user_scope_model_per_field_and_update_persists(self):
        self.apply("install", "user")
        self.apply("model", "user", "--set", "analyst.model=sonnet", "--set", "Explore.effort=high")
        self.apply("update", "user")
        show_code, show = self.call("show", "user")
        self.assertEqual(show_code, 0)
        self.assertEqual(show["choices"]["analyst"], {"model": "sonnet", "effort": "high"})
        self.assertEqual(show["choices"]["Explore"], {"model": "sonnet", "effort": "high"})
        self.assertTrue((self.home / "agents" / "Explore.md").exists())
        self.assertFalse((self.project / ".claude" / "agents").exists())

    def test_stale_plan_and_user_explore_is_kept(self):
        code, preview = self.call("install")
        self.assertEqual(code, 0)
        (self.project / "CLAUDE.md").write_text("changed", encoding="utf-8")
        code, error = self.call("install", "project", "--apply", "--expected-plan", preview["plan_id"])
        self.assertEqual(code, 2)
        self.assertIn("matching", error["error"])
        explore = self.project / ".claude" / "agents" / "Explore.md"
        explore.parent.mkdir(parents=True)
        for content in ("owned by user", "---\nname: explore-notes\n---\nNotes\n"):
            with self.subTest(content=content):
                # Not an agent named Explore: the built-in stays active, so this only blocks the path.
                explore.write_text(content, encoding="utf-8")
                before = self.files()
                code, error = self.call("install")
                self.assertEqual(code, 2, error)
                self.assertIn("unowned role file already exists", error["error"])
                self.assertEqual(before, self.files())
                self.assertIsNone(self.call("check")[1]["pending_external_roles"])
        explore.write_text("---\nname: Explore\n---\nMine\n", encoding="utf-8")
        self.apply("install")
        self.assertEqual(explore.read_text(encoding="utf-8"), "---\nname: Explore\n---\nMine\n")
        self.assert_external_explore(prefix="")

    def test_drift_and_malformed_markers_block_mutation(self):
        self.apply("install")
        path = self.project / ".claude" / "agents" / "Explore.md"
        path.write_text("changed", encoding="utf-8")
        code, result = self.call("model", "project", "--set", "scout.model=opus")
        self.assertEqual(code, 2)
        self.assertIn("managed role changed", result["error"])
        self.assertEqual(self.call("check")[1]["status"], "conflict")
        path.write_bytes(config._render("Explore", {"model": "haiku", "effort": "low"}))
        guidance = self.project / "CLAUDE.md"
        guidance.write_text(guidance.read_text(encoding="utf-8") + config.BEGIN, encoding="utf-8")
        code, result = self.call("remove")
        self.assertEqual(code, 2)
        self.assertIn("malformed", result["error"])

    def test_backups_and_io_rollback(self):
        original = "Keep this guidance"
        (self.project / "CLAUDE.md").write_text(original, encoding="utf-8")
        code, preview = self.call("install")
        self.assertEqual(code, 0)
        real_replace = config._replace
        count = 0
        def fail_second_role(path, data):
            nonlocal count
            if "agents" in path.parts:
                count += 1
                if count == 2:
                    raise OSError("injected failure")
            return real_replace(path, data)
        with mock.patch.object(config, "_replace", side_effect=fail_second_role):
            code, result = self.call("install", "project", "--apply", "--expected-plan", preview["plan_id"])
        self.assertEqual(code, 2)
        self.assertIn("injected failure", result["error"])
        self.assertIn("recovery backups:", result["error"])
        self.assertEqual((self.project / "CLAUDE.md").read_text(encoding="utf-8"), original)
        self.assertFalse((self.project / ".claude" / "agents" / "scout.md").exists())
        self.assertFalse((self.project / ".claude" / "cc-feather" / "state.json").exists())
        self.assertTrue(list((self.project / ".claude" / "cc-feather" / "backups").glob("*/manifest.json")))
        applied = self.apply("install")
        self.assertTrue(Path(applied["backup_dir"]).joinpath("manifest.json").exists())

    def test_replace_copies_mode_before_publish_and_preserves_original_on_failure(self):
        target = self.project / "CLAUDE.md"
        target.write_bytes(b"original")
        mode = stat.S_IMODE(target.stat().st_mode)
        seen = []

        def check_mode(fd, actual):
            self.assertEqual(target.read_bytes(), b"original")
            self.assertEqual(actual, mode)
            seen.append(fd)

        with mock.patch.object(config.os, "fchmod", side_effect=check_mode, create=True):
            config._replace(target, b"updated")
        self.assertEqual(len(seen), 1)
        self.assertEqual(target.read_bytes(), b"updated")
        with mock.patch.object(config.os, "fchmod", side_effect=OSError("mode denied"), create=True):
            with self.assertRaisesRegex(OSError, "mode denied"):
                config._replace(target, b"must not publish")
        self.assertEqual(target.read_bytes(), b"updated")
        self.assertEqual(list(self.project.glob(".cc-feather-*")), [])
        with mock.patch.object(config.os, "fchmod", create=True) as chmod:
            config._replace(self.project / "new.md", b"new")
            chmod.assert_not_called()

    @unittest.skipUnless(os.name == "posix", "requires POSIX permission bits")
    def test_guidance_mode_survives_lifecycle_and_rollback(self):
        guidance = self.project / "CLAUDE.md"
        guidance.write_bytes(b"Existing guidance")
        guidance.chmod(0o640)
        for command, extra in [("install", ()), ("review", ("--review-mode", "auto")),
                               ("update", ())]:
            self.apply(command, "project", *extra)
            self.assertEqual(stat.S_IMODE(guidance.stat().st_mode), 0o640)
        original = guidance.read_bytes()
        _, preview = self.call("review", "project", "--review-mode", "off")
        real_replace = config._replace
        state_path = self.project / ".claude" / "cc-feather" / "state.json"

        def fail_state(path, data):
            if path == state_path:
                raise OSError("injected state failure")
            return real_replace(path, data)

        with mock.patch.object(config, "_replace", side_effect=fail_state):
            code, result = self.call("review", "project", "--review-mode", "off",
                                     "--apply", "--expected-plan", preview["plan_id"])
        self.assertEqual(code, 2, result)
        self.assertEqual(guidance.read_bytes(), original)
        self.assertEqual(stat.S_IMODE(guidance.stat().st_mode), 0o640)
        self.apply("remove")
        self.assertEqual(guidance.read_bytes(), b"Existing guidance")
        self.assertEqual(stat.S_IMODE(guidance.stat().st_mode), 0o640)
        fresh = self.project / "private.md"
        config._replace(fresh, b"private")
        self.assertEqual(stat.S_IMODE(fresh.stat().st_mode), 0o600)

    def drop_added_roles(self, record):
        for role in config.ADDED_ROLES:
            del record["choices"][role]
            del record["hashes"][role]
            (self.project / ".claude" / "agents" / f"{role}.md").unlink()

    def six_role_install(self, version):
        """Simulate a delegation installation saved before the added roles existed."""
        # Version 2 kept only delegation, without the legacy name flag.
        component = "both" if version == 3 else "delegation"
        self.apply("install", "project", "--component", component, "--review-mode", "auto")
        self.apply("model", "project", "--set", "analyst.model=sonnet")
        state_path = self.project / ".claude" / "cc-feather" / "state.json"
        state = json.loads(state_path.read_bytes())
        delegation = state["components"]["delegation"]
        self.drop_added_roles(delegation)
        if version == 2:
            state = {"version": 2, "scope": "project",
                     **{key: value for key, value in delegation.items() if key not in {"legacy_names", "role_prefix", "external_roles"}}}
        else:
            del delegation["role_prefix"], delegation["external_roles"]
            state = {"version": 3, "scope": "project", "components": state["components"]}
        state_path.write_bytes(config.canonical(state) + b"\n")
        return state_path

    def assert_all_unprefixed_roles(self):
        agents = self.project / ".claude" / "agents"
        self.assertEqual({p.name for p in agents.glob("*.md")}, {f"{role}.md" for role in config.ROLES})

    def test_delegation_policy_scopes_plan_driven_statement_to_auto(self):
        self.apply("install", "project", "--review-mode", "auto")
        guidance = self.project / "CLAUDE.md"
        self.assertIn("Before implementing, state whether the work is plan-driven", guidance.read_text(encoding="utf-8"))
        self.apply("review", "project", "--review-mode", "off")
        policy = guidance.read_text(encoding="utf-8")
        self.assertNotIn("plan-driven", policy)
        self.assertIn("explicitly requested plan review, code review or outcome verification", policy)

    def seven_role_install(self):
        """Simulate a delegation installation saved by 0.8.0, before reviewer existed."""
        self.apply("install", "project", "--review-mode", "auto")
        self.apply("model", "project", "--set", "executor.model=sonnet")
        state_path = self.project / ".claude" / "cc-feather" / "state.json"
        state = json.loads(state_path.read_bytes())
        record = state["components"]["delegation"]
        del record["choices"]["reviewer"], record["hashes"]["reviewer"]
        (self.project / ".claude" / "agents" / "reviewer.md").unlink()
        state_path.write_bytes(config.canonical(state) + b"\n")

    def test_fresh_install_includes_reviewer(self):
        self.apply("install")
        self.assert_all_unprefixed_roles()
        text = (self.project / ".claude" / "agents" / "reviewer.md").read_text(encoding="utf-8")
        self.assertIn("name: reviewer", text)
        self.assertIn("model: opus", text)
        self.assertIn("effort: high", text)
        self.assertIn("tools: Read, Glob, Grep, Bash", text)
        for phrase in ("APPROVED", "CHANGES_REQUESTED", "base revision", "untracked", "Do not run tests"):
            self.assertIn(phrase, text)
        self.assertNotIn("{{", text)
        self.assertEqual(self.call("show")[1]["choices"]["reviewer"], {"model": "opus", "effort": "high"})

    def test_code_review_belongs_to_reviewer_not_analyst(self):
        self.apply("install")
        agents = self.project / ".claude" / "agents"
        analyst = (agents / "analyst.md").read_text(encoding="utf-8")
        # Repository safety (Adversarial review of C2, finding F2): the paragraph for roles without a shell defines a
        # review assignment by every kind of review D4 lists, code review included, so that sentence is set aside;
        # nothing else in analyst's template mentions code review.
        definition = ("Every assignment that reads a repository for a plan review, code review, outcome verification, "
                      "Adversarial review or security analysis is a review assignment, whatever mode or name your brief "
                      "gives it.")
        self.assertEqual(analyst.count(definition), 1)
        analyst = analyst.replace(definition, "")
        self.assertNotIn("Code review", analyst)
        self.assertNotIn("code review", analyst)
        self.assertIn("code review to reviewer", (agents / "verifier.md").read_text(encoding="utf-8"))
        self.assertIn("each claim can be verified independently", analyst)
        self.assertNotIn("cut too finely", analyst)

    def test_update_adds_reviewer_to_seven_role_state(self):
        self.seven_role_install()
        shown = self.call("show")[1]
        self.assertEqual(shown["status"], "ok", shown)
        self.assertTrue(shown["role_update_required"])
        self.apply("update")
        self.assert_all_unprefixed_roles()
        shown = self.call("show")[1]
        self.assertFalse(shown["role_update_required"])
        self.assertEqual(shown["review_mode"], "auto")
        self.assertEqual(shown["choices"]["executor"], {"model": "sonnet", "effort": "medium"})
        self.assertEqual(shown["choices"]["reviewer"], {"model": "opus", "effort": "high"})

    def test_seven_role_update_with_unowned_reviewer_moves_to_prefix(self):
        self.seven_role_install()
        agents = self.project / ".claude" / "agents"
        conflict = agents / "reviewer.md"
        user_role = "---\nname: reviewer\n---\nExisting user role\n"
        conflict.write_text(user_role, encoding="utf-8")
        self.assertEqual(self.call("show")[1]["pending_role_prefix"], config.ROLE_PREFIX)
        self.apply("update")
        self.assert_prefixed_roles(agents, extra={"reviewer.md"})
        self.assertEqual(conflict.read_text(encoding="utf-8"), user_role)

    BEDROCK_ARN = "arn:aws:bedrock:us-east-2:123456789012:application-inference-profile/abc123def456"

    def test_bedrock_inference_profile_arn_round_trips_as_a_role_model(self):
        arn = self.BEDROCK_ARN
        code, exported = self.call("session", "project", "--set", f"analyst.model={arn}")
        self.assertEqual(code, 0, exported)  # not installed
        self.assertEqual(exported["analyst"]["model"], arn)
        self.apply("install")
        role = self.project / ".claude" / "agents" / "analyst.md"
        self.apply("model", "project", "--set", f"analyst.model={arn}")
        # Written unquoted: the value reads back as the same string.
        self.assertIn(f"\nmodel: {arn}\n", role.read_text(encoding="utf-8"))
        self.assertEqual(self.call("show")[1]["choices"]["analyst"]["model"], arn)
        self.assertEqual(self.call("check")[0], 0)
        code, exported = self.call("session")
        self.assertEqual(code, 0, exported)
        self.assertEqual(exported["analyst"]["model"], arn)
        self.apply("model", "project", "--set", "analyst.model=sonnet")
        self.assertIn("\nmodel: sonnet\n", role.read_text(encoding="utf-8"))
        self.apply("model", "project", "--set", f"analyst.model={arn}")
        self.apply("update")
        self.assertIn(f"\nmodel: {arn}\n", role.read_text(encoding="utf-8"))
        self.assertEqual(self.call("check")[0], 0)
        try:
            import yaml
        except ImportError:
            return
        frontmatter = role.read_text(encoding="utf-8").split("---\n")[1]
        self.assertEqual(yaml.safe_load(frontmatter)["model"], arn)

    def test_bedrock_arn_syntax_is_bounded(self):
        prefix = "arn:aws:bedrock:us-east-1:123456789012:"
        accepted = (prefix + "inference-profile/us.anthropic.claude-v1:0",
                    "arn:aws-us-gov:bedrock:us-gov-west-1:123456789012:inference-profile/us-gov.anthropic.claude-v1",
                    "arn:aws-cn:bedrock:cn-north-1:123456789012:application-inference-profile/abc123")
        for model in accepted:
            with self.subTest(model=model):
                config._validate_choice(model, "high")
        long_id = prefix + "inference-profile/" + "a" * (config.MAX_ARN_LENGTH - len(prefix + "inference-profile/"))
        config._validate_choice(long_id, "high")
        rejected = (long_id + "a",  # over the length limit
                    prefix + "inference-profile/abc[1m]",  # no suffix after an ARN
                    prefix + "inference-profile/abc:",  # a trailing colon is not a plain YAML value
                    prefix + "foundation-model/anthropic.claude-v1",  # not an inference profile
                    "arn:aws:bedrock:us-east-1:12345:inference-profile/abc",  # account is twelve digits
                    prefix + "inference-profile/a b",
                    prefix + "inference-profile/a---b",  # "---" would close Claude Code's frontmatter early
                    "arn:aws:bedrock:us---east:123456789012:inference-profile/x",
                    "arn:aws-iso:bedrock:us-iso-east-1:123456789012:inference-profile/x")  # unlisted partition
        for model in rejected:
            with self.subTest(model=model[:80]), self.assertRaisesRegex(config.ConfigError, "invalid model identifier"):
                config._validate_choice(model, "high")
        # Other identifiers keep their own syntax and 128-character limit.
        config._validate_choice("a" * 128, "high")
        config._validate_choice("a" * 128 + "[1m]", "high")
        with self.assertRaisesRegex(config.ConfigError, "invalid model identifier"):
            config._validate_choice("a" * 129, "high")
        self.apply("install")
        code, error = self.call("model", "project", "--set", f"analyst.model={prefix}inference-profile/abc:")
        self.assertEqual(code, 2)
        self.assertIn("invalid model identifier", error["error"])

    def save_model_choices(self, values):
        """Save model values that an earlier version accepted, in the state and the installed role files alike."""
        state_path = self.project / ".claude" / "cc-feather" / "state.json"
        state = json.loads(state_path.read_bytes())
        record = state["components"]["delegation"]
        for role, model in values.items():
            path = self.project / ".claude" / "agents" / f"{role}.md"
            old = record["choices"][role]["model"]
            path.write_bytes(path.read_bytes().replace(f"\nmodel: {old}\n".encode(), f"\nmodel: {model}\n".encode(), 1))
            record["choices"][role]["model"] = model
            record["hashes"][role] = config.digest(path.read_bytes())
        state_path.write_bytes(config.canonical(state) + b"\n")

    def test_model_identifiers_never_break_role_frontmatter(self):
        # Claude Code ends the frontmatter at any "---", and a trailing colon is not a plain YAML value.
        for model in ("opus---x", "a---b[1m]", "abc:", "abc:[1m]", "---", "a:---"):
            with self.subTest(model=model), self.assertRaisesRegex(config.ConfigError, "invalid model identifier"):
                config._validate_choice(model, "high")
        for model in ("opus", "sonnet", "claude-opus-4-1", "us.anthropic.claude-v1:0", "opus[1m]", "a--b", "a" * 128,
                      "a" * 127 + "1[1m]"):
            with self.subTest(model=model[:40]):
                config._validate_choice(model, "high")
        self.apply("install")
        for model in ("opus---x", "a---b[1m]", "abc:", "abc:[1m]"):
            with self.subTest(command="model", model=model):
                code, error = self.call("model", "project", "--set", f"analyst.model={model}")
                self.assertEqual(code, 2)
                self.assertIn("invalid model identifier", error["error"])

    def test_saved_model_an_earlier_version_accepted_is_reported_and_replaceable(self):
        self.apply("install")
        self.save_model_choices({"analyst": "abc:", "scout": "a---b"})
        code, checked = self.call("check")
        self.assertEqual(code, 2, checked)
        text = json.dumps(checked)
        self.assertIn("saved model for analyst is no longer accepted", text)
        self.assertIn("saved model for scout is no longer accepted", text)
        self.assertEqual(self.call("session")[0], 2)
        code, error = self.call("update")
        self.assertEqual(code, 2)
        self.assertIn("saved model is no longer accepted", error["error"])
        # Replacing only one leaves the other still refused; replacing both repairs the installation.
        code, error = self.call("model", "project", "--set", "analyst.model=sonnet")
        self.assertEqual(code, 2)
        self.assertIn("scout ('a---b')", error["error"])
        # Operations that write no role file still run: the handoff component and the review mode.
        self.apply("install", "project", "--component", "handoff")
        self.apply("review", "project", "--review-mode", "off")
        self.apply("model", "project", "--set", "analyst.model=sonnet", "--set", "scout.model=haiku")
        self.assertEqual(self.call("check")[0], 0)
        self.assertEqual(self.call("show")[1]["choices"]["scout"]["model"], "haiku")

    def test_saved_model_no_version_accepted_is_still_rejected_on_load(self):
        self.apply("install")
        self.save_model_choices({"analyst": "-abc"})
        code, error = self.call("check")
        self.assertEqual(code, 2)
        self.assertIn("invalid model identifier", error["error"])

    def test_saved_unsafe_model_with_outdated_roles_recovers_by_remove_and_reinstall(self):
        # model refuses until the roles are updated, and update refuses the saved value, so remove and reinstall.
        self.six_role_install(3)
        self.save_model_choices({"analyst": "abc:"})
        code, error = self.call("model", "project", "--set", "analyst.model=sonnet")
        self.assertEqual(code, 2)
        self.assertIn("run setup update first", error["error"])
        code, error = self.call("update")
        self.assertEqual(code, 2)
        self.assertIn("saved model is no longer accepted", error["error"])
        self.apply("remove")
        self.apply("install")
        self.assertEqual(self.call("check")[0], 0)

    def test_reviewer_model_and_session_overrides(self):
        self.apply("install")
        self.apply("model", "project", "--set", "reviewer.effort=medium")
        self.assertEqual(self.call("show")[1]["choices"]["reviewer"], {"model": "opus", "effort": "medium"})
        code, exported = self.call("session", "project", "--set", "reviewer.model=sonnet")
        self.assertEqual(code, 0, exported)
        self.assertEqual(exported["reviewer"]["model"], "sonnet")
        self.assertEqual(exported["reviewer"]["effort"], "medium")
        self.assertEqual(exported["reviewer"]["tools"], ["Read", "Glob", "Grep", "Bash"])

    def test_handoff_policy_updates_before_waiting_during_implementation(self):
        self.apply("install", "project", "--component", "handoff")
        policy = (self.project / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("During implementation, before stopping to wait for the user", policy)

    def test_fresh_install_includes_verifier(self):
        self.apply("install")
        self.assert_all_unprefixed_roles()
        text = (self.project / ".claude" / "agents" / "verifier.md").read_text(encoding="utf-8")
        self.assertIn("name: verifier", text)
        self.assertIn("model: opus", text)
        self.assertIn("effort: high", text)
        self.assertIn("tools: Read, Glob, Grep, Bash", text)
        self.assertNotIn("disallowedTools", text)
        self.assertEqual(self.call("show")[1]["choices"]["verifier"], {"model": "opus", "effort": "high"})

    def assert_update_adds_verifier(self, version):
        self.six_role_install(version)
        shown = self.call("show")[1]
        self.assertEqual(shown["status"], "ok", shown)
        self.assertTrue(shown["role_update_required"])
        self.assertEqual(shown["components"]["delegation"]["issues"], [])
        self.apply("update")
        self.assert_all_unprefixed_roles()
        shown = self.call("show")[1]
        self.assertFalse(shown["role_update_required"])
        self.assertEqual(shown["review_mode"], "auto")
        self.assertEqual(shown["choices"]["analyst"], {"model": "sonnet", "effort": "high"})
        self.assertEqual(shown["choices"]["verifier"], {"model": "opus", "effort": "high"})
        self.assertEqual(shown["choices"]["reviewer"], {"model": "opus", "effort": "high"})
        return shown

    def test_update_adds_verifier_to_six_role_v2_state(self):
        self.assert_update_adds_verifier(2)

    def test_update_adds_verifier_to_six_role_v3_state_and_keeps_handoff(self):
        shown = self.assert_update_adds_verifier(3)
        self.assertTrue(shown["components"]["handoff"]["installed"])
        self.assertIn(config.HANDOFF_BEGIN, (self.project / "CLAUDE.md").read_text(encoding="utf-8"))

    def test_six_role_state_blocks_settings_until_update(self):
        self.six_role_install(3)
        before = {p: p.read_bytes() for p in self.project.rglob("*") if p.is_file()}
        for command in (("model", "project", "--set", "analyst.effort=low"),
                        ("review", "project", "--review-mode", "off"),
                        ("session",)):
            with self.subTest(command=command[0]):
                code, result = self.call(*command)
                self.assertEqual(code, 2, result)
                self.assertIn("run setup update first", result["error"])
        self.assertEqual(before, {p: p.read_bytes() for p in self.project.rglob("*") if p.is_file()})

    def assert_prefixed_roles(self, agents, extra=()):
        names = {config._role_name(role, config.ROLE_PREFIX) for role in config.ROLES}
        self.assertEqual({p.name for p in agents.glob("*.md")}, {f"{name}.md" for name in names} | set(extra))
        self.assertEqual(self.saved_state()["components"]["delegation"]["role_prefix"], config.ROLE_PREFIX)
        scout = (agents / "cc-scout.md").read_text(encoding="utf-8")
        self.assertIn("name: cc-scout", scout)
        self.assertIn("belongs to cc-analyst", scout)
        self.assertIn("name: Explore", (agents / "Explore.md").read_text(encoding="utf-8"))
        self.assertIn("scout = cc-scout", (self.project / "CLAUDE.md").read_text(encoding="utf-8"))

    def test_six_role_update_with_unowned_verifier_moves_to_prefix(self):
        for filename in ("verifier.md", "custom.md"):
            with self.subTest(filename=filename):
                self.project = self.root / f"six-{filename}"
                self.project.mkdir()
                self.six_role_install(3)
                agents = self.project / ".claude" / "agents"
                conflict = agents / filename
                conflict.write_text("---\nname: verifier\n---\nExisting user role\n", encoding="utf-8")
                shown = self.call("show")[1]
                self.assertEqual(shown["components"]["delegation"]["status"], "ok", shown)
                self.assertEqual(shown["pending_role_prefix"], config.ROLE_PREFIX)
                self.apply("update")
                self.assert_prefixed_roles(agents, extra={filename})
                self.assertEqual(self.call("show")[1]["choices"]["analyst"], {"model": "sonnet", "effort": "high"})
                self.apply("remove")
                self.assertEqual([p.name for p in agents.glob("*.md")], [filename])
                self.assertEqual(conflict.read_text(encoding="utf-8"), "---\nname: verifier\n---\nExisting user role\n")

    def test_install_with_name_conflict_uses_prefix(self):
        agents = self.project / ".claude" / "agents"
        agents.mkdir(parents=True)
        user_scout = agents / "scout.md"
        user_scout.write_text("---\nname: scout\n---\nMy scout\n", encoding="utf-8")
        self.apply("install")
        self.assert_prefixed_roles(agents, extra={"scout.md"})
        self.assertEqual(user_scout.read_text(encoding="utf-8"), "---\nname: scout\n---\nMy scout\n")
        self.apply("model", "project", "--set", "scout.effort=medium")
        self.assertIn("effort: medium", (agents / "cc-scout.md").read_text(encoding="utf-8"))
        code, exported = self.call("session")
        self.assertEqual(code, 0, exported)
        self.assertEqual(set(exported), {config._role_name(role, config.ROLE_PREFIX) for role in config.ROLES})
        user_scout.unlink()
        self.apply("update")
        self.assertTrue((agents / "cc-scout.md").exists())
        self.assertFalse((agents / "scout.md").exists())
        self.apply("remove")
        self.assertEqual(list(agents.glob("*.md")), [])

    def test_later_conflict_moves_unprefixed_install_to_prefix(self):
        self.apply("install", "project", "--review-mode", "auto")
        self.apply("model", "project", "--set", "executor.model=sonnet")
        agents = self.project / ".claude" / "agents"
        (agents / "team").mkdir()
        (agents / "team" / "qa.md").write_text("---\nname: verifier\n---\nTeam QA\n", encoding="utf-8")
        self.apply("update")
        self.assert_prefixed_roles(agents)
        shown = self.call("show")[1]
        self.assertEqual(shown["choices"]["executor"], {"model": "sonnet", "effort": "medium"})
        self.assertEqual(shown["review_mode"], "auto")
        self.assertEqual(shown["status"], "ok", shown)

    def test_prefixed_name_conflicts_still_block(self):
        agents = self.project / ".claude" / "agents"
        agents.mkdir(parents=True)
        for name in ("scout.md", "cc-scout.md"):
            (agents / name).write_text(f"---\nname: {Path(name).stem}\n---\nMine\n", encoding="utf-8")
        before = self.files()
        code, result = self.call("install")
        self.assertEqual(code, 2, result)
        self.assertIn("cc-scout.md", result["error"])
        self.assertEqual(before, self.files())
        shown = self.call("check")[1]
        self.assertEqual((shown["status"], shown["pending_role_prefix"]), ("conflict", None))

    def assert_external_explore(self, prefix):
        agents = self.project / ".claude" / "agents"
        record = self.saved_state()["components"]["delegation"]
        self.assertEqual((record["external_roles"], record["role_prefix"]), (["Explore"], prefix))
        self.assertNotIn("Explore", record["choices"])
        self.assertNotIn("Explore", record["hashes"])
        for role in config.ROLES:
            if role != "Explore":
                self.assertTrue((agents / f"{config._role_name(role, prefix)}.md").exists(), role)
        shown = self.call("show")[1]
        self.assertEqual((shown["status"], shown["external_roles"], shown["pending_external_roles"]),
                         ("ok", ["Explore"], None), shown)

    def test_user_explore_with_another_conflict_uses_prefix(self):
        agents = self.project / ".claude" / "agents"
        agents.mkdir(parents=True)
        explore = agents / "Explore.md"
        explore.write_bytes(b"---\nname: Explore\nmodel: haiku\n---\nMine\n")
        (agents / "scout.md").write_text("---\nname: scout\n---\nMine\n", encoding="utf-8")
        self.apply("install")
        self.assert_external_explore(prefix=config.ROLE_PREFIX)
        self.assertEqual(explore.read_bytes(), b"---\nname: Explore\nmodel: haiku\n---\nMine\n")
        policy = (self.project / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("scout = cc-scout", policy)
        self.assertNotIn("Explore = ", policy)

    def test_later_user_explore_replaces_owned_explore_and_returns(self):
        for prefixed in (False, True):
            with self.subTest(prefixed=prefixed):
                self.project = self.root / f"explore-{prefixed}"
                self.project.mkdir()
                agents = self.project / ".claude" / "agents"
                agents.mkdir(parents=True)
                if prefixed:
                    (agents / "scout.md").write_text("---\nname: scout\n---\nMine\n", encoding="utf-8")
                self.apply("install", "project", "--review-mode", "auto")
                self.apply("model", "project", "--set", "Explore.model=opus")
                prefix = config.ROLE_PREFIX if prefixed else ""
                owned_explore = agents / "Explore.md"
                self.assertIn("model: opus", owned_explore.read_text(encoding="utf-8"))
                for variant in ("subdirectory", "replaced"):
                    if variant == "subdirectory":
                        user_file = agents / "team" / "explorer.md"
                        user_file.parent.mkdir()
                        user_file.write_text("---\nname: Explore\n---\nTeam explorer\n", encoding="utf-8")
                    else:
                        user_file = owned_explore
                    shown = self.call("check")[1]
                    if variant == "subdirectory":
                        self.assertEqual((shown["status"], shown["pending_external_roles"]), ("ok", ["Explore"]), shown)
                        self.assertFalse([i for i in shown["issues"] if "duplicate native agent name Explore" in i])
                        self.apply("update")
                        self.assertFalse(owned_explore.exists())
                        self.assert_external_explore(prefix=prefix)
                        user_file.unlink()
                        user_file.parent.rmdir()
                        self.assertEqual(self.call("show")[1]["pending_external_roles"], [])
                        self.apply("update")
                        self.assertIn("name: Explore", owned_explore.read_text(encoding="utf-8"))
                        self.assertEqual(self.saved_state()["components"]["delegation"]["external_roles"], [])
                    else:
                        # The user rewrites the owned file as their own Explore: it is released, never deleted.
                        user_file.write_bytes(b"---\nname: Explore\n---\nMine now\n")
                        shown = self.call("check")[1]
                        self.assertEqual((shown["status"], shown["pending_external_roles"]), ("ok", ["Explore"]), shown)
                        self.apply("update")
                        self.assertEqual(user_file.read_bytes(), b"---\nname: Explore\n---\nMine now\n")
                        self.assert_external_explore(prefix=prefix)
                        user_file.unlink()
                        self.apply("update")
                        self.assertIn("name: Explore", owned_explore.read_text(encoding="utf-8"))
                        self.assertEqual(self.saved_state()["components"]["delegation"]["external_roles"], [])
                self.assertEqual(self.saved_state()["components"]["delegation"]["review_mode"], "auto")

    def test_remove_keeps_a_rewritten_explore_without_update(self):
        self.apply("install")
        agents = self.project / ".claude" / "agents"
        explore = agents / "Explore.md"
        explore.write_bytes(b"---\nname: Explore\n---\nMine now\n")
        self.assertEqual(self.call("check")[1]["status"], "ok")
        self.apply("remove")
        self.assertEqual(explore.read_bytes(), b"---\nname: Explore\n---\nMine now\n")
        self.assertEqual([p.name for p in agents.glob("*.md")], ["Explore.md"])
        self.assertFalse((self.project / ".claude" / "cc-feather" / "state.json").exists())

    def test_external_explore_is_not_configured_exported_or_removed(self):
        agents = self.project / ".claude" / "agents"
        agents.mkdir(parents=True)
        explore = agents / "Explore.md"
        explore.write_text("---\nname: Explore\n---\nMine\n", encoding="utf-8")
        self.apply("install", "project", "--component", "both")
        before = self.files()
        for command in (("model", "project", "--set", "Explore.model=opus"),
                        ("session", "project", "--set", "Explore.effort=high")):
            with self.subTest(command=command[0]):
                code, result = self.call(*command)
                self.assertEqual(code, 2, result)
                self.assertIn("provided by another agent", result["error"])
        self.assertEqual(before, self.files())
        self.apply("model", "project", "--set", "scout.effort=medium")
        code, exported = self.call("session")
        self.assertEqual(code, 0, exported)
        self.assertNotIn("Explore", exported)
        self.assertEqual(len(exported), len(config.ROLES) - 1)
        self.apply("remove", "project", "--component", "both")
        self.assertEqual(explore.read_text(encoding="utf-8"), "---\nname: Explore\n---\nMine\n")
        self.assertEqual([p.name for p in agents.glob("*.md")], ["Explore.md"])

    def test_commands_before_update_point_to_update_when_explore_changes(self):
        self.apply("install")
        agents = self.project / ".claude" / "agents"
        explore = agents / "Explore.md"
        user_file = agents / "team" / "explorer.md"
        user_file.parent.mkdir()
        for setup_change in ("subdirectory", "rewritten"):
            with self.subTest(change=setup_change):
                if setup_change == "subdirectory":
                    user_file.write_text("---\nname: Explore\n---\nTeam\n", encoding="utf-8")
                else:
                    user_file.unlink()
                    original = explore.read_bytes()
                    explore.write_bytes(b"---\nname: Explore\n---\nMine\n")
                before = self.files()
                for command in (("model", "project", "--set", "scout.effort=medium"),
                                ("review", "project", "--review-mode", "auto"), ("session",)):
                    code, result = self.call(*command)
                    self.assertEqual(code, 2, result)
                    self.assertIn("run setup update first", result["error"])
                self.assertEqual(before, self.files())
                if setup_change == "rewritten":
                    explore.write_bytes(original)

    def test_session_uses_a_pending_prefix_and_never_a_user_agent_name(self):
        agents = self.project / ".claude" / "agents"
        agents.mkdir(parents=True)
        (agents / "scout.md").write_text("---\nname: scout\n---\nMine\n", encoding="utf-8")
        code, exported = self.call("session")
        self.assertEqual(code, 0, exported)
        self.assertEqual(set(exported), {config._role_name(role, config.ROLE_PREFIX) for role in config.ROLES})
        self.assertIn("cc-analyst", exported["cc-scout"]["description"])
        (agents / "scout.md").unlink()
        self.apply("install")
        (agents / "team").mkdir()
        (agents / "team" / "s.md").write_text("---\nname: scout\n---\nTeam\n", encoding="utf-8")
        code, result = self.call("session")
        self.assertEqual(code, 2, result)
        self.assertIn("run setup update first", result["error"])
        self.apply("update")
        code, exported = self.call("session")
        self.assertEqual(code, 0, exported)
        self.assertIn("cc-scout", exported)

    def test_user_explore_renamed_in_place_points_to_a_user_decision(self):
        agents = self.project / ".claude" / "agents"
        agents.mkdir(parents=True)
        explore = agents / "Explore.md"
        explore.write_text("---\nname: Explore\n---\nMine\n", encoding="utf-8")
        self.apply("install")
        explore.write_text("---\nname: notes\n---\nNow notes\n", encoding="utf-8")
        before = self.files()
        for command in (("model", "project", "--set", "scout.model=haiku"),
                        ("review", "project", "--review-mode", "auto"), ("update",)):
            with self.subTest(command=command[0]):
                code, result = self.call(*command)
                self.assertEqual(code, 2, result)
                self.assertIn("unowned role file already exists", result["error"])
                self.assertIn("user decision required", result["error"])
        self.assertEqual(before, self.files())

    def test_session_without_installation_skips_a_user_explore(self):
        agents = self.project / ".claude" / "agents"
        agents.mkdir(parents=True)
        (agents / "Explore.md").write_text("---\nname: Explore\n---\nMine\n", encoding="utf-8")
        code, exported = self.call("session")
        self.assertEqual(code, 0, exported)
        self.assertNotIn("Explore", exported)
        code, result = self.call("session", "project", "--set", "Explore.model=opus")
        self.assertEqual(code, 2, result)
        self.assertIn("provided by another agent", result["error"])

    def test_old_states_with_a_user_explore_update(self):
        for kind in ("legacy", "six-role"):
            with self.subTest(kind=kind):
                self.project = self.root / f"old-{kind}"
                self.project.mkdir()
                if kind == "legacy":
                    self.legacy_install()
                else:
                    self.six_role_install(3)
                agents = self.project / ".claude" / "agents"
                user_file = agents / "mine" / "explore.md"
                user_file.parent.mkdir()
                user_file.write_text("---\nname: Explore\n---\nMine\n", encoding="utf-8")
                self.apply("update")
                self.assertFalse((agents / "Explore.md").exists())
                self.assert_external_explore(prefix="")
                self.assertEqual(user_file.read_text(encoding="utf-8"), "---\nname: Explore\n---\nMine\n")
                self.assertEqual(self.call("show")[1]["choices"]["analyst"], {"model": "sonnet", "effort": "high"})

    def test_check_reports_a_conflict_the_prefix_resolves_as_pending(self):
        agents = self.project / ".claude" / "agents"
        agents.mkdir(parents=True)
        (agents / "scout.md").write_text("---\nname: scout\n---\nMine\n", encoding="utf-8")
        code, shown = self.call("check")
        self.assertEqual(code, 0, shown)
        self.assertEqual((shown["status"], shown["pending_role_prefix"]), ("ok", config.ROLE_PREFIX))
        (agents / "scout.md").unlink()
        self.apply("install")
        self.assertIsNone(self.call("check")[1]["pending_role_prefix"])
        (agents / "custom.md").write_text("---\nname: analyst\n---\nMine\n", encoding="utf-8")
        code, shown = self.call("check")
        self.assertEqual((code, shown["status"], shown["pending_role_prefix"]), (0, "ok", config.ROLE_PREFIX))
        self.apply("update")
        self.assertIsNone(self.call("check")[1]["pending_role_prefix"])

    def test_created_claude_md_emptied_by_the_user_is_removed(self):
        (self.project / "AGENTS.md").write_text("Team rules\n", encoding="utf-8")
        self.apply("install", "project", "--guidance", "claude")
        claude_md = self.project / "CLAUDE.md"
        claude_md.write_bytes(claude_md.read_bytes().replace(b"@AGENTS.md\n", b"", 1))
        self.apply("remove")
        self.assertFalse(claude_md.exists())

    def test_created_imports_only_with_a_created_claude_md(self):
        (self.project / "AGENTS.md").write_text("Team rules\n", encoding="utf-8")
        self.apply("install", "project", "--guidance", "agents")
        state_path = self.project / ".claude" / "cc-feather" / "state.json"
        state = self.saved_state()
        state["created_imports"] = ["@AGENTS.md"]
        state_path.write_bytes(config.canonical(state) + b"\n")
        before = self.files()
        code, result = self.call("remove")
        self.assertEqual(code, 2, result)
        self.assertIn("invalid instruction file state", result["error"])
        self.assertEqual(before, self.files())

    def test_unprefixed_rendering_matches_templates(self):
        self.apply("install")
        defaults = config._defaults()
        for role in config.ROLES:
            # Keep checkout newlines; rendering preserves the template bytes.
            template = (config.ROOT / "templates" / "agents" / f"{role}.md").read_bytes().decode("utf-8")
            expected = re.sub(r"\{\{name:([A-Za-z-]+)\}\}", r"\1", template)
            expected = expected.replace("{{model}}", defaults[role]["model"]).replace("{{effort}}", defaults[role]["effort"])
            self.assertEqual((self.project / ".claude" / "agents" / f"{role}.md").read_bytes(), expected.encode("utf-8"))
        guidance = (self.project / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertNotIn("Native role names", guidance)
        self.assertNotIn("{{", guidance)
        self.assertEqual(self.saved_state()["components"]["delegation"]["role_prefix"], "")

    def test_verifier_model_and_session_overrides(self):
        self.apply("install")
        self.apply("model", "project", "--set", "verifier.effort=medium")
        self.assertEqual(self.call("show")[1]["choices"]["verifier"], {"model": "opus", "effort": "medium"})
        self.assertIn("effort: medium", (self.project / ".claude" / "agents" / "verifier.md").read_text(encoding="utf-8"))
        code, exported = self.call("session", "project", "--set", "verifier.model=sonnet")
        self.assertEqual(code, 0, exported)
        self.assertEqual(exported["verifier"]["model"], "sonnet")
        self.assertEqual(exported["verifier"]["effort"], "medium")
        self.assertEqual(exported["verifier"]["tools"], ["Read", "Glob", "Grep", "Bash"])

    # 0.18.0 C3 (docs/specs/security-critical-routing.md): adversary is a managed role like the others.
    ADVERSARY_TOOLS = ["Read", "Glob", "Grep", "Bash"]

    def assert_adversary_file(self, path, prefix, model="opus", effort="high"):
        """The installed adversary has exactly name, description, model, effort and the four-tool line.

        The exact key list also rules out every field that could widen what the role can reach or load,
        such as permissionMode, hooks, mcpServers, skills, memory, background, isolation or disallowedTools.
        """
        text = path.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"), path)
        header = text[4:].split("\n---\n", 1)[0].split("\n")
        keys = [line.split(":", 1)[0] for line in header]
        self.assertEqual(keys, ["name", "description", "model", "effort", "tools"], path)
        self.assertEqual(header[0], f"name: {prefix}adversary")
        self.assertEqual(header[2:], [f"model: {model}", f"effort: {effort}", "tools: Read, Glob, Grep, Bash"])
        self.assertIn(f"Code review belongs to {prefix}reviewer; claim verification to {prefix}verifier.", header[1])
        self.assertNotIn("{{", text)

    def drop_role(self, scope, role):
        """Simulate an installation saved before a role existed, such as a 0.17.0 one without adversary."""
        base = self.project / ".claude" if scope == "project" else self.home
        state_path = base / "cc-feather" / "state.json"
        state = json.loads(state_path.read_bytes())
        record = state["components"]["delegation"]
        del record["choices"][role], record["hashes"][role]
        (base / "agents" / f"{record['role_prefix']}{role}.md").unlink()
        state_path.write_bytes(config.canonical(state) + b"\n")
        return base

    def test_adversary_is_an_added_managed_role_with_opus_high_defaults(self):
        self.assertIn("adversary", config.ROLES)
        self.assertIn("adversary", config.ADDED_ROLES)
        self.assertNotIn("adversary", config.EXTERNAL_ROLES)
        self.assertEqual(config._defaults()["adversary"], {"name": "adversary", "model": "opus", "effort": "high"})

    def test_adversary_installs_with_defaults_in_both_scopes_with_and_without_prefix(self):
        for scope in ("project", "user"):
            for prefixed in (False, True):
                with self.subTest(scope=scope, prefixed=prefixed):
                    self.use_fresh_roots(f"adversary-{scope}-{prefixed}")
                    agents = (self.project / ".claude" if scope == "project" else self.home) / "agents"
                    if prefixed:
                        agents.mkdir(parents=True)
                        (agents / "custom.md").write_text("---\nname: scout\n---\nThe user's own scout\n", encoding="utf-8")
                    self.apply("install", scope)
                    prefix = config.ROLE_PREFIX if prefixed else ""
                    path = agents / f"{prefix}adversary.md"
                    self.assert_adversary_file(path, prefix)
                    code, shown = self.call("show", scope)
                    self.assertEqual(code, 0, shown)
                    self.assertFalse(shown["role_update_required"])
                    self.assertEqual(shown["choices"]["adversary"], {"model": "opus", "effort": "high"})
                    self.assertEqual(shown["paths"]["agents"]["adversary"], str(path))
                    code, exported = self.call("session", scope)
                    self.assertEqual(code, 0, exported)
                    self.assertEqual(exported[f"{prefix}adversary"]["tools"], self.ADVERSARY_TOOLS)
                    self.assertEqual((exported[f"{prefix}adversary"]["model"], exported[f"{prefix}adversary"]["effort"]),
                                     ("opus", "high"))

    def test_installation_without_adversary_reports_it_and_refuses_settings_until_update(self):
        for scope in ("project", "user"):
            with self.subTest(scope=scope):
                self.use_fresh_roots(f"no-adversary-{scope}")
                self.apply("install", scope, "--review-mode", "auto")
                self.apply("model", scope, "--set", "analyst.model=sonnet", "--set", "reviewer.effort=medium")
                base = self.drop_role(scope, "adversary")
                for command in ("check", "show"):
                    code, shown = self.call(command, scope)
                    self.assertEqual(code, 0, shown)
                    self.assertEqual((shown["status"], shown["components"]["delegation"]["status"]), ("ok", "ok"), shown)
                    self.assertEqual(shown["issues"], [])
                    self.assertTrue(shown["role_update_required"])
                    self.assertNotIn("adversary", shown["choices"])
                before = self.files(base)
                for command, extra in (("model", ("--set", "adversary.effort=low")), ("model", ("--set", "scout.effort=medium")),
                                       ("review", ("--review-mode", "off")), ("session", ())):
                    with self.subTest(scope=scope, command=command, extra=extra):
                        code, error = self.call(command, scope, *extra)
                        self.assertEqual(code, 2, error)
                        self.assertIn("run setup update first", error["error"])
                self.assertEqual(before, self.files(base))
                self.apply("update", scope)
                shown = self.call("show", scope)[1]
                self.assertEqual(shown["status"], "ok", shown)
                self.assertFalse(shown["role_update_required"])
                self.assertEqual(shown["review_mode"], "auto")
                self.assertEqual(shown["choices"]["adversary"], {"model": "opus", "effort": "high"})
                self.assertEqual(shown["choices"]["analyst"], {"model": "sonnet", "effort": "high"})
                self.assertEqual(shown["choices"]["reviewer"], {"model": "opus", "effort": "medium"})
                self.assert_adversary_file(base / "agents" / "adversary.md", "")
                self.apply("model", scope, "--set", "adversary.effort=xhigh")
                self.assert_adversary_file(base / "agents" / "adversary.md", "", effort="xhigh")

    def test_adversary_model_and_session_export(self):
        # Without an installation, session exports what install would set up.
        code, exported = self.call("session")
        self.assertEqual(code, 0, exported)
        self.assertEqual(exported["adversary"]["tools"], self.ADVERSARY_TOOLS)
        self.assertEqual((exported["adversary"]["model"], exported["adversary"]["effort"]), ("opus", "high"))
        self.apply("install")
        self.apply("model", "project", "--set", "adversary.effort=xhigh")
        self.assertEqual(self.call("show")[1]["choices"]["adversary"], {"model": "opus", "effort": "xhigh"})
        self.assert_adversary_file(self.project / ".claude" / "agents" / "adversary.md", "", effort="xhigh")
        code, exported = self.call("session", "project", "--set", "adversary.model=sonnet")
        self.assertEqual(code, 0, exported)
        agent = exported["adversary"]
        self.assertEqual(set(agent), {"description", "prompt", "model", "effort", "tools"})
        self.assertEqual((agent["model"], agent["effort"]), ("sonnet", "xhigh"))
        self.assertEqual(agent["tools"], self.ADVERSARY_TOOLS)
        self.assertIn("never fix what you find", agent["prompt"])

    def test_stale_adversary_template_is_reported_until_setup_update(self):
        self.apply("install")
        agents = self.project / ".claude" / "agents"
        fixture = self.root / "package"
        shutil.copytree(config.ROOT / "templates", fixture / "templates")
        template = fixture / "templates" / "agents" / "adversary.md"
        template.write_bytes(template.read_bytes() + b"\nUPGRADED ADVERSARY\n")
        with mock.patch.object(config, "ROOT", fixture):
            code, shown = self.call("check")
            self.assertEqual(code, 0, shown)
            self.assertEqual(shown["components"]["delegation"]["status"], "ok")
            self.assertTrue(shown["role_update_required"])
            self.assertEqual(self.stale_warnings(shown), [self.stale_warning(agents, "", "adversary")])
            for command, extra in (("model", ("--set", "adversary.effort=low")), ("session", ())):
                code, error = self.call(command, "project", *extra)
                self.assertEqual(code, 2, error)
                self.assertIn("run setup update first", error["error"])
            self.apply("update")
            self.assertIn("UPGRADED ADVERSARY", (agents / "adversary.md").read_text(encoding="utf-8"))
            code, shown = self.call("check")
            self.assertEqual(code, 0, shown)
            self.assertFalse(shown["role_update_required"])
            self.assertEqual(self.stale_warnings(shown), [])

    def test_user_agent_named_adversary_makes_install_use_prefix(self):
        user_role = "---\nname: adversary\n---\nMy own adversary\n"
        for filename in ("adversary.md", "team/red.md"):
            with self.subTest(filename=filename):
                self.use_fresh_roots(f"user-adversary-{filename.replace('/', '-')}")
                agents = self.project / ".claude" / "agents"
                path = agents / filename
                path.parent.mkdir(parents=True)
                path.write_text(user_role, encoding="utf-8")
                shown = self.call("check")[1]
                self.assertEqual(shown["pending_role_prefix"], config.ROLE_PREFIX, shown)
                self.apply("install")
                self.assert_prefixed_roles(agents, extra={"adversary.md"} if filename == "adversary.md" else set())
                self.assert_adversary_file(agents / "cc-adversary.md", config.ROLE_PREFIX)
                self.assertIn("adversary = cc-adversary", (self.project / "CLAUDE.md").read_text(encoding="utf-8"))
                self.assertEqual(path.read_text(encoding="utf-8"), user_role)
                code, exported = self.call("session")
                self.assertEqual(code, 0, exported)
                self.assertNotIn("adversary", exported)
                self.assertEqual(exported["cc-adversary"]["tools"], self.ADVERSARY_TOOLS)

    def test_update_without_adversary_and_user_agent_named_adversary_moves_to_prefix(self):
        self.apply("install", "project", "--review-mode", "auto")
        self.apply("model", "project", "--set", "executor.model=sonnet")
        self.drop_role("project", "adversary")
        agents = self.project / ".claude" / "agents"
        conflict = agents / "adversary.md"
        user_role = "---\nname: adversary\n---\nMy own adversary\n"
        conflict.write_text(user_role, encoding="utf-8")
        shown = self.call("show")[1]
        self.assertEqual(shown["components"]["delegation"]["status"], "ok", shown)
        self.assertEqual(shown["pending_role_prefix"], config.ROLE_PREFIX)
        self.assertTrue(shown["role_update_required"])
        self.apply("update")
        self.assert_prefixed_roles(agents, extra={"adversary.md"})
        self.assert_adversary_file(agents / "cc-adversary.md", config.ROLE_PREFIX)
        self.assertEqual(conflict.read_text(encoding="utf-8"), user_role)
        shown = self.call("show")[1]
        self.assertFalse(shown["role_update_required"])
        self.assertEqual(shown["review_mode"], "auto")
        self.assertEqual(shown["choices"]["executor"], {"model": "sonnet", "effort": "medium"})
        self.assertEqual(shown["choices"]["adversary"], {"model": "opus", "effort": "high"})

    def test_update_adds_prefixed_adversary_to_prefixed_installation_without_it(self):
        # 0.19.0 C7 item 2: a 0.17.0 installation whose roles already use the prefix gains cc-adversary.
        for scope in ("project", "user"):
            with self.subTest(scope=scope):
                self.use_fresh_roots(f"prefixed-no-adversary-{scope}")
                agents = (self.project / ".claude" if scope == "project" else self.home) / "agents"
                agents.mkdir(parents=True)
                user_role = "---\nname: scout\n---\nThe user's own scout\n"
                (agents / "custom.md").write_text(user_role, encoding="utf-8")
                self.apply("install", scope, "--review-mode", "auto")
                self.apply("model", scope, "--set", "executor.model=sonnet")
                self.drop_role(scope, "adversary")
                self.assertFalse((agents / "cc-adversary.md").exists())
                code, shown = self.call("check", scope)
                self.assertEqual(code, 0, shown)
                self.assertTrue(shown["role_update_required"])
                self.assertNotIn("adversary", shown["choices"])
                self.apply("update", scope)
                self.assert_adversary_file(agents / "cc-adversary.md", config.ROLE_PREFIX)
                self.assertFalse((agents / "adversary.md").exists())
                self.assertEqual((agents / "custom.md").read_text(encoding="utf-8"), user_role)
                code, shown = self.call("check", scope)
                self.assertEqual(code, 0, shown)
                self.assertEqual(shown["status"], "ok", shown)
                self.assertFalse(shown["role_update_required"])
                self.assertEqual(self.stale_warnings(shown), [])
                self.assertEqual(shown["review_mode"], "auto")
                self.assertEqual(shown["choices"]["executor"], {"model": "sonnet", "effort": "medium"})
                self.assertEqual(shown["choices"]["adversary"], {"model": "opus", "effort": "high"})
                self.assertEqual(shown["paths"]["agents"]["adversary"], str(agents / "cc-adversary.md"))
                code, exported = self.call("session", scope)
                self.assertEqual(code, 0, exported)
                self.assertNotIn("adversary", exported)
                self.assertEqual(exported["cc-adversary"]["tools"], self.ADVERSARY_TOOLS)

    def files(self, root=None):
        root = root or self.root
        return {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}

    def saved_state(self):
        return json.loads((self.project / ".claude" / "cc-feather" / "state.json").read_bytes())

    def assert_choice_required(self, *extra):
        before = self.files()
        code, result = self.call("install", "project", *extra)
        self.assertEqual(code, 2, result)
        self.assertIn("guidance target choice required", result["error"])
        self.assertEqual(before, self.files())

    def test_agents_only_project_requires_a_choice(self):
        (self.project / "AGENTS.md").write_text("Team rules\n", encoding="utf-8")
        self.assert_choice_required()
        self.assert_choice_required("--component", "handoff")
        self.assertTrue(self.call("show")[1]["guidance_choice_required"])

    def test_guidance_claude_creates_importing_claude_md_and_removes_it(self):
        agents_md = self.project / "AGENTS.md"
        agents_md.write_text("Team rules\n", encoding="utf-8")
        self.apply("install", "project", "--component", "both", "--guidance", "claude")
        claude_md = self.project / "CLAUDE.md"
        self.assertTrue(claude_md.read_text(encoding="utf-8").startswith("@AGENTS.md\n\n" + config.HANDOFF_BEGIN))
        self.assertEqual(agents_md.read_text(encoding="utf-8"), "Team rules\n")
        state = self.saved_state()
        self.assertEqual((state["version"], state["guidance"], state["created_imports"]), (4, "CLAUDE.md", ["@AGENTS.md"]))
        self.assertEqual(self.call("update", "project", "--guidance", "claude")[0], 2)
        self.apply("update", "project", "--component", "both")
        self.apply("remove", "project", "--component", "both")
        self.assertFalse(claude_md.exists())
        self.assertEqual(agents_md.read_text(encoding="utf-8"), "Team rules\n")

    def test_created_claude_md_with_user_text_is_kept_on_remove(self):
        (self.project / "AGENTS.md").write_text("Team rules\n", encoding="utf-8")
        self.apply("install", "project", "--guidance", "claude")
        claude_md = self.project / "CLAUDE.md"
        claude_md.write_bytes(claude_md.read_bytes() + b"\nUse pnpm.\n")
        self.apply("remove")
        text = claude_md.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("@AGENTS.md"))
        self.assertIn("Use pnpm.", text)

    def test_guidance_agents_writes_into_agents_md(self):
        agents_md = self.project / "AGENTS.md"
        agents_md.write_text("Team rules\n", encoding="utf-8")
        self.apply("install", "project", "--component", "both", "--guidance", "agents")
        self.assertFalse((self.project / "CLAUDE.md").exists())
        text = agents_md.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("Team rules\n"))
        self.assertIn(config.BEGIN, text)
        self.assertIn(config.HANDOFF_BEGIN, text)
        self.assertEqual(self.saved_state()["guidance"], "AGENTS.md")
        self.assertEqual(self.call("show")[1]["paths"]["guidance"], str(agents_md))
        self.apply("model", "project", "--set", "scout.effort=medium")
        self.apply("remove", "project", "--component", "both")
        self.assertEqual(agents_md.read_text(encoding="utf-8"), "Team rules\n")

    def test_dot_claude_agents_md_and_both_agents_files(self):
        nested = self.project / ".claude" / "AGENTS.md"
        nested.parent.mkdir()
        nested.write_text("Nested rules\n", encoding="utf-8")
        self.assert_choice_required()
        self.apply("install", "project", "--guidance", "agents")
        self.assertIn(config.BEGIN, nested.read_text(encoding="utf-8"))
        self.assertEqual(self.saved_state()["guidance"], ".claude/AGENTS.md")
        self.apply("remove")
        self.assertEqual(nested.read_text(encoding="utf-8"), "Nested rules\n")
        (self.project / "AGENTS.md").write_text("Team rules\n", encoding="utf-8")
        self.apply("install", "project", "--guidance", "claude")
        self.assertEqual(self.saved_state()["created_imports"], ["@AGENTS.md", "@.claude/AGENTS.md"])
        self.assertTrue((self.project / "CLAUDE.md").read_text(encoding="utf-8").startswith("@AGENTS.md\n@.claude/AGENTS.md\n\n"))

    def test_ancestor_agents_md_needs_an_importing_claude_md(self):
        (self.root / "AGENTS.md").write_text("Monorepo rules\n", encoding="utf-8")
        self.assert_choice_required()
        code, result = self.call("install", "project", "--guidance", "agents")
        self.assertEqual(code, 2, result)
        self.assertIn("only ancestor AGENTS.md", result["error"])
        self.apply("install", "project", "--guidance", "claude")
        self.assertEqual(self.saved_state()["created_imports"], ["@../AGENTS.md"])

    def test_guidance_choice_offers_agents_only_with_a_project_agents_file(self):
        (self.root / "AGENTS.md").write_text("Monorepo rules\n", encoding="utf-8")
        for own, offered in ((False, False), (True, True)):
            with self.subTest(own=own):
                if own:
                    (self.project / "AGENTS.md").write_text("Team rules\n", encoding="utf-8")
                before = self.files()
                code, result = self.call("install")
                self.assertEqual(code, 2, result)
                self.assertIn("guidance target choice required", result["error"])
                self.assertIn("--guidance claude", result["error"])
                self.assertEqual("--guidance agents" in result["error"], offered, result["error"])
                self.assertEqual(before, self.files())

    def test_user_instruction_file_in_an_ancestor_does_not_count(self):
        fake_home = self.root / "home"
        self.project = fake_home / "proj"
        self.project.mkdir(parents=True)
        user_file = fake_home / ".claude" / "CLAUDE.md"
        user_file.parent.mkdir()
        user_file.write_text("Personal rules\n", encoding="utf-8")
        (self.project / "AGENTS.md").write_text("Team rules\n", encoding="utf-8")
        for claude_home in (self.home, fake_home / ".claude"):
            with self.subTest(claude_home=claude_home), mock.patch("pathlib.Path.home", return_value=fake_home):
                self.home = claude_home
                self.assert_choice_required()
        with mock.patch("pathlib.Path.home", return_value=fake_home):
            self.apply("install", "project", "--guidance", "agents")
            warnings = self.call("show")[1]["warnings"]
        self.assertFalse([w for w in warnings if "skips AGENTS.md" in w], warnings)
        self.assertEqual(user_file.read_text(encoding="utf-8"), "Personal rules\n")

    def test_existing_claude_files_take_precedence_over_agents_md(self):
        (self.project / "AGENTS.md").write_text("Team rules\n", encoding="utf-8")
        dot_claude = self.project / ".claude" / "CLAUDE.md"
        dot_claude.parent.mkdir()
        dot_claude.write_text("Project rules\n", encoding="utf-8")
        self.apply("install")
        self.assertIn(config.BEGIN, dot_claude.read_text(encoding="utf-8"))
        self.assertFalse((self.project / "CLAUDE.md").exists())
        self.apply("remove")
        dot_claude.unlink()
        for counting in (self.project / "CLAUDE.local.md", self.root / "CLAUDE.md"):
            with self.subTest(counting=counting.name):
                counting.write_text("Local rules\n", encoding="utf-8")
                self.apply("install")
                text = (self.project / "CLAUDE.md").read_text(encoding="utf-8")
                self.assertTrue(text.startswith(config.BEGIN))
                self.assertEqual(self.saved_state()["created_imports"], [])
                self.apply("remove")
                self.assertFalse((self.project / "CLAUDE.md").exists())
                counting.unlink()

    def test_v3_state_migrates_to_recorded_claude_md(self):
        self.apply("install", "project", "--component", "both")
        state_path = self.project / ".claude" / "cc-feather" / "state.json"
        state = self.saved_state()
        components = {**state["components"], "delegation": {key: value for key, value in state["components"]["delegation"].items() if key not in {"role_prefix", "external_roles"}}}
        v3 = {"version": 3, "scope": "project", "components": components}
        state_path.write_bytes(config.canonical(v3) + b"\n")
        guidance = (self.project / "CLAUDE.md").read_bytes()
        (self.project / "AGENTS.md").write_text("Team rules\n", encoding="utf-8")
        shown = self.call("show")[1]
        self.assertEqual(shown["status"], "ok", shown)
        self.assertFalse(shown["guidance_choice_required"])
        self.apply("update", "project", "--component", "both")
        self.assertEqual((self.project / "CLAUDE.md").read_bytes(), guidance)
        state = self.saved_state()
        self.assertEqual((state["version"], state["guidance"], state["created_imports"]), (4, "CLAUDE.md", []))

    def test_agents_md_guidance_warnings(self):
        (self.project / "AGENTS.md").write_text("Team rules\n", encoding="utf-8")
        self.apply("install", "project", "--guidance", "agents")
        self.assertEqual(self.call("show")[1]["warnings"], [])
        (self.home / "settings.json").write_text(json.dumps({"pluginConfigs": {"agents-md@builtin": {
            "options": {"instructionFiles": "claude-md"}}}}), encoding="utf-8")
        self.assertTrue([w for w in self.call("show")[1]["warnings"] if "set to claude-md" in w])
        (self.home / "settings.json").unlink()
        (self.project / "CLAUDE.local.md").write_text("Local rules\n", encoding="utf-8")
        self.assertTrue([w for w in self.call("show")[1]["warnings"] if "skips AGENTS.md" in w])

    def test_user_scope_and_guidance_misuse(self):
        (self.project / "AGENTS.md").write_text("Team rules\n", encoding="utf-8")
        self.apply("install", "user")
        self.assertIn(config.BEGIN, (self.home / "CLAUDE.md").read_text(encoding="utf-8"))
        self.assertFalse((self.project / "CLAUDE.md").exists())
        self.assertEqual(self.call("update", "user", "--guidance", "claude")[0], 2)
        (self.project / "AGENTS.md").unlink()
        for command in (("install", "project", "--guidance", "claude"), ("check", "project", "--guidance", "agents")):
            with self.subTest(command=command[0]):
                code, result = self.call(*command)
                self.assertEqual(code, 2, result)

    def legacy_install(self):
        self.apply("install", "project", "--review-mode", "auto")
        self.apply("model", "project", "--set", "analyst.model=sonnet")
        state_path = self.project / ".claude" / "cc-feather" / "state.json"
        state = json.loads(state_path.read_bytes())
        state = {"version": 1, "scope": "project", **{
            key: value for key, value in state["components"]["delegation"].items()
            if key not in {"legacy_names", "role_prefix", "external_roles"}
        }}
        guidance = self.project / "CLAUDE.md"
        body = guidance.read_text(encoding="utf-8")
        reminder = ("\n\n## Handoff and setup lifecycle\n\n"
                    "When asked to save, list, read or resume handoff work, use the available "
                    "cc-feather:handoff skill and preserve its records/history rules. "
                    "Maintain an already active handoff at useful milestones.\n")
        body = body.replace(config.END, reminder + config.END)
        guidance.write_bytes(body.encode("utf-8"))
        state["block_hash"] = config.digest(config._block_parts(body)[1].encode("utf-8"))
        # Legacy installations predate the added roles.
        self.drop_added_roles(state)
        for role in state["choices"]:
            if role == "Explore":
                continue
            path = self.project / ".claude" / "agents" / f"{role}.md"
            data = path.read_bytes().replace(f"name: {role}".encode(), f"name: feather-{role}".encode())
            old = path.with_name(f"feather-{role}.md")
            path.rename(old)
            old.write_bytes(data)
            state["hashes"][role] = config.digest(data)
        state_path.write_bytes(config.canonical(state) + b"\n")

    def test_legacy_update_migrates_names_preserves_choices_and_removes_owned_files(self):
        self.legacy_install()
        code, shown = self.call("show")
        self.assertEqual(code, 0, shown)
        self.assertTrue(shown["migration_required"])
        self.assertEqual(self.call("session")[0], 2)
        self.assertEqual(self.call("review", "project", "--review-mode", "off")[0], 2)
        self.apply("update")
        _, shown = self.call("show")
        self.assertFalse(shown["migration_required"])
        self.assertEqual(shown["review_mode"], "auto")
        self.assertEqual(shown["choices"]["analyst"], {"model": "sonnet", "effort": "high"})
        self.assertEqual(shown["choices"]["verifier"], {"model": "opus", "effort": "high"})
        agents = self.project / ".claude" / "agents"
        self.assert_all_unprefixed_roles()
        self.assertEqual(set(self.call("session")[1]), set(config.ROLES))
        self.apply("remove")
        self.assertEqual(list(agents.glob("*.md")), [])

    def test_legacy_migration_drift_leaves_files_untouched(self):
        self.legacy_install()
        agents = self.project / ".claude" / "agents"
        old = agents / "feather-analyst.md"
        old.write_bytes(old.read_bytes() + b"User customization\n")
        before = self.files()
        self.assertEqual(self.call("update")[0], 2)
        self.assertEqual(before, self.files())

    def test_legacy_migration_with_name_conflict_moves_to_prefix(self):
        for filename in ("analyst.md", "custom.md"):
            with self.subTest(filename=filename):
                self.project = self.root / f"legacy-{filename}"
                self.project.mkdir()
                self.legacy_install()
                agents = self.project / ".claude" / "agents"
                conflict = agents / filename
                conflict.write_text("---\nname: analyst\n---\nExisting user role\n", encoding="utf-8")
                self.apply("update")
                self.assert_prefixed_roles(agents, extra={filename})
                self.assertEqual(self.call("show")[1]["choices"]["analyst"], {"model": "sonnet", "effort": "high"})

    def test_legacy_migration_failure_rolls_back_and_legacy_remove_is_supported(self):
        self.legacy_install()
        agents = self.project / ".claude" / "agents"
        legacy_scout = agents / "feather-scout.md"
        if os.name == "posix":
            legacy_scout.chmod(0o640)
        before = {p: p.read_bytes() for p in agents.glob("*.md")}
        _, preview = self.call("update")
        real_replace = config._replace

        def fail_old_removal(path, data):
            if path.name == "feather-analyst.md" and data is None:
                raise OSError("injected migration failure")
            return real_replace(path, data)

        with mock.patch.object(config, "_replace", side_effect=fail_old_removal):
            code, result = self.call("update", "project", "--apply", "--expected-plan", preview["plan_id"])
        self.assertEqual(code, 2, result)
        self.assertEqual(before, {p: p.read_bytes() for p in agents.glob("*.md")})
        self.assertTrue(self.call("show")[1]["migration_required"])
        if os.name == "posix":
            self.assertEqual(stat.S_IMODE(legacy_scout.stat().st_mode), 0o640)
        self.apply("remove")
        self.assertEqual(list(agents.glob("*.md")), [])

    def test_session_is_read_only_and_uses_requested_overrides(self):
        code, agents = self.call("session", "project", "--set", "Explore.model=opus",
                                 "--set", "analyst.effort=medium")
        self.assertEqual(code, 0, agents)
        self.assertEqual(set(agents), set(config.ROLES))
        self.assertEqual(agents["Explore"]["model"], "opus")
        self.assertEqual(agents["Explore"]["effort"], "low")
        self.assertEqual(agents["analyst"]["effort"], "medium")
        self.assertIn("tools", agents["Explore"])
        self.assertIn("disallowedTools", agents["executor"])
        self.assertFalse((self.project / ".claude").exists())
        self.assertFalse((self.project / "CLAUDE.md").exists())

    def test_custom_file_declaring_explore_is_used_instead_of_ours(self):
        custom = self.project / ".claude" / "agents" / "nested" / "custom.md"
        custom.parent.mkdir(parents=True)
        custom.write_text("---\nname: 'Explore'\n---\nMine", encoding="utf-8")
        code, shown = self.call("check")
        self.assertEqual(code, 0, shown)
        self.assertEqual((shown["status"], shown["pending_external_roles"]), ("ok", ["Explore"]))
        self.assertTrue([w for w in shown["warnings"] if "Explore is provided by another agent" in w and "custom.md" in w])
        self.apply("install")
        self.assert_external_explore(prefix="")
        self.assertEqual(custom.read_text(encoding="utf-8"), "---\nname: 'Explore'\n---\nMine")

    def test_subprocess_json_is_utf8_with_cp950_console(self):
        project = self.root / "中文 project"
        project.mkdir()
        environment = dict(os.environ, PYTHONIOENCODING="cp950", PYTHONUTF8="0")
        result = subprocess.run([sys.executable, "-B", str(SCRIPT), "install", "--project", str(project),
                                 "--scope", "project", "--claude-home", str(self.home)],
                                cwd=SCRIPT.parent.parent, env=environment, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, check=False)
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", errors="replace"))
        preview = json.loads(result.stdout.decode("utf-8"))
        self.assertEqual(preview["status"], "preview")
        self.assertIn("中文 project", result.stdout.decode("utf-8"))
        self.assertFalse((project / ".claude").exists())

    def test_bom_and_comment_declared_explore_is_external(self):
        custom = self.project / ".claude" / "agents" / "other.md"
        custom.parent.mkdir(parents=True)
        custom.write_text("\ufeff---\nname: Explore # native name\n---\nMine", encoding="utf-8")
        code, result = self.call("check")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["pending_external_roles"], ["Explore"])
        custom.write_text("---\nname: [Explore]\n---\nMine", encoding="utf-8")
        code, error = self.call("install")
        self.assertEqual(code, 2)
        self.assertIn("cannot inspect agent name syntax", error["error"])

    def test_show_uninstalled_reports_conflicts_and_owner_paths(self):
        scout = self.project / ".claude" / "agents" / "scout.md"
        scout.parent.mkdir(parents=True)
        scout.write_text("mine", encoding="utf-8")
        (scout.parent / "cc-scout.md").write_text("mine too", encoding="utf-8")
        code, shown = self.call("show")
        self.assertEqual(code, 2)
        self.assertFalse(shown["installed"])
        self.assertTrue(shown["requested_configuration_only"])
        self.assertEqual(shown["paths"]["agents"]["scout"], str(scout))
        self.assertIn("unowned role", shown["issues"][0])
        self.assertIsNone(shown["pending_role_prefix"])

    def test_model_preserves_installed_bodies_policy_and_session(self):
        self.apply("install")
        base = self.project / ".claude" / "agents"
        scout = base / "scout.md"
        explore = base / "Explore.md"
        original_scout = scout.read_bytes()
        original_explore = explore.read_bytes()
        guidance = (self.project / "CLAUDE.md").read_bytes()
        fixture = self.root / "package"
        shutil.copytree(config.ROOT / "templates", fixture / "templates")
        policy_template = fixture / "templates" / "CLAUDE.md"
        policy_template.write_text(policy_template.read_text(encoding="utf-8").replace(config.END, "UPGRADED POLICY\n" + config.END), encoding="utf-8")
        with mock.patch.object(config, "ROOT", fixture):
            self.apply("model", "project", "--set", "Explore.model=opus")
            code, session = self.call("session")
            self.assertEqual(code, 0)
            self.assertEqual(session["Explore"]["model"], "opus")
            self.assertEqual(scout.read_bytes(), original_scout)
            self.assertEqual((self.project / "CLAUDE.md").read_bytes(), guidance)
            self.assertEqual(explore.read_bytes().replace(b"model: opus", b"model: sonnet"), original_explore)
            self.apply("update")
            self.assertIn(b"UPGRADED POLICY", (self.project / "CLAUDE.md").read_bytes())

    def test_role_template_change_blocks_model_review_and_session_until_update(self):
        self.apply("install")
        explore = self.project / ".claude" / "agents" / "Explore.md"
        original_explore = explore.read_bytes()
        fixture = self.root / "package"
        shutil.copytree(config.ROOT / "templates", fixture / "templates")
        role_template = fixture / "templates" / "agents" / "Explore.md"
        role_template.write_text(role_template.read_text(encoding="utf-8") + "\nUPGRADED TEMPLATE", encoding="utf-8")
        with mock.patch.object(config, "ROOT", fixture):
            for command, extra in (("model", ("--set", "Explore.model=opus")), ("review", ("--review-mode", "auto")),
                                   ("session", ())):
                with self.subTest(command=command):
                    code, error = self.call(command, "project", *extra)
                    self.assertEqual(code, 2, error)
                    self.assertIn("run setup update first", error["error"])
            self.assertEqual(explore.read_bytes(), original_explore)
            self.apply("update")
            self.assertIn(b"UPGRADED TEMPLATE", explore.read_bytes())
            self.apply("model", "project", "--set", "Explore.model=opus")
            code, session = self.call("session")
            self.assertEqual(code, 0, session)
            self.assertIn("UPGRADED TEMPLATE", session["Explore"]["prompt"])
            self.assertEqual(session["Explore"]["model"], "opus")

    ANALYST_0_16_0 = (
        '- Plan review: review the supplied stable plan in a fresh context. Check outcome, scope/non-goals, '
        'ownership, dependencies, acceptance proving the outcome, and rollback where relevant. Check that '
        'each claim can be verified independently with its own acceptance. Return READY when no material '
        'blocker remains, with brief checked scope and non-blocking advice separately; otherwise REVISE with '
        'every known blocker, evidence, minimum revision and observable closure check. Style preferences and '
        'speculative improvements do not block. Never rewrite or implement the plan. On a second review, '
        'verify resolved blockers and material regressions introduced by the revision without expanding into '
        'unrelated work. Judge each blocker main rejected on its evidence: withdraw it when the evidence '
        'holds, otherwise uphold it with the specific reason. Report missing essential evidence as a blocker,'
        ' not assumed readiness.')
    REVIEWER_0_16_0 = (
        'On a second review, check only whether the earlier findings are closed and whether the fixes '
        'introduced regressions; do not expand into unrelated work. When the main Agent rejects an earlier '
        'finding, it supplies evidence. Judge that evidence on its merits: withdraw the finding when the '
        'evidence holds, otherwise uphold it with the specific reason.')
    REVIEW_AUTO_0_16_0 = (
        'Automatic plan review is on. Use cc-feather:delegation so that work done from a plan, spec or ticket'
        ' the user agreed to gets plan review before implementation, then code review, then outcome '
        'verification before it is reported complete. Unplanned work that changes a security boundary, '
        'migrates data or performs an irreversible operation first needs a written, reviewed plan the user '
        'approves; other unplanned edits get no automatic review. Before implementing, state whether the work'
        ' is plan-driven and therefore reviewed, with a one-line reason. A task or session choice to turn '
        'automatic review off, or project guidance stating that automatic plan review is off in this project,'
        ' overrides this.')

    def templates_0_16_0(self):
        """The packaged templates with the analyst, reviewer and automatic review texts 0.16.0 installed."""
        fixture = self.root / "package-0.16.0"
        if fixture.exists():
            return fixture
        shutil.copytree(config.ROOT / "templates", fixture / "templates")
        for name, marker, text in (("analyst.md", "- Plan review:", self.ANALYST_0_16_0),
                                   ("reviewer.md", "the previous call for this claim", self.REVIEWER_0_16_0)):
            path = fixture / "templates" / "agents" / name
            lines = path.read_text(encoding="utf-8").split("\n")
            found = [index for index, line in enumerate(lines) if marker in line]
            self.assertEqual(len(found), 1, name)
            self.assertNotEqual(lines[found[0]], text, name)
            lines[found[0]] = text
            path.write_bytes("\n".join(lines).encode("utf-8"))
        (fixture / "templates" / "review-auto.md").write_bytes(self.REVIEW_AUTO_0_16_0.encode("utf-8") + b"\n")
        return fixture

    def use_fresh_roots(self, name):
        self.project = self.root / name / "project"
        self.home = self.root / name / "claude-home"
        self.project.mkdir(parents=True)
        self.home.mkdir()

    def install_0_16_0(self, scope="project", mode="auto", prefixed=False):
        """Install delegation as 0.16.0 rendered it, with a model choice the upgrade must keep."""
        agents = (self.project / ".claude" if scope == "project" else self.home) / "agents"
        if prefixed:
            agents.mkdir(parents=True, exist_ok=True)
            (agents / "custom.md").write_text("---\nname: scout\n---\nThe user's own scout\n", encoding="utf-8")
        with mock.patch.object(config, "ROOT", self.templates_0_16_0()):
            self.apply("install", scope, "--review-mode", mode)
            self.apply("model", scope, "--set", "analyst.model=sonnet")
        prefix = config.ROLE_PREFIX if prefixed else ""
        self.assertIn("On a second review", (agents / f"{prefix}reviewer.md").read_text(encoding="utf-8"))
        return agents, prefix

    @staticmethod
    def stale_warnings(shown):
        return [warning for warning in shown["warnings"] if warning.startswith("role ") and "older template" in warning]

    def stale_warning(self, agents, prefix, role):
        return f"role {prefix}{role} is from an older template ({agents / f'{prefix}{role}.md'}); run setup update"

    def test_0_16_0_role_templates_are_stale_until_setup_update(self):
        for scope in ("project", "user"):
            for mode in ("auto", "off"):
                for prefixed in (False, True):
                    with self.subTest(scope=scope, mode=mode, prefixed=prefixed):
                        self.use_fresh_roots(f"{scope}-{mode}-{prefixed}")
                        agents, prefix = self.install_0_16_0(scope, mode, prefixed)
                        guidance = (self.project if scope == "project" else self.home) / "CLAUDE.md"
                        for command in ("check", "show"):
                            code, shown = self.call(command, scope)
                            self.assertEqual(code, 0, shown)
                            self.assertEqual((shown["status"], shown["components"]["delegation"]["status"]), ("ok", "ok"))
                            self.assertEqual(shown["issues"], [])
                            self.assertTrue(shown["role_update_required"])
                            self.assertEqual(self.stale_warnings(shown), [self.stale_warning(agents, prefix, role)
                                                                          for role in ("analyst", "reviewer")])
                        before = {path: path.read_bytes() for path in (*agents.glob("*.md"), guidance)}
                        other = "off" if mode == "auto" else "auto"
                        for command, extra in (("model", ("--set", "scout.effort=low")), ("review", ("--review-mode", other)),
                                               ("session", ())):
                            code, error = self.call(command, scope, *extra)
                            self.assertEqual(code, 2, error)
                            self.assertIn("run setup update first", error["error"])
                        self.assertEqual(before, {path: path.read_bytes() for path in before})
                        self.apply("update", scope)
                        code, shown = self.call("check", scope)
                        self.assertEqual(code, 0, shown)
                        self.assertFalse(shown["role_update_required"])
                        self.assertEqual([w for w in shown["warnings"] if "older template" in w], [])
                        self.assertEqual(shown["review_mode"], mode)
                        self.assertEqual(shown["role_prefix"], prefix)
                        self.assertEqual(shown["choices"]["analyst"], {"model": "sonnet", "effort": "high"})
                        reviewer = (agents / f"{prefix}reviewer.md").read_text(encoding="utf-8")
                        analyst = (agents / f"{prefix}analyst.md").read_text(encoding="utf-8")
                        self.assertIn("When the brief says the previous call for this claim completed", reviewer)
                        self.assertIn("When the brief says the previous call for this plan completed", analyst)
                        self.assertIn("\nmodel: sonnet\n", analyst)
                        disclosure = "In auto, before the passes of a claim of plan-driven work main may, without asking"
                        self.assertNotIn(disclosure, before[guidance].decode("utf-8"))
                        self.assertEqual(disclosure in guidance.read_text(encoding="utf-8"), mode == "auto")
                        self.apply("model", scope, "--set", "scout.effort=low")
                        code, exported = self.call("session", scope)
                        self.assertEqual(code, 0, exported)
                        self.assertIn("previous call for this claim completed", exported[f"{prefix}reviewer"]["prompt"])

    # Repository safety C2 item 5 (B10): the role templates v0.20.0 shipped, kept verbatim in a data file copied from
    # `git show v0.20.0:templates/agents/<role>.md`, never rebuilt from the current templates. It replaces the v0.18.0
    # fixture and its two tests, retired in the same change: the stale check that matters is against the previous
    # release, and their assertion that exactly four role templates differ from v0.18.0 no longer holds.
    TEMPLATES_0_20_0 = Path(__file__).resolve().parent / "role_templates_0_20_0.json"
    CHANGED_SINCE_0_20_0 = ("reviewer", "verifier", "adversary", "analyst", "scout", "Explore")
    # The reference's read-only Git prefix for reading the tag (repository safety's Safe Git invocation).
    GIT_READ = ("git", "--no-pager", "--no-optional-locks", "-c", "core.fsmonitor=", "-c", "core.quotePath=true",
                "-c", "log.showSignature=false", "-c", "mailmap.file=", "-c", "mailmap.blob=",
                "-c", "blame.ignoreRevsFile=", "-c", "diff.orderFile=/dev/null", "-c", "submodule.recurse=false")

    def recorded_0_20_0(self):
        recorded = json.loads(self.TEMPLATES_0_20_0.read_bytes())
        self.assertEqual(recorded["tag"], "v0.20.0")
        self.assertEqual(recorded["source"], "git show v0.20.0:templates/agents/<role>.md")
        self.assertEqual(set(recorded["templates"]), set(self.CHANGED_SINCE_0_20_0))
        return recorded["templates"]

    def templates_0_20_0(self):
        """The packaged templates with the six role templates exactly as v0.20.0 shipped them."""
        fixture = self.root / "package-0.20.0"
        if fixture.exists():
            return fixture
        shutil.copytree(config.ROOT / "templates", fixture / "templates")
        for role, text in self.recorded_0_20_0().items():
            path = fixture / "templates" / "agents" / f"{role}.md"
            self.assertNotEqual(path.read_text(encoding="utf-8"), text, role)
            path.write_bytes(text.encode("utf-8"))
        return fixture

    def test_0_20_0_fixture_is_the_tagged_content_of_every_changed_role_template(self):
        def git(*args):
            return subprocess.run([*self.GIT_READ, *args], cwd=config.ROOT, stdin=subprocess.DEVNULL,
                                  capture_output=True, timeout=60)
        try:
            listed = git("ls-tree", "-r", "-z", "--name-only", "v0.20.0", "--", "templates")
        except (OSError, subprocess.TimeoutExpired) as error:
            self.skipTest(f"Git cannot be run, so the v0.20.0 templates cannot be read: {error}")
        if listed.returncode != 0:
            self.skipTest(f"no v0.20.0 tag in this checkout: {listed.stderr.decode('utf-8', 'replace').strip()}")
        changed = {}
        for name in filter(None, listed.stdout.decode("utf-8").split("\0")):
            shown = git("cat-file", "blob", f"v0.20.0:{name}")
            self.assertEqual(shown.returncode, 0, shown.stderr)
            current = config.ROOT / name
            if not current.is_file() or current.read_bytes() != shown.stdout:
                changed[name] = shown.stdout
        recorded = self.recorded_0_20_0()
        # Repository safety C1 changes the automatic-review guidance template, which is not a role template; the fixture
        # records role templates only, and changed guidance is reported by check's older-template warning instead.
        guidance = {name for name in changed if not name.startswith("templates/agents/")}
        self.assertEqual(guidance, {"templates/review-auto.md"})
        changed = {name: text for name, text in changed.items() if name not in guidance}
        self.assertEqual(sorted(changed), sorted(f"templates/agents/{role}.md" for role in self.CHANGED_SINCE_0_20_0))
        for role, text in recorded.items():
            with self.subTest(role=role):
                self.assertEqual(text.encode("utf-8"), changed[f"templates/agents/{role}.md"])

    def test_0_20_0_role_templates_are_stale_until_setup_update(self):
        stale = [role for role in config.ROLES if role in self.CHANGED_SINCE_0_20_0]
        self.assertEqual(len(stale), len(self.CHANGED_SINCE_0_20_0))
        for scope in ("project", "user"):
            for mode in ("auto", "off"):
                for prefixed in (False, True):
                    with self.subTest(scope=scope, mode=mode, prefixed=prefixed):
                        self.use_fresh_roots(f"0.20.0-{scope}-{mode}-{prefixed}")
                        agents = (self.project / ".claude" if scope == "project" else self.home) / "agents"
                        if prefixed:
                            agents.mkdir(parents=True)
                            (agents / "custom.md").write_text("---\nname: scout\n---\nThe user's own scout\n",
                                                              encoding="utf-8")
                        prefix = config.ROLE_PREFIX if prefixed else ""
                        # Explore keeps its exact name under a prefix.
                        names = {role: config._role_name(role, prefix) for role in config.ROLES}
                        with mock.patch.object(config, "ROOT", self.templates_0_20_0()):
                            self.apply("install", scope, "--review-mode", mode)
                            self.apply("model", scope, "--set", "reviewer.model=sonnet", "--set", "scout.effort=medium")
                            installed = {role: config._render(role, self.call("show", scope)[1]["choices"][role], prefix)
                                         for role in stale}
                        for role in stale:
                            self.assertEqual((agents / f"{names[role]}.md").read_bytes(), installed[role], role)
                        guidance = (self.project if scope == "project" else self.home) / "CLAUDE.md"
                        warnings = [f"role {names[role]} is from an older template ({agents / (names[role] + '.md')}); "
                                    "run setup update" for role in stale]
                        for command in ("check", "show"):
                            code, shown = self.call(command, scope)
                            self.assertEqual(code, 0, shown)
                            self.assertEqual((shown["status"], shown["components"]["delegation"]["status"]), ("ok", "ok"))
                            self.assertEqual(shown["issues"], [])
                            self.assertTrue(shown["role_update_required"])
                            self.assertEqual(set(shown["choices"]), set(config.ROLES))
                            self.assertEqual(self.stale_warnings(shown), warnings)
                            self.assertNotIn("delegation guidance is from an older template; run setup update",
                                             shown["warnings"])
                        before = {path: path.read_bytes() for path in (*agents.glob("*.md"), guidance)}
                        other = "off" if mode == "auto" else "auto"
                        for command, extra in (("model", ("--set", "scout.effort=low")), ("review", ("--review-mode", other)),
                                               ("session", ())):
                            code, error = self.call(command, scope, *extra)
                            self.assertEqual(code, 2, error)
                            self.assertIn("run setup update first", error["error"])
                        self.assertEqual(before, {path: path.read_bytes() for path in before})
                        self.apply("update", scope)
                        code, shown = self.call("check", scope)
                        self.assertEqual(code, 0, shown)
                        self.assertFalse(shown["role_update_required"])
                        self.assertEqual([w for w in shown["warnings"] if "older template" in w], [])
                        self.assertEqual(shown["review_mode"], mode)
                        self.assertEqual(shown["role_prefix"], prefix)
                        self.assertEqual(shown["choices"]["reviewer"], {"model": "sonnet", "effort": "high"})
                        self.assertEqual(shown["choices"]["scout"]["effort"], "medium")
                        by_name = {name: role for role, name in names.items()}
                        for path, data in before.items():
                            role = by_name.get(path.stem)
                            if path.parent == agents and role in stale:
                                current = config._render(role, shown["choices"][role], prefix)
                                self.assertEqual(path.read_bytes(), current, role)
                                self.assertNotEqual(current, data, role)
                            else:
                                self.assertEqual(path.read_bytes(), data, path)
                        self.apply("model", scope, "--set", "scout.effort=low")
                        code, exported = self.call("session", scope)
                        self.assertEqual(code, 0, exported)
                        for role in ("reviewer", "verifier", "adversary"):
                            self.assertIn("**Repository safety.** These rules govern every repository read",
                                          exported[names[role]]["prompt"])
                        for role in ("analyst", "scout", "Explore"):
                            self.assertIn("When a review assignment's brief gives no allowlist, report it as a missing "
                                          "requirement instead of reading the repository.",
                                          exported[names[role]]["prompt"])

    def test_edited_0_16_0_role_is_a_conflict_not_stale(self):
        agents, prefix = self.install_0_16_0()
        analyst = agents / "analyst.md"
        analyst.write_bytes(analyst.read_bytes() + b"\nUser changes\n")
        code, shown = self.call("check")
        self.assertEqual(code, 2, shown)
        self.assertEqual(shown["components"]["delegation"]["issues"], [f"managed role changed or missing: {analyst}"])
        self.assertTrue(shown["role_update_required"])
        self.assertEqual(self.stale_warnings(shown), [self.stale_warning(agents, prefix, "reviewer")])

    def test_role_differing_only_in_line_endings_is_stale(self):
        self.apply("install")
        reviewer = self.project / ".claude" / "agents" / "reviewer.md"
        state_path = self.project / ".claude" / "cc-feather" / "state.json"
        state = json.loads(state_path.read_bytes())
        reviewer.write_bytes(reviewer.read_bytes().replace(b"\n", b"\r\n"))
        state["components"]["delegation"]["hashes"]["reviewer"] = config.digest(reviewer.read_bytes())
        state_path.write_bytes(config.canonical(state) + b"\n")
        code, shown = self.call("check")
        self.assertEqual(code, 0, shown)
        self.assertEqual(shown["status"], "ok")
        self.assertTrue(shown["role_update_required"])
        self.assertEqual(self.stale_warnings(shown), [self.stale_warning(reviewer.parent, "", "reviewer")])
        self.apply("update")
        self.assertNotIn(b"\r\n", reviewer.read_bytes())
        self.assertFalse(self.call("check")[1]["role_update_required"])

    def test_legacy_name_installation_is_not_compared_with_current_templates(self):
        self.apply("install")
        agents = self.project / ".claude" / "agents"
        state_path = self.project / ".claude" / "cc-feather" / "state.json"
        state = json.loads(state_path.read_bytes())
        record = state["components"]["delegation"]
        for role in config.ROLES:
            if role == "Explore":
                continue
            path = agents / f"{role}.md"
            data = path.read_bytes().replace(f"name: {role}\n".encode(), f"name: feather-{role}\n".encode(), 1)
            path.unlink()
            (agents / f"feather-{role}.md").write_bytes(data)
            record["hashes"][role] = config.digest(data)
        record["legacy_names"] = True
        state_path.write_bytes(config.canonical(state) + b"\n")
        code, shown = self.call("check")
        self.assertEqual(code, 0, shown)
        self.assertTrue(shown["role_migration_required"])
        self.assertFalse(shown["role_update_required"])
        self.assertEqual(self.stale_warnings(shown), [])

    def test_role_whose_rendering_fails_is_not_reported_stale(self):
        agents, prefix = self.install_0_16_0()
        broken = self.root / "broken"
        shutil.copytree(config.ROOT / "templates", broken / "templates")
        reviewer = broken / "templates" / "agents" / "reviewer.md"
        reviewer.write_text(reviewer.read_text(encoding="utf-8").replace("{{effort}}", "high"), encoding="utf-8")
        with mock.patch.object(config, "ROOT", broken):
            code, shown = self.call("check")
            self.assertEqual(code, 0, shown)
            self.assertTrue(shown["role_update_required"])
            self.assertEqual(self.stale_warnings(shown), [self.stale_warning(agents, prefix, "analyst")])
            analyst = broken / "templates" / "agents" / "analyst.md"
            analyst.write_text(analyst.read_text(encoding="utf-8").replace("{{model}}", "opus"), encoding="utf-8")
            code, shown = self.call("check")
            self.assertEqual(code, 0, shown)
            self.assertFalse(shown["role_update_required"])
            self.assertEqual(self.stale_warnings(shown), [])

    def test_current_installation_reports_no_stale_roles(self):
        for scope in ("project", "user"):
            for mode in ("auto", "off"):
                with self.subTest(scope=scope, mode=mode):
                    self.use_fresh_roots(f"current-{scope}-{mode}")
                    self.apply("install", scope, "--review-mode", mode)
                    self.apply("model", scope, "--set", "analyst.model=sonnet", "--set", "reviewer.effort=medium")
                    code, shown = self.call("check", scope)
                    self.assertEqual(code, 0, shown)
                    self.assertFalse(shown["role_update_required"])
                    self.assertEqual([w for w in shown["warnings"] if "older template" in w], [])

    def test_rejected_saved_model_in_stale_installation_names_remove_and_reinstall(self):
        self.install_0_16_0()
        self.save_model_choices({"scout": "abc:"})
        code, checked = self.call("check")
        self.assertEqual(code, 2, checked)
        self.assertTrue(checked["role_update_required"])
        reported = [issue for issue in checked["issues"] if "saved model for scout" in issue]
        self.assertEqual(len(reported), 1, checked["issues"])
        self.assertIn("remove and reinstall", reported[0])
        self.assertIn("--review-mode", reported[0])
        self.assertNotIn("model --set", reported[0])
        code, error = self.call("model", "project", "--set", "scout.model=sonnet")
        self.assertEqual(code, 2)
        self.assertIn("run setup update first", error["error"])
        code, error = self.call("update")
        self.assertEqual(code, 2)
        self.assertIn("saved model is no longer accepted", error["error"])
        self.apply("remove")
        self.apply("install", "project", "--review-mode", "auto")
        code, checked = self.call("check")
        self.assertEqual(code, 0, checked)
        self.assertEqual(checked["review_mode"], "auto")
        self.assertFalse(checked["role_update_required"])

    def test_install_both_adds_handoff_beside_delegation_with_rejected_saved_model(self):
        self.apply("install")
        self.save_model_choices({"analyst": "abc:"})
        agents = self.project / ".claude" / "agents"
        roles = {path: path.read_bytes() for path in agents.glob("*.md")}
        self.apply("install", "project", "--component", "both")
        shown = self.call("show")[1]
        self.assertTrue(shown["components"]["handoff"]["installed"])
        self.assertEqual(roles, {path: path.read_bytes() for path in agents.glob("*.md")})
        for component in ("both", "delegation"):
            with self.subTest(component=component):
                code, error = self.call("update", "project", "--component", component)
                self.assertEqual(code, 2, error)
                self.assertIn("saved model is no longer accepted", error["error"])

    def test_review_mode_toggle_preserves_roles_and_choices(self):
        self.apply("install", "project", "--review-mode", "off")
        self.apply("model", "project", "--set", "scout.model=sonnet")
        scout = self.project / ".claude" / "agents" / "scout.md"
        original = scout.read_bytes()
        self.assertEqual(self.call("show")[1]["review_mode"], "off")
        self.apply("review", "project", "--review-mode", "auto")
        self.assertEqual(scout.read_bytes(), original)
        guidance = self.project / "CLAUDE.md"
        self.assertIn("Automatic plan review is on.", guidance.read_text(encoding="utf-8"))
        self.apply("review", "project", "--review-mode", "off")
        self.assertIn(config.PROJECT_REVIEW_OFF, guidance.read_text(encoding="utf-8"))
        self.assertNotIn("Automatic plan review is on.", guidance.read_text(encoding="utf-8"))
        self.apply("review", "project", "--review-mode", "auto")
        self.apply("update")
        self.assertIn("Automatic plan review is on.", guidance.read_text(encoding="utf-8"))
        self.apply("review", "project", "--review-mode", "off")
        self.apply("update")
        shown = self.call("show")[1]
        self.assertEqual(shown["review_mode"], "off")
        self.assertEqual(shown["choices"]["scout"]["model"], "sonnet")
        self.apply("remove")

    def test_review_toggle_keeps_guidance_from_older_templates(self):
        legacy = ("<!-- cc-feather:begin -->\n# Feather delegation for Claude Code\n\nOlder rules.\n\n"
                  "Automatic plan review mode: {mode}\n\nOlder triggers.\n\n<!-- cc-feather:end -->")
        with mock.patch.object(config, "_policy", lambda mode, prefix="", *, scope="user": legacy.format(mode=mode)):
            self.apply("install", "project", "--review-mode", "off")
        guidance = self.project / "CLAUDE.md"
        self.apply("review", "project", "--review-mode", "auto")
        self.assertIn("Automatic plan review mode: auto\n\nOlder triggers.", guidance.read_text(encoding="utf-8"))
        self.apply("update")
        text = guidance.read_text(encoding="utf-8")
        self.assertNotIn("Automatic plan review mode", text)
        self.assertIn("Automatic plan review is on.", text)
        self.assertEqual(self.call("show")[1]["review_mode"], "auto")

    def test_review_toggle_requires_update_for_unrecognized_older_guidance(self):
        older = "<!-- cc-feather:begin -->\n# Feather delegation for Claude Code\n\nOlder rules.\n<!-- cc-feather:end -->"
        with mock.patch.object(config, "_policy", lambda mode, prefix="", *, scope="user": older):
            self.apply("install", "project")
        guidance = self.project / "CLAUDE.md"
        before = guidance.read_bytes()
        code, result = self.call("review", "project", "--review-mode", "auto")
        self.assertNotEqual(code, 0)
        self.assertIn("run setup update first", json.dumps(result))
        self.assertEqual(guidance.read_bytes(), before)

    def test_check_warns_about_guidance_from_an_older_template(self):
        older = "<!-- cc-feather:begin -->\n# Feather delegation for Claude Code\n\nOlder rules.\n<!-- cc-feather:end -->"
        warning = "delegation guidance is from an older template; run setup update"
        for scope in ("project", "user"):
            with self.subTest(scope=scope):
                with mock.patch.object(config, "_policy", lambda mode, prefix="", *, scope="user": older):
                    self.apply("install", scope, "--review-mode", "auto")
                code, shown = self.call("check", scope)
                self.assertEqual((code, shown["status"], shown["components"]["delegation"]["status"]),
                                 (0, "ok", "ok"), shown)
                self.assertIn(warning, shown["warnings"])
                code, exported = self.call("session", scope)
                self.assertEqual(code, 0, exported)
                self.assertEqual(set(exported), set(config.ROLES))
                self.apply("update", scope)
                self.assertNotIn(warning, self.call("check", scope)[1]["warnings"])
        # A project installed off before the off line lets a user-scope auto win until setup update.
        guidance = self.project / "CLAUDE.md"
        self.apply("review", "project", "--review-mode", "off")
        self.replace_delegation_block(guidance, config._policy("off", "", scope="user"))
        code, shown = self.call("check")
        self.assertEqual((code, shown["status"]), (0, "ok"), shown)
        self.assertIn(warning, shown["warnings"])
        self.apply("update")
        self.assertIn(config.PROJECT_REVIEW_OFF, guidance.read_text(encoding="utf-8"))
        self.assertNotIn(warning, self.call("check")[1]["warnings"])

    def test_automatic_review_triggers_match_the_plan_review_procedure(self):
        triggers = "Unplanned work that makes a Security-critical change, migrates data or performs an irreversible operation"
        self.assertIn(triggers, config._auto_review())
        procedure = (config.ROOT / "skills" / "delegation" / "references" / "plan-review.md").read_text(encoding="utf-8")
        self.assertIn(triggers, procedure)

    def test_scope_path_state_and_choice_validation(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = config.main(["install", "--project", str(self.project)])
        self.assertEqual(code, 2)
        self.assertIn("--scope", output.getvalue())
        missing = self.root / "missing"
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = config.main(["install", "--project", str(missing), "--scope", "project"])
        self.assertEqual(code, 2)
        self.assertIn("does not exist", output.getvalue())
        code, error = self.call("model", "project", "--set", "scout.model=claude-opus-4-5[1m]")
        self.assertEqual(code, 2)  # not installed, but syntax is accepted
        self.assertIn("not installed", error["error"])
        self.apply("install")
        self.apply("model", "project", "--set", "scout.model=claude-opus-4-5[1m]", "--set", "scout.effort=max")
        state = self.project / ".claude" / "cc-feather" / "state.json"
        raw = json.loads(state.read_text(encoding="utf-8"))
        raw["components"]["delegation"]["choices"]["scout"]["effort"] = []
        state.write_text(json.dumps(raw), encoding="utf-8")
        code, error = self.call("show")
        self.assertEqual(code, 2)
        self.assertIn("invalid effort", error["error"])

    def test_settings_override_observations_redact_values(self):
        settings = self.project / ".claude" / "settings.local.json"
        settings.parent.mkdir()
        settings.write_text(json.dumps({"env": {"CLAUDE_CODE_SUBAGENT_MODEL": "secret-model-value",
                                               "CLAUDE_CODE_SUBAGENT_MODEL_FORCE": "true"},
                                        "private": "secret-token-value"}), encoding="utf-8")
        with mock.patch.dict(os.environ, {"CLAUDE_CODE_SUBAGENT_MODEL_FORCE": "true"}, clear=False):
            code, shown = self.call("show")
        self.assertEqual(code, 0)
        warning_text = "\n".join(shown["warnings"])
        self.assertIn("CLAUDE_CODE_SUBAGENT_MODEL_FORCE", warning_text)
        self.assertIn(str(settings), warning_text)
        self.assertNotIn("secret-model-value", warning_text)
        self.assertNotIn("secret-token-value", warning_text)

    def test_hard_link_target_is_rejected(self):
        target = self.root / "outside-hardlink.txt"
        target.write_text("keep", encoding="utf-8")
        explore = self.project / ".claude" / "agents" / "Explore.md"
        explore.parent.mkdir(parents=True)
        try:
            os.link(target, explore)
        except OSError:
            self.skipTest("hard link creation unavailable")
        code, result = self.call("install")
        self.assertEqual(code, 2)
        self.assertIn("hard-linked target", result["error"])
        self.assertEqual(target.read_text(encoding="utf-8"), "keep")

    def test_linked_target_is_rejected(self):
        target = self.root / "outside.txt"
        target.write_text("keep", encoding="utf-8")
        explore = self.project / ".claude" / "agents" / "Explore.md"
        explore.parent.mkdir(parents=True)
        try:
            explore.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation unavailable")
        code, result = self.call("install")
        self.assertEqual(code, 2)
        self.assertIn("linked path", result["error"])
        self.assertEqual(target.read_text(encoding="utf-8"), "keep")


    def test_handoff_lifecycle_preserves_delegation_and_unrelated_text(self):
        guidance = self.project / "CLAUDE.md"
        guidance.write_bytes(b"User first\n")
        self.apply("install", "project", "--component", "delegation")
        agent = self.project / ".claude" / "agents" / "scout.md"
        agent_before = agent.read_bytes()
        delegation = config._block_parts(guidance.read_text(encoding="utf-8"))[1]
        self.apply("install", "project", "--component", "handoff")
        shown = self.call("show")[1]
        self.assertTrue(shown["components"]["handoff"]["installed"])
        self.assertTrue(shown["components"]["delegation"]["installed"])
        self.assertEqual(shown["components"]["handoff"]["status"], "ok")
        self.assertEqual(agent.read_bytes(), agent_before)
        self.assertEqual(config._block_parts(guidance.read_text(encoding="utf-8"))[1], delegation)
        self.apply("update", "project", "--component", "handoff")
        self.apply("remove", "project", "--component", "handoff")
        self.assertFalse(self.call("show")[1]["components"]["handoff"]["installed"])
        self.assertTrue(self.call("show")[1]["components"]["delegation"]["installed"])
        self.assertIn("User first", guidance.read_text(encoding="utf-8"))
        self.assertEqual(agent.read_bytes(), agent_before)
        self.apply("remove", "project", "--component", "delegation")
        self.assertEqual(guidance.read_bytes(), b"User first\n")

    def test_handoff_only_ignores_agent_conflict_and_delegation_drift(self):
        agent = self.project / ".claude" / "agents" / "Explore.md"
        agent.parent.mkdir(parents=True)
        agent.write_text("user agent", encoding="utf-8")
        (agent.parent / "analyst.md").write_text("user analyst", encoding="utf-8")
        (agent.parent / "cc-analyst.md").write_text("user cc-analyst", encoding="utf-8")
        self.assertEqual(self.call("check")[1]["components"]["delegation"]["status"], "conflict")
        self.apply("install", "project", "--component", "handoff")
        self.assertEqual(agent.read_text(encoding="utf-8"), "user agent")
        self.assertEqual(self.call("show")[1]["components"]["handoff"]["status"], "ok")
        self.apply("update", "project", "--component", "handoff")
        self.apply("remove", "project", "--component", "handoff")
        self.assertEqual(agent.read_text(encoding="utf-8"), "user agent")
        self.assertFalse((self.project / ".claude" / "cc-feather" / "state.json").exists())

    def test_both_mixed_install_update_remove_is_single_plan(self):
        self.apply("install", "project", "--component", "handoff")
        guidance = self.project / "CLAUDE.md"
        handoff = config._block_parts(guidance.read_text(encoding="utf-8"),
                                      config.HANDOFF_BEGIN, config.HANDOFF_END)[1]
        result = self.apply("install", "project", "--component", "both")
        self.assertEqual(len([change for change in result["changes"] if change["path"].endswith("state.json")]), 1)
        self.assertEqual(config._block_parts(guidance.read_text(encoding="utf-8"),
                                             config.HANDOFF_BEGIN, config.HANDOFF_END)[1], handoff)
        self.apply("remove", "project", "--component", "delegation")
        self.assertTrue(self.call("show")[1]["components"]["handoff"]["installed"])
        self.apply("update", "project", "--component", "both")
        self.assertFalse(self.call("show")[1]["components"]["delegation"]["installed"])
        self.apply("remove", "project", "--component", "both")
        self.assertFalse((self.project / ".claude" / "cc-feather" / "state.json").exists())
        self.assertFalse(guidance.exists() and guidance.read_text(encoding="utf-8").strip())

    def test_legacy_delegation_remove_preserves_handoff_reminder(self):
        self.legacy_install()
        guidance = self.project / "CLAUDE.md"
        self.apply("remove", "project", "--component", "delegation")
        shown = self.call("show")[1]
        self.assertTrue(shown["components"]["handoff"]["installed"])
        self.assertFalse(shown["components"]["delegation"]["installed"])
        self.assertIn("handoff work", guidance.read_text(encoding="utf-8"))
        self.apply("update", "project", "--component", "handoff")
        self.assertIn("handoff", guidance.read_text(encoding="utf-8"))
        self.apply("remove", "project", "--component", "handoff")

    def test_both_apply_rolls_back_components_together(self):
        guidance = self.project / "CLAUDE.md"
        guidance.write_bytes(b"Keep me")
        _, preview = self.call("install", "project", "--component", "both")
        real_replace = config._replace

        def fail_handoff(path, data):
            if path == guidance:
                raise OSError("injected guidance failure")
            return real_replace(path, data)

        with mock.patch.object(config, "_replace", side_effect=fail_handoff):
            code, result = self.call("install", "project", "--component", "both",
                                     "--apply", "--expected-plan", preview["plan_id"])
        self.assertEqual(code, 2, result)
        self.assertIn("injected guidance failure", result["error"])
        self.assertEqual(guidance.read_bytes(), b"Keep me")
        self.assertFalse((self.project / ".claude" / "cc-feather" / "state.json").exists())
        self.assertFalse(list((self.project / ".claude" / "agents").glob("*.md")))

    def test_legacy_v2_combined_block_splits_with_lf_and_crlf(self):
        for newline in ("\n", "\r\n"):
            with self.subTest(newline=repr(newline)):
                self.apply("install", "project")
                state_path = self.project / ".claude" / "cc-feather" / "state.json"
                guidance = self.project / "CLAUDE.md"
                raw = json.loads(state_path.read_bytes())
                legacy = {"version": 2, "scope": "project", **{
                    key: value for key, value in raw["components"]["delegation"].items()
                    if key not in {"legacy_names", "role_prefix", "external_roles"}
                }}
                body = guidance.read_bytes().decode("utf-8")
                historical = (
                    "\n\n## Handoff and setup lifecycle\n\n"
                    "When asked to save, list, read or resume handoff work, use the available "
                    "cc-feather:handoff skill and preserve its records/history rules. "
                    "Maintain an already active handoff at useful milestones with accepted findings, "
                    "decisions, verification and remaining blockers. Delegation alone does not start "
                    "a handoff or authorize editing other records.\n\n"
                    "Use cc-feather:setup for installation checks, updates and removal. "
                    "Preserve handoff data.\n"
                )
                body = body.replace(config.END, historical + config.END).replace("\n", newline)
                guidance.write_bytes(body.encode("utf-8"))
                legacy["block_hash"] = config.digest(config._block_parts(body)[1].encode("utf-8"))
                state_path.write_bytes(config.canonical(legacy) + b"\n")
                shown = self.call("show")[1]
                self.assertTrue(shown["components"]["handoff"]["installed"])
                self.assertTrue(shown["components"]["handoff"]["migration_required"])
                self.assertFalse(shown["role_migration_required"])
                before_export = {p: p.read_bytes() for p in self.project.rglob("*") if p.is_file()}
                code, exported = self.call("session")
                self.assertEqual(code, 0, exported)
                self.assertEqual(set(exported), set(config.ROLES))
                self.assertEqual(before_export, {p: p.read_bytes() for p in self.project.rglob("*") if p.is_file()})
                self.apply("update", "project", "--component", "handoff")
                migrated = guidance.read_text(encoding="utf-8")
                self.assertEqual(migrated.count("When asked to save"), 0)
                self.assertIn("## Setup lifecycle", migrated)
                self.assertIn("Preserve handoff data.", migrated)
                self.assertTrue(self.call("show")[1]["components"]["delegation"]["installed"])
                self.apply("remove", "project", "--component", "handoff")
                self.assertIn("Preserve handoff data.", guidance.read_text(encoding="utf-8"))
                self.apply("remove", "project", "--component", "delegation")

    def test_both_update_remove_handoff_only_ignore_unowned_agents(self):
        self.apply("install", "project", "--component", "handoff")
        agent = self.project / ".claude" / "agents" / "analyst.md"
        agent.parent.mkdir(parents=True)
        agent.write_text("user analyst", encoding="utf-8")
        self.apply("update", "project", "--component", "both")
        self.assertFalse(self.call("show")[1]["components"]["delegation"]["installed"])
        self.apply("remove", "project", "--component", "both")
        self.assertEqual(agent.read_text(encoding="utf-8"), "user analyst")
        self.assertFalse((self.project / ".claude" / "cc-feather" / "state.json").exists())

    def test_v1_handoff_migration_requires_role_rename_before_model(self):
        self.legacy_install()
        self.apply("update", "project", "--component", "handoff")
        shown = self.call("show")[1]
        self.assertTrue(shown["migration_required"])
        for command, extra in (("model", ("--set", "scout.model=opus")),
                               ("review", ("--review-mode", "off"))):
            code, result = self.call(command, "project", *extra)
            self.assertEqual(code, 2, result)
            self.assertIn("run setup update first", result["error"])
        self.apply("update", "project", "--component", "delegation")
        self.assertFalse(self.call("show")[1]["migration_required"])
        self.apply("model", "project", "--set", "scout.model=opus")

    def test_unreadable_agent_tree_does_not_hide_handoff_status(self):
        self.apply("install", "project", "--component", "handoff")
        with mock.patch.object(config, "_collisions", side_effect=PermissionError("agent tree denied")):
            code, shown = self.call("check")
            self.assertEqual(code, 2)
            self.assertEqual(shown["status"], "conflict")
            self.assertTrue(shown["components"]["handoff"]["installed"])
            self.assertEqual(shown["components"]["handoff"]["status"], "ok")
            self.assertEqual(shown["components"]["delegation"]["status"], "conflict")
            self.assertIn("agent tree denied", shown["components"]["delegation"]["issues"])
            self.apply("update", "project", "--component", "handoff")

    def test_unreadable_or_linked_settings_remain_diagnostic_warnings(self):
        self.apply("install", "project", "--component", "handoff")
        target = self.home / "settings.json"
        real_read, real_safe = config.read, config._safe_path

        def denied_read(path):
            if path == target:
                raise PermissionError("settings denied")
            return real_read(path)

        def linked_path(path):
            if path == target:
                raise config.ConfigError("linked settings")
            return real_safe(path)

        for field, handler in (("read", denied_read), ("_safe_path", linked_path)):
            with self.subTest(field=field), mock.patch.object(config, field, side_effect=handler):
                code, shown = self.call("check")
                self.assertEqual(code, 0, shown)
                self.assertTrue(shown["components"]["handoff"]["installed"])
                self.assertIn("runtime overrides are unknown", " ".join(shown["warnings"]))
                self.assertIn(str(target), " ".join(shown["warnings"]))

    def test_both_install_rejects_changed_mode_for_existing_delegation(self):
        self.apply("install", "project", "--component", "delegation")
        before = {p: p.read_bytes() for p in self.project.rglob("*") if p.is_file()}
        code, result = self.call("install", "project", "--component", "both", "--review-mode", "auto")
        self.assertEqual(code, 2, result)
        self.assertIn("use review", result["error"])
        self.assertEqual(before, {p: p.read_bytes() for p in self.project.rglob("*") if p.is_file()})
        result = self.apply("install", "project", "--component", "both", "--review-mode", "off")
        self.assertEqual(result["review_mode"], "off")
        self.assertEqual(self.call("show")[1]["review_mode"], "off")
        self.assertTrue(self.call("show")[1]["components"]["handoff"]["installed"])

    def test_handoff_options_do_not_require_delegation(self):
        self.assertEqual(self.call("model", "project", "--component", "handoff",
                                   "--set", "scout.model=opus")[0], 2)
        self.assertEqual(self.call("review", "project", "--component", "handoff",
                                   "--review-mode", "auto")[0], 2)
        self.assertEqual(self.call("install", "project", "--component", "handoff",
                                   "--review-mode", "auto")[0], 2)
        self.apply("install", "project", "--component", "handoff")
        self.assertEqual(self.call("session")[0], 0)
        self.assertFalse((self.project / ".claude" / "agents").exists())

    # D1: an off project overrides user-scope automatic review.

    def replace_delegation_block(self, guidance, block):
        """Install-time rendering from an earlier version: put the block in place and own it."""
        parts = config._block_parts(guidance.read_bytes().decode("utf-8"))
        guidance.write_bytes((parts[0] + block + parts[2]).encode("utf-8"))
        base = self.home if guidance.parent == self.home else self.project / ".claude"
        state_path = base / "cc-feather" / "state.json"
        state = json.loads(state_path.read_bytes())
        state["components"]["delegation"]["block_hash"] = config.digest(block.encode("utf-8"))
        state_path.write_bytes(config.canonical(state) + b"\n")

    def test_project_off_overrides_user_auto(self):
        self.apply("install", "user", "--review-mode", "auto")
        self.apply("install", "project")
        project_text = (self.project / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn(config.PROJECT_REVIEW_OFF + "\n\n" + config.END, project_text)
        self.assertNotIn("Automatic plan review is on.", project_text)
        user_text = (self.home / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn(config._auto_review(), user_text)
        self.assertNotIn(config.PROJECT_REVIEW_OFF, user_text)
        self.apply("review", "user", "--review-mode", "off")
        self.assertNotIn("Automatic plan review", (self.home / "CLAUDE.md").read_text(encoding="utf-8"))

    def test_project_off_auto_off_round_trip(self):
        self.apply("install", "project")
        guidance = self.project / "CLAUDE.md"
        installed = guidance.read_bytes()
        self.apply("review", "project", "--review-mode", "auto")
        text = guidance.read_text(encoding="utf-8")
        self.assertIn("Automatic plan review is on.", text)
        self.assertNotIn(config.PROJECT_REVIEW_OFF, text)
        self.apply("review", "project", "--review-mode", "off")
        self.assertEqual(guidance.read_bytes(), installed)
        self.assertEqual(self.call("check")[1]["components"]["delegation"]["status"], "ok")

    def test_project_off_install_from_before_the_off_line_is_accepted(self):
        self.apply("install", "project")
        guidance = self.project / "CLAUDE.md"
        self.replace_delegation_block(guidance, config._policy("off", "", scope="user"))
        self.assertNotIn("Automatic plan review", guidance.read_text(encoding="utf-8"))
        shown = self.call("check")[1]
        self.assertEqual((shown["status"], shown["components"]["delegation"]["status"]), ("ok", "ok"), shown)
        self.apply("review", "project", "--review-mode", "auto")
        self.assertIn("Automatic plan review is on.", guidance.read_text(encoding="utf-8"))
        self.apply("review", "project", "--review-mode", "off")
        self.assertIn(config.PROJECT_REVIEW_OFF, guidance.read_text(encoding="utf-8"))

    def crlf_package(self):
        """A copy of the templates as a CRLF checkout would have them."""
        fixture = self.root / "crlf-package"
        shutil.copytree(config.ROOT / "templates", fixture / "templates")
        for path in (fixture / "templates").rglob("*"):
            if path.is_file():
                path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
        return fixture

    def test_crlf_installs_from_before_lf_templates_switch_review_and_keep_crlf(self):
        fixture = self.crlf_package()
        template = (fixture / "templates" / "CLAUDE.md").read_bytes().decode("utf-8")
        with mock.patch.object(config, "ROOT", fixture):
            auto = config._auto_review() + "\n\n"
        # Rendering by versions that kept the template's line endings.
        legacy = {mode: config._block_parts(template)[1].replace("{{auto_review}}", text).replace("{{role_names}}", "")
                  for mode, text in (("off", ""), ("auto", auto))}
        self.assertIn("\r\n", legacy["off"])
        for scope, mode, new_mode, expected in (("project", "off", "auto", "Automatic plan review is on."),
                                                ("user", "auto", "off", None)):
            with self.subTest(scope=scope):
                self.apply("install", scope, "--review-mode", mode)
                guidance = (self.project if scope == "project" else self.home) / "CLAUDE.md"
                self.replace_delegation_block(guidance, legacy[mode])
                self.assertEqual(self.call("check", scope)[1]["components"]["delegation"]["status"], "ok")
                self.apply("review", scope, "--review-mode", new_mode)
                block = config._block_parts(guidance.read_bytes().decode("utf-8"))[1]
                self.assertEqual(block.count("\n"), block.count("\r\n"))
                self.assertGreater(block.count("\r\n"), 3)
                if expected:
                    self.assertIn(expected, block)
                    self.assertNotIn(config.PROJECT_REVIEW_OFF, block)
                else:
                    self.assertNotIn("Automatic plan review", block)
                shown = self.call("check", scope)[1]
                self.assertEqual(shown["components"]["delegation"]["status"], "ok", shown)
                self.assertEqual(shown["review_mode"], new_mode)

    # D5: rendering does not depend on the checkout's line endings.

    def test_crlf_templates_render_like_lf(self):
        def rendered():
            defaults = config._defaults()
            items = {"handoff": config._handoff_policy(), "auto": config._auto_review()}
            for prefix in ("", config.ROLE_PREFIX):
                for role in config.ROLES:
                    items[(role, prefix)] = config._render(role, defaults[role], prefix)
                for mode in ("auto", "off"):
                    for scope in ("project", "user"):
                        items[(mode, prefix, scope)] = config._policy(mode, prefix, scope=scope)
            return items
        expected = rendered()
        with mock.patch.object(config, "ROOT", self.crlf_package()):
            actual = rendered()
        self.assertEqual(actual, expected)
        for value in actual.values():
            self.assertNotIn("\r", value if isinstance(value, str) else value.decode("utf-8"))

    # D2: a later agent using a role name blocks only what update must settle first.

    def test_later_same_name_agent_does_not_block_remove(self):
        self.apply("install")
        agents = self.project / ".claude" / "agents"
        mine = agents / "mine" / "my-scout.md"
        mine.parent.mkdir()
        mine.write_text("---\nname: scout\n---\nMine\n", encoding="utf-8")
        before = self.files()
        for command in (("model", "project", "--set", "scout.effort=medium"),
                        ("review", "project", "--review-mode", "auto")):
            with self.subTest(command=command[0]):
                code, result = self.call(*command)
                self.assertEqual(code, 2, result)
                self.assertIn("role names are now taken by other agents; run setup update first", result["error"])
        self.assertEqual(before, self.files())
        self.assertEqual(self.call("check")[1]["pending_role_prefix"], config.ROLE_PREFIX)
        self.apply("remove")
        self.assertEqual([p.relative_to(agents).as_posix() for p in agents.rglob("*.md")], ["mine/my-scout.md"])
        self.assertEqual(mine.read_text(encoding="utf-8"), "---\nname: scout\n---\nMine\n")

    def test_later_same_name_agent_update_moves_to_prefix(self):
        self.apply("install", "project", "--review-mode", "auto")
        agents = self.project / ".claude" / "agents"
        mine = agents / "mine" / "my-scout.md"
        mine.parent.mkdir()
        mine.write_text("---\nname: scout\n---\nMine\n", encoding="utf-8")
        self.apply("update")
        self.assert_prefixed_roles(agents)
        self.apply("model", "project", "--set", "scout.effort=medium")
        self.apply("review", "project", "--review-mode", "off")
        # A prefixed name taken later still blocks settings, but never removal.
        taken = agents / "mine" / "taken.md"
        taken.write_text("---\nname: cc-scout\n---\nMine too\n", encoding="utf-8")
        code, result = self.call("model", "project", "--set", "scout.effort=high")
        self.assertEqual(code, 2, result)
        self.assertIn("duplicate native agent name cc-scout", result["error"])
        self.apply("remove")
        self.assertEqual(sorted(p.name for p in agents.rglob("*.md")), ["my-scout.md", "taken.md"])

    # D3: project scope must not be the user configuration.

    def assert_user_configuration_refused(self, command=("install", "project")):
        # Nothing is created: no file, no lock and no backup directory.
        entries = lambda: {p: p.read_bytes() if p.is_file() else None for p in self.root.rglob("*")}
        before = entries()
        code, result = self.call(*command)
        self.assertEqual(code, 2, result)
        self.assertIn("project scope here would write the user configuration", result["error"])
        self.assertIn("use --scope user", result["error"])
        self.assertEqual(before, entries())

    def test_project_scope_that_is_the_user_configuration_is_refused(self):
        fake_home = self.root / "home"
        (fake_home / ".claude").mkdir(parents=True)
        other = self.root / "other"
        other.mkdir()
        config_dir = self.root / "config"
        config_dir.mkdir()
        cases = [("home", fake_home, self.home),
                 ("home claude directory", fake_home / ".claude", self.home),
                 ("claude home", config_dir, config_dir),
                 ("project .claude is the claude home", other, other / ".claude")]
        if os.name == "nt":
            cases.append(("case variant of home", Path(str(fake_home).upper()), self.home))
        environment = {"HOME": str(fake_home), "USERPROFILE": str(fake_home)}
        with mock.patch.dict(os.environ, environment):
            self.assertEqual(Path.home(), fake_home)
            for name, project, claude_home in cases:
                with self.subTest(case=name):
                    self.project, self.home = project, claude_home
                    self.assert_user_configuration_refused()
                    self.assert_user_configuration_refused(("install", "project", "--component", "handoff"))

    def test_existing_aliased_project_install_can_be_checked_and_removed(self):
        elsewhere = self.root / "elsewhere"
        elsewhere.mkdir()
        with mock.patch.dict(os.environ, {"HOME": str(elsewhere), "USERPROFILE": str(elsewhere)}):
            self.apply("install", "project", "--component", "both")
        # The same project directory later is the user's home: its .claude is the user configuration.
        with mock.patch.dict(os.environ, {"HOME": str(self.project), "USERPROFILE": str(self.project)}):
            for command in (("install", "project", "--component", "both"), ("update", "project"),
                            ("model", "project", "--set", "scout.effort=medium"),
                            ("review", "project", "--review-mode", "auto")):
                with self.subTest(command=command[0]):
                    self.assert_user_configuration_refused(command)
            code, shown = self.call("check")
            self.assertEqual((code, shown["status"]), (0, "ok"), shown)
            self.apply("remove", "project", "--component", "both")
        self.assertEqual(list((self.project / ".claude" / "agents").glob("*.md")), [])
        self.assertFalse((self.project / ".claude" / "cc-feather" / "state.json").exists())

    # D6: plain-text names in other Markdown files do not block setup.

    def test_plain_text_agent_name_is_not_a_native_name(self):
        notes = self.project / ".claude" / "agents" / "notes" / "README.md"
        notes.parent.mkdir(parents=True)
        notes.write_text("---\nname: My agent notes\n---\nNotes\n", encoding="utf-8")
        self.apply("install")
        self.assertEqual(self.call("check")[1]["status"], "ok")
        self.apply("remove")
        for header in ("name: >-\n  scout", "name: !!str scout", "name: My agent\n  notes", "name: - scout",
                       "name: 'unterminated", "name: My notes\n\n  continued"):
            with self.subTest(header=header):
                notes.write_text(f"---\n{header}\n---\nNotes\n", encoding="utf-8")
                before = self.files()
                code, result = self.call("install")
                self.assertEqual(code, 2, result)
                self.assertIn("cannot inspect agent name syntax", result["error"])
                self.assertEqual(before, self.files())
        # Without a closing line Claude Code reads no frontmatter, so the file is no agent.
        notes.write_text("---\nname: My agent notes\nNo closing line\n", encoding="utf-8")
        code, preview = self.call("install")
        self.assertEqual(code, 0, preview)
        self.assertIn(f"Agent file has no closing frontmatter line: {notes}; it was not read as an agent",
                      preview["warnings"])
        self.apply("install")

    def test_non_utf8_agent_markdown_is_skipped_with_a_warning(self):
        legacy = self.project / ".claude" / "agents" / "legacy" / "old.md"
        legacy.parent.mkdir(parents=True)
        legacy.write_bytes(b"---\nname: \xff\xfe scout\n---\n")
        code, preview = self.call("install")
        self.assertEqual(code, 0, preview)
        self.assertTrue([w for w in preview["warnings"] if "not UTF-8" in w and str(legacy) in w], preview["warnings"])
        self.apply("install")
        code, shown = self.call("check")
        self.assertEqual((code, shown["status"]), (0, "ok"), shown)
        self.assertTrue([w for w in shown["warnings"] if "not UTF-8" in w and str(legacy) in w], shown["warnings"])
        self.apply("remove")
        self.assertEqual(legacy.read_bytes(), b"---\nname: \xff\xfe scout\n---\n")

    # DF2: an agent file that is not UTF-8 goes through the same name parser as a UTF-8 one.

    def test_non_utf8_agent_using_a_role_name_does_not_block_remove(self):
        # test_later_same_name_agent_does_not_block_remove with a byte that is not UTF-8.
        self.apply("install")
        agents = self.project / ".claude" / "agents"
        mine = agents / "mine" / "my-scout.md"
        mine.parent.mkdir()
        content = b"---\nname: scout\ndescription: \xff\n---\nMine\n"
        mine.write_bytes(content)
        before = self.files()
        for command in (("model", "project", "--set", "scout.effort=medium"),
                        ("review", "project", "--review-mode", "auto")):
            with self.subTest(command=command[0]):
                code, result = self.call(*command)
                self.assertEqual(code, 2, result)
                self.assertIn("role names are now taken by other agents; run setup update first", result["error"])
        self.assertEqual(before, self.files())
        shown = self.call("check")[1]
        self.assertEqual(shown["pending_role_prefix"], config.ROLE_PREFIX)
        # A managed name gets the collision handling instead of the warning.
        self.assertFalse([w for w in shown["warnings"] if "not UTF-8" in w], shown["warnings"])
        self.apply("remove")
        self.assertEqual([p.relative_to(agents).as_posix() for p in agents.rglob("*.md")], ["mine/my-scout.md"])
        self.assertEqual(mine.read_bytes(), content)

    def test_non_utf8_agent_using_a_role_name_moves_install_and_update_to_prefix(self):
        # test_later_same_name_agent_update_moves_to_prefix with bytes that are not UTF-8, for a fresh install too.
        content = b"---\nname: scout\ndescription: \xff\n---\nMine\n"
        for when in ("install", "update"):
            with self.subTest(when=when):
                self.project = self.root / f"non-utf8-{when}"
                agents = self.project / ".claude" / "agents"
                mine = agents / "mine" / "my-scout.md"
                mine.parent.mkdir(parents=True)
                if when == "install":
                    mine.write_bytes(content)
                self.apply("install", "project", "--review-mode", "auto")
                if when == "update":
                    mine.write_bytes(content)
                    self.apply("update")
                self.assert_prefixed_roles(agents)
                self.apply("model", "project", "--set", "scout.effort=medium")
                self.apply("review", "project", "--review-mode", "off")
                # A prefixed name taken later still blocks settings, but never removal.
                taken = agents / "mine" / "taken.md"
                taken.write_bytes(b"---\nname: cc-scout\ndescription: \xff\n---\nMine too\n")
                code, result = self.call("model", "project", "--set", "scout.effort=high")
                self.assertEqual(code, 2, result)
                self.assertIn("duplicate native agent name cc-scout", result["error"])
                self.apply("remove")
                self.assertEqual(sorted(p.name for p in agents.rglob("*.md")), ["my-scout.md", "taken.md"])
                self.assertEqual(mine.read_bytes(), content)

    def test_non_utf8_agent_name_syntax_errors_block_like_utf8(self):
        notes = self.project / ".claude" / "agents" / "notes" / "README.md"
        notes.parent.mkdir(parents=True)
        for content, error in ((b"---\nname: !!str scout\ndescription: \xff\n---\nNotes\n", "cannot inspect agent name syntax"),
                               (b"---\nname: scout\nname: notes\ndescription: \xff\n---\n", "duplicate agent name declaration")):
            with self.subTest(error=error):
                notes.write_bytes(content)
                before = self.files()
                code, result = self.call("install")
                self.assertEqual(code, 2, result)
                self.assertIn(error, result["error"])
                self.assertEqual(before, self.files())
        # Without a closing line the file is no agent, as for UTF-8 files: a warning, not an error.
        notes.write_bytes(b"---\nname: scout\ndescription: \xff\nNo closing line\n")
        code, preview = self.call("install")
        self.assertEqual(code, 0, preview)
        self.assertIn(f"Agent file has no closing frontmatter line: {notes}; it was not read as an agent",
                      preview["warnings"])
        self.apply("install")
        self.assertEqual(self.saved_state()["components"]["delegation"]["role_prefix"], "")

    def test_utf16_agent_with_a_byte_order_mark_is_read_like_utf8(self):
        text = "---\nname: scout\ndescription: Mine\n---\nMine\n"
        for name, content in (("utf-16-le", b"\xff\xfe" + text.encode("utf-16-le")),
                              ("utf-16-be", b"\xfe\xff" + text.encode("utf-16-be"))):
            with self.subTest(encoding=name):
                self.project = self.root / name
                agents = self.project / ".claude" / "agents"
                mine = agents / "mine" / "scout.md"
                mine.parent.mkdir(parents=True)
                mine.write_bytes(content)
                shown = self.call("check")[1]
                self.assertEqual((shown["status"], shown["pending_role_prefix"]), ("ok", config.ROLE_PREFIX), shown)
                self.assertFalse([w for w in shown["warnings"] if "not UTF-8" in w], shown["warnings"])
                self.apply("install")
                self.assert_prefixed_roles(agents)
                self.apply("remove")
                self.assertEqual(mine.read_bytes(), content)

    def test_unmanaged_non_utf8_agent_warning_names_how_it_was_read(self):
        text = "---\nname: my-helper\ndescription: Mine\n---\nMine\n"
        for name, content, how in (("utf-16-le", b"\xff\xfe" + text.encode("utf-16-le"), "read as UTF-16"),
                                   ("latin-1", text.replace("Mine\n---", "Mine \xff\n---").encode("latin-1"),
                                    "read with replacement characters")):
            with self.subTest(encoding=name):
                self.project = self.root / name
                mine = self.project / ".claude" / "agents" / "mine" / "helper.md"
                mine.parent.mkdir(parents=True)
                mine.write_bytes(content)
                code, preview = self.call("install")
                self.assertEqual(code, 0, preview)
                self.assertTrue([w for w in preview["warnings"] if "not UTF-8" in w and how in w], preview["warnings"])

    # D8: a lock left by an interrupted run names the file to delete.

    def test_lock_error_names_the_lock_to_delete(self):
        _, preview = self.call("install")
        lock = self.project / ".claude" / "cc-feather" / ".lock"
        lock.parent.mkdir(parents=True)
        lock.write_bytes(b"")
        code, result = self.call("install", "project", "--apply", "--expected-plan", preview["plan_id"])
        self.assertEqual(code, 2, result)
        self.assertIn(f"scope is locked: {lock}; if no other setup is running, delete {lock} and retry", result["error"])
        self.assertTrue(lock.exists())

    # D9: remove deletes an instruction file setup created once nothing else remains in it.

    def test_remove_deletes_a_created_instruction_file_left_empty(self):
        guidance = self.project / "CLAUDE.md"
        self.apply("install")
        self.assertIs(self.saved_state()["created_guidance"], True)
        self.apply("remove")
        self.assertFalse(guidance.exists())
        self.apply("install", "user")
        self.apply("remove", "user")
        self.assertFalse((self.home / "CLAUDE.md").exists())

    def test_remove_keeps_instruction_files_setup_did_not_create_or_the_user_changed(self):
        guidance = self.project / "CLAUDE.md"
        guidance.write_bytes(b"")
        self.apply("install")
        self.assertNotIn("created_guidance", self.saved_state())
        self.apply("remove")
        self.assertEqual(guidance.read_bytes(), b"")
        guidance.unlink()
        self.apply("install")
        guidance.write_bytes(guidance.read_bytes() + b"\nUse pnpm.\n")
        self.apply("remove")
        self.assertEqual(guidance.read_text(encoding="utf-8").strip(), "Use pnpm.")

    def test_created_instruction_file_flag_survives_component_changes(self):
        guidance = self.project / "CLAUDE.md"
        self.apply("install", "project", "--component", "handoff")
        self.apply("install", "project", "--component", "delegation")
        self.apply("review", "project", "--review-mode", "auto")
        self.apply("remove", "project", "--component", "delegation")
        self.assertIs(self.saved_state()["created_guidance"], True)
        self.apply("update", "project", "--component", "handoff")
        self.assertIs(self.saved_state()["created_guidance"], True)
        self.apply("remove", "project", "--component", "handoff")
        self.assertFalse(guidance.exists())

    def test_created_guidance_state_is_validated(self):
        self.apply("install", "project", "--component", "both")
        state_path = self.project / ".claude" / "cc-feather" / "state.json"
        original = self.saved_state()
        components = {**original["components"], "delegation": {
            key: value for key, value in original["components"]["delegation"].items()
            if key not in {"role_prefix", "external_roles"}}}
        for name, state in (("false", {**original, "created_guidance": False}),
                            ("string", {**original, "created_guidance": "true"}),
                            ("one", {**original, "created_guidance": 1}),
                            ("v3", {"version": 3, "scope": "project", "components": components, "created_guidance": True})):
            with self.subTest(value=name):
                state_path.write_bytes(config.canonical(state) + b"\n")
                code, result = self.call("show")
                self.assertEqual(code, 2, result)
                self.assertIn("state component schema mismatch", result["error"])
                code, result = self.call("remove", "project", "--component", "both")
                self.assertEqual(code, 2, result)
        state_path.write_bytes(config.canonical(original) + b"\n")
        self.assertEqual(self.call("show")[1]["status"], "ok")

    # D4: linked ancestors of the roots are resolved once; links at or below them stay refused.

    def use_link_base(self, require_strict_realpath=True):
        """Move this test to a base where directory links work; FEATHER_LINK_TEST_DIR selects the volume."""
        parent = os.environ.get("FEATHER_LINK_TEST_DIR")
        if parent:
            os.makedirs(parent, exist_ok=True)
        # The canonical base keeps links above the temp directory out of tests that build their own.
        base = Path(os.path.realpath(tempfile.mkdtemp(prefix="link-", dir=parent or None)))
        self.addCleanup(remove_link_base, base)
        if require_strict_realpath:
            try:
                os.path.realpath(base, strict=True)
            except OSError:
                self.skipTest("strict realpath unsupported")
        self.root = base
        self.project = base / "project"
        self.home = base / "claude-home"
        self.project.mkdir()
        self.home.mkdir()
        return base

    def test_linked_project_ancestor_is_resolved_once_and_reported(self):
        base = self.use_link_base()
        (base / "real" / "proj").mkdir(parents=True)
        make_directory_link(base / "alias", base / "real")
        self.project = base / "alias" / "proj"
        real_project = Path(os.path.realpath(base / "real" / "proj", strict=True))
        result = self.apply("install")
        self.assertEqual(result["resolved_paths"]["project"], str(real_project))
        self.assertTrue(result["changes"])
        for change in result["changes"]:
            self.assertTrue(Path(change["path"]).is_relative_to(real_project), change["path"])
        self.assertTrue((real_project / ".claude" / "agents" / "scout.md").exists())
        code, shown = self.call("check")
        self.assertEqual((code, shown["status"]), (0, "ok"), shown)
        self.assertEqual(shown["paths"]["guidance"], str(real_project / "CLAUDE.md"))
        self.apply("remove")
        self.assertFalse((real_project / ".claude" / "agents" / "scout.md").exists())

    def test_claude_home_under_a_linked_ancestor_installs_user_scope(self):
        base = self.use_link_base()
        (base / "real-config").mkdir()
        make_directory_link(base / "config-link", base / "real-config")
        self.home = base / "config-link" / "claude"
        real_home = Path(os.path.realpath(base / "real-config", strict=True)) / "claude"
        result = self.apply("install", "user")
        self.assertEqual(result["resolved_paths"]["claude_home"], str(real_home))
        self.assertTrue((real_home / "agents" / "scout.md").exists())
        self.assertTrue((real_home / "CLAUDE.md").exists())
        self.assertEqual(self.call("check", "user")[1]["status"], "ok")
        self.apply("remove", "user")
        self.assertFalse((real_home / "CLAUDE.md").exists())

    def test_links_below_the_roots_are_refused(self):
        base = self.use_link_base()
        (base / "elsewhere").mkdir()
        make_directory_link(self.project / ".claude", base / "elsewhere")
        make_directory_link(self.home / "cc-feather", base / "elsewhere")
        for command in (("install", "project"), ("remove", "project"), ("install", "user")):
            with self.subTest(command=command):
                before = self.files()
                code, result = self.call(*command)
                self.assertEqual(code, 2, result)
                self.assertIn("linked path is unsafe", result["error"])
                self.assertEqual(before, self.files())
        self.assertEqual(list((base / "elsewhere").iterdir()), [])

    def test_root_changed_after_resolution_is_refused(self):
        base = self.use_link_base()
        real_project = os.path.realpath(self.project, strict=True)
        original = os.path.realpath
        other = base / "other"
        other.mkdir()

        def swapped(path, *, strict=False):
            # Every later check of the root sees another directory.
            if not strict and os.path.normcase(os.fspath(path)) == os.path.normcase(real_project):
                return original(other, strict=strict)
            return original(path, strict=strict)

        resolutions = []

        def moving(path, *, strict=False):
            # A second resolution of the project in the same invocation reaches another directory.
            if strict and os.path.normcase(os.path.abspath(path)) == os.path.normcase(os.path.abspath(self.project)):
                resolutions.append(path)
                if len(resolutions) > 1:
                    return original(other, strict=strict)
            return original(path, strict=strict)

        for name, fake in (("checked root", swapped), ("resolved again", moving)):
            with self.subTest(case=name), mock.patch("os.path.realpath", side_effect=fake):
                before = self.files()
                code, result = self.call("install")
                self.assertEqual(code, 2, result)
                self.assertIn("configuration root changed after it was resolved", result["error"])
                self.assertEqual(before, self.files())

    def test_repointed_ancestor_link_between_preview_and_apply_writes_nothing(self):
        base = self.use_link_base()
        for name in ("one", "two"):
            (base / name / "proj").mkdir(parents=True)
            (base / name / "proj" / "CLAUDE.md").write_text("Same rules\n", encoding="utf-8")
        link = base / "current"
        make_directory_link(link, base / "one")
        self.project = link / "proj"
        code, preview = self.call("install")
        self.assertEqual(code, 0, preview)
        trees = {name: self.files(base / name) for name in ("one", "two")}
        remove_directory_link(link)
        make_directory_link(link, base / "two")
        code, result = self.call("install", "project", "--apply", "--expected-plan", preview["plan_id"])
        self.assertEqual(code, 2, result)
        self.assertTrue(any(text in result["error"] for text in
                            ("matching", "plan became stale", "configuration root changed")), result)
        for name in ("one", "two"):
            self.assertEqual(self.files(base / name), trees[name], name)

    def test_unsupported_strict_realpath_keeps_full_ancestor_checks(self):
        base = self.use_link_base(require_strict_realpath=False)
        (base / "real" / "proj").mkdir(parents=True)
        make_directory_link(base / "alias", base / "real")
        original = os.path.realpath

        def unsupported(path, *, strict=False):
            if strict:
                raise OSError(errno.EINVAL, "Incorrect function", os.fspath(path))
            return original(path, strict=strict)

        with mock.patch("os.path.realpath", side_effect=unsupported):
            self.project = base / "alias" / "proj"
            before = self.files()
            code, result = self.call("install")
            self.assertEqual(code, 2, result)
            self.assertIn("linked path is unsafe", result["error"])
            self.assertEqual(before, self.files())
            self.project = base / "real" / "proj"
            result = self.apply("install")
            self.assertNotIn("resolved_paths", result)
            self.assertEqual(self.call("check")[1]["status"], "ok")
            self.apply("remove")

    def test_dangling_link_in_a_missing_claude_home_is_refused(self):
        base = self.use_link_base()
        gone = base / "gone"
        gone.mkdir()
        make_directory_link(base / "dangling", gone)
        gone.rmdir()
        self.home = base / "dangling" / "claude"

        def entries():
            # os.walk lists what pathlib's rglob would fail on; POSIX puts a dangling symlink among the files,
            # so record where a link points instead of reading through it.
            found = {}
            for current, directories, files in os.walk(base):
                found.update({Path(current) / name: None for name in directories})
                found.update({Path(current) / name: ("link", os.readlink(Path(current) / name))
                              if os.path.islink(Path(current) / name) else (Path(current) / name).read_bytes()
                              for name in files})
            return found

        before = entries()
        with self.subTest(command=("install", "user")):
            code, result = self.call("install", "user")
            self.assertEqual(code, 2, result)
            self.assertIn("linked path is unsafe", result["error"])
            self.assertEqual(before, entries())
        with self.subTest(command=("install", "project")):
            # Project scope never writes the Claude home, so the home's dangling link does not block it.
            outside = lambda found: {path: data for path, data in found.items() if not path.is_relative_to(self.project)}
            self.apply("install", "project")
            self.assertTrue((self.project / ".claude" / "agents" / "scout.md").exists())
            self.assertEqual(self.call("check")[0], 0)
            self.apply("remove", "project")
            self.assertEqual(outside(before), outside(entries()))
        self.assertFalse(os.path.exists(base / "dangling"))

    def test_dangling_claude_home_link_to_the_project_claude_directory_is_the_user_configuration(self):
        base = self.use_link_base()
        target = self.project / ".claude"
        target.mkdir()
        make_directory_link(base / "dangling", target)
        target.rmdir()
        # The unresolvable home is compared at its supplied path, which still leads to the project's .claude.
        self.home = base / "dangling"
        code, result = self.call("install", "project")
        self.assertEqual(code, 2, result)
        self.assertIn("project scope here would write the user configuration", result["error"])
        self.assertFalse(os.path.lexists(target))

    def test_linked_project_reading_different_agents_files_requires_a_choice(self):
        base = self.use_link_base()
        found = [directory / name for directory in base.parents for name in
                 ("CLAUDE.md", ".claude/CLAUDE.md", "CLAUDE.local.md", "AGENTS.md", ".claude/AGENTS.md")
                 if (directory / name).exists()]
        if found:
            self.skipTest(f"an ancestor instruction file changes this layout: {found[0]}")
        (base / "outer").mkdir()
        (base / "target" / "proj").mkdir(parents=True)
        make_directory_link(base / "outer" / "link", base / "target")
        outer_agents = base / "outer" / "AGENTS.md"
        outer_agents.write_text("Outer rules\n", encoding="utf-8")
        self.project = base / "outer" / "link" / "proj"
        real_project = os.path.realpath(base / "target" / "proj", strict=True)
        before = self.files()
        code, result = self.call("install")
        self.assertEqual(code, 2, result)
        self.assertIn("guidance target choice required", result["error"])
        self.assertIn(f"through {self.project}: AGENTS files {outer_agents}", result["error"])
        self.assertIn(f"through {real_project}: AGENTS files none", result["error"])
        self.assertEqual(before, self.files())
        self.assertTrue(self.call("show")[1]["guidance_choice_required"])
        self.apply("install", "project", "--guidance", "claude")
        self.assertTrue((Path(real_project) / "CLAUDE.md").read_text(encoding="utf-8").startswith(config.BEGIN))

    def test_linked_project_choice_offers_agents_only_with_a_project_agents_file(self):
        base = self.use_link_base()
        found = [directory / name for directory in base.parents for name in
                 ("CLAUDE.md", ".claude/CLAUDE.md", "CLAUDE.local.md", "AGENTS.md", ".claude/AGENTS.md")
                 if (directory / name).exists()]
        if found:
            self.skipTest(f"an ancestor instruction file changes this layout: {found[0]}")
        (base / "outer").mkdir()
        (base / "target" / "proj").mkdir(parents=True)
        make_directory_link(base / "outer" / "link", base / "target")
        (base / "outer" / "AGENTS.md").write_text("Outer rules\n", encoding="utf-8")
        self.project = base / "outer" / "link" / "proj"
        for own, offered in ((False, False), (True, True)):
            with self.subTest(own=own):
                if own:
                    (base / "target" / "proj" / "AGENTS.md").write_text("Team rules\n", encoding="utf-8")
                before = self.files()
                code, result = self.call("install")
                self.assertEqual(code, 2, result)
                self.assertIn("Claude reads different instruction files through each", result["error"])
                self.assertIn("--guidance claude", result["error"])
                self.assertEqual("--guidance agents" in result["error"], offered, result["error"])
                self.assertEqual(before, self.files())

    # DX1: only the top-level name of an agent's frontmatter is its name.

    def other_agent(self, text, name="notes.md"):
        """Another agent's file in a subdirectory of the project agents tree."""
        path = self.project / ".claude" / "agents" / "mine" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))
        return path

    def use_case(self, name):
        self.project = self.root / name
        self.project.mkdir()

    def assert_other_agent_ignored(self, text):
        path = self.other_agent(text)
        code, shown = self.call("check")
        self.assertEqual((code, shown["status"], shown["pending_role_prefix"]), (0, "ok", None), shown)
        self.apply("install")
        self.assert_all_unprefixed_roles()
        self.apply("remove")
        self.assertEqual(path.read_bytes(), text.encode("utf-8"))

    def assert_other_agent_named(self, text):
        self.other_agent(text)
        code, shown = self.call("check")
        self.assertEqual((code, shown["status"], shown["pending_role_prefix"]), (0, "ok", config.ROLE_PREFIX), shown)
        self.apply("install")
        self.assert_prefixed_roles(self.project / ".claude" / "agents")

    def assert_other_agent_uninspectable(self, text, error="cannot inspect agent name syntax"):
        self.other_agent(text)
        before = self.files()
        code, result = self.call("install")
        self.assertEqual(code, 2, result)
        self.assertIn(error, result["error"])
        self.assertEqual(before, self.files())

    def test_nested_mapping_name_is_not_the_agent_name(self):
        for index, text in enumerate(("---\nname: mine\nmetadata:\n  name: verifier\n---\nMine\n",
                                      "---\nname: mine\nskills:\n-\n  name: verifier\n---\nMine\n")):
            with self.subTest(text=text):
                self.use_case(f"nested-{index}")
                self.assert_other_agent_ignored(text)

    def test_block_scalar_text_is_not_the_agent_name(self):
        for index, text in enumerate(("---\nname: mine\ndescription: |\n  name: scout\n---\nMine\n",
                                      "---\ndescription: >-\n  name: scout\n---\nMine\n")):
            with self.subTest(text=text):
                self.use_case(f"block-{index}")
                self.assert_other_agent_ignored(text)

    def test_uniformly_indented_header_declares_its_name(self):
        for index, text in enumerate(("---\n  name: scout\n  description: Mine\n---\nMine\n",
                                      "---\n  name: scout\n  metadata:\n    name: other\n---\nMine\n")):
            with self.subTest(text=text):
                self.use_case(f"indented-{index}")
                self.assert_other_agent_named(text)

    def test_multi_line_flow_mapping_header_is_uninspectable(self):
        self.assert_other_agent_uninspectable("---\n{\n  name: verifier\n}\n---\nMine\n")

    def test_merge_key_header_is_uninspectable(self):
        # YAML merges the anchored mapping into the top level, so verifier would become the name.
        self.assert_other_agent_uninspectable("---\nbase: &base\n  name: verifier\n<<: *base\ndescription: Mine\n---\nMine\n")

    def test_tab_indented_header_line_is_uninspectable(self):
        for index, text in enumerate(("---\n\tname: verifier\n---\nMine\n",
                                      "---\nname: mine\nmetadata:\n\tname: verifier\n---\nMine\n",
                                      "---\nname: mine\n \t# note\n---\nMine\n")):
            with self.subTest(text=text):
                self.use_case(f"tab-{index}")
                self.assert_other_agent_uninspectable(text)

    def test_other_line_breaks_in_a_header_are_uninspectable(self):
        for index, character in enumerate(("\u2028", "\u2029", "\x85", "\x0b", "\x0c", "\x1c", "\x1e", "\ufeff")):
            with self.subTest(character=hex(ord(character))):
                self.use_case(f"break-{index}")
                self.assert_other_agent_uninspectable(f"---\n# note{character}name: verifier\n---\nMine\n")

    def test_duplicate_top_level_name_still_blocks(self):
        self.assert_other_agent_uninspectable("---\nname: mine\nmetadata:\n  name: other\nname: scout\n---\nMine\n",
                                              "duplicate agent name declaration")

    def test_compact_sequences_are_values_not_top_level_keys(self):
        for index, text in enumerate(("---\nname: mine\ntools:\n- Read\n- Grep\n---\nMine\n",
                                      "---\nname: mine\nskills:\n- name: verifier\n  description: Theirs\n- name: scout\n---\nMine\n",
                                      "---\nname: mine\ntools: # listed below\n\n- Read\n---\nMine\n")):
            with self.subTest(text=text):
                self.use_case(f"sequence-{index}")
                self.assert_other_agent_ignored(text)

    def test_sequence_entry_without_its_key_is_uninspectable(self):
        for index, text in enumerate(("---\n- x\n---\nMine\n", "---\n- name: verifier\n---\nMine\n",
                                      "---\nname: mine\ndescription: Mine\n- name: verifier\n---\nMine\n",
                                      "---\nname: mine\ntools:\n  x: 1\n- name: verifier\n---\nMine\n")):
            with self.subTest(text=text):
                self.use_case(f"entry-{index}")
                self.assert_other_agent_uninspectable(text)

    # DX2: the frontmatter ends at the first "---" after its opening line, as Claude Code reads it.

    def test_frontmatter_closed_at_the_end_of_the_file_is_read(self):
        self.assert_other_agent_ignored("---\nname: mine\ndescription: x\n---")
        self.use_case("closed-at-eof")
        self.assert_other_agent_named("---\nname: scout\ndescription: x\n---")

    def test_markdown_opening_with_a_rule_is_not_an_agent(self):
        path = self.other_agent("---\n\nNotes\n", "README.md")
        warning = f"Agent file has no closing frontmatter line: {path}; it was not read as an agent"
        code, shown = self.call("check")
        self.assertEqual((code, shown["status"], shown["pending_role_prefix"]), (0, "ok", None), shown)
        self.assertIn(warning, shown["warnings"])
        code, preview = self.call("install")
        self.assertEqual(code, 0, preview)
        self.assertIn(warning, preview["warnings"])
        self.apply("install")
        self.assert_all_unprefixed_roles()

    def test_plain_text_between_rules_is_not_an_agent(self):
        # Notes framed by horizontal rules are a YAML scalar, not a mapping, as before the name rules changed.
        self.assert_other_agent_ignored("---\nSome notes here\n---\nBody")

    def test_plain_text_between_rules_is_named_in_the_warnings(self):
        path = self.other_agent("---\nSome notes here\n---\nBody", "README.md")
        warning = f"Agent file frontmatter declares no agent name: {path}; it was not read as an agent"
        self.assertIn(warning, self.call("check")[1]["warnings"])
        code, preview = self.call("install")
        self.assertEqual(code, 0, preview)
        self.assertIn(warning, preview["warnings"])

    def test_plain_text_beside_a_key_or_flow_mapping_is_uninspectable(self):
        for index, text in enumerate(("---\nname: mine\nSome text\n---\n", "---\n{name: verifier}\n---\n")):
            with self.subTest(text=text):
                self.use_case(f"mixed-{index}")
                self.assert_other_agent_uninspectable(text)

    def test_ambiguous_closing_frontmatter_line_is_uninspectable(self):
        for index, text in enumerate(("---\nname: scout\n----\nMine\n", "---\nname: scout\n--- end\nMine\n",
                                      "---\nname: executor---x\n---\nMine\n",
                                      "---\nname: mine\ndescription: a --- b\n---\nMine\n")):
            with self.subTest(text=text):
                self.use_case(f"closing-{index}")
                self.assert_other_agent_uninspectable(text, "ambiguous closing frontmatter line")

    def test_opening_line_with_trailing_whitespace_opens_frontmatter(self):
        for index, text in enumerate(("---  \nname: scout\n---\nMine\n", "---\t\nname: scout\n---\nMine\n",
                                      "---\r\nname: scout\r\n---\r\nMine\r\n")):
            with self.subTest(text=text):
                self.use_case(f"opening-{index}")
                self.assert_other_agent_named(text)

    # DX3: managed blocks follow the instruction file's line endings, and ownership ignores them.

    def assert_crlf_only(self, data):
        self.assertIsNone(re.search(rb"(?<!\r)\n", data), data)

    def assert_normalized_block_hashes(self, guidance, components=("handoff", "delegation")):
        text = guidance.read_bytes().decode("utf-8")
        markers = {"handoff": (config.HANDOFF_BEGIN, config.HANDOFF_END), "delegation": (config.BEGIN, config.END)}
        recorded = self.saved_state()["components"]
        for name in components:
            block = config._block_parts(text, *markers[name])[1]
            self.assertEqual(recorded[name]["block_hash"], config.digest(block.replace("\r\n", "\n").encode("utf-8")), name)

    def test_install_into_crlf_guidance_writes_crlf_blocks(self):
        guidance = self.project / "CLAUDE.md"
        guidance.write_bytes(b"User rules\r\nlast line")
        self.apply("install", "project", "--component", "both")
        self.assert_crlf_only(guidance.read_bytes())
        self.assert_normalized_block_hashes(guidance)
        self.assertEqual(self.call("check")[1]["status"], "ok")
        # A later conversion of the whole file to LF keeps the installation owned.
        guidance.write_bytes(guidance.read_bytes().replace(b"\r\n", b"\n"))
        code, shown = self.call("check")
        self.assertEqual((code, shown["status"]), (0, "ok"), shown)
        self.apply("review", "project", "--review-mode", "auto")
        self.apply("update", "project", "--component", "both")
        self.assertNotIn(b"\r", guidance.read_bytes())
        self.apply("remove", "project", "--component", "both")
        self.assertEqual(guidance.read_bytes(), b"User rules\nlast line")

    def test_lf_guidance_converted_to_crlf_stays_owned(self):
        guidance = self.project / "CLAUDE.md"
        guidance.write_bytes(b"User rules\n")
        self.apply("install", "project", "--component", "both")
        guidance.write_bytes(guidance.read_bytes().replace(b"\n", b"\r\n"))
        code, shown = self.call("check")
        self.assertEqual((code, shown["status"]), (0, "ok"), shown)
        self.apply("model", "project", "--set", "scout.effort=medium")
        self.assert_normalized_block_hashes(guidance, ("delegation",))
        self.apply("review", "project", "--review-mode", "auto")
        self.apply("update", "project", "--component", "both")
        self.assert_crlf_only(guidance.read_bytes())
        self.assert_normalized_block_hashes(guidance)
        self.apply("remove", "project", "--component", "both")
        self.assertEqual(guidance.read_bytes(), b"User rules\r\n")

    def test_block_hash_recorded_from_a_crlf_block_is_still_accepted(self):
        self.apply("install", "project", "--review-mode", "auto")
        guidance = self.project / "CLAUDE.md"
        block = config._block_parts(guidance.read_bytes().decode("utf-8"))[1]
        # The earlier review path recorded the raw digest of a block it kept in CRLF.
        self.replace_delegation_block(guidance, block.replace("\n", "\r\n"))
        self.assertEqual(self.call("check")[1]["status"], "ok")
        guidance.write_bytes(guidance.read_bytes().replace(b"\r\n", b"\n"))
        code, shown = self.call("check")
        self.assertEqual((code, shown["status"]), (0, "ok"), shown)
        self.apply("review", "project", "--review-mode", "off")
        self.assert_normalized_block_hashes(guidance, ("delegation",))
        self.apply("remove")
        self.assertFalse(guidance.exists())

    def test_guidance_template_with_a_bare_carriage_return_is_refused(self):
        fixture = self.root / "package"
        shutil.copytree(config.ROOT / "templates", fixture / "templates")
        for template, extra in (("handoff.md", ("--component", "handoff")), ("CLAUDE.md", ()),
                                ("review-auto.md", ("--review-mode", "auto"))):
            with self.subTest(template=template):
                path = fixture / "templates" / template
                original = path.read_bytes()
                path.write_bytes(original.replace(b"\r\n", b"\n").replace(b"\n", b"\r \n", 1))
                before = self.files()
                with mock.patch.object(config, "ROOT", fixture):
                    code, result = self.call("install", "project", *extra)
                self.assertEqual(code, 2, result)
                self.assertIn("bare carriage return", result["error"])
                self.assertEqual(before, self.files())
                path.write_bytes(original)

    # DX4: only name-surrogate reparse points are links; cloud placeholders and similar entries are not.

    def reparse(self, target, *, lstat_tag=None, listed_tag=None, listed=True):
        """Report target as a reparse point to lstat (with lstat_tag) and its parent listing (with listed_tag).

        CPython's lstat traverses a non-surrogate reparse point and reports tag 0, while the directory
        listing keeps the tag. None leaves that source unchanged; listed=False omits the entry.
        """
        real_lstat, real_scandir = Path.lstat, os.scandir
        same = lambda path: os.path.normcase(os.fspath(path)) == os.path.normcase(os.fspath(target))

        def reparse_point(info, tag):
            return types.SimpleNamespace(st_mode=info.st_mode, st_nlink=info.st_nlink, st_reparse_tag=tag,
                                         st_file_attributes=getattr(info, "st_file_attributes", 0) | 0x400)

        def lstat(path):
            info = real_lstat(path)
            return reparse_point(info, lstat_tag) if lstat_tag is not None and same(path) else info

        class Entry:
            def __init__(self, entry):
                self.entry, self.name, self.path = entry, entry.name, entry.path

            def stat(self, *, follow_symlinks=True):
                info = self.entry.stat(follow_symlinks=follow_symlinks)
                return info if follow_symlinks else reparse_point(info, listed_tag)

        @contextlib.contextmanager
        def scandir(path):
            with real_scandir(path) as entries:
                listing = []
                for entry in entries:
                    if not same(entry.path):
                        listing.append(entry)
                    elif listed:
                        listing.append(entry if listed_tag is None else Entry(entry))
                yield iter(listing)

        stack = contextlib.ExitStack()
        stack.enter_context(mock.patch.object(Path, "lstat", autospec=True, side_effect=lstat))
        stack.enter_context(mock.patch("os.scandir", scandir))
        return stack

    def test_reparse_point_with_a_listed_non_surrogate_tag_is_an_ordinary_file(self):
        guidance = self.project / "CLAUDE.md"
        guidance.write_bytes(b"User rules\n")
        # A cloud placeholder: lstat traversed it, the listing reports IO_REPARSE_TAG_CLOUD_6.
        with self.reparse(guidance, lstat_tag=0, listed_tag=0x9000601A):
            self.apply("install")
            code, shown = self.call("check")
        self.assertEqual((code, shown["status"]), (0, "ok"), shown)
        self.assertTrue(guidance.read_text(encoding="utf-8").startswith("User rules\n" + config.BEGIN))

    def test_non_surrogate_tag_reported_by_lstat_is_an_ordinary_file(self):
        guidance = self.project / "CLAUDE.md"
        guidance.write_bytes(b"User rules\n")
        # IO_REPARSE_TAG_DEDUP, reported by lstat itself.
        with self.reparse(guidance, lstat_tag=0x80000013):
            self.apply("install")
        self.assertIn(config.BEGIN, guidance.read_text(encoding="utf-8"))

    def test_reparse_point_without_a_known_non_surrogate_tag_is_refused(self):
        guidance = self.project / "CLAUDE.md"
        guidance.write_bytes(b"User rules\n")
        cases = (("listed without a tag", {"lstat_tag": 0, "listed_tag": 0}),
                 ("missing from the listing", {"lstat_tag": 0, "listed": False}),
                 ("junction", {"lstat_tag": 0xA0000003}), ("symlink", {"lstat_tag": 0xA000000C}))
        for name, options in cases:
            with self.subTest(case=name):
                before = self.files()
                with self.reparse(guidance, **options):
                    code, result = self.call("install")
                self.assertEqual(code, 2, result)
                self.assertIn("linked path is unsafe", result["error"])
                self.assertEqual(before, self.files())

    def test_agents_tree_takes_reparse_tags_from_its_listing(self):
        mine = self.other_agent("---\nname: scout\n---\nMine\n", "scout.md")
        with self.reparse(mine, lstat_tag=0, listed_tag=0x9000601A):
            code, shown = self.call("check")
        self.assertEqual((code, shown["status"], shown["pending_role_prefix"]), (0, "ok", config.ROLE_PREFIX), shown)
        for name, tag in (("junction", 0xA0000003), ("no tag", 0)):
            with self.subTest(case=name):
                with self.reparse(mine, lstat_tag=tag, listed_tag=tag):
                    code, shown = self.call("check")
                self.assertEqual((code, shown["status"]), (2, "conflict"), shown)
                self.assertIn(f"linked agents tree entry cannot be inspected: {mine}", shown["issues"])

    def test_junction_in_the_agents_tree_is_refused(self):
        base = self.use_link_base()
        (base / "elsewhere").mkdir()
        agents = self.project / ".claude" / "agents"
        agents.mkdir(parents=True)
        make_directory_link(agents / "linked", base / "elsewhere")
        before = self.files()
        code, result = self.call("install")
        self.assertEqual(code, 2, result)
        self.assertIn(f"linked agents tree entry cannot be inspected: {agents / 'linked'}", result["error"])
        self.assertEqual(before, self.files())

    # DX5 and DX6: setup and review guidance say only what the tool and the flow do.

    def test_setup_never_offers_to_replace_another_agents_file(self):
        for path in (config.ROOT / "skills" / "setup" / "SKILL.md", config.ROOT / "docs" / "setup.md"):
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("replace it", text)
                self.assertNotIn("replacing it", text)
                self.assertIn("rerun setup", text)

    def test_explicit_reviews_are_outside_every_automatic_budget(self):
        rule = "Explicit calls do not count toward the automatic budget below"
        references = config.ROOT / "skills" / "delegation" / "references"
        for name in ("plan-review.md", "code-review.md", "outcome-verification.md"):
            with self.subTest(reference=name):
                self.assertIn(rule, (references / name).read_text(encoding="utf-8"))
        self.assertIn("an explicit call is outside the count",
                      (references / "plan-review.md").read_text(encoding="utf-8"))

    def test_every_step_counts_consecutive_failures_and_a_pass_resets(self):
        references = config.ROOT / "skills" / "delegation" / "references"
        for name in ("plan-review.md", "code-review.md", "outcome-verification.md"):
            text = (references / name).read_text(encoding="utf-8")
            for phrase in ("Count consecutive automatic calls without a pass", "resets the count to zero"):
                with self.subTest(reference=name, phrase=phrase):
                    self.assertIn(phrase, text)

    def test_a_fix_after_refuted_is_code_reviewed_before_the_recheck(self):
        references = config.ROOT / "skills" / "delegation" / "references"
        review = (references / "code-review.md").read_text(encoding="utf-8")
        verification = (references / "outcome-verification.md").read_text(encoding="utf-8")
        for text in (review, verification):
            self.assertNotIn("without another code review", text)
            self.assertNotIn("not code-reviewed", text)
        self.assertIn("A fix goes to [code review](code-review.md) first", verification)
        self.assertIn("resets only on an automatic CONFIRMED", verification)

    def test_an_explicit_verdict_never_changes_the_automatic_count(self):
        references = config.ROOT / "skills" / "delegation" / "references"
        for name in ("plan-review.md", "code-review.md", "outcome-verification.md"):
            text = (references / name).read_text(encoding="utf-8")
            for phrase in ("an explicit call's verdict", "does not change it"):
                with self.subTest(reference=name, phrase=phrase):
                    self.assertIn(phrase, text)

    def test_the_named_document_is_the_plan_and_its_tickets_are_its_claims(self):
        references = config.ROOT / "skills" / "delegation" / "references"
        plan_review = (references / "plan-review.md").read_text(encoding="utf-8")
        for phrase in ("The plan is what the user names",
                       "each unfinished ticket in the named scope is one claim",
                       "no plan in this session already covers the named work",
                       "keeps its count, verdicts and blockers",
                       "applies to that spec's tickets when they are named",
                       "Main does not edit a spec or ticket to add claims"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, plan_review)
        for name in ("code-review.md", "outcome-verification.md"):
            with self.subTest(reference=name):
                self.assertIn("as identified for the plan", (references / name).read_text(encoding="utf-8"))

    def test_a_plan_listing_no_claims_is_still_one_claim(self):
        references = config.ROOT / "skills" / "delegation" / "references"
        for name, phrase in (("plan-review.md", "lists none is one claim"), ("preview.md", "lists none is one Claim")):
            with self.subTest(reference=name):
                self.assertIn(phrase, (references / name).read_text(encoding="utf-8"))

    def test_a_preview_binds_only_its_session_and_flags_missing_parts(self):
        text = (config.ROOT / "skills" / "delegation" / "references" / "preview.md").read_text(encoding="utf-8")
        for phrase in ("only in the session that made it", "refers to its own tickets or Claims that cannot be found"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_tickets_are_looked_for_where_they_live_and_unresolved_references_are_asked(self):
        references = config.ROOT / "skills" / "delegation" / "references"
        plan_review = (references / "plan-review.md").read_text(encoding="utf-8")
        for phrase in ("the project's instructions, such as CLAUDE.md or AGENTS.md",
                       "an empty result is not evidence that none exist",
                       "can skip files that version control ignores",
                       "both ignored and hidden files included",
                       "keeps that list without asking",
                       "Unless the spec lists its own claims",
                       "before plan review or implementation whether to point to them"):
            with self.subTest(reference="plan-review.md", phrase=phrase):
                self.assertIn(phrase, plan_review)
        preview = (references / "preview.md").read_text(encoding="utf-8")
        for phrase in ("ignored directories included", "will ask before plan review or implementation"):
            with self.subTest(reference="preview.md", phrase=phrase):
                self.assertIn(phrase, preview)

    # Review state: one shared model, load-bearing rules, and documents that agree with the procedures.

    def test_review_procedures_cite_one_shared_state_model(self):
        references = config.ROOT / "skills" / "delegation" / "references"
        state = (references / "review-state.md").read_text(encoding="utf-8")
        for phrase in ("Work identity", "Reviewed content", "Call source", "Consecutive non-pass count",
                       "Valid verdict", "Blockers"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, state)
        for name in ("plan-review.md", "code-review.md", "outcome-verification.md"):
            with self.subTest(reference=name):
                self.assertIn("(review-state.md)", (references / name).read_text(encoding="utf-8"))

    def test_load_bearing_review_rules_stay_in_their_procedures(self):
        references = config.ROOT / "skills" / "delegation" / "references"
        rules = (
            ("plan-review.md", "partly overlaps one inherits its unresolved verdicts and blockers"),
            ("plan-review.md", "When every ticket in the named scope is finished, report that nothing is left to implement"),
            ("plan-review.md", "must agree with all of them"),
            ("plan-review.md", "a spec that refers to none is one claim without asking"),
            ("plan-review.md", "Main never approves such a plan itself"),
            ("plan-review.md", "If the in-session state is unknown"),
            ("code-review.md", "Its count continues from where it stands"),
            ("code-review.md", "do not land it on the default branch, release it or report it complete"),
            ("outcome-verification.md", "made before the automatic flow reached verification does not complete a claim of plan-driven work"),
        )
        for name, phrase in rules:
            with self.subTest(reference=name, phrase=phrase):
                self.assertIn(phrase, (references / name).read_text(encoding="utf-8"))

    def test_stops_recovery_and_counting_follow_the_review_state_rules(self):
        references = config.ROOT / "skills" / "delegation" / "references"
        expected = {
            references / "review-state.md": (
                "clears the stop and leaves the count unchanged",
                "needs the user's explicit request",
                "a pass resets the count and a non-pass stops the step again",
                "does not count as that step's pass",
                "automatic if the flow is due to run that step",
                "State the classification before dispatching",
                "including a generic retry after a temporary failure",
                "never dispatched again as a retry",
                "treat the step as stopped and ask the user",
                "does not start a new session",
                "State the current count with each review result",
                "gains no new automatic calls",
                "does not clear the inherited stop",
                "receives the inherited findings with their dispositions",
                "Independent new work is counted on its own",
                "counts of different plans are not added",
                "precondition failure, not a call",
                "not part of the request",
                "in auto the automatic flow continues to the next step",
                "explicit if the step has stopped or the request is outside the flow",
                "including a call the user requests for a step the flow is due to run",
            ),
            references / "plan-review.md": ("treat the step as stopped and ask the user",
                                            "its count and stop for them",
                                            "an explicit READY clears the stop"),
            references / "outcome-verification.md": ("made before the automatic flow reached verification",
                                                     "An explicit CONFIRMED that clears a verification step",
                                                     "makes the step stopped until the user decides"),
            references / "code-review.md": ("the automatic flow resumes",
                                            "after an explicit review outside a stopped automatic step",
                                            "makes the step stopped until the user decides",
                                            "a retry counts as a call"),
            config.ROOT / "skills" / "delegation" / "SKILL.md": ("the automatic flow resumes",
                                                                 "is never used on a stopped step"),
            config.ROOT / "CONTEXT.md": ("clears the stop without resetting the count",
                                         "the Automatic flow resumes from there",
                                         "is an automatic call, not an Explicit request"),
            config.ROOT / "README.md": ("the automatic flow resumes from there",
                                        "in auto the automatic flow continues to the next step"),
            config.ROOT / "README.zh-TW.md": ("自動流程會從那裡接續", "在 auto 下自動流程接著進入下一步"),
        }
        for path, phrases in expected.items():
            text = path.read_text(encoding="utf-8")
            for phrase in phrases:
                with self.subTest(path=path.name, phrase=phrase):
                    self.assertIn(phrase, text)
        # The 0.13.2 recovery rule let main guess at a lost state; it must not come back.
        for name in ("plan-review.md", "code-review.md", "outcome-verification.md"):
            with self.subTest(reference=name):
                self.assertNotIn("before another automatic call",
                                 (references / name).read_text(encoding="utf-8"))

    def test_passes_stay_valid_only_for_what_they_judged_and_gate_completion(self):
        references = config.ROOT / "skills" / "delegation" / "references"
        expected = {
            references / "review-state.md": (
                "A pass covers the work identity, its acceptance and the reviewed content",
                "reopens code review and outcome verification",
                "reopens outcome verification only",
                "states why it does not affect the pass",
                "Updating a ticket's status is not a relevant change",
                "continues the step's count from where it stands",
                "a reopened automatic call needs the user's explicit request",
                "an active handoff records as unreviewed, unverified or pending acceptance",
                "only with a valid APPROVED and a valid CONFIRMED",
                "push it to a branch main created for the current work",
                "labels each commit made before its claim's passes (both passes, plus HELD for a Security-critical claim) unaccepted",
                "Off mode otherwise keeps its behaviour",
                "is a postcondition",
                "checks and reports it after the operation",
                "in a step whose stop was cleared, a later call that step needs",
            ),
            references / "plan-review.md": ("after an explicit READY that cleared a stop", "never assume a count of zero"),
            references / "code-review.md": ("a reopened automatic call needs the user's explicit request",
                                            "In off, an explicit APPROVED is reported like any explicit review"),
            references / "outcome-verification.md": ("do not land it on the default branch, release it or report it complete",
                                                     "must not be landed on the default branch, released or reported complete",
                                                     "checks and reports it after the operation"),
            config.ROOT / "skills" / "delegation" / "SKILL.md": ("Reuse a verdict only while it is valid",
                                                                 "classify it as [review state]"),
            config.ROOT / "README.md": ("needs your request again", "does not count as that step's pass",
                                        "a pass resets the count and a non-pass stops the step again"),
            config.ROOT / "README.zh-TW.md": ("都需要你要求", "不算該步驟的通過", "仍需要你再要求"),
        }
        for path, phrases in expected.items():
            text = path.read_text(encoding="utf-8")
            for phrase in phrases:
                with self.subTest(path=path.name, phrase=phrase):
                    self.assertIn(phrase, text)
        entries = self.glossary_entries((config.ROOT / "CONTEXT.md").read_text(encoding="utf-8"))
        self.assertIn("Unverified claim", entries)
        self.assertIn("no currently valid CONFIRMED", entries["Unverified claim"])

    def test_ticket_status_and_user_decisions_follow_the_review_state_rules(self):
        references = config.ROOT / "skills" / "delegation" / "references"
        expected = {
            references / "review-state.md": (
                "sets its ticket's status to the completion value",
                "with a note naming the version or commit",
                "reports which tickets it considers done",
                "or the user says it is done",
                "without a defined value, main asks",
                "re-review, deferral, cancellation, changed acceptance, waiver or accept and land",
                "with its scope",
                "stays visible with its remaining risk",
                "never recorded as READY, APPROVED, CONFIRMED or HELD",
                "does not accept a known defect",
                "leaves their status alone",
                "equals one of the completion values that convention defines",
                "Re-review is another call, classified as above",
                "Deferral keeps the work, its blockers and any handoff note waiting",
                "Cancellation drops the work and its open findings",
                "Changed acceptance replaces the claim's acceptance and reopens its review and verification",
                "in the report and in any active handoff",
                "A waiver does not complete a claim the acceptance gate covers",
                "which is zero after an automatic pass",
            ),
            references / "plan-review.md": ("status equals a completion value the project's tracker convention defines",
                                            "as [review state](review-state.md) records it",
                                            "keeping any waiver visible"),
            references / "code-review.md": ("only as [review state](review-state.md)'s Pending acceptance describes", "a waiver stays visible in it"),
            references / "outcome-verification.md": ("only as [review state](review-state.md)'s Pending acceptance describes",
                                                     "a waiver stays visible in it"),
            config.ROOT / "skills" / "delegation" / "SKILL.md": ("update its ticket as [review state]",),
            config.ROOT / "README.md": ("never counts as READY, APPROVED, CONFIRMED or HELD", "does not accept a known defect",
                                        "or you say it is done", "one of the convention's completion values",
                                        "a waived claim the acceptance gate covers is landed on the default branch, released or reported complete only after a later pass"),
            config.ROOT / "README.zh-TW.md": ("絕不記為 READY、APPROVED、CONFIRMED 或 HELD", "不代表接受已知的缺陷", "或你說它已完成",
                                              "慣例定義的任一完成值", "受驗收把關約束的 claim 被豁免後，要等之後的審查或驗證通過"),
        }
        for path, phrases in expected.items():
            text = path.read_text(encoding="utf-8")
            for phrase in phrases:
                with self.subTest(path=path.name, phrase=phrase):
                    self.assertIn(phrase, text)

    def test_resumed_sessions_and_plan_changes_follow_the_review_state_rules(self):
        references = config.ROOT / "skills" / "delegation" / "references"
        expected = {
            references / "review-state.md": (
                "Counts and passing verdicts do not cross sessions",
                "reviews an unfinished plan again before implementing it",
                "does not redo tickets that are finished",
                "still restricts that ticket when the whole spec is named",
                "without an active handoff record, no restriction carries into a resumed session",
                "needs claims added, split or changed",
                "the user or the planning step decides",
                "only after the user authorises it",
                "keeping a mapping from old claims to new ones",
                "only from its original text, an available record of it or a version the user confirms",
                "without reverting changes already made",
                "keeps the work, its blockers and any handoff note waiting",
                "a waiver kept in that handoff counts as that record for the gate",
                "the unresolved blockers each carries",
                "Where a procedure waits for the user to decide",
                "A waiver accepts a named open finding or missing pass",
                "only after a later pass",
                "for done work",
            ),
            references / "plan-review.md": (
                "Passing verdicts do not cross sessions either",
                "still restricts that ticket when the whole spec is named",
                "without such a record no restriction carries over",
                "unless the user authorises a claim change",
                "or when the user asks",
                "is identified only from its original text, an available record or a version the user confirms",
                "is reported for the user or the planning step to decide",
                "or the user says it is done; without a defined value, ask",
                "unless the decision is a deferral",
                "or the user cancels the work, changes its acceptance or waives it",
            ),
            references / "code-review.md": ("so a deferral keeps it and a waiver stays visible in it",),
            references / "outcome-verification.md": ("so a deferral keeps it and a waiver stays visible in it",),
            config.ROOT / "README.md": (
                "Counts and passing verdicts do not carry over",
                "Without an active handoff record, no restriction carries over",
                "unless you authorise it",
                "keeping a mapping from old claims to new ones",
                "from its original text, an available record or a version you confirm",
                "only after a later pass",
                "a waiver stays recorded",
                "for done work",
                "with its scope",
                "and their unresolved blockers",
                "or you cancel the work, change its acceptance or waive it",
                "A deferral keeps the note and a waiver stays recorded in it",
            ),
            config.ROOT / "README.zh-TW.md": (
                "次數與通過的結論不會帶到新的 session",
                "沒有進行中的交接記錄時，不會有任何限制帶過去",
                "除非你授權",
                "保留新舊 claim 的對應",
                "依它的原文、現有紀錄或你確認過的版本",
                "才會進入預設 branch、release 或回報完成",
                "豁免也會繼續記在裡面",
                "表示已完成的完成值",
                "並註明範圍",
                "與尚未解決的阻擋事項",
                "或你取消工作、修改驗收或豁免為止",
                "延後時記錄保留",
            ),
        }
        for path, phrases in expected.items():
            text = path.read_text(encoding="utf-8")
            for phrase in phrases:
                with self.subTest(path=path.name, phrase=phrase):
                    self.assertIn(phrase, text)
        entries = self.glossary_entries((config.ROOT / "CONTEXT.md").read_text(encoding="utf-8"))
        # Claims at implementation ticket 01 replaced the 0.22.0 Plan definition with the named-Plan cases.
        self.assertIn("a named spec is one Claim unless it lists its own", entries["Plan"])
        self.assertNotIn("with its claims listed, its unfinished tickets in the named scope as claims, or else one claim",
                         entries["Plan"])
        self.assertIn("In auto, Unplanned work", entries["Unplanned work"])

    def test_adr_0006_records_the_review_state_decisions_and_amends_earlier_adrs(self):
        adr = config.ROOT / "docs" / "adr"
        decision = (adr / "0006-review-state-validity-and-completion.md").read_text(encoding="utf-8")
        for phrase in (
            "one state model", "without resetting its count", "states which before dispatching",
            "a generic retry included", "Unknown state is treated as stopped", "keeps that Plan's count and stop",
            "A pass covers only the content it judged", "labelled unaccepted", "as one of its postconditions",
            "completion value", "a waiver is never a pass", "Counts and passing verdicts do not cross sessions",
            "keeping the old-to-new mapping", "only from its original text",
            "only after the user authorises it", "without a defined value it reports instead",
            "where the project defines a completion value", "is not that step's pass",
            "does not accept a known defect", "never reported complete without a valid APPROVED and CONFIRMED",
            "the unresolved blockers each Claim carries",
            # Rejected options.
            "Fixed totals per Plan or Claim", "Reset the count on an explicit pass", "Trust passes across sessions",
            "Treat a generic retry as free", "Rebuild a conversation Plan from memory",
            "Widen automatic review to all unplanned work",
            # What it amends.
            "This amends ADR 0004's consequence", "this amends ADR 0005's statement",
            "ADR 0005's consequence that another checkout",
        ):
            with self.subTest(adr="0006", phrase=phrase):
                self.assertIn(phrase, decision)
        # Earlier ADRs keep their original text and gain a note pointing to the current rule.
        earlier = {
            "0004-consecutive-failure-review-budget.md": (
                "A Claim makes at most six automatic calls",
                "(Amended by ADR 0006: six is the bound of one uninterrupted completion attempt per Claim; "
                "reopened Claims and Material deviations add calls.)"),
            "0005-the-named-plan-and-its-tickets.md": (
                "never edits a spec or ticket to add Claims",
                "Another checkout without the tickets falls back to the spec's listed Claims or one Claim",
                "(Amended by ADR 0006: main edits a spec or ticket",
                "only after the user authorises it", "where the project defines a completion value",
                "(Amended by ADR 0006: another checkout"),
        }
        for name, phrases in earlier.items():
            text = (adr / name).read_text(encoding="utf-8")
            for phrase in phrases:
                with self.subTest(adr=name, phrase=phrase):
                    self.assertIn(phrase, text)

    def test_claim_change_authorisation_is_recorded_in_each_adr_place(self):
        # The authorisation rule must stay in the ADR 0005 note and in both places ADR 0006 states it.
        adr = config.ROOT / "docs" / "adr"
        earlier = (adr / "0005-the-named-plan-and-its-tickets.md").read_text(encoding="utf-8")
        decision = (adr / "0006-review-state-validity-and-completion.md").read_text(encoding="utf-8")
        note = next(line for line in earlier.splitlines() if line.startswith("(Amended by ADR 0006: main edits"))
        paragraph = next(block for block in decision.split("\n\n") if "Claim changes a review requires" in block)
        consequences = decision.split("## Consequences", 1)[1].split("\n## ", 1)[0]
        for place, text in (("ADR 0005 note", note), ("ADR 0006 decision", paragraph),
                            ("ADR 0006 consequences", consequences)):
            with self.subTest(place=place):
                self.assertIn("only after the user authorises it", text)

    # 0.15.0 sentences that had no guard of their own, pinned whole so no clause can drift silently.
    FOLLOW_UP_SENTENCES = {
        'plan-review.md step 1': (
            'Passing verdicts do not cross sessions either: in auto, a resumed session reviews an unfinished plan again before implementing it; in either mode, finished tickets are not redone, as [review state](review-state.md) describes.',
            'An unresolved verdict restricts a resumed session only when an active handoff records it; it then applies, in either mode, until a later call passes it or the user cancels the work, changes its acceptance or waives it. A re-review is another call and lifts it only by passing, and a deferral keeps it.',
            "In auto, a plan that is implemented, in part or whole, and has no plan-review state in this session is handled before any call as [review state](review-state.md)'s Implemented before plan review describes: main asks the user whether to run plan review first or go straight to code review with the missing READY waived.",
        ),
        'plan-review.md': (
            '4. On REVISE, a blocker that needs claims added, split or changed is reported for the user or the planning step to decide, as [review state](review-state.md) describes; it cannot be dispositioned FIX until the user authorises the claim change.',
        ),
        'review-state.md': (
            "- **Resumed sessions.** Counts and passing verdicts do not cross sessions. In auto, a resumed session reviews an unfinished plan again before implementing it; in either mode it does not redo tickets that are finished. In either mode, an unresolved verdict that an active handoff records for a spec's plan restricts that spec's tickets when they are named, and one recorded for a ticket's plan still restricts that ticket when the whole spec is named; without an active handoff record, no restriction carries into a resumed session. Before a gated operation, a claim needs valid passes from this session, so a claim that passed in an earlier session is reviewed and verified again, and a Security-critical claim gets Adversarial review again, counted as usual. Only a claim whose ticket was set to a done value after valid passes or an accept-and-land decision, with no relevant change since, is exempt and counts as accepted for landing and release, as is a claim whose pending-acceptance note records an accept-and-land decision that still holds; any other finished ticket is only not redone. For a plan with an implemented claim, Implemented before plan review comes first.",
            "After a claim has passed (both passes, plus HELD for a Security-critical claim) and is committed, and any postcondition holds, main sets its ticket's status to the completion value the project's tracker convention defines for done work, with a note naming the version or commit; after an accept-and-land decision it does the same, and the note also names the decision and its remaining risk.",
            'A postcondition that does not hold leaves the claim incomplete and its ticket unfinished, with the observed state noted.',
        ),
        'SKILL.md': (
            'After a claim passes and is committed, and any postcondition holds, update its ticket as [review state](references/review-state.md) describes.',
        ),
    }

    def test_follow_up_sentences_from_0_15_0_are_stated_whole(self):
        references = config.ROOT / "skills" / "delegation" / "references"
        plan_review = (references / "plan-review.md").read_text(encoding="utf-8")
        texts = {"plan-review.md step 1": next(line for line in plan_review.splitlines()
                                               if line.startswith("1. Identify the logical plan")),
                 "plan-review.md": plan_review,
                 "review-state.md": (references / "review-state.md").read_text(encoding="utf-8"),
                 "SKILL.md": (config.ROOT / "skills" / "delegation" / "SKILL.md").read_text(encoding="utf-8")}
        for name, sentences in self.FOLLOW_UP_SENTENCES.items():
            text = texts[name]
            for sentence in sentences:
                with self.subTest(path=name, sentence=sentence[:60]):
                    self.assertIn(sentence, text)
        english = dict(self.readme_rule_bullets((config.ROOT / "README.md").read_text(encoding="utf-8"),
                                                "## Roles and routing", "### Automatic review switch"))
        chinese = dict(self.readme_rule_bullets((config.ROOT / "README.zh-TW.md").read_text(encoding="utf-8"),
                                                "## 分派與預設模型", "### 自動審查開關"))
        self.assertIn('Plan review first is an automatic call that covers the whole plan; going straight to code review records the missing READY as a waiver for the implemented claims.',
                      english["Implemented before plan review"])
        self.assertIn('先補計畫審查算一次自動呼叫，審查整份計畫；直接做程式碼審查則把缺少的 READY 記為已實作 claim 的豁免。',
                      chinese["實作完才做計畫審查"])

    # Whole sentences, so that removing or rewording any clause of the acceptance gate fails the suite.
    ACCEPTANCE_GATE_SENTENCES = {
        'review-state.md': (
            'For a claim the acceptance gate covers, that change is the commit named in the brief, judged with a clean workspace, as What a gated pass judged describes.',
            "- **Commit and completion.** For a claim of plan-driven work in the automatic flow, and for any claim an active handoff records as unreviewed, unverified or pending acceptance, main lands the claim on the remote default branch (by pushing it there or merging it, directly or through a pull request), releases or tags it, reports it complete or sets its ticket to a done value only with a valid APPROVED and a valid CONFIRMED, and for a Security-critical claim a valid HELD as well, or with the user's accept-and-land decision for it. This is the acceptance gate. It covers the completion value for done work; a value for work that will not be done is set only on the user's recorded cancellation and never counts as acceptance. Landing a branch lands every claim on it, so it waits for every gated claim there. A cancelled claim's commits that remain on a branch are listed as unaccepted, in the report and in any active handoff, until the user decides their disposition: reverted with a new commit, kept off the default branch, or accepted and landed; landing a branch that carries them waits for that decision. The default branch is the branch the `origin` remote's HEAD names, or the only remote's HEAD when there is no `origin`; with no remote, several remotes and no `origin`, or no HEAD, main asks. A protected or shared branch the user names counts as a default branch.",
            "- **Commits before the passes.** Before its passes, main may commit a claim of plan-driven work in the automatic flow on any branch, push it to a branch main created for the current work and open a pull request whose description lists the claims still unaccepted, without the user's permission, and keeps that list current as claims pass or are accepted. Before pushing to a remote branch that already existed and that main did not create, it asks the user; in a resumed session main treats a branch as its own only when an active handoff records that main created it for this work, and otherwise asks. For a claim the gate covers only because an active handoff records it, main may make the local commit a gated call needs without asking, while pushes and pull requests follow off-mode behaviour, so main asks. Before dispatching a gated code review, outcome verification or Adversarial review, main ensures the claim's content is committed and the precondition of What a gated pass judged holds; when a commit is needed, the authority above permits it without asking, and an already suitable commit needs no new one. It never rewrites pushed history, so a fix is a new commit. On a default branch, main labels each commit made before its claim's passes (both passes, plus HELD for a Security-critical claim) unaccepted in its message when it creates it; the label records the commit's state then and stays in history. Commits on other branches carry no label. It pushes such commits to the remote default branch only after both passes, plus a valid HELD for a Security-critical claim, or the user's accept-and-land decision for their claim, or as a work-in-progress push the user explicitly allows, and while they stay unpushed it says a reclaimed environment would lose them. Off mode otherwise keeps its behaviour.",
            "- **What a gated pass judged.** For a claim the acceptance gate covers, main dispatches a code review, outcome verification or Adversarial review only when the workspace equals the commit it names in the brief: HEAD is that commit, nothing the claim's files or acceptance checks depend on has an uncommitted or untracked change, and nothing changes the workspace during the call. An Adversarial review that can count as the step's pass also needs a valid APPROVED and a valid CONFIRMED at that same commit, so it follows them, as [adversarial review](adversarial-review.md) describes; an explicit one the user requests before them runs but does not count. The pass covers that commit, and a second review after a completed review receives the range from the previously judged commit to the new one, as Completed calls and coverage describes. A call for work the gate does not cover, such as an explicit review of unplanned edits or of work in off that no active handoff restricts, judges the workspace change from the base revision, except that an Adversarial review run through [the adversarial-review command](../../adversarial-review/SKILL.md) reviews the range that command defines, and main does not commit that work to review it.",
            '- **Existing handoff notes.** An active handoff\'s record that a claim is unreviewed, unverified or pending acceptance restricts it under the acceptance gate whatever its wording, such as "must not be committed"; main updates the wording at the next handoff maintenance.',
            'A waiver does not complete a claim the acceptance gate covers: such a claim is landed on the default branch, released or reported complete only after a later pass or an accept-and-land decision.',
            'For a claim an active handoff recorded as unreviewed, unverified or pending acceptance, a waiver kept in that handoff counts as that record for the gate.',
            "Separately, a work-in-progress push the user allows may move a gated claim's commits to the default branch, labelled as under Commits before the passes; it satisfies neither release nor completion.",
            'Before a gated operation, a claim needs valid passes from this session, so a claim that passed in an earlier session is reviewed and verified again, and a Security-critical claim gets Adversarial review again, counted as usual. Only a claim whose ticket was set to a done value after valid passes or an accept-and-land decision, with no relevant change since, is exempt and counts as accepted for landing and release, as is a claim whose pending-acceptance note records an accept-and-land decision that still holds; any other finished ticket is only not redone.',
        ),
        'code-review.md': (
            "while [review state](review-state.md)'s acceptance gate still covers, in either mode, a claim an active handoff records as unreviewed, unverified or pending acceptance, and the handoff note changes after a pass as [review state](review-state.md)'s Pending acceptance describes in either mode;",
            'For a claim the acceptance gate covers, also name the commit under review and dispatch only with a clean workspace at that commit, as [review state](review-state.md) describes.',
            "and, for a claim the acceptance gate covers, the range from the previously judged commit to the new one; when the previous call did not complete, supply instead the full range from the claim's base revision with earlier and partial findings as evidence.",
            'do not land it on the default branch, release it or report it complete, report its open findings',
            'record as plain text that the claim is unreviewed, its open findings and that it must not be landed on the default branch, released or reported complete.',
        ),
        'outcome-verification.md': (
            'For a claim the acceptance gate covers, also name the base revision and the commit under verification, and dispatch only with a clean workspace at that commit, as [review state](review-state.md) describes.',
            'do not land it on the default branch, release it or report it complete, and require',
            'record as plain text that the claim is unverified, its open findings and that it must not be landed on the default branch, released or reported complete.',
        ),
    }
    ACCEPTANCE_GATE_README = {
        ('en', 'Commit', "in auto, main may commit a claim of plan-driven work before its passes, push it to a branch it created for the work and open a pull request that lists the claims still unaccepted, without asking. It asks before pushing to a branch that already existed and that it did not create; in a resumed session a branch counts as its own only when an active handoff records that it created it for this work. Before a gated review or verification, main commits only when that call needs a commit. Opening a pull request is not permission to merge it, a pass is not a request to land or release, and your explicit instruction not to commit or not to push wins; a claim whose review or verification then lacks its commit is reported blocked. For a claim gated only because an active handoff records it as unreviewed, unverified or pending acceptance, main may make the local commit a review or verification needs without asking, and asks before pushes and pull requests, as in `off`. For all these claims, main lands the claim on the remote default branch, releases it, reports it complete or marks its ticket done only with a valid APPROVED and CONFIRMED, plus a valid HELD for a Security-critical claim, or with your accept-and-land decision. A cancelled claim's commits left on a branch stay listed as unaccepted until you decide to revert them, keep them off the default branch or accept and land them; a branch carrying them is not landed before that. Pushed history is never rewritten, so a fix is a new commit, and landing a branch lands every claim on it. Each review, verification and Adversarial review of such a claim judges a named commit with a clean workspace. The default branch is the one the remote's HEAD names, or a protected or shared branch you name. On the default branch, commits made before the passes are labelled unaccepted and pushed only after both passes, plus HELD for a Security-critical claim, or your accept-and-land decision, or with your explicit permission; until then main reminds you that a reclaimed environment would lose them. In `off`, nothing else changes."),
        ('en', 'Not passed', 'a claim without APPROVED is unreviewed: it is not landed on the default branch, released or reported complete.'),
        ('en', 'Not passed', 'A claim without a valid CONFIRMED is unverified and is not landed, released or reported complete either.'),
        ('en', 'Your decisions', 'so a waived claim the acceptance gate covers is landed on the default branch, released or reported complete only after a later pass or your accept-and-land decision.'),
        ('en', 'Resumed session', 'Before landing, release or completion, a claim that passed in an earlier session is reviewed and verified again, and a Security-critical claim gets Adversarial review again, unless its ticket was set to a done value after both passes (plus HELD for a Security-critical claim) or your accept-and-land decision and nothing relevant changed since.'),
        ('zh', 'Commit 條件', '在 auto 下，主 Agent 可以不經詢問，在依計畫施工的 claim 通過前先 commit，推到它為這項工作建立的 branch，並開 PR 列出尚未驗收的 claim。要推到原本就存在、不是它建立的 branch 前，會先問你；恢復的 session 裡，只有進行中的交接記錄了它為這項工作建立該 branch，才算它自己的 branch。受把關約束的審查或驗證需要 commit 時，主 Agent 才會先 commit。開 PR 不等於可以 merge，通過也不代表要 land 或 release；你明確說不要 commit 或不要 push 時，以你的指示為準，因此審查或驗證缺少所需 commit 時，該 claim 會回報為受阻。只因進行中的交接記錄為未審查、未驗證或待驗收而受把關的 claim，主 Agent 可以不經詢問做審查或驗證所需的本機 commit，但 push 與開 PR 會先問你，和 `off` 相同。以上 claim 都只有在 APPROVED 與 CONFIRMED（安全關鍵 claim 還要加上 HELD）都仍有效，或你決定接受並合併時，才會讓 claim 進入遠端的預設 branch、release、回報完成或把 ticket 設成完成。取消的 claim 留在 branch 上的 commit 會一直列為未驗收，直到你決定用新 commit revert、不讓它進入預設 branch，或接受並合併；在那之前，帶著它們的 branch 不會被合併。已推送的歷史不會改寫，修正一律加新 commit；合併一個 branch 就等於合併上面所有 claim。這類 claim 的每次審查、驗證與對抗式審查，都針對指名的 commit，且工作區乾淨。預設 branch 指遠端 HEAD 所在的 branch，或你指定為受保護或共用的 branch。在預設 branch 上，通過前的 commit 會標示為未驗收，要等兩關都通過（安全關鍵 claim 還要加上 HELD）、你決定接受並合併，或你明確允許才會推送；在那之前，主 Agent 會提醒你環境回收時這些 commit 會遺失。`off` 下其他行為不變。'),
        ('zh', '未通過', '沒拿到 APPROVED 的 claim 視為未審查，不進入預設 branch、不 release、不回報完成。'),
        ('zh', '未通過', '沒有有效 CONFIRMED 的 claim 視為未驗證，同樣不進入預設 branch、不 release、不回報完成。'),
        ('zh', '你的決定', '所以受驗收把關約束的 claim 被豁免後，要等之後的審查或驗證通過，或你決定接受並合併，才會進入預設 branch、release 或回報完成。'),
        ('zh', '恢復的 session', '在進入預設 branch、release 或回報完成前，之前 session 通過的 claim 要重新審查與驗證，安全關鍵 claim 也要重新做對抗式審查；只有 ticket 是在兩關通過（安全關鍵 claim 還要加上 HELD）或你決定接受並合併之後才設成表示已完成的完成值、且之後沒有相關變更的 claim 例外。'),
    }

    def test_acceptance_gate_sentences_are_stated_whole(self):
        references = config.ROOT / "skills" / "delegation" / "references"
        for name, sentences in self.ACCEPTANCE_GATE_SENTENCES.items():
            text = (references / name).read_text(encoding="utf-8")
            for sentence in sentences:
                with self.subTest(path=name, sentence=sentence[:60]):
                    self.assertIn(sentence, text)
        bullets = {
            "en": dict(self.readme_rule_bullets((config.ROOT / "README.md").read_text(encoding="utf-8"),
                                              "## Roles and routing", "### Automatic review switch")),
            "zh": dict(self.readme_rule_bullets((config.ROOT / "README.zh-TW.md").read_text(encoding="utf-8"),
                                              "## 分派與預設模型", "### 自動審查開關")),
        }
        for language, label, sentence in self.ACCEPTANCE_GATE_README:
            with self.subTest(language=language, bullet=label, sentence=sentence[:60]):
                self.assertIn(sentence, bullets[language][label])
        adr = config.ROOT / "docs" / "adr"
        for name, note in (("0002-session-scoped-review-counts.md", '(Amended by ADR 0007: the restriction now applies to landing on the default branch, release and reporting complete rather than to committing; a restricted claim may be committed before its passes.)'),
                           ("0006-review-state-validity-and-completion.md", '(Amended by ADR 0007: the commit gate moved to landing on the remote default branch, release, reporting complete and ticket completion; claims may be committed before their passes, and a claim that passed in an earlier session is reviewed and verified again before a gated operation unless its ticket is finished.)')):
            with self.subTest(adr=name):
                self.assertIn(note, (adr / name).read_text(encoding="utf-8").splitlines())

    def test_acceptance_gates_landing_release_and_completion_not_commits(self):
        # ADR 0007: claims may be committed before their passes; what the passes gate is reaching the default branch.
        references = config.ROOT / "skills" / "delegation" / "references"
        expected = {
            references / "review-state.md": (
                "judged with a clean workspace, as What a gated pass judged describes",
                "main lands the claim on the remote default branch (by pushing it there or merging it",
                "This is the acceptance gate",
                "releases or tags it, reports it complete or sets its ticket to a done value only with a valid APPROVED",
                "Commits on other branches carry no label",
                "Before a gated operation, a claim needs valid passes from this session",
                "is reviewed and verified again, and a Security-critical claim gets Adversarial review again, counted as usual",
                "a work-in-progress push the user allows may move a gated claim's commits to the default branch, labelled",
                "Landing a branch lands every claim on it",
                "A cancelled claim's commits that remain on a branch are listed as unaccepted",
                "the branch the `origin` remote's HEAD names",
                "or the only remote's HEAD when there is no `origin`",
                "with no remote, several remotes and no `origin`, or no HEAD, main asks",
                "A protected or shared branch the user names counts as a default branch",
                "lists the claims still unaccepted, without the user's permission, and keeps that list current",
                "It never rewrites pushed history, so a fix is a new commit",
                "the label records the commit's state then and stays in history",
                "only after both passes, plus a valid HELD for a Security-critical claim, or the user's accept-and-land decision for their claim, or as a work-in-progress push the user explicitly allows",
                "a reclaimed environment would lose them",
                "dispatches a code review, outcome verification or Adversarial review only when the workspace equals the commit it names",
                "HEAD is that commit, nothing the claim's files or acceptance checks depend on has an uncommitted or untracked change",
                "and nothing changes the workspace during the call",
                "a second review after a completed review receives the range from the previously judged commit",
                "A call for work the gate does not cover",
                "main does not commit that work to review it",
                "restricts it under the acceptance gate whatever its wording",
                "main updates the wording at the next handoff maintenance",
                "a claim that passed in an earlier session is reviewed and verified again",
                "any other finished ticket is only not redone",
            ),
            references / "code-review.md": (
                "acceptance gate still covers, in either mode",
                "also name the commit under review and dispatch only with a clean workspace at that commit",
                "the range from the previously judged commit to the new one",
                "must not be landed on the default branch, released or reported complete"),
            references / "outcome-verification.md": (
                "also name the base revision and the commit under verification, and dispatch only with a clean workspace",
                "do not land it on the default branch, release it or report it complete",
                "must not be landed on the default branch, released or reported complete"),
        }
        for path, phrases in expected.items():
            text = path.read_text(encoding="utf-8")
            for phrase in phrases:
                with self.subTest(path=path.name, phrase=phrase):
                    self.assertIn(phrase, text)
        english = dict(self.readme_rule_bullets((config.ROOT / "README.md").read_text(encoding="utf-8"),
                                                "## Roles and routing", "### Automatic review switch"))
        chinese = dict(self.readme_rule_bullets((config.ROOT / "README.zh-TW.md").read_text(encoding="utf-8"),
                                                "## 分派與預設模型", "### 自動審查開關"))
        for bullets, label, phrase in (
                (english, "Commit", "in auto, main may commit a claim of plan-driven work before its passes, push it to a branch it created for the work"),
                (english, "Commit", "open a pull request that lists the claims still unaccepted, without asking"),
                (english, "Commit", "judges a named commit with a clean workspace"),
                (english, "Not passed", "it is not landed on the default branch, released or reported complete"),
                (english, "Not passed", "is unverified and is not landed, released or reported complete either"),
                (chinese, "未通過", "沒拿到 APPROVED 的 claim 視為未審查，不進入預設 branch、不 release、不回報完成"),
                (chinese, "未通過", "沒有有效 CONFIRMED 的 claim 視為未驗證，同樣不進入預設 branch、不 release、不回報完成"),
                (english, "Commit", "main lands the claim on the remote default branch, releases it, reports it complete or marks its "
                                    "ticket done only with a valid APPROVED and CONFIRMED"),
                (english, "Commit", "Pushed history is never rewritten, so a fix is a new commit"),
                (english, "Commit", "landing a branch lands every claim on it"),
                (english, "Commit", "or a protected or shared branch you name"),
                (english, "Commit", "a reclaimed environment would lose them"),
                (english, "Your decisions", "A work-in-progress push you allow can move its commits to the default branch, but it is neither a release nor completion"),
                (english, "Commit", "labelled unaccepted and pushed only after both passes, plus HELD for a Security-critical claim, or your accept-and-land decision, or with your explicit permission"),
                (english, "Resumed session", "a claim that passed in an earlier session is reviewed and verified again, "
                                             "and a Security-critical claim gets Adversarial review again, "
                                             "unless its ticket was set to a done value after both passes (plus HELD for a Security-critical claim) or your accept-and-land decision"),
                (chinese, "Commit 條件", "在依計畫施工的 claim 通過前先 commit，推到它為這項工作建立的 branch"),
                (chinese, "Commit 條件", "並開 PR 列出尚未驗收的 claim"),
                (chinese, "Commit 條件", "都針對指名的 commit，且工作區乾淨"),
                (chinese, "Commit 條件", "才會讓 claim 進入遠端的預設 branch、release、回報完成或把 ticket 設成完成"),
                (chinese, "Commit 條件", "已推送的歷史不會改寫，修正一律加新 commit"),
                (chinese, "Commit 條件", "合併一個 branch 就等於合併上面所有 claim"),
                (chinese, "Commit 條件", "或你指定為受保護或共用的 branch"),
                (chinese, "Commit 條件", "環境回收時這些 commit 會遺失"),
                (chinese, "你的決定", "你允許的工作中途推送可以把它的 commit 推到預設 branch，但不算 release，也不算完成"),
                (chinese, "Commit 條件", "通過前的 commit 會標示為未驗收，要等兩關都通過（安全關鍵 claim 還要加上 HELD）、你決定接受並合併，或你明確允許才會推送"),
                (chinese, "恢復的 session", "之前 session 通過的 claim 要重新審查與驗證，安全關鍵 claim 也要重新做對抗式審查；只有 ticket 是在兩關通過（安全關鍵 claim 還要加上 HELD）或你決定接受並合併之後才設成表示已完成的完成值")):
            with self.subTest(bullet=label, phrase=phrase):
                self.assertIn(phrase, bullets[label])
        entries = self.glossary_entries((config.ROOT / "CONTEXT.md").read_text(encoding="utf-8"))
        for term in ("Unreviewed claim", "Unverified claim"):
            with self.subTest(term=term):
                self.assertIn("It is not landed on the default branch, released or reported complete.", entries[term])
        adr = config.ROOT / "docs" / "adr"
        decision = (adr / "0007-commit-before-acceptance.md").read_text(encoding="utf-8")
        for phrase in ("The acceptance gate now covers landing a Claim on the remote default branch",
                       "push it to any branch other than a default branch without the user's permission",
                       "Pushed history is never rewritten", "labels each such commit unaccepted when it creates it",
                       "judges a named commit with a clean workspace",
                       "a Claim that passed in an earlier session is reviewed and verified again, unless its ticket is finished",
                       "restricts it under the new gate", "Keep the commit gate", "Commit locally only, push after acceptance",
                       "Label every early commit on a working branch", "Trust passes across sessions by commit",
                       "amends ADR 0006's commit rule and ADR 0002's statement"):
            with self.subTest(adr="0007", phrase=phrase):
                self.assertIn(phrase, decision)
        for name, phrase in (("0002-session-scoped-review-counts.md", "(Amended by ADR 0007: the restriction now applies"),
                             ("0006-review-state-validity-and-completion.md", "(Amended by ADR 0007: the commit gate moved")):
            with self.subTest(adr=name):
                self.assertIn(phrase, (adr / name).read_text(encoding="utf-8"))

    def test_implemented_work_without_plan_review_state_asks_the_user_first(self):
        # A plan implemented elsewhere, or while review was off, has no plan-review state here; main asks first.
        references = config.ROOT / "skills" / "delegation" / "references"
        expected = {
            references / "review-state.md": (
                "**Implemented before plan review.**",
                "has no plan-review state in this session (no automatic plan-review call and no recorded user decision",
                "in another session, outside Claude, or in this session while review was off",
                "An explicit READY given before the flow reached plan review is not plan-review state",
                "without treating it as a pass",
                "plan review first: an automatic call of the flow covering the whole plan",
                "recorded as a waiver of the missing READY for the implemented claims",
                "Main dispatches neither call until the user answers",
                "Claims of the plan not yet implemented still get plan review before they are implemented",
                "follows the rules above, and main does not ask again",
                "Implemented before plan review below comes first",
                "For a plan with an implemented claim, Implemented before plan review comes first",
                "main names it",
                "a REVISE then follows [plan review](plan-review.md) steps 4 and 5",
                "changes needed in implemented claims are fixes that go through code review",
                "with its scope, visible in the report and in any active handoff",
                "When plan-review state cannot be established, Unknown state applies",
                "work overlapping a stopped plan keeps the Overlap rule",
            ),
            references / "plan-review.md": ("has no plan-review state in this session is handled before any call",),
            references / "preview.md": ("a Plan with implemented Claims and no plan-review state in this session",),
            config.ROOT / "skills" / "delegation" / "SKILL.md": (
                "when implemented work's plan has no plan-review state in this session, first ask",),
            config.ROOT / "README.md": ("main first asks as under Implemented before plan review",
                                        "Claims not yet implemented still get plan review first",
                                        "names any record of an earlier plan review it found but does not treat it as a pass",
                                        "a plan with implemented claims and no plan review in this session",
                                        "records the missing READY as a waiver for the implemented claims",
                                        "follows the usual rules, without asking again",
                                        "For a plan with an implemented claim, main first asks as under Implemented before plan review",
                                        "already reviewed by the automatic flow"),
            config.ROOT / "README.zh-TW.md": ("主 Agent 會先照「實作完才做計畫審查」問你",
                                              "尚未實作的 claim 仍會先做計畫審查",
                                              "它會列出找到的先前計畫審查紀錄，但不把它當成通過",
                                              "已有 claim 實作但這個 session 沒有計畫審查紀錄的計畫",
                                              "把缺少的 READY 記為已實作 claim 的豁免",
                                              "照一般規則處理，不會再問",
                                              "已有 claim 實作的計畫，主 Agent 會先照「實作完才做計畫審查」問你",
                                              "自動流程已經審查過"),
        }
        for path, phrases in expected.items():
            text = path.read_text(encoding="utf-8")
            for phrase in phrases:
                with self.subTest(path=path.name, phrase=phrase):
                    self.assertIn(phrase, text)
        # The same deferral appears in two README bullets, so each is checked within its own bullet.
        english = dict(self.readme_rule_bullets((config.ROOT / "README.md").read_text(encoding="utf-8"),
                                                "## Roles and routing", "### Automatic review switch"))
        chinese = dict(self.readme_rule_bullets((config.ROOT / "README.zh-TW.md").read_text(encoding="utf-8"),
                                                "## 分派與預設模型", "### 自動審查開關"))
        for bullets, label, phrase in (
                (english, "Asking for a review", "main first asks as under Implemented before plan review"),
                (english, "Resumed session", "main first asks as under Implemented before plan review"),
                (chinese, "要求審查時", "主 Agent 會先照「實作完才做計畫審查」問你"),
                (chinese, "恢復的 session", "主 Agent 會先照「實作完才做計畫審查」問你")):
            with self.subTest(bullet=label):
                self.assertIn(phrase, bullets[label])

    def test_rules_whose_pairings_moved_to_newer_phrases_stay_stated(self):
        # README_RULES and GLOSSARY_RULES now pair these entries with their 0.14.0 rules; the earlier rules still hold.
        references = config.ROOT / "skills" / "delegation" / "references"
        english = dict(self.readme_rule_bullets((config.ROOT / "README.md").read_text(encoding="utf-8"),
                                                "## Roles and routing", "### Automatic review switch"))
        chinese = dict(self.readme_rule_bullets((config.ROOT / "README.zh-TW.md").read_text(encoding="utf-8"),
                                                "## 分派與預設模型", "### 自動審查開關"))
        entries = self.glossary_entries((config.ROOT / "CONTEXT.md").read_text(encoding="utf-8"))
        for place, text, phrase in (
                ("code-review.md", (references / "code-review.md").read_text(encoding="utf-8"),
                 "applies in either mode and does not start verification"),
                ("plan-review.md", (references / "plan-review.md").read_text(encoding="utf-8"),
                 "a plan proposed in conversation and approved by the user"),
                ("plan-review.md handoff", (references / "plan-review.md").read_text(encoding="utf-8"),
                 "an unresolved verdict that an active handoff records for a spec's plan"),
                ("README Claim changes", english["Claim changes"], "main never edits a spec or ticket to add claims"),
                ("README 修改 claim", chinese["修改 claim"], "不會為了補 claim 而修改 spec 或 ticket"),
                ("README Resumed session", english["Resumed session"], "an unresolved verdict that an active handoff records"),
                ("README 恢復的 session", chinese["恢復的 session"], "進行中的交接若記錄了"),
                ("README Plan-mode", english["Plan-mode and conversation plans"], "another session cannot see them"),
                ("README plan mode", chinese["plan mode 與對話中的計畫"], "其他 session 看不到"),
                ("glossary Plan", entries["Plan"], "a document lacking scope or acceptance is not yet a Plan"),
                ("glossary Explicit request", entries["Explicit request"], "runs only what was requested")):
            with self.subTest(place=place):
                self.assertIn(phrase, text)

    def test_readme_commit_and_not_passed_bullets_state_their_scope(self):
        english = dict(self.readme_rule_bullets((config.ROOT / "README.md").read_text(encoding="utf-8"),
                                                "## Roles and routing", "### Automatic review switch"))
        chinese = dict(self.readme_rule_bullets((config.ROOT / "README.zh-TW.md").read_text(encoding="utf-8"),
                                                "## 分派與預設模型", "### 自動審查開關"))
        for bullets, label, phrase in (
                (english, "Commit", "For a claim gated only because an active handoff records it as unreviewed, unverified or pending acceptance"),
                (chinese, "Commit 條件", "只因進行中的交接記錄為未審查、未驗證或待驗收而受把關的 claim"),
                (english, "Not passed", "A claim without a valid CONFIRMED is unverified"),
                (chinese, "未通過", "沒有有效 CONFIRMED 的 claim 視為未驗證")):
            with self.subTest(label=label):
                self.assertIn(phrase, bullets[label])

    def test_per_claim_bound_is_described_as_one_uninterrupted_attempt(self):
        # Configurable Stop threshold C2: the bound is K(K+1), and its K = 2 example is 6.
        # The per-claim bound holds only while nothing reopens the claim; it must never read as a total.
        readme = (config.ROOT / "README.md").read_text(encoding="utf-8")
        readme_zh = (config.ROOT / "README.zh-TW.md").read_text(encoding="utf-8")
        sources = {
            "preview.md": ((config.ROOT / "skills" / "delegation" / "references" / "preview.md")
                           .read_text(encoding="utf-8"), "K(K+1)", "uninterrupted", r"[.;:] "),
            "README cost": (readme.split("- **Cost:**", 1)[1].split("\n", 1)[0], "K(K+1)", "uninterrupted", r"[.;:] "),
            "README preview": (readme.split("### Delegation preview", 1)[1].split("\n### ", 1)[0],
                               "K(K+1)", "uninterrupted", r"[.;:] "),
            "README.zh-TW cost": (readme_zh.split("- **成本：**", 1)[1].split("\n", 1)[0], "K(K+1)", "不中斷", "[。；：]"),
            "README.zh-TW preview": (readme_zh.split("### 分派預覽", 1)[1].split("\n### ", 1)[0],
                                     "K(K+1)", "不中斷", "[。；：]"),
        }
        # The bound may also be written as the numeral 6 ("6 calls", 「6 次」), but not as part of "6N".
        numeral = re.compile(r"(?<![0-9A-Za-z])[6６]\s*(?:calls?|automatic|次)")
        for name, (text, figure, qualifier, stop) in sources.items():
            sentences = [clause for clause in re.split(stop, text) if figure in clause or numeral.search(clause)]
            with self.subTest(source=name):
                self.assertTrue(sentences)
                for sentence in sentences:
                    self.assertIn(qualifier, sentence)
        # Every place that states the bound also says what adds to it.
        for name, text in (("preview.md", sources["preview.md"][0]), ("README cost", sources["README cost"][0]),
                           ("README preview", sources["README preview"][0])):
            with self.subTest(adds=name):
                self.assertIn("reopened", text)
        for name in ("README.zh-TW cost", "README.zh-TW preview"):
            with self.subTest(adds=name):
                self.assertIn("重新打開", sources[name][0])

    # Each README bullet maps English label -> (Traditional Chinese label, English phrase, Chinese phrase,
    # procedure file, procedure phrase); every bold-label bullet of the two lists must have an entry.
    README_RULES = {
        "Unplanned work": ("沒有計畫的工作", "first needs a written plan", "須先寫出計畫",
                           "plan-review.md", "must not start without one"),
        "Budget": ("次數上限", "each step counts consecutive automatic calls", "每個步驟計算連續沒通過的自動呼叫次數",
                   "plan-review.md", "Count consecutive automatic calls without a pass"),
        "Re-review during implementation": ("施工中的重審", "a plan is reviewed again only after a material deviation",
                                            "只有重大偏離", "plan-review.md", "a material deviation stops dependent work"),
        "Findings": ("問題分級", "Non-blocking ones are listed in the final report", "非阻擋問題列在最終回報",
                     "code-review.md", "List them in the final report"),
        "Not passed": ("未通過", "it is not landed on the default branch, released or reported complete", "不進入預設 branch、不 release、不回報完成",
                       "code-review.md", "do not land it on the default branch, release it or report it complete"),
        "Authority": ("授權", "a pass grants no new authority", "通過不代表新的授權",
                      "plan-review.md", "READY grants no new authority"),
        "Explicit requests": ("明確要求", "do not use the automatic budget", "不佔自動次數",
                              "plan-review.md", "Explicit calls do not count toward the automatic budget below"),
        "After a stop": ("停下之後", "it clears the stop and leaves the count unchanged", "次數維持在停下時的數字",
                         "review-state.md", "clears the stop and leaves the count unchanged"),
        "Asking for a review": ("要求審查時", "main states which before dispatching", "主 Agent 派出前會先說明是哪一種",
                                "review-state.md", "State the classification before dispatching"),
        "Implemented before plan review": ("實作完才做計畫審查",
                                           "main asks before any review whether to run plan review first",
                                           "主 Agent 會在任何審查前先問你", "review-state.md", "main asks before any call"),
        "Retries": ("重試", "including a generic retry after a temporary failure", "包括暫時失敗後的一般重試",
                    "review-state.md", "including a generic retry after a temporary failure"),
        "Lost state": ("狀態不明", "main treats the step as stopped and asks you", "主 Agent 會視為已停下並問你",
                       "review-state.md", "treat the step as stopped and ask the user"),
        "Cost": ("成本", "a claim makes at most K(K+1)", "每個 claim 最多 K(K+1) 次",
                 "preview.md", "a Claim makes at most K(K+1) automatic calls"),
        "Independence": ("獨立性", "each review runs in a fresh context", "每次審查都在新的 context",
                         "plan-review.md", "in fresh native context"),
        # Claims at implementation ticket 01: the three named-Plan cases replace "A spec, or some of its tickets".
        "A spec": ("一份 spec", "main first asks whether you mean the spec as it stands or its tickets",
                   "主 Agent 會先問你要實作 spec 本身還是它的 ticket", "plan-review.md",
                   "main first asks the user whether to implement the spec as it stands or its tickets"),
        "Tickets of a spec, all or some": ("一份 spec 的 ticket（全部或部分）", "Each unfinished ticket among them is one claim",
                                           "其中每張未完成的 ticket 是一個 claim", "plan-review.md",
                                           "each unfinished ticket in the named scope is one claim"),
        "A single ticket": ("單一 ticket", "that ticket is the plan and its one claim", "該 ticket 就是計畫，也是它唯一的 claim",
                            "plan-review.md", "A single named ticket is the plan and its one claim"),
        "A ticket that belongs to no spec": ("不屬於任何 spec 的 ticket", "is its own plan", "自成一份計畫",
                                             "plan-review.md", "A ticket that belongs to no spec is its own plan"),
        "Example": ("例子", "makes one plan with three claims", "是一份有三個 claim 的計畫",
                    "plan-review.md", "The plan is what the user names"),
        # Claims at implementation ticket 02: the spec as a checklist for plan review over tickets, and citations.
        "The spec as a checklist": ("spec 作為檢查清單", "The spec is not part of the plan, only a checklist",
                                    "spec 不是計畫的一部分，只是檢查清單", "plan-review.md",
                                    "It uses the spec only as a checklist for what the tickets must carry"),
        "Citations": ("引用", "is not a citation", "都不算引用", "plan-review.md",
                      "a `Spec:` line, a parent reference or a shared directory is not a citation"),
        "Checklist limits": ("檢查清單的限制", "the checklist runs at plan review", "檢查清單在計畫審查時執行",
                             "plan-review.md", "a ticket's reviews after plan review do not read the parts of the spec"),
        # Claims at implementation ticket 03: what a claim's reviews and implementation read.
        "What a review reads": ("審查讀什麼", "read the same reading set", "讀的是同一組閱讀範圍",
                                "code-review.md", "A claim's reading set is what its implementation and every review of it read"),
        "Already covered": ("已涵蓋", "that plan continues with no new plan review", "不重做計畫審查",
                            "plan-review.md", "otherwise that plan continues with no new plan review"),
        "Partial overlap": ("部分重疊", "gains no new automatic calls", "不會多出新的自動呼叫",
                            "review-state.md", "gains no new automatic calls"),
        "Validity": ("有效範圍", "a pass holds only for what it judged", "通過只對它審過的內容有效",
                     "review-state.md", "A pass covers the work identity, its acceptance and the reviewed content"),
        "Commit": ("Commit 條件", "only with a valid APPROVED and CONFIRMED", "都仍有效，或你決定接受並合併時，才會讓 claim 進入遠端的預設 branch",
                   "review-state.md", "only with a valid APPROVED and a valid CONFIRMED"),
        "Release checks": ("事後檢查", "is checked and reported by main after the operation", "在操作後檢查並回報",
                           "review-state.md", "checks and reports it after the operation"),
        "Your decisions": ("你的決定", "re-review, deferral, cancellation, changed acceptance, waiver or accept and land",
                           "重審、延後、取消、修改驗收、豁免或接受並合併",
                           "review-state.md", "re-review, deferral, cancellation, changed acceptance, waiver or accept and land"),
        "Ticket status": ("Ticket 狀態", "noting the version or commit", "並註明版本或 commit",
                          "review-state.md", "with a note naming the version or commit"),
        "Resumed session": ("恢復的 session", "an unfinished plan is reviewed again", "未完成的計畫會重新審查",
                            "review-state.md", "reviews an unfinished plan again before implementing it"),
        "Nothing left": ("沒有剩餘工作", "nothing is left to implement", "沒有剩下要實作",
                         "plan-review.md", "report that nothing is left to implement"),
        "Finding the tickets": ("辨識 ticket", "an empty result does not count as none", "搜不到不代表沒有",
                                "plan-review.md", "an empty result is not evidence that none exist"),
        "Telling main where tickets live": ("告訴主 Agent ticket 放在哪裡", "add a line to your project's CLAUDE.md or AGENTS.md",
                                            "在專案的 CLAUDE.md 或 AGENTS.md", "plan-review.md",
                                            "Look first at the project's instructions"),
        "Disagreement": ("不一致", "a mismatch is a blocker for you to settle", "不一致會列為阻擋事項",
                         "plan-review.md", "report a mismatch as a blocker for the user to settle"),
        "Claim changes": ("修改 claim", "main edits only after your authorisation", "在你授權後才修改",
                          "review-state.md", "only after the user authorises it"),
        # Claims at implementation ticket 04 (Acceptance items 5 and 11): the drafting rule.
        "Drafting a spec": ("草擬 spec", "it lists no claims and cuts none unless you ask", "除非你要求，不會在裡面列出 claim",
                            "plan-review.md", "When main drafts a spec for the user, it lists no claims and cuts none "
                            "unless the user asks."),
        "Not yet a plan": ("還不算計畫", "is not yet a plan", "主 Agent 會先補齊",
                           "plan-review.md", "A document without scope or acceptance is not yet a plan"),
        "Plan-mode and conversation plans": ("plan mode 與對話中的計畫",
                                             "only from its original text, an available record or a version you confirm",
                                             "依它的原文、現有紀錄或你確認過的版本", "plan-review.md",
                                             "is identified only from its original text, an available record or a version the user confirms"),
        "Where files live": ("檔案位置", "cc-feather does not decide where specs live", "不由 cc-feather 決定",
                             "plan-review.md", "Where specs live and whether tickets are committed are the project's choice"),
        # Repository safety C1 item 7: the Repository safety section's bullets summarise the shared reference.
        # Repository safety follow-ups C2 item 3: the statement names outcome 1's exception on this machine.
        "Git commands": ("Git 指令",
                         "runs no program the repository chose, such as an fsmonitor, a textconv or external diff, a "
                         "filter, a signing program or a hook, with one exception on this machine:",
                         "也不執行儲存庫選定的程式，例如 fsmonitor、textconv 或外部 diff、filter、簽章程式或 hook；只有一個例外，"
                         "發生在這台機器上：",
                         "repository-safety.md",
                         "runs no Repository-chosen program, with one exception on this machine: main's content hashing "
                         "under outcome 1 of Main's preparation"),
        "File reads": ("讀取檔案", "has a single hard link", "只有一個硬連結",
                       "repository-safety.md", "that its link count is 1."),
        "Running repository code": ("執行儲存庫程式碼", "the repository is trusted to run on this machine",
                                    "這個儲存庫可以在這台機器上執行", "repository-safety.md",
                                    "the user has said that the repository is trusted to run on this machine"),
        "Before a review": ("審查之前", "Git is 2.32 or later", "2.32 或更新版本",
                            "repository-safety.md", "Git is 2.32 or later"),
        # Repository safety deviation D-6: the bullet summarises the fixed forms instead of the named programs.
        "Before add, commit, tag or push": ("add、commit、tag 或 push 之前", "runs in a fixed form", "以固定形式執行",
                                            "repository-safety.md", "Each operation runs only in its fixed form"),
        # Repository safety C2 item 6: the roles bullet summarises the paragraph for roles without a shell.
        "Roles": ("角色", "report a missing list instead of reading", "沒有清單時回報缺少需求而不讀取",
                  "repository-safety.md", "report it as a missing requirement instead of reading the repository"),
    }

    # Glossary term -> (phrase in its CONTEXT.md entry, procedure file, procedure phrase).
    GLOSSARY_RULES = {
        # Claims at implementation ticket 01 (Acceptance item 9): the Plan entry states the named-Plan cases.
        "Plan": ("named tickets of a spec, all or some, form one Plan with each unfinished ticket as one Claim",
                 "plan-review.md", "each unfinished ticket in the named scope is one claim"),
        "Claim": ("One independently verifiable outcome with its own acceptance",
                  "plan-review.md", "each an independently verifiable outcome with its own acceptance"),
        "Unplanned work": ("must first become Plan-driven work", "plan-review.md", "must not start without one"),
        "Explicit request": ("it clears the stop without resetting the count",
                             "review-state.md", "clears the stop and leaves the count unchanged"),
        "Code review": ("answered APPROVED, CHANGES_REQUESTED or INCONCLUSIVE",
                        "code-review.md", "its APPROVED, CHANGES_REQUESTED or INCONCLUSIVE report"),
        "Unreviewed claim": ("stopped at its Stop threshold without APPROVED",
                             "code-review.md", "When the count reaches the Stop threshold in effect without APPROVED"),
        "Unverified claim": ("no currently valid CONFIRMED", "outcome-verification.md", "report the claim as unverified"),
        "Delegation preview": ("the dispatch basis only in the session that made it",
                               "preview.md", "only in the session that made it"),
    }

    readme_rule_bullets = staticmethod(feather_support.readme_rule_bullets)

    glossary_entries = staticmethod(feather_support.glossary_entries)

    def test_readme_review_rules_match_the_procedures_in_both_languages(self):
        references = config.ROOT / "skills" / "delegation" / "references"
        english_bullets = self.readme_rule_bullets((config.ROOT / "README.md").read_text(encoding="utf-8"),
                                                   "## Roles and routing", "### Automatic review switch")
        chinese_bullets = self.readme_rule_bullets((config.ROOT / "README.zh-TW.md").read_text(encoding="utf-8"),
                                                   "## 分派與預設模型", "### 自動審查開關")
        english, chinese = dict(english_bullets), dict(chinese_bullets)
        self.assertEqual(len(english), len(english_bullets), "English rule bullet labels must be unique")
        self.assertEqual(len(chinese), len(chinese_bullets), "Traditional Chinese rule bullet labels must be unique")
        self.assertEqual(set(english), set(self.README_RULES), "every English rule bullet needs exactly one mapping")
        self.assertEqual(set(chinese), {entry[0] for entry in self.README_RULES.values()},
                         "every Traditional Chinese rule bullet must pair with an English one")
        for label, (zh_label, en_phrase, zh_phrase, procedure, rule) in self.README_RULES.items():
            with self.subTest(label=label):
                self.assertIn(en_phrase, english[label])
                self.assertIn(zh_phrase, chinese[zh_label])
                self.assertIn(rule, (references / procedure).read_text(encoding="utf-8"))

    def test_glossary_entries_match_the_procedures(self):
        references = config.ROOT / "skills" / "delegation" / "references"
        entries = self.glossary_entries((config.ROOT / "CONTEXT.md").read_text(encoding="utf-8"))
        for term, (definition, procedure, rule) in self.GLOSSARY_RULES.items():
            with self.subTest(term=term):
                self.assertIn(term, entries)
                self.assertIn(definition, entries[term])
                self.assertIn(rule, (references / procedure).read_text(encoding="utf-8"))

    # Delegation preview: an explicit command whose rules sit beside the delegation procedures.

    def test_delegation_preview_is_an_explicit_command_listed_in_the_manifest(self):
        manifest = json.loads((config.ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertIn("./skills/delegation-preview", manifest["skills"])
        command = (config.ROOT / "skills" / "delegation-preview" / "SKILL.md").read_text(encoding="utf-8")
        frontmatter = command.split("---")[1]
        self.assertIn("name: delegation-preview", frontmatter)
        self.assertIn("disable-model-invocation: true", frontmatter)
        self.assertIn("argument-hint:", frontmatter)
        self.assertIn("(../delegation/references/preview.md)", command)

    def test_delegation_skill_never_offers_a_preview(self):
        text = (config.ROOT / "skills" / "delegation" / "SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("preview", text.lower())

    def test_delegation_preview_is_read_only_and_reuses_dispatch_rules(self):
        text = (config.ROOT / "skills" / "delegation" / "references" / "preview.md").read_text(encoding="utf-8")
        for phrase in ("(../SKILL.md)", "(../../model/SKILL.md)", "(plan-review.md)",
                       "dispatches no child", "starts no review", "writes no file",
                       "listed once", "is not applied",
                       "A session choice takes precedence over the saved mode"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    # DX7: a state from before created_guidance cannot claim the instruction file it leaves empty.

    def test_remove_keeps_and_reports_a_file_a_pre_flag_state_leaves_empty(self):
        guidance = self.project / "CLAUDE.md"
        self.apply("install", "project", "--component", "both")
        state_path = self.project / ".claude" / "cc-feather" / "state.json"
        state = self.saved_state()
        del state["created_guidance"]
        state_path.write_bytes(config.canonical(state) + b"\n")
        result = self.apply("remove", "project", "--component", "both")
        self.assertEqual(guidance.read_bytes(), b"")
        self.assertIn(f"{guidance} is now empty; setup did not record creating it, so it was kept", result["warnings"])

    # DX8: check and show name the role files install or update would write.

    def test_check_reports_the_role_paths_install_or_update_would_write(self):
        agents = self.project / ".claude" / "agents"
        self.other_agent("---\nname: scout\n---\nMine\n", "scout.md")
        self.other_agent("---\nname: Explore\n---\nMine\n", "explorer.md")
        prefixed = {role: str(agents / f"{config._role_name(role, config.ROLE_PREFIX)}.md")
                    for role in config.ROLES if role != "Explore"}
        shown = self.call("check")[1]
        self.assertEqual((shown["pending_role_prefix"], shown["pending_external_roles"]),
                         (config.ROLE_PREFIX, ["Explore"]), shown)
        self.assertEqual(shown["paths"]["agents"], prefixed)
        self.apply("install")
        self.assertEqual(self.call("show")[1]["paths"]["agents"], prefixed)
        # An unprefixed installation that another agent's name now moves to the prefix.
        self.use_case("later-conflict")
        agents = self.project / ".claude" / "agents"
        self.apply("install")
        self.other_agent("---\nname: analyst\n---\nMine\n", "analyst.md")
        shown = self.call("check")[1]
        self.assertEqual((shown["pending_role_prefix"], shown["pending_external_roles"]), (config.ROLE_PREFIX, None))
        self.assertEqual(shown["paths"]["agents"], {role: str(agents / f"{config._role_name(role, config.ROLE_PREFIX)}.md")
                                                    for role in config.ROLES})

    # DX10: a configuration directory that is a file stops at preview, not part-way through apply.

    def test_configuration_directory_that_is_a_file_is_refused_at_preview(self):
        dot_claude = self.project / ".claude"
        dot_claude.write_bytes(b"not a directory")
        before = self.files()
        for command in (("install", "project"), ("install", "project", "--component", "handoff"), ("check", "project")):
            with self.subTest(command=command):
                code, result = self.call(*command)
                self.assertEqual(code, 2, result)
                self.assertIn(f"{dot_claude} exists and is not a directory", result["error"])
        self.home = self.root / "claude-home-file"
        self.home.write_bytes(b"not a directory")
        before[self.home] = b"not a directory"
        code, result = self.call("install", "user")
        self.assertEqual(code, 2, result)
        try:
            os.path.realpath(self.home, strict=True)
        except OSError:
            # A volume without strict realpath refuses this home earlier, while resolving it.
            pass
        else:
            self.assertIn(f"{self.home} exists and is not a directory", result["error"])
        self.assertEqual(before, self.files())


    def test_claude_home_that_is_a_file_is_refused_on_every_volume(self):
        self.home = self.root / "claude-home-file"
        self.home.write_bytes(b"not a directory")
        before = self.files()
        with mock.patch("os.path.realpath", side_effect=OSError(None, "invalid", None, 1)):
            code, result = self.call("install", "user")
        self.assertEqual(code, 2, result)
        self.assertIn(f"{self.home} exists and is not a directory", result["error"])
        self.assertEqual(before, self.files())

    def test_claude_home_below_a_file_names_the_file(self):
        parent = self.root / "claude-home-file"
        parent.write_bytes(b"not a directory")
        self.home = parent / "sub"
        before = self.files()
        code, result = self.call("install", "user")
        self.assertEqual(code, 2, result)
        self.assertIn(f"{parent} exists and is not a directory", result["error"])
        self.assertEqual(before, self.files())


class SavedStopThresholdTests(unittest.TestCase):
    """Configurable Stop threshold C1: the configuration tool saves, states, shows, keeps and removes K per scope."""

    setUp = FeatherConfigTests.setUp
    call = FeatherConfigTests.call
    apply = FeatherConfigTests.apply
    files = FeatherConfigTests.files
    replace_delegation_block = FeatherConfigTests.replace_delegation_block

    USER_LINE = "The Stop threshold for automatic review is {k}."
    PROJECT_LINE = "The Stop threshold in this project is {k}; this overrides broader Feather guidance."

    def line(self, scope, k):
        return (self.PROJECT_LINE if scope == "project" else self.USER_LINE).format(k=k)

    def guidance(self, scope):
        return self.project / "CLAUDE.md" if scope == "project" else self.home / "CLAUDE.md"

    def state_path(self, scope):
        base = self.project / ".claude" if scope == "project" else self.home
        return base / "cc-feather" / "state.json"

    def record(self, scope):
        return json.loads(self.state_path(scope).read_bytes())["components"]["delegation"]

    def block(self, scope):
        return config._block_parts(self.guidance(scope).read_text(encoding="utf-8"))[1]

    def older_template_warnings(self, scope):
        return [w for w in self.call("check", scope)[1]["warnings"] if "older template" in w]

    @staticmethod
    def release_0_19_0_block(mode, scope):
        """The delegation block 0.19.0 renders without a role prefix, rebuilt from the templates."""
        template = (config.ROOT / "templates" / "CLAUDE.md").read_text(encoding="utf-8").replace("\r\n", "\n")
        auto = (config.ROOT / "templates" / "review-auto.md").read_text(encoding="utf-8").replace("\r\n", "\n").strip()
        if mode == "auto":
            middle = auto + "\n\n"
        else:
            middle = ("Automatic plan review is off in this project; this overrides broader Feather guidance.\n\n"
                      if scope == "project" else "")
        return template.replace("{{auto_review}}", middle).replace("{{role_names}}", "").rstrip("\n")

    def test_review_saves_shows_and_removes_the_stop_threshold_in_each_scope(self):
        for scope in ("project", "user"):
            with self.subTest(scope=scope):
                self.apply("install", scope, "--review-mode", "auto")
                guidance_before = self.guidance(scope).read_bytes()
                state_before = self.state_path(scope).read_bytes()
                shown = self.call("show", scope)[1]
                self.assertEqual((shown["stop_threshold"], shown["stop_threshold_set"]), (2, False))
                code, preview = self.call("review", scope, "--stop-threshold", "4")
                self.assertEqual(code, 0, preview)
                self.assertEqual((preview["stop_threshold"], preview["stop_threshold_set"]), (4, True))
                self.assertEqual(self.guidance(scope).read_bytes(), guidance_before)
                self.apply("review", scope, "--stop-threshold", "4")
                self.assertEqual(self.record(scope)["stop_threshold"], 4)
                self.assertEqual(self.record(scope)["review_mode"], "auto")
                self.assertEqual(self.block(scope).count(self.line(scope, 4)), 1)
                for command in ("show", "check"):
                    code, shown = self.call(command, scope)
                    self.assertEqual((code, shown["status"]), (0, "ok"), shown)
                    self.assertEqual((shown["stop_threshold"], shown["stop_threshold_set"]), (4, True))
                self.assertEqual(self.older_template_warnings(scope), [])
                self.apply("review", scope, "--stop-threshold", "10")
                self.assertEqual(self.record(scope)["stop_threshold"], 10)
                self.assertNotIn(self.line(scope, 4), self.block(scope))
                self.assertEqual(self.block(scope).count(self.line(scope, 10)), 1)
                self.apply("review", scope, "--stop-threshold", "default")
                self.assertNotIn("stop_threshold", self.record(scope))
                self.assertEqual(self.guidance(scope).read_bytes(), guidance_before)
                self.assertEqual(self.state_path(scope).read_bytes(), state_before)
                shown = self.call("show", scope)[1]
                self.assertEqual((shown["stop_threshold"], shown["stop_threshold_set"]), (2, False))
                # Setting it back to default where none is set changes nothing.
                code, preview = self.call("review", scope, "--stop-threshold", "default")
                self.assertEqual((code, preview["changes"]), (0, []), preview)

    def test_the_sentence_is_separate_from_the_review_paragraph_in_both_modes(self):
        auto = (config.ROOT / "templates" / "review-auto.md").read_text(encoding="utf-8").replace("\r\n", "\n").strip()
        for scope in ("project", "user"):
            for mode in ("auto", "off"):
                with self.subTest(scope=scope, mode=mode):
                    self.apply("install", scope, "--review-mode", mode)
                    self.apply("review", scope, "--stop-threshold", "3")
                    block = self.block(scope).replace("\r\n", "\n")
                    paragraphs = block.split("\n\n")
                    self.assertIn(self.line(scope, 3), paragraphs)
                    self.assertEqual(auto in paragraphs, mode == "auto")
                    self.assertEqual(config.PROJECT_REVIEW_OFF in paragraphs, mode == "off" and scope == "project")
                    # The sentence follows the review paragraph or the off line, never inside it.
                    expected = self.release_0_19_0_block(mode, scope).replace(
                        config.END, self.line(scope, 3) + "\n\n" + config.END)
                    self.assertEqual(block, expected)
                    self.assertEqual(self.older_template_warnings(scope), [])
                    self.apply("remove", scope)

    def test_guidance_without_a_stop_threshold_is_byte_identical_to_0_19_0(self):
        for scope in ("project", "user"):
            for mode in ("auto", "off"):
                with self.subTest(scope=scope, mode=mode):
                    self.apply("install", scope, "--review-mode", mode)
                    self.assertEqual(self.block(scope), self.release_0_19_0_block(mode, scope))
                    before = self.guidance(scope).read_bytes()
                    self.assertNotIn("stop_threshold", self.record(scope))
                    self.apply("review", scope, "--stop-threshold", "7")
                    self.apply("review", scope, "--stop-threshold", "default")
                    self.assertEqual(self.guidance(scope).read_bytes(), before)
                    self.assertEqual(self.older_template_warnings(scope), [])
                    self.apply("remove", scope)

    def test_review_combines_both_settings_in_one_plan_and_needs_one(self):
        self.apply("install", "project", "--review-mode", "off")
        before = self.files()
        code, error = self.call("review", "project")
        self.assertEqual(code, 2, error)
        self.assertIn("review requires --review-mode", error["error"])
        self.assertIn("--stop-threshold", error["error"])
        self.assertEqual(self.files(), before)
        self.apply("review", "project", "--review-mode", "auto", "--stop-threshold", "5")
        self.assertEqual((self.record("project")["review_mode"], self.record("project")["stop_threshold"]), ("auto", 5))
        self.assertEqual(self.block("project").replace("\r\n", "\n"), self.release_0_19_0_block("auto", "project").replace(
            config.END, self.line("project", 5) + "\n\n" + config.END))
        self.apply("review", "project", "--review-mode", "off", "--stop-threshold", "default")
        self.assertEqual(self.block("project"), self.release_0_19_0_block("off", "project"))
        self.assertNotIn("stop_threshold", self.record("project"))

    def test_invalid_values_commands_and_scopes_are_refused_before_writing(self):
        self.apply("install", "project", "--review-mode", "auto")
        before = self.files()
        for value in ("1", "0", "11", "-2", "-3", "2.5", "3.0", "three", "", " 3", "+3", "1e1", "auto"):
            with self.subTest(value=value):
                code, error = self.call("review", "project", "--stop-threshold", value)
                self.assertEqual((code, error["status"]), (2, "error"), error)
                self.assertIn("--stop-threshold", error["error"])
                self.assertEqual(self.files(), before)
        for command, extra in (("install", ("--component", "handoff")), ("update", ()), ("remove", ()),
                               ("model", ("--set", "scout.model=sonnet")), ("check", ()), ("show", ()),
                               ("session", ())):
            with self.subTest(command=command):
                code, error = self.call(command, "project", *extra, "--stop-threshold", "4")
                self.assertEqual((code, error["status"]), (2, "error"), error)
                self.assertIn("--stop-threshold", error["error"])
                self.assertEqual(self.files(), before)
        code, error = self.call("review", "project", "--component", "handoff", "--stop-threshold", "4")
        self.assertEqual(code, 2, error)
        self.assertEqual(self.files(), before)
        # Delegation absent from the scope: nothing installed there, or only the handoff component.
        code, error = self.call("review", "user", "--stop-threshold", "4")
        self.assertEqual(code, 2, error)
        self.assertIn("user delegation component is not installed", error["error"])
        self.apply("install", "user", "--component", "handoff")
        before = self.files()
        code, error = self.call("review", "user", "--stop-threshold", "4")
        self.assertEqual(code, 2, error)
        self.assertIn("user delegation component is not installed", error["error"])
        self.assertEqual(self.files(), before)

    def test_a_malformed_saved_stop_threshold_is_refused_on_load(self):
        self.apply("install", "project", "--review-mode", "auto")
        self.apply("review", "project", "--stop-threshold", "3")
        path = self.state_path("project")
        valid = json.loads(path.read_bytes())
        for bad in (True, False, 1, 0, 11, -2, 3.0, "3", None, [3]):
            with self.subTest(bad=bad):
                state = json.loads(json.dumps(valid))
                state["components"]["delegation"]["stop_threshold"] = bad
                path.write_bytes(config.canonical(state) + b"\n")
                before = self.files()
                for command, extra in (("check", ()), ("show", ()), ("session", ()),
                                       ("review", ("--stop-threshold", "4")), ("update", ())):
                    code, error = self.call(command, "project", *extra)
                    self.assertEqual((code, error["status"]), (2, "error"), (command, error))
                    self.assertIn("invalid saved stop threshold", error["error"])
                self.assertEqual(self.files(), before)
        path.write_bytes(config.canonical(valid) + b"\n")
        self.assertEqual(self.call("check")[1]["status"], "ok")

    def test_session_export_is_unchanged_by_a_saved_stop_threshold(self):
        for scope in ("project", "user"):
            with self.subTest(scope=scope):
                self.apply("install", scope, "--review-mode", "auto")
                code, exported = self.call("session", scope)
                self.assertEqual(code, 0, exported)
                self.apply("review", scope, "--stop-threshold", "8")
                self.assertEqual(self.call("session", scope), (0, exported))

    def test_update_model_review_mode_and_handoff_changes_keep_it_and_removal_drops_it(self):
        for scope in ("project", "user"):
            with self.subTest(scope=scope):
                self.apply("install", scope, "--component", "delegation", "--review-mode", "auto")
                self.apply("review", scope, "--stop-threshold", "6")
                steps = (("update", ("--component", "delegation")),
                         ("model", ("--set", "scout.model=sonnet")),
                         ("review", ("--review-mode", "off")),
                         ("update", ("--component", "delegation")),
                         ("review", ("--review-mode", "auto")),
                         ("install", ("--component", "handoff")),
                         ("update", ("--component", "both")),
                         ("remove", ("--component", "handoff")))
                for command, extra in steps:
                    self.apply(command, scope, *extra)
                    self.assertEqual(self.record(scope)["stop_threshold"], 6, (command, extra))
                    self.assertEqual(self.block(scope).count(self.line(scope, 6)), 1, (command, extra))
                    shown = self.call("check", scope)[1]
                    self.assertEqual((shown["status"], shown["stop_threshold"]), ("ok", 6), (command, extra))
                    self.assertEqual(self.older_template_warnings(scope), [], (command, extra))
                self.assertEqual(self.call("show", scope)[1]["choices"]["scout"]["model"], "sonnet")
                self.apply("remove", scope, "--component", "delegation")
                self.assertFalse(self.state_path(scope).exists())
                self.assertNotIn("Stop threshold", self.guidance(scope).read_text(encoding="utf-8")
                                 if self.guidance(scope).exists() else "")
                shown = self.call("show", scope)[1]
                self.assertEqual((shown["stop_threshold"], shown["stop_threshold_set"]), (2, False))
                # Removing delegation alongside handoff removes the saved value too.
                self.apply("install", scope, "--component", "both", "--review-mode", "off")
                self.apply("review", scope, "--stop-threshold", "9")
                self.apply("remove", scope, "--component", "delegation")
                self.assertNotIn("delegation", json.loads(self.state_path(scope).read_bytes())["components"])
                self.assertNotIn("Stop threshold", self.guidance(scope).read_text(encoding="utf-8"))
                self.apply("install", scope, "--component", "delegation")
                self.assertNotIn("stop_threshold", self.record(scope))
                self.apply("remove", scope, "--component", "both")

    def test_a_failed_write_rolls_back_state_and_guidance(self):
        self.apply("install", "project", "--review-mode", "auto")
        self.apply("review", "project", "--stop-threshold", "3")
        guidance, state_path = self.guidance("project"), self.state_path("project")
        for extra in (("--stop-threshold", "5"), ("--stop-threshold", "default"),
                      ("--review-mode", "off", "--stop-threshold", "4")):
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
                self.assertEqual(self.call("show")[1]["stop_threshold"], 3)

    def test_older_template_guidance_needs_setup_update_before_a_stop_threshold(self):
        legacy = ("<!-- cc-feather:begin -->\n# Feather delegation for Claude Code\n\nOlder rules.\n\n"
                  "Automatic plan review mode: {mode}\n\nOlder triggers.\n\n<!-- cc-feather:end -->")
        with mock.patch.object(config, "_policy", lambda mode, prefix="", *, scope="user": legacy.format(mode=mode)):
            self.apply("install", "project", "--review-mode", "off")
        before = self.files()
        for extra in (("--stop-threshold", "4"), ("--review-mode", "auto", "--stop-threshold", "4")):
            with self.subTest(extra=extra):
                code, error = self.call("review", "project", *extra)
                self.assertEqual(code, 2, error)
                self.assertIn("installed guidance is from an older template; run setup update first", error["error"])
                self.assertEqual(self.files(), before)
        # The mode line still switches, and setup update makes the scope editable.
        self.apply("review", "project", "--review-mode", "auto")
        self.apply("update")
        self.apply("review", "project", "--stop-threshold", "4")
        self.assertEqual(self.block("project").count(self.line("project", 4)), 1)

    def test_setup_document_describes_the_saved_stop_threshold(self):
        setup = (config.ROOT / "docs" / "setup.md").read_text(encoding="utf-8")
        section = setup.split("## Stop threshold\n", 1)[1].split("\n## ", 1)[0]
        for sentence in (
                "The Stop threshold is the number of consecutive automatic calls without a pass after which a step of the automatic review flow stops and waits for the user: one integer from 2 to 10 that applies to plan review, code review, outcome verification and Adversarial review alike, 2 by default.",
                "`review --stop-threshold <2–10|default>` saves it in project or user scope, alone or together with `--review-mode`, through the usual preview and `--apply --expected-plan` steps; it needs the delegation component installed in that scope, and `default` removes the saved value.",
                "A project's saved value overrides the user's.",
                "The configuration tool refuses any other value, `--stop-threshold` on another command, and a scope without delegation before it writes anything.",
                "A scope with a saved value states it in one sentence of its managed delegation block, in auto and in off: user scope says the Stop threshold for automatic review is K, and project scope says the Stop threshold in this project is K and that this overrides broader Feather guidance.",
                "That sentence is how main learns a saved value: the procedures read it from the loaded guidance and do not run the configuration tool at each review decision.",
                "A scope without a saved value has no such sentence, so its guidance and state stay byte-identical to what 0.19.0 writes.",
                "Delegation guidance from a template older than the one the tool can edit is not changed: `--stop-threshold` asks for setup update first.",
                "`show` and `check` report `stop_threshold`, which is the saved value or the default 2, and `stop_threshold_set`, which is false when none is saved; session export is unchanged.",
                "Setup update, `model`, switching the review mode and installing or removing the handoff component keep the saved value and its sentence; removing the delegation component removes both.",
                "Like the review mode, the Stop threshold is an agent instruction, not a hook-enforced counter."):
            with self.subTest(sentence=sentence[:40]):
                self.assertIn(sentence, section)


class ClaimsAtImplementationTests(unittest.TestCase):
    """0.23.0 ticket 01 (docs/specs/claims-at-implementation.md, Acceptance items 1, 2, 8 and 9, S2 and S12): Claims are
    decided when the user asks for implementation, by what the user names."""

    REFERENCES = config.ROOT / "skills" / "delegation" / "references"
    ADR = config.ROOT / "docs" / "adr"
    ADR_0012 = "0012-claims-are-decided-by-what-the-user-names.md"

    @classmethod
    def text(cls, path):
        return path.read_text(encoding="utf-8")

    @classmethod
    def named_plan_paragraph(cls):
        # The plan-review paragraph that decides the Plan and its Claims (Implementation Decisions "Where the rules live").
        text = cls.text(cls.REFERENCES / "plan-review.md")
        return next(block for block in text.split("\n\n") if "A plan lists its claims" in block)

    @classmethod
    def readme_section(cls, name):
        # The "Which document is the plan" part of each README, intro and rule bullets.
        text = cls.text(config.ROOT / name)
        start = {"README.md": "**Which document is the plan.**", "README.zh-TW.md": "**哪份文件是計畫。**"}[name]
        return start + "\n\n".join(text.split(start, 1)[1].split("\n\n", 2)[:2])

    @classmethod
    def readme_bullets(cls, name):
        text = cls.text(config.ROOT / name)
        start, end = {"README.md": ("## Roles and routing", "### Automatic review switch"),
                      "README.zh-TW.md": ("## 分派與預設模型", "### 自動審查開關")}[name]
        return dict(feather_support.readme_rule_bullets(text, start, end))

    # Acceptance item 1: the three named-Plan cases, the spec-or-tickets question and a spec's own Claims list.
    NAMED_PLAN = (
        "The plan is what the user names when asking for implementation, and its claims are decided then, by what the "
        "user names, in three cases.",
        "A named spec is the plan and one claim, unless it lists its own claims, which then count as listed; a spec's "
        "own claims list counts only when the spec has one.",
        "When the named spec has at least one unfinished ticket and no plan in this session already covers the named "
        "work, main first asks the user whether to implement the spec as it stands or its tickets: \"the spec\" makes "
        "the spec one claim, or its listed claims, and \"the tickets\" makes those unfinished tickets the plan.",
        "Named tickets of a spec, all or some, are the plan: each unfinished ticket in the named scope is one claim, and "
        "its `Blocked by` lines are the dependencies.",
        "A single named ticket is the plan and its one claim",
        # The question does not displace "nothing left": a named spec whose tickets are all finished asks nothing.
        "For a named spec that has tickets, the named scope is all of them, so when they are all finished nothing is "
        "left to implement and no question is asked.",
    )

    # Acceptance item 2: one Claim from a spec, and the separability note that does not stop the flow.
    ONE_CLAIM_FROM_A_SPEC = (
        "A spec without tickets and without a claims list, which refers to no tickets or claims of its own, is one "
        "claim only when it has scope and acceptance of its own; otherwise it is not yet a plan, as above.",
        "Main may say in one line that such a spec looks separable into tickets; that line does not stop the flow or "
        "wait for an answer.",
    )

    # S2: a single named ticket is named tickets of its spec for plan review, so the coverage rule reaches it too.
    SINGLE_TICKET_COVERAGE = (
        "plan review treats it as a named ticket of its spec, so every check plan review makes for named tickets of a "
        "spec, a single named ticket included, applies to it too.",
    )

    # Acceptance item 1: the rules this ticket keeps, pinned whole so removing one fails.
    KEPT = (
        "A plan lists its claims, each an independently verifiable outcome with its own acceptance; a plan that lists "
        "none is one claim.",
        "A ticket that belongs to no spec is its own plan.",
        "When every ticket in the named scope is finished, report that nothing is left to implement.",
        "The named-plan rule applies only when no plan in this session already covers the named work; otherwise that "
        "plan continues with no new plan review and keeps its count, verdicts and blockers, and a new plan that partly "
        "overlaps one inherits its unresolved verdicts and blockers for the overlapping tickets,",
        "In a resumed session, an unresolved verdict that an active handoff records for a spec's plan applies to that "
        "spec's tickets when they are named; one recorded for a ticket's plan still restricts that ticket when the "
        "whole spec is named, and without such a record no restriction carries over.",
        "Recognise a spec's tickets by an explicit link such as a `Spec:` line or parent reference, a shared feature "
        "directory, or the user naming them; ask when none or several plans match, and state the tickets used.",
        "Look first at the project's instructions, such as CLAUDE.md or AGENTS.md, and any file they point to, for "
        "where tickets live.",
        "If a spec's tickets still cannot be found, a spec that lists its own claims keeps that list without asking.",
        "A spec that lists claims and also has tickets must agree with all of them, finished or not; report a mismatch "
        "as a blocker for the user to settle.",
    )

    # Replaced 0.22.0 wording: the spec with its tickets as one Plan.
    REPLACED = (
        "A spec, or a set of its tickets, makes the spec with those tickets the plan",
    )

    def test_plan_review_states_the_three_named_plan_cases_and_the_question(self):
        paragraph = self.named_plan_paragraph()
        for sentence in self.NAMED_PLAN + self.ONE_CLAIM_FROM_A_SPEC + self.SINGLE_TICKET_COVERAGE:
            with self.subTest(sentence=sentence[:60]):
                self.assertIn(sentence, paragraph)
        for sentence in self.REPLACED:
            with self.subTest(removed=sentence[:60]):
                self.assertNotIn(sentence, self.text(self.REFERENCES / "plan-review.md"))

    def test_plan_review_keeps_the_existing_named_plan_rules(self):
        paragraph = self.named_plan_paragraph()
        for sentence in self.KEPT:
            with self.subTest(sentence=sentence[:60]):
                self.assertIn(sentence, paragraph)

    def test_the_question_comes_before_its_answers_and_the_existing_plan_rule_follows(self):
        # The question is asked only when no plan already covers the named work, which the existing-plan rule decides.
        paragraph = self.named_plan_paragraph()
        question = paragraph.index("main first asks the user whether to implement the spec as it stands or its tickets")
        self.assertLess(paragraph.index("A named spec is the plan and one claim"), question)
        self.assertLess(question, paragraph.index("The named-plan rule applies only when no plan in this session"))

    # Acceptance item 8 and S12: the preview applies the rules by reference and reports the question as open.
    PREVIEW = (
        "Identify each Plan and its Claims as [plan review](plan-review.md) does,",
        "When plan review's rules would have main ask whether to implement a named spec as it stands or its tickets, "
        "report that question as open rather than answering it: show both readings, the spec as one Claim or its "
        "listed Claims and its unfinished tickets as Claims, or mark the counts of Plans, Claims and Security-critical "
        "claims as depending on the answer.",
        "- a named spec with unfinished tickets whose spec-or-tickets question is still open, with both readings shown or "
        "its counts marked as depending on the answer;",
    )

    def test_the_preview_reports_the_spec_or_tickets_question_as_open(self):
        preview = self.text(self.REFERENCES / "preview.md")
        for sentence in self.PREVIEW:
            with self.subTest(sentence=sentence[:60]):
                self.assertIn(sentence, preview)
        command = self.text(config.ROOT / "skills" / "delegation-preview" / "SKILL.md")
        self.assertIn("this command adds no separate rules", command)

    # Acceptance items 11 and 12 for these rules, S2 and S12: both READMEs, paired.
    README_BULLETS = (
        ("A spec", "一份 spec",
         "main first asks whether you mean the spec as it stands or its tickets: \"the spec\" makes it one claim, or its "
         "listed claims, and \"the tickets\" makes those unfinished tickets the plan.",
         "主 Agent 會先問你要實作 spec 本身還是它的 ticket：答「spec」，spec 就是一個 claim，或以它列出的 claim 為準；答「ticket」，"
         "這些未完成的 ticket 就是計畫。"),
        ("A spec", "一份 spec",
         "A spec written earlier with its own claims table keeps it: naming it and answering \"the spec\" keeps its "
         "listed claims, which must still agree with its tickets.",
         "先前寫成、自己列了 claim 表的 spec 會保留它：指名它並回答「spec」時，沿用它列出的 claim，且仍須與它的 ticket 一致。"),
        ("Tickets of a spec, all or some", "一份 spec 的 ticket（全部或部分）",
         "those tickets are one plan, reviewed once. Each unfinished ticket among them is one claim, and its `Blocked by` "
         "lines are its dependencies.",
         "這些 ticket 是一份計畫，只做一次計畫審查。其中每張未完成的 ticket 是一個 claim，它的 `Blocked by` 行就是相依關係。"),
        ("A single ticket", "單一 ticket",
         "that ticket is the plan and its one claim",
         "該 ticket 就是計畫，也是它唯一的 claim"),
        ("A single ticket", "單一 ticket",
         "Plan review treats it as a named ticket of its spec, just as when several are named.",
         "計畫審查把它當作該 spec 被指名的 ticket，和指名多張時一樣。"),
        ("A ticket that belongs to no spec", "不屬於任何 spec 的 ticket",
         "**A spec without tickets** keeps the claims it lists or, when it lists none, is one claim provided it has scope "
         "and acceptance of its own; main may say in one line that it looks separable into tickets, without stopping.",
         "**沒有 ticket 的 spec** 沿用它列出的 claim；沒有列出時，只要有自己的範圍與驗收條件，整份就是一個 claim。主 Agent 可能用一句話"
         "提醒它看起來可以拆成 ticket，但不會因此停下。"),
        ("Example", "例子",
         "\"Implement the login spec\" makes main ask first: \"the tickets\" makes one plan with three claims, with one "
         "plan review, and 03 waits for 02; \"the spec\" makes the whole spec one claim. \"Implement tickets 02 and 03\" "
         "makes one plan with two claims.",
         "「實作 login spec」時主 Agent 會先問你：答「ticket」是一份有三個 claim 的計畫，計畫審查一次，03 等 02 完成；答「spec」則整份 "
         "spec 是一個 claim。「實作 ticket 02 和 03」是一份有兩個 claim 的計畫。"),
        ("Example", "例子",
         "`docs/specs/logout.md`, with no tickets and no claims list, is one claim when you name it.",
         "沒有 ticket、也沒有列 claim 的 `docs/specs/logout.md`，指名它就是一個 claim。"),
    )

    README_INTRO = (
        "naming it is your agreement to it, and what you name decides its claims.",
        "指名即代表你同意它，指名什麼也決定了它有哪些 claim。",
    )

    # S12: the READMEs state the limits of these rules where this ticket's text makes a claim.
    README_LIMITS = (
        "These rules are instructions to main, not enforced by any tool; tests only keep the texts consistent.",
        "這些規則是給主 Agent 的指示，沒有任何工具強制執行；測試只確保各文件說法一致。",
    )

    README_PREVIEW = (
        "For a named spec with unfinished tickets, the preview does not answer whether you mean the spec or its tickets: "
        "it shows both readings, or marks its counts as depending on your answer.",
        "指名的 spec 還有未完成的 ticket 時，預覽不替你回答要實作 spec 還是它的 ticket：它會列出兩種解讀，或標示它的數量取決於你怎麼回答。",
    )

    # Replaced README wording: the spec with its tickets as one plan.
    README_REPLACED = (
        ("README.md", "the spec with those tickets is one plan"),
        ("README.md", "- **A spec, or some of its tickets:**"),
        ("README.zh-TW.md", "該 spec 連同這些 ticket 是一份計畫"),
        ("README.zh-TW.md", "- **一份 spec，或其中幾張 ticket：**"),
    )

    def test_readmes_explain_the_three_cases_with_an_example_in_both_languages(self):
        english, chinese = self.readme_bullets("README.md"), self.readme_bullets("README.zh-TW.md")
        for label, zh_label, en, zh in self.README_BULLETS:
            with self.subTest(label=label, sentence=en[:50]):
                self.assertIn(en, english[label])
                self.assertIn(zh, chinese[zh_label])
        for name, sentence in zip(("README.md", "README.zh-TW.md"), self.README_INTRO):
            with self.subTest(readme=name, intro=sentence[:40]):
                self.assertIn(sentence, self.readme_section(name))
        for name, sentence in self.README_REPLACED:
            with self.subTest(readme=name, removed=sentence[:40]):
                self.assertNotIn(sentence, self.text(config.ROOT / name))

    def test_readmes_state_the_limits_and_the_open_question_in_the_preview(self):
        for name, limits, preview, heading in (
                ("README.md", self.README_LIMITS[0], self.README_PREVIEW[0], "### Delegation preview"),
                ("README.zh-TW.md", self.README_LIMITS[1], self.README_PREVIEW[1], "### 分派預覽")):
            text = self.text(config.ROOT / name)
            with self.subTest(readme=name, part="limits"):
                self.assertIn(limits, self.readme_section(name))
            with self.subTest(readme=name, part="preview"):
                self.assertIn(preview, text.split(heading, 1)[1].split("\n### ", 1)[0])

    # Acceptance item 9 and S1: the glossary entries, aligned with the procedures.
    GLOSSARY = {
        "Plan": (
            "It is what the user names when asking for implementation, and its Claims are decided then: a named spec is "
            "one Claim unless it lists its own, and when it has unfinished tickets and no Plan in this session already "
            "covers the work, main first asks whether to implement the spec or its tickets; named tickets of a spec, all "
            "or some, form one Plan with each unfinished ticket as one Claim; a single named ticket is its own Plan and "
            "one Claim.",
            "When the Plan is tickets of a spec, a single named ticket included, the spec serves plan review only as a "
            "checklist for what the tickets must carry.",
        ),
        "Claim": (
            "One independently verifiable outcome with its own acceptance: a named spec without a Claims list of its "
            "own, a single named ticket, one a spec lists itself, or one unfinished ticket among those named.",
            "A spec lists Claims only when the user asked for them.",
            "Code review and outcome verification each judge one Claim, reading what it is written in, the parts of a "
            "spec it cites and, for a Claim a spec lists, the spec's parts that state they hold for every Claim.",
        ),
        "Security-critical claim": (
            # Ticket 04 aligned the timing with off mode's classification before dispatch (S7).
            "It is identified when main writes a Plan it proposes itself, such as one for Unplanned work, or, otherwise, "
            "before the Plan's first review and before its implementation is dispatched.",
            "A spec main drafts at the user's request is not a Plan main proposes itself.",
        ),
    }

    # Wording of the uncommitted revision that the alignment replaced.
    GLOSSARY_REPLACED = {
        "Plan": ("the spec serving only to check that they cover it",),
        "Claim": ("the parts of a spec it cites or that state they hold for every Claim",),
        "Security-critical claim": ("when main lists the Plan's Claims itself",
                                    "is not thereby a Plan whose Claims main lists"),
    }

    def test_glossary_entries_state_the_rules_and_match_the_procedures(self):
        entries = feather_support.glossary_entries(self.text(config.ROOT / "CONTEXT.md"))
        for term, sentences in self.GLOSSARY.items():
            for sentence in sentences:
                with self.subTest(term=term, sentence=sentence[:60]):
                    self.assertIn(sentence, entries[term])
        for term, sentences in self.GLOSSARY_REPLACED.items():
            for sentence in sentences:
                with self.subTest(term=term, removed=sentence[:60]):
                    self.assertNotIn(sentence, entries[term])

    # Acceptance item 9: ADR 0012 records the decision and its rejected options; ADR 0005 gains a note only.
    ADR_0012_DECISIONS = (
        "**Claims are decided at implementation by what the user names.**",
        "**A ticket's Plan is its own content, and the spec is a checklist for plan review.**",
        "**Reviews and implementation read the Claim and its citations.**",
        "**Main does not cut Claims while drafting.**",
        "Main first asks whether to implement the spec as it stands or its tickets",
        "only when the named spec has at least one unfinished ticket and no Plan in this session already covers the "
        "named work",
        "This amends [ADR 0005](0005-the-named-plan-and-its-tickets.md)",
    )

    ADR_0012_REJECTED = (
        "**Ask at drafting time whether to list Claims**",
        "**Main writes a Claims table into specs it drafts**",
        "**Each ticket its own Plan when several are named**",
        "**The whole spec as context for a single ticket**",
        "**Plan review reads only the tickets**",
        "**Security invariants kept only in briefs and handoffs**",
        "**The implementer reads the whole spec while reviewers read the ticket**",
    )

    ADR_0005_NOTE = (
        "(Amended by ADR 0012: the single named ticket's spec is no longer context for its reviews; a named spec with "
        "unfinished tickets prompts a question, whether to implement the spec as it stands or its tickets, unless a "
        "Plan in this session already covers the named work; and when tickets are named, the spec is a checklist for "
        "plan review, not part of the Plan's content.)"
    )

    def test_adr_0012_records_the_decision_and_its_rejected_options(self):
        decision = self.text(self.ADR / self.ADR_0012)
        options = decision.split("## Considered Options", 1)[1].split("\n## ", 1)[0]
        for phrase in self.ADR_0012_DECISIONS:
            with self.subTest(decision=phrase[:60]):
                self.assertIn(phrase, decision)
        for phrase in self.ADR_0012_REJECTED:
            with self.subTest(rejected=phrase[:60]):
                self.assertIn(phrase, options)

    def test_adr_0005_gains_its_amendment_note_and_keeps_its_text(self):
        lines = self.text(self.ADR / "0005-the-named-plan-and-its-tickets.md").splitlines()
        self.assertIn(self.ADR_0005_NOTE, lines)
        # The original decision stays as written; the note names what changed.
        self.assertTrue(any("a single named ticket is the Plan with its spec as context" in line for line in lines))
        self.assertTrue(any("- **Treat every ticket as its own Plan even when the whole spec is named**" in line
                            for line in lines))


class SpecChecklistTests(unittest.TestCase):
    """0.23.0 ticket 02 (docs/specs/claims-at-implementation.md, Acceptance item 3 and the parts of items 11 and 12 for
    this rule, Implementation Decisions "The checklist" and "Citations", S1, S2, S3, S6, S12 and Residual R1): plan review
    over tickets of a spec uses the spec as a checklist, and a citation is explicit."""

    REFERENCES = config.ROOT / "skills" / "delegation" / "references"

    @classmethod
    def text(cls, path):
        return path.read_text(encoding="utf-8")

    @classmethod
    def plan_review_paragraphs(cls):
        return cls.text(cls.REFERENCES / "plan-review.md").split("\n\n")

    @classmethod
    def checklist_paragraph(cls):
        return next(block for block in cls.plan_review_paragraphs()
                    if block.startswith("When the plan is one or more tickets of a spec,"))

    @classmethod
    def readme_bullets(cls, name):
        text = cls.text(config.ROOT / name)
        start, end = {"README.md": ("## Roles and routing", "### Automatic review switch"),
                      "README.zh-TW.md": ("## 分派與預設模型", "### 自動審查開關")}[name]
        return dict(feather_support.readme_rule_bullets(text, start, end))

    # Acceptance item 3 and S2: what plan review over tickets receives, and what it judges per ticket and across them.
    RECEIVES = (
        "When the plan is one or more tickets of a spec, a single named ticket included, plan review receives the named "
        "tickets and the spec and, for the coverage and invariant-citation checks only, the spec's other tickets, "
        "finished or not.",
        "It judges each named ticket's outcome, acceptance and dependencies and, when several are named, checks the "
        "tickets against each other.",
    )

    # Acceptance item 3 and Implementation Decisions "The checklist": the spec is a checklist, not Plan content and
    # not a Claim's acceptance.
    CHECKLIST = (
        "It uses the spec only as a checklist for what the tickets must carry: the spec is not part of the plan's "
        "content, and it is not a claim's acceptance, so a ticket's reviews after plan review do not read the parts of "
        "the spec it does not cite.",
    )

    # Acceptance item 3 and S3: the scope, Out of Scope and citation parts run for any named tickets of a spec.
    PARTS = (
        "The checklist's scope, Out of Scope and citation parts run for any named tickets of a spec, a single named "
        "ticket included: every named ticket stays within the spec's scope and Out of Scope and cites the spec's "
        "decisions and security invariants that apply to it, and an Out of Scope line of the spec that limits what a "
        "ticket may change is part of what that ticket must cite.",
    )

    # S2: coverage whenever the named and finished tickets are all of the spec's tickets; every invariant cited.
    COVERAGE = (
        "The coverage part runs whenever the named tickets together with the finished ones are all of the spec's "
        "tickets, a single named ticket included: together they must cover the spec's outcome.",
        "Every plan review over tickets of a spec also checks that each of the spec's security invariants is cited by "
        "at least one of its tickets, named or not.",
    )

    BLOCKER = (
        "A missing coverage or citation is a blocker, an uncited security invariant included.",
    )

    # Implementation Decisions "Citations" and S6: the citation definition every later ticket uses.
    CITATIONS = (
        "A citation is explicit: a named section or heading, a numbered item or an identifier such as `C1 item 1`, `D3` "
        "or `S2`, and a ticket that needs a whole section cites the section; a `Spec:` line, a parent reference or a "
        "shared directory is not a citation.",
        "A reviewer follows a citation to the cited part only.",
        "A citation that does not resolve to exactly one part of the spec is a blocker.",
    )

    # S1: a spec's own listed Claims carry what applies to them.
    LISTED_CLAIMS = (
        "When a spec lists its own claims, plan review checks that every decision, Out of Scope line and security "
        "invariant that applies to a listed claim is in the claim's own text, a part it cites or a part the spec states "
        "holds for every claim; a missing one is a blocker.",
    )

    # Residual R1: a ticket with no link to a spec gets no checklist.
    NO_SPEC = (
        "A ticket with no link to a spec, no `Spec:` line, parent reference or shared directory, is its own plan and "
        "gets no checklist; the user's naming of it is the agreement.",
    )

    # Step 2 supplies what the checklist needs.
    STEP_2 = "For tickets of a spec, also supply the spec and the spec's other tickets, as described above."

    def test_plan_review_over_tickets_uses_the_spec_as_a_checklist(self):
        paragraph = self.checklist_paragraph()
        for sentence in (self.RECEIVES + self.CHECKLIST + self.PARTS + self.COVERAGE + self.BLOCKER + self.CITATIONS
                         + self.LISTED_CLAIMS + self.NO_SPEC):
            with self.subTest(sentence=sentence[:60]):
                self.assertIn(sentence, paragraph)

    def test_the_checklist_follows_the_named_plan_rules_and_precedes_classification(self):
        # The checklist builds on the named-Plan cases and comes before the classification paragraph.
        paragraphs = self.plan_review_paragraphs()
        named = next(index for index, block in enumerate(paragraphs) if "A plan lists its claims" in block)
        checklist = paragraphs.index(self.checklist_paragraph())
        classify = next(index for index, block in enumerate(paragraphs) if block.startswith("Classify every plan's claims"))
        self.assertEqual(checklist, named + 1)
        self.assertEqual(classify, checklist + 1)
        # The kept single-ticket sentence still points every named-ticket check at a single named ticket.
        self.assertIn("so every check plan review makes for named tickets of a spec, a single named ticket included, "
                      "applies to it too.", paragraphs[named])

    def test_step_2_supplies_the_spec_and_its_other_tickets(self):
        step = next(line for line in self.text(self.REFERENCES / "plan-review.md").splitlines() if line.startswith("2. "))
        self.assertIn("Supply a stable plan with outcome, scope/exclusions, claims with their acceptance, ownership, "
                      "dependencies and relevant rollback. " + self.STEP_2, step)

    # Acceptance items 11 and 12 for this rule, S12 and Residual R1: both READMEs, paired.
    README_BULLETS = (
        ("The spec as a checklist", "spec 作為檢查清單",
         "when the plan is tickets of a spec, a single ticket included, plan review receives the named tickets and the "
         "spec and, only for the coverage and invariant checks below, the spec's other tickets, finished or not.",
         "計畫是某份 spec 的 ticket 時（包括只指名一張），計畫審查會拿到指名的 ticket 與 spec；只為了下面的涵蓋與不變條件檢查，"
         "也會拿到該 spec 的其他 ticket，不論是否完成。"),
        ("The spec as a checklist", "spec 作為檢查清單",
         "It judges each ticket's outcome, acceptance and dependencies, and the tickets against each other when several "
         "are named.",
         "它判斷每張 ticket 的結果、驗收條件與相依關係，指名多張時也檢查 ticket 彼此之間。"),
        ("The spec as a checklist", "spec 作為檢查清單",
         "The spec is not part of the plan, only a checklist: each named ticket must stay within the spec's scope and "
         "Out of Scope and cite the spec's decisions and security invariants that apply to it, including any Out of "
         "Scope line that limits what it may change.",
         "spec 不是計畫的一部分，只是檢查清單：每張指名的 ticket 必須留在 spec 的範圍與 Out of Scope 之內，並引用 spec 中適用於它的"
         "決定與安全不變條件，包括限制它能改什麼的 Out of Scope 條目。"),
        ("The spec as a checklist", "spec 作為檢查清單",
         "When the named tickets together with the finished ones are all of the spec's tickets, they must also cover the "
         "spec's outcome, so naming the last unfinished ticket alone runs this check too.",
         "指名的 ticket 加上已完成的 ticket 就是 spec 的全部 ticket 時，它們還必須涵蓋 spec 的結果，所以只指名最後一張未完成的 "
         "ticket 也會做這項檢查。"),
        ("The spec as a checklist", "spec 作為檢查清單",
         "Every plan review over tickets of a spec also checks that each of the spec's security invariants is cited by at "
         "least one of its tickets, named or not. A missing coverage or citation is a blocker.",
         "每次針對 spec 的 ticket 做的計畫審查，也會檢查 spec 的每條安全不變條件至少被它的一張 ticket 引用，不論那張 ticket 是否"
         "被指名。缺少涵蓋或引用都是阻擋事項。"),
        ("The spec as a checklist", "spec 作為檢查清單",
         "For a spec that lists its own claims, plan review checks that each decision, Out of Scope line and security "
         "invariant applying to a listed claim is in the claim's own text, a part it cites or a part the spec says holds "
         "for every claim; a missing one is a blocker.",
         "spec 自己列了 claim 時，計畫審查會檢查適用於每個列出 claim 的決定、Out of Scope 條目與安全不變條件，都寫在該 claim "
         "自己的文字、它引用的部分，或 spec 聲明適用於每個 claim 的部分；缺少就是阻擋事項。"),
        ("Citations", "引用",
         "a citation is explicit: a named section or heading, a numbered item or an identifier such as `C1 item 1`, `D3` "
         "or `S2`; a ticket that needs a whole section cites the section. A `Spec:` line, a parent reference or a shared "
         "directory is not a citation.",
         "引用必須明確：具名的段落或標題、編號項目，或 `C1 item 1`、`D3`、`S2` 這類識別碼；需要整個段落的 ticket 就引用那個段落。"
         "`Spec:` 行、parent 參照或同一個目錄都不算引用。"),
        ("Citations", "引用",
         "A reviewer follows a citation to the cited part only, and a citation that does not resolve to exactly one part "
         "of the spec is a blocker at plan review.",
         "審查者只會順著引用讀到被引用的那個部分；引用無法對應到 spec 中恰好一個部分時，在計畫審查就是阻擋事項。"),
        # S12: the checklist's limits.
        ("Checklist limits", "檢查清單的限制",
         "the checklist runs at plan review, on the spec and tickets as written then; its coverage check runs only when "
         "the named and finished tickets are all of the spec's tickets; the spec is not a claim's acceptance, so a "
         "ticket's reviews after plan review read only the ticket and the spec parts it cites; and these rules are "
         "instructions to the model, not enforced by any tool.",
         "檢查清單在計畫審查時執行，看的是當時寫下的 spec 與 ticket；涵蓋檢查只在指名與已完成的 ticket 就是 spec 的全部 ticket "
         "時執行；spec 不是 claim 的驗收條件，所以計畫審查之後，ticket 的各項審查只讀該 ticket 與它引用的 spec 部分；這些規則是"
         "給模型的指示，沒有任何工具強制執行。"),
        # Residual R1.
        ("A ticket that belongs to no spec", "不屬於任何 spec 的 ticket",
         ", with no `Spec:` line, parent reference or shared directory linking it to one, is its own plan and gets no "
         "checklist: naming it is your agreement to it.",
         "（沒有 `Spec:` 行、parent 參照或同一個目錄把它連到某份 spec）自成一份計畫，不做檢查清單：指名它就代表你同意它。"),
    )

    # The 0.22.0 bullet opening that Residual R1's statement replaces.
    README_REPLACED = (
        ("README.md", "- **A ticket that belongs to no spec** is its own plan."),
        ("README.zh-TW.md", "- **不屬於任何 spec 的 ticket** 自成一份計畫。"),
    )

    def test_readmes_describe_the_checklist_its_limits_and_residual_r1_in_both_languages(self):
        english, chinese = self.readme_bullets("README.md"), self.readme_bullets("README.zh-TW.md")
        for label, zh_label, en, zh in self.README_BULLETS:
            with self.subTest(label=label, sentence=en[:50]):
                self.assertIn(en, english[label])
                self.assertIn(zh, chinese[zh_label])
        for name, sentence in self.README_REPLACED:
            with self.subTest(readme=name, removed=sentence[:40]):
                self.assertNotIn(sentence, self.text(config.ROOT / name))


class ReadingSetTests(unittest.TestCase):
    """0.23.0 ticket 03 (docs/specs/claims-at-implementation.md, Acceptance item 4, the `Spec:` part of item 10 and the
    parts of items 11 and 12 for this rule, Implementation Decisions "Where the rules live" and "Citations", Testing
    Decisions, S1, S3, S4, S5 and S12): what a Claim's reviews and implementation read."""

    REFERENCES = config.ROOT / "skills" / "delegation" / "references"
    REVIEWS = ("code-review.md", "outcome-verification.md", "adversarial-review.md")

    @classmethod
    def text(cls, path):
        return path.read_text(encoding="utf-8")

    @classmethod
    def step(cls, name, number):
        return next(line for line in cls.text(cls.REFERENCES / name).splitlines() if line.startswith(f"{number}. "))

    @classmethod
    def readme_bullets(cls, name):
        text = cls.text(config.ROOT / name)
        start, end = {"README.md": ("## Roles and routing", "### Automatic review switch"),
                      "README.zh-TW.md": ("## 分派與預設模型", "### 自動審查開關")}[name]
        return dict(feather_support.readme_rule_bullets(text, start, end))

    # Acceptance item 4, S1 and S3: the material, stated in the same words wherever a brief is built from it.
    CORE = (
        "the text the claim is written in and the parts of a spec it cites, an Out of Scope line that limits what the "
        "claim may change included, and, only for a claim a spec lists, the spec's parts that state they hold for every "
        "claim; no other part of a spec is supplied, and the whole spec only when the spec itself is the claim"
    )

    READS = "A claim's reading set is what its implementation and every review of it read: " + CORE + "."

    # Implementation Decisions "Citations": ticket 02's definition, used by reference.
    CITES = (
        "Citations are as [plan review](plan-review.md) defines them, so a `Spec:` line, a parent reference or a shared "
        "directory brings in no part of a spec, and the brief tells the role to follow a citation to the cited part only."
    )

    # S5: confirmed unchanged before dispatch; briefs use only the recorded set.
    RECORDED = (
        "Before dispatch, main confirms that the reading set is unchanged and supplies only the reading set it recorded, "
        "as [review state](review-state.md)'s Reading set describes."
    )

    # The step-2 sentences that now name the reading set where the single ticket's spec was context.
    SUPPLY = {
        "code-review.md": "Supply the claim as identified for the plan (see [plan review](plan-review.md)), its reading "
                          "set, the base revision to diff against, the file scope including untracked new files, and the "
                          "acceptance results.",
        "outcome-verification.md": "Supply the exact claim as identified for the plan (see [plan review](plan-review.md)) "
                                   "with the claim's acceptance checks, its reading set, the relevant diff or paths and the "
                                   "commands main ran.",
        # Kept and pinned: the Adversarial review brief keeps carrying the invariants and targets (S4).
        "adversarial-review.md": "Supply the claim as identified for the plan (see [plan review](plan-review.md)), the "
                                 "commit under attack and its base revision, the claim's security invariants, each test "
                                 "target with where it runs (host, container or virtual machine), the environment "
                                 "variables it starts with, how to start and reset it, its synthetic data, its allowed "
                                 "effects and the dependencies it can reach, any isolated environment the user named for "
                                 "it, and the gaps earlier calls for this claim left open.",
    }

    # S4: exactly the invariants and targets in the reading set, and main's findings to the implementer go to reviewers.
    SECURITY_CRITICAL = (
        "For a Security-critical claim, the security invariants and test targets the brief carries are exactly those "
        "written in its reading set, and the brief also carries every finding or disposition main gave the claim's "
        "implementer, masked and limited as [Adversarial review](adversarial-review.md) step 7 sets for findings it "
        "passes to code review or outcome verification."
    )

    ADVERSARIAL = (
        "The security invariants and test targets the brief carries are exactly those written in the claim's reading "
        "set, together with any target the user's own command arguments name as step 3 allows, and the brief also "
        "carries every finding or disposition main gave the claim's implementer, with any secret, credential or real "
        "data masked as step 7 requires."
    )

    # S4: a cited part is part of the approved plan for Adversarial review's targets.
    APPROVED_PLAN = "A spec part the claim cites counts as part of the plan the user approved, for these targets."
    KEPT_PROVENANCE = ("Every target in a brief traces to a plan the user approved or to the user's own command "
                       "arguments.")

    KEPT_INVARIANTS = "The brief for a Security-critical claim also carries its security invariants."

    # Replaced 0.22.0 wording: the single ticket's spec as context, in the procedures.
    REPLACED = (
        ("code-review.md", "when the plan is a single ticket, its spec as context"),
        ("code-review.md", "the plan or spec it implements"),
        ("outcome-verification.md", "its spec as context when the plan is a single ticket"),
        ("plan-review.md", "with its spec supplied as context to plan review, code review and outcome verification"),
    )

    # S5: review state records and confirms the reading set.
    READING_SET = (
        "- **Reading set.** " + READS,
        "Citations are as [plan review](plan-review.md) defines them, and a `Spec:` line, a parent reference or a shared "
        "directory brings in no part of a spec.",
        "A Security-critical claim's security invariants and test targets are those written in its reading set.",
        "When plan review returns READY, main records each claim's reading set, by content or by hash; when no READY was "
        "given for the claim in this session, as in off mode, after a waived plan review or for an explicit call, main "
        "records it at the claim's first dispatch in this session.",
        "Before dispatching the claim's implementation or any of its reviews, main confirms that the reading set is "
        "unchanged, and the briefs use only the recorded reading set.",
        "The status and note main writes under Ticket status are not a change to the reading set.",
        "A change the user did not authorise is a material deviation, as [plan review](plan-review.md) step 5 describes; "
        "after a change the user authorises, main records the changed reading set before the claim's next dispatch.",
    )

    PLAN_REVIEW_READY = ("Main records each claim's reading set at that READY, as [review state](review-state.md)'s "
                         "Reading set describes.")

    # Acceptance item 4: the implementing Assignment's brief carries the same material.
    IMPLEMENTING = (
        "The brief of an Assignment that implements a claim carries the claim's reading set, as [review state]"
        "(references/review-state.md)'s Reading set describes: " + CORE + ".",
        "Citations are as [plan review](references/plan-review.md) defines them.",
        "This is the same material the claim's code review, outcome verification and Adversarial review read; main "
        "confirms it unchanged before dispatch and supplies only the reading set it recorded.",
        "For a Security-critical claim, the brief carries exactly the security invariants and test targets written in "
        "that reading set, and any finding or disposition main gives the implementer also goes to the claim's code "
        "review, outcome verification and Adversarial review.",
    )

    # Acceptance item 10, the `Spec:` part.
    TRACKER = ("- Each ticket starts with a `Spec: docs/specs/<feature-slug>.md` line linking it to its spec; that line "
               "records where the ticket came from and is not a citation of the whole spec.")

    def test_each_review_states_what_a_claim_s_reviews_read(self):
        for name in self.REVIEWS:
            step = self.step(name, 2)
            for sentence in (self.SUPPLY[name], self.READS, self.CITES, self.RECORDED):
                with self.subTest(procedure=name, sentence=sentence[:60]):
                    self.assertIn(sentence, step)
            with self.subTest(procedure=name, part="order"):
                self.assertLess(step.index(self.SUPPLY[name]), step.index(self.READS))

    def test_the_single_ticket_spec_as_context_is_gone(self):
        for name, sentence in self.REPLACED:
            with self.subTest(procedure=name, removed=sentence[:50]):
                self.assertNotIn(sentence, self.text(self.REFERENCES / name))
        for name in self.REVIEWS + ("plan-review.md", "review-state.md"):
            with self.subTest(procedure=name, removed="spec as context"):
                self.assertNotIn("spec as context", self.text(self.REFERENCES / name))
                self.assertNotIn("spec supplied as context", self.text(self.REFERENCES / name))
        # The kept single-ticket sentence still reads as one: the Plan, its one Claim, and the named-ticket checks.
        self.assertIn("A single named ticket is the plan and its one claim; plan review treats it as a named ticket of "
                      "its spec,", self.text(self.REFERENCES / "plan-review.md"))

    def test_security_critical_briefs_carry_exactly_the_invariants_and_targets_in_the_reading_set(self):
        for name in ("code-review.md", "outcome-verification.md"):
            step = self.step(name, 2)
            with self.subTest(procedure=name):
                self.assertIn(self.KEPT_INVARIANTS + " " + self.SECURITY_CRITICAL, step)
        step = self.step("adversarial-review.md", 2)
        self.assertIn(self.ADVERSARIAL, step)
        self.assertLess(step.index(self.SUPPLY["adversarial-review.md"]), step.index(self.ADVERSARIAL))
        step_3 = self.step("adversarial-review.md", 3)
        self.assertIn(self.KEPT_PROVENANCE + " " + self.APPROVED_PLAN, step_3)

    def test_review_state_records_and_confirms_the_reading_set(self):
        bullet = feather_support.review_rules_source("review-state.md#Reading set")
        for sentence in self.READING_SET:
            with self.subTest(sentence=sentence[:60]):
                self.assertIn(sentence, bullet)
        # The bullet sits in Validity and completion, after what a pass covers.
        text = self.text(self.REFERENCES / "review-state.md")
        section = text.split("## Validity and completion", 1)[1].split("\n## ", 1)[0]
        self.assertIn(bullet, section)
        self.assertLess(section.index("- **What a pass covers.**"), section.index("- **Reading set.**"))
        self.assertIn(self.PLAN_REVIEW_READY, self.step("plan-review.md", 5))

    def test_the_implementing_brief_carries_the_same_material(self):
        skill = self.text(config.ROOT / "skills" / "delegation" / "SKILL.md")
        dispatch = skill.split("## Dispatch", 1)[1].split("\n## ", 1)[0]
        for sentence in self.IMPLEMENTING:
            with self.subTest(sentence=sentence[:60]):
                self.assertIn(sentence, dispatch)

    def test_every_claim_parts_are_read_only_for_a_listed_claim(self):
        # S1: wherever this rule names the parts that hold for every Claim, it limits them to a Claim a spec lists.
        places = {name: self.text(self.REFERENCES / name) for name in self.REVIEWS + ("review-state.md",)}
        places["SKILL.md"] = self.text(config.ROOT / "skills" / "delegation" / "SKILL.md")
        for name, text in places.items():
            with self.subTest(place=name):
                self.assertGreater(text.count("hold for every claim"), 0)
                self.assertEqual(text.count("hold for every claim"),
                                 text.count("only for a claim a spec lists, the spec's parts that state they hold for "
                                            "every claim"))
        claim = feather_support.glossary_entries(self.text(config.ROOT / "CONTEXT.md"))["Claim"]
        self.assertIn("for a Claim a spec lists, the spec's parts that state they hold for every Claim", claim)

    def test_the_tracker_note_says_a_spec_line_is_not_a_citation(self):
        line = next(line for line in self.text(config.ROOT / "docs" / "agents" / "issue-tracker.md").splitlines()
                    if line.startswith("- Each ticket starts with"))
        self.assertTrue(line.startswith(self.TRACKER), line)

    # Acceptance items 11 and 12 for this rule, and S12: both READMEs, paired.
    README_BULLETS = (
        ("What a review reads", "審查讀什麼",
         "a claim's code review, outcome verification and Adversarial review, and the implementer of it, read the same "
         "reading set: the text the claim is written in and the spec parts it cites, including any Out of Scope line "
         "that limits it, and, only for a claim a spec lists, the parts the spec says hold for every claim.",
         "claim 的程式碼審查、結果驗證與對抗式審查，以及實作它的角色，讀的是同一組閱讀範圍：claim 所寫的文字與它引用的 spec 部分，"
         "包括限制它的 Out of Scope 條目；只有 spec 自己列出的 claim，才另外讀 spec 聲明適用於每個 claim 的部分。"),
        ("What a review reads", "審查讀什麼",
         "The whole spec is read only when the spec itself is the claim; a ticket's `Spec:` line records where the ticket "
         "came from and brings no part of the spec in.",
         "只有 spec 本身就是 claim 時才讀整份 spec；ticket 的 `Spec:` 行只記錄 ticket 從哪裡來，不會帶進 spec 的任何部分。"),
        ("What a review reads", "審查讀什麼",
         "For a Security-critical claim, the security invariants and test targets the briefs carry are exactly those "
         "written there, and any finding main gives the implementer also goes to the reviewers.",
         "安全關鍵 claim 的 brief 所帶的安全不變條件與測試目標，恰好就是寫在這組範圍裡的那些；主 Agent 給實作者的任何發現，"
         "也會交給審查者。"),
        ("What a review reads", "審查讀什麼",
         "Main records the reading set when plan review returns READY, or at the claim's first dispatch in a session "
         "without one, and confirms it is unchanged before each implementation or review; a change you did not "
         "authorise is a material deviation, while the ticket status and note main writes are not a change.",
         "主 Agent 在計畫審查回傳 READY 時記錄這組閱讀範圍，這個 session 沒有 READY 時則在該 claim 第一次派出時記錄，並在每次"
         "實作或審查前確認它沒有改變；未經你授權的變更是重大偏離，主 Agent 自己寫的 ticket 狀態與註記則不算變更。"),
        # S12: the limit of this rule.
        ("What a review reads", "審查讀什麼",
         "These are instructions to the model: a role can still open the whole spec file, and only its brief keeps it to "
         "the cited parts.",
         "這些是給模型的指示：角色仍可能打開整份 spec 檔案，只有它的 brief 讓它停在被引用的部分。"),
        ("A single ticket", "單一 ticket",
         "that ticket is the plan and its one claim. Plan review treats it",
         "該 ticket 就是計畫，也是它唯一的 claim。計畫審查把它當作"),
        ("Example", "例子",
         "\"Implement ticket 02\" in a fresh session makes ticket 02 the plan and its one claim, whose reviews read ticket "
         "02 and the parts of `login.md` it cites.",
         "在新 session 中「實作 ticket 02」，則 ticket 02 是計畫，也是它唯一的 claim，它的審查讀 ticket 02 與它引用的 "
         "`login.md` 部分。"),
    )

    # Replaced 0.22.0 README wording: the single ticket's spec as context, and the example's `login.md` as context.
    README_REPLACED = (
        ("README.md", "with its spec given as context to plan review, code review and outcome verification"),
        ("README.md", "with `login.md` as context"),
        ("README.zh-TW.md", "其 spec 作為背景提供給計畫審查、程式碼審查與結果驗證"),
        ("README.zh-TW.md", "`login.md` 作為背景"),
    )

    def test_readmes_state_what_a_review_reads_in_both_languages(self):
        english, chinese = self.readme_bullets("README.md"), self.readme_bullets("README.zh-TW.md")
        for label, zh_label, en, zh in self.README_BULLETS:
            with self.subTest(label=label, sentence=en[:50]):
                self.assertIn(en, english[label])
                self.assertIn(zh, chinese[zh_label])
        for name, sentence in self.README_REPLACED:
            with self.subTest(readme=name, removed=sentence[:40]):
                self.assertNotIn(sentence, self.text(config.ROOT / name))
        # The new bullet follows the citation definition it relies on.
        for name, citations, reads in (("README.md", "- **Citations:**", "- **What a review reads:**"),
                                       ("README.zh-TW.md", "- **引用：**", "- **審查讀什麼：**")):
            text = self.text(config.ROOT / name)
            with self.subTest(readme=name, part="order"):
                self.assertLess(text.index(citations), text.index(reads))


class DraftingSpecTests(unittest.TestCase):
    """0.23.0 ticket 04 (docs/specs/claims-at-implementation.md, Solution's drafting rule, Acceptance items 5 and 6, the
    Claims-table part of item 10 and the parts of items 11 and 12 for these rules, Implementation Decisions "Where the
    rules live" and "Unchanged", S4, S7, S8 and S12): drafting a spec lists no Claims, and when Claims are classified."""

    REFERENCES = config.ROOT / "skills" / "delegation" / "references"

    @classmethod
    def text(cls, path):
        return path.read_text(encoding="utf-8")

    @classmethod
    def plan_review_paragraph(cls, opening):
        text = cls.text(cls.REFERENCES / "plan-review.md")
        return next(block for block in text.split("\n\n") if block.startswith(opening))

    @classmethod
    def classification_paragraph(cls):
        return cls.plan_review_paragraph("Classify every plan's claims by what they change:")

    @classmethod
    def security_analysis_paragraph(cls):
        return cls.plan_review_paragraph("In auto, a plan with a Security-critical claim gets a security analysis")

    @classmethod
    def readme_bullets(cls, name):
        text = cls.text(config.ROOT / name)
        start, end = {"README.md": ("## Roles and routing", "### Automatic review switch"),
                      "README.zh-TW.md": ("## 分派與預設模型", "### 自動審查開關")}[name]
        return dict(feather_support.readme_rule_bullets(text, start, end))

    @classmethod
    def readme_security_section(cls, name):
        heading = {"README.md": "### Security-critical work", "README.zh-TW.md": "### 安全關鍵工作"}[name]
        return cls.text(config.ROOT / name).split(heading, 1)[1].split("\n### ", 1)[0]

    # Acceptance item 5: the drafting rule, stated in plan review.
    DRAFTING = "When main drafts a spec for the user, it lists no claims and cuts none unless the user asks."

    # Acceptance item 5 and S7: marking when written covers only a plan main proposes itself, whatever its form.
    NARROWED = (
        "Main marks each Security-critical claim in a plan it proposes itself, such as one for Unplanned work, when it "
        "writes that plan; a plan main writes because Unplanned work needs one is a plan main proposes itself, whatever "
        "its form."
    )

    # Acceptance item 5: a spec main drafts is classified before the Plan's first plan review.
    DRAFTED_SPEC = (
        "A spec main drafts is not a plan main proposes itself: its claims are classified before the plan's first plan "
        "review, as for any plan the user wrote."
    )

    # Kept: the timing for every other plan.
    OTHER_PLANS = (
        "For any other plan, such as a spec or ticket the user wrote, one written before cc-feather 0.18.0 or a "
        "conversation plan, main classifies its claims before the first plan review of that plan in the session or, for "
        "implemented work, before its code review."
    )

    # S8: classification reads the whole spec, unlike a claim's reviews.
    WHOLE_SPEC = (
        "Classifying a ticket's claim reads the ticket and, when it belongs to a spec, its whole spec, as plan review's "
        "checklist does, not only the claim's reading set."
    )

    # S7: off mode classifies before dispatch (kept), and an executor's reported Security-critical change is routed.
    OFF_MODE = "In off mode, main classifies before dispatching the implementation, so that Security-critical work is " \
               "routed to security-executor."
    EXECUTOR_REPORT = "In either mode, a Security-critical change an executor reports goes to security-executor."

    SKILL_OFF_MODE = (
        "A Security-critical claim is a claim whose outcome includes a Security-critical change; classify claims as "
        "[plan review](references/plan-review.md) describes, in off mode too, before dispatching their implementation."
    )
    SKILL_EXECUTOR_REPORT = "In off mode too, a Security-critical change an executor reports goes to security-executor."

    # Replaced 0.22.0 wording: marking in any plan main writes.
    REPLACED = "Main marks each Security-critical claim in a plan it writes."

    def test_plan_review_states_the_drafting_rule_and_the_narrowed_marking_rule(self):
        paragraph = self.classification_paragraph()
        for sentence in (self.DRAFTING, self.NARROWED, self.DRAFTED_SPEC, self.OTHER_PLANS, self.WHOLE_SPEC,
                         self.OFF_MODE, self.EXECUTOR_REPORT):
            with self.subTest(sentence=sentence[:60]):
                self.assertIn(sentence, paragraph)
        self.assertNotIn(self.REPLACED, self.text(self.REFERENCES / "plan-review.md"))
        # The drafted spec is classified as the other plans are, so its rule precedes theirs.
        self.assertLess(paragraph.index(self.NARROWED), paragraph.index(self.DRAFTING))
        self.assertLess(paragraph.index(self.DRAFTED_SPEC), paragraph.index(self.OTHER_PLANS))

    def test_the_delegation_skill_keeps_off_mode_classification_and_routes_reported_changes(self):
        skill = self.text(config.ROOT / "skills" / "delegation" / "SKILL.md")
        paragraph = next(block for block in skill.split("\n\n")
                         if block.startswith("For requested security analysis or a Security-critical change,"))
        self.assertIn(self.SKILL_OFF_MODE, skill)
        self.assertIn(self.SKILL_EXECUTOR_REPORT, paragraph)

    # S4, writing side: accepted controls and test targets go where the claim's reading set reaches.
    WRITTEN_INTO_THE_CLAIM = (
        "Main writes each such security invariant into the claim's own acceptance or a part of a spec the claim cites, "
        "and each test target into the claim's own text or a part it cites, not into another part of the named spec, so "
        "that both are in the claim's reading set, as [review state](review-state.md)'s Reading set describes."
    )

    # Acceptance item 6 and Implementation Decisions "Unchanged": timing, invariants and the approval step are kept.
    SECURITY_ANALYSIS_KEPT = (
        "In auto, a plan with a Security-critical claim gets a security analysis before its plan review.",
        "Main dispositions every finding into the plan, turning each accepted control into a security invariant in the "
        "acceptance of each Security-critical claim it applies to,",
        "Plan review then receives the revised plan; security analysis and plan review stay separate assignments, and "
        "neither runs inside the other.",
        "The user's approval then follows step 5: a disposition that adds a security invariant or otherwise materially "
        "changes the plan's outcome, scope or acceptance needs the user's approval of the revised plan, while a plan the "
        "analysis leaves unchanged keeps the user's earlier agreement.",
        "Security analysis reopens only for a new trust boundary, a changed attacker capability or a materially revised "
        "control, and then covers only what changed, before plan review runs again.",
    )

    def test_security_analysis_writes_its_controls_where_the_claim_reads_them(self):
        paragraph = self.security_analysis_paragraph()
        for sentence in (self.WRITTEN_INTO_THE_CLAIM,) + self.SECURITY_ANALYSIS_KEPT:
            with self.subTest(sentence=sentence[:60]):
                self.assertIn(sentence, paragraph)
        # Written while dispositioning, before plan review receives the revised plan and before the approval.
        self.assertLess(paragraph.index(self.SECURITY_ANALYSIS_KEPT[1]), paragraph.index(self.WRITTEN_INTO_THE_CLAIM))
        self.assertLess(paragraph.index(self.WRITTEN_INTO_THE_CLAIM), paragraph.index(self.SECURITY_ANALYSIS_KEPT[2]))
        # Where Acceptance item 6's looser place differs, S4 governs: the procedure never names the looser place.
        self.assertNotIn("written into the named ticket or spec", paragraph)

    # Acceptance item 10, the Claims-table part.
    TRACKER = "A spec lists claims in a Claims table only when the user asks; its tickets then mirror that table."
    TRACKER_REPLACED = "A spec may also list its claims in a Claims table; its tickets then mirror that table."

    def test_the_tracker_note_lists_a_claims_table_only_when_the_user_asks(self):
        text = self.text(config.ROOT / "docs" / "agents" / "issue-tracker.md")
        line = next(line for line in text.splitlines() if line.startswith("- Each ticket starts with"))
        self.assertIn(self.TRACKER, line)
        self.assertNotIn(self.TRACKER_REPLACED, text)

    # Acceptance items 11 and 12 for these rules, S7, S8 and S12: both READMEs, paired.
    README_DRAFTING = (
        ("when main drafts a spec for you, it lists no claims and cuts none unless you ask: its claims are decided when "
         "you name the spec or its tickets for implementation.",
         "主 Agent 替你草擬 spec 時，除非你要求，不會在裡面列出 claim，也不會切分 claim：它的 claim 在你指名要實作這份 spec 或它的 "
         "ticket 時才決定。"),
        ("A spec main drafts is not a plan main proposes itself, so its claims are classified like those of a spec you "
         "wrote, before its first plan review; see [Security-critical work](#security-critical-work).",
         "主 Agent 草擬的 spec 不算它自己提出的計畫，所以它的 claim 和你寫的 spec 一樣，在第一次計畫審查前分類；見"
         "[安全關鍵工作](#安全關鍵工作)。"),
    )

    README_SECURITY = (
        ("Main marks each Security-critical claim when it writes a plan it proposes itself, such as the plan that "
         "unplanned work needs, whatever its form; it classifies the claims of any other plan, such as a spec you wrote "
         "or one main drafted for you, before its first plan review in the session or, for implemented work, before its "
         "code review, and in `off` before dispatching their implementation.",
         "主 Agent 寫自己提出的計畫時（例如沒有計畫的工作所需要的計畫，不論形式），會在其中標出每個安全關鍵 claim；其他計畫（例如你寫的 "
         "spec，或主 Agent 替你草擬的 spec）會在這個 session 第一次計畫審查前分類，已實作的工作則在程式碼審查前分類，`off` 下則在派出"
         "實作前分類。"),
        ("Classifying a ticket's claim reads the ticket and its whole spec, not only the parts it cites.",
         "分類 ticket 的 claim 時，會讀該 ticket 與它的整份 spec，不只它引用的部分。"),
        ("A Security-critical change an executor reports also goes to security-executor.",
         "executor 回報的安全關鍵變更也交給 security-executor。"),
        # S4, writing side.
        ("Main writes those invariants and test targets into the claim's own text or a spec part it cites, so that its "
         "implementer and reviewers read them.",
         "主 Agent 把這些不變條件與測試目標寫進該 claim 自己的文字或它引用的 spec 部分，讓實作者與審查者都讀得到。"),
    )

    # Replaced README wording: marking in any plan main writes.
    README_REPLACED = (
        ("README.md", "Main marks each Security-critical claim in a plan it writes"),
        ("README.zh-TW.md", "主 Agent 會在自己寫的計畫中標出每個安全關鍵 claim"),
    )

    def test_readmes_state_the_drafting_rule_and_when_claims_are_classified_in_both_languages(self):
        english, chinese = self.readme_bullets("README.md"), self.readme_bullets("README.zh-TW.md")
        for en, zh in self.README_DRAFTING:
            with self.subTest(sentence=en[:50]):
                self.assertIn(en, english["Drafting a spec"])
                self.assertIn(zh, chinese["草擬 spec"])
        sections = {name: self.readme_security_section(name) for name in ("README.md", "README.zh-TW.md")}
        for en, zh in self.README_SECURITY:
            with self.subTest(sentence=en[:50]):
                self.assertIn(en, sections["README.md"])
                self.assertIn(zh, sections["README.zh-TW.md"])
        for name, sentence in self.README_REPLACED:
            with self.subTest(readme=name, removed=sentence[:40]):
                self.assertNotIn(sentence, self.text(config.ROOT / name))

    # S12: the drafting bullet sits under the section intro that states these rules are instructions to main.
    def test_the_drafting_bullet_sits_under_the_stated_limits(self):
        for name, intro, bullet in (
                ("README.md", "These rules are instructions to main, not enforced by any tool;", "- **Drafting a spec:**"),
                ("README.zh-TW.md", "這些規則是給主 Agent 的指示，沒有任何工具強制執行；", "- **草擬 spec：**")):
            section = ClaimsAtImplementationTests.readme_section(name)
            with self.subTest(readme=name):
                self.assertIn(intro, section)
                self.assertIn(bullet, section)

    # Re-checked against the procedures after this ticket: a plan main proposes itself, and off-mode timing.
    GLOSSARY = {
        "Security-critical claim": (
            "It is identified when main writes a Plan it proposes itself, such as one for Unplanned work, or, otherwise, "
            "before the Plan's first review and before its implementation is dispatched.",
            "A spec main drafts at the user's request is not a Plan main proposes itself.",
        ),
        "Claim": ("A spec lists Claims only when the user asked for them.",),
    }

    def test_glossary_entries_match_the_procedures_after_this_ticket(self):
        entries = feather_support.glossary_entries(self.text(config.ROOT / "CONTEXT.md"))
        for term, sentences in self.GLOSSARY.items():
            for sentence in sentences:
                with self.subTest(term=term, sentence=sentence[:60]):
                    self.assertIn(sentence, entries[term])


if __name__ == "__main__":
    unittest.main()
