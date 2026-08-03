"""Barrier declarations are evidence: an observed placement localizes the
placer to the wall's passable neighbors (law of barriers) inside the belief,
wired through Perception on BOTH wires — geometric sealed payloads and
reference-v3 barrier_placed declarations. Duplicate declarations (at-least-
once transport) must never double-boost."""

from types import SimpleNamespace

from p2p_police.domain.engine import GameEngine
from p2p_police.domain.primitives import Role
from p2p_police.domain.rules import RuleSet
from p2p_police.peer.perception import Perception
from p2p_police.peer.runtime import GeometricRuntime
from p2p_police.wire import codec
from p2p_police.wire.hidden_turns import their_half_turn
from p2p_police.wire.own_state import OwnState

RULES = RuleSet(max_barriers=14, max_moves=35, survival_threshold=35)
ORIGINS = [(2, 4), (4, 4), (3, 3), (3, 5)]  # passable neighbors of (3, 4)


def origin_mass(belief) -> float:
    return sum(belief.value_at(cell) for cell in ORIGINS)


def test_observed_barrier_concentrates_belief_on_origins() -> None:
    engine = GameEngine(7, (3, 3), (0, 0), RULES)
    perception = Perception(Role.THIEF, 7)
    engine.police_place_barrier((3, 4))
    perception.observe(engine, Role.POLICE, None, barrier_cell=(3, 4))
    assert perception.belief.value_at((3, 4)) == 0.0
    assert origin_mass(perception.belief) > 0.5


def test_observe_without_barrier_keeps_prior_flat() -> None:
    engine = GameEngine(7, (3, 3), (0, 0), RULES)
    perception = Perception(Role.THIEF, 7)
    perception.observe(engine, Role.POLICE, None)
    assert origin_mass(perception.belief) < 0.2  # no phantom localization


def test_inbound_hint_view_capped_at_signed_words() -> None:
    """An overlong rival hint never reaches belief/GUI beyond the signed
    hint_max_words — the VIEW is capped; the wire message stays untouched
    for the audit's live-vs-sealed comparison (inbound hardening)."""
    engine = GameEngine(7, (3, 3), (0, 0), RULES)
    perception = Perception(Role.THIEF, 7, hint_cap=15)
    perception.observe(engine, Role.POLICE, " ".join(["word"] * 40))
    assert len(perception.last_hint.split()) == 15


def test_geometric_runtime_feeds_declared_barriers_to_belief() -> None:
    """_their_half_turn passes the sealed barrier action into Perception."""
    engine = GameEngine(7, (3, 3), (0, 0), RULES)
    payload = {"role": "police", "action": {"type": "barrier", "cell": [3, 4]}}
    rt = SimpleNamespace(
        exchange=SimpleNamespace(receive_sealed=lambda index: payload),
        role=Role.THIEF, engine=engine, perception=Perception(Role.THIEF, 7),
    )
    GeometricRuntime._their_half_turn(rt, 1)
    assert engine.board.is_barrier((3, 4))
    assert origin_mass(rt.perception.belief) > 0.5


def test_hidden_wire_feeds_fresh_barrier_declarations_once() -> None:
    """reference-v3: barrier_placed reaches the belief the turn it is NEW;
    a redelivered declaration is transport noise and must not re-boost."""
    own = OwnState(Role.THIEF, 7, (0, 0), RULES)
    own.apply_own_action({"type": "move", "move": "STAY"})
    own.close_full_turn()  # our step ticks the round; now the rival replies
    message = codec.build_turn_message(
        1, "police", "walls going up", {}, "c" * 64, barrier_placed=[3, 4])
    rt = SimpleNamespace(
        their_step=0, own=own, role=Role.THIEF, pending_claim_response=None,
        exchange=SimpleNamespace(receive_turn=lambda step: dict(message)),
        perception=Perception(Role.THIEF, 7),
    )
    their_half_turn(rt)
    assert own.board.is_barrier((3, 4))
    first = origin_mass(rt.perception.belief)
    assert first > 0.5
    own.apply_own_action({"type": "move", "move": "STAY"})  # play our step
    own.close_full_turn()
    message["step"] = 2  # rival resends the same declaration next turn
    their_half_turn(rt)
    assert origin_mass(rt.perception.belief) <= first  # diffusion only
