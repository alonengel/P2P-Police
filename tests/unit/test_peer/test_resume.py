"""Crash-resume (E6): snapshot fidelity, mid-game resume, dedup interplay,
tampered-snapshot rejection. In-process loopback pairs (test_runtime pattern)."""

import json
import queue
import threading
from pathlib import Path

import pytest
from test_runtime import LoopbackTransport, build_runtime

from p2p_police.domain import crypto
from p2p_police.domain.primitives import Outcome, Role
from p2p_police.infra.mcp_server import PeerInboxes
from p2p_police.peer import resume as resume_mod
from p2p_police.peer.resume import ResumeError, ResumeRecorder
from p2p_police.peer.sealing import SealedExchange
from p2p_police.shared.config import Config

ME = Role.POLICE  # this repo's live role (twin repo: thief)


class ControlLoopback(LoopbackTransport):
    """Loopback that also routes the control channel (resume_offer)."""

    def send_control(self, payload: dict, deadline) -> dict:
        self._them.controls.put(payload)
        return {"accepted": True}


def _crash_and_resume(config: Config, snap: Path, crash_after: int) -> tuple[dict, dict]:
    """Play to `crash_after` half-turns, discard the runtime, resume, finish."""
    my_in, stub_in = PeerInboxes(), PeerInboxes()
    stub = build_runtime(ME.rival, config, ControlLoopback(my_in), stub_in, 99)
    mine = build_runtime(ME, config, ControlLoopback(stub_in), my_in, 7)
    mine.resume = ResumeRecorder(snap)
    stub_box: dict = {}
    stub_thread = threading.Thread(target=lambda: stub_box.update(stub.play()), daemon=True)
    stub_thread.start()
    mine.negotiate()
    turn = 0
    while mine.engine.outcome is Outcome.ONGOING and turn < crash_after:
        turn += 1
        if mine.engine.next_actor is mine.role:
            mine._my_half_turn(turn)
        else:
            mine._their_half_turn(turn)
        mine.resume.checkpoint(mine, turn)
    del mine  # the crash: runtime object and its in-memory state are gone

    mine2 = build_runtime(ME, config, ControlLoopback(stub_in), my_in, 7)
    snapshot = resume_mod.load_snapshot(snap)
    start_turn = resume_mod.rearm(mine2, snapshot)
    assert start_turn == turn
    mine2.resume = ResumeRecorder(snap)
    resume_mod.offer_resume(mine2, start_turn)
    report = mine2.play(resume_from=start_turn)
    stub_thread.join(timeout=30)
    assert stub_box, "stub runtime deadlocked"
    return report, stub_box


@pytest.mark.parametrize("crash_after", [1, 2, 5])
def test_resume_mid_game_completes_with_audits_green(
    config_dir: Path, tmp_path: Path, crash_after: int
) -> None:
    config = Config.load(config_dir)
    report, stub_report = _crash_and_resume(config, tmp_path / "snap.json", crash_after)
    assert report["outcome"] in ("capture", "survival")
    assert report["outcome"] == stub_report["outcome"]
    assert report["digest_match"] and stub_report["digest_match"]
    assert report["end_state_digest"] == stub_report["end_state_digest"]
    # the commit-reveal chain survived the crash on BOTH sides of the audit
    assert report["audit"] == "Verified OK" and stub_report["audit"] == "Verified OK"


def test_snapshot_roundtrip_restores_engine_and_exchange(
    config_dir: Path, tmp_path: Path
) -> None:
    config, snap = Config.load(config_dir), tmp_path / "snap.json"
    report, _ = _crash_and_resume(config, snap, 3)
    # the FINAL checkpoint (written by play's loop) replays to the end state
    snapshot = resume_mod.load_snapshot(snap)
    fresh = build_runtime(ME, config, ControlLoopback(PeerInboxes()), PeerInboxes(), 7)
    resume_mod.rearm(fresh, snapshot)
    from p2p_police.domain import protocol

    assert protocol.end_state_digest(fresh.engine) == report["end_state_digest"]
    own, their, consumed = fresh.exchange.export_state()
    assert own == snapshot["own_records"] and their == snapshot["their_records"]
    assert [record["nonce"] for record in own] == [r["nonce"] for r in snapshot["own_records"]]
    assert consumed == snapshot["consumed"]
    assert fresh.opponent_group_id == snapshot["opponent_agreement"]["group_id"]


