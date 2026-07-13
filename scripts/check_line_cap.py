"""Enforce the 150-code-line file cap (submission guidelines section 3.2).

Counts CODE lines only: blank lines and comment-only lines are excluded, as
the guidelines measure logic size, not file length. Docstrings count as code
because they occupy statement positions and grow real file weight.

Usage: uv run python scripts/check_line_cap.py [paths...]
With no arguments, scans src/ and tests/.
"""

import sys
import tokenize
from pathlib import Path

CAP = 150


def count_code_lines(path: Path) -> int:
    """Count lines holding at least one non-comment token."""
    code_lines: set[int] = set()
    with path.open("rb") as stream:
        try:
            for token in tokenize.tokenize(stream.readline):
                if token.type in (
                    tokenize.COMMENT,
                    tokenize.NL,
                    tokenize.NEWLINE,
                    tokenize.ENCODING,
                    tokenize.ENDMARKER,
                    tokenize.INDENT,
                    tokenize.DEDENT,
                ):
                    continue
                for line_no in range(token.start[0], token.end[0] + 1):
                    code_lines.add(line_no)
        except tokenize.TokenError as error:
            print(f"WARN {path}: tokenize failed ({error}); falling back to raw count")
            return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    return len(code_lines)


def collect_targets(args: list[str]) -> list[Path]:
    """Resolve CLI args (files or dirs) to the .py files to check."""
    roots = [Path(a) for a in args] if args else [Path("src"), Path("tests")]
    targets: list[Path] = []
    for root in roots:
        if root.is_dir():
            targets.extend(sorted(root.rglob("*.py")))
        elif root.suffix == ".py" and root.exists():
            targets.append(root)
    return targets


def main(argv: list[str]) -> int:
    offenders = []
    for path in collect_targets(argv):
        count = count_code_lines(path)
        if count > CAP:
            offenders.append((path, count))
    for path, count in offenders:
        print(f"FAIL {path}: {count} code lines (cap {CAP})")
    if offenders:
        return 1
    print(f"OK: all checked files within the {CAP}-code-line cap")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
