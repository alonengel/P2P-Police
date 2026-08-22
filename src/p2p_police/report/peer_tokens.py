"""The rival's per-window token usage, priced from its sealed step-zero
chain (rule 50 needs both sides' spend on the report; the peer's own
number is its claim — ours must ECHO evidence, never invent).

Wire semantics decoded live against najamjad (2026-08-22): each side's
step-zero carries its CUMULATIVE usage at window start, per role process,
so one window's usage is the NEXT same-role window's snapshot minus its
own. The four checkable deltas of that series reproduce their emailed
per-window claims digit-for-digit; each chain's LAST window has no
successor seal, so its usage is in-band unknowable and files null — our
reports coerced it to 0 against their truthful 27,866, the exact reader
bug their own terms doc (§9.5) warns about.
"""


def _snapshot(summary: dict) -> int | None:
    zero = summary.get("opponent_step_zero") or {}
    value = zero.get("tokens_total")
    return int(value) if isinstance(value, (int, float)) else None


def usage_by_slot(by_slot: dict) -> dict[int, int | None]:
    """slot -> the peer's usage in that window (None = unknowable). The
    peer runs one process per role, so chains group by the PEER's role
    (the complement of ours) and deltas never cross processes."""
    chains: dict[str, list[int]] = {}
    for slot in sorted(by_slot):
        ours = by_slot[slot]["summary"].get("role", "police")
        theirs = "thief" if ours == "police" else "police"
        chains.setdefault(theirs, []).append(slot)
    usage: dict[int, int | None] = {}
    for slots in chains.values():
        snaps = {n: _snapshot(by_slot[n]["summary"]) for n in slots}
        for here, following in zip(slots, slots[1:] + [None], strict=True):
            start = snaps[here]
            end = None if following is None else snaps[following]
            delta = None if start is None or end is None else end - start
            # a shrinking meter is no meter: refuse negative claims
            usage[here] = delta if delta is not None and delta >= 0 else None
    return usage


def series_total(per_slot: dict[int, int | None]) -> int | None:
    """A series total is claimed only when EVERY window is known — a sum
    over partial knowledge would understate the peer's truthful figure
    and diff two honest reports against each other."""
    values = list(per_slot.values())
    if not values or any(value is None for value in values):
        return None
    return sum(values)


def totals_by_name(sub_games: list[dict]) -> dict[str, int | None]:
    """tokens_total_series from the settled rows, per NAME (self-play
    suffixes flip columns per window, so names — not sides — key it):
    our own column is all ints and sums; the chain-priced peer column
    totals only when every window is known, else null."""
    columns: dict[str, dict[int, int | None]] = {}
    for i, entry in enumerate(sub_games):
        for name, value in entry["tokens"].items():
            columns.setdefault(name, {})[i] = value
    return {name: series_total(column) for name, column in columns.items()}
