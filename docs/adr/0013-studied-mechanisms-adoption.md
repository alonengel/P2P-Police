# ADR-0013: Cross-team studied mechanisms — adoption with attribution

Date: 2026-08-22 · Status: accepted

## Context

The league's strongest team (imreeyal — Imree; nine counted 90-30
sweeps) granted us read access to their private cop and thief repos.
Their own code credits OUR doctrine layer as "studied, no code copied"
(their endgame and wall-forecast modules) — the league norm both teams
now follow: **mechanisms may be studied and re-implemented with
attribution; code is never copied; repos are never imported** (course
attribution requirement; ADR-0001's separation rule untouched).

Independently, the 2026-08-22 najamjad series exposed a latch hazard in
our scent trust boundary: their serializer floors sub-0.005 residues to
zero, and consecutive floored frames could latch our gate off for a
whole game (three consecutive law-breaks latch by design, ADR-0010).

## Decision

Three mechanisms adopted, each re-implemented in our own idiom:

1. **Floored-residue tolerance** (`peer/floor_tolerance.py`, ours from
   our own forensics): a transition unsolvable ONLY because cells at or
   under `floor_tolerance_eps` (0.006) read zero is re-solved with
   lawful decay restored; accepted frames record `floored_steps`
   evidence beside `refused_steps`. Validated on the day's sealed data:
   the four live refusals become four floored-notes, zero refusals.
2. **Safe-region compression term** (`strategy/region_race.py`,
   mechanism studied from imreeyal's mobility/containment leaf): the
   pursuit score prices the believed thief's safe ground (two-front BFS
   race) beside distance. `[strategy.pursuit] w_safe_region` — **kept
   DEFAULT OFF (0.0)**. The recorded-tape sweep measured it strongly
   positive on runner classes (55/55 kept, mean conversion t15.7 ->
   t12.0 at 0.15), but the percher mimics collapse under it (0/10, was
   10/10) and the live-dodger drill drops to 6/15: against a stationary
   thief the term rewards containment hovering over walking the landing
   in. Same verdict shape as imreeyal's own w_intercept (positive on two
   classes, negative on a third -> default 0.0, per-pairing option).
   Never arm it against a parking endgame (najamjad parks).
3. **Barrier reserve** (`[strategy.trap] reserve`, studied from their
   contain_reserve): the trap gate never spends the last N walls; the
   endgame solver's proven finishing seal stays affordable. Default 0
   in code; armed at 2 in game.toml — full strategy suite green with it
   (every drill, mimic and tape).

## Consequences

- Attribution recorded here and in module docstrings; no code crossed
  repos; parity scope (domain/) untouched.
- Both knobs are config-armed with the sweep evidence quoted beside the
  value — the keep-gate discipline (docs/evidence/cop-strength.md).
- The thief repo carries the floor tolerance identically (twin
  perception); the cop-side pursuit knobs do not apply there.
