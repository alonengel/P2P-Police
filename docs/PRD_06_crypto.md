# PRD 06 — Commit-reveal integrity (ch. 5, rules 17-24)

## Scope & non-goals

The four-phase sealing of every half-turn, the end-of-game mutual audit,
and the byte-level canonicalization contract that makes both work across
implementations. Non-goals: transport reliability (PRD 05) and reporting
artifacts (PRD 07).

## Design / I/O contracts

- **Sealed record** (7 fields, per-team schema): step, role, sub_game,
  state_digest (pre-action anchor), action, hint, verdict (the intent
  flag). Missing-field commits are rejected at construction.
- **Byte forms = the official reference's** (ADR-0004): canonical JSON is
  sort_keys + compact separators + ensure_ascii=false; commit =
  `SHA256(canonical(payload) + "|" + nonce)`; nonce = 32 lowercase hex from
  `secrets`; game_uid derived from the agreed terms + sorted group ids;
  the settlement consensus signature uses the reference's SECOND (spaced)
  serialization, sign-then-insert.
- **Phase discipline**: commit -> transport ack locks it -> reveal (payload
  MINUS the verdict; nonce withheld) -> audit (nonces + verdicts arrays,
  every commitment recomputed with constant-time comparison). Revealing
  the verdict live would hand the rival our lie bit — learned the hard way
  and now guarded by test (rule-guard 18).
- **Verifier**: `verify-log` proves records untampered AND physics-legal —
  every action re-applied on a fresh engine from the game's OWN archived
  config; illegal moves and forged digests read TAMPERED.

## Decisions & alternatives rejected

- **Our original nested-nonce form** (`canonical({payload, nonce})`,
  ensure_ascii=true): legal under the documented-contradiction clause,
  rejected for interop — reference-derived teams produce the pipe form,
  and rule 19 makes byte-agreement existential (ADR-0004).
- **The book's replay-sketch form** (`nonce|move`): rejected — binds
  neither state nor intent; cryptographically insufficient (the league
  kit's divergent-forms diagnostic agrees).
- **prev/prev_recv transcript interlock** (our own design, adopted by the
  league kit with credit): NOT run in counted games — it modifies the
  rule-19-sensitive sealed record for a guarantee the book doesn't
  require; documented in README section 2.

## Test plan / acceptance (all met)

Unit: determinism, wrong-nonce/wrong-payload rejection, key-order
independence, malformed-audit = TAMPERED. Conformance: 13 tests over the
league kit's vectors incl. divergent-form rejection. Integration: tamper
injection voids the game; "not received" audit stays dispute evidence, not
tampering. Evidence: `docs/evidence/interop-alignment.md`, INTEROP_HASHING.md.
