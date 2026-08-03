# Evidence — reference byte-form alignment & cross-team verification

> Status: complete (ADR-0004). Rollback point: tag
> `checkpoint-pre-interop-2026-07-18` (= release v1.0.0-rc.1).

## The problem, measured before it burned us

Our original forms (`ensure_ascii=True`, nonce nested in a wrapper object,
random uuid4 game_uid) were LEGAL under the book's documented-contradiction
clause — and byte-incompatible with the lecturer's reference implementation
in three independent ways. Verified directly against the local reference
copy (`../docs/DemoExamples`), not against anyone's claims: a cross-team
game would have failed at the handshake, and past it, every non-ASCII hint
audits as mutual TAMPERED (rule 19).

## What changed (all in one day, all gated)

| Construction | Before | After (reference form) |
|---|---|---|
| Canonical JSON | ensure_ascii=true | ensure_ascii=false |
| Commit preimage | SHA256(canonical({payload,nonce})) | SHA256(canonical(payload) + "\|" + nonce) |
| game_uid | uuid4 (random) | UUID(SHA256(canonical(terms)\|sorted group ids)[:16]) |
| Settlement signature | (none) | SHA-256, SPACED serialization, sign-then-insert |

## Proof, not assumption

- `tests/unit/test_reference_conformance.py`: 13 tests over the league
  kit's vectors (MIT, attributed in `tests/vectors/foreign/_README.md`) —
  including REJECTING the book's two divergent commit forms.
- Full cross-repo E2E games on the aligned bytes: local and fully public
  (`results/dev-history/results/public_bidirectional_e2e_*.json`), audits Verified OK both
  directions, identical derived game_uid on both peers.
- Counterparty verification BOTH directions: we independently re-verified
  the rival team's six-game demo-interop package (35/35 commits, 35/35
  scent grids byte-identical under their locked model, uid derivation
  reproduced), and they re-verified our scent trace "to the digit."

## The one deliberate divergence (disclosed)

Scent physics: the reference (and the rival team) run subtractive/linear
decay; WE run the book's printed multiplicative formula + Gaussian 5x5
kernel (the book outranks the example — ADR-0004 "NOT adopted"). This
cannot void an audit (the field is transmitted, not re-derived) but locked
models must match per pair: the mitigation is the named-scent-model
negotiation (both teams agreed book-v3 for our series; our spec became
their build plan) plus the standing runbook offer of our scent code +
golden vectors to every opponent.

## What this does NOT prove

game_uid derivation was confirmed against the rival's committed config and
group ids; against unknown third teams the handshake still depends on their
fidelity to the same reference forms — which is exactly what the
conformance suite lets any opponent check before move one.
