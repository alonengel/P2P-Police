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


## Addendum (2026-07-27): the regimes are a registry, and legality is checked

`info_mode` was a bare string compared with `== "exact"`. Two silent failures
lived in that:

- **A typo degraded silently.** `info_mode = "exakt"` is not `"exact"`, so the
  peer played belief while its config said otherwise. On the reference wire it
  was never even declared, so nothing surfaced the disagreement.
- **An impossible regime was ignored rather than refused.** Asking for `exact`
  on the reference wire cannot be honoured - `OwnState` holds a single-key
  positions dict, so there is no rival cell to read - and the runtime simply
  carried on in belief mode without saying so.

Both are now startup errors. `shared/info_modes.py` holds one table:

| regime | information source | wires that can serve it | peer agreement |
|---|---|---|---|
| `belief` (default) | scent/hint posterior | bookletter, reference | no |
| `exact` | replicated-engine truth | bookletter only | yes (both-declare) |

`resolve(name, wire_shape)` raises `InfoModeError` (surfaced as `ConfigError`)
for an unknown regime or one this wire cannot serve, and both runtimes resolve
ONCE at construction - a peer that believes it agreed to one regime and plays
another is the failure this seam exists to make impossible. `brain_view(mode,
perception)` is the single extension point: `exact` hands the brain nothing so
it reads the engine, every posterior regime hands it a view.

**Adding a regime is a row and a branch.** That was the point of the
refactor: a third regime (`derived`, ADR-0010) is designed and deliberately
NOT built, and the registry carries a comment saying so rather than leaving
the option undiscoverable. Nothing about the default posture changed - belief
mode plays exactly as before, verified by the full suites, the campaign
measurements and a live two-peer game.
