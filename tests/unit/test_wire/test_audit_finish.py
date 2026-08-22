"""finish(): the three-tier audit verdict + the reference audit envelope.

2026-07-24 live findings, both directions of the same mutual-audit failure:
our verdict must not call a commit-clean foreign-schema rival TAMPERED, and
our own audit message must be the reference AuditPayload envelope EXACTLY —
the counterparty's parser rejected our envelope for lacking `sender`, and
the reference from_dict (a dataclass cls(**data)) rejects ANY extra key."""

from dataclasses import dataclass
from types import SimpleNamespace

import pytest
from test_audit_foreign import (
    exchange_with_live_commits,
    reference_spec_record,
    rival_walk,
)

from p2p_police.domain.primitives import Outcome, Role
from p2p_police.wire import audit, hidden_turns

SHARED = {"board_and_agents": {"grid_size": 7, "cop_start": [0, 0],
                               "thief_start": [3, 3]}}


@dataclass
class ReferenceAuditPayload:
    """The reference protocol's exact AuditPayload field set (strict parse)."""

    sender: str
    records: list
    result_claim: str

    @classmethod
    def from_dict(cls, data: dict) -> "ReferenceAuditPayload":
        return cls(**data)


def stub_runtime(exchange, audit_message: dict, sent: list) -> SimpleNamespace:
    own = SimpleNamespace(digest=lambda: "ab" * 32, outcome=Outcome.SURVIVAL,
                          turns_completed=35)
    return SimpleNamespace(
        role=Role.POLICE, own=own, exchange=exchange,
        config=SimpleNamespace(turn_timeout_seconds=5, shared=SHARED),
        transport=SimpleNamespace(send_audit=lambda payload, _d: sent.append(payload)),
        inboxes=SimpleNamespace(audits=None),
        _wait=lambda _inbox, _what: audit_message,
    )


def test_foreign_schema_rival_half_renders_verified_ok() -> None:
    """Commit-clean reference reveals: audit Verified OK, digest tier
    not-comparable (None) — the exact case tonight's games mis-rendered."""
    walk = rival_walk()
    exchange = exchange_with_live_commits(walk)
    theirs = {"sender": "thief", "records": [reference_spec_record(), *walk],
              "result_claim": "survival"}
    report = hidden_turns.finish(stub_runtime(exchange, theirs, []))
    assert report["audit"] == "Verified OK"
    assert report["digest_match"] is None
    assert report["end_state_digest"] == "ab" * 32  # our own construction stands


def test_forged_foreign_reveal_still_renders_tampered() -> None:
    walk = rival_walk()
    exchange = exchange_with_live_commits(walk)
    forged = dict(walk[0], payload=dict(walk[0]["payload"], position=[6, 6]))
    theirs = {"sender": "thief", "records": [forged, *walk[1:]],
              "result_claim": "survival"}
    report = hidden_turns.finish(stub_runtime(exchange, theirs, []))
    assert report["audit"] == "TAMPERED"
    assert report["digest_match"] is False


def test_summary_declares_own_token_usage_from_the_meter() -> None:
    """The window summary carries OUR real spend (rule 50): the talk meter
    when a chain exists, an honest 0 when none does — the series report's
    own-side column reads this, never a constant (najamjad diff 2026-08-22:
    a summary without the key coerced every own row to an unread 0)."""
    walk = rival_walk()
    exchange = exchange_with_live_commits(walk)
    theirs = {"sender": "thief", "records": [reference_spec_record(), *walk],
              "result_claim": "survival"}
    metered = stub_runtime(exchange, theirs, [])
    metered.talk = SimpleNamespace(meter=SimpleNamespace(total=42))
    assert hidden_turns.finish(metered)["tokens_total"] == 42
    bare = hidden_turns.finish(stub_runtime(exchange, theirs, []))
    assert bare["tokens_total"] == 0


def test_our_audit_message_is_the_reference_envelope_exactly() -> None:
    walk = rival_walk()
    exchange = exchange_with_live_commits(walk)
    exchange.seal_step("d" * 64, 1, {"type": "move", "move": "E"}, "hint", True)
    sent: list = []
    theirs = {"sender": "thief", "records": [reference_spec_record(), *walk],
              "result_claim": "survival"}
    hidden_turns.finish(stub_runtime(exchange, theirs, sent))
    assert len(sent) == 1
    message = sent[0]
    assert set(message) == {"sender", "records", "result_claim"}
    assert message["sender"] == "police"
    assert message["records"] == exchange.own_records
    parsed = ReferenceAuditPayload.from_dict(message)  # strict parse accepts
    assert parsed.sender == "police" and parsed.result_claim == "survival"


def test_reference_parser_rejects_extra_envelope_keys() -> None:
    """Why 'exactly': the reference from_dict is cls(**data) — one extra key
    of ours voids the whole audit on the counterparty's side."""
    with pytest.raises(TypeError):
        ReferenceAuditPayload.from_dict(
            {"sender": "police", "records": [], "result_claim": "survival",
             "state_digest": "ab" * 32})


def test_build_audit_payload_carries_the_sender_role() -> None:
    exchange = exchange_with_live_commits(rival_walk())
    for role in (Role.POLICE, Role.THIEF):
        message = audit.build_audit_payload(exchange, role.value, "capture")
        assert message["sender"] == role.value
        assert set(message) == {"sender", "records", "result_claim"}
