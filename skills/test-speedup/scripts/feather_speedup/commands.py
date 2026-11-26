"""The commands of the Speed-up record; the protocol is in the launcher, scripts/speedup.py."""
import copy
from datetime import datetime
import json

from .location import SpeedupError
from .store import (Store, State, canonical, content_hash, empty_record, in_scope, moment, now, relative, shared_set)
from .versions import compare, read_versions

SECTIONS = ("speed-up", "removal", "test-resource-risk", "run-configuration-resource-risk")
STATES = ("undecided", "picked", "declined", "landed", "obsolete")
OPEN = ("undecided", "picked", "declined")
TEXT = ("location", "expected_gain", "correctness", "risk")
KEY_FIELDS = ("command", "selected", "concurrency", "override", "runner", "left_out")
TOP = 10
FORMS = ["show", "show items [undecided|picked|declined|landed|obsolete]", "show runs",
         "prune [--measurements-before DATE] [--keep-measurements N] [--obsolete] [--landed-before DATE] "
         "[--version V]"]


# Input checks ---------------------------------------------------------------------------------------------------

def need(payload: dict, name: str, kind, what: str):
    value = payload.get(name)
    if not isinstance(value, kind) or (kind is not bool and isinstance(value, bool)):
        raise SpeedupError("input", f"{name} must be {what}")
    return value


def scope_of(payload: dict) -> list[str]:
    values = need(payload, "scope", list, "a non-empty list of paths")
    if not values:
        raise SpeedupError("input", "scope must be a non-empty list of paths")
    return [relative(value, "a scope entry") for value in values]


def date_of(payload: dict) -> str:
    value = payload.get("date")
    if value is None:
        return now()
    try:
        if not isinstance(value, str) or "T" not in value or datetime.fromisoformat(value).utcoffset() is None:
            raise ValueError
    except ValueError:
        raise SpeedupError("input", f"date must be an ISO 8601 date and time with a time zone: {value!r}") from None
    return value


def commit_of(payload: dict):
    value = payload.get("commit")
    if value is not None and not (isinstance(value, str) and value.strip()):
        raise SpeedupError("input", "commit must be a commit id or null")
    return value


def analysed_files(payload: dict, name: str = "files") -> list[tuple[str, list]]:
    values = payload.get(name, [])
    if not isinstance(values, list):
        raise SpeedupError("input", f"{name} must be a list of {{path, shared}} objects")
    result, seen = [], set()
    for value in values:
        if not isinstance(value, dict):
            raise SpeedupError("input", f"each entry of {name} must be an object with path and shared")
        path = relative(value.get("path"), "a test file")
        if path in seen:
            raise SpeedupError("input", f"{path} is listed twice")
        seen.add(path)
        shared = value.get("shared", [])
        if not isinstance(shared, list):
            raise SpeedupError("input", f"shared of {path} must be a list of paths")
        result.append((path, shared))
    return result


def item_key(section: str, file: str, tests: list[str] | None, setting: str | None) -> str:
    concern = ["tests", sorted(set(tests))] if tests is not None else ["setting", setting]
    return json.dumps([section, file, *concern], ensure_ascii=False, separators=(",", ":"))


def found_item(value) -> dict:
    if not isinstance(value, dict):
        raise SpeedupError("input", "each item must be an object")
    section = value.get("section")
    if section not in SECTIONS:
        raise SpeedupError("input", f"section must be one of {', '.join(SECTIONS)}")
    file = relative(value.get("file"), "an item's file")
    tests, setting = value.get("tests"), value.get("setting")
    if (tests is None) == (setting is None):
        raise SpeedupError("input", "an item names exactly one of tests or setting")
    if tests is not None and (not isinstance(tests, list) or not tests
                              or not all(isinstance(test, str) and test for test in tests)):
        raise SpeedupError("input", "tests must be a non-empty list of test ids")
    if setting is not None and not (isinstance(setting, str) and setting.strip()):
        raise SpeedupError("input", "setting must be a non-empty string")
    description = value.get("description")
    if not isinstance(description, str) or not description.strip():
        raise SpeedupError("input", "description must be a non-empty string")
    for name in TEXT:
        if value.get(name) is not None and not isinstance(value[name], str):
            raise SpeedupError("input", f"{name} must be a string or null")
    item = {"key": item_key(section, file, tests, setting), "section": section, "file": file,
            "description": description, **{name: value.get(name) for name in TEXT}}
    if tests is not None:
        item["tests"] = sorted(set(tests))
    else:
        item["setting"] = setting
    return item


