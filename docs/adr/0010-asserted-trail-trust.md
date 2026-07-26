# ADR-0010 — The scent channel is unforgeable only under the replicated-engine wire

Date: 2026-07-27. Status: accepted. Scope: both repos (mirrored twins).

## Context

The rulebook treats the pheromone channel as the one observation that cannot
lie: scent is a *consequence* of movement, an agent can only strengthen the
cell it stands on, and ch. 4 builds the lie detector on exactly that ("the
scent map cannot lie"). Our belief pipeline leans on it hard, and PRD 10 leans
harder still — the dwell-plateau pin fits a shape to the trail and multiplies
one cell by `PLATEAU_ORIGIN_BOOST = 25.0`.

Reviewing that new dependency, we checked what actually guarantees the
property, and the guarantee turns out to be a property of the WIRE SHAPE
rather than of scent:

- **Bookletter wire (replicated engines).** Both peers apply both actions to
  their own `GameEngine` and compute the field from the shared physics. Nobody
  transmits a trail; it is *derived*. Unforgeable, exactly as the book says.
- **Reference wire (hidden information, ADR-0007/0008).** The field is
  TRANSMITTED. `wire/codec.py` puts `smell_grid` in the turn message as a
  plaintext sibling of `commit` — never inside the sealed payload — and
  `wire/own_state.py::OwnState.absorb` replaces our whole view with whatever
  arrived. The end-of-game audit recomputes hashes of the SEALED records, so
  a forged grid is not merely undetected, it is outside what the audit can
  see even in principle.

Measured (`scripts/measure_trail_forgery.py`, and a closed-loop probe against
a live-opponent replica): with no check, a forged trail is decisive. A decoy
plateau stamped away from the truth drove capture rate 1.000 -> 0.000 and mean
belief error to ~7 cells; a field saturating every cell did the same with no
pin firing at all. Note the second case: this exposure PRE-DATES PRD 10 —
`observe_scent` alone was already enough to be blinded. The pin did not open
the hole; it made one variant of it precise rather than merely destructive.

## Decision

1. **Hold an asserted trail to the movement model** (`peer/perception.py`,
   `domain/evidence.py::credible_cells` / `incredible_saturation`). A reading
   claiming a clamp-level deposit somewhere no emitter moving one step per turn
   could have reached is refused WHOLE for that turn — the diffused prior
   stands. Half-believing an impossible field is how a forgery steers us.
2. **Anchor on the AGREED start cell, never on a later estimate.** The one
   rival position both sides signed is public contract, not leaked truth.
3. **Ignore barriers when computing reachability.** Walls arrive during the
   game, so a barrier-aware reachability test asks "could it get there on
   today's board" when the honest answer is "it walked there before the wall
   existed". Measured: 22.5% false refusals on a late, wall-filled board.
4. **Latch the refusal.** One impossible reading is proof the channel is broken
   or hostile. Re-checking per turn is defeatable, because a refused turn
   cannot refresh the anchor and the allowed set relaxes within a few turns.
5. **Record it for the audit.** The refusal count ships in the game summary as
   `scent_readings_refused`, so the claim lands in the log a third party reads
   (rule 36) rather than living only in our console.

## Consequences

Soundness is ranked above sensitivity throughout, and that ordering is the
whole decision. The refusal latches, so a single false positive blinds the peer
for an entire game: an unsound check on this path is a self-inflicted denial of
service, strictly worse than no check. Both the barrier fix and the
start-anchor rule exist because the tighter version measured *worse* in
exactly that way (pool capture 0.983 -> 0.358 with a rolling anchor).

**What this does not buy.** A forger who respects the movement model — a decoy
that starts where the rival legitimately is and walks a step per turn — is
undetectable from the scent channel alone, and it is the most damaging attack
we measured. That is information-theoretic, not a tuning gap: such a field is
indistinguishable from a legal one. We can refuse to be *steered* by impossible
data; we cannot recover information from a channel that lies plausibly.

**Proposal, not shipped.** The structural fix belongs in the protocol: seal the
grid (or its hash) inside the commit, and forgery becomes detectable by the
same mechanism that already protects moves. We will not adopt that unilaterally
— the wire shape is a negotiated, hash-locked term and a one-sided change would
break interop with any reference-shaped peer. It is offered as an amendment for
a future pairing instead.

**Honest scope.** We have no reason to think any counterparty would forge, and
this is defensive work, not an accusation: the far likelier trigger is a buggy
or stale field from a peer under repair. The exposure was found by auditing our
own new dependency, and the mitigation is measured in both directions —
0.0 false positives on honest traffic in both repos, gross forgeries caught
every time.
