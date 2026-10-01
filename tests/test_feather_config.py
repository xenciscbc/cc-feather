from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import re
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
        changed = guidance.read_bytes().replace(b"Automatic plan review mode: off", b"Automatic plan review mode: auto")
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
        self.assertIn("Automatic plan review mode: off", guidance.read_text(encoding="utf-8"))
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

    def assert_seven_unprefixed_roles(self):
        agents = self.project / ".claude" / "agents"
        self.assertEqual({p.name for p in agents.glob("*.md")}, {f"{role}.md" for role in config.ROLES})

    def test_fresh_install_includes_verifier(self):
        self.apply("install")
        self.assert_seven_unprefixed_roles()
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
        self.assert_seven_unprefixed_roles()
        shown = self.call("show")[1]
        self.assertFalse(shown["role_update_required"])
        self.assertEqual(shown["review_mode"], "auto")
        self.assertEqual(shown["choices"]["analyst"], {"model": "sonnet", "effort": "high"})
        self.assertEqual(shown["choices"]["verifier"], {"model": "opus", "effort": "high"})
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
                (self.project / "CLAUDE.md").unlink()
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
        self.assert_seven_unprefixed_roles()
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
        role_template = fixture / "templates" / "agents" / "Explore.md"
        role_template.write_text(role_template.read_text(encoding="utf-8") + "\nUPGRADED TEMPLATE", encoding="utf-8")
        policy_template = fixture / "templates" / "CLAUDE.md"
        policy_template.write_text(policy_template.read_text(encoding="utf-8").replace(config.END, "UPGRADED POLICY\n" + config.END), encoding="utf-8")
        with mock.patch.object(config, "ROOT", fixture):
            self.apply("model", "project", "--set", "Explore.model=opus")
            code, session = self.call("session")
            self.assertEqual(code, 0)
            self.assertEqual(session["Explore"]["model"], "opus")
            self.assertNotIn("UPGRADED TEMPLATE", session["Explore"]["prompt"])
            self.assertEqual(scout.read_bytes(), original_scout)
            self.assertEqual((self.project / "CLAUDE.md").read_bytes(), guidance)
            self.assertNotIn(b"UPGRADED TEMPLATE", explore.read_bytes())
            self.assertEqual(explore.read_bytes().replace(b"model: opus", b"model: sonnet"), original_explore)
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


if __name__ == "__main__":
    unittest.main()
