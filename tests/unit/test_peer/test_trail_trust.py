"""Perception's trust boundary: where an asserted trail becomes belief.

The movement-model check lives here because this is the only place a
transmitted field turns into a posterior. Both properties are load-bearing:
it must NEVER refuse an honest trail (the refusal latches, so a false positive
blinds the peer for the whole game), and it must refuse an impossible one
permanently rather than per-turn.
"""

from p2p_police.domain.engine import GameEngine
from p2p_police.domain.primitives import Move, Role
from p2p_police.domain.rules import RuleSet
from p2p_police.peer.perception import Perception

RULES = RuleSet(max_barriers=14, max_moves=35, survival_threshold=35)


def test_an_honest_trail_is_never_refused_over_a_whole_game() -> None:
    """Soundness of the movement-model check, and the regression that matters.

    An earlier version re-anchored to the latest position estimate, which made
    the allowed set tight - and WRONG: a walker's saturated trail legitimately
    extends behind it, into cells unreachable from where it stands now. Honest
    readings were refused, and because the refusal latches, one false positive
    blinded the peer for the rest of the game (measured: pool capture rate
    0.983 -> 0.358). Anchoring on the AGREED start is sound by construction,
    since every cell the rival ever deposited on lies within kernel range of a
    position reachable in the elapsed turns."""
    engine = GameEngine(7, (0, 0), (3, 3), RULES)
    perception = Perception(Role.POLICE, 7, rival_start=(3, 3))
    walk = [Move.E, Move.E, Move.S, Move.S, Move.E, Move.STAY, Move.STAY,
            Move.STAY, Move.N, Move.W, Move.W, Move.W, Move.N, Move.N]
    for move in walk:
        engine.police_move(Move.STAY)
        engine.thief_move(move)
        perception.observe(engine, Role.THIEF, None)
    assert perception.refused_readings == 0
    assert perception.scent_trusted


def test_a_trail_that_breaks_the_movement_model_latches_off() -> None:
    """A reading claiming a clamp-level deposit the rival could not have
    reached is refused, and the refusal LATCHES - one impossible reading is
    proof the channel is broken or hostile, and re-checking each turn
    independently is defeatable (a refused turn cannot refresh the anchor, so
    the allowed set grows to the whole board within a few turns)."""
    engine = GameEngine(7, (0, 0), (3, 3), RULES)
    perception = Perception(Role.POLICE, 7, rival_start=(3, 3))
    forged = engine.scent[Role.THIEF]
    for _ in range(12):  # a dweller's plateau stamped in the far corner
        forged.update((0, 6))
    perception.observe(engine, Role.THIEF, None)
    assert perception.refused_readings == 1 and not perception.scent_trusted
    before = perception.belief.values()
    engine.police_move(Move.STAY)
    engine.thief_move(Move.STAY)
    perception.observe(engine, Role.THIEF, None)  # honest-looking, still refused
    assert perception.refused_readings == 2
    assert perception.belief.values() != before  # diffusion still runs
