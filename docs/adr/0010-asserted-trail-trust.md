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

1. **Hold an asserted trail to physics** (`peer/perception.py`, checks in
   `domain/trail_forensics.py`: the one-frame envelope
   `credible_cells` / `incredible_saturation`, and the consecutive-frame
   `transition_emitters` added in the addendum below). A reading
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

## Addendum (same day): the drifting decoy is NOT undetectable

The first version of this ADR closed with a claim that a forgery respecting the
movement model is "information-theoretic" undetectable from the scent channel.
**That was wrong, and it was wrong in an instructive way** — it generalized from
the check we had built rather than from what the channel actually constrains.

The envelope test asks only WHERE saturation may appear, using one frame. The
update law binds far more than that, and it binds every cell every turn:

&nbsp;&nbsp;&nbsp;&nbsp;`F_t(c) = clamp((1-rho)·F_{t-1}(c) + delta(c - e), 0, center)`

for a SINGLE emitter `e`. Two consequences the envelope threw away. A deposit is
non-negative, so **no cell may ever fall below `(1-rho)` times its own previous
value** — whatever the sender claims about where it stands. And the residual
after decay must match the kernel exactly, centred on one cell.

A drifting decoy walks its plateau one legal step per turn, which the movement
model permits — but doing so requires cells that read the clamp last frame to
read zero this frame. The law forbids it outright. **A forgery can move its
position; it cannot move its history.**

Measured (`transition_emitters`, both repos):

| | before | after |
|---|---|---|
| drifting decoy detected | 0.000 | **1.000** |
| false positives, honest traffic | 0.000 | **0.000** |
| refusals over 300 games vs a FOREIGN implementation | 0 | **0** |

The cross-implementation result is the one that matters: 396 honest frames
produced by the opponent's own scent code matched our predicted transition
bit-exactly (0 misses at tolerance 1e-9), and detection was unchanged from 1e-9
to 1e-2. The shipped tolerance is 1e-3 — four orders of margin for a peer that
rounds its field into JSON, at no measured cost.

Two guards were kept rather than one: the envelope still covers the FIRST frame,
where there is no predecessor to compare against. And the latch now needs **two
consecutive** unexplained frames, because the law was validated against a single
foreign implementation and the refusal is irreversible — a sustained forgery
breaks it every frame, while an unforeseen quirk gets one free pass.

**A third false positive, found the same way as the first two.** The candidate
scan originally skipped cells holding a barrier — "nobody emits from inside a
wall". The law of barriers lets the cop wall its OWN cell, and it still emits
from there that turn, so the filter discarded the true emitter and refused
honest frames in 50% of games on the twin's side. Every tightening on this path
has needed measurement to prove it sound; none has been safe by inspection.

**What remains open.** A forger willing to simulate a full legal trail — running
the real physics for a fictional trajectory — still produces frames that satisfy
the law, because such frames ARE legal frames for a different game. Detecting
that needs the grid bound to the sealed record, which is the protocol proposal
below, not a check we can add on our side.

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


## Addendum: the pairing round (2026-07-28)

The counterparty reproduced every claim before answering (their house rule) and
returned two things worth recording.

**The leak is not a property of the book model.** They re-ran the §4.1 scan
under `subtractive_chebyshev_v1` — max-merge deposit, ring falloff, round-3
quantization — and got 224/224 frame pairs inverting to exactly one candidate,
same as under `multiplicative_book_v1`. So the finding generalizes: *any*
full-field transmission under deterministic public physics names its emitter,
and rounding to three decimals does not blur it. Whichever model a series
locks, if the grid crosses the wire the inversion rides along.

**A coherence defect in the registry document, not in either implementation.**
Our `config/scent_model_lock.json` — adopted verbatim from the league registry
so our `scent_model_sha256` equals the pinned `934c220d…` — contains
`"transmitted": false`. On the reference wire that is simply untrue:
`smell_grid` is a member of the closed turn-message key set, so a grid crosses
on every half-turn by construction. We cannot correct it unilaterally, because
the value is inside the hashed document and any edit changes the hash and
breaks the lock against every peer using the registry's. Recorded here as a
joint item to raise at registry level rather than patched locally.

**Which stack produced our validated frames** (their precision question, and a
fair one — it decides the compare mode). Ours came from an implementation of
`multiplicative_book_v1` with `rounding_decimals: null`, i.e. the unrounded
book law — *not* round-3 subtractive frames: 396 honest frame pairs, 0
unexplained at tolerance 1e-9. We ship 1e-3 regardless, which is four orders of
margin, so a last-bit divergence or a peer that rounds into JSON cannot reach
the decision either way.

### Counted-series posture (agreed, pending their confirmation)

The series locks `info_mode: belief`, defined as: the transmitted field reaches
decisions ONLY through the probabilistic belief layer; neither side runs
deterministic transition-inversion to pin the current cell; both step-0
declarations say so. `shared/info_modes.py` carries that definition on the
`belief` row so the constraint lives with the code rather than only in prose.

Two honest notes on it. The belief layer legitimately *reads* the field — that
is the designed observation channel, and under the reference form it already
makes a pursuer near-exact; what belief-mode forswears is the oracle, not the
mechanic. And the merits argument runs the same way for both of us: exactness
upgrades the evader more than the pursuer, so "both may, declared" tilts a
series toward six survivals and structural near-ties — a worse game and a worse
pair of reports.

### Scope of the sealing amendment

Binding `smell_grid` (or its hash) into the commit preimage buys
**authenticity**, not privacy: a stale, malformed or forged field becomes
audit-grade evidence instead of a console-only observation. An honest,
correctly bound field inverts exactly as before — §2 is untouched by it.
Privacy would require changing the physics or the wire (noise, lag, or not
transmitting), all of which are deviations from locked terms, which is why
posture is the only lever on that side of the line.

Timing constraint, theirs and correct: the amendment changes the commit
preimage, so it plays in a counted series only after a warm-up drill proves it
on both sides. A preimage change in the week of a counted game is how rule 35
takes both scores with nobody cheating.
