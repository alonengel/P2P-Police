"""Rules 46/47 adjudicated from a FOREIGN rival's own revealed positions
(split from audit_foreign.py for the 150-code-line cap).

A barrier capture is only ever SELF-declared: under hidden information the cop
cannot see that its wall sealed the thief, so a peer that never runs its own
imprisonment check simply plays on and claims survival (measured live
2026-08-01, three games). The reveal settles it after the fact — their
positions are in their own records — so the evidence exists even though the
live game could not use it. Reported, never a unilateral rewrite: the logs
decide (rule 35).
"""

NEIGHBOURS = ((-1, 0), (1, 0), (0, 1), (0, -1))


def own_barrier_timeline(own_records: list) -> list:
    """(step, cell) for every barrier WE sealed — the placement clock the
    dispute check needs, read from our own records."""
    timeline = []
    for record in own_records:
        payload = record.get("payload") or {}
        action = payload.get("action") or {}
        if action.get("type") == "barrier" and payload.get("step") is not None:
            timeline.append((payload["step"], tuple(action["cell"])))
    return timeline


def _step_of(record: dict):
    step = record.get("payload", {}).get("step") if isinstance(record, dict) else None
    return step if isinstance(step, int) and not isinstance(step, bool) else None


def unconceded_capture(their_records: list, barriers: list, grid: int,
                       outcome: str | None = None) -> dict | None:
    """The first capture their own reveal proves and their peer never
    conceded, as an evidence dict — or None.

    `barriers` is (step, cell) pairs: a wall constrains only from the step it
    was PLACED. Comparing positions against the final barrier set flags every
    cell the thief legally crossed before the wall existed — a false
    accusation, and the first thing this check did in the wild (2026-08-03).
    A game that ENDED in capture is never disputed either: the duty was
    honoured, whatever route it took.
    """
    if outcome == "capture":
        return None
    timeline = [(step, (cell[0], cell[1])) for step, cell in barriers]
    for record in sorted((r for r in their_records if _step_of(r) is not None),
                         key=_step_of):
        cell = record.get("payload", {}).get("position")
        step = _step_of(record)
        if not (isinstance(cell, list) and len(cell) == 2):
            continue
        spot = (cell[0], cell[1])
        walls = {wall for placed, wall in timeline if placed <= step}
        sealed = all(
            not (0 <= spot[0] + dr < grid and 0 <= spot[1] + dc < grid)
            or (spot[0] + dr, spot[1] + dc) in walls
            for dr, dc in NEIGHBOURS)
        if spot in walls or sealed:
            return {"step": step, "cell": list(spot),
                    "rule": "46 (barrier on the thief)" if spot in walls
                            else "47 (fully surrounded)",
                    "barriers": sorted(list(w) for w in walls)}
    return None
