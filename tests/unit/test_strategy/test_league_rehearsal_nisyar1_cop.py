"""League rehearsal: nis-yar1's RUNNER thief (2026-08-11, g03/g05 tapes).

Their thief stopped camping and started running: perimeter loops (g03),
interior loops with corner HOLDs (g05), landmark-lying prose the whole way.
Our cop lost both games — walls landed one turn late, adjacency never
converted. These tapes replay their exact recorded moves+hints through our
REAL perception + brain; the fixed cop must catch the recorded trajectory,
and must not lose the fast capture it already owns (g01 tape).
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
    (Path(__file__).parent / "nisyar1_thief_tapes.json").read_text(encoding="utf-8"))


def play_tape(seed: int, game: str):
    """Our live cop pipeline vs their recorded thief, open loop.

    Turn order mirrors the live windows: our cop acts on its belief, their
    thief answers from the tape, then perception consumes the thief's move
    and hint (scent rides the engine exactly as the live wire transmits it).
    """
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


SEEDS = range(5)


def _captures(game: str) -> int:
    return sum(play_tape(seed, game)[0] is Outcome.CAPTURE for seed in SEEDS)


def test_runner_tape_g03_is_caught() -> None:
    """The perimeter runner that survived our cop on 2026-08-11 g03."""
    captures = _captures("g03")
    assert captures >= 4, f"g03 runner caught only {captures}/5"


def test_looper_tape_g05_is_caught() -> None:
    """The interior looper with corner HOLDs that survived g05."""
    captures = _captures("g05")
    assert captures >= 4, f"g05 looper caught only {captures}/5"


def test_newest_runner_tape_g03new_is_caught_with_margin() -> None:
    """Their 2026-08-11 15:25 thief — the one that survived our fixed cop
    live (pre trail-pin). Following-only pursuit converted this tape at turn
    33 of 35: zero margin, and their next iteration survived live. The
    INTERCEPTING cop must beat the tape with room to spare — assume the live
    thief is stronger than its recording."""
    for seed in SEEDS:
        outcome, turns = play_tape(seed, "g03new")
        assert outcome is Outcome.CAPTURE, f"g03new seed {seed}: {outcome}"
        assert turns <= 30, f"g03new seed {seed}: caught only at turn {turns}"


def test_recovered_live_survivor_tape_is_caught() -> None:
    """The 2026-08-11 16:28 g01 — the game their thief SURVIVED live against
    our pre-interception cop (tape recovered from their archive after ours
    was lost to a cleanup sweep). The intercepting cop converts it at turn
    21; the bound leaves margin for a live thief stronger than its tape."""
    for seed in SEEDS:
        outcome, turns = play_tape(seed, "g01surv")
        assert outcome is Outcome.CAPTURE, f"g01surv seed {seed}: {outcome}"
        assert turns <= 30, f"g01surv seed {seed}: caught only at turn {turns}"


def test_ditherer_tape_g01_stays_fast() -> None:
    """Regression pin: the g01 capture our cop already owns must not regress
    — caught, and caught fast (live: 10 turns; allow slack to 14)."""
    for seed in range(5):
        outcome, turns = play_tape(seed, "g01")
        assert outcome is Outcome.CAPTURE, f"g01 seed {seed}: {outcome}"
        assert turns <= 14, f"g01 seed {seed}: caught only at turn {turns}"


_IMREE_TAPES = json.loads(
    (Path(__file__).parent / "nisyar1_imree_tapes.json").read_text(encoding="utf-8"))


def test_their_best_escape_is_caught() -> None:
    """Their thief's strongest recorded game (2026-08-11 vs imreeyal g01):
    SE drift, column-5 run north, top-edge perch — a full 35-turn survival
    against the counted-champion's cop. Ours must cut the column run. The
    tape rides the imreeyal jsonl audit reveals, hints included."""
    tape = _IMREE_TAPES["imree_g01_theirthief"]
    moves, hints = [], []
    for row in tape:
        arg = row["move"].partition(":")[2] or "STAY"
        moves.append(arg if arg in ("N", "S", "E", "W") else "-")
        hints.append(row.get("hint", ""))
    _TAPES["imree_escape"] = {"moves": moves, "hints": hints}
    for seed in SEEDS:
        outcome, turns = play_tape(seed, "imree_escape")
        assert outcome is Outcome.CAPTURE, f"seed {seed}: {outcome}"
        assert turns <= 30, f"seed {seed}: caught only at turn {turns}"
