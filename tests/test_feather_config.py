from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "feather_config.py"
spec = importlib.util.spec_from_file_location("feather_config", SCRIPT)
assert spec and spec.loader
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)


class FeatherConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
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
        self.assertIn("Automatic plan review mode: off", guidance.read_text(encoding="utf-8"))
        explore = self.project / ".claude" / "agents" / "Explore.md"
        self.assertIn("name: Explore", explore.read_text(encoding="utf-8"))
        self.assertIn("model: haiku", explore.read_text(encoding="utf-8"))
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
        self.assertEqual(show["choices"]["Explore"], {"model": "haiku", "effort": "high"})
        self.assertTrue((self.home / "agents" / "Explore.md").exists())
        self.assertFalse((self.project / ".claude" / "agents").exists())

    def test_stale_plan_and_unowned_explore_conflict(self):
        code, preview = self.call("install")
        self.assertEqual(code, 0)
        (self.project / "CLAUDE.md").write_text("changed", encoding="utf-8")
        code, error = self.call("install", "project", "--apply", "--expected-plan", preview["plan_id"])
        self.assertEqual(code, 2)
        self.assertIn("matching", error["error"])
        explore = self.project / ".claude" / "agents" / "Explore.md"
        explore.parent.mkdir(parents=True)
        explore.write_text("owned by user", encoding="utf-8")
        code, error = self.call("install")
        self.assertEqual(code, 2)
        self.assertIn("unowned role", error["error"])
        self.assertEqual(explore.read_text(encoding="utf-8"), "owned by user")

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

    def legacy_install(self):
        self.apply("install", "project", "--review-mode", "auto")
        self.apply("model", "project", "--set", "analyst.model=sonnet")
        state_path = self.project / ".claude" / "cc-feather" / "state.json"
        state = json.loads(state_path.read_bytes())
        state["version"] = 1
        for role in config.ROLES:
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
        agents = self.project / ".claude" / "agents"
        self.assertEqual({p.stem for p in agents.glob("*.md")}, set(config.ROLES))
        self.assertEqual(set(self.call("session")[1]), set(config.ROLES))
        self.apply("remove")
        self.assertEqual(list(agents.glob("*.md")), [])

    def test_legacy_migration_conflicts_and_drift_leave_files_untouched(self):
        self.legacy_install()
        agents = self.project / ".claude" / "agents"
        for filename in ("analyst.md", "custom.md"):
            with self.subTest(filename=filename):
                conflict = agents / filename
                conflict.write_text("---\nname: analyst\n---\nExisting user role\n", encoding="utf-8")
                before = {p: p.read_bytes() for p in self.project.rglob("*") if p.is_file()}
                code, result = self.call("update")
                self.assertEqual(code, 2, result)
                self.assertEqual(before, {p: p.read_bytes() for p in self.project.rglob("*") if p.is_file()})
                conflict.unlink()
        old = agents / "feather-analyst.md"
        old.write_bytes(old.read_bytes() + b"User customization\n")
        self.assertEqual(self.call("update")[0], 2)
        self.assertFalse((agents / "analyst.md").exists())

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
        self.assertEqual(set(agents), {"scout", "analyst",
                                       "mech-executor", "executor",
                                       "security-executor", "Explore"})
        self.assertEqual(agents["Explore"]["model"], "opus")
        self.assertEqual(agents["Explore"]["effort"], "low")
        self.assertEqual(agents["analyst"]["effort"], "medium")
        self.assertIn("tools", agents["Explore"])
        self.assertIn("disallowedTools", agents["executor"])
        self.assertFalse((self.project / ".claude").exists())
        self.assertFalse((self.project / "CLAUDE.md").exists())

    def test_custom_file_declaring_explore_blocks_install_and_check(self):
        custom = self.project / ".claude" / "agents" / "nested" / "custom.md"
        custom.parent.mkdir(parents=True)
        custom.write_text("---\nname: 'Explore'\n---\nMine", encoding="utf-8")
        code, shown = self.call("check")
        self.assertEqual(code, 2)
        self.assertIn("duplicate native agent name Explore", shown["issues"][0])
        code, error = self.call("install")
        self.assertEqual(code, 2)
        self.assertIn("duplicate native agent name Explore", error["error"])
        self.assertEqual(custom.read_text(encoding="utf-8"), "---\nname: 'Explore'\n---\nMine")
        self.assertFalse((self.project / ".claude" / "cc-feather" / "state.json").exists())

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

    def test_bom_and_comment_declared_explore_collision(self):
        custom = self.project / ".claude" / "agents" / "other.md"
        custom.parent.mkdir(parents=True)
        custom.write_text("\ufeff---\nname: Explore # native name\n---\nMine", encoding="utf-8")
        code, result = self.call("check")
        self.assertEqual(code, 2)
        self.assertIn("duplicate native agent name Explore", result["issues"][0])
        custom.write_text("---\nname: [Explore]\n---\nMine", encoding="utf-8")
        code, error = self.call("install")
        self.assertEqual(code, 2)
        self.assertIn("cannot inspect agent name syntax", error["error"])

    def test_show_uninstalled_reports_conflicts_and_owner_paths(self):
        owned_name = self.project / ".claude" / "agents" / "Explore.md"
        owned_name.parent.mkdir(parents=True)
        owned_name.write_text("mine", encoding="utf-8")
        code, shown = self.call("show")
        self.assertEqual(code, 2)
        self.assertFalse(shown["installed"])
        self.assertTrue(shown["requested_configuration_only"])
        self.assertEqual(shown["paths"]["agents"]["Explore"], str(owned_name))
        self.assertIn("unowned role", shown["issues"][0])

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
        role_template = fixture / "templates" / "agents" / "Explore.md"
        role_template.write_text(role_template.read_text(encoding="utf-8") + "\nUPGRADED TEMPLATE", encoding="utf-8")
        policy_template = fixture / "templates" / "CLAUDE.md"
        policy_template.write_text(policy_template.read_text(encoding="utf-8").replace(config.END, "UPGRADED POLICY\n" + config.END), encoding="utf-8")
        with mock.patch.object(config, "ROOT", fixture):
            self.apply("model", "project", "--set", "Explore.model=sonnet")
            code, session = self.call("session")
            self.assertEqual(code, 0)
            self.assertEqual(session["Explore"]["model"], "sonnet")
            self.assertNotIn("UPGRADED TEMPLATE", session["Explore"]["prompt"])
            self.assertEqual(scout.read_bytes(), original_scout)
            self.assertEqual((self.project / "CLAUDE.md").read_bytes(), guidance)
            self.assertNotIn(b"UPGRADED TEMPLATE", explore.read_bytes())
            self.assertEqual(explore.read_bytes().replace(b"model: sonnet", b"model: haiku"), original_explore)
            self.apply("update")
            self.assertIn(b"UPGRADED TEMPLATE", explore.read_bytes())

    def test_review_mode_toggle_preserves_roles_and_choices(self):
        self.apply("install", "project", "--review-mode", "off")
        self.apply("model", "project", "--set", "scout.model=sonnet")
        scout = self.project / ".claude" / "agents" / "scout.md"
        original = scout.read_bytes()
        self.assertEqual(self.call("show")[1]["review_mode"], "off")
        self.apply("review", "project", "--review-mode", "auto")
        self.assertEqual(scout.read_bytes(), original)
        self.assertIn("Automatic plan review mode: auto", (self.project / "CLAUDE.md").read_text(encoding="utf-8"))
        self.apply("review", "project", "--review-mode", "off")
        self.apply("update")
        shown = self.call("show")[1]
        self.assertEqual(shown["review_mode"], "off")
        self.assertEqual(shown["choices"]["scout"]["model"], "sonnet")
        self.apply("remove")

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
        raw["choices"]["scout"]["effort"] = []
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


if __name__ == "__main__":
    unittest.main()
