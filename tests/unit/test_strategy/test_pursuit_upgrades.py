"""The two imreeyal-studied pursuit knobs, both OFF by default so the
counted decision stream stays byte-identical until a sweep arms them:
[strategy.pursuit] w_safe_region (compression term) and [strategy.trap]
reserve (barriers held back for the endgame solver's finishing walls).
"""

import random

from p2p_police.domain.engine import GameEngine
from p2p_police.domain.primitives import Role
from p2p_police.domain.rules import RuleSet
from p2p_police.shared.tuning import PURSUIT_DEFAULTS, TRAP_DEFAULTS
from p2p_police.strategy.police_brain import PoliceBrain

RULES = RuleSet(max_barriers=14, max_moves=35, survival_threshold=35)


class _Config:
    def __init__(self, private):
        self.private = private


def test_both_knobs_default_off() -> None:
    assert PURSUIT_DEFAULTS["w_safe_region"] == 0.0
    assert TRAP_DEFAULTS["reserve"] == 0


def test_compression_term_steers_equal_distance_approaches() -> None:
    """Cop two BFS steps from the thief via S or E (asymmetric thief cell
    so the safe regions differ): armed with a small weight, the approach
    leaving the thief LESS safe ground wins the tie — every time."""
    from p2p_police.strategy.region_race import safe_region_size

    engine = GameEngine(7, (4, 4), (6, 5), RULES)
    tied = {"S": (5, 4), "E": (4, 5)}  # both BFS distance 2 from (6,5)
    regions = {m: safe_region_size(engine.board, (6, 5), c)
               for m, c in tied.items()}
    assert regions["S"] != regions["E"]  # the asymmetry is load-bearing
    want = min(regions, key=lambda m: regions[m])
    armed = PoliceBrain(Role.POLICE, random.Random(1),
                        _Config({"strategy": {"pursuit": {"w_safe_region": 0.05}}}))
    assert all(armed.decide(engine)["move"] == want for _ in range(8))


def test_reserve_holds_back_the_last_walls() -> None:
    """With reserve=2 and only 2 barriers left in quota, the trap gate
    refuses to spend — those walls belong to the endgame's proven seal.
    (Thief NOT in reach, so the step-in preference stays out of the way.)"""
    engine = GameEngine(7, (4, 6), (6, 6), RULES)
    for i in range(12):  # 12 of 14 spent elsewhere
        engine.board.add_barrier((0, i % 7) if i < 7 else (1, i - 7))
    reserved = PoliceBrain(Role.POLICE, random.Random(3),
                           _Config({"strategy": {"trap": {"reserve": 2}}}))
    spender = PoliceBrain(Role.POLICE, random.Random(3), _Config({}))
    assert reserved._trap_barrier(engine, (4, 6), (6, 6), 2) is None
    assert spender._trap_barrier(engine, (4, 6), (6, 6), 2) is not None
