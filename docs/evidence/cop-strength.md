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

## The dwell plateau: localization, not lookahead (2026-07-26)

The keep-gates above both failed for ONE root cause — a posterior too blunt
to act on. Attacking the blur directly beat every attempt to search harder
on top of it.

**The physics.** Under re-emission `tau' = (1-rho)*tau + delta` a kernel cell
converges to `delta / rho`. Every offset with `delta >= rho * 0.9` therefore
reaches the clamp; the kernel's four far corners (`delta = 0.04`) never do.
A rival that dwells stamps its own kernel window onto the board at max
intensity, board-clipped. Reach-decoding alone cannot read it — every
saturated cell decodes reach 0, so the evidence ties flat across the whole
plateau and the argmax lands wherever diffusion happens to favour. Fitting
the SHAPE back (Jaccard over each candidate's clipped saturating window)
inverts the plateau to the emitter's own cell. Corners and edges make the
fit *sharper*, not weaker: clipping removes hypotheses.

**Localization measured** (1,292 blind turns, ground truth from the closed
loop; `domain/evidence.py::plateau_origin`, boost in `BeliefMap.observe_plateau`):

| estimator | fires | exact | mean error |
|---|---|---|---|
| belief argmax (before) | every turn | 7% | 2.42 cells |
| plateau fit, `fit >= 0.9`, margin 0.05 | 43% of turns | **89%** | **0.11 cells** |

Loosening to `fit >= 0.7` fires on 57% of turns at 82% exact; the tighter
gate is kept because a pin is acted on as certainty. It abstains on silence,
on a lone fresh spike (one cell — no shape) and on a straight open march (a
smear fitting no single window). Abstention is the safety property.

**Capture rate**, same 150-game closed loop, shipped brain otherwise
unchanged: **0.147 -> 0.733**. The surgical barrier policy had been
information-starved, not badly designed — it fired 0.00 walls/game before and
1.59 after, and 74 of the 110 captures were walled.

## Barrier-gate sweep ([strategy.trap])

With a pin worth acting on, the quota gate itself was re-swept (150 games at
the winner, 60 at the rest). `escape_limit` and `range` moved together:

| gate | 2 (old) | **3** | 4 | 5 |
|---|---|---|---|---|
| capture rate | 0.733 | **0.847** | 0.817 | 0.817 |
| walls/game | 1.59 | 3.39 | 3.22 | 3.22 |

An unspent quota buys nothing: 14 barriers over 35 turns is generous, and
hoarding them was costing more than spending them. Both values are now
config-driven (`[strategy.trap]`, defaults in `shared/tuning.py`) rather than
frozen constants in the brain.

**Rejected (honest negative): area-denial herding.** A policy spending
barriers on the placement that maximally CUTS the believed thief's reachable
region produced outcomes *byte-identical* to the shipped brain over 60 games
— the region gate never opened, because a region small enough to be worth
cutting is already a region the trap gate walls one turn later. Not shipped;
the trap gate covers the same ground with no extra machinery.

**Net for the cop:** capture rate **0.147 -> 0.847** with no change to the
pursuit score, no new brain, and no lookahead.
