# Evidence — disqualification-class rules, enforced and drilled

> Status: complete; all guards run in CI on every push.

## Enforced as invariants (tests/unit/test_rule_guards.py)

| Rule | Guard |
|---|---|
| 25 (moves never LLM-decided) | AST scan: no LLM path importable from any move-decision module |
| 30 (send-only Gmail) | the ONLY `auth/gmail.*` scope string in the codebase is `gmail.send` |
| 18 (nonce secrecy) + deception | a real sealed exchange is built; the commit message carries exactly {kind,turn,actor,commit}; the reveal carries neither nonce nor intent verdict |
| 27 (free language) | hundreds of generated hints, zero coordinate-shaped tokens |
| 11-12 (constitution legality) | the committed game.json passes the Appendix-VI fixed/minimum gate |

## Drilled behaviors (unit + integration suites)

- **Rule 19 (any mismatch voids)**: tamper-injection tests flip one byte of
  a sealed record -> replay and verify-log read TAMPERED; a TAMPERED audit
  voids the outcome to technical loss in the report path.
- **Physics-legality**: `verify-log` re-simulates every logged action on a
  fresh engine from the game's OWN archived config; an illegal logged move
  or a forged end-digest reads TAMPERED (tested against the real committed
  E2E log and a forged copy).
- **Rules 4-7 (state machine, deadlines, watchdog)**: illegal FSM
  transitions raise; every wait is deadline-bounded and routes to
  TECHNICAL_LOSS instead of deadlock; the watchdog persists a timestamped
  dump under logs/ and shuts down cleanly (silent-opponent integration
  test).
- **Rules 32/35 (always report)**: the catch-all funnel emits all four
  artifacts + (in send mode) the email on EVERY game end including
  technical losses — exercised by the technical-loss E2E flow.

## What this does NOT prove

Guards freeze OUR compliance; they cannot police an opponent. The mutual
audit + the physics-recomputing verifier are the instruments that face
outward.
