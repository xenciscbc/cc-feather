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
ROLES = ("scout", "analyst", "mech-executor", "executor", "security-executor", "Explore", "verifier", "reviewer")
# Roles introduced after an installation may have been saved; update installs them.
ADDED_ROLES = ("verifier", "reviewer")
# Prefix for every role except Explore when another agent already uses a role name.
ROLE_PREFIX = "cc-"
# Roles another agent may already provide; cc-feather then installs none of its own.
EXTERNAL_ROLES = ("Explore",)
MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}(?:\[[0-9]+m\])?$")
EFFORTS = {"low", "medium", "high", "xhigh", "max"}
BEGIN = "<!-- cc-feather:begin -->"
END = "<!-- cc-feather:end -->"
HANDOFF_BEGIN = "<!-- cc-feather:handoff:begin -->"
HANDOFF_END = "<!-- cc-feather:handoff:end -->"
VERSION = 4
# Instruction files a project-scope installation may manage, relative to the project.
GUIDANCE_FILES = ("CLAUDE.md", ".claude/CLAUDE.md", "AGENTS.md", ".claude/AGENTS.md")


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


def _exists(path: Path) -> bool:
    try:
        return path.exists()
    except OSError as exc:
        raise ConfigError(f"cannot inspect instruction file: {path}: {exc}") from exc


def _instruction_files(args: argparse.Namespace) -> tuple[list[Path], list[Path]]:
    """Return the CLAUDE files that make Claude skip AGENTS.md, and the AGENTS files it reads.

    Claude Code reads AGENTS.md files from the project and its ancestors only when no
    CLAUDE.md, .claude/CLAUDE.md or CLAUDE.local.md exists there; the user's own
    instruction file does not count.
    """
    project = Path(args.project)
    home_text = args.claude_home or os.environ.get("CLAUDE_CONFIG_DIR")
    claude_home = Path(home_text) if home_text else Path.home() / ".claude"
    user_files = {(Path.home() / ".claude" / "CLAUDE.md").resolve(), (claude_home / "CLAUDE.md").resolve()}
    directories = [project, *project.parents]
    counting = [directory / name for directory in directories
                for name in ("CLAUDE.md", ".claude/CLAUDE.md", "CLAUDE.local.md")
                if _exists(directory / name) and (directory / name).resolve() not in user_files]
    agents = [] if counting else [directory / name for directory in reversed(directories)
                                  for name in ("AGENTS.md", ".claude/AGENTS.md") if _exists(directory / name)]
    return counting, agents


def _import_line(target: Path, project: Path) -> str:
    return "@" + os.path.relpath(target, project).replace(os.sep, "/").replace(" ", "\\ ")


def _resolve_guidance(args: argparse.Namespace, state: dict[str, Any] | None) -> dict[str, Any]:
    """Choose the instruction file this scope manages: CLAUDE.md first, then the AGENTS files in effect."""
    _, user_guidance, _ = _scope(args)
    choice = getattr(args, "guidance", None)
    if args.scope == "user":
        if choice:
            raise ConfigError("--guidance applies only to project scope")
        return {"rel": "CLAUDE.md", "path": user_guidance, "imports": [], "choice_required": False}
    project = Path(args.project)
    recorded = (state["guidance"] if state["version"] == VERSION else "CLAUDE.md") if state is not None else None
    if recorded is not None:
        if choice:
            raise ConfigError(f"--guidance is only for a new installation; this scope manages {recorded}")
        result = {"rel": recorded, "path": project / recorded, "choice_required": False,
                  "imports": state["created_imports"] if state["version"] == VERSION else []}
    else:
        existing = next((rel for rel in GUIDANCE_FILES[:2] if _exists(project / rel)), None)
        agents = [] if existing else _instruction_files(args)[1]
        if not agents:
            if choice:
                raise ConfigError("--guidance applies only when AGENTS.md is the project's instruction file")
            rel = existing or "CLAUDE.md"
            result = {"rel": rel, "path": project / rel, "imports": [], "choice_required": False}
        elif choice == "agents":
            rel = next((rel for rel in GUIDANCE_FILES[2:] if project / rel in agents), None)
            if rel is None:
                raise ConfigError("--guidance agents needs an AGENTS.md in the project itself; only ancestor AGENTS.md files are in effect")
            result = {"rel": rel, "path": project / rel, "imports": [], "choice_required": False}
        else:
            result = {"rel": "CLAUDE.md", "path": project / "CLAUDE.md", "choice_required": choice is None,
                      "imports": [_import_line(path, project) for path in agents]}
    _safe_path(result["path"])
    return result


