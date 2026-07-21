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


def test_receive_rejects_echoes() -> None:
    """Out-of-order traffic now buffers (see the reorder test); an opponent
    echoing OUR role in a commit is still an instant violation."""
    exchange, sent = make_pair()
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


def test_reordered_pair_is_buffered_not_fatal() -> None:
    """A crash+resume can split a pair: the reveal may arrive while the
    commit is still expected. Buffer-ahead absorbs it; the resent commit
    then unblocks the step and the buffered reveal is served in order."""
    engine = GameEngine(7, (0, 0), (3, 3), RULES)
    alice, a_sent = make_pair()
    alice.send_sealed(engine, 1, {"type": "move", "move": "E"}, "hi", True)
    commit, reveal = a_sent.pop(0), a_sent.pop(0)
    a_sent.extend([reveal, commit, dict(reveal)])  # reveal first + resent copy
    bob = SealedExchange(Role.THIEF, 1, a_sent.append, lambda what: a_sent.pop(0))
    payload = bob.receive_sealed(1)
    assert payload["action"] == {"type": "move", "move": "E"}


def test_flooded_pending_buffer_is_the_true_desync() -> None:
    """Unbounded buffering would let a chatty rival stall us forever - the
    cap converts a flood into a clean protocol violation."""
    junk = [{"kind": "commit", "turn": 90 + n, "actor": "thief"} for n in range(9)]
    bob = SealedExchange(Role.POLICE, 1, junk.append, lambda what: junk.pop(0))
    with pytest.raises(GameRuleError, match="flooded"):
        bob.receive_sealed(1)


def test_junk_deliveries_do_not_reset_the_deadline() -> None:
    """One deadline per EXPECTED message: stale duplicates must burn the
    rival's clock, not refresh ours (anti-stall). The wait callable must
    receive the SAME deadline object across skips within one expectation."""
    engine = GameEngine(7, (0, 0), (3, 3), RULES)
    alice, a_sent = make_pair()
    alice.send_sealed(engine, 1, {"type": "move", "move": "E"}, "hi", True)
    a_sent.insert(0, dict(a_sent[0]))  # stale duplicate ahead of the commit
    seen = []

    def wait(what, deadline=None):
        seen.append(deadline)
        return a_sent.pop(0)

    bob = SealedExchange(Role.THIEF, 1, a_sent.append, wait, turn_timeout=5.0)
    bob.receive_sealed(1)
    # the first copy serves as the commit; its twin is skipped inside the
    # REVEAL expectation - which must keep ONE clock across the skip
    assert seen[1] is not None and seen[1] is seen[2]
    assert seen[0] is not seen[1]  # each expectation gets a fresh deadline
