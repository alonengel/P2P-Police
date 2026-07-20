# Evidence — the RL campaign (pursuit side)

> Status: complete. Every number below regenerates from a committed script
> and lands in a committed artifact; promotion decisions went through gates
> coded BEFORE results existed. Twin doc (evasion side): the sibling repo's
> `docs/evidence/rl-campaign.md`.

## Setup / provenance

| Item | Value |
|---|---|
| Board | 7x7, starts (0,0)/(3,3), 14 barriers, 35 moves (signed constitution) |
| Scripts | `scripts/train_rl.py`, `train_deep_rl.py`, `sweep_deep_rl.py`, `balance_run.py` |
| Artifacts | `results/experiments/{rl_training, deep_rl_training, deep_rl_sweep, wire_shape_balance}.json`, curves in `assets/` |
| Determinism | fixed base seeds; evals on dedicated RNG streams; 100-game held-out finals |

## Observed (chronological)

1. **Linear Q-learning (movement-only)**: 1.00 vs a random walker;
   **0.00/100 vs a perfect BFS-distance evader** — the theorem (movement
   alone cannot corner a distance-maximizer) reproduced as a measurement,
   and later as a unit test (`test_arena_thief.py`).
2. **Double-DQN with barrier actions** (pure-Python MLP, replay + frozen
   target + containment-shaped reward): capture vs the perfect evader
   **0.00 -> 0.74/100**, statistically tying the hand-engineered
   PoliceBrain (0.73/100) — trap-building learned from scratch.
3. **v3 — ensemble + belief-noise domain randomization** (perfect evader +
   the twin's learned counter-evader + random; 40% jittered observations):
   0.74 retained, **0.78 under belief noise** (noise regularizes; the
   policy survives partial observability), 1.00 vs random — and **0.00 vs
   the counter-evader even when trained directly against it**.
4. **Six-config hyperparameter sweep** (equal 1200-episode budget):
   learning rate / width / replay depth barely matter; the exploration
   floor dominates (0.82 short-budget winner). The gated full-budget
   promotion REGRESSED to exactly 0.74 and was rejected.
5. **Wire-shape balance (cop side)**: PoliceBrain 23/32 exact vs **28/32
   blinded** (chasing where the evader WAS works); DQN 24/24 identical;
   both cops 0/32 vs the trap-aware counter-evader in BOTH arms.

## Findings

- Three independent 4000-episode runs converge on **0.74 vs the perfect
  evader: the ceiling is the game's structure** (barrier budget +
  move-forfeit economics), not tuning.
- The **cop role is information-insensitive** — the wire-shape question is
  entirely an evader-side phenomenon (twin doc carries that half).
- Training curves oscillate (catastrophic forgetting vs deterministic
  adversaries): **best-eval checkpointing is load-bearing**. Gates rejected
  a worse model twice on this side alone.

## What this does NOT prove

- Nothing here measures play against OTHER teams' brains (the separation
  rule forbids cross-repo evaluation); cross-team numbers exist only for
  the physics/interop layer.
- The perfect evader is trap-naive; a trap-aware evader beats every cop we
  own in both information modes — disclosed, not hidden.
