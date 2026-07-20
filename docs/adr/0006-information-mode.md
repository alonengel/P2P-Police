# ADR-0006 — info_mode is a NEGOTIATED term; unilateral exact play forbidden

Date: 2026-07-20. Status: accepted. Scope: both repos (mirrored twins).

## Context

Under our bookletter wire every action is revealed per step, so both
engines hold true positions; whether the BRAIN consumes them (exact) or
plays from the belief map (the Dec-POMDP posture) is a strategy-relevant
choice with competitive consequences (measured: the wire-shape balance
tables). The book's formal model (Omega_i) excludes the rival's position
from observations; consuming information the locked protocol itself
delivered to both sides symmetrically is legal ONLY as a pair-level,
signed-off resolution of the book's ch.5-vs-Omega_i self-contradiction.
An earlier draft left `[strategy] info_mode` as a private toggle - a
unilateral-advantage hole our own audit flagged.

## Decision

`info_mode` ("belief" default | "exact") is DECLARED in the negotiate
agreement and verified under the both-declare convention: the handshake
REFUSES when both peers declare and disagree; a peer that omits the field
(foreign implementations) is not a refusal. The runtime feeds the brain
exactly what the agreed mode allows; the live UI shows the belief map in
every mode (rules 8-9 govern display, unchanged).

## Consequences

- Unilateral exact-information play against a belief-mode opponent is now
  structurally impossible between conforming peers, and detectable (the
  declared mode is in both sides' negotiate records).
- The pair ADR line for a bookletter-locked series reads: "per-step reveals
  are shared local knowledge; either side may consume them for decisions -
  declared mode X, verified at handshake."
