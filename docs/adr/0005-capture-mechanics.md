# ADR-0005 — All three capture families resolve automatically (no claim flow)

Date: 2026-07-20. Status: accepted. Scope: both repos (mirrored twins).

## Context

The book (ch. 3 + D.1) distinguishes landing-capture — which carries a
Capture Claim and a truth-duty on the thief's answer (rules 21-22) — from
the automatic captures (barrier-on-thief, fully-blocked thief). Early
comments in `domain/rules.py` and PRD-01 promised a "cryptographic Capture
Claim (Phase 6)" message; it was never built, and the stale references
contradicted the code.

## Decision

No claim/response exchange exists, deliberately. In our wire every
half-turn is commit-revealed and both replicated engines apply both
actions: the thief's position at claim time is ALREADY cryptographically
committed and end-of-game audited. A claim message would ask the thief to
attest to a fact the protocol has sealed — it can add nothing the audit
does not prove, and a false denial is impossible without a hash mismatch
(which rule 19 already voids). The claim-time truth duty (rule 21) and the
false-claim prohibition (rule 22) are therefore SUBSUMED: no party can
claim or deny anything inconsistent with its own sealed records. All three
capture families resolve in `domain/engine.py` identically and are covered
by the same audit.

## Consequences

- The stale "Phase 6" comments were removed from `rules.py` and PRD-01.
- In a hidden-wire (reference-shape) pairing, where positions are NOT
  revealed per step, a claim flow would be meaningful again — that wire is
  not implemented here (issue-#6 registration: bookletter-v3), and any
  future hidden-wire build must revisit this ADR.
