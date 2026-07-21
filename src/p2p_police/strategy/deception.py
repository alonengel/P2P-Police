"""Self-mirror deception: lie exactly when the lie pays (reputation economy).

A SECOND belief filter — fed ONLY by what WE transmit (our own scent trail,
our own hint claims; reusing the rival's exact BeliefMap math) — estimates
what the rival can currently infer about OUR cell. While exposure is low we
tell the truth: honest hints keep our credibility priced high in the rival's
profiler, which is precisely what makes the eventual lie land. Once exposure
crosses the configured threshold AND the rival is (by belief, never by its
true cell) closing in AND the budget/cooldown clock allows, we spend one lie
whose decoy claim points AWAY from the true heading. Intent flags stay
sealed until the audit (ch. 5), so lying remains legal and audit-honest.
All tunables live in game.toml [deception] (private, per-peer).
"""

import random

from p2p_police.domain.belief import BeliefMap
from p2p_police.domain.engine import GameEngine
from p2p_police.domain.primitives import Cell, Move, Role
from p2p_police.strategy.hints import build_hint

OPPOSITE_CLAIM = {"N": "S", "S": "N", "E": "W", "W": "E"}


def decoy_claim(actual_move: Move, rng: random.Random) -> str:
    """The lie's claim: the OPPOSITE of our true heading; a STAY has no
    heading, so claim motion in a random direction (any pulls mass away)."""
    return OPPOSITE_CLAIM.get(actual_move.name) or rng.choice(sorted(OPPOSITE_CLAIM))


class SelfMirror:
    """What can the rival currently infer about US?

    Input: our own engine-side emissions + our own hint claims — never any
    rival data. Output: exposure(), the mass near our true cell. Setup: our
    role + grid size; runs the rival's own BeliefMap pipeline against us.
    """

    def __init__(self, role: Role, grid_size: int) -> None:
        self.role = role
        self.belief = BeliefMap(grid_size)

    def observe_own_turn(self, engine: GameEngine, claim: str | None) -> None:
        """Replay the receiving side's update order (diffuse, scent, hint —
        the sibling Perception.observe) over OUR trail and OUR claim."""
        self.belief.diffuse(engine.board)
        own_scent = engine.scent[self.role]
        self.belief.observe_scent(own_scent, engine.board)
        if claim:
            self.belief.observe_hint(claim, own_scent)

    def exposure(self, true_cell: Cell, radius: int) -> float:
        """Probability mass the mirror puts within Manhattan `radius` of our
        TRUE cell — high means the rival has effectively found us."""
        return sum(
            self.belief.value_at((row, col))
            for row in range(self.belief.grid_size)
            for col in range(self.belief.grid_size)
            if abs(row - true_cell[0]) + abs(col - true_cell[1]) <= radius
        )


class DeceptionClock:
    """Lie budget per sub-game + cooldown between lies (config-driven).

    Scarcity is the point: each truthful hint deposits credibility the rare
    lie later withdraws at full value.
    """

    def __init__(self, max_lies: int, cooldown_turns: int) -> None:
        self.max_lies = max_lies
        self.cooldown_turns = cooldown_turns
        self.lies_told = 0
        self.last_lie_turn: int | None = None

    def may_lie(self, turn: int) -> bool:
        if self.lies_told >= self.max_lies:
            return False
        return self.last_lie_turn is None or turn - self.last_lie_turn > self.cooldown_turns

    def record_lie(self, turn: int) -> None:
        self.lies_told += 1
        self.last_lie_turn = turn


class DeceptionPolicy:
    """decide_truth: lie only when exposed AND hunted AND the clock allows."""

    def __init__(self, tuning: dict) -> None:
        self.exposure_threshold = float(tuning["exposure_threshold"])
        self.distance_threshold = int(tuning["opponent_distance_threshold"])
        self.exposure_radius = int(tuning["exposure_radius"])

    def decide_truth(self, engine, perception, mirror, clock, turn: int) -> bool:
        """True = truthful hint. Consumes LOCAL truth (our own cell) and our
        belief about the rival — never the rival's true position."""
        me = engine.positions[mirror.role]
        exposed = mirror.exposure(me, self.exposure_radius) >= self.exposure_threshold
        guess = perception.belief.argmax_cell()
        close = abs(guess[0] - me[0]) + abs(guess[1] - me[1]) <= self.distance_threshold
        return not (exposed and close and clock.may_lie(turn))


class Deceiver:
    """Runtime facade: one object owning mirror + clock + policy.

    Input per own half-turn: engine, perception, chosen move. Output:
    (claim, intent_is_truth) — `decisions` is the trail the audit reveals.
    Setup: role, loaded Config, the brain's RNG (deterministic per seed).
    """

    def __init__(self, role: Role, config, rng: random.Random) -> None:
        tuning = config.deception()
        self.rng = rng
        self.max_words = int(config.shared["world"]["hint_max_words"])
        self.mirror = SelfMirror(role, config.grid_size)
        self.clock = DeceptionClock(tuning["max_lies"], tuning["cooldown_turns"])
        self.policy = DeceptionPolicy(tuning)
        self.decisions: list[bool] = []

    def plan_hint(self, engine, perception, move: Move, turn: int) -> tuple[str, bool]:
        truth = self.policy.decide_truth(engine, perception, self.mirror, self.clock, turn)
        decoy = None if truth else decoy_claim(move, self.rng)
        _text, claim, verdict = build_hint(move, truth, self.max_words, self.rng, decoy=decoy)
        if not verdict:
            self.clock.record_lie(turn)
        self.decisions.append(verdict)
        return claim, verdict

    def observe_own(self, engine: GameEngine, claim: str) -> None:
        """After our action applies: feed the mirror what we just leaked —
        the exact state the rival's Perception reads on receipt."""
        self.mirror.observe_own_turn(engine, claim)
