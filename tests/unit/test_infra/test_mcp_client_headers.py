"""Outbound extra headers, config-declared per pairing.

League 2026-08-16 (best2934): their network began blocking cloudflared's
port outright, their door moved behind ngrok's free tier, and that tier
answers any request WITHOUT `ngrok-skip-browser-warning` with an HTML
interstitial carrying HTTP 200 â€” a naive readiness check passes and the
JSON parse then dies mid-handshake. The transport must therefore build its
client with the config-declared headers when any are given, and exactly as
before when none are.
"""

from p2p_police.infra import mcp_client
from p2p_police.infra.mcp_client import McpTransport


def test_extra_headers_ride_an_explicit_http_transport(monkeypatch):
    captured = {}

    class FakeHttp:
        def __init__(self, url, headers=None):
            captured["url"], captured["headers"] = url, headers

    monkeypatch.setattr(mcp_client, "StreamableHttpTransport", FakeHttp)
    monkeypatch.setattr(mcp_client, "Client", lambda target: ("client", target))
    transport = McpTransport(
        "https://door.test/mcp", 1.0,
        extra_headers={"ngrok-skip-browser-warning": "1"})
    _, target = transport._build_client()
    assert isinstance(target, FakeHttp)
    assert captured == {"url": "https://door.test/mcp",
                        "headers": {"ngrok-skip-browser-warning": "1"}}


def test_no_headers_keeps_the_plain_url_client(monkeypatch):
    monkeypatch.setattr(mcp_client, "Client", lambda target: ("client", target))
    transport = McpTransport("https://door.test/mcp", 1.0)
    _, target = transport._build_client()
    assert target == "https://door.test/mcp"
