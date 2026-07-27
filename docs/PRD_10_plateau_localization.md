# PRD 10 — Dwell-plateau localization: inverting the clamp to find a stationary rival

## Description & theory

The scent channel is the rulebook's only unforgeable observation (ch. 4): an
agent emits on every turn and can strengthen a cell only by *standing on it*.
PRD 04 established the first decode — a reading is a **clock**, every value
being some kernel deposit `K_d` decayed by `(1-rho)` per full turn, so it
inverts to a *reach* radius `d + age` (`domain/evidence.py::decoded_reach`).

That decode has one blind spot, and it is exactly the blind spot a patient
opponent lives in. The book's update rule is

&nbsp;&nbsp;&nbsp;&nbsp;`tau'(c) = clamp((1 - rho) * tau(c) + delta(c), 0, center_intensity)`

Under **re-emission** — the same emitter depositing on the same cell turn
after turn — each cell converges to the fixed point `delta / rho`. With the
book's fixed `rho = 0.10` and `center_intensity = 0.9`, a kernel offset
therefore reaches the clamp exactly when

&nbsp;&nbsp;&nbsp;&nbsp;`delta >= rho * center_intensity = 0.09`

Of the 5×5 kernel's 25 offsets, **21 clear that bar and 4 do not** — the far
corners (`delta = 0.04`, fixed point 0.4). So a rival that dwells does not
merely leave a hot cell: it stamps *its own kernel window*, minus those four
corners, onto the board at maximum intensity, clipped by the board edges.

`decoded_reach` cannot read this. Every saturated cell decodes to reach 0, so
the scent likelihood is **flat across the entire plateau** and the posterior
peak settles wherever diffusion happens to favour — measured at 7% exact and
2.42 cells of error over 1,292 blind turns. The information is present in the
data and invisible to a per-cell decode, because it lives in the *shape*.

**The second decode inverts the shape.** For each candidate cell we construct
the saturating window it *would* stamp, clipped to the board and excluding
barriers, and score the fit against the observed plateau by Jaccard overlap.
The best-fitting cell is the emitter. Board clipping makes the fit **sharper,
not weaker**: a corner dweller's plateau is a distinctive 8-cell quarter that
only one cell can produce, so edges and corners — where a cornered rival most
wants to hide — are where localization is most certain.

The symmetry is worth stating plainly, because it governs both repos:
**camping is self-reporting.** This is why the thief's `[strategy.doctrine]`
`stay_cap` is kept enabled even though its own keep-gate measures neutral —
our own decode is the proof that the behaviour it forbids is exploitable.

## I/O contracts

`domain/evidence.py` (parity-locked, byte-identical in both repos):

| symbol | input | output |
|---|---|---|
| `SATURATING_OFFSETS` | *(derived at import from `EMISSION_KERNEL`)* | the 21 offsets whose fixed point reaches the clamp — never hand-written |
| `saturated_cells(scent, board, grid)` | a scent reading + board | set of passable cells reading reach 0 |
| `plateau_origin(scent, board, grid)` | same | the fitted emitter `Cell`, or `None` |

`domain/belief.py::BeliefMap.observe_plateau(scent, board)` applies the pin as
a **multiplicative boost** (`PLATEAU_ORIGIN_BOOST = 25.0`, the same evidence
grade as a declared barrier origin) followed by renormalization — never a
collapse to certainty, so a wrong pin stays recoverable by the next turn's
evidence.

`peer/perception.py::Perception.observe` calls it **last**, after both hint
tiers, and the ordering is a deliberate epistemic claim: a saturated plateau
is physics the rival emitted *about itself*, so it must outrank anything the
rival *chose to say*. Local truth only — the pin is computed from the
transmitted trail and never touches a position.

**Abstention is part of the contract.** Three gates (`PLATEAU_MIN_CELLS = 4`,
`PLATEAU_MIN_FIT = 0.9`, `PLATEAU_MARGIN = 0.05`) mean the function declines
to answer unless the shape is both a good fit *and* clearly better than the
runner-up. A pin is consumed as near-certainty, so a confident wrong pin is
far more dangerous than silence.

## Performance characteristics

Cost is `O(|plateau| × 21)` set operations per observation — bounded by the
board, negligible against the 180 s turn deadline; no measurable change in
live turn latency.

Localization, 1,292 blind turns against a live opponent with per-turn ground
truth:

| estimator | fires on | exact | mean error |
|---|---|---|---|
| posterior argmax (PRD 04 pipeline) | every turn | 7% | 2.42 cells |
| `plateau_origin` @ fit ≥ 0.9 | 43% of turns | **89%** | **0.11 cells** |
| `plateau_origin` @ fit ≥ 0.7 | 57% of turns | 82% | 0.23 cells |