def entries_of(payload: dict, states: tuple, need_reason: str) -> list[dict]:
    values = payload.get("items")
    if not isinstance(values, list) or not values:
        raise SpeedupError("input", "items must be a non-empty list")
    result, seen = [], set()
    for value in values:
        if not isinstance(value, dict) or not isinstance(value.get("key"), str):
            raise SpeedupError("input", "each entry names an item by its key")
        if value["key"] in seen:
            raise SpeedupError("duplicate-key", f"The item {value['key']} is named twice")
        seen.add(value["key"])
        if value.get("state") not in states:
            raise SpeedupError("input", f"state must be one of {', '.join(states)}")
        reason = value.get(need_reason)
        if value["state"] != "unchanged" and not (isinstance(reason, str) and reason.strip()):
            raise SpeedupError("input", f"{need_reason} must be a non-empty string")
        result.append({**value, "date": date_of(value)})
    return result


def known(record: dict, key: str) -> dict:
    if key not in record["items"]:
        raise SpeedupError("unknown-item", f"No recorded item has the key {key}. Nothing was written.")
    return record["items"][key]


def change_state(item: dict, state: str, date: str, reason: str | None) -> None:
    item["history"].append({"state": item["state"], "date": item["state_date"], "reason": item["state_reason"]})
    item.update(state=state, state_date=date, state_reason=reason)


# Commands -------------------------------------------------------------------------------------------------------

def read(store: Store, state: State, args, payload) -> dict:
    return {"status": "ok", "present": state.record is not None, "record": state.record,
            "measurements": state.measurements, "version": state.version}


def changes(store: Store, state: State, args, payload) -> dict:
    top = store.location.top
    scope = scope_of(payload)
    files = analysed_files(payload)
    record = state.record or empty_record()
    recorded = record["files"]
    listed = {path for path, _ in files}
    report = []
    for path, shared in files:
        current = content_hash(top, path)
        if current is None:
            raise SpeedupError("input", f"The listed test file {path} does not exist")
        set_hash, hashes = shared_set(top, shared)
        entry = recorded.get(path)
        item = {"path": path, "content_hash": current, "shared_set_hash": set_hash,
                "recorded_content_hash": None, "recorded_shared_set_hash": None, "shared_set_changed": None,
                "shared_changes": []}
        if entry is None:
            item["state"] = "new"
        else:
            item.update(state="unchanged" if entry["content_hash"] == current else "changed",
                        recorded_content_hash=entry["content_hash"], recorded_shared_set_hash=entry["shared_set_hash"],
                        shared_set_changed=entry["shared_set_hash"] != set_hash)
            before = entry.get("shared", {})
            for name in sorted(before.keys() | hashes.keys()):
                if name not in hashes:
                    item["shared_changes"].append({"path": name, "change": "removed"})
                elif name not in before:
                    item["shared_changes"].append({"path": name, "change": "added"})
                elif before[name] != hashes[name]:
                    item["shared_changes"].append({"path": name, "change": "changed"})
        report.append(item)
    for path in sorted(recorded):
        if path not in listed and in_scope(path, scope) and content_hash(top, path) is None:
            entry = recorded[path]
            report.append({"path": path, "state": "deleted", "content_hash": None,
                           "recorded_content_hash": entry["content_hash"], "shared_set_hash": None,
                           "recorded_shared_set_hash": entry["shared_set_hash"], "shared_set_changed": None,
                           "shared_changes": []})
    last = record["runs"][-1] if record["runs"] else None
    versions_now = read_versions(top, payload.get("versions"))
    last_versions = None if last is None else last.get("versions", [])
    return {"status": "ok", "version": state.version, "present": state.record is not None,
            "last_run": None if last is None else {"date": last["date"], "commit": last["commit"]},
            "files": report,
            "versions": {"now": versions_now, "last_run": last_versions, "changed": compare(versions_now,
                                                                                           last_versions)}}


