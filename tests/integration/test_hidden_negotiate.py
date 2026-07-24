"""Reference-v3 negotiate round-trip between two in-process hidden runtimes:
the wire carries the reference's literal {terms, nonce, signature} form with
our declarations alongside — and never the bookletter config_sha256."""

import threading

import pytest
from hidden_helpers import ScriptedBrain, build_runtime, hidden_config

from p2p_police.domain.errors import GameRuleError
from p2p_police.domain.primitives import Role
from p2p_police.infra.mcp_server import PeerInboxes
from p2p_police.wire import terms as wire_terms

REGISTRY_PIN = "229ae6487a418c3fcb6da9be404de2f2533c288ebc228811bff6dedc4164d6f7"


class _Loopback:
    """Agreement-only transport into the rival's inboxes."""

    def __init__(self, them: PeerInboxes, log: list) -> None:
        self._them, self.log = them, log

    def send_agreement(self, payload: dict, _deadline) -> dict:
        self.log.append(payload)
        self._them.agreements.put(payload)
        return {"accepted": True}


def _pair(config):
    police_in, thief_in, log = PeerInboxes(), PeerInboxes(), []
    police = build_runtime(Role.POLICE, config, _Loopback(thief_in, log),
                           police_in, ScriptedBrain(Role.POLICE, []))
    thief = build_runtime(Role.THIEF, config, _Loopback(police_in, log),
                          thief_in, ScriptedBrain(Role.THIEF, []))
    return police, thief, log


def test_round_trip_negotiate_between_two_hidden_runtimes(config_dir):
    config = hidden_config(config_dir)
    police, thief, log = _pair(config)
    results: dict[str, dict] = {}
    threads = [threading.Thread(target=lambda n=n, r=r: results.update({n: r.negotiate()}))
               for n, r in (("police", police), ("thief", thief))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    assert set(results) == {"police", "thief"}, "negotiate deadlocked"
    flat = wire_terms.terms_from_shared(config.shared)
    for message in log:  # both wire payloads carry the reference-v3 shape
        assert message["terms"] == flat
        assert message["signature"] == wire_terms.sign_terms(
            message["terms"], message["nonce"])
        assert message["wire_shape_sha256"] == REGISTRY_PIN
        assert "config_sha256" not in message  # bookletter-v3 property
        # agreed mutual shape: BOTH keys ride top-level, unsigned, spelled so
        assert message["sub_game_number"] == 1
        assert "sub_game_number" not in message["terms"]
        assert "role" not in message["terms"]
    assert {message["role"] for message in log} == {"police", "thief"}
    assert police.opponent_group_id == thief.opponent_group_id == "anrbj666"
    assert len(log) == 2 and results["police"] != results["thief"]  # fresh nonces
    assert results["police"] in log and results["thief"] in log
    assert police.opponent_info == results["police"]


def _foreign_message(shared: dict, group_id: str) -> dict:
    """What an independent reference-form implementation would send."""
    flat = wire_terms.terms_from_shared(shared)
    nonce = "a1a2a3a4b1b2b3b4c1c2c3c4d1d2d3d4"
    return {"terms": flat, "nonce": nonce,
            "signature": wire_terms.sign_terms(flat, nonce),
            "identity": {"group_id": group_id}}


def test_negotiate_accepts_a_minimal_reference_peer(config_dir, shared_terms):
    """No declarations at all (the unmodified reference posture): plays,
    and the rival id is read from inside identity."""
    police, _thief, _log = _pair(hidden_config(config_dir))
    police.inboxes.agreements.put(_foreign_message(shared_terms, "ref-team1"))
    theirs = police.negotiate()
    assert police.opponent_group_id == "ref-team1"
    assert theirs["terms"] == wire_terms.terms_from_shared(shared_terms)


def test_negotiate_refuses_a_same_role_peer(config_dir, shared_terms):
    """A rival declaring OUR role (a mispointed same-role instance) is
    refused loudly; complementary and silent roles keep playing."""
    police, _thief, _log = _pair(hidden_config(config_dir))
    message = _foreign_message(shared_terms, "ref-team1")
    message["role"] = "police"  # equal to ours -> collision
    police.inboxes.agreements.put(message)
    with pytest.raises(GameRuleError, match="complementary"):
        police.negotiate()


def test_negotiate_refuses_a_diverging_term_naming_it(config_dir, shared_terms):
    """A rival playing a different map area is refused pre-game with a
    diagnostic naming the term and BOTH values."""
    police, _thief, _log = _pair(hidden_config(config_dir))
    shared_terms["world"]["map_area"] = "Haifa"
    police.inboxes.agreements.put(_foreign_message(shared_terms, "ref-team1"))
    with pytest.raises(GameRuleError) as caught:
        police.negotiate()
    text = str(caught.value)
    assert "setting" in text and "'New York'" in text and "'Haifa'" in text
