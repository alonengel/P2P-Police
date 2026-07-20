# PRD 03 — Strategy module (the brain seam and the shipped brains)

## Scope & non-goals

The decision layer between perception and commitment: a `BrainBase` seam
(`strategy/brain_base.py`) the runtime calls once per half-turn, resolved
from private config (`[strategy] police_class/thief_class`, Table 22 —
import errors surface loudly; a silently wrong brain is a league-day
disaster). Non-goals: hint TEXT generation (PRD 04's verbal layer) and any
LLM involvement in moves (rule 25 — enforced by an AST-scan guard test).

## Design / I/O contracts

- `BrainBase.decide(engine, belief=None) -> action dict` — pure decision;
  `belief` is the Dec-POMDP observation surface (None = exact-information
  play, legal only under a pair-locked bookletter wire; see the
  `[strategy] info_mode` switch, runtime-tested).
- Shipped pursuit brain (`police_brain.py`): belief-peak chase + surgical
  barrier placement; measured 0.73/100 vs a perfect full-info evader.
- Optional deep brains via the same seam: linear Q (`rl_brain.py`) and the
  Double-DQN with barrier actions (`rl_deep.py`, PRD 08) — league defaults
  remain the hand-tuned brains (no training-collapse risk).
- Arena adversaries (`arena_thief.py`) exist for training/benchmarks only.

## Decisions & alternatives rejected

- **Belief-fed by default** — brains hunt the belief peak, never the true
  cell; the exact-information mode is config-gated to a signed wire lock.
- **Minimax over full state**: rejected — the belief-space branching on
  7x7 with barriers put depth out of the line-cap/latency budget; shallow
  heuristics + learned policies measured competitive instead.
- **LLM-advised moves** (book's conditional exception): rejected outright —
  three conjoined conditions plus hallucination risk vs zero measured gain.

## Test plan / acceptance (all met)

- Seam: the exact league config line loads through `resolve_brain`; a
  RandomBrain override test proves substitution.
- Legality: every emitted action valid under engine validation in both
  exploration and greedy modes (brain tests + engine rejection tests).
- Performance floors: pursuit beats a random evader; the evidence pack
  (`docs/evidence/rl-campaign.md`) carries the measured tables.

## Evidence

`docs/evidence/rl-campaign.md` · `results/experiments/*.json` · PRD 08.
