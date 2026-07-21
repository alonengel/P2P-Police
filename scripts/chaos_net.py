"""Chaos-drill network plumbing (split from chaos_lib.py, 150-line cap).

FlappyProxy sits between OUR transport and the stub's real FastMCP server so
a drill can sever/refuse the opponent endpoint and heal it on the SAME port —
the localhost analogue of a tunnel dying and coming back.
"""

import contextlib
import socket
import threading
import time

from p2p_police.infra.mcp_server import PeerInboxes, build_peer_server, start_peer_server


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def start_inbox_server(name: str) -> tuple[PeerInboxes, int]:
    """One real FastMCP peer server on an ephemeral port (roundtrip pattern)."""
    inboxes = PeerInboxes()
    port = free_port()
    start_peer_server(build_peer_server(inboxes, name=name), port)
    return inboxes, port


class FlappyProxy:
    """TCP forwarder in front of the stub server; stop() refuses new
    connections AND severs live ones, start() heals on the SAME port."""

    def __init__(self, target_port: int, host: str = "127.0.0.1") -> None:
        self.target_port, self.host, self.port = target_port, host, free_port()
        self.url = f"http://{host}:{self.port}/mcp"
        self._listener: socket.socket | None = None
        self._conns: list[socket.socket] = []
        self._lock = threading.Lock()

    def start(self) -> None:
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind((self.host, self.port))
        listener.listen(16)
        self._listener = listener
        threading.Thread(target=self._accept_loop, args=(listener,),
                         name=f"flappy-proxy-{self.port}", daemon=True).start()

    def stop(self) -> None:
        with self._lock:
            listener, self._listener = self._listener, None
            for sock in ([listener] if listener else []) + self._conns:
                with contextlib.suppress(OSError):
                    sock.close()
            self._conns.clear()

    def _accept_loop(self, listener: socket.socket) -> None:
        while True:
            try:
                client, _ = listener.accept()
                upstream = socket.create_connection((self.host, self.target_port), timeout=5)
            except OSError:
                return  # listener closed by stop()
            with self._lock:
                self._conns += [client, upstream]
            for source, sink in ((client, upstream), (upstream, client)):
                threading.Thread(target=self._pump, args=(source, sink), daemon=True).start()

    def _pump(self, source: socket.socket, sink: socket.socket) -> None:
        with contextlib.suppress(OSError):
            while chunk := source.recv(65536):
                sink.sendall(chunk)
        for sock in (source, sink):
            with contextlib.suppress(OSError):
                sock.close()


class RetryCounter:
    """Injectable transport sleep that counts REAL retry backoffs."""

    def __init__(self) -> None:
        self.retries = 0

    def sleep(self, seconds: float) -> None:
        self.retries += 1
        time.sleep(seconds)
