"""Chaos-drill network plumbing (split from chaos_lib.py, 150-line cap).

FlappyProxy sits between OUR transport and the stub's real FastMCP server so
a drill can sever/refuse the opponent endpoint and heal it on the SAME port —
the localhost analogue of a tunnel dying and coming back.
"""

import contextlib
import socket
import threading
import time

from p2p_police.infra.mcp_server import (
    OrphanPeerError,
    PeerInboxes,
    PortBusyError,
    build_peer_server,
    start_peer_server,
)

PORT_ATTEMPTS = 6  # a lost race is retried, never reported as a drill failure


def free_port() -> int:
    """An ephemeral port that was free A MOMENT AGO.

    Deliberately not a reservation: the probe socket must close before the
    real server can bind the port, so every caller races anything else on the
    machine for it. Callers must therefore RETRY rather than trust the number
    (see `bind_with_retry`) - the drills bind several ports in quick
    succession while a full test suite churns sockets alongside them.
    """
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def bind_with_retry(start, attempts: int = PORT_ATTEMPTS):
    """Call `start(port)` on fresh ports until one really listens.

    `free_port` cannot reserve, so losing the port between the probe and the
    bind is normal under load and says nothing about the code under test. It
    surfaced as intermittent drill failures in full-suite runs only (never in
    isolation), which is the signature of a port race rather than a timing
    bug. A genuine port problem still fails - after `attempts` distinct ports.
    """
    last: Exception | None = None
    for _ in range(attempts):
        port = free_port()
        try:
            return start(port), port
        except (OrphanPeerError, PortBusyError) as error:
            last = error  # somebody took it in the gap; try another
    raise PortBusyError(
        f"no free port survived {attempts} attempts; last: {last}")


def start_inbox_server(name: str) -> tuple[PeerInboxes, int]:
    """One real FastMCP peer server on an ephemeral port (roundtrip pattern)."""
    inboxes = PeerInboxes()
    _thread, port = bind_with_retry(
        lambda port: start_peer_server(build_peer_server(inboxes, name=name), port))
    return inboxes, port


class FlappyProxy:
    """TCP forwarder in front of the stub server; stop() refuses new
    connections AND severs live ones, start() heals on the SAME port."""

    def __init__(self, target_port: int, host: str = "127.0.0.1") -> None:
        self.target_port, self.host, self.port = target_port, host, free_port()
        self.url = f"http://{host}:{self.port}/mcp"
        # start() re-binds this port after every heal, so it is claimed for the
        # whole drill; a lost initial race is retried there rather than here.
        self._listener: socket.socket | None = None
        self._served = False  # once bound, the port is fixed for heal-on-same-port
        self._conns: list[socket.socket] = []
        self._silent = False  # blackhole: bound, accepting, answering nothing
        self._lock = threading.Lock()

    def start(self) -> None:
        listener = self._bind()
        listener.listen(16)
        threading.Thread(target=self._accept_loop, args=(listener,),
                         name=f"flappy-proxy-{self.port}", daemon=True).start()

    def _bind(self) -> socket.socket:
        """Bind the proxy port; on the FIRST start a lost race just moves us.

        A heal must re-bind the SAME port (the transport holds that URL), so
        only the initial bind may relocate - and it is safe there because the
        caller reads `url` after `start()`.
        """
        healing = self._served
        for _ in range(1 if healing else PORT_ATTEMPTS):
            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # heal-on-same-port: without SO_REUSEADDR the severed listener's
            # TIME_WAIT blocks the re-bind on Linux (EADDRINUSE; CI runners)
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                listener.bind((self.host, self.port))
            except OSError:
                listener.close()
                if healing:
                    raise
                self.port = free_port()  # somebody took it in the gap
                self.url = f"http://{self.host}:{self.port}/mcp"
                continue
            self._served = True
            self._listener = listener
            return listener
        raise PortBusyError(f"proxy could not bind after {PORT_ATTEMPTS} ports")

    def stop(self) -> None:
        with self._lock:
            listener, self._listener = self._listener, None
            for sock in ([listener] if listener else []) + self._conns:
                with contextlib.suppress(OSError):
                    sock.close()
            self._conns.clear()

    def blackhole(self) -> None:
        """Stay BOUND but answer nothing: the peer meets silence, not a
        refusal. Closing the listener is not the same fault on every OS -
        Linux refuses a connect to a closed port instantly (httpx raises
        ConnectError) while Windows leaves it hanging, so a drill that means
        to exercise the DEADLINE classified two different things depending on
        the runner and failed only in CI (2026-08-23). Silence is the fault
        we actually mean, and every platform renders it identically."""
        with self._lock:
            self._silent = True
            for sock in self._conns:
                with contextlib.suppress(OSError):
                    sock.close()
            self._conns.clear()

    def _accept_loop(self, listener: socket.socket) -> None:
        while True:
            try:
                client, _ = listener.accept()
                if self._silent:  # accepted, then never answered
                    with self._lock:
                        self._conns.append(client)
                    continue
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
