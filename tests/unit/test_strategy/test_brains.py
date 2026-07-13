"""Strategy tests: the [strategy] seam resolves configured brains, the shipped
pursuit brain wins the PRD-03 arena milestone (beats a random thief), and
brain actions are always legal."""

import random
from pathlib import Path

import pytest

from p2p_police.domain import protocol
from p2p_police.domain.board import Board
from p2p_police.domain.engine import GameEngine
from p2p_police.domain.pathfind import bfs_distances, distance_between
from p2p_police.domain.primitives import Outcome, Role
from p2p_police.domain.rules import RuleSet
from p2p_police.shared.config import Config
from p2p_police.strategy.brain_base import BrainBase, RandomBrain, resolve_brain
from p2p_police.strategy.police_brain import PoliceBrain, ThiefForArena

RULES = RuleSet(max_barriers=14, max_moves=35, survival_threshold=35)


def test_bfs_respects_barriers() -> None:
    board = Board(7)
    assert distance_between(board, (0, 0), (0, 2)) == 2
    board.add_barrier((0, 1))
    assert distance_between(board, (0, 0), (0, 2)) == 4  # around the wall


def test_bfs_unreachable_when_walled_off() -> None:
    board = Board(7)
    for cell in [(0, 1), (1, 1), (1, 0)]:
        board.add_barrier(cell)
    assert distance_between(board, (0, 0), (6, 6)) == -1
    assert (6, 6) not in bfs_distances(board, (0, 0))


def play_arena(police_brain: BrainBase, thief_brain: BrainBase) -> Outcome:
    engine = GameEngine(7, (0, 0), (3, 3), RULES)
    while engine.outcome is Outcome.ONGOING:
        actor = engine.next_actor
        brain = police_brain if actor is Role.POLICE else thief_brain
        protocol.apply_action(engine, actor, brain.decide(engine))
    return engine.outcome


def test_pursuit_brain_beats_random_thief_at_least_80_percent() -> None:
    """PRD-03 milestone."""
    wins = 0
    for seed in range(25):
        outcome = play_arena(
            PoliceBrain(Role.POLICE, random.Random(seed)),
            RandomBrain(Role.THIEF, random.Random(seed + 1000)),
        )
        wins += outcome is Outcome.CAPTURE
    assert wins >= 20, f"pursuit brain captured only {wins}/25 random thieves"


def test_pursuit_vs_evading_arena_thief_completes_legally() -> None:
    """Sanity vs a real evader (the true thief brain lives in the twin repo):
    games complete legally; dominance is not asserted here."""
    for seed in range(5):
        outcome = play_arena(
            PoliceBrain(Role.POLICE, random.Random(seed)),
            ThiefForArena(Role.THIEF, random.Random(seed + 7)),
        )
        assert outcome in (Outcome.CAPTURE, Outcome.SURVIVAL)


def test_resolve_brain_defaults_to_shipped_police_brain(config_dir: Path) -> None:
    config = Config.load(config_dir)
    assert isinstance(resolve_brain(config, Role.POLICE, random.Random(0)), PoliceBrain)


def test_resolve_brain_honors_strategy_override(config_dir: Path) -> None:
    toml_path = config_dir / "game.toml"
    toml_path.write_text(
        toml_path.read_text(encoding="utf-8")
        + '\n[strategy]\npolice_class = "p2p_police.strategy.brain_base:RandomBrain"\n',
        encoding="utf-8",
    )
    config = Config.load(config_dir)
    assert isinstance(resolve_brain(config, Role.POLICE, random.Random(0)), RandomBrain)


def test_resolve_brain_surfaces_bad_spec_loudly(config_dir: Path) -> None:
    toml_path = config_dir / "game.toml"
    toml_path.write_text(
        toml_path.read_text(encoding="utf-8")
        + '\n[strategy]\npolice_class = "no.such.module:Nope"\n',
        encoding="utf-8",
    )
    config = Config.load(config_dir)
    with pytest.raises(ModuleNotFoundError):
        resolve_brain(config, Role.POLICE, random.Random(0))
