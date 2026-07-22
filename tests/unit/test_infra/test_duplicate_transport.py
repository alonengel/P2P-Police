"""DuplicatingTransport: every turn push goes out twice; evidence is real."""

import json
from pathlib import Path

from p2p_police.infra.duplicate_transport import (
    DuplicatingTransport,
    JsonlEvidence,
    maybe_duplicate_outbound,
)
from p2p_police.shared.config import Config


class FakeInner:
    """Recording stand-in for McpTransport (same four-call surface)."""

    opponent_url = "http://peer.example/mcp"

    def __init__(self, fail_duplicates: bool = False) -> None:
        self.turns: list = []
        self.agreements: list = []
        self.audits: list = []
        self.closed = False
        self._fail_duplicates = fail_duplicates

    def send_agreement(self, payload: dict, deadline) -> dict:
        self.agreements.append(payload)
        return {"accepted": True}

    def send_turn(self, payload: dict, deadline) -> dict:
        self.turns.append(payload)
        if self._fail_duplicates and self.turns.count(payload) > 1:
            raise ConnectionError("duplicate refused by rival")
        return {"accepted": True}

    def send_audit(self, payload: dict, deadline) -> dict:
        self.audits.append(payload)
        return {"accepted": True}

    def close(self) -> None:
        self.closed = True


def read_lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_every_turn_push_is_sent_twice_and_recorded(tmp_path: Path) -> None:
    path = tmp_path / "evidence.jsonl"
    inner = FakeInner()
    wrapper = DuplicatingTransport(inner, JsonlEvidence(path))
    ack = wrapper.send_turn({"kind": "commit", "turn": 3}, None)
    wrapper.send_turn({"kind": "reveal", "turn": 3}, None)
    assert ack == {"accepted": True}
    assert len(inner.turns) == 4 and wrapper.duplicated == 2
    lines = read_lines(path)
    assert [line["stage"] for line in lines] == ["duplicate", "duplicate"]
    assert lines[0]["message_kind"] == "commit" and lines[0]["turn"] == 3
    assert lines[0]["target"] == "http://peer.example/mcp"
    assert lines[0]["duplicate_ack_ok"] is True


def test_hidden_wire_turnmessages_record_their_step(tmp_path: Path) -> None:
    wrapper = DuplicatingTransport(FakeInner(), JsonlEvidence(tmp_path / "e.jsonl"))
    wrapper.send_turn({"step": 5, "commit": "aa"}, None)  # hidden TurnMessage shape
    (line,) = read_lines(tmp_path / "e.jsonl")
    assert line["message_kind"] == "turn_message" and line["turn"] == 5


def test_duplicate_failure_never_kills_the_original_ack(tmp_path: Path) -> None:
    wrapper = DuplicatingTransport(FakeInner(fail_duplicates=True),
                                   JsonlEvidence(tmp_path / "e.jsonl"))
    assert wrapper.send_turn({"kind": "commit", "turn": 1}, None) == {"accepted": True}
    (line,) = read_lines(tmp_path / "e.jsonl")
    assert line["duplicate_ack_ok"] is False and "ConnectionError" in line["error"]


def test_agreement_audit_and_close_pass_through_once(tmp_path: Path) -> None:
    inner = FakeInner()
    wrapper = DuplicatingTransport(inner, JsonlEvidence(tmp_path / "e.jsonl"))
    wrapper.send_agreement({"a": 1}, None)
    wrapper.send_audit({"b": 2}, None)
    wrapper.close()
    assert len(inner.agreements) == 1 and len(inner.audits) == 1
    assert inner.closed and wrapper.duplicated == 0


def test_maybe_wrap_reads_the_chaos_knob(config_dir: Path) -> None:
    config = Config.load(config_dir)
    inner = FakeInner()
    assert maybe_duplicate_outbound(inner, config) is inner  # knob off: untouched
    config.private["chaos"] = {
        "duplicate_outbound_sends": True,
        "duplicate_outbound_evidence_dir": str(config_dir / "evidence"),
    }
    wrapped = maybe_duplicate_outbound(inner, config)
    assert isinstance(wrapped, DuplicatingTransport)
