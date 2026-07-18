# PRD 08 — Deep-RL pursuit: MLP Q-network with barrier actions

## Description & theory

The linear Q-learner (PRD within README §3) is movement-only, and its
recorded negative result — 0.00 vs a perfect BFS-distance evader — is a
theorem about movement-only pursuit on an open board. Barriers are the
mechanism that breaks the theorem. `strategy/rl_deep.py` extends the RL
action space to barrier placement and replaces the linear value function
with a small MLP (10 → tanh(12) → 1, hand-rolled backprop, pure Python —
rule 25: moves stay algorithmic; zero new dependencies). Training
(`scripts/train_deep_rl.py`) is Double-DQN: experience replay, a frozen
target network for value estimation with online-net action selection
(curbing max-operator overestimation), containment-shaped reward
(per-step "rent" on the thief's reachable region), best-eval checkpointing,
and — v3 — an adversary ENSEMBLE plus belief-noise domain randomization
(40% of decisions see a Chebyshev-≤2-jittered thief cell) so the policy
survives partial observability.

## I/O contracts

- `features(engine, action, thief=None) -> list[10 floats]` — pure; the
  after-state of a move OR a hypothetical barrier; `thief` overrides the
  target cell (belief argmax in blind games).
- `candidate_actions(engine) -> list[action dict]` — legal moves + barrier
  placements validated by the same `validate_barrier_placement` the engine
  enforces (legality is guaranteed twice).
- `DeepQBrain(role, rng).decide(engine, belief=None) -> action dict` — the
  standard brain seam; greedy at play time; weights loaded repo-anchored
  from `results/deep_rl_weights.json` (loud warning on absence).
- Artifacts: `results/experiments/deep_rl_training.json` (+ sweep file),
  `assets/deep_rl_curve.png`, weights JSON with full hyperparameters.

## Measured performance (100 held-out games each)

| Policy | vs perfect evader |
|---|---|
| Linear, movement-only | 0.00 (provable) |
| Hand-coded PoliceBrain | 0.73 |
| Deep v2/v3 (learned barriers) | **0.74** (v3: 0.78 under belief noise) |

Arms race: the twin's counter-evader survives every cop version 1.00 — the
evader holds the structural advantage at this barrier budget. A six-config
hyperparameter sweep + a gated full-budget promotion confirmed the 0.74
ceiling is structural (three independent 4000-episode runs converge on it).

## Alternatives considered & rejected

- **torch/numpy** — heavy dependencies for a 10×12 network; hand-rolled
  backprop is ~40 lines and auditable.
- **Tabular Q** — cannot represent barrier-modified boards (state space
  explodes); BFS features generalize.
- **Shipping the deep brain as league default** — rejected: training-collapse
  risk (curves show catastrophic forgetting cycles) vs engineered tactics
  that cannot regress; the deep brain remains a `[strategy]`-seam option.
- **Last-episode weights** — rejected for best-eval checkpointing; the
  oscillating curves make this load-bearing, not cosmetic.

## Success criteria (all met, tested)

- Every emitted action legal under engine validation (tests: extended action
  space, exploration and greedy modes).
- MLP math verified (deterministic forward; SGD reduces error toward target).
- The exact league config line loads through `resolve_brain` (seam test).
- The uncatchability theorem reproduced as a test (perfect evader survives a
  movement-only chaser).
- Promotion discipline: shipped weights change ONLY through a coded gate
  (demonstrated twice by rejection: sweep winner and thief fine-tune).
