"""Verify the twin repos' shared physics is byte-identical (paired-commit rule).

The rulebook requires both peers to compute identical physics (the shared
config is signed and mutually audited); this project keeps the physics in
duplicated-not-imported `domain/` modules, so drift between the twins is the
main failure risk. This script hashes every physics-relevant file here and in
the sibling checkout and reports any mismatch.

Skips gracefully (exit 0) when the sibling checkout is absent (e.g. CI clones
only one repo); the golden vectors in tests/vectors/ still guard behavior.

Usage: uv run python scripts/check_physics_parity.py
"""

import hashlib
from pathlib import Path

# Role-specific names that legitimately differ between the twins.
ROLE_TOKENS = {"p2p_police": "p2p_thief", "p2p_thief": "p2p_police"}

PARITY_GLOBS = [
    "src/*/domain/*.py",
    "tests/vectors/*.json",
]


def normalized_digest(path: Path) -> str:
    """SHA-256 of file content with role package names canonicalized."""
    text = path.read_text(encoding="utf-8")
    for token, twin in ROLE_TOKENS.items():
        text = text.replace(token, min(token, twin))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parity_files(root: Path) -> dict[str, Path]:
    """Map role-agnostic relative keys to files under the given repo root."""
    found: dict[str, Path] = {}
    for pattern in PARITY_GLOBS:
        for path in sorted(root.glob(pattern)):
            key = "/".join(path.relative_to(root).parts)
            for token, twin in ROLE_TOKENS.items():
                key = key.replace(token, min(token, twin))
            found[key] = path
    return found


def main() -> int:
    here = Path(__file__).resolve().parents[1]
    sibling_name = "P2P-Thief" if here.name == "P2P-Police" else "P2P-Police"
    sibling = here.parent / sibling_name
    if not sibling.is_dir():
        print(f"SKIP: sibling checkout not found at {sibling}")
        return 0

    mine, theirs = parity_files(here), parity_files(sibling)
    problems = []
    for key in sorted(set(mine) | set(theirs)):
        if key not in mine:
            problems.append(f"MISSING here: {key}")
        elif key not in theirs:
            problems.append(f"MISSING in sibling: {key}")
        elif normalized_digest(mine[key]) != normalized_digest(theirs[key]):
            problems.append(f"DRIFT: {key}")
    for problem in problems:
        print(problem)
    if problems:
        return 1
    print(f"OK: {len(mine)} physics files identical with {sibling_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
