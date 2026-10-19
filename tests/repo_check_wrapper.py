"""Test wrapper for the repo-check tool: python -I -B repo_check_wrapper.py <record file> <tool> <directory>

Installs an audit hook for `open`, `os.scandir` and `os.listdir`, loads the tool with runpy, replaces the tool's one
metadata-and-open function `fs` with a recording wrapper, runs the tool's `main(argv)` and writes the record, a JSON
list of [event, path] pairs, to the record file. The record file lies outside the checked directory. Holds no tests,
so discovery does not load it as one."""

import json
import os
import runpy
import sys

record_path, tool, *arguments = sys.argv[1:]
events = []


def audit(event, args):
    if event in ("open", "os.scandir", "os.listdir") and args and isinstance(args[0], (str, bytes, os.PathLike)):
        events.append([event, os.fsdecode(args[0])])


sys.addaudithook(audit)
module = runpy.run_path(tool, run_name="repo_check_under_test")
namespace = module["main"].__globals__
original = namespace["fs"]


def observed(operation, path):
    events.append(["fs." + operation, os.fsdecode(path)])
    return original(operation, path)


namespace["fs"] = observed
code = namespace["main"](arguments)
recorded = list(events)
with open(record_path, "w", encoding="utf-8") as handle:
    json.dump(recorded, handle)
sys.exit(code)
