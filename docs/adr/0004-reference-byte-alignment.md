# ADR-0004 — Adopt the official reference's byte-level hash forms

Date: 2026-07-18. Status: accepted. Scope: both repos (mirrored twins, ADR-0001).
Rollback point: tag `checkpoint-pre-interop-2026-07-18`.

## Context

The rulebook is internally contradictory about the commit preimage: ch. 5's listing
hashes a canonical JSON object with the nonce among the fields, while its replay
sketch hashes only `nonce|move` (which binds neither state nor intent — broken, and
flagged by the book itself as a simplification). The book's front matter says examples
illustrate rather than legislate, and contradictions may be resolved either way if
documented. Our original, documented choice (`SHA256(canonical({"payload": p,
"nonce": n}))`, `ensure_ascii=true`) was therefore legal — but the official reference
implementation (rmisegal/Game-P2P-Cop-Chase v3.0.0, our local copy in
`../docs/DemoExamples`) computes different bytes:

- canonical JSON with `ensure_ascii=false` (native UTF-8) — `domain/crypto.py:22`;
- commit = `SHA256(canonical(payload) + "|" + nonce)` — `domain/crypto.py:30`;
- `game_uid` derived from `SHA256(canonical(terms)|sorted-group-ids)[:16]` —
  `domain/game_ids.py:31`;
- a settlement consensus signature over the report body in a SECOND canonical form:
  `sort_keys=true, ensure_ascii=false`, DEFAULT (spaced) separators, computed before
  the signature key is inserted — `report/report_writer.py:24,81`.

A cross-team interop conformance kit circulating in the league pins exactly these
reference bytes with test vectors. Teams building from the reference will produce
these forms; against our original forms, a cross-team game fails at the negotiation
sha exchange and — past it — every audit reads mutual TAMPERED on the first
non-ASCII hint (rule 19 makes any mismatch fatal, no interpretation).

## Decision

Adopt the reference's byte forms as an interoperability convention:
`ensure_ascii=false` canonical JSON, pipe-appended-nonce commit preimage, derived
game_uid, and the spaced sign-then-insert consensus signature on the result artifact.
Our richer sealed-record field set (step/role/sub_game/state_digest/action/hint/
verdict) stays — the audit re-hashes the opponent's revealed records verbatim, so the
payload schema is per-team; only the combination rules must match.

NOT adopted (the book outranks the example — ADR-0001 iron rule): the reference's
subtractive/linear scent model and its per-half-turn decay. The book prints the
multiplicative formula and the Gaussian 5x5 kernel; our physics vectors pin the
book's reading, the model is negotiation-locked (`scent_model_sha256`), transmitted
on the wire, and offered to every opponent pre-series (LEAGUE_RUNBOOK step 3).

## Consequences

- Any team derived from the official reference can play us with zero adapters; the
  foreign-conformance test suite (`tests/unit/test_reference_conformance.py`) proves
  our bytes against independently generated vectors.
- This is a behavioral break with every artifact produced before 2026-07-18; the
  pre-change state is preserved at `checkpoint-pre-interop-2026-07-18` (v1.0.0-rc.1).
- The contradiction documentation duty (book front matter) is discharged here and in
  `docs/INTEROP_HASHING.md` items 1/3/3b/3c.
