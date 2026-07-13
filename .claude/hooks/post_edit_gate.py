"""PostToolUse hook: fast quality gate on every edited Python file.

Runs ruff and the 150-code-line cap on JUST the touched file so violations are
fixed the moment they appear instead of at commit time. Exit 2 blocks and
feeds the tool output back to Claude.
"""

import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    payload = json.load(sys.stdin)
    file_path = (payload.get("tool_input") or {}).get("file_path", "")
    if not file_path.endswith(".py"):
        return 0
    path = Path(file_path)
    if not path.exists():
        return 0

    failures = []
    for label, cmd in (
        ("ruff", ["uv", "run", "ruff", "check", str(path)]),
        ("line-cap", ["uv", "run", "python", "scripts/check_line_cap.py", str(path)]),
    ):
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            failures.append(f"[{label}]\n{result.stdout}{result.stderr}")

    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