def _defaults() -> dict[str, dict[str, str]]:
    path = ROOT / "templates" / "roles.json"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ConfigError(f"cannot read defaults: {path}: {exc}") from exc
    if not isinstance(raw, dict) or set(raw) != set(ROLES):
        raise ConfigError("roles.json must contain exactly the required roles: " + ", ".join(ROLES))
    for key, item in raw.items():
        if not isinstance(item, dict) or set(item) != {"name", "model", "effort"} or item["name"] != key:
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
    if not isinstance(value, dict) or value.get("version") not in (1, 2, 3, VERSION) or value.get("scope") != scope:
        raise ConfigError("state schema or scope mismatch")
    if value["version"] >= 3:
        top = {"version", "scope", "components"} | ({"guidance", "created_imports"} if value["version"] == VERSION else set())
        if set(value) != top or not isinstance(value["components"], dict) or not set(value["components"]) <= {"handoff", "delegation"} or not value["components"]:
            raise ConfigError("state component schema mismatch")
        if value["version"] == VERSION:
            allowed = GUIDANCE_FILES if scope == "project" else ("CLAUDE.md",)
            imports = value["created_imports"]
            if value["guidance"] not in allowed or not isinstance(imports, list) or not all(
                    isinstance(line, str) and line.startswith("@") and "\n" not in line for line in imports) or (
                    imports and value["guidance"] != "CLAUDE.md"):
                raise ConfigError("invalid instruction file state")
        records = value["components"]
    else:
        if set(value) != {"version", "scope", "choices", "hashes", "block_hash", "added_before", "added_after", "review_mode"}:
            raise ConfigError("legacy state schema mismatch")
        records = {"delegation": value}
    for name, record in records.items():
        expected = {"block_hash", "added_before", "added_after"}
        if name == "delegation":
            expected |= {"choices", "hashes", "review_mode", "legacy_names"}
            if value["version"] == VERSION:
                expected |= {"role_prefix", "external_roles"}
        if not isinstance(record, dict) or (value["version"] >= 3 and set(record) != expected):
            raise ConfigError(f"invalid {name} state schema")
        if not isinstance(record["added_before"], bool) or not isinstance(record["added_after"], bool):
            raise ConfigError("invalid guidance separator state")
        if not isinstance(record["block_hash"], str) or not re.fullmatch(r"[0-9a-f]{64}", record["block_hash"]):
            raise ConfigError("invalid state hash")
        if name == "delegation":
            if value["version"] >= 3 and not isinstance(record["legacy_names"], bool):
                raise ConfigError("invalid legacy role flag")
            if record.get("role_prefix", "") not in ("", ROLE_PREFIX):
                raise ConfigError("invalid role prefix state")
            if record.get("external_roles", []) not in ([], list(EXTERNAL_ROLES)):
                raise ConfigError("invalid external role state")
            if record["review_mode"] not in ("auto", "off"):
                raise ConfigError("invalid saved review mode")
            if (not isinstance(record["choices"], dict) or not isinstance(record["hashes"], dict)
                    or set(record["hashes"]) != set(record["choices"])
                    or not set(ROLES) - set(ADDED_ROLES) - _external(record) <= set(record["choices"])
                    <= set(ROLES) - _external(record)):
                raise ConfigError("state role schema mismatch")
            for role in _recorded_roles(record):
                choice = record["choices"][role]
                if not isinstance(choice, dict) or set(choice) != {"model", "effort"}:
                    raise ConfigError(f"invalid state choice for {role}")
                _validate_choice(choice["model"], choice["effort"])
                if not isinstance(record["hashes"][role], str) or not re.fullmatch(r"[0-9a-f]{64}", record["hashes"][role]):
                    raise ConfigError("invalid state hash")
    return value


def _recorded_roles(record: dict[str, Any]) -> tuple[str, ...]:
    return tuple(role for role in ROLES if role in record["choices"])


def _external(record: dict[str, Any] | None) -> set[str]:
    return set(record.get("external_roles", [])) if record else set()


def _roles_outdated(record: dict[str, Any] | None) -> bool:
    return record is not None and set(record["choices"]) != set(ROLES) - _external(record)


