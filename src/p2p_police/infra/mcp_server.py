"""This peer's own FastMCP server (rulebook ch. 2: every agent is a server).

Four tools mirror the game protocol: negotiate, receive_turn, submit_audit,
receive_control. Tools are dumb doors: they drop payloads into thread-safe
inbox queues and acknowledge — all game logic lives behind the SDK, never in
the transport (separation of concerns, ch. 8).
"""

import queue
import socket
import threading
import time

from fastmcp import FastMCP


class PortBusyError(Exception):
    """The configured port is taken — fail fast with an actionable message."""


class OrphanPeerError(PortBusyError):
    """Something already ANSWERS on our role port: an orphaned peer instance
    would swallow the rival's traffic while the real peer starves and
    mis-reports the game — never start beside it."""


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
        # Set by the SDK once this peer's own sub-game settles (classified,
        # audit exchanged or failed): tools then REFUSE instead of enqueueing.
        self.settled = False


SETTLED_REFUSAL = {"accepted": False, "reason": "sub-game settled"}


def deliver(inboxes: PeerInboxes, box: queue.Queue, payload: dict) -> dict:
    """Inbox door with the settlement gate: a settled peer must never
    swallow the rival's NEXT-sub-game greeting into a queue nobody reads —
    refusing here lets their transport retry reach our next instance."""
    if inboxes.settled:
        return dict(SETTLED_REFUSAL)
    box.put(payload)
    return {"accepted": True}


def ensure_port_free(port: int, host: str = "127.0.0.1",
                     timeout: float = 0.5) -> None:
    """CONNECT-probe the role port BEFORE binding: anything that ANSWERS is
    an orphaned peer (or a foreign server) — refuse by name (rulebook: fail
    fast beats a silent second instance fighting over the inbox). Never
    trial-bind as the guard: on Windows two binds can BOTH succeed, so
    answering, not bindability, is the only honest test."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            answered = True
    except OSError:
        answered = False  # nothing listening: the port is ours to take
    if answered:
        raise OrphanPeerError(
            f"port {port} on {host} already ANSWERS a connect probe - an "
            "orphaned peer instance seems to hold it (the real peer would "
            "starve and mis-report); stop that process or change "
            "[network].my_port in config/game.toml")


def await_listening(port: int, host: str = "127.0.0.1",
                    attempts: int = 40, delay: float = 0.1) -> None:
    """AFTER the daemon server thread starts: prove it actually listens
    (connect-probe with small retries) — a peer that cannot be reached must
    fail loudly at startup, never play on and mis-report the rival absent."""
    for _ in range(attempts):
        try:
            with socket.create_connection((host, port), timeout=0.25):
                return
        except OSError:
            time.sleep(delay)
    raise PortBusyError(
        f"our MCP server never started listening on {host}:{port} "
        f"(~{attempts * delay:.0f}s of connect probes) - refusing to play "
        "unreachable")


def build_peer_server(inboxes: PeerInboxes, name: str = "p2p_police_peer") -> FastMCP:
    """Wire the four protocol tools onto a FastMCP instance."""
    mcp = FastMCP(name)

    @mcp.tool
    def negotiate(message: dict) -> dict:
        """Receive the opponent's pre-game agreement (config sha, commit order)."""
        return deliver(inboxes, inboxes.agreements, message)

    @mcp.tool
    def receive_turn(message: dict) -> dict:
        """Receive one turn message from the opponent."""
        return deliver(inboxes, inboxes.turns, message)

    @mcp.tool
    def submit_audit(payload: dict) -> dict:
        """Receive end-of-game audit material (nonces, digests)."""
        return deliver(inboxes, inboxes.audits, payload)

    @mcp.tool
    def receive_control(message: dict) -> dict:
        """Receive out-of-band control messages (pause, abort, info)."""
        return deliver(inboxes, inboxes.controls, message)

    return mcp


def start_peer_server(
    mcp: FastMCP, port: int, host: str = "127.0.0.1"
) -> threading.Thread:
    """Run the server over HTTP in a daemon thread and return the thread.

    Daemon: the game loop owns process lifetime; a wedged transport must never
    keep a dead peer alive (watchdog does controlled shutdown, ch. 8).
    Guarded on both edges: an orphan answering the port refuses BEFORE we
    bind; the started server must prove it listens AFTER (await_listening).
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
    await_listening(port, host)
    return thread