Downstream effect on play (150-game closed loop, then the 4-evader arena):

| | before | after |
|---|---|---|
| barriers placed per game | 0.00 | 2.0–3.4 |
| capture rate vs a live opponent | 0.147 | **1.000** |
| capture rate over the whole evader pool | 0.625 | **0.983** |

The pin also **re-opened two keep-gates that had honestly failed**: the exact
endgame solver (0 fires in 160 games → 230, capture 0.625 → 0.850) and the
thief's survival certificate (0 in 180 games → 120). Both had failed *because
of the belief*, not because of the solver — recorded in
`docs/evidence/cop-strength.md` and `docs/evidence/thief-certificate.md`.

## Alternatives considered & rejected

1. **Centroid of the saturated set.** Fails precisely where it matters: board
   clipping pulls the centroid inward, so a corner dweller — the common case —
   is systematically mislocated.
2. **Directional (asymmetric) fit score** `|S ∩ K| − |S \ K|`. Rejected after
   measurement: it never fires. A large window trivially covers a small
   plateau, so every wide hypothesis ties with the true one and the margin
   gate never opens. Jaccard is symmetric, which is the whole point — an
   unfilled window refutes a hypothesis just as an unexplained cell does.
3. **Exact shape match.** Correct but far too slow: a corner plateau needs 12
   dwelt turns to saturate completely, and a rival that camps 10 turns and
   leaves would never be caught. The graded fit reads the plateau while it is
   still forming.
4. **Requiring a "camper" classification first.** Unnecessary — the fit is not
   a camp detector but a general saturation-shape inverter, and it correctly
   pins a slow walker's current cell too. Adding a classifier would have
   discarded true positives to answer a question nobody asked.
5. **Area-denial herding on top of the sharpened belief** (spending barriers on
   the placement that maximally cuts the believed reachable region). Built and
   measured: outcomes **byte-identical** to the shipped brain over 60 games —
   it never fires, because a region small enough to be worth cutting is one the
   existing trap gate walls a turn later. Honest negative; not shipped.

## Success criteria (all met, tested)

- Pins a corner dweller the posterior argmax cannot find —
  `test_plateau_origin_pins_a_camper_the_argmax_cannot_find`.
- **Abstains** on silence, on a lone fresh spike and on a straight open march —
  `test_plateau_origin_stays_silent_when_the_shape_is_ambiguous`.
- Never pins a barrier and is unharmed by walls in the window —
  `test_plateau_origin_ignores_walls_and_never_pins_one`.
- The whole decode is pinned by golden vectors byte-identical in both repos
  (`tests/vectors/physics_vectors.json` → `evidence`), *including the three
  refusals* — parity hashing catches drift between the twins, but only vectors
  catch a change made identically in both, and a silent loss of abstention is
  the dangerous regression —
  `test_decode_matches_the_twin_repo_golden_vectors`.
- Verified live over the reference (hidden-information) wire: full game, both
  sides `Verified OK` with matching end-state digests, capture on turn 15 with
  three barriers spent — the behaviour the offline campaigns predicted.

## Trust boundary (added 2026-07-27, ADR-0010)

This mechanism consumes the rival's TRANSMITTED field and boosts one cell 25x,
so the dependency was audited. On the reference wire `smell_grid` is a
plaintext sibling of `commit`, never sealed, and the end-of-game audit
recomputes hashes of SEALED records - a forged grid is outside what the audit
can see. The rulebook's "scent cannot lie" holds under the replicated-engine
wire, where the field is derived rather than asserted.

`Perception` therefore holds an asserted trail to physics, in two tiers
(`domain/trail_forensics.py`). `incredible_saturation` bounds WHERE a deposit
may appear given the movement model - all a single frame can support, and what
covers the first frame. `transition_emitters` uses the much tighter constraint
between CONSECUTIVE frames: the update law is arithmetic, so no cell may fall
below `(1-rho)` times its own previous value and the residual must match the
kernel centred on one cell. A forgery can move its position; it cannot move its
history.

Measured in both repos: **0.000 false positives** on honest traffic, **1.000
detection** on every forged arm including the drifting decoy that the envelope
alone could not touch, and **0 refusals over 300 games** against a foreign
implementation whose honest frames matched our predicted transition bit-exactly.
Full reasoning, the corrected claim, and the protocol-level proposal (seal the
grid inside the commit) are in ADR-0010.

- Sensitivity analysis and figures for this mechanism: `notebooks/analysis.ipynb`
  sections 5-6, regenerated from `scripts/measure_localization.py` and
  `scripts/measure_trail_forgery.py` into `results/experiments/` and rendered by
  `scripts/render_pin_figures.py`.
