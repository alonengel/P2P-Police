"""Agreement re-push (fake clock, no sleeps): a greeting swallowed by the
rival's dying previous-sub-game peer gets more chances — negotiate re-sends
the SAME payload every [network] agreement_repush_sec until the rival's
agreement arrives or the turn deadline lapses. Bystander tolerance: a
pairing-class refusal (wrong window / role-equal) is logged on the record
and the wait continues; genuine violations stay first-offense fatal."""

import json
import logging

import pytest
from hidden_helpers import ScriptedBrain, build_runtime, hidden_config

from p2p_police.domain.errors import GameRuleError
from p2p_police.domain.primitives import Role
from p2p_police.infra.mcp_server import PeerInboxes
from p2p_police.peer.deadline import DeadlineExpiredError
from p2p_police.wire import terms as wire_terms

REPUSH_LOGGER = "p2p_police.wire.repush"


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


def test_wrong_window_bystander_is_logged_and_the_real_counterpart_pairs(
        config_dir, shared_terms, caplog):
    """A leftover rival instance greeting the WRONG sub-game window arrives
    first: the refusal is logged on the record with the differing values and
    the wait continues until the real counterpart pairs (never a loss)."""
    runtime, transport = _runtime(config_dir, shared_terms, answer_on=2)
    runtime.inboxes.agreements.put(
        dict(_rival_answer(shared_terms), sub_game_number=5))
    with caplog.at_level(logging.INFO, logger=REPUSH_LOGGER):
        theirs = runtime.negotiate()
    assert theirs["identity"]["group_id"] == "ref-team1"
    assert runtime.opponent_group_id == "ref-team1"  # the REAL one paired
    assert len(transport.sent) == 2  # refused once, re-pushed, then paired
    assert "agreement refused: wrong game, not you" in caplog.text
    assert "sub_game_number" in caplog.text  # the differing values are named
    assert "mine=1" in caplog.text and "theirs=5" in caplog.text


def test_role_equal_bystander_is_logged_and_the_real_counterpart_pairs(
        config_dir, shared_terms, caplog):
    """A same-role instance (or our own echo) greeting us is a pairing
    problem, not a violation: logged, tolerated, and the game proceeds."""
    runtime, transport = _runtime(config_dir, shared_terms, answer_on=2)
    runtime.inboxes.agreements.put(dict(_rival_answer(shared_terms), role="police"))
    with caplog.at_level(logging.INFO, logger=REPUSH_LOGGER):
        theirs = runtime.negotiate()
    assert theirs["role"] == "thief"  # the complementary counterpart won
    assert "agreement refused: wrong game, not you" in caplog.text
    assert "complementary" in caplog.text


@pytest.mark.parametrize("poison", [
    lambda m: m.update(signature="f" * 64),                      # bad signature
    lambda m: m.update(scent_model_sha256="b" * 64),             # scent-lock drift
    lambda m: m["terms"].update(setting="Springfield") or m.update(
        signature=wire_terms.sign_terms(m["terms"], m["nonce"])),  # terms drift
])
def test_genuine_violations_stay_first_offense_fatal(config_dir, shared_terms, poison):
    """Terms drift / bad signature / scent-lock mismatch are violations by
    a REAL counterpart: the first offense still ends the handshake."""
    runtime, _transport = _runtime(config_dir, shared_terms, answer_on=0)
    message = _rival_answer(shared_terms)
    poison(message)
    runtime.inboxes.agreements.put(message)
    with pytest.raises(GameRuleError) as caught:
        runtime.negotiate()
    assert not isinstance(caught.value, wire_terms.PairingRefusalError)
    assert not isinstance(caught.value, DeadlineExpiredError)


def test_deadline_bounds_an_endless_bystander_stream(config_dir, shared_terms, caplog):
    """A stream of wrong-window greetings arriving forever must not hold the
    wait open: every one is logged and the ONE overall deadline still ends
    the negotiate loudly."""
    runtime, transport = _runtime(config_dir, shared_terms, answer_on=0, timeout=9.0)
    bystander = json.dumps(dict(_rival_answer(shared_terms), sub_game_number=4))
    original_send = transport.send_agreement

    def send_and_heckle(payload: dict, deadline) -> dict:
        runtime.inboxes.agreements.put(json.loads(bystander))  # fresh copy each time
        return original_send(payload, deadline)

    transport.send_agreement = send_and_heckle
    with caplog.at_level(logging.INFO, logger=REPUSH_LOGGER), \
            pytest.raises(DeadlineExpiredError, match="opponent agreement"):
        runtime.negotiate()
    assert len(transport.sent) >= 2  # kept trying, never looped silently
    assert caplog.text.count("agreement refused: wrong game, not you") >= 2
