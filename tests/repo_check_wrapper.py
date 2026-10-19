"""Test wrapper for the repo-check tool:
python -I -B repo_check_wrapper.py <record file> [--overlay <overlay file>] <tool> <directory>

Installs an audit hook for `open`, `os.scandir` and `os.listdir`, loads the tool with runpy, replaces the tool's one
metadata-and-open function `fs` with a recording wrapper, runs the tool's `main(argv)` and writes the record, a JSON
list of [event, path] pairs, to the record file. The record file lies outside the checked directory.

With --overlay, the overlay file is a JSON object mapping absolute paths to "dir" or "file": an `lstat` of such a path
through `fs` returns metadata of that kind as if the entry existed, so that a test can build a layout the platform
cannot, such as a repository around the Git executable's own directory. Every other call goes to the tool's own `fs`.
Holds no tests, so discovery does not load it as one."""

import json
import os
import runpy
import stat
import sys

record_path, *rest = sys.argv[1:]
overlay = {}
if rest[:1] == ["--overlay"]:
    with open(rest[1], encoding="utf-8") as handle:
        overlay = json.load(handle)
    rest = rest[2:]
tool, *arguments = rest
events = []


def plain(path: str) -> str:
    if path.startswith("\\\\?\\UNC\\"):
        path = "\\\\" + path[8:]
    elif path.startswith("\\\\?\\"):
        path = path[4:]
    return os.path.normcase(os.path.normpath(path))


faked = {plain(path): kind for path, kind in overlay.items()}


def audit(event, args):
    if event in ("open", "os.scandir", "os.listdir") and args and isinstance(args[0], (str, bytes, os.PathLike)):
        events.append([event, os.fsdecode(args[0])])


def fake(kind: str):
    mode = (stat.S_IFDIR | 0o755) if kind == "dir" else (stat.S_IFREG | 0o644)
    return type("Metadata", (), {"st_mode": mode, "st_ino": 0, "st_dev": 0, "st_nlink": 1, "st_size": 0,
                                 "st_file_attributes": 0, "st_reparse_tag": 0})()


sys.addaudithook(audit)
module = runpy.run_path(tool, run_name="repo_check_under_test")
namespace = module["main"].__globals__
original = namespace["fs"]


def observed(operation, path):
    events.append(["fs." + operation, os.fsdecode(path)])
    if operation == "lstat" and plain(os.fsdecode(path)) in faked:
        return fake(faked[plain(os.fsdecode(path))])
    return original(operation, path)


namespace["fs"] = observed
code = namespace["main"](arguments)
recorded = list(events)
with open(record_path, "w", encoding="utf-8") as handle:
    json.dump(recorded, handle)
sys.exit(code)
