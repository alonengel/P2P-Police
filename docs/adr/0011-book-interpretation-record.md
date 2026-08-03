# ADR-0011 — Book-interpretation record (defended readings, pre-league)

Status: accepted · Date: 2026-07-29 · Both repos (parity: identical text)

The 2026-07-29 full-rulebook audit (Appendix ה 1–55 + Appendix ו against the
code, five independent verification passes) confirmed no violation, but named
five places where the book admits two readings and our code commits to one.
This ADR is the written defense for each — the reading, why it is correct,
and where the code implements it. (Interpretations only; the enforcement
gaps that same audit found are fixed in code, not argued here.)

## 1. Private email throttle below the Table-19 "minimum" row

`config/rate_limits.json` caps OUR OWN Gmail service harder (5 rpm / 1
concurrent / 10 s retry) than Table 19's 30/2/5 floor. The Table-19 statuses
bind the NEGOTIATED gatekeeper block — which meets the floor exactly
(`config/game.json` `rate_limiter_gatekeeper`, locked by `config_sha256`).
Rules 28–29 exist to prevent hammering Google into a 429/account block;
throttling ourselves harder serves that purpose and takes nothing from the
rival (the peer wire is not rate-limited by this service entry). Purposive
reading adopted; the shared block is the compliance surface.

## 2. Rule 11 "byte-identical" = canonical-JSON identity (ADR-0004)

Config identity is enforced as SHA-256 over canonical JSON, not raw file
bytes (`domain/negotiation.py::config_sha256`). Two peers on different OSes
/ formatters provably hold the SAME agreement while differing in whitespace;
hashing raw bytes would refuse honest peers over formatting. The reference
kit does the same (ADR-0004 alignment). The book's intent — neither side can
play under different terms — is exactly what the canonical hash locks.

## 3. "35 moves" = 35 FULL turns (cop+thief each act 35 times)

Appendix ו's step cap and survival threshold are counted in full rounds:
`engine.py` ticks `turns_completed` once per completed round, and the hidden
wire counts the thief's own steps (reference cadence, `wire/audit.py`). The
official demo and the reference kit both count this way; the survival prize
is meaningful only if the thief actually survived N of ITS OWN exposures.
Both peers lock the same `max_moves`/`survival_threshold` in the signed
config, so no cross-team ambiguity can arise mid-game.

## 4. Same-cell capture direction differs per wire — deliberately

The replicated-engine wire calls ANY co-location capture (`engine.py`; the
book p. 22 defines capture by the cop's landing, and under replicated truth
a thief stepping onto the cop is self-evident and indefensible). The hidden
wire's audit reconstruction credits a capture only to the cop's OWN action
(`wire/audit.py` header; ADR-0005/0008): under hidden information a
co-location the cop never claimed is unobservable live, so the replay proves
only what the wire could prove. Each wire is internally consistent, both
peers of a game always run the SAME wire, and the audit tier matches the
wire it audits. Not a drift — an epistemic property of each wire shape.

## 5. league-day sibling-results polling is not the ch. 2.4.2 crime

`scripts/league_series.py` / `league_close.py` poll the twin repo's
`results/` for the EXISTENCE (name + mtime) of a SETTLED sub-game's log, and
aggregate only after the series closed. This is the orchestration script,
not either peer process (peers receive only `--sub-game/--seed/--counted`);
what is read is a finished game's artifact that the rule-36 mutual audit
reveals to the opponent anyway. The boxed prohibition (book p. 15, ch.
2.4.2) names shared memory, shared live-state modules and shared variables
between the two AGENTS — none of which occurs. The live game channel remains
MCP-only.

## Consequences

- These readings ship as the submitted record; a grader or rival pressing
  any of the five points gets pointed here, not at memory.
- The plateau-localization posture stays defended by ADR-0010 (unchanged).
- If the course staff ever rules against one of these readings, the affected
  value/behavior is config-driven or single-module in every case above; an
  ADR supersession + paired commit adapts it without touching physics.

## Addendum (2026-08-03, imreeyal repo review #1): the unclaimed-landing capture

Their review found a case section 4 above did not cover, verified by repro
before fixing: the cop can LAND on the thief's true cell while its belief
gate (claim threshold 0.10) keeps it from claiming - under the hidden wire
neither peer can know, the game legitimately plays on, but the strict audit
reconstruction fired CAPTURE on the co-location and then read the next
honest action as "a real action after game end" -> TAMPERED -> rule 19 ->
rule 35: an honest game self-destructing to 0/0 for both teams.

Resolution (wire/audit.py reconstruct): a LANDING capture is now
PROVISIONAL, matching the live game's claim-mediated semantics - if the
thief's sealed closure follows, the capture stands exactly as before; if a
real action follows instead, the landing was evidently never claimed or
conceded, so the replay downgrades it to `disputed_capture` evidence
(mirroring the foreign tier) and continues to the outcome the peers lived.
LAW captures (barrier-on-thief / fully surrounded) stay strict: the thief
self-detects those and playing past them remains tampering evidence.
Regression tests: tests/unit/test_wire/test_audit_disputed.py.
