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
from p2p_police.domain.scent import ScentField
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


def _play(engine, perception, moves, corrupt=None):
    for move in moves:
        engine.police_move(Move.STAY)
        engine.thief_move(move)
        if corrupt is not None:
            engine.scent[Role.THIEF]._grid[corrupt[0]][corrupt[1]] = 0.9
        perception.observe(engine, Role.THIEF, None)


def test_one_bad_frame_is_refused_and_the_peer_recovers() -> None:
    """A transient corrupt frame must cost two comparisons, not the game.

    The first version failed both ways at once: needing TWO breaks before
    refusing meant the bad frame was fed to belief (the very half-believing we
    warn others against), and keeping the baseline at the last ACCEPTED frame
    meant every later honest frame sat two-or-more advances away and broke
    forever. One glitch both poisoned the posterior and blinded the peer.
    """
    engine = GameEngine(7, (0, 0), (3, 3), RULES)
    perception = Perception(Role.POLICE, 7, rival_start=(3, 3))
    _play(engine, perception, [Move.E, Move.S])
    assert perception.refused_readings == 0

    _play(engine, perception, [Move.E], corrupt=(0, 6))  # one transport glitch
    assert perception.refused_readings == 1  # refused, NOT absorbed
    assert perception.scent_trusted  # and not latched on a single glitch

    _play(engine, perception, [Move.S, Move.E, Move.S])
    # PERSISTENT corruption (written into the field, so it evolves onward)
    # costs exactly one comparison, whatever its sign: the phantom then decays
    # by (1-rho), which is decay-only and legal, so the next frame is explained
    # again. See the transient case below for the other row - the sign never
    # decides this, only whether the corruption entered an evolving state.
    assert perception.refused_readings == 1
    assert perception.scent_trusted


def test_a_sustained_forgery_still_latches() -> None:
    """Recovery must not become a way to keep steering us frame after frame."""
    engine = GameEngine(7, (0, 0), (3, 3), RULES)
    perception = Perception(Role.POLICE, 7, rival_start=(3, 3))
    _play(engine, perception, [Move.E])
    _play(engine, perception, [Move.S, Move.E, Move.S, Move.E], corrupt=(0, 6))
    assert not perception.scent_trusted


def test_an_empty_field_is_absence_of_data_not_impossible_data() -> None:
    """Interop with a peer that transmits no trail.

    Under book-v1 an empty field explains NO emitter - a live agent always
    deposits somewhere - so a naive checker refuses every frame and latches
    against a peer doing exactly what a `transmitted: false` lock asks. The
    distinction is between a field that lies and a field that is not sent."""
    engine = GameEngine(7, (0, 0), (3, 3), RULES)
    perception = Perception(Role.POLICE, 7, rival_start=(3, 3))
    _play(engine, perception, [Move.E])
    for move in (Move.S, Move.W, Move.N, Move.E):
        engine.police_move(Move.STAY)
        engine.thief_move(move)
        engine.scent[Role.THIEF]._grid = [[0.0] * 7 for _ in range(7)]  # nothing sent
        perception.observe(engine, Role.THIEF, None)
    assert perception.scent_trusted
    assert perception.refused_readings == 0


class _Seen:
    """Engine view whose RIVAL field is a copy corrupted in transit."""

    def __init__(self, engine, field):
        self.board = engine.board
        self.scent = dict(engine.scent)
        self.scent[Role.THIEF] = field


def test_a_transient_corruption_costs_two_comparisons_and_still_recovers() -> None:
    """The other row of the matrix, and the one a faulty transport produces.

    A frame corrupted IN TRANSIT never reaches the sender's state, so the next
    honest frame does not carry the phantom either - and the comparison starts
    from the corrupted baseline, where the value is already gone. Staying gone
    is not legal for a cell the emitter is still feeding, so that second
    comparison breaks too. Two refusals, then recovery, and never a latch.
    """
    engine = GameEngine(7, (0, 0), (3, 3), RULES)
    perception = Perception(Role.POLICE, 7, rival_start=(3, 3))
    for turn, move in enumerate([Move.E, Move.S, Move.E, Move.S, Move.W], start=1):
        engine.police_move(Move.STAY)
        engine.thief_move(move)
        if turn == 3:  # one frame mangled between sender and receiver
            field = ScentField(7)
            field._grid = [row.copy() for row in engine.scent[Role.THIEF].values()]
            field._grid[0][6] = 0.9
            perception.observe(_Seen(engine, field), Role.THIEF, None)
            continue
        perception.observe(engine, Role.THIEF, None)
    assert perception.refused_readings == 2
    assert perception.scent_trusted  # recovered, never latched
