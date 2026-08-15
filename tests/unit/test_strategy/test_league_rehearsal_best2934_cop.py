"""League rehearsal: best2934's thief (2026-08-15 friendly #1, g01/g03/g05).

Their thief is a fixed-opening edge-parker: (3,3) -S,S,S-> (6,3) -E,E->
(6,5), then STAY through step 35, announcing the park in plaintext ("Honest
one: nowhere, by ..."). It survived friendly #1 against our STALL DECOY —
by design. These tapes replay their exact recorded moves+hints through our
REAL perception + brain: the series cop must convert a 30-turn camper with
margin (the saturated plateau is the exact case the plateau pin exists
for), or the counted loadout is not ready and the decoder debate reopens.
Live caveat as ever: assume the live thief reacts (adjacency veto) and is
stronger than its recording — hence the margin bound, not just capture.
"""

import json
import random
from pathlib import Path

from p2p_police.domain import protocol
from p2p_police.domain.engine import GameEngine
from p2p_police.domain.primitives import Outcome, Role
from p2p_police.domain.rules import RuleSet
from p2p_police.peer.perception import Perception
from p2p_police.shared.config import Config
from p2p_police.strategy.police_brain import PoliceBrain

RULES = RuleSet(max_barriers=14, max_moves=35, survival_threshold=35)
_TAPES = json.loads(
    (Path(__file__).parent / "best2934_thief_tapes.json").read_text(encoding="utf-8"))
SEEDS = range(5)


def play_tape(seed: int, game: str):
    """Our live cop pipeline vs their recorded thief, open loop (same
    harness as the nis-yar1 rehearsals: cop acts on belief, thief answers
    from the tape, perception consumes the move + hint)."""
    tape = _TAPES[game]
    engine = GameEngine(7, (0, 0), (3, 3), RULES)
    config = Config.load("config")
    brain = PoliceBrain(Role.POLICE, random.Random(seed), config)
    percep = Perception.for_peer(Role.POLICE, config)
    moves, hints = tape["moves"], tape["hints"]
    for turn in range(RULES.max_moves):
        protocol.apply_action(engine, Role.POLICE, brain.decide(engine, percep.belief))
        if engine.outcome is not Outcome.ONGOING:
            break
        step = moves[turn] if turn < len(moves) else "-"
        action = {"type": "move", "move": "STAY" if step == "-" else step}
        try:
            protocol.apply_action(engine, Role.THIEF, action)
        except Exception:  # tape diverged into a wall we placed: hold instead
            protocol.apply_action(engine, Role.THIEF, {"type": "move", "move": "STAY"})
        if engine.outcome is not Outcome.ONGOING:
            break
        hint = hints[turn] if turn < len(hints) else ""
        percep.observe(engine, Role.THIEF, hint)
    return engine.outcome, engine.turns_completed


def test_edge_parker_tapes_convert_with_margin() -> None:
    """All three recorded games, every seed: the camper must be CAUGHT, and
    early enough that a live, veto-reacting thief still falls inside 35."""
    for game in ("g01", "g03", "g05"):
        for seed in SEEDS:
            outcome, turns = play_tape(seed, game)
            assert outcome is Outcome.CAPTURE, f"{game} seed {seed}: {outcome}"
            assert turns <= 25, f"{game} seed {seed}: caught only at {turns}"
