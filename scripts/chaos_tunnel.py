"""Live public-tunnel drill: one REAL game over the named Cloudflare tunnel,
with cloudflared killed and restarted mid-game (docs/DEPLOYMENT.md tunnel).

Named tunnel = stable hostnames, so a restart is a true kill/heal drill: the
retrying transport must survive the outage and finish the game. Both peers
are in-process (stub = our own runtime in the rival role, ADR-0001) but every
message crosses the public internet via [game].mcp_servers hostnames.
If the tunnel cannot come up, the abort is recorded honestly - never faked.
"""

import subprocess
import threading
import time
from pathlib import Path

import chaos_lib
import chaos_net
from chaos_lib import MY_ROLE, EvidenceLog

from p2p_police.domain.primitives import Outcome, Role
from p2p_police.infra.mcp_client import McpTransport
from p2p_police.infra.mcp_server import PeerInboxes, build_peer_server, start_peer_server
from p2p_police.peer.deadline import Deadline

NAME = "tunnel_kill_heal"


def _public_url(config, role: Role) -> str:
    """The role's public hostname from [game].mcp_servers (cop/thief keys)."""
    servers = config.private["game"]["mcp_servers"]
    return servers["cop" if role is Role.POLICE else "thief"]


def _spawn(chaos) -> subprocess.Popen:
    return subprocess.Popen(
        [chaos["cloudflared_exe"], "tunnel", "run", chaos["tunnel_name"]],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _probe(url: str, chaos) -> float:
    """Retry a control ping until the tunnel answers; returns seconds waited."""
    started = time.perf_counter()
    transport = McpTransport(url, chaos["tunnel_retry_backoff_sec"])
    transport.send_control({"kind": "ping", "source": "chaos_tunnel"},
                           Deadline(chaos["tunnel_ready_timeout_seconds"]))
    return round(time.perf_counter() - started, 3)


def _kill_heal(box: dict, chaos, engine, evidence: EvidenceLog) -> threading.Thread:
    def trigger():
        while (engine.turns_completed < chaos["tunnel_kill_after_full_turns"]
               and engine.outcome is Outcome.ONGOING):
            time.sleep(0.05)
        box["t"] = time.perf_counter()
        evidence.event(NAME, "inject", fault="tunnel_killed", pid=box["proc"].pid,
                       at_full_turn=engine.turns_completed)
        box["proc"].kill()
        box["proc"].wait(timeout=15)
        time.sleep(chaos["tunnel_downtime_seconds"])
        box["proc"] = _spawn(chaos)
        evidence.event(NAME, "observe", healed="cloudflared restarted",
                       downtime_sec=chaos["tunnel_downtime_seconds"], new_pid=box["proc"].pid)
    thread = threading.Thread(target=trigger, name="tunnel-kill-heal", daemon=True)
    thread.start()
    return thread


def drill_tunnel(config, evidence: EvidenceLog) -> dict:
    chaos = config.private["chaos"]
    config.private["network"]["turn_timeout_seconds"] = chaos["tunnel_turn_timeout_seconds"]
    row = {"drill": NAME, "passed": False, "outcome": "aborted", "tunnel_type": "named"}
    if not Path(chaos["cloudflared_exe"]).is_file():
        evidence.event(NAME, "abort", reason=f"cloudflared not found: {chaos['cloudflared_exe']}")
        return row
    my_public, stub_public = _public_url(config, MY_ROLE), _public_url(config, MY_ROLE.rival)
    try:  # both LOCAL league ports must be free (the tunnel ingress is pinned to them)
        my_inboxes, stub_inboxes = PeerInboxes(), PeerInboxes()
        start_peer_server(build_peer_server(my_inboxes, name=f"chaos_{MY_ROLE.value}"),
                          config.my_port)
        stub_port = int(config.opponent_url.rsplit(":", 1)[1].split("/", 1)[0])
        start_peer_server(build_peer_server(stub_inboxes, name="chaos_stub"), stub_port)
    except Exception as error:  # noqa: BLE001 - abort honestly, never fake
        evidence.event(NAME, "abort", reason=f"local servers: {type(error).__name__}: {error}")
        return row
    box = {"proc": _spawn(chaos)}
    evidence.event(NAME, "start", tunnel_type="named", tunnel=chaos["tunnel_name"],
                   my_public=my_public, stub_public=stub_public,
                   turn_timeout_sec=chaos["tunnel_turn_timeout_seconds"],
                   kill_after_full_turns=chaos["tunnel_kill_after_full_turns"],
                   downtime_sec=chaos["tunnel_downtime_seconds"])
    try:
        ready = {"mine": _probe(my_public, chaos), "stub": _probe(stub_public, chaos)}
        evidence.event(NAME, "observe", tunnel_ready_sec=ready)
        counter, stub_counter = chaos_net.RetryCounter(), chaos_net.RetryCounter()
        mine = chaos_lib.build_runtime(
            MY_ROLE, config,
            McpTransport(stub_public, chaos["tunnel_retry_backoff_sec"],
                         config.response_timeout_sec, sleep=counter.sleep),
            my_inboxes, chaos["my_seed"])
        stub = chaos_lib.build_runtime(
            MY_ROLE.rival, config,
            McpTransport(my_public, chaos["tunnel_retry_backoff_sec"],
                         config.response_timeout_sec, sleep=stub_counter.sleep),
            stub_inboxes, chaos["stub_seed"])
        trigger = _kill_heal(box, chaos, mine.engine, evidence)
        thread, stub_box = chaos_lib.play_in_thread(stub, NAME)
        classified = chaos_lib.run_classified(mine)
        trigger.join(timeout=chaos["tunnel_downtime_seconds"] + 30)
        thread.join(timeout=chaos["tunnel_turn_timeout_seconds"])
        report = classified["report"]
        evidence.event(NAME, "classify", classification=report["outcome"],
                       phase=classified["phase"], error=classified["error"],
                       seconds_since_kill=round(time.perf_counter() - box.get("t", 0), 3))
        row.update({"outcome": report["outcome"], "phase": classified["phase"],
                    "turns_completed": report["turns_completed"],
                    "digest_match": report["digest_match"], "audit": report["audit"],
                    "elapsed_sec": classified["elapsed"], "retries": counter.retries,
                    "stub_retries": stub_counter.retries,
                    "stub_outcome": stub_box.get("report", {}).get("outcome"),
                    "killed_at_full_turn": chaos["tunnel_kill_after_full_turns"]})
        evidence.event(NAME, "outcome",  # the pass verdict is computed after
                       **{k: v for k, v in row.items() if k not in ("drill", "passed")})
        # heal is proven by the kill landing mid-game and the game completing
        row["passed"] = (row["outcome"] != "technical_loss" and row["digest_match"]
                         and row["audit"] == "Verified OK" and "t" in box
                         and chaos["tunnel_kill_after_full_turns"] < row["turns_completed"])
    except Exception as error:  # noqa: BLE001 - abort honestly, never fake
        evidence.event(NAME, "abort", reason=f"{type(error).__name__}: {error}")
    finally:
        box["proc"].kill()
    return row
