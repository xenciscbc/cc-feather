"""Feather's Checkout lease command (Python 3.11+, standard library only).

It imports low-level helpers from the handoff skill's package, which the plugin ships beside this skill as
skills/handoff/scripts/feather_handoff; the handoff tool itself is never changed."""
import json
import os
import sys

sys.dont_write_bytecode = True

if sys.version_info < (3, 11):
    print(json.dumps({"status": "error", "code": "python-version",
                      "message": "Python 3.11+ required. Ask whether to help install it."}))
    sys.exit(2)

_SKILLS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(1, os.path.join(_SKILLS, "handoff", "scripts"))

from feather_leases.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
