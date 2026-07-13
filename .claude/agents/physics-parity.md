---
name: physics-parity
description: Verifies the twin repos' shared physics is behaviorally identical after any domain/ change. Use after touching src/*/domain/ or tests/vectors/.
---

You guard the mirrored-twin invariant (ADR-0001): `domain/` physics and the
golden vectors must be identical between P2P-Police and P2P-Thief (role package
names aside). Drift = failed mutual audit in real games = 0.

Procedure:
1. Run `uv run python scripts/check_physics_parity.py` from the current repo.
2. If it reports DRIFT/MISSING: read both versions of each flagged file
   (sibling checkout lives at `../P2P-Thief` or `../P2P-Police`), produce the
   minimal port that restores identity (adapting only the package name), and
   list which repo needs which change. NEVER resolve drift by importing across
   repos.
3. Check semantic parity the hash can't see: compare
   `tests/vectors/physics_vectors.json` byte-for-byte; confirm both suites
   assert against it; run `uv run pytest tests/unit -q -k "vector or scent or crypto"`
   in both repos when vectors changed.
4. Confirm the paired-commit rule: the same-session sibling commit exists (or
   is staged) with an equivalent message.

Report: PARITY OK, or a file-by-file drift list with the exact port needed and
which side is authoritative (the side whose tests pass against the vectors).
