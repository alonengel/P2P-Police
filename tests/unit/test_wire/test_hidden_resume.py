"""Hidden-wire crash-resume (wire/hidden_resume.py): snapshot round-trip,
the rule-18 guard on the control-channel re-send, integrity failures."""

import json
import random

import pytest

from p2p_police.domain.primitives import Outcome, Role
from p2p_police.infra.mcp_server import PeerInboxes
from p2p_police.peer import resume as base
from p2p_police.shared.config import Config
from p2p_police.strategy.brain_base import RandomBrain
from p2p_police.wire import codec, hidden_resume, hidden_turns
from p2p_police.wire.hidden_runtime import HiddenRuntime
from p2p_police.wire.own_state import OwnState


class StubTransport:
    def __init__(self, sent: list) -> None:
        self.sent = sent

    def send_turn(self, payload, _deadline):
        self.sent.append(("turn", payload))
        return {"accepted": True}

    def send_control(self, payload, _deadline):
        self.sent.append(("control", payload))
        return {"accepted": True}


def _runtime(config_dir, sent: list) -> tuple[HiddenRuntime, PeerInboxes]:
    config = Config.load(config_dir)
    config.private["network"]["wire_shape"] = "reference"
    inboxes = PeerInboxes()
    own = OwnState(Role.POLICE, config.grid_size, config.cop_start, config.rule_set())
    runtime = HiddenRuntime(Role.POLICE, config, own, StubTransport(sent), inboxes,
                            RandomBrain(Role.POLICE, random.Random(3)))
    runtime.opponent_info = {"group_id": "anrbj666"}
    runtime.opponent_group_id = "anrbj666"
    return runtime, inboxes


def _play_three_half_turns(runtime: HiddenRuntime, inboxes: PeerInboxes) -> int:
    hidden_turns.my_half_turn(runtime, 1)
    inboxes.turns.put(codec.build_turn_message(
        2, "thief", "nowhere near", {"3,3": 0.9}, "c" * 64))
    step = hidden_turns.their_half_turn(runtime, 2)
    hidden_turns.my_half_turn(runtime, step + 1)
    return step + 1


def test_snapshot_rearm_restores_the_exact_own_state(config_dir, tmp_path):
    sent: list = []
    runtime, inboxes = _runtime(config_dir, sent)
    last = _play_three_half_turns(runtime, inboxes)
    path = tmp_path / "snap.json"
    base.ResumeRecorder(path, builder=hidden_resume.build_snapshot).checkpoint(
        runtime, last)

    fresh, _ = _runtime(config_dir, [])
    resumed_from = hidden_resume.rearm(fresh, base.load_snapshot(path))
    assert resumed_from == last
    assert fresh.own.cell == runtime.own.cell
    assert fresh.own.turns_completed == runtime.own.turns_completed == 1
    assert fresh.own.next_actor is runtime.own.next_actor
    assert fresh.own.digest() == runtime.own.digest()
    assert fresh.own.scent[Role.POLICE].values() == runtime.own.scent[Role.POLICE].values()
    assert fresh.own.scent[Role.THIEF].values() == runtime.own.scent[Role.THIEF].values()
    assert fresh.exchange.own_records == runtime.exchange.own_records
    assert fresh.exchange.last_sent == runtime.exchange.last_sent
    assert fresh.opponent_group_id == "anrbj666"
    assert fresh.own.outcome is Outcome.ONGOING


def test_rule_18_resume_offer_resends_the_commit_never_a_reveal(config_dir):
    sent: list = []
    runtime, inboxes = _runtime(config_dir, sent)
    _play_three_half_turns(runtime, inboxes)
    nonces = {record["nonce"] for record in runtime.exchange.own_records}
    sent.clear()
    inboxes.controls.put({"kind": "resume_offer", "turn": 2, "group_id": "anrbj666"})
    hidden_resume.handle_controls(runtime)
    assert len(sent) == 1 and sent[0][0] == "turn"
    resent = sent[0][1]
    assert set(resent) == set(codec.REQUIRED_KEYS) | set(codec.OPTIONAL_KEYS)
    blob = json.dumps(resent, ensure_ascii=False)
    assert '"nonce"' not in blob and '"action"' not in blob and '"payload"' not in blob
    assert not any(nonce in blob for nonce in nonces), "rule 18: nonce on a resume re-send"
    hidden_resume.handle_controls(runtime)  # empty inbox: no spurious sends
    assert len(sent) == 1


def test_tampered_snapshot_and_digest_divergence_both_refuse(config_dir, tmp_path):
    sent: list = []
    runtime, inboxes = _runtime(config_dir, sent)
    last = _play_three_half_turns(runtime, inboxes)
    path = tmp_path / "snap.json"
    base.ResumeRecorder(path, builder=hidden_resume.build_snapshot).checkpoint(
        runtime, last)
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["own"]["cell"] = [6, 6]  # forged position; integrity hash now stale
    path.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(base.ResumeError, match="integrity"):
        base.load_snapshot(path)
    doc["integrity"] = base._integrity(doc)  # re-signed forgery: digest guard's turn
    path.write_text(json.dumps(doc), encoding="utf-8")
    fresh, _ = _runtime(config_dir, [])
    with pytest.raises(base.ResumeError, match="digest"):
        hidden_resume.rearm(fresh, base.load_snapshot(path))


def test_attach_wires_recorder_offers_resume_and_discard_cleans(
        config_dir, tmp_path, monkeypatch):
    monkeypatch.setattr(hidden_resume, "snapshot_path", lambda _c: tmp_path / "s.json")
    sent: list = []
    runtime, inboxes = _runtime(config_dir, sent)
    assert hidden_resume.attach(runtime, runtime.config) == 0
    assert isinstance(runtime.resume, base.ResumeRecorder)
    last = _play_three_half_turns(runtime, inboxes)
    runtime.resume.checkpoint(runtime, last)

    fresh, _ = _runtime(config_dir, sent)
    sent.clear()
    assert hidden_resume.attach(fresh, fresh.config, resume=True) == last
    offers = [payload for kind, payload in sent if kind == "control"]
    assert offers == [{"kind": "resume_offer", "turn": last, "group_id": "anrbj666"}]
    hidden_resume.discard(fresh.config)
    assert not (tmp_path / "s.json").exists()
