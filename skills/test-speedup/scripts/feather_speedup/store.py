"""The store (record.json and the measurement files beside it), its version, and the project files it hashes."""
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets

from feather_handoff.storage import HandoffError, Snapshot, check_path, create_file, read_file, replace_file

from .location import Location, SpeedupError

SCHEMA_VERSION = 1
ABSENT = "absent"
IGNORE = b"*\n"
RECORD = "record.json"
MEASUREMENTS = "measurements"
MEASUREMENT_NAME = re.compile(r"[0-9A-Za-z_-]+\.json")
VERSION = re.compile(r"absent|[0-9a-f]{64}")


class Changed(Exception):
    """The store is no longer the version the caller read; nothing was written."""


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def moment(text: str) -> datetime:
    """A stored or given ISO 8601 date as an aware datetime; one without a time zone is local time."""
    value = datetime.fromisoformat(text)
    return value if value.utcoffset() is not None else value.astimezone()


def canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def relative(value, what: str) -> str:
    """A project path from input, normalised to `/` form relative to the top level."""
    if not isinstance(value, str) or not value.strip():
        raise SpeedupError("input", f"{what} must be a non-empty path")
    text = value.replace("\\", "/")
    path = PurePosixPath(text)
    if path.is_absolute() or re.match(r"^[A-Za-z]:", text) or ".." in path.parts:
        raise SpeedupError("input", f"{what} must be relative to the top level without '..': {value!r}")
    normal = path.as_posix()
    return "." if normal in ("", ".") else normal


def in_scope(path: str, scope: list[str]) -> bool:
    return any(entry == "." or path == entry or path.startswith(entry.rstrip("/") + "/") for entry in scope)


def target(top: Path, path: str) -> Path:
    """The file a relative path names, refused when it leaves the top level, through a link or otherwise."""
    full = top / path
    real = os.path.normcase(os.path.realpath(full))
    base = os.path.normcase(os.path.realpath(top))
    if real != base and not real.startswith(base.rstrip("\\/") + os.sep):
        raise SpeedupError("input", f"{path} leaves the top level {top}")
    return full


def content_hash(top: Path, path: str) -> str | None:
    """The SHA-256 of the file's bytes, or None when it does not exist."""
    full = target(top, path)
    if not os.path.lexists(full):
        return None
    if not full.is_file():
        raise SpeedupError("input", f"{path} is not a regular file")
    return digest(full.read_bytes())


def shared_set(top: Path, paths) -> tuple[str, dict]:
    if not isinstance(paths, list):
        raise SpeedupError("input", "shared must be a list of paths")
    hashes = {}
    for value in paths:
        path = relative(value, "a shared file")
        hashes[path] = content_hash(top, path)
    return digest(canonical(sorted([path, value] for path, value in hashes.items())).encode("utf-8")), hashes


def empty_record() -> dict:
    return {"schema_version": SCHEMA_VERSION, "files": {}, "items": {}, "runs": []}


@dataclass
class State:
    snapshot: Snapshot | None
    record: dict | None
    measurements: list[str]
    version: str


class Store:
    def __init__(self, location: Location):
        self.location = location
        self.directory = location.directory
        self.record_path = self.directory / RECORD
        self.measurement_directory = self.directory / MEASUREMENTS

    def measurement_names(self) -> list[str]:
        try:
            entries = list(os.scandir(self.measurement_directory))
        except FileNotFoundError:
            return []
        return sorted(entry.name for entry in entries
                      if MEASUREMENT_NAME.fullmatch(entry.name) and entry.is_file(follow_symlinks=False))

    def load(self) -> State:
        try:
            snapshot = read_file(self.record_path)
        except FileNotFoundError:
            snapshot = None
        record = None
        if snapshot is not None:
            try:
                record = json.loads(snapshot.text)
            except (ValueError, UnicodeError) as error:
                raise SpeedupError("record", f"{self.record_path} is not valid JSON: {error}") from None
            if (not isinstance(record, dict) or record.get("schema_version") != SCHEMA_VERSION
                    or not isinstance(record.get("files"), dict) or not isinstance(record.get("items"), dict)
                    or not isinstance(record.get("runs"), list)):
                raise SpeedupError("record", f"{self.record_path} is not a Speed-up record of schema version "
                                   f"{SCHEMA_VERSION}")
        names = self.measurement_names()
        if snapshot is None and not names:
            version = ABSENT
        else:
            version = digest(canonical({"record": None if snapshot is None else snapshot.version,
                                        "measurements": names}).encode("utf-8"))
        return State(snapshot, record, names, version)

    def require(self, version: str) -> State:
        state = self.load()
        if state.version != version:
            raise Changed()
        return state

    def ensure_ignore(self) -> None:
        path = self.directory / ".gitignore"
        if not os.path.lexists(path):
            try:
                create_file(path, IGNORE)
            except HandoffError as error:
                if error.code != "exists":
                    raise

    def save(self, state: State, record: dict) -> None:
        self.ensure_ignore()
        data = (json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
        try:
            if state.snapshot is None:
                create_file(self.record_path, data)
            else:
                replace_file(state.snapshot, data)
        except HandoffError as error:
            if error.code in ("exists", "conflict"):
                raise Changed() from None
            raise

    def add_measurement(self, measurement: dict) -> str:
        self.ensure_ignore()
        stamp = moment(measurement["date"]).strftime("%Y%m%dT%H%M%S")
        name = f"{stamp}-{secrets.token_hex(4)}.json"
        data = (json.dumps(measurement, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
        create_file(self.measurement_directory / name, data)
        return name

    def measurement(self, name: str) -> dict:
        try:
            value = json.loads(read_file(self.measurement_directory / name).text)
        except (ValueError, UnicodeError) as error:
            raise SpeedupError("record", f"The measurement {name} is not valid JSON: {error}") from None
        if not isinstance(value, dict) or value.get("schema_version") != SCHEMA_VERSION or "date" not in value:
            raise SpeedupError("record", f"The measurement {name} is not of schema version {SCHEMA_VERSION}")
        return {**value, "measurement": name}

    def measurements(self, state: State) -> list[dict]:
        """Every measurement, oldest first by date, ties by name."""
        loaded = [self.measurement(name) for name in state.measurements]
        return sorted(loaded, key=lambda item: (moment(item["date"]), item["measurement"]))

    def remove_measurement(self, name: str) -> None:
        path = self.measurement_directory / name
        check_path(path)
        path.unlink()
