"""Config-owned reorder-buffer cap ([network] inbound_buffer_limit, floored)
and the evidence-grade absorption event for tolerated duplicates."""

import logging

import pytest

from p2p_police.domain.engine import GameEngine
from p2p_police.domain.errors import GameRuleError
from p2p_police.domain.primitives import Role
from p2p_police.domain.rules import RuleSet
from p2p_police.peer.sealing import SealedExchange, pending_cap_from

RULES = RuleSet(max_barriers=14, max_moves=35, survival_threshold=35)


def test_pending_cap_is_config_owned_with_a_floor() -> None:
    """[network] inbound_buffer_limit owns the cap (default 8); the floor
    keeps a resume-split pair absorbable - below it the exchange refuses."""
    class Tuned:
        private = {"network": {"inbound_buffer_limit": 5}}

    class Bare:
        private = {}

    assert pending_cap_from(Tuned()) == 5
    assert pending_cap_from(Bare()) == 8  # committed default preserved
    with pytest.raises(ValueError, match="inbound_buffer_limit"):
        SealedExchange(Role.POLICE, 1, [].append, lambda what: None, pending_cap=3)


def test_config_narrowed_cap_trips_the_flood_earlier() -> None:
    junk = [{"kind": "commit", "turn": 90 + n, "actor": "thief"} for n in range(5)]
    bob = SealedExchange(Role.POLICE, 1, junk.append, lambda what: junk.pop(0),
                         pending_cap=4)
    with pytest.raises(GameRuleError, match="flooded"):
        bob.receive_sealed(1)


def test_duplicate_absorption_is_an_evidence_grade_event(caplog) -> None:
    """The tolerated duplicate leaves a structured INFO record (stable key
    inbound_tolerated, fields kind/turn/reason) - evidence, not debug noise,
    and never a wire change."""
    engine = GameEngine(7, (0, 0), (3, 3), RULES)
    sent: list = []
    alice = SealedExchange(Role.POLICE, 1, sent.append, lambda what: sent.pop(0))
    alice.send_sealed(engine, 1, {"type": "move", "move": "E"}, "hi", True)
    sent.insert(1, dict(sent[0]))  # duplicate the commit in-queue
    bob = SealedExchange(Role.THIEF, 1, sent.append, lambda what: sent.pop(0))
    with caplog.at_level(logging.INFO, logger="p2p_police.peer.sealing"):
        bob.receive_sealed(1)
    tolerated = [r for r in caplog.records if "inbound_tolerated" in r.getMessage()]
    assert len(tolerated) == 1
    message = tolerated[0].getMessage()
    assert "kind=commit" in message and "turn=1" in message
    assert "reason=duplicate delivery" in message
