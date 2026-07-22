# ADR-0008 — Hidden-wire audits replay on Board physics, not the engine

Date: 2026-07-22. Status: accepted. Scope: the reference-v3 hidden wire ONLY
(`wire/audit.py`, `report/lookup.py:recompute_hidden`); the bookletter path
keeps the engine replay byte-for-byte. Both repos (mirrored twins).

## Context

The end-of-game audit and the offline replay verifier must rebuild a game
from its revealed records and decide Verified OK / TAMPERED (rules 19-20).
For bookletter logs both peers replicated one `GameEngine`, so the verifier
re-applies every action on a fresh engine and recomputes the digest.

`GameEngine` declares ANY cop–thief co-location an instant capture
(`_check_captures_mid_round`). That is correct when both positions are
shared local knowledge. Under the hidden wire it is false: the rival's
position is structurally absent from `OwnState`, live messages carry only a
commit, and co-location is CLAIM-MEDIATED — the cop learns it landed on the
thief only through the capture-claim/answer flow (rules 21-22), and a thief
that silently crosses the cop's cell is unobservable to everyone during
play. An engine replay of an honest hidden game therefore diverges from the
game both peers actually lived (early capture verdict, then "action after
game over" errors on the mandatory concession record) and would read
**TAMPERED for honest games** — a false flag, not a stricter check.

## Decision

1. Hidden audits and hidden-log verification replay both sides' revealed
   actions directly on the domain **Board physics** (`Board.apply_move`,
   `validate_barrier_placement` — the same validators the engine uses), with
   capture recognized exactly where the wire can prove it:
   - the cop's OWN action created the co-location (landing on the thief, a
     barrier declared on the thief's cell), or left the thief surrounded;
   - the thief's own action walked into a provable pocket (onto a barrier /
     into full enclosure), which the book resolves automatically.
2. The truth duty is enforced at the audit: once capture occurred, the only
   legal further record is the thief's action-free concession (STAY). Any
   real action after game end — or records that end with the game still
   ongoing — raises and voids the log as tampering evidence.
3. Routing: hidden game logs carry `"wire_shape": "reference"`;
   `verify_log` dispatches on that marker (`report/lookup.py`). The marker
   cannot launder a log: a hidden log stripped of it falls into the engine
   replay and fails on the concession record; a bookletter log relabeled as
   hidden fails the reconstruction digest — relabeling only ever invalidates
   (guard-tested in `tests/integration/test_hidden_artifacts.py`).
4. A hidden technical-loss log has no revealed rival actions to replay (the
   rival's payloads exist only after a completed mutual audit), so only the
   commit checks apply — the same degradation a bookletter log has when its
   archived terms are missing. Completed outcomes (capture/survival) are
   always replayed and digest-checked.

## Consequences

- The audit proves exactly what the wire can prove; it never asserts
  knowledge no honest peer could have had (rules 8-9 carried into ch. 7).
- The reconstruction lives in `wire/`/`report/`, NOT `domain/` — the engine
  stays the single bookletter truth and the parity-locked physics files are
  untouched by this mode.
- A thief crossing the cop's cell mid-game without a claim being raised is
  NOT a capture under this wire — that is the book's own consequence of
  hidden information, matching the official demo protocol's claim flow.
