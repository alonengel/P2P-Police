"""Slow integration test (PRD 02): a real FastMCP server on an ephemeral
localhost port receives payloads sent through McpTransport, intact, into the
peer inboxes. This keeps the transport modules inside the coverage gate."""

import socket

import pytest

from p2p_police.infra.mcp_client import McpTransport
from p2p_police.infra.mcp_server import (
    PeerInboxes,
    PortBusyError,
    build_peer_server,
    ensure_port_free,
    start_peer_server,
)
from p2p_police.peer.deadline import Deadline

pytestmark = pytest.mark.slow


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


@pytest.fixture(scope="module")
def live_peer() -> tuple[PeerInboxes, str]:
    inboxes = PeerInboxes()
    port = free_port()
    start_peer_server(build_peer_server(inboxes), port)
    url = f"http://127.0.0.1:{port}/mcp"
    transport = McpTransport(url, retry_backoff_sec=0.2)
    # retry-until-up doubles as the server-ready wait
    transport.send_control({"kind": "ping"}, Deadline(15))
    return inboxes, url


def test_turn_payload_arrives_intact(live_peer: tuple[PeerInboxes, str]) -> None:
    inboxes, url = live_peer
    transport = McpTransport(url, retry_backoff_sec=0.2)
    payload = {"turn": 3, "actor": "police", "action": {"type": "move", "move": "E"}}
    ack = transport.send_turn(payload, Deadline(10))
    assert ack == {"accepted": True}
    assert inboxes.turns.get(timeout=5) == payload


def test_agreement_and_audit_route_to_their_inboxes(live_peer: tuple[PeerInboxes, str]) -> None:
    inboxes, url = live_peer
    transport = McpTransport(url, retry_backoff_sec=0.2)
    transport.send_agreement({"config_sha256": "abc"}, Deadline(10))
    transport.send_audit({"digest": "xyz"}, Deadline(10))
    assert inboxes.agreements.get(timeout=5)["config_sha256"] == "abc"
    assert inboxes.audits.get(timeout=5)["digest"] == "xyz"


def test_second_bind_on_busy_port_fails_fast(live_peer: tuple[PeerInboxes, str]) -> None:
    _, url = live_peer
    busy_port = int(url.rsplit(":", 1)[1].split("/")[0])
    with pytest.raises(PortBusyError, match="game.toml"):
        ensure_port_free(busy_port)


def test_settled_peer_refuses_all_four_tools_over_real_http() -> None:
    """Post-settlement gate through the real FastMCP doors: a settled peer
    answers {"accepted": false, "reason": "sub-game settled"} instead of
    enqueueing — its dying instance can never swallow the rival's next
    greeting (own server: fresh port, never the shared module fixture)."""
    inboxes = PeerInboxes()
    port = free_port()
    start_peer_server(build_peer_server(inboxes, name="settled_peer"), port)
    transport = McpTransport(f"http://127.0.0.1:{port}/mcp", retry_backoff_sec=0.2)
    assert transport.send_control({"kind": "ping"}, Deadline(15)) == {"accepted": True}
    inboxes.settled = True
    refusal = {"accepted": False, "reason": "sub-game settled"}
    assert transport.send_agreement({"terms": {}}, Deadline(10)) == refusal
    assert transport.send_turn({"step": 9}, Deadline(10)) == refusal
    assert transport.send_audit({"records": []}, Deadline(10)) == refusal
    assert transport.send_control({"kind": "late"}, Deadline(10)) == refusal
    assert inboxes.agreements.empty() and inboxes.turns.empty()
    assert inboxes.audits.empty() and inboxes.controls.qsize() == 1  # ping only


def test_unreachable_opponent_expires_the_deadline() -> None:
    dead_url = f"http://127.0.0.1:{free_port()}/mcp"
    transport = McpTransport(dead_url, retry_backoff_sec=0.1, sleep=lambda _s: None)
    from p2p_police.peer.deadline import DeadlineExpiredError

    with pytest.raises(DeadlineExpiredError):
        transport.send_turn({"turn": 1}, Deadline(0.5))
