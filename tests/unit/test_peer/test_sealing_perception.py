"""SealedExchange happy-path + desync rejections; Perception local-truth gate."""

import pytest

from p2p_police.domain.engine import GameEngine
from p2p_police.domain.errors import GameRuleError
from p2p_police.domain.primitives import Role
from p2p_police.domain.rules import RuleSet
from p2p_police.peer.perception import Perception
from p2p_police.peer.sealing import SealedExchange

RULES = RuleSet(max_barriers=14, max_moves=35, survival_threshold=35)


def make_pair():
    sent = []
    exchange = SealedExchange(Role.POLICE, 1, sent.append, lambda what: sent.pop(0))
    return exchange, sent


def test_commit_then_reveal_are_sent_and_logged() -> None:
    engine = GameEngine(7, (0, 0), (3, 3), RULES)
    exchange, sent = make_pair()
    exchange.send_sealed(engine, 1, {"type": "move", "move": "E"}, "hi", True)
    assert [m["kind"] for m in sent] == ["commit", "reveal"]
    assert len(exchange.own_records) == 1
    assert exchange.own_records[0]["commit"] == sent[0]["commit"]
    assert "nonce" not in sent[1]  # nonce secret until audit


def test_receive_rejects_desync_and_echoes() -> None:
    exchange, sent = make_pair()
    sent.append({"kind": "reveal", "turn": 1})
    with pytest.raises(GameRuleError, match="expected commit"):
        exchange.receive_sealed(1)
    sent.clear()
    sent.append({"kind": "commit", "turn": 1, "actor": "police", "commit": "x"})
    with pytest.raises(GameRuleError, match="echoed"):
        exchange.receive_sealed(1)


def test_roundtrip_audit_verifies() -> None:
    engine = GameEngine(7, (0, 0), (3, 3), RULES)
    alice, a_sent = make_pair()
    alice.send_sealed(engine, 1, {"type": "move", "move": "E"}, "hi", True)
    bob = SealedExchange(Role.THIEF, 1, a_sent.append, lambda what: a_sent.pop(0))
    payload = bob.receive_sealed(1)
    assert payload["action"] == {"type": "move", "move": "E"}
    assert "verdict" not in payload  # intent stays secret until audit
    bob.apply_revealed_verdicts(alice.own_verdicts())
    assert bob.audit_theirs(alice.own_nonces()) == "Verified OK"
    assert bob.audit_theirs(["deadbeef"]) == "TAMPERED"


def test_perception_snapshot_is_local_truth_only() -> None:
    engine = GameEngine(7, (0, 0), (3, 3), RULES)
    perception = Perception(Role.POLICE, 7)
    seen = []
    perception.on_snapshot = seen.append
    perception.observe(engine, Role.THIEF, "Slipping south past the docks.")
    perception.emit(engine, 1)
    snap = seen[0]
    assert snap["my_cell"] == (0, 0)
    assert "belief" in snap and "barriers" in snap
    assert (3, 3) not in [tuple(v) for k, v in snap.items() if k == "rival_cell"]
    assert "rival_cell" not in snap  # the rival's truth never leaves Perception


def test_duplicate_deliveries_are_skipped_not_fatal() -> None:
    """At-least-once transport: a duplicated commit must never desync."""
    engine = GameEngine(7, (0, 0), (3, 3), RULES)
    alice, a_sent = make_pair()
    alice.send_sealed(engine, 1, {"type": "move", "move": "E"}, "hi", True)
    a_sent.insert(1, dict(a_sent[0]))  # duplicate the commit in-queue
    bob = SealedExchange(Role.THIEF, 1, a_sent.append, lambda what: a_sent.pop(0))
    payload = bob.receive_sealed(1)
    assert payload["action"] == {"type": "move", "move": "E"}


def test_missing_verdicts_in_audit_yield_tampered_not_crash() -> None:
    """A foreign opponent that omits our verdict extension fails the audit
    cleanly (TAMPERED) instead of crashing the peer (rules 32/35)."""
    engine = GameEngine(7, (0, 0), (3, 3), RULES)
    alice, a_sent = make_pair()
    alice.send_sealed(engine, 1, {"type": "move", "move": "E"}, "hi", True)
    bob = SealedExchange(Role.THIEF, 1, a_sent.append, lambda what: a_sent.pop(0))
    bob.receive_sealed(1)
    bob.apply_revealed_verdicts([])  # opponent never disclosed intents
    assert bob.audit_theirs(alice.own_nonces()) == "TAMPERED"
