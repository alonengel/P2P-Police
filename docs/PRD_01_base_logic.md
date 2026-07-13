# PRD 01 — Base game logic (rulebook ch. 3–4, stage 1 of 7)

## Goal

Pure, single-process game physics — no networking, no AI, no crypto. Everything
here is **parity-locked** with the twin repo (ADR-0001) and pinned by golden
vectors, because both peers must compute byte-identical physics from the signed
config.

## Scope (modules under `src/*/domain/`)

| Module | Contract |
|---|---|
| primitives | `Cell=(row,col)` top-left origin, 0-indexed; `Move` N/S/E/W/STAY with row/col deltas (N=row−1); `Role`; `GamePhase`; `Outcome` |
| errors | typed domain exceptions (illegal move / barrier / transition) |
| board | grid bounds, permanent barriers, orthogonal+STAY legality, `is_surrounded` (all 4 neighbors impassable) |
| rules | barrier-placement legality (distance ≤1 incl. own cell, quota, not duplicated); captures: landing / barrier-on-thief / surrounded-thief; survival at threshold |
| scoring | outcome → (cop, thief) points: capture 20/5, survival 5/10, technical loss 0/0; series tie helper (2/2) |
| scent | 5×5 radial kernel (book reference matrix, center 0.9); update once per FULL turn: τ′ = clamp((1−ρ)·τ + Δτ, 0, center); per-agent fields |
| engine | turn loop: cop acts (move OR barrier — placing forgoes the move), thief moves, full-turn boundary → both scent fields update, outcome check |
| state_machine | WAITING_FOR_OPPONENT → COMPUTING_MOVE → {COMMITTING\|TECHNICAL_LOSS} → AWAITING_REVEAL → {VERIFYING\|TECHNICAL_LOSS} → back; TECHNICAL_LOSS terminal; illegal transition raises |

## Binding requirements encoded as tests

- Diagonal movement impossible by construction; illegal targets (off-board,
  barrier) rejected (rules 13–14).
- Barrier beyond quota rejected; placement only at distance ≤1 (book milestone).
- Barrier on thief's cell = capture; fully-surrounded thief = capture — both
  AUTOMATIC (no claim) (rules 46–47). Landing capture is a separate event that
  will carry a Capture Claim at the protocol layer (Phase 6).
- Scent decay exactly ONCE per full turn (after both agents acted); silent cell
  = 0.0; values clamped to [0, 0.9].
- Scoring per the fixed table (rule 48); technical loss = 0/0.
- Golden vectors (`tests/vectors/physics_vectors.json`, byte-identical with the
  twin): kernel matrix, single-deposit decay series, corner-clipped emission,
  two-turn field evolution.

## Documented assumptions (negotiable items pinned later in negotiation)

- Intra-round order: cop acts first, thief second (book Fig. 6 depiction);
  formally agreed per game in Phase 2 negotiation.
- Reaching max_moves uncaptured counts as survival (defaults make
  max_moves = survival_threshold = 35, so the branch is theoretical).
- Emission starts at the first full-turn boundary (no turn-0 emission).
- Re-emission on an occupied cell is capped at center intensity (τ ≤ 0.9,
  matching the book's stated range and Fig. 5). ⚠ This clamp EXTENDS the
  book's literal formula (which only floors at 0) — it MUST be stated
  explicitly in the human-readable scent model exchanged and SHA-256-locked
  with each opponent (rule 23, Phase 6 deliverable), or a literal-formula
  opponent diverges on any dwelt cell.
- Reaching the max_moves hard cap uncaptured is DEFINED as thief survival;
  with the default 35/35 config the distinction never arises (spec-audit
  MINOR-4).

## Definition of done

Full random-legal self-play game runs crash-free to CAPTURE or SURVIVAL;
all unit tests green in BOTH repos against the same vectors; parity check OK;
coverage ≥85%; ruff clean; ≤150 code lines per file.
