"""This peer's own FastMCP server (rulebook ch. 2: every agent is a server).

Four tools mirror the game protocol: negotiate, receive_turn, submit_audit,
receive_control. Tools are dumb doors: they drop payloads into thread-safe
inbox queues and acknowledge — all game logic lives behind the SDK, never in
the transport (separation of concerns, ch. 8).
"""

import queue
import socket
import threading

from fastmcp import FastMCP


class PortBusyError(Exception):
    """The configured port is taken — fail fast with an actionable message."""


class PeerInboxes:
    """Thread-safe handoff between the server thread and the game loop.

    Input: payload dicts from remote tool calls. Output: FIFO consumption by
    the runtime. Setup: unbounded stdlib queues (turn cadence is tiny).
    """

    def __init__(self) -> None:
        self.agreements: queue.Queue[dict] = queue.Queue()
        self.turns: queue.Queue[dict] = queue.Queue()
        self.audits: queue.Queue[dict] = queue.Queue()
        self.controls: queue.Queue[dict] = queue.Queue()


def ensure_port_free(port: int, host: str = "127.0.0.1") -> None:
    """Raise PortBusyError if `port` cannot be bound (rulebook: fail fast
    beats a silent second instance fighting over the inbox)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind((host, port))
        except OSError as error:
            raise PortBusyError(
                f"port {port} on {host} is busy ({error}); stop the other process "
                f"or change [network].my_port in config/game.toml"
            ) from error


def build_peer_server(inboxes: PeerInboxes, name: str = "p2p_police_peer") -> FastMCP:
    """Wire the four protocol tools onto a FastMCP instance."""
    mcp = FastMCP(name)

    @mcp.tool
    def negotiate(message: dict) -> dict:
        """Receive the opponent's pre-game agreement (config sha, commit order)."""
        inboxes.agreements.put(message)
        return {"accepted": True}

    @mcp.tool
    def receive_turn(message: dict) -> dict:
        """Receive one turn message from the opponent."""
        inboxes.turns.put(message)
        return {"accepted": True}

    @mcp.tool
    def submit_audit(payload: dict) -> dict:
        """Receive end-of-game audit material (nonces, digests)."""
        inboxes.audits.put(payload)
        return {"accepted": True}

    @mcp.tool
    def receive_control(message: dict) -> dict:
        """Receive out-of-band control messages (pause, abort, info)."""
        inboxes.controls.put(message)
        return {"accepted": True}

    return mcp


def start_peer_server(
    mcp: FastMCP, port: int, host: str = "127.0.0.1"
) -> threading.Thread:
    """Run the server over HTTP in a daemon thread and return the thread.

    Daemon: the game loop owns process lifetime; a wedged transport must never
    keep a dead peer alive (watchdog does controlled shutdown, ch. 8).
    """
    ensure_port_free(port, host)
    thread = threading.Thread(
        target=lambda: mcp.run(
            transport="http",
            host=host,
            port=port,
            show_banner=False,
            # keep stdout clean for the CLI's JSON report: uvicorn access logs
            # are noise at turn cadence
            log_level="warning",
        ),
        name=f"mcp-server-{port}",
        daemon=True,
    )
    thread.start()
    return thread
