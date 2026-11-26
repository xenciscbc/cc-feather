"""Test runner and plugin versions read from the files that declare them, without running anything."""
from email.parser import HeaderParser
import json
import os
from pathlib import Path

from .location import SpeedupError

LINES = ("go", "toolchain")


def _metadata(path: Path) -> str | None:
    if path.is_dir():
        path = path / "METADATA"
    return HeaderParser().parsestr(path.read_text(encoding="utf-8", errors="replace")).get("Version")


def _go_mod(path: Path, line: str) -> str | None:
    for text in path.read_text(encoding="utf-8").splitlines():
        words = text.split("//", 1)[0].split()
        if len(words) == 2 and words[0] == line:
            return words[1]
    return None


def _python_version(path: Path) -> str | None:
    for text in path.read_text(encoding="utf-8").splitlines():
        text = text.strip()
        if text and not text.startswith("#"):
            return text
    return None


def _pyvenv(path: Path) -> str | None:
    values = {}
    for text in path.read_text(encoding="utf-8").splitlines():
        key, separator, value = text.partition("=")
        if separator:
            values[key.strip().lower()] = value.strip()
    return values.get("version") or values.get("version_info")


def _package_json(path: Path) -> str | None:
    value = json.loads(path.read_text(encoding="utf-8-sig")).get("version")
    return value if isinstance(value, str) else None


def read_one(top: Path, entry) -> dict:
    if not isinstance(entry, dict) or not isinstance(entry.get("name"), str) or not entry["name"].strip():
        raise SpeedupError("input", "each version source must be an object with a non-empty name")
    source = entry.get("source")
    line = entry.get("line", "go")
    if source is not None and not (isinstance(source, str) and source.strip()):
        raise SpeedupError("input", f"the source of {entry['name']} must be a path or null")
    if line not in LINES:
        raise SpeedupError("input", f"line must be one of {', '.join(LINES)}")
    result = {"name": entry["name"], "source": source, "version": None, "state": "unknown"}
    if source is None:
        return {**result, "reason": "no source was named"}
    path = Path(source) if os.path.isabs(source) else top / source.replace("\\", "/")
    name = path.name
    try:
        if name == "package.json":
            version = _package_json(path)
        elif name in ("METADATA", "PKG-INFO") or name.endswith(".dist-info"):
            version = _metadata(path)
        elif name == "go.mod":
            version = _go_mod(path, line)
        elif name == ".python-version":
            version = _python_version(path)
        elif name == "pyvenv.cfg":
            version = _pyvenv(path)
        else:
            return {**result, "reason": f"{name} is not a source a version is read from"}
    except FileNotFoundError:
        return {**result, "reason": f"{source} does not exist"}
    except (OSError, ValueError, UnicodeError, AttributeError) as error:
        return {**result, "reason": f"{source} could not be read: {type(error).__name__}"}
    if not version:
        return {**result, "reason": f"{source} declares no version"}
    return {**result, "version": version, "state": "read"}


def read_versions(top: Path, entries) -> list[dict]:
    if entries is None:
        return []
    if not isinstance(entries, list):
        raise SpeedupError("input", "versions must be a list of version sources")
    return [read_one(top, entry) for entry in entries]


def compare(now: list[dict], last: list[dict] | None) -> list[dict]:
    if last is None:
        return []
    before = {entry["name"]: entry.get("version") for entry in last}
    after = {entry["name"]: entry.get("version") for entry in now}
    return [{"name": name, "last_run": before.get(name), "now": after.get(name)}
            for name in sorted(before.keys() | after.keys()) if before.get(name) != after.get(name)]
