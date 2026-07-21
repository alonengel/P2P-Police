# Cop-strength boosters: exact endgame solver + info-gain term (keep-gate)

Two belief-mode boosters for `PoliceBrain`, built under a hard keep-gate:
**a feature stays enabled only if it measurably raises capture rate.**
Both failed the gate. The modules ship tested and correct, defaults OFF,
and this document records the negative results honestly.

## Mechanisms

- **Exact endgame solver** (`strategy/endgame.py`, `[strategy.endgame]`):
  memoized win/loss minimax (the exists/forall early exits are alpha-beta
  specialized to boolean payoffs) over the compact state (cop cell,
  candidate thief cell, hypothetical-barrier delta, turns left). BELIEF-
  CORRECT: a capture counts as forced only when ONE first action forces it
  against EVERY thief cell holding belief mass ≥ `support_mass_threshold`
  and every legal reply — the rival's true cell is never read (guard-tested
  in `test_endgame*.py`). Iterative deepening returns the SHALLOWEST forcing
  depth, so re-solving each turn strictly closes on the capture. Compute is
  hard-capped (`node_cap`, `time_cap_ms`); a cap hit defers to the heuristic
  — the turn deadline is never at risk. Wired as a `decide()` pre-check.
- **Info-gain term** (`strategy/info_gain.py`, `[strategy.info_gain]`): for
  each candidate landing, the expected belief-entropy reduction given the
  scent-kernel reading the cop would collect there (computed on `values()`
  snapshots — live belief state untouched), blended into the pursuit score
  as `-BFS_distance + weight * gain`.

## Measurement (`scripts/measure_cop_strength.py`)

80 seeded games/arm (20 seeds x 4-evader pool), same seeds across arms; the
cop always blind (scent-fed `BeliefMap`). Pool: belief-driven heuristic
evader (blind), RandomBrain (blind calibration floor), PerfectEvader and the
twin-trained DeepEvader (full information). Results:
`results/experiments/cop_strength.json` (2026-07-21).

| arm        | capture rate | mean turns-to-capture | solver fired |
|------------|--------------|-----------------------|--------------|
| baseline   | 0.237        | 9.16                  | –            |
| +endgame   | 0.237        | 9.16                  | **0 turns**  |
| +info_gain | 0.237        | 9.11                  | –            |
| +both      | 0.237        | 9.11                  | 0 turns      |

Every capture came from the random evader (0.95 within-pool rate); the
strong evaders sit at 0 captures for a blind cop in every arm — consistent
with the pre-existing `deception_policy.json` (0/60).

## Why the endgame solver never fires (root cause, probed)

The gate `support <= max_support_cells` never opens in real play. Probed
support-size histograms over live blind games: the scent-floor belief
(`SCENT_LIKELIHOOD_FLOOR = 0.05` + kernel spread + diffusion) keeps 7–10
cells above the 0.05 mass threshold on almost every turn (top-3 cells cover
only ~41% of mass); adding the hint channel barely changes it (support <= 3
once in ~480 turns). Loosening the gate to K=6 and K=8 still produced **0
fires in 30 games each**: a support that wide is genuinely not force-
capturable by any single sound first action. This is structural, not a bug:
under the current belief pipeline, belief-correct forced-capture windows do
not occur.

## Info-gain sweep

Weights 0.5 / 1.0 / 2.0 / 4.0 vs the heuristic and random evaders (30 seeds
each): capture rate unmoved at every weight (heuristic 0/30, random 28/30
everywhere); the only effect was mean turns-to-capture vs the random evader
9.16→9.11 (~0.3 turns) — noise-level, not a capture-rate gain.

## Keep-gate verdict

- `[strategy.endgame] enabled = false` (default; `shared/tuning.py` agrees).
- `[strategy.info_gain] enabled = false` (default; `shared/tuning.py` agrees).
- Both modules stay in the tree fully tested: the solver becomes valuable
  the moment the belief pipeline sharpens (e.g., richer observations or a
  tighter scent floor) — flipping one boolean re-arms it, and the arena
  harness re-measures it in one command.

Re-run: `uv run python scripts/measure_cop_strength.py 20`
