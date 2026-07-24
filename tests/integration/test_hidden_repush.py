"""Agreement re-push (fake clock, no sleeps): a greeting swallowed by the
rival's dying previous-sub-game peer gets more chances — negotiate re-sends
the SAME payload every [network] agreement_repush_sec until the rival's
agreement arrives or the turn deadline lapses."""

import pytest
from hidden_helpers import ScriptedBrain, build_runtime, hidden_config

from p2p_police.domain.primitives import Role
from p2p_police.infra.mcp_server import PeerInboxes
from p2p_police.peer.deadline import DeadlineExpiredError
from p2p_police.wire import terms as wire_terms


class TickClock:
    """Monotonic fake advancing a fixed step per read — tests never sleep."""

    def __init__(self, step: float = 0.5) -> None:
        self.now, self.step = 0.0, step

    def __call__(self) -> float:
        self.now += self.step
        return self.now


class SwallowingTransport:
    """The rival's dying previous peer: acks every agreement into the void;
    only the `answer_on`-th send finally reaches the real peer, which then
    answers into OUR agreements inbox."""

    def __init__(self, me: PeerInboxes, answer: dict, answer_on: int) -> None:
        self.me, self.answer, self.answer_on = me, answer, answer_on
        self.sent: list[dict] = []

    def send_agreement(self, payload: dict, _deadline) -> dict:
        self.sent.append(payload)
        if len(self.sent) == self.answer_on:
            self.me.agreements.put(self.answer)
        return {"accepted": True}


def _rival_answer(shared: dict) -> dict:
    flat = wire_terms.terms_from_shared(shared)
    nonce = "a1a2a3a4b1b2b3b4c1c2c3c4d1d2d3d4"
    return {"terms": flat, "nonce": nonce,
            "signature": wire_terms.sign_terms(flat, nonce),
            "identity": {"group_id": "ref-team1"}, "role": "thief"}


def _runtime(config_dir, shared_terms, answer_on: int, timeout: float = 600.0):
    config = hidden_config(config_dir)
    config.private["network"]["turn_timeout_seconds"] = timeout
    config.private["network"]["agreement_repush_sec"] = 2.0
    inboxes = PeerInboxes()
    transport = SwallowingTransport(inboxes, _rival_answer(shared_terms), answer_on)
    runtime = build_runtime(Role.POLICE, config, transport, inboxes,
                            ScriptedBrain(Role.POLICE, []))
    runtime.clock = TickClock()
    return runtime, transport


def test_agreement_re_sent_until_theirs_arrives_then_stops(config_dir, shared_terms):
    runtime, transport = _runtime(config_dir, shared_terms, answer_on=3)
    theirs = runtime.negotiate()
    assert len(transport.sent) == 3  # initial push + two re-pushes, then done
    assert transport.sent[0] == transport.sent[1] == transport.sent[2]
    assert theirs["identity"]["group_id"] == "ref-team1"
    assert runtime.opponent_group_id == "ref-team1"


def test_repush_payload_carries_the_agreed_top_level_keys(config_dir, shared_terms):
    """Every (re-)pushed negotiate message is the SAME dict carrying the
    mutual wire shape: `sub_game_number` and `role` spelled exactly, at the
    TOP level, unsigned, beside identity/nonce/terms/signature."""
    runtime, transport = _runtime(config_dir, shared_terms, answer_on=2)
    runtime.negotiate()
    for message in transport.sent:
        assert message["sub_game_number"] == 1
        assert message["role"] == "police"
        assert "sub_game_number" not in message["terms"]
        assert "role" not in message["terms"]
        assert {"terms", "nonce", "signature", "identity"} <= set(message)


def test_immediate_agreement_needs_a_single_push(config_dir, shared_terms):
    runtime, transport = _runtime(config_dir, shared_terms, answer_on=1)
    runtime.negotiate()
    assert len(transport.sent) == 1  # no gratuitous repeats


def test_deadline_still_bounds_the_repush_loop(config_dir, shared_terms):
    """No rival ever answers: the turn deadline lapses and negotiate fails
    loudly after having kept trying (never a silent infinite loop)."""
    runtime, transport = _runtime(config_dir, shared_terms,
                                  answer_on=0, timeout=9.0)
    with pytest.raises(DeadlineExpiredError, match="opponent agreement"):
        runtime.negotiate()
    assert len(transport.sent) >= 2  # it re-pushed until the deadline judged
