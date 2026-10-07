from __future__ import annotations

import contextlib
import errno
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
import types
import unittest
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "feather_config.py"
spec = importlib.util.spec_from_file_location("feather_config", SCRIPT)
assert spec and spec.loader
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)


def make_directory_link(link: Path, target: Path) -> None:
    """Link a directory with a junction on Windows, else a symlink; skip when neither works."""
    if os.name == "nt":
        try:
            import _winapi
            _winapi.CreateJunction(str(target), str(link))
            return
        except (ImportError, OSError):
            pass
    try:
        os.symlink(target, link, target_is_directory=True)
    except (OSError, NotImplementedError) as exc:
        raise unittest.SkipTest(f"directory link creation unavailable: {exc}")


def remove_directory_link(link: Path) -> None:
    """Remove the link itself, never its target's content."""
    try:
        os.unlink(link)
    except (IsADirectoryError, PermissionError):
        os.rmdir(link)


def remove_link_base(base: Path) -> None:
    # Unlink every directory link first so removing the tree never reaches through one.
    for current, directories, _ in os.walk(base):
        for name in list(directories):
            info = (Path(current) / name).lstat()
            if stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & 0x400):
                remove_directory_link(Path(current) / name)
                directories.remove(name)
    shutil.rmtree(base)


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
        triggers = "Unplanned work that changes a security boundary, migrates data or performs an irreversible operation"
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
            # os.walk skips the dangling link that pathlib's rglob would fail to list.
            found = {}
            for current, directories, files in os.walk(base):
                found.update({Path(current) / name: None for name in directories})
                found.update({Path(current) / name: (Path(current) / name).read_bytes() for name in files})
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
        self.assertIn("resets only on CONFIRMED", verification)

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


if __name__ == "__main__":
    unittest.main()
