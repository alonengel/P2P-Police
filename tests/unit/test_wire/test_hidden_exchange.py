"""HiddenExchange: commit-only live wire over the hardened receiver."""

import pytest

from p2p_police.domain import crypto
from p2p_police.domain.errors import GameRuleError
from p2p_police.domain.primitives import Role
from p2p_police.wire.hidden_exchange import HiddenExchange


def build(feed: list[dict], sent: list | None = None) -> HiddenExchange:
    """Exchange whose wait pops scripted (pre-normalized) messages."""

    def wait(_what, _deadline=None):
        assert feed, "test feed exhausted while the exchange still waits"
        message = feed.pop(0)
        return {**message, "kind": "turn", "turn": int(message.get("step", -1))}

    return HiddenExchange(Role.POLICE, 1, (sent if sent is not None else []).append,
                          wait, turn_timeout=5)


def turn(step, sender="thief", commit="c" * 64, **extra):
    return {"step": step, "sender": sender, "commit": commit, **extra}


def _sealed(step, role="thief"):
    payload = crypto.build_step_payload(step, role, 1, "d" * 64,
                                        {"type": "move", "move": "STAY"}, "h", True)
    nonce = crypto.new_nonce()
    return {"payload": payload, "nonce": nonce, "commit": crypto.commit_hash(payload, nonce)}


def test_seal_step_returns_commit_and_sends_nothing():
    sent = []
    exchange = build([], sent)
    commit = exchange.seal_step("d" * 64, 1, {"type": "move", "move": "E"}, "hi", True)
    record = exchange.own_records[0]
    assert crypto.verify_commit(record["payload"], record["nonce"], commit)
    assert sent == []  # sealing is local; the runtime sends the TurnMessage


def test_receive_stores_the_live_commit():
    exchange = build([turn(1, commit="a" * 64)])
    message = exchange.receive_turn(1)
    assert message["step"] == 1
    assert "kind" not in message
    assert exchange.their_records == [{"commit": "a" * 64}]


def test_duplicate_delivery_dropped():
    exchange = build([turn(1), turn(1), turn(2, commit="b" * 64)])
    exchange.receive_turn(1)
    assert exchange.receive_turn(2)["commit"] == "b" * 64


def test_out_of_order_messages_buffered():
    exchange = build([turn(2, commit="b" * 64), turn(1, commit="a" * 64)])
    assert exchange.receive_turn(1)["commit"] == "a" * 64
    assert exchange.receive_turn(2)["commit"] == "b" * 64


def test_flood_raises_protocol_desync():
    exchange = build([turn(100 + i) for i in range(10)])
    with pytest.raises(GameRuleError):
        exchange.receive_turn(1)


def test_role_echo_rejected():
    exchange = build([turn(1, sender="police")])
    with pytest.raises(GameRuleError):
        exchange.receive_turn(1)


def test_missing_commit_rejected():
    exchange = build([{"step": 1, "sender": "thief"}])
    with pytest.raises(GameRuleError):
        exchange.receive_turn(1)


def test_audit_reveals_verify_against_live_commits():
    records = [_sealed(1), _sealed(2)]
    exchange = build([turn(1, commit=records[0]["commit"]),
                      turn(2, commit=records[1]["commit"])])
    exchange.receive_turn(1)
    exchange.receive_turn(2)
    assert exchange.audit_reveals(records) == "Verified OK"
    assert exchange.their_records[0]["payload"] == records[0]["payload"]
    assert exchange.their_records[1]["nonce"] == records[1]["nonce"]


def test_audit_rejects_rewritten_history():
    record = _sealed(1)
    exchange = build([turn(1, commit=record["commit"])])
    exchange.receive_turn(1)
    forged = dict(record, payload=dict(record["payload"], hint="rewritten"))
    assert exchange.audit_reveals([forged]) == "TAMPERED"


def test_audit_rejects_a_swapped_commit():
    record = _sealed(1)
    exchange = build([turn(1, commit="e" * 64)])  # live commit differs
    exchange.receive_turn(1)
    assert exchange.audit_reveals([record]) == "TAMPERED"


def test_audit_rejects_count_mismatch_and_malformed_material():
    record = _sealed(1)
    exchange = build([turn(1, commit=record["commit"])])
    exchange.receive_turn(1)
    assert exchange.audit_reveals([]) == "TAMPERED"
    assert exchange.audit_reveals([{"commit": record["commit"]}]) == "TAMPERED"
