"""PreToolUse hook: block forbidden package-manager commands (uv-only rule).

The submission guidelines forbid pip/venv/python -m pip anywhere in the
project. Exit 2 blocks the command and tells Claude why.
"""

import json
import re
import sys

FORBIDDEN = [
    (r"\bpip\s+install\b", "pip install is forbidden - use 'uv add <pkg>'"),
    (r"\bpython\s+-m\s+pip\b", "python -m pip is forbidden - use uv"),
    (r"\bpython\s+-m\s+venv\b", "python -m venv is forbidden - uv manages the env"),
    (r"\bvirtualenv\b", "virtualenv is forbidden - uv manages the env"),
    (r"\bpip3?\s+(?:un)?install\b", "pip is forbidden - use uv"),
]


def main() -> int:
    payload = json.load(sys.stdin)
    command = (payload.get("tool_input") or {}).get("command", "")
    for pattern, message in FORBIDDEN:
        if re.search(pattern, command):
            print(f"BLOCKED (uv-only rule): {message}", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