def record_run(store: Store, state: State, args, payload) -> dict:
    top = store.location.top
    scope = scope_of(payload)
    commit = commit_of(payload)
    full = need(payload, "full", bool, "true or false")
    date = date_of(payload)
    files = analysed_files(payload)
    deleted_values = payload.get("deleted", [])
    if not isinstance(deleted_values, list):
        raise SpeedupError("input", "deleted must be a list of paths")
    deleted = sorted({relative(value, "a deleted file") for value in deleted_values})
    items_values = payload.get("items", [])
    if not isinstance(items_values, list):
        raise SpeedupError("input", "items must be a list")
    found = [found_item(value) for value in items_values]
    keys = [item["key"] for item in found]
    duplicates = sorted({key for key in keys if keys.count(key) > 1})
    if duplicates:
        raise SpeedupError("duplicate-key", "Two found items share a key; merge them and submit again. Nothing was "
                           "written. Keys: " + "; ".join(duplicates))
    versions = read_versions(top, payload.get("versions"))
    record = copy.deepcopy(state.record) if state.record is not None else empty_record()
    analysed = {path for path, _ in files}
    for path in deleted:
        if path in analysed:
            raise SpeedupError("input", f"{path} is listed both as analysed and as deleted")
        if path not in record["files"] or not in_scope(path, scope) or content_hash(top, path) is not None:
            raise SpeedupError("input", f"{path} is not a recorded file inside the scope that is missing on disk")
    for path, shared in files:
        current = content_hash(top, path)
        if current is None:
            raise SpeedupError("input", f"The analysed test file {path} does not exist")
        set_hash, hashes = shared_set(top, shared)
        record["files"][path] = {"content_hash": current, "shared_set_hash": set_hash, "shared": hashes,
                                 "commit": commit, "analysed": date}
    obsoleted = []
    for path in deleted:
        del record["files"][path]
        for item in record["items"].values():
            if item["file"] == path and item["state"] != "obsolete":
                evidence = f"{path} was deleted"
                change_state(item, "obsolete", date, evidence)
                item["obsolete"] = {"date": date, "evidence": evidence}
                obsoleted.append(item["key"])
    report = []
    for item in found:
        key = item["key"]
        existing = record["items"].get(key)
        if existing is None:
            record["items"][key] = {**item, "state": "undecided", "state_date": date, "state_reason": "found",
                                    "decision": None, "landed": None, "obsolete": None, "first_seen": date,
                                    "last_seen_commit": commit, "history": []}
            outcome = "new"
        else:
            existing.update(item, last_seen_commit=commit)
            if existing["state"] in ("landed", "obsolete"):
                change_state(existing, "undecided", date, "found again")
                existing.update(landed=None, obsolete=None)
                outcome = "reopened"
            else:
                outcome = "matched"
        entry = record["items"][key]
        current = content_hash(top, entry["file"])
        decided = (entry.get("decision") or {}).get("content_hash") if entry["state"] in ("picked", "declined") \
            else None
        report.append({"key": key, "outcome": outcome, "state": entry["state"], "decision_content_hash": decided,
                       "content_hash": current,
                       "decided_file_changed": None if entry["state"] not in ("picked", "declined")
                       else decided != current})
    seen = set(keys)
    missing: dict[str, list] = {}
    for item in record["items"].values():
        if item["key"] in seen or item["state"] not in OPEN:
            continue
        if item["file"] in analysed or (item["section"] == "run-configuration-resource-risk"
                                        and in_scope(item["file"], scope)):
            missing.setdefault(item["file"], []).append(
                {"key": item["key"], "state": item["state"], "section": item["section"],
                 "location": item.get("location"), "description": item["description"]})
    record["runs"].append({"date": date, "scope": scope, "commit": commit, "full": full, "versions": versions})
    store.save(state, record)
    return {"status": "ok", "version": store.load().version, "found": report, "obsoleted": obsoleted,
            "not_found": [{"file": file, "items": missing[file]} for file in sorted(missing)]}


def classify(store: Store, state: State, args, payload) -> dict:
    entries = entries_of(payload, ("landed", "obsolete", "unchanged"), "evidence")
    record = copy.deepcopy(state.record) if state.record is not None else empty_record()
    for entry in entries:
        known(record, entry["key"])
    for entry in entries:
        item = record["items"][entry["key"]]
        if entry["state"] != "unchanged":
            change_state(item, entry["state"], entry["date"], entry["evidence"])
            item[entry["state"]] = {"date": entry["date"], "evidence": entry["evidence"]}
    if any(entry["state"] != "unchanged" for entry in entries):
        store.save(state, record)
    return {"status": "ok", "version": store.load().version,
            "items": [{"key": entry["key"], "state": record["items"][entry["key"]]["state"]} for entry in entries]}


def decide(store: Store, state: State, args, payload) -> dict:
    entries = entries_of(payload, ("picked", "declined"), "reason")
    record = copy.deepcopy(state.record) if state.record is not None else empty_record()
    for entry in entries:
        known(record, entry["key"])
    top = store.location.top
    for entry in entries:
        item = record["items"][entry["key"]]
        change_state(item, entry["state"], entry["date"], entry["reason"])
        item["decision"] = {"date": entry["date"], "reason": entry["reason"],
                            "content_hash": content_hash(top, item["file"])}
    store.save(state, record)
    return {"status": "ok", "version": store.load().version,
            "items": [{"key": entry["key"], "state": record["items"][entry["key"]]["state"],
                       "decision": record["items"][entry["key"]]["decision"]} for entry in entries]}


