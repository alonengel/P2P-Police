"""Floored-residue tolerance for the scent law gate (najamjad 2026-08-22).

Some emitters zero sub-epsilon residues at serialization (najamjad's
floor sits at ~0.005: smallest value ever transmitted 0.005341, and all
four refused frames of the 17:50 six were single remote cells crossing
it). The update law forbids any cell falling below (1-rho) times its
previous value, so such frames are honest motion wearing a serialization
bug — refusing them is correct evidence, but a LATCH HAZARD: trail cells
laid on adjacent turns cross the floor on adjacent turns, and three
consecutive breaks latch scent trust off for the whole game. Blinding
ourselves against an honest-but-sloppy emitter loses games to noise.

The tolerance: when the raw transition admits no emitter, re-solve with
every floored cell (previous > 0, current == 0, lawful next value at or
under epsilon) restored to its lawful decay. Solvable after restoration
means the frame tracks — accepted, with the floored cells returned as
EVIDENCE (surfaced beside refusals, never silently). A zeroed cell whose
lawful value exceeds epsilon is real physics violation and still refuses:
at 0.005 intensity a forger hides ten-turn-old history, nothing else, so
the tolerance launders noise and only noise.
"""

from p2p_police.domain.trail_forensics import transition_emitters
from p2p_police.peer import foreign_scent

DECAY_KEEP = 0.9  # (1 - rho): the signed retention factor per turn


def solve_with_tolerance(previous: list, current: list, board, grid_size: int,
                         epsilon: float) -> tuple[list, list]:
    """(emitters, floored_cells) for one frame transition.

    Raw-solvable frames pass through untouched (floored_cells empty).
    Otherwise floored cells are restored to lawful decay and the law is
    asked again; still-unsolvable transitions return ([], [])."""
    emitters = transition_emitters(previous, current, board, grid_size)
    if emitters:
        return emitters, []
    floored = [
        (r, c)
        for r in range(grid_size) for c in range(grid_size)
        if previous[r][c] > 0.0 and current[r][c] == 0.0
        and 0.0 < DECAY_KEEP * previous[r][c] <= epsilon
    ]
    if not floored:
        return [], []
    patched = [row[:] for row in current]
    for r, c in floored:
        patched[r][c] = DECAY_KEEP * previous[r][c]
    emitters = transition_emitters(previous, patched, board, grid_size)
    return (emitters, floored) if emitters else ([], [])


def law_verdict(percep, rival_scent, board) -> bool:
    """Do two consecutive frames admit NO single emitter (ADR-0010)?

    The check that closes the gap the reachability envelope leaves: a
    forgery can walk its decoy one legal step per turn, but the update
    law binds the whole board — a cell may never fall below (1-rho)
    times its previous value. EVERY break refuses the frame; the LATCH
    is separate and needs three in a row, because a single transient
    frame necessarily poisons two comparisons. Floored-residue frames
    are re-solved with lawful decay restored (module docstring) and
    recorded on percep.floored_steps — accepted, never silent."""
    field = rival_scent.values()
    if not any(any(row) for row in field):
        # An EMPTY field is absence of data, not impossible data (a peer
        # honouring a no-trail lock sends nothing to check) — but the
        # census books it: silence must be visible in the summary.
        percep.scent_frames_empty += 1
        return False
    percep.scent_frames_seen += 1
    if percep.rival_scent_law != "book":
        # The rival DECLARED the league's other branch (the reference's
        # subtractive_chebyshev_v1). Our own law cannot verify those frames -
        # under subtraction a cell legally falls below (1-rho) times its
        # previous value, so the gate would break on every frame and the latch
        # would blind us by turn four against an HONEST peer.
        #
        # Solve THEIR published law instead (peer/foreign_scent.py). Strictly
        # additive: a solved transition yields the emitter pin (and with it the
        # rule-36 trail track), an unsolved one yields nothing. It never
        # refuses and never latches, because an error in OUR model of THEIR
        # physics must not be able to blind us - the exact failure this path
        # exists to prevent.
        percep._last_emitter = None
        if percep._previous_field is not None:
            found = foreign_scent.foreign_emitters(
                percep._previous_field, field, percep.grid_size)
            if len(found) == 1:
                percep._last_emitter = found[0]
        return False
    if percep._previous_field is None:
        return False  # nothing to compare the first frame against
    emitters, floored = solve_with_tolerance(
        percep._previous_field, field, board, percep.grid_size,
        percep.floor_eps)
    if floored:
        percep.floored_steps.append(percep._anchor_age)
    if emitters:
        percep._law_breaks, percep._last_emitter = 0, (
            emitters[0] if len(emitters) == 1 else None)
        return False
    percep._law_breaks += 1
    if percep._law_breaks >= 3:
        percep.scent_trusted = False
    return True


def scent_evidence(percep) -> dict:
    """The summary's scent-trust evidence block (rule 36): counts, the
    exact refused rival turns, and the tolerated floored turns."""
    law = getattr(percep, "rival_scent_law", "book")
    return {
        "scent_readings_refused": getattr(percep, "refused_readings", 0),
        "scent_refused_steps": getattr(percep, "refused_steps", []),
        "scent_floored_steps": getattr(percep, "floored_steps", []),
        "scent_frames_seen": getattr(percep, "scent_frames_seen", 0),
        "scent_frames_empty": getattr(percep, "scent_frames_empty", 0),
        # Names WHY rival_trail_track may be empty. Under a foreign law we
        # consume the rival's field without solving it, so no emitter is
        # pinned and the track is null by construction - an absence we
        # declare, never a check we silently skipped.
        "rival_scent_law": law,
        "rival_trail_solved": law == "book",
    }
