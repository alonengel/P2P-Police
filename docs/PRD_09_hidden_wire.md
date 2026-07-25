# PRD 09 — The hidden-information wire: reference-v3 client behind the wire_shape lock

## Description & theory

The bookletter wire reveals every action per step, so both replicated
engines hold true positions and the Dec-POMDP posture (the book's Ωᵢ
excludes the rival's position from observations) is a *strategy* choice —
the negotiated `info_mode` (ADR-0006). The book's ch. 5 simultaneous
commit-ack-reveal picture and Ωᵢ cannot both be literal at once; ADR-0007
records our resolution and its addendum registers the consequence: rule
11's lock has TWO registered realizations, one per wire shape. `wire/`
implements the second — the **reference-v3 hidden mode**, in which rules
8-9 become *structural*: live messages carry a commit, never a move;
`wire/own_state.py:OwnState` holds a single-key `positions` dict, so any
code that asks for the rival's cell fails loudly instead of silently
peeking; belief (Perception) is the only rival estimate; capture is
claim-mediated. The shape is itself a locked model: the pair registry
entry `config/wire_shape_lock.json` (family/name/params/example) is
declared as `wire_shape_sha256` beside the agreement under the
both-declare refusal rule (`wire/lock.py`) — omission never refuses, so an
unmodified reference peer stays playable, and an undeclared game is
byte-identical to the pre-PRD-09 bookletter default. Goals: (1)
interoperate with reference-shaped rivals first try; (2) make the
hidden-information reading enforceable by shape rather than discipline;
(3) never fork the hardened machinery — `HiddenExchange` subclasses the
`SealedExchange` receiver (dedup, reorder buffer, flood cap, one deadline
per expectation), and Deadline/watchdog/Deceiver/talk-chain are reused
as-is (`wire/hidden_runtime.py`, assembled by `sdk/hidden.py`).

## I/O contracts

- **Negotiate** (`wire/terms.py`): the reference's literal flat form —
  `terms` (14 keys DERIVED from the signed game.json, never duplicated;
  `max_steps` maps from `survival_threshold`, and a config whose
  `max_moves` diverges from it is unrepresentable → refuse) + `nonce` +
  `signature = SHA256(canonical(terms) + "|" + nonce)` — the league kit's
  terms_signature CORE vector, same preimage form as a step commit.
  Riding alongside, OUTSIDE the signature: `group_id` + the identity
  block, `scent_model_sha256`, `info_mode` (structurally `"belief"` on
  this wire), `hardware_spec_sha256`, `wire_shape_sha256`, and the agreed
  mutual pairing keys `sub_game_number` and `role` (both top-level,
  unsigned). Verification: key-by-key VALUE equality with a per-key
  diagnostic naming every differing value, plus signature recompute.
  Refusal semantics are typed: locked-model mismatches are plain-fatal;
  wrong `sub_game_number` or an EQUAL `role` classify as
  `PairingRefusalError` — a bystander ("wrong game, not you"), logged and
  tolerated while the one overall deadline still judges. The agreement is
  re-pushed unchanged (same nonce, dedup-safe) every
  `agreement_repush_sec` until a VERIFIED counterpart arrives
  (`wire/repush.py`).
- **TurnMessage** (`wire/codec.py`): a CLOSED ten-key codec — required
  `step` / `sender` / `hint` / `smell_grid` / `commit` / `timestamp`,
  optional `barrier_placed` / `capture_claim` / `claim_response` /
  `win_claim`. An unknown key is rejected outright, so a position can
  never ride along — the structural hidden-information guarantee. The
  scent field travels sparse (`{"r,c": intensity}`, zero cells off the
  wire), sender-computed under the locked model and absorbed as-is.
- **Audit envelope** (`wire/audit.py:build_audit_payload`): EXACTLY the
  reference `AuditPayload` — `{sender, records, result_claim}`, nothing
  else. The reference parser is a strict dataclass: a missing `sender` is
  refused outright (live 2026-07-24 cross-team finding — our envelope
  without it voided an otherwise clean 35-turn game on the counterparty's
  side), and any extra key of ours would reject the whole audit.

## Cadence, claims and reconstruction

- **Per-sender cadence** (`wire/hidden_turns.py`): the THIEF opens every
  round, and each side numbers its OWN steps 1, 2, 3… independently. The
  thief's step ticks the round clock — survival counts the thief's own
  steps — and the book-model scent update runs on the sender's field
  BEFORE serializing. A `caught=True` closure may re-use the sender's
  last step number (demo send_final behavior), so it is keyed to the live
  expectation instead of its embedded number; an echo of our own role is
  transport noise, dropped and logged, never protocol content.
- **Claim-mediated capture** (`wire/claims.py`, rules 21-22 made
  structural): after a move the cop claims its landing cell; the thief's
  answer is a PURE function of its own state and the claimed cell — no
  strategy object, config flag or RNG appears in any signature, so the
  truthful path is the only path. The automatic families (barrier on my
  cell, fully surrounded) self-concede without any claim; a barrier
  placement claims nothing (it forgoes the move; barrier captures resolve
  on the thief's side). Once captured, the only legal further record is
  the sealed action-free STAY concession.
- **Audit reconstruction tiers** (`wire/hidden_turns.py:finish`,
  `wire/audit_foreign.py`, ADR-0008): **(a)** the commit criterion —
  schema-agnostic re-hash of every reveal, alignment BY COMMIT: every
  commit received live must be re-proven by a commit-clean reveal (a
  reference reveal set also carries a step-0 system-spec record whose
  commit never crossed the live wire — it anchors nothing, can rewrite
  nothing, and is tolerated); **(b)** the strict reconstruction — both
  sides' revealed actions replayed on the domain **Board physics** (the
  same validators the engine uses), capture recognized exactly where the
  wire can prove it and the truth duty enforced (a real action after game
  end, or records ending mid-game, void the log as tampering evidence) —
  but ONLY when the rival's payloads parse as OUR schema; a commit-clean
  foreign half is judged on the derivable checks alone (per-sender step
  continuity, revealed-position movement legality), never called TAMPERED
  for its schema; **(c)** the digest comparison — defined only where one
  construction exists on both sides; foreign pairs report `digest_match`
  as `null` (not-comparable), never false. Offline, `verify-log`
  dispatches on the log's `"wire_shape": "reference"` marker
  (`report/lookup.py:recompute_hidden`); relabeling a log in either
  direction only ever invalidates it.
- **Crash-resume** (`wire/hidden_resume.py`, E6 under secrecy): the
  snapshot persists exactly what this peer truly holds (own cell, public
  barrier record, boundary-cell scent history, per-sender clocks, sealed
  records — own nonces never crossed the wire pre-audit, so a LOCAL file
  may hold them); a rival's `resume_offer` is answered by re-sending the
  last TurnMessage, which carries the COMMIT alone — a crash can never
  become a pre-audit reveal (rule 18 survives E6).

## Settlement rules

A series result exists only for a settled series (`sdk/series.py`,
`report/series_doc.py`, rule 35): every sub-game 1..num_games needs a
settled, audit-clean log; logs must agree on one consensus `game_uid` AND
declare the series' `num_games`; everything excluded is excluded BY NAME,
never silently; a refused series emits nothing and emails nothing. The
result document is the reference-conformant shape (groups, per-sub-game
roles/scores/commits/tokens, sign-then-insert consensus signature —
ADR-0004/0009). Mutually discarded evidence relocates to
`docs/evidence/discarded-series/` — committed history that is structurally
out of the aggregation glob — and counted series take a fresh unique game
id, making stale same-id collisions impossible.

## Performance characteristics

- ONE message per half-turn versus the bookletter's commit+reveal pair;
  the sparse scent serialization keeps zero cells off the wire.
- Live: full 35-turn cross-team games completed inside the league turn
  budgets over the public tunnels (2026-07-24, both directions); the
  hidden kill-and-resume drill restores in 0.062 s
  (`docs/evidence/drills/hidden_resume_recovery_2026-07-22.jsonl`).
- The information regime is strategy-relevant and measured: the
  wire-shape balance tables (`results/experiments/wire_shape_balance.json`)
  quantify how one move of staleness (this wire's best case for reading a
  rival) swings each brain pairing — the evidence behind locking
  `info_mode` and `wire_shape` as negotiated terms instead of private
  toggles (ADR-0006).

## Alternatives considered & rejected

- **config_sha256 handshake on this wire** — rejected: a reference peer
  verifies exactly `{terms, nonce, signature}` and would not recognize
  the bookletter's config-hash substitution; rule 11's substance
  (identical agreed values, cryptographically locked) has two REGISTERED
  realizations, and each shape must speak its own (ADR-0007 addendum).
  The flat terms stay DERIVED from the signed game.json — never a second
  source of truth.
- **Reveal-alignment by list position (zip + length)** — rejected: the
  reference's step-0 spec record makes strict zip permanently misaligned,
  flagging honest rivals. Alignment BY COMMIT judges exactly what the
  live wire anchored (live 2026-07-24 finding; `wire/audit_foreign.py`).
- **Engine replay for hidden audits** — rejected: `GameEngine` declares
  ANY co-location an instant capture, which is false under this wire
  (co-location is claim-mediated and a silent crossing is unobservable);
  an engine replay reads honest hidden games as TAMPERED — a false flag,
  not a stricter check (ADR-0008). Board-physics reconstruction proves
  exactly what the wire can prove.
- **A shared end-digest construction with foreign peers** — rejected: the
  interop contract is canonical JSON + `SHA256(canonical(payload)|nonce)`
  and nothing more; payload schema and digest construction are per-team
  choices, so `digest_match` reports not-comparable (`null`) instead of
  manufacturing a false verdict.
- **Forking the receiver for the new mode** — rejected: `HiddenExchange`
  subclasses the hardened `SealedExchange` receiver (dedup / reorder /
  flood cap / deadline discipline) — reused, not duplicated.

## Success criteria (all met, tested)

- Handshake pinned byte-for-byte: exact key set + signature construction
  against the kit CORE vector (`tests/unit/test_wire/test_terms.py`,
  `test_terms_verify.py`, `test_reference_message_fixture.py`); pairing
  guards incl. the bystander/fatal split (`test_terms_pairing.py`,
  `tests/integration/test_hidden_repush.py`,
  `test_hidden_negotiate.py`); the wire-shape lock (`test_lock.py`).
- Structural hiding: closed codec key set + malformed-message rejection
  (`test_codec.py`); `OwnState` carries no rival key (`test_own_state.py`);
  the truth duty is a pure function (`test_claims_truth.py`); cadence and
  role handling (`test_hidden_turns_roles.py`,
  `tests/integration/test_hidden_cross_cadence.py`); capture flows
  end-to-end (`tests/integration/test_hidden_capture.py`).
- Audit fairness + anti-laundering: the three tiers incl. foreign-schema
  halves and the relabeling guards (`test_audit_finish.py`,
  `test_audit_foreign.py`, `tests/integration/test_hidden_artifacts.py`).
- End-to-end: full hidden games over real MCP
  (`tests/integration/test_hidden_game.py`, `test_hidden_sdk_e2e.py`);
  the crash-resume drill (`test_hidden_resume_drill.py` + the committed
  JSONL evidence).
- Live evidence: the committed twin pair of hidden game g03 pair-verifies
  `Verified OK` (`scripts/verify_pair.py`); the cross-team logs under
  `docs/evidence/discarded-series/` verify `Verified OK` per side via
  `verify-log`; the 47-47 six-sub-game rehearsal result and the
  Verified-OK replay witness (`assets/replay_hidden_verified.png`) are in
  README Part II §2/§4.
