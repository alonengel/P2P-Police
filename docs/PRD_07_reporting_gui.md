# PRD 07 — Reporting, artifacts, email & the two UIs

## Scope & non-goals

Everything after the last move: the four Table-20 artifacts, the automatic
report email, the live local-truth view, and the replay witness. Non-goal:
result AGREEMENT semantics beyond the audit (rules 35-36 are exercised in
the runtime's finish path).

## Design / I/O contracts

- **Four artifacts per game**, one shared derived game_uid, filenames from
  game_id (declaration / config_gNN / log_gNN / result): emitted on EVERY
  game end including technical losses (rules 32/35 — the catch-all funnel;
  an unreported forfeit is the worst outcome the league allows). The
  result carries the spaced sign-then-insert consensus_signature and the
  gatekeeper monitoring view.
- **Email** (rule 32): send-only Gmail scope (rule 30, guard-tested),
  through the single per-run gatekeeper, `[email] mode` config-gated —
  disabled in dev, send for counted games. ONE attachment: the result
  JSON only (same canonical bytes as the body) — NOT all four kinds and
  never the 14-file set. Superseded here per ADR-0012 second addendum:
  the course repo's own bot ruled the automated email carries only
  result_<game_id>.json; logs/configs/declaration reach the lecturer via
  GitHub, and logs serve the Replay Viewer, not the mail.
- **Live GUI** (rules 8-9): own position + belief heatmap + received hints
  ONLY — never the objective board; YOUR-TURN/LOCKED banner mirrors the
  FSM. `info_mode=exact` changes what the BRAIN sees, never the display.
- **Replay viewer** (rule 20): loads a log artifact, re-verifies every
  sealed record (green "Verified OK" / red "TAMPERED - game void"), reads
  board geometry from the game's OWN archived config artifact — a third
  party replays the negotiated terms, not our defaults.

## Decisions & alternatives rejected

- **Draft-mode email** (the book's own config example): rejected — the
  gmail.send scope cannot create drafts and rule 32 mandates automatic
  reporting; the book-internal contradiction is documented (ADR lineage).
- **Objective-board debug view**: rejected outright (rule 9 sanction is
  disqualification); replay shows both agents legally because post-game
  logs are revealed evidence.

## Test plan / acceptance (all met)

Artifact schemas + emission on success AND technical loss; email path
mocked (gatekeeper-gated, never live in CI); GUI screenshots for every
state committed under assets/; replay TAMPERED demo committed; verify-log
physics path tested against the real committed log and a forged copy.
Evidence: `docs/evidence/rule-guards.md`, `docs/evidence/public-games.md`, UI.md.