def _components(state: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if state is None:
        return {}
    return state["components"] if state["version"] >= 3 else {"delegation": {
        key: item for key, item in state.items() if key not in {"version", "scope"}
    }}


def _block_parts(text: str, begin: str = BEGIN, end: str = END) -> tuple[str, str, str] | None:
    if begin not in text and end not in text:
        return None
    if text.count(begin) != 1 or text.count(end) != 1 or text.index(begin) > text.index(end):
        raise ConfigError("CLAUDE.md has malformed or duplicate cc-feather markers")
    start = text.index(begin)
    finish = text.index(end) + len(end)
    return text[:start], text[start:finish], text[finish:]


def _role_name(role: str, prefix: str) -> str:
    """Native agent name of a role; Explore keeps its exact name to override the built-in."""
    return role if role == "Explore" else prefix + role


def _policy(review_mode: str, prefix: str = "") -> str:
    path = ROOT / "templates" / "CLAUDE.md"
    text = _decode(read(path), path)
    parts = _block_parts(text)
    if (parts is None or parts[0].strip() or parts[2].strip() or parts[1].count("{{auto_review}}") != 1
            or parts[1].count("{{role_names}}") != 1):
        raise ConfigError("policy template must contain one marked block with auto review and role names tokens")
    # The automatic review rules exist in the guidance only while the mode is auto, so off loads nothing to ignore.
    auto = _auto_review() + "\n\n" if review_mode == "auto" else ""
    names = ""
    if prefix:
        listed = ", ".join(f"{role} = {_role_name(role, prefix)}" for role in ROLES if role != "Explore")
        names = f"Native role names in this scope: {listed}; Explore is unchanged. Dispatch each role to its listed name.\n\n"
    return parts[1].replace("{{auto_review}}", auto).replace("{{role_names}}", names)


def _auto_review() -> str:
    path = ROOT / "templates" / "review-auto.md"
    text = _decode(read(path), path).replace("\r\n", "\n").strip()
    if not text or "{{" in text or "\n\n" in text or "<!--" in text:
        raise ConfigError("automatic review template must be one paragraph without placeholders or markers")
    return text


def _handoff_policy() -> str:
    path = ROOT / "templates" / "handoff.md"
    text = _decode(read(path), path)
    parts = _block_parts(text, HANDOFF_BEGIN, HANDOFF_END)
    if parts is None or parts[0].strip() or parts[2].strip() or "{{" in parts[1]:
        raise ConfigError("handoff template must contain one marked block without placeholders")
    return parts[1]

def _overrides(items: list[str]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for item in items:
        match = re.fullmatch(rf"({'|'.join(map(re.escape, ROLES))})\.(model|effort)=(.+)", item)
        if not match:
            raise ConfigError(f"invalid --set value: {item!r}")
        role, field, value = match.groups()
        if field in result.get(role, {}):
            raise ConfigError(f"duplicate override: {role}.{field}")
        result.setdefault(role, {})[field] = value
    return result


def _render(role: str, choice: dict[str, str], prefix: str = "") -> bytes:
    path = ROOT / "templates" / "agents" / f"{role}.md"
    template = _decode(read(path), path)
    if template.count("{{model}}") != 1 or template.count("{{effort}}") != 1:
        raise ConfigError(f"template requires one model and effort token: {path}")
    text = template.replace("{{model}}", choice["model"]).replace("{{effort}}", choice["effort"])
    text = re.sub(r"\{\{name:([A-Za-z-]+)\}\}",
                  lambda m: _role_name(m.group(1), prefix) if m.group(1) in ROLES else m.group(0), text)
    if "{{" in text:
        raise ConfigError(f"template has an unknown token: {path}")
    return text.encode("utf-8")


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
    return [f"duplicate native agent name {name}: {path}" for name, path in _collision_entries(base, agents)]


def _collision_entries(base: Path, agents: dict[str, Path]) -> list[tuple[str, Path]]:
    """Other agent files under the scope's agents tree that declare one of these native names."""
    directory = base / "agents"
    _safe_path(directory / ".cc-feather-path-check")
    if not directory.exists():
        return []
    owned_paths = {path for path in agents.values()}
    native_names = {path.stem for path in agents.values()}
    issues: list[tuple[str, Path]] = []
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
                            issues.append((name, path))
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


def _edit_review_block(block: str, old: str, new: str, prefix: str) -> str:
    if block == _policy(old, prefix):
        return _policy(new, prefix)
    # Guidance from earlier templates keeps its rules and switches them with a mode line.
    line = f"Automatic plan review mode: {old}"
    if block.count(line) == 1:
        return block.replace(line, f"Automatic plan review mode: {new}", 1)
    raise ConfigError("installed guidance is from an older template; run setup update first")


def _snapshot(paths: list[Path]) -> dict[str, bytes | None]:
    result = {}
    for path in paths:
        _safe_path(path)
        result[str(path)] = read(path)
    return result


def _agent_paths(base: Path, state: dict[str, Any] | None = None, prefix: str = "",
                 exclude: tuple[str, ...] | list[str] = ()) -> dict[str, Path]:
    """Target paths for the roles under a prefix, or the owned paths of the roles a state records."""
    roles = tuple(role for role in ROLES if role not in exclude)
    if state is not None:
        delegation = _components(state).get("delegation")
        if delegation is not None:
            roles = _recorded_roles(delegation)
            prefix = delegation.get("role_prefix", "")
        if state["version"] == 1 or (state["version"] >= 3 and delegation is not None and delegation["legacy_names"]):
            prefix = "feather-"
    return {role: base / "agents" / f"{_role_name(role, prefix)}.md" for role in roles}


def _explore_providers(base: Path, owned: dict[str, Path]) -> list[Path]:
    """Files of other agents named Explore; any of them already overrides the built-in Explore."""
    target = base / "agents" / "Explore.md"
    _safe_path(target)
    found = [path for _, path in _collision_entries(base, {"Explore": target})]
    # A file at the Explore path only provides Explore when it declares that name; any other
    # file there leaves the built-in Explore active and stays an unowned file for the user.
    if owned.get("Explore") != target and read(target) is not None and _agent_name(target) == "Explore":
        found.insert(0, target)
    return found


def _release_user_explore(owned: dict[str, Path], record: dict[str, Any] | None) -> dict[str, Path]:
    """Stop owning an Explore.md the user has rewritten as their own Explore; it is never deleted."""
    path = owned.get("Explore")
    if path is None or record is None:
        return owned
    _safe_path(path)
    data = read(path)
    if data is None or digest(data) == record["hashes"]["Explore"] or _agent_name(path) != "Explore":
        return owned
    return {role: owned_path for role, owned_path in owned.items() if role != "Explore"}


def _layout(base: Path, owned: dict[str, Path], current: str) -> tuple[str, list[str]]:
    """Return the role prefix and the external roles for an install or update.

    Explore is external whenever another agent uses its name, whatever the saved prefix. The
    other roles keep a saved prefix, or take it when another agent already uses one of their names.
    """
    external = list(EXTERNAL_ROLES) if _explore_providers(base, owned) else []
    if current:
        return current, external
    conflicts = _conflicting_roles(base, _agent_paths(base, exclude=external), owned)
    return (ROLE_PREFIX if conflicts else ""), external


def _conflicting_roles(base: Path, targets: dict[str, Path], owned: dict[str, Path]) -> set[str]:
    """Roles whose target name is already used by an agent this installation does not own."""
    roles = set()
    for role, path in targets.items():
        _safe_path(path)
        if owned.get(role) != path and read(path) is not None:
            roles.add(role)
    by_name = {path.stem: role for role, path in targets.items()}
    roles.update(by_name[name] for name, _ in _collision_entries(base, targets))
    return roles


def _selected(args: argparse.Namespace) -> tuple[str, ...]:
    return ("handoff", "delegation") if args.component == "both" else (args.component,)


def _guidance_parts(text: str, name: str) -> tuple[str, str, str] | None:
    return _block_parts(text, HANDOFF_BEGIN, HANDOFF_END) if name == "handoff" else _block_parts(text)


def _put_block(text: str, name: str, block: str, record: dict[str, Any] | None) -> tuple[str, bool, bool]:
    parts = _guidance_parts(text, name)
    if parts:
        return parts[0] + block + parts[2], record["added_before"], record["added_after"]
    before = bool(text and not text.endswith("\n"))
    return text + ("\n" if before else "") + block + "\n", before, True


def _drop_block(text: str, name: str, record: dict[str, Any]) -> str:
    parts = _guidance_parts(text, name)
    assert parts is not None
    prefix, _, suffix = parts
    if record["added_before"]:
        if not prefix.endswith("\n"):
            raise ConfigError("managed guidance separator changed")
        prefix = prefix[:-2] if prefix.endswith("\r\n") else prefix[:-1]
    if record["added_after"]:
        if not suffix.startswith(("\n", "\r\n")):
            raise ConfigError("managed guidance separator changed")
        suffix = suffix[2:] if suffix.startswith("\r\n") else suffix[1:]
    return prefix + suffix


def _legacy_handoff(block: str) -> tuple[str, str] | None:
    marker = "## Handoff and setup lifecycle"
    if marker not in block:
        return None
    if block.count(marker) != 1:
        raise ConfigError("legacy handoff reminder cannot be split confidently")
    prefix, section = block.removesuffix(END).split(marker, 1)
    normalized = section.replace("\r\n", "\n")
    if not normalized.startswith("\n\n"):
        raise ConfigError("legacy handoff reminder cannot be split confidently")
    body = normalized[2:].rstrip("\n")
    paragraphs = body.split("\n\n", 1)
    reminder = paragraphs[0].strip()
    if "handoff" not in reminder.lower() or "skill" not in reminder.lower():
        raise ConfigError("legacy handoff reminder cannot be split confidently")
    newline = "\r\n" if "\r\n" in block else "\n"
    handoff = HANDOFF_BEGIN + newline + marker + newline * 2 + reminder.replace("\n", newline) + newline + HANDOFF_END
    setup = paragraphs[1].strip() if len(paragraphs) > 1 else ""
    if setup:
        remaining = prefix + "## Setup lifecycle" + newline * 2 + setup.replace("\n", newline) + newline + END
    else:
        remaining = prefix.rstrip("\r\n") + newline + END
    return handoff, remaining


def _plan(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, bytes | None], dict[str, bytes | None]]:
    selected = _selected(args)
    if args.command in {"model", "review"} and selected != ("delegation",):
        raise ConfigError("model and review belong to the delegation component")
    if args.command != "model" and args.set:
        raise ConfigError("--set is supported only by model")
    if args.command == "review" and args.review_mode is None:
        raise ConfigError("review requires --review-mode auto|off")
    if args.command not in {"install", "review"} and args.review_mode is not None:
        raise ConfigError("--review-mode is supported only by install or review")
    if args.review_mode is not None and "delegation" not in selected:
        raise ConfigError("--review-mode belongs to the delegation component")
    defaults = _defaults() if "delegation" in selected else {}
    base, _, state_path = _scope(args)
    state = _load_state(state_path, args.scope, defaults)
    target = _resolve_guidance(args, state)
    if target["choice_required"] and args.command == "install":
        raise ConfigError("guidance target choice required: AGENTS.md is the project's instruction file; "
                          "rerun with --guidance claude to create CLAUDE.md importing it, or --guidance agents to write into it")
    guidance = target["path"]
    records = {k: dict(v) for k, v in _components(state).items()}
    legacy_schema = state is not None and state["version"] in (1, 2)
    delegation = records.get("delegation")
    legacy_names = delegation is not None and (state["version"] == 1 if legacy_schema else delegation["legacy_names"])
    if legacy_schema and delegation is not None:
        delegation["legacy_names"] = legacy_names
    if delegation is not None:
        # Records saved before v4 have no prefix or external roles; the v4 state written below carries both.
        delegation.setdefault("role_prefix", "")
        delegation.setdefault("external_roles", [])
    if legacy_names and args.command in {"model", "review"}:
        raise ConfigError("legacy role names are out of date; run setup update first")
    if args.command in {"model", "review"} and delegation is None:
        raise ConfigError(f"{args.scope} delegation component is not installed")
    if args.command in {"model", "review"} and _roles_outdated(delegation):
        raise ConfigError("delegation roles are out of date; run setup update first")
    if (args.command == "install" and args.component == "both" and delegation is not None
            and args.review_mode is not None and args.review_mode != delegation["review_mode"]):
        raise ConfigError("delegation is already installed; use review to change its saved review mode")
    if args.component == "both" and args.command in {"update", "remove"} and not records:
        raise ConfigError(f"{args.scope} scope is not installed")
    def operates(name: str) -> bool:
        if name not in selected:
            return False
        if args.component != "both":
            return True
        return (name not in records) if args.command == "install" else (name in records)

    owned = _agent_paths(base, state) if delegation is not None else {}
    active_delegation = operates("delegation") and (delegation is not None or args.command == "install")
    prefix = delegation["role_prefix"] if delegation is not None else ""
    external = list(delegation["external_roles"]) if delegation is not None else []
    if active_delegation and args.command in {"install", "update"}:
        # Another agent's Explore stays in place of ours; a taken role name moves the others to the prefix.
        owned = _release_user_explore(owned, delegation)
        prefix, external = _layout(base, owned, prefix)
    elif active_delegation and args.command == "remove":
        # The user's rewritten Explore.md is theirs now; remove leaves it in place.
        owned = _release_user_explore(owned, delegation)
    elif active_delegation and args.command in {"model", "review"}:
        provided = bool(_explore_providers(base, _release_user_explore(owned, delegation)))
        if provided != bool(external):
            explore = base / "agents" / "Explore.md"
            if not provided and read(explore) is not None:
                # The file is no longer an agent named Explore, but update cannot replace it either.
                raise ConfigError(f"unowned role file already exists: {explore}; user decision required")
            change = "now provided by another agent" if provided else "no longer provided by another agent"
            raise ConfigError(f"Explore is {change}; run setup update first")
    for role in _overrides(args.set):
        if role in external:
            raise ConfigError(f"{role} is provided by another agent and is not managed by cc-feather")
    agents = owned if args.command == "remove" else _agent_paths(base, prefix=prefix, exclude=external)
    agent_paths = [*agents.values(), *owned.values()] if active_delegation else []
    paths = list(dict.fromkeys([*agent_paths, guidance, state_path]))
    before = _snapshot(paths)
    text = _decode(before[str(guidance)], guidance)
    if before[str(guidance)] is None and state is None and target["imports"]:
        # Keep the AGENTS files Claude reads today loaded once CLAUDE.md exists.
        text = "\n".join(target["imports"]) + "\n\n"
    if legacy_schema and delegation is not None:
        old = _guidance_parts(text, "delegation")
        if old is None or digest(old[1].encode("utf-8")) != delegation["block_hash"]:
            raise ConfigError(f"managed delegation guidance block changed or missing: {guidance}")
        split = _legacy_handoff(old[1])
        if split is not None:
            if _guidance_parts(text, "handoff") is not None:
                raise ConfigError(f"unowned handoff guidance block already exists: {guidance}")
            reminder, remaining = split
            text = old[0] + remaining + old[2]
            text, added_before, added_after = _put_block(text, "handoff", reminder, None)
            records["handoff"] = {"block_hash": digest(reminder.encode("utf-8")),
                                  "added_before": added_before, "added_after": added_after}
            delegation["block_hash"] = digest(remaining.encode("utf-8"))
    for name in selected:
        installed = name in records
        if args.command == "install" and installed and args.component != "both":
            raise ConfigError(f"{args.scope} {name} component is already installed; use update")
        if args.command in {"update", "remove"} and not installed and args.component != "both":
            raise ConfigError(f"{args.scope} {name} component is not installed")
    # Validate only components this operation changes; skipped components may
    # have drift or unowned markers that must remain untouched.
    active_components = tuple(name for name in selected if operates(name))
    for name in active_components:
        record = records.get(name)
        parts = _guidance_parts(text, name)
        if record:
            if parts is None or digest(parts[1].encode("utf-8")) != record["block_hash"]:
                raise ConfigError(f"managed {name} guidance block changed or missing: {guidance}")
        elif parts is not None:
            raise ConfigError(f"unowned {name} guidance block already exists: {guidance}")
    if active_delegation:
        collisions = _collisions(base, agents)
        if collisions:
            raise ConfigError("; ".join(collisions))
        if delegation:
            for role, path in owned.items():
                data = before[str(path)]
                if data is None or digest(data) != delegation["hashes"][role]:
                    raise ConfigError(f"managed role changed or missing: {path}")
            if args.command != "remove":
                # Renamed legacy roles and newly added roles must not take over existing files.
                for role, path in agents.items():
                    if owned.get(role) != path and before[str(path)] is not None:
                        raise ConfigError(f"unowned role file already exists: {path}; user decision required")
        else:
            for path in agents.values():
                if before[str(path)] is not None:
                    raise ConfigError(f"unowned role file already exists: {path}")
    after = dict(before)
    choices = {r: dict(delegation["choices"][r]) if delegation and r in delegation["choices"] else
               {"model": defaults[r]["model"], "effort": defaults[r]["effort"]}
               for r in ROLES if r not in external} if "delegation" in selected else {}
    for role, fields in _overrides(args.set).items():
        choices[role].update(fields)
    for choice in choices.values():
        _validate_choice(choice["model"], choice["effort"])
    review_mode = args.review_mode or (delegation["review_mode"] if delegation else "off")
    for name in active_components:
        record = records.get(name)
        if args.command == "remove" and record is None:
            continue
        if name == "handoff":
            if args.command == "remove":
                text = _drop_block(text, name, record)
                del records[name]
            else:
                block = _handoff_policy()
                text, added_before, added_after = _put_block(text, name, block, record)
                records[name] = {"block_hash": digest(block.encode("utf-8")),
                                 "added_before": added_before, "added_after": added_after}
            continue
        if args.command == "remove":
            for path in owned.values():
                after[str(path)] = None
            text = _drop_block(text, name, record)
            del records[name]
            continue
        if args.command == "update":
            # Legacy and unprefixed names move to the current names.
            for role, path in owned.items():
                if path != agents.get(role):
                    after[str(path)] = None
        for role, path in agents.items():
            if args.command == "model":
                after[str(path)] = _edit_role_fields(before[str(path)], record["choices"][role], choices[role], path) if choices[role] != record["choices"][role] else before[str(path)]
            elif args.command == "review":
                after[str(path)] = before[str(path)]
            else:
                after[str(path)] = _render(role, choices[role], prefix)
        parts = _guidance_parts(text, name)
        if args.command == "review":
            block = _edit_review_block(parts[1], record["review_mode"], review_mode, prefix)
        elif args.command == "model":
            block = parts[1]
        else:
            block = _policy(review_mode, prefix)
        text, added_before, added_after = _put_block(text, name, block, record)
        records[name] = {"choices": choices, "hashes": {role: digest(after[str(path)]) for role, path in agents.items()},
                         "block_hash": digest(block.encode("utf-8")), "review_mode": review_mode,
                         "added_before": added_before, "added_after": added_after, "legacy_names": False,
                         "role_prefix": prefix, "external_roles": external}
    created_imports = list(target["imports"])
    if not records and created_imports and (not text.strip() or text.split() == [
            word for line in created_imports for word in line.split()]):
        # Only the imports setup added remain; drop the CLAUDE.md it created.
        after[str(guidance)] = None
    else:
        after[str(guidance)] = text.encode("utf-8")
    after[str(state_path)] = canonical({"version": VERSION, "scope": args.scope, "components": records,
                                        "guidance": target["rel"], "created_imports": created_imports}) + b"\n" if records else None
    changes = []
    for path in paths:
        key = str(path)
        old, new = before[key], after[key]
        if old != new:
            changes.append({"path": key, "before": None if old is None else _decode(old, path),
                            "after": None if new is None else _decode(new, path),
                            "before_sha256": None if old is None else digest(old),
                            "after_sha256": None if new is None else digest(new)})
    identity = {"command": args.command, "component": args.component, "scope": args.scope,
                "project": str(Path(args.project)), "claude_home": str(base), "guidance": target["rel"],
                "snapshot": {key: None if value is None else digest(value) for key, value in before.items()},
                "changes": [{"path": c["path"], "after_sha256": c["after_sha256"]} for c in changes],
                "templates": {role: digest(_render(role, choices[role], prefix)) for role in choices}
                             if "delegation" in active_components and args.command in {"install", "update"} else {},
                "policy": digest(_policy(review_mode, prefix).encode("utf-8")) if "delegation" in active_components and args.command in {"install", "update"} else None,
                "handoff_policy": digest(_handoff_policy().encode("utf-8")) if "handoff" in active_components and args.command in {"install", "update"} else None}
    plan_id = digest(canonical(identity))
    result = {"status": "preview", "command": args.command, "component": args.component, "scope": args.scope,
              "plan_id": plan_id, "components": {name: {"installed": name in records} for name in ("handoff", "delegation")},
              "choices": choices if choices else (delegation["choices"] if delegation else {}),
              "review_mode": review_mode, "guidance": str(guidance), "requested_configuration_only": True,
              "changes": changes, "warnings": _warnings(args) if "delegation" in selected else []}
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
        try:
            _safe_path(path)
            data = read(path)
        except (ConfigError, OSError):
            warnings.append(f"Could not safely inspect settings file: {path}; runtime overrides are unknown.")
            continue
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


def _instruction_setting(args: argparse.Namespace) -> str | None:
    """Read the user's Project instructions choice; only that key is inspected."""
    home_text = args.claude_home or os.environ.get("CLAUDE_CONFIG_DIR")
    path = (Path(home_text) if home_text else Path.home() / ".claude") / "settings.json"
    try:
        _safe_path(path)
        settings = json.loads(read(path) or b"{}")
        value = settings["pluginConfigs"]["agents-md@builtin"]["options"]["instructionFiles"]
    except (ConfigError, OSError, ValueError, UnicodeDecodeError, KeyError, TypeError):
        return None
    return value if isinstance(value, str) else None


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
    base, _, state_path = _scope(args)
    state = _load_state(state_path, args.scope, defaults)
    records = _components(state)
    agents = _agent_paths(base, state)
    target = _resolve_guidance(args, state)
    guidance = target["path"]
    text = _decode(read(guidance), guidance)
    guidance_warnings = []
    if target["rel"] in GUIDANCE_FILES[2:] and state is not None:
        counting = _instruction_files(args)[0]
        if counting:
            guidance_warnings.append(f"{target['rel']} holds the managed guidance, but Claude skips AGENTS.md while "
                                     f"{counting[0]} exists; move the guidance or import AGENTS.md from it.")
        setting = _instruction_setting(args)
        if setting in {"claude-md", "managed-only"}:
            guidance_warnings.append(f"Project instructions is set to {setting}, so Claude does not read {target['rel']}.")
    component_info: dict[str, dict[str, Any]] = {}
    pending_prefix = pending_external = None
    external_warnings: list[str] = []
    for name in ("handoff", "delegation"):
        record = records.get(name)
        issues = []
        try:
            parts = _guidance_parts(text, name)
            if record:
                if parts is None or digest(parts[1].encode("utf-8")) != record["block_hash"]:
                    issues.append(f"managed {name} guidance block changed or missing: {guidance}")
            elif parts is not None:
                issues.append(f"unowned {name} guidance block already exists: {guidance}")
        except ConfigError as exc:
            issues.append(str(exc))
        if name == "delegation":
            try:
                owned = _release_user_explore(agents, record) if record else {}
                current = record.get("role_prefix", "") if record else ""
                prefix, external = _layout(base, owned, current)
                if prefix != current:
                    pending_prefix = prefix
                if external != sorted(_external(record)):
                    pending_external = external
                providers = _explore_providers(base, owned)
                if providers:
                    external_warnings.append(
                        "Explore is provided by another agent (" + ", ".join(map(str, providers)) + "); cc-feather does not "
                        "install or manage it, so its model is whatever that file sets, or the main model if it sets none.")
                targets = _agent_paths(base, prefix=prefix, exclude=external)
                issues.extend(_collisions(base, targets))
                for role, path in targets.items():
                    if owned.get(role) == path:
                        continue
                    _safe_path(path)
                    if read(path) is not None:
                        issues.append(f"unowned role file already exists: {path}")
                for role, path in owned.items():
                    _safe_path(path)
                    data = read(path)
                    if data is None or digest(data) != record["hashes"][role]:
                        issues.append(f"managed role changed or missing: {path}")
            except (ConfigError, OSError) as exc:
                issues.append(str(exc))
            if issues:
                # A planned layout is only reported when install or update could apply it.
                pending_prefix = pending_external = None
        component_info[name] = {"installed": record is not None, "status": "ok" if not issues else "conflict",
                                "issues": issues}
    issues = [issue for entry in component_info.values() for issue in entry["issues"]]
    delegation = records.get("delegation")
    migration_required = state is not None and (state["version"] in (1, 2) or (delegation is not None and delegation.get("legacy_names", False)))
    role_migration_required = state is not None and (state["version"] == 1 or
        (delegation is not None and delegation.get("legacy_names", False)))
    if state is not None and state["version"] in (1, 2):
        try:
            parts = _guidance_parts(text, "delegation")
            if parts and digest(parts[1].encode("utf-8")) == delegation["block_hash"]:
                embedded = _legacy_handoff(parts[1]) is not None
                component_info["handoff"]["migration_required"] = embedded
                if embedded:
                    component_info["handoff"]["installed"] = True
        except ConfigError as exc:
            component_info["handoff"]["issues"].append(str(exc))
            component_info["handoff"]["status"] = "conflict"
            issues.append(str(exc))
    return {"status": "ok" if not issues else "conflict", "scope": args.scope,
            "installed": bool(records), "components": component_info, "migration_required": migration_required,
            "role_migration_required": role_migration_required,
            "role_update_required": _roles_outdated(delegation),
            "role_prefix": delegation.get("role_prefix", "") if delegation else "",
            # Install or update will adopt this prefix because another agent already uses a role name.
            "pending_role_prefix": pending_prefix,
            "external_roles": sorted(_external(delegation)),
            # Install or update will add or drop cc-feather's own Explore to match these external roles.
            "pending_external_roles": pending_external,
            "requested_configuration_only": True,
            "review_mode": delegation["review_mode"] if delegation else "off",
            "paths": {"config_root": str(base / "cc-feather"), "state": str(state_path),
                      "guidance": str(guidance), "agents": {role: str(path) for role, path in agents.items()}},
            "choices": delegation["choices"] if delegation else {r: {"model": defaults[r]["model"], "effort": defaults[r]["effort"]} for r in ROLES},
            "guidance_choice_required": target["choice_required"],
            "issues": issues, "warnings": _warnings(args) + guidance_warnings + external_warnings}



def _session(args: argparse.Namespace) -> dict[str, Any]:
    inspected = _inspect(args)
    if inspected["components"]["delegation"]["status"] != "ok":
        raise ConfigError("delegation configuration has conflicts or drift: " + "; ".join(inspected["components"]["delegation"]["issues"]))
    if inspected["role_migration_required"]:
        raise ConfigError("legacy role names are out of date; run setup update first")
    if inspected["role_update_required"]:
        raise ConfigError("delegation roles are out of date; run setup update first")
    installed = inspected["components"]["delegation"]["installed"]
    external = inspected["external_roles"]
    prefix = inspected["role_prefix"]
    if inspected["pending_external_roles"] is not None:
        if installed:
            raise ConfigError("Explore is now provided by another agent, or no longer is; run setup update first")
        # Without an installation, export what install would set up: no Explore over the user's own.
        external = inspected["pending_external_roles"]
    if inspected["pending_role_prefix"] is not None:
        if installed:
            raise ConfigError("another agent now uses a role name, so the roles move to the "
                              f"{inspected['pending_role_prefix']} prefix; run setup update first")
        # Export the prefixed names install would use, never the names of the user's own agents.
        prefix = inspected["pending_role_prefix"]
    choices = {role: dict(value) for role, value in inspected["choices"].items() if role not in external}
    for role, fields in _overrides(args.set).items():
        if role in external:
            raise ConfigError(f"{role} is provided by another agent and is not managed by cc-feather")
        choices[role].update(fields)
    result: dict[str, Any] = {}
    base, _, _ = _scope(args)
    for role in (role for role in ROLES if role not in external):
        _validate_choice(choices[role]["model"], choices[role]["effort"])
        if installed:
            path = base / "agents" / f"{_role_name(role, prefix)}.md"
            _safe_path(path)
            saved = inspected["choices"][role]
            data = read(path)
            rendered_bytes = _edit_role_fields(data, saved, choices[role], path) if choices[role] != saved else data
        else:
            rendered_bytes = _render(role, choices[role], prefix)
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
        if fields.get("name") != _role_name(role, prefix):
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
    parser.add_argument("--component", choices=("handoff", "delegation", "both"), help="Component for mutations; default delegation")
    parser.add_argument("--guidance", choices=("claude", "agents"),
                        help="Project install where AGENTS.md is in effect: create CLAUDE.md importing it, or write into it")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--expected-plan")
    args = parser.parse_args(argv)
    try:
        if args.scope is None:
            if args.command in {"check", "show", "session"}:
                args.scope = "project"
            else:
                raise ConfigError("--scope project|user is required for mutations")
        if args.component is None:
            args.component = "delegation" if args.command not in {"check", "show"} else "both"
        if args.command == "session":
            if args.apply or args.expected_plan or args.review_mode or args.guidance or args.component != "delegation":
                raise ConfigError("session is read-only and delegation-only")
            result = _session(args)
        elif args.command in {"check", "show"}:
            if args.apply or args.expected_plan or args.set or args.review_mode or args.guidance:
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
