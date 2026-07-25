"""Port-probe orphan guard (real sockets, ephemeral ports): an orphaned
peer ANSWERING our role port refuses startup by name BEFORE we bind (a
trial-bind is no guard on Windows — two binds can both succeed), and the
started daemon server must PROVE it listens afterwards."""

import socket
import threading
import time

import pytest

from p2p_police.infra.mcp_server import (
    OrphanPeerError,
    PeerInboxes,
    PortBusyError,
    await_listening,
    build_peer_server,
    ensure_port_free,
    start_peer_server,
)


def ephemeral_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def test_free_port_passes_the_connect_probe() -> None:
    ensure_port_free(ephemeral_port())  # nothing answers -> no raise


def test_answering_orphan_refuses_by_name() -> None:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]
        with pytest.raises(OrphanPeerError, match="ANSWERS"):
            ensure_port_free(port)
    assert issubclass(OrphanPeerError, PortBusyError)  # existing handlers still catch


def test_start_peer_server_refuses_an_orphaned_port_before_binding() -> None:
    """The startup path itself: an orphan on the role port means NO second
    server thread ever starts (never trial-bind beside it)."""
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]
        with pytest.raises(OrphanPeerError, match=str(port)):
            start_peer_server(build_peer_server(PeerInboxes()), port)
        names = [thread.name for thread in threading.enumerate()]
        assert f"mcp-server-{port}" not in names  # no daemon thread started


def test_await_listening_succeeds_once_the_server_comes_up() -> None:
    """The post-start probe retries through the server's startup window."""
    port = ephemeral_port()
    ready = threading.Event()

    def late_listener() -> None:
        time.sleep(0.15)  # the server thread needs a moment to bind
        with socket.socket() as server:
            server.bind(("127.0.0.1", port))
            server.listen(1)
            ready.wait(5)

    thread = threading.Thread(target=late_listener, daemon=True)
    thread.start()
    try:
        await_listening(port, attempts=40, delay=0.05)  # must not raise
    finally:
        ready.set()
        thread.join(timeout=5)


def test_await_listening_fails_loudly_when_nothing_ever_listens() -> None:
    with pytest.raises(PortBusyError, match="never started listening"):
        await_listening(ephemeral_port(), attempts=3, delay=0.01)