def test_tampered_snapshot_rejected(config_dir: Path, tmp_path: Path) -> None:
    config, snap = Config.load(config_dir), tmp_path / "snap.json"
    runtime = build_runtime(ME, config, ControlLoopback(PeerInboxes()), PeerInboxes(), 7)
    runtime.opponent_info = {"group_id": "anrbj666"}
    ResumeRecorder(snap).checkpoint(runtime, 0)
    resume_mod.load_snapshot(snap)  # pristine snapshot loads fine
    doc = json.loads(snap.read_text(encoding="utf-8"))
    doc["turns_completed"] = 99  # the tamper
    snap.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(ResumeError, match="integrity"):
        resume_mod.load_snapshot(snap)
    with pytest.raises(ResumeError, match="no resume snapshot"):
        resume_mod.load_snapshot(tmp_path / "missing.json")


def _sealed(step: int, role: str, nonce: str = "aa") -> dict:
    payload = crypto.build_step_payload(step, role, 1, "digest", {"type": "move", "move": "N"},
                                        "hint", True)
    return {"payload": payload, "nonce": nonce, "commit": crypto.commit_hash(payload, nonce)}


def test_restored_dedup_absorbs_redelivered_duplicates() -> None:
    """A resumed peer re-receives an already-consumed pair and survives."""
    rival = ME.rival.value
    old, new = _sealed(1, rival), _sealed(2, rival)
    incoming = queue.Queue()
    for record in (old, new):  # the duplicate redelivery, then the real next pair
        step = record["payload"]["step"]
        incoming.put({"kind": "commit", "turn": step, "actor": rival,
                      "commit": record["commit"]})
        incoming.put({"kind": "reveal", "turn": step, "actor": rival,
                      "payload": record["payload"]})
    exchange = SealedExchange(ME, 1, lambda msg: None, lambda what: incoming.get_nowait())
    exchange.restore_state([], [{"payload": old["payload"], "commit": old["commit"]}],
                           [["commit", 1], ["reveal", 1]])
    payload = exchange.receive_sealed(2)  # skips both step-1 duplicates
    assert payload["step"] == 2
    assert len(exchange.their_records) == 2


def test_resume_offer_triggers_resend_of_last_sealed_pair(config_dir: Path) -> None:
    config = Config.load(config_dir)
    inboxes = PeerInboxes()
    spy_in = PeerInboxes()  # capture what we send by looping back to a spy inbox
    runtime = build_runtime(ME, config, ControlLoopback(spy_in), inboxes, 7)
    record = _sealed(4, ME.value, nonce="bb")
    runtime.exchange.restore_state([record], [], [])
    inboxes.controls.put({"kind": "resume_offer", "turn": 4, "group_id": "anrbj666"})
    resume_mod.handle_controls(runtime)
    commit_msg, reveal_msg = spy_in.turns.get_nowait(), spy_in.turns.get_nowait()
    assert commit_msg == {"kind": "commit", "turn": 4, "actor": ME.value,
                          "commit": record["commit"]}
    assert reveal_msg["kind"] == "reveal" and "verdict" not in reveal_msg["payload"]
    assert spy_in.turns.empty() and inboxes.controls.empty()
    resume_mod.handle_controls(runtime)  # no pending offers -> no sends
    assert spy_in.turns.empty()


def test_recorder_is_on_by_default_and_config_gated(
    config_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)  # snapshot_path is results/local/-relative
    config = Config.load(config_dir)
    assert config.resume_enabled()  # ON by default: no [resume] table needed
    runtime = build_runtime(ME, config, ControlLoopback(PeerInboxes()), PeerInboxes(), 7)
    assert resume_mod.attach(runtime, config, resume=False) == 0
    assert isinstance(runtime.resume, ResumeRecorder)
    assert "results" in str(runtime.resume.path.parent) and "local" in str(runtime.resume.path)
    config.private["resume"] = {"enabled": False}
    runtime2 = build_runtime(ME, config, ControlLoopback(PeerInboxes()), PeerInboxes(), 7)
    resume_mod.attach(runtime2, config, resume=False)
    assert isinstance(runtime2.resume, resume_mod.NullResume)