def number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0


def difference(test: str, before: float, after: float) -> dict:
    return {"test": test, "before": before, "after": after, "seconds": after - before,
            "factor": None if before == 0 else after / before}


def comparison(earlier: dict | None, current: dict) -> dict:
    if not current["succeeded"]:
        return {"available": False, "reason": "This measurement failed, so it is compared with none."}
    if earlier is None:
        return {"available": False, "reason": "No earlier measurement with an equal comparison key succeeded."}
    before, after = earlier["tests"], current["tests"]
    common = sorted(before.keys() & after.keys())
    changes = [difference(test, before[test], after[test]) for test in common]
    rose = sorted((change for change in changes if change["seconds"] > 0), key=lambda c: (-c["seconds"], c["test"]))
    fell = sorted((change for change in changes if change["seconds"] < 0), key=lambda c: (c["seconds"], c["test"]))
    return {"available": True,
            "against": {"measurement": earlier["measurement"], "date": earlier["date"], "commit": earlier["commit"]},
            "total": {"before": earlier["total_seconds"], "after": current["total_seconds"],
                      "seconds": current["total_seconds"] - earlier["total_seconds"],
                      "factor": None if earlier["total_seconds"] == 0
                      else current["total_seconds"] / earlier["total_seconds"]},
            "rose": rose[:TOP], "fell": fell[:TOP], "only_before": sorted(before.keys() - after.keys()),
            "only_after": sorted(after.keys() - before.keys())}


def side(measurement: dict | None, tests: list[str]) -> dict:
    if measurement is None:
        return {"state": "unavailable"}
    return {"state": "available", "measurement": measurement["measurement"], "date": measurement["date"],
            "times": {test: measurement["tests"].get(test) for test in tests}}


def measure(store: Store, state: State, args, payload) -> dict:
    key = payload.get("key")
    if not isinstance(key, dict) or any(name not in key for name in KEY_FIELDS):
        raise SpeedupError("input", "key must be an object with " + ", ".join(KEY_FIELDS))
    succeeded = need(payload, "succeeded", bool, "true or false")
    total = payload.get("total_seconds")
    tests = payload.get("tests")
    if not number(total):
        raise SpeedupError("input", "total_seconds must be a number of seconds")
    if not isinstance(tests, dict) or not all(isinstance(test, str) and test and number(seconds)
                                              for test, seconds in tests.items()):
        raise SpeedupError("input", "tests must map each test id to its seconds")
    current = {"schema_version": 1, "date": date_of(payload), "commit": commit_of(payload), "key": key,
               "succeeded": succeeded, "total_seconds": total, "tests": tests}
    existing = store.measurements(state)
    same = [item for item in existing
            if item.get("succeeded") is True and canonical(item.get("key")) == canonical(key)]
    result_comparison = comparison(same[-1] if same and succeeded else None, current)
    name = store.add_measurement(current)
    current["measurement"] = name
    candidates = sorted([*same, current] if succeeded else same,
                        key=lambda item: (moment(item["date"]), item["measurement"]))
    landed = []
    record = state.record or empty_record()
    for item in sorted(record["items"].values(), key=lambda value: value["key"]):
        if item["state"] != "landed" or not item.get("tests") or not item.get("landed"):
            continue
        when = moment(item["landed"]["date"])
        before = [candidate for candidate in candidates if moment(candidate["date"]) < when]
        after = [candidate for candidate in candidates if moment(candidate["date"]) >= when]
        landed.append({"key": item["key"], "landed": item["landed"]["date"],
                       "before": side(before[-1] if before else None, item["tests"]),
                       "after": side(after[0] if after else None, item["tests"])})
    return {"status": "ok", "version": store.load().version, "measurement": name,
            "comparison": result_comparison, "landed": landed}


def summary(measurement: dict) -> dict:
    return {"measurement": measurement["measurement"], "date": measurement["date"],
            "commit": measurement.get("commit"), "key": measurement.get("key"),
            "succeeded": measurement.get("succeeded"), "total_seconds": measurement.get("total_seconds")}


