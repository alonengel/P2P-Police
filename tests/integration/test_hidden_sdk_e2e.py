"""run_peer on the hidden wire, end to end over real HTTP MCP: the SDK's
wire-shape seam must route to the HiddenRuntime, arm the watchdog with the
own-state provider, and emit the four artifacts with the hidden log marker
- all through the same single entry the bookletter path uses."""

import json
import socket
import threading

import pytest
from hidden_helpers import ScriptedBrain, build_runtime

from p2p_police.domain.primitives import Role
from p2p_police.infra.mcp_client import McpTransport
from p2p_police.infra.mcp_server import PeerInboxes, build_peer_server, start_peer_server
from p2p_police.sdk.sdk import SimulationSdk
from p2p_police.shared.config import Config

pytestmark = pytest.mark.slow


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def test_run_peer_routes_to_the_hidden_runtime(config_dir, tmp_path, monkeypatch):
    my_port, stub_port = _free_port(), _free_port()
    toml = (config_dir / "game.toml").read_text(encoding="utf-8")
    toml = toml.replace("my_port = 18902", f"my_port = {my_port}")
    toml = toml.replace('opponent_url = "http://127.0.0.1:18901/mcp"',
                       f'opponent_url = "http://127.0.0.1:{stub_port}/mcp"')
    toml = toml.replace("turn_timeout_seconds = 5",
                        'turn_timeout_seconds = 20\nwire_shape = "reference"')
    (config_dir / "game.toml").write_text(toml, encoding="utf-8")
    monkeypatch.chdir(tmp_path)  # artifacts land here, never in the repo

    stub_config = Config.load(config_dir)
    stub_in = PeerInboxes()
    start_peer_server(build_peer_server(stub_in, name="stub_thief"), stub_port)
    stub = build_runtime(
        Role.THIEF, stub_config,
        McpTransport(f"http://127.0.0.1:{my_port}/mcp", 0.2), stub_in,
        ScriptedBrain(Role.THIEF, []))  # camps on (3,3); concedes honestly
    box: dict = {}
    rival = threading.Thread(target=lambda: box.update(stub.play()), daemon=True)
    rival.start()

    report = SimulationSdk(str(config_dir)).run_peer(seed=11)
    rival.join(timeout=90)

    assert report["audit"] == "Verified OK", report
    assert report["digest_match"] is True
    assert report["outcome"] in ("capture", "survival")
    assert box and box["audit"] == "Verified OK"
    assert box["outcome"] == report["outcome"]
    assert box["end_state_digest"] == report["end_state_digest"]

    log_path = tmp_path / "results" / "log_anrbj666-vs-anrbj666_g01.json"
    doc = json.loads(log_path.read_text(encoding="utf-8"))
    assert doc["wire_shape"] == "reference"  # the hidden runtime played this
    assert SimulationSdk.verify_log(str(log_path)) == "Verified OK"
    assert (tmp_path / "config" / "games" / "config_anrbj666-vs-anrbj666_g01.json").is_file()
