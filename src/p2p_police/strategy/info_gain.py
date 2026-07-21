"""Information-gain pursuit term: expected belief-entropy reduction per move.

The cop's only positional sense is the thief's scent field, so a landing cell
whose LOCAL reading would differ across the belief's competing hypotheses is
worth steps: next turn's observation collapses exactly those hypotheses. For
each candidate landing we simulate, per hypothesis cell (weighted by its
mass), the fresh-emission kernel reading the cop would collect there, apply a
match/mismatch likelihood to a values() SNAPSHOT of the belief (the live map
is never touched) and average the posterior entropies:

    gain(landing) = H(belief now) - E_hypothesis[H(belief | reading)]  >= 0

The kernel takes few distinct values, so hypotheses are grouped by their
predicted reading - one posterior per distinct reading, not per cell.
Blend weight and likelihood shape come from [strategy.info_gain].
"""

import math

from p2p_police.domain.primitives import Cell
from p2p_police.domain.scent import EMISSION_KERNEL, KERNEL_RADIUS


def kernel_reading(landing: Cell, emitter: Cell) -> float:
    """Fresh-emission intensity the cop would read at `landing` for a thief
    at `emitter` (the book's fixed 5x5 kernel; silence outside it)."""
    row = landing[0] - emitter[0] + KERNEL_RADIUS
    col = landing[1] - emitter[1] + KERNEL_RADIUS
    if 0 <= row < len(EMISSION_KERNEL) and 0 <= col < len(EMISSION_KERNEL):
        return EMISSION_KERNEL[row][col]
    return 0.0


def entropy(masses: list[float]) -> float:
    """Shannon entropy (nats) of an unnormalized mass vector."""
    total = sum(masses)
    if total <= 0.0:
        return 0.0
    return -sum((m / total) * math.log(m / total) for m in masses if m > 0.0)


def expected_gain(belief, landing: Cell, settings: dict) -> float:
    """Expected entropy reduction from the scent reading at `landing`."""
    values = belief.values()  # snapshot copy - live belief state never touched
    cells = [((row, col), mass) for row, masses in enumerate(values)
             for col, mass in enumerate(masses) if mass > 0.0]
    if len(cells) < 2:
        return 0.0  # a settled belief has nothing left to learn
    readings = [kernel_reading(landing, cell) for cell, _ in cells]
    tolerance, mismatch = settings["match_tolerance"], settings["mismatch_likelihood"]
    prior = entropy([mass for _, mass in cells])
    grouped: dict[float, float] = {}
    for reading, (_, mass) in zip(readings, cells, strict=True):
        grouped[reading] = grouped.get(reading, 0.0) + mass
    expected = 0.0
    for observed, group_mass in grouped.items():
        posterior = [
            mass * (1.0 if abs(reading - observed) <= tolerance else mismatch)
            for reading, (_, mass) in zip(readings, cells, strict=True)
        ]
        expected += group_mass * entropy(posterior)
    return max(0.0, prior - expected)