def show(store: Store, state: State, args, payload) -> dict:
    form = list(args.form or [])
    if form and not (form == ["runs"] or form == ["items"] or (len(form) == 2 and form[0] == "items")):
        raise SpeedupError("usage", "show takes no form, `items [STATE]` or `runs`; forms: " + "; ".join(FORMS))
    if len(form) == 2 and form[1] not in STATES:
        raise SpeedupError("usage", f"show items takes one of {', '.join(STATES)}")
    if state.record is None and not state.measurements:
        return {"status": "ok", "present": False, "version": state.version,
                "message": "There is no Speed-up record yet; the next /cc-feather:test-speedup run creates it.",
                "forms": FORMS}
    record = state.record or empty_record()
    measurements = store.measurements(state)
    if form == ["runs"]:
        return {"status": "ok", "present": state.record is not None, "version": state.version,
                "runs": record["runs"], "measurements": [summary(item) for item in measurements], "forms": FORMS}
    if form:
        items = sorted(record["items"].values(), key=lambda item: item["key"])
        if len(form) == 2:
            items = [item for item in items if item["state"] == form[1]]
        return {"status": "ok", "present": state.record is not None, "version": state.version, "items": items,
                "forms": FORMS}
    top = store.location.top
    changed = 0
    for path, entry in record["files"].items():
        try:
            current = content_hash(top, path)
        except SpeedupError:
            current = None
        changed += current != entry["content_hash"]
    last = record["runs"][-1] if record["runs"] else None
    counts = {name: 0 for name in STATES}
    for item in record["items"].values():
        counts[item["state"]] = counts.get(item["state"], 0) + 1
    return {"status": "ok", "present": state.record is not None, "version": state.version,
            "last_analysis": None if last is None else {"date": last["date"], "commit": last["commit"]},
            "items_by_state": counts,
            "last_measurement": summary(measurements[-1]) if measurements else None,
            "files_changed": changed, "forms": FORMS}


def prune_date(value: str | None, option: str):
    if value is None:
        return None
    try:
        return moment(value)
    except ValueError:
        raise SpeedupError("usage", f"{option} must be an ISO 8601 date: {value!r}") from None


def prune(store: Store, state: State, args, payload) -> dict:
    measured_before = prune_date(args.measurements_before, "--measurements-before")
    landed_before = prune_date(args.landed_before, "--landed-before")
    if args.keep_measurements is not None and args.keep_measurements < 0:
        raise SpeedupError("usage", "--keep-measurements must be 0 or more")
    if measured_before is None and landed_before is None and args.keep_measurements is None and not args.obsolete:
        raise SpeedupError("usage", "prune needs a selection: --measurements-before, --keep-measurements, "
                           "--obsolete or --landed-before")
    if args.version is not None:
        state = store.require(args.version)
    record = state.record or empty_record()
    measurements = store.measurements(state)
    names = set()
    if measured_before is not None:
        names |= {item["measurement"] for item in measurements if moment(item["date"]) < measured_before}
    if args.keep_measurements is not None:
        dropped = measurements[:max(len(measurements) - args.keep_measurements, 0)]
        names |= {item["measurement"] for item in dropped}
    keys = set()
    for item in record["items"].values():
        if args.obsolete and item["state"] == "obsolete":
            keys.add(item["key"])
        if (landed_before is not None and item["state"] == "landed" and item.get("landed")
                and moment(item["landed"]["date"]) < landed_before):
            keys.add(item["key"])
    selection = {"items": sorted(keys), "measurements": sorted(names)}
    if args.version is None:
        return {"status": "ok", "dry_run": True, "version": state.version, "remove": selection}
    removed = {"items": [], "measurements": []}
    pending = {"items": list(selection["items"]), "measurements": list(selection["measurements"])}
    try:
        if keys:
            changed = copy.deepcopy(record)
            for key in keys:
                del changed["items"][key]
            store.save(state, changed)
            removed["items"], pending["items"] = pending["items"], []
        for name in selection["measurements"]:
            store.remove_measurement(name)
            removed["measurements"].append(name)
            pending["measurements"].remove(name)
    except Exception as error:
        if not removed["items"] and not removed["measurements"]:
            raise
        return {"status": "error", "code": "partial", "message": f"The removal failed part-way: {error}",
                "removed": removed, "not_removed": pending, "version": store.load().version}
    return {"status": "ok", "dry_run": False, "version": store.load().version, "removed": removed}


COMMANDS = {"read": read, "changes": changes, "record-run": record_run, "classify": classify, "decide": decide,
            "measure": measure, "show": show, "prune": prune}
WRITING = {"record-run", "classify", "decide", "measure"}
STDIN = {"changes", "record-run", "classify", "decide", "measure"}
