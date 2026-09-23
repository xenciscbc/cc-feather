#!/usr/bin/env python3
"""Install and maintain cc-feather's opt-in Claude agent configuration.

Python 3.11 standard library only. Run ``python -B scripts/feather_config.py --help``.
Every write uses a preview plan and requires ``--apply --expected-plan <id>``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ROLES = ("scout", "analyst", "mech-executor", "executor", "security-executor", "Explore")
MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}(?:\[[0-9]+m\])?$")
EFFORTS = {"low", "medium", "high", "xhigh", "max"}
BEGIN = "<!-- cc-feather:begin -->"
END = "<!-- cc-feather:end -->"
VERSION = 2


class ConfigError(Exception):
    pass


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def read(path: Path) -> bytes | None:
    return path.read_bytes() if path.exists() else None


def _safe_path(path: Path) -> None:
    """Reject links at the target and all existing ancestors, including junctions."""
    for member in (path, *path.parents):
        try:
            info = member.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & 0x400):
            raise ConfigError(f"linked path is unsafe: {member}")
        if member == path and info.st_nlink > 1 and stat.S_ISREG(info.st_mode):
            raise ConfigError(f"hard-linked target is unsafe: {member}")
        if member == path and not stat.S_ISREG(info.st_mode):
            raise ConfigError(f"target is not a regular file: {member}")


def _decode(data: bytes | None, path: Path) -> str:
    try:
        return (data or b"").decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ConfigError(f"not UTF-8: {path}") from exc


def _scope(args: argparse.Namespace) -> tuple[Path, Path, Path]:
    project = Path(args.project)
    if not project.is_absolute() or ".." in project.parts:
        raise ConfigError("--project must be absolute without '..'")
    _safe_path(project / ".cc-feather-path-check")
    if not project.is_dir():
        raise ConfigError(f"project directory does not exist: {project}")
    home_text = args.claude_home or os.environ.get("CLAUDE_CONFIG_DIR")
    home = Path(home_text) if home_text else Path.home() / ".claude"
    if not home.is_absolute() or ".." in home.parts:
        raise ConfigError("--claude-home and CLAUDE_CONFIG_DIR must be absolute without '..'")
    base = project / ".claude" if args.scope == "project" else home
    guidance = project / "CLAUDE.md" if args.scope == "project" else home / "CLAUDE.md"
    _safe_path(base / "cc-feather" / "state.json")
    _safe_path(guidance)
    return base, guidance, base / "cc-feather" / "state.json"


def _defaults() -> dict[str, dict[str, str]]:
    path = ROOT / "templates" / "roles.json"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ConfigError(f"cannot read defaults: {path}: {exc}") from exc
    if not isinstance(raw, dict) or set(raw) != set(ROLES):
        raise ConfigError("roles.json must contain exactly the six required roles")
    expected = {"scout": "scout", "analyst": "analyst", "mech-executor": "mech-executor", "executor": "executor", "security-executor": "security-executor", "Explore": "Explore"}
    for key, item in raw.items():
        if not isinstance(item, dict) or set(item) != {"name", "model", "effort"} or item["name"] != expected[key]:
            raise ConfigError(f"invalid defaults for {key}")
        _validate_choice(item["model"], item["effort"])
    return raw


def _validate_choice(model: str, effort: str) -> None:
    if not isinstance(model, str) or not MODEL_RE.fullmatch(model):
        raise ConfigError(f"invalid model identifier: {model!r}")
    if not isinstance(effort, str) or effort not in EFFORTS:
        raise ConfigError(f"invalid effort: {effort!r}; expected low, medium, high, xhigh, or max")


def _load_state(path: Path, scope: str, defaults: dict[str, dict[str, str]]) -> dict[str, Any] | None:
    _safe_path(path)
    data = read(path)
    if data is None:
        return None
    try:
        value = json.loads(data)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ConfigError(f"invalid state file: {path}") from exc
    if not isinstance(value, dict) or set(value) != {"version", "scope", "choices", "hashes", "block_hash", "added_before", "added_after", "review_mode"} or value["version"] not in (1, VERSION) or value["scope"] != scope:
        raise ConfigError("state schema or scope mismatch")
    if not isinstance(value["added_before"], bool) or not isinstance(value["added_after"], bool):
        raise ConfigError("invalid guidance separator state")
    if value["review_mode"] not in ("auto", "off"):
        raise ConfigError("invalid saved review mode")
    if not isinstance(value["choices"], dict) or set(value["choices"]) != set(ROLES) or not isinstance(value["hashes"], dict) or set(value["hashes"]) != set(ROLES):
        raise ConfigError("state role schema mismatch")
    for role in ROLES:
        choice = value["choices"][role]
        if not isinstance(choice, dict) or set(choice) != {"model", "effort"}:
            raise ConfigError(f"invalid state choice for {role}")
        _validate_choice(choice["model"], choice["effort"])
        for h in (value["hashes"][role], value["block_hash"]):
            if not isinstance(h, str) or not re.fullmatch(r"[0-9a-f]{64}", h):
                raise ConfigError("invalid state hash")
    return value


def _block_parts(text: str) -> tuple[str, str, str] | None:
    if BEGIN not in text and END not in text:
        return None
    if text.count(BEGIN) != 1 or text.count(END) != 1 or text.index(BEGIN) > text.index(END):
        raise ConfigError("CLAUDE.md has malformed or duplicate cc-feather markers")
    start = text.index(BEGIN)
    finish = text.index(END) + len(END)
    return text[:start], text[start:finish], text[finish:]


def _policy(review_mode: str) -> str:
    path = ROOT / "templates" / "CLAUDE.md"
    text = _decode(read(path), path)
    parts = _block_parts(text)
    if parts is None or parts[0].strip() or parts[2].strip() or parts[1].count("{{review_mode}}") != 1:
        raise ConfigError("policy template must contain one marked block and review mode token")
    return parts[1].replace("{{review_mode}}", review_mode)


def _overrides(items: list[str]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for item in items:
        match = re.fullmatch(r"(scout|analyst|mech-executor|executor|security-executor|Explore)\.(model|effort)=(.+)", item)
        if not match:
            raise ConfigError(f"invalid --set value: {item!r}")
        role, field, value = match.groups()
        if field in result.get(role, {}):
            raise ConfigError(f"duplicate override: {role}.{field}")
        result.setdefault(role, {})[field] = value
    return result


def _render(role: str, choice: dict[str, str]) -> bytes:
    path = ROOT / "templates" / "agents" / f"{role}.md"
    template = _decode(read(path), path)
    if template.count("{{model}}") != 1 or template.count("{{effort}}") != 1:
        raise ConfigError(f"template requires one model and effort token: {path}")
    return template.replace("{{model}}", choice["model"]).replace("{{effort}}", choice["effort"]).encode("utf-8")


def _agent_name(path: Path) -> str | None:
    text = _decode(read(path), path).removeprefix("\ufeff").replace("\r\n", "\n")
    if not text.startswith("---\n"):
        return None
    if "\n---\n" not in text[4:]:
        raise ConfigError(f"cannot inspect agent frontmatter: {path}")
    header = text[4:].split("\n---\n", 1)[0]
    names = []
    for line in header.splitlines():
        match = re.match(r"^\s*name\s*:\s*(.*?)\s*$", line)
        if not match:
            continue
        scalar = match.group(1).strip()
        if scalar.startswith('"'):
            quoted = re.fullmatch(r'("(?:\\.|[^"\\])*")(?:\s+#.*)?', scalar)
            if quoted is None:
                raise ConfigError(f"cannot inspect agent name syntax: {path}")
            try:
                name = json.loads(quoted.group(1))
            except ValueError as exc:
                raise ConfigError(f"cannot inspect agent name syntax: {path}") from exc
        elif scalar.startswith("'"):
            quoted = re.fullmatch(r"'((?:''|[^'])*)'(?:\s+#.*)?", scalar)
            if quoted is None:
                raise ConfigError(f"cannot inspect agent name syntax: {path}")
            name = quoted.group(1).replace("''", "'")
        else:
            name = re.split(r"\s+#", scalar, maxsplit=1)[0].strip()
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name):
                raise ConfigError(f"cannot inspect agent name syntax: {path}")
        names.append(name)
    if len(names) > 1:
        raise ConfigError(f"duplicate agent name declaration: {path}")
    return names[0] if names else None


def _collisions(base: Path, agents: dict[str, Path]) -> list[str]:
    directory = base / "agents"
    _safe_path(directory / ".cc-feather-path-check")
    if not directory.exists():
        return []
    owned_paths = {path for path in agents.values()}
    native_names = {path.stem for path in agents.values()}
    issues: list[str] = []
    pending = [directory]
    while pending:
        current = pending.pop()
        with os.scandir(current) as entries:
            for item in entries:
                path = Path(item.path)
                info = path.lstat()
                if stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & 0x400):
                    raise ConfigError(f"linked agents tree entry cannot be inspected: {path}")
                if stat.S_ISDIR(info.st_mode):
                    pending.append(path)
                elif stat.S_ISREG(info.st_mode):
                    if path.suffix.lower() == ".md" and path not in owned_paths:
                        name = _agent_name(path)
                        if name in native_names:
                            issues.append(f"duplicate native agent name {name}: {path}")
                else:
                    raise ConfigError(f"agents tree entry cannot be inspected: {path}")
    return issues


def _edit_role_fields(data: bytes, old: dict[str, str], new: dict[str, str], path: Path) -> bytes:
    text = _decode(data, path)
    if not re.match(r"^---\r?\n", text):
        raise ConfigError(f"invalid installed role frontmatter: {path}")
    closing = re.search(r"\r?\n---\r?\n", text[4:])
    if closing is None:
        raise ConfigError(f"invalid installed role frontmatter: {path}")
    split = 4 + closing.start()
    header, tail = text[:split], text[split:]
    for field in ("model", "effort"):
        pattern = re.compile(r"^" + field + r": ([^\r\n]+)(\r?)$", re.MULTILINE)
        matches = list(pattern.finditer(header))
        if len(matches) != 1 or matches[0].group(1) != old[field]:
            raise ConfigError(f"installed role {field} differs from saved choice: {path}")
        if old[field] != new[field]:
            header = pattern.sub(lambda match: field + ": " + new[field] + match.group(2), header, count=1)
    return (header + tail).encode("utf-8")


def _edit_review_block(block: str, old: str, new: str) -> str:
    line = f"Automatic plan review mode: {old}"
    if block.count(line) != 1:
        raise ConfigError("installed guidance review mode line changed")
    return block.replace(line, f"Automatic plan review mode: {new}", 1)


def _snapshot(paths: list[Path]) -> dict[str, bytes | None]:
    result = {}
    for path in paths:
        _safe_path(path)
        result[str(path)] = read(path)
    return result


def _agent_paths(base: Path, state: dict[str, Any] | None = None) -> dict[str, Path]:
    legacy = state is not None and state["version"] == 1
    return {role: base / "agents" / f"{'feather-' if legacy and role != 'Explore' else ''}{role}.md"
            for role in ROLES}


def _plan(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, bytes | None], dict[str, bytes | None]]:
    defaults = _defaults()
    base, guidance, state_path = _scope(args)
    state = _load_state(state_path, args.scope, defaults)
    owned = _agent_paths(base, state)
    legacy = state is not None and state["version"] == 1
    if legacy and args.command in {"model", "review"}:
        raise ConfigError("legacy role names require setup update before changing settings")
    agents = owned if args.command == "remove" else _agent_paths(base)
    paths = list(dict.fromkeys([*agents.values(), *owned.values(), guidance, state_path]))
    before = _snapshot(paths)
    collisions = _collisions(base, agents)
    if collisions:
        raise ConfigError("; ".join(collisions))
    if legacy and args.command == "update":
        for role, path in agents.items():
            if path != owned[role] and before[str(path)] is not None:
                raise ConfigError(f"unowned role file already exists: {path}; user decision required")
    if args.command in {"update", "model", "review", "remove"} and state is None:
        raise ConfigError(f"{args.scope} scope is not installed")
    if args.command == "install" and state is not None:
        raise ConfigError(f"{args.scope} scope is already installed; use update or model")
    if args.command != "model" and args.set:
        raise ConfigError("--set is supported only by model")
    if args.command == "review" and args.review_mode is None:
        raise ConfigError("review requires --review-mode auto|off")
    if args.command not in {"install", "review"} and args.review_mode is not None:
        raise ConfigError("--review-mode is supported only by install or review")
    review_mode = args.review_mode or (state["review_mode"] if state else "off")
    choices = {r: dict(state["choices"][r]) if state else {"model": defaults[r]["model"], "effort": defaults[r]["effort"]} for r in ROLES}
    for role, fields in _overrides(args.set).items():
        choices[role].update(fields)
    for choice in choices.values():
        _validate_choice(choice["model"], choice["effort"])
    text = _decode(before[str(guidance)], guidance)
    parts = _block_parts(text)
    if state:
        for role, path in owned.items():
            data = before[str(path)]
            if data is None or digest(data) != state["hashes"][role]:
                raise ConfigError(f"managed role changed or missing: {path}")
        if parts is None or digest(parts[1].encode("utf-8")) != state["block_hash"]:
            raise ConfigError(f"managed guidance block changed or missing: {guidance}")
    else:
        for path in agents.values():
            if before[str(path)] is not None:
                raise ConfigError(f"unowned role file already exists: {path}")
        if parts is not None:
            raise ConfigError(f"unowned guidance block already exists: {guidance}")
    after = dict(before)
    if legacy and args.command == "update":
        for role, path in owned.items():
            if path != agents[role]:
                after[str(path)] = None
    if args.command == "remove":
        for path in agents.values():
            after[str(path)] = None
        assert parts is not None
        prefix, _, suffix = parts
        if state["added_before"]:
            if not prefix.endswith("\n"):
                raise ConfigError("managed guidance separator changed")
            prefix = prefix[:-1]
        if state["added_after"]:
            if not suffix.startswith("\n"):
                raise ConfigError("managed guidance separator changed")
            suffix = suffix[1:]
        after[str(guidance)] = (prefix + suffix).encode("utf-8")
        after[str(state_path)] = None
    else:
        if args.command in {"model", "review"}:
            assert state is not None and parts is not None
            block = parts[1]
        else:
            block = _policy(review_mode)
        for role, path in agents.items():
            if args.command == "model":
                after[str(path)] = _edit_role_fields(before[str(path)], state["choices"][role], choices[role], path) if choices[role] != state["choices"][role] else before[str(path)]
            elif args.command == "review":
                after[str(path)] = before[str(path)]
            else:
                after[str(path)] = _render(role, choices[role])
        if args.command == "review":
            block = _edit_review_block(block, state["review_mode"], review_mode)
        added_before = state["added_before"] if state else bool(text and not text.endswith("\n"))
        added_after = state["added_after"] if state else True
        if parts:
            new_guidance = parts[0] + block + parts[2]
        else:
            new_guidance = text + ("\n" if added_before else "") + block + "\n"
        after[str(guidance)] = new_guidance.encode("utf-8")
        new_state = {"version": VERSION, "scope": args.scope, "choices": choices,
                     "hashes": {role: digest(after[str(path)]) for role, path in agents.items()},
                     "block_hash": digest(block.encode("utf-8")), "review_mode": review_mode,
                     "added_before": added_before, "added_after": added_after}
        after[str(state_path)] = canonical(new_state) + b"\n"
    changes = []
    for path in paths:
        key = str(path)
        old, new = before[key], after[key]
        if old != new:
            changes.append({"path": key, "before": None if old is None else _decode(old, path),
                            "after": None if new is None else _decode(new, path),
                            "before_sha256": None if old is None else digest(old),
                            "after_sha256": None if new is None else digest(new)})
    identity = {"command": args.command, "scope": args.scope, "project": str(Path(args.project)),
                "claude_home": str(base), "choices": choices, "review_mode": review_mode,
                "snapshot": {key: None if value is None else digest(value) for key, value in before.items()},
                "changes": [{"path": c["path"], "after_sha256": c["after_sha256"]} for c in changes],
                "templates": {role: digest(_render(role, choices[role])) for role in ROLES} if args.command in {"install", "update"} else {},
                "policy": digest(_policy(review_mode).encode("utf-8")) if args.command in {"install", "update"} else None}
    plan_id = digest(canonical(identity))
    result = {"status": "preview", "command": args.command, "scope": args.scope, "plan_id": plan_id,
              "choices": choices, "review_mode": review_mode, "requested_configuration_only": True,
              "changes": changes, "warnings": _warnings(args)}
    return result, before, after


def _warnings(args: argparse.Namespace) -> list[str]:
    # Observations only: Claude may have other configuration layers and runtime overrides.
    warnings = []
    keys = ("CLAUDE_CODE_SUBAGENT_MODEL", "CLAUDE_CODE_SUBAGENT_MODEL_FORCE")
    for key in keys:
        if os.environ.get(key):
            warnings.append(f"Environment {key} is set; requested role models may differ at runtime.")
    if os.environ.get("CLAUDE_CODE_SUBAGENT_MODEL_FORCE"):
        warnings.append("CLAUDE_CODE_SUBAGENT_MODEL_FORCE may force the main model even when CLAUDE_CODE_SUBAGENT_MODEL is unset.")
    project = Path(args.project)
    _, _, _ = _scope(args)
    home_text = args.claude_home or os.environ.get("CLAUDE_CONFIG_DIR")
    home = Path(home_text) if home_text else Path.home() / ".claude"
    for path in (home / "settings.json", home / "settings.local.json",
                 project / ".claude" / "settings.json", project / ".claude" / "settings.local.json"):
        _safe_path(path)
        data = read(path)
        if data is None:
            continue
        try:
            settings = json.loads(data)
        except (ValueError, UnicodeDecodeError):
            warnings.append(f"Could not inspect settings JSON: {path}")
            continue
        if not isinstance(settings, dict):
            warnings.append(f"Could not inspect settings object: {path}")
            continue
        env = settings.get("env")
        if isinstance(env, dict):
            for key in keys:
                if env.get(key):
                    warnings.append(f"Settings {path} define {key}; requested role models may differ at runtime.")
        elif env is not None:
            warnings.append(f"Could not inspect settings env object: {path}")
    return warnings


def _replace(path: Path, data: bytes | None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if data is None:
        path.unlink(missing_ok=True)
        return
    # POSIX replacement uses a new inode; retain the existing permission bits.
    # New files keep mkstemp's private default. Windows ACLs are not POSIX modes.
    mode = None
    if hasattr(os, "fchmod"):
        try:
            mode = stat.S_IMODE(path.stat().st_mode)
        except FileNotFoundError:
            pass
    fd, temporary = tempfile.mkstemp(prefix=".cc-feather-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            if mode is not None:
                os.fchmod(handle.fileno(), mode)
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _apply(args: argparse.Namespace, result: dict[str, Any], before: dict[str, bytes | None], after: dict[str, bytes | None]) -> dict[str, Any]:
    if not args.expected_plan or args.expected_plan != result["plan_id"]:
        raise ConfigError("--apply requires the matching --expected-plan from a fresh preview")
    base, _, _ = _scope(args)
    lock = base / "cc-feather" / ".lock"
    _safe_path(lock)
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise ConfigError(f"scope is locked: {lock}") from exc
    os.close(fd)
    try:
        fresh, old_now, new_now = _plan(args)
        if fresh["plan_id"] != result["plan_id"] or old_now != before or new_now != after:
            raise ConfigError("plan became stale before apply")
        changes = [Path(c["path"]) for c in fresh["changes"]]
        original_modes = {path: stat.S_IMODE(path.stat().st_mode) for path in changes
                          if hasattr(os, "fchmod") and before[str(path)] is not None}
        backup_dir = base / "cc-feather" / "backups" / f"{int(time.time_ns())}-{os.getpid()}"
        _safe_path(backup_dir / "manifest.json")
        backup_dir.mkdir(parents=True, exist_ok=False)
        manifest = []
        for index, path in enumerate(changes):
            original = before[str(path)]
            entry = {"path": str(path), "existed": original is not None,
                     "sha256": None if original is None else digest(original)}
            if original is not None:
                backup = backup_dir / f"{index:02d}.bak"
                _safe_path(backup)
                _replace(backup, original)
                entry["backup"] = backup.name
            manifest.append(entry)
        _replace(backup_dir / "manifest.json", canonical(manifest) + b"\n")
        written: list[Path] = []
        try:
            for path in changes:
                _safe_path(path)
                if read(path) != before[str(path)]:
                    raise ConfigError(f"concurrent edit before write: {path}")
                _replace(path, after[str(path)])
                written.append(path)
        except Exception as exc:
            failures = []
            for path in reversed(written):
                try:
                    _safe_path(path)
                    if read(path) == after[str(path)]:
                        _replace(path, before[str(path)])
                        # A migrated legacy file may have been deleted before rollback.
                        if path in original_modes:
                            os.chmod(path, original_modes[path])
                    else:
                        failures.append(str(path))
                except (OSError, ConfigError):
                    failures.append(str(path))
            if failures:
                raise ConfigError(f"apply failed; rollback incomplete for {failures}; recovery backups: {backup_dir}")
            raise ConfigError(f"apply failed: {exc}; recovery backups: {backup_dir}") from exc
        return {**fresh, "status": "applied", "backup_dir": str(backup_dir)}
    finally:
        lock.unlink(missing_ok=True)


def _inspect(args: argparse.Namespace) -> dict[str, Any]:
    defaults = _defaults()
    base, guidance, state_path = _scope(args)
    state = _load_state(state_path, args.scope, defaults)
    agents = _agent_paths(base, state)
    issues = _collisions(base, agents)
    if state:
        for role in ROLES:
            path = agents[role]
            _safe_path(path)
            data = read(path)
            if data is None or digest(data) != state["hashes"][role]:
                issues.append(f"managed role changed or missing: {path}")
        _safe_path(guidance)
        try:
            parts = _block_parts(_decode(read(guidance), guidance))
            if parts is None or digest(parts[1].encode("utf-8")) != state["block_hash"]:
                issues.append(f"managed guidance block changed or missing: {guidance}")
        except ConfigError as exc:
            issues.append(str(exc))
    else:
        for path in agents.values():
            _safe_path(path)
            if read(path) is not None:
                issues.append(f"unowned role file already exists: {path}")
        _safe_path(guidance)
        try:
            if _block_parts(_decode(read(guidance), guidance)) is not None:
                issues.append(f"unowned guidance block already exists: {guidance}")
        except ConfigError as exc:
            issues.append(str(exc))
    return {"status": "ok" if not issues else "conflict", "scope": args.scope,
            "installed": state is not None, "migration_required": state is not None and state["version"] == 1,
            "requested_configuration_only": True,
            "review_mode": state["review_mode"] if state else "off",
            "paths": {"config_root": str(base / "cc-feather"), "state": str(state_path),
                      "guidance": str(guidance), "agents": {role: str(path) for role, path in agents.items()}},
            "choices": state["choices"] if state else {r: {"model": defaults[r]["model"], "effort": defaults[r]["effort"]} for r in ROLES},
            "issues": issues, "warnings": _warnings(args)}


def _session(args: argparse.Namespace) -> dict[str, Any]:
    inspected = _inspect(args)
    if inspected["status"] != "ok":
        raise ConfigError("installed configuration has drift: " + "; ".join(inspected["issues"]))
    if inspected["migration_required"]:
        raise ConfigError("legacy role names require setup update before session export")
    choices = {role: dict(value) for role, value in inspected["choices"].items()}
    for role, fields in _overrides(args.set).items():
        choices[role].update(fields)
    result: dict[str, Any] = {}
    defaults = _defaults()
    base, _, _ = _scope(args)
    for role in ROLES:
        _validate_choice(choices[role]["model"], choices[role]["effort"])
        if inspected["installed"]:
            path = base / "agents" / f"{defaults[role]['name']}.md"
            _safe_path(path)
            saved = inspected["choices"][role]
            data = read(path)
            rendered_bytes = _edit_role_fields(data, saved, choices[role], path) if choices[role] != saved else data
        else:
            rendered_bytes = _render(role, choices[role])
        rendered = rendered_bytes.decode("utf-8").replace("\r\n", "\n")
        if not rendered.startswith("---\n") or "\n---\n" not in rendered[4:]:
            raise ConfigError(f"invalid agent frontmatter: {role}")
        header, prompt = rendered[4:].split("\n---\n", 1)
        fields: dict[str, str] = {}
        for line in header.splitlines():
            if not line.strip():
                continue
            if ":" not in line:
                raise ConfigError(f"invalid agent frontmatter line: {role}")
            key, value = line.split(":", 1)
            if key in fields:
                raise ConfigError(f"duplicate agent frontmatter field: {role}.{key}")
            fields[key] = value.strip()
        if fields.get("name") != defaults[role]["name"]:
            raise ConfigError(f"agent name mismatch: {role}")
        if fields.get("model") != choices[role]["model"] or fields.get("effort") != choices[role]["effort"]:
            raise ConfigError(f"agent model or effort mismatch: {role}")
        description = fields.get("description", "")
        if description.startswith('"'):
            try:
                description = json.loads(description)
            except ValueError as exc:
                raise ConfigError(f"invalid agent description: {role}") from exc
        if not isinstance(description, str) or not description:
            raise ConfigError(f"missing agent description: {role}")
        agent: dict[str, Any] = {"description": description, "prompt": prompt.lstrip("\n"),
                                 "model": choices[role]["model"], "effort": choices[role]["effort"]}
        for field in ("tools", "disallowedTools"):
            if field in fields:
                agent[field] = [part.strip() for part in fields[field].split(",") if part.strip()]
        result[fields["name"]] = agent
    return result


def main(argv: list[str] | None = None) -> int:
    # JSON must have a stable encoding even on Windows consoles using CP950.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "show", "install", "update", "remove", "model", "review", "session"))
    parser.add_argument("--project", required=True, help="Absolute project directory")
    parser.add_argument("--scope", choices=("project", "user"), help="Required for mutations; read-only commands default to project")
    parser.add_argument("--claude-home", help="Absolute Claude configuration directory (default: CLAUDE_CONFIG_DIR or ~/.claude)")
    parser.add_argument("--set", action="append", default=[], metavar="ROLE.FIELD=VALUE")
    parser.add_argument("--review-mode", choices=("auto", "off"))
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--expected-plan")
    args = parser.parse_args(argv)
    try:
        if args.scope is None:
            if args.command in {"check", "show", "session"}:
                args.scope = "project"
            else:
                raise ConfigError("--scope project|user is required for mutations")
        if args.command == "session":
            if args.apply or args.expected_plan or args.review_mode:
                raise ConfigError("session is read-only")
            result = _session(args)
        elif args.command in {"check", "show"}:
            if args.apply or args.expected_plan or args.set or args.review_mode:
                raise ConfigError("check and show are read-only and accept no mutation options")
            result = _inspect(args)
        else:
            result, before, after = _plan(args)
            if args.apply:
                result = _apply(args, result, before, after)
            elif args.expected_plan:
                raise ConfigError("--expected-plan requires --apply")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2 if result.get("status") == "conflict" else 0
    except (ConfigError, OSError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False), file=sys.stdout)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
