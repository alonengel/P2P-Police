"""Outbound transport to the opponent's FastMCP server (rulebook ch. 2).

ONE persistent MCP session lives on a dedicated event-loop thread and is
reused across calls â€” per-call sessions churn through tunnels/proxies and get
terminated (Phase-5 field finding; ex6 hit the same and fixed it the same
way). On any connection-flavored failure the session is rebuilt and the call
retried until its deadline lapses (rule 6: a lapsed wait is failure).
"""

import asyncio
import concurrent.futures
import contextlib
import threading
import time
from collections.abc import Callable

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from p2p_police.peer.deadline import Deadline, DeadlineExpiredError


class McpTransport:
    """Synchronous facade over one long-lived async fastmcp Client session.

    Input: opponent URL + retry/backoff/timeout settings (from config).
    Output: tool-call result dicts. Setup: lazy loop thread; injectable sleep.
    """

    def __init__(
        self,
        opponent_url: str,
        retry_backoff_sec: float,
        response_timeout_sec: float = 30.0,
        sleep: Callable[[float], None] = time.sleep,
        beat_slice_sec: float = 2.0,
        extra_headers: dict | None = None,
    ) -> None:
        self.opponent_url = opponent_url
        self.extra_headers = dict(extra_headers or {})
        self.retry_backoff_sec = retry_backoff_sec
        self.response_timeout_sec = response_timeout_sec
        self.beat_slice_sec = beat_slice_sec  # max un-beaten single wait
        self._sleep = sleep
        self.beat: Callable[[], None] = lambda: None  # watchdog liveness: a
        # legal retry-until-up wait is WORK, not a hang (live-session finding)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._client: Client | None = None
        self._closed = False

    def _ensure_loop(self) -> asyncio.AbstractEventLoop:
        if self._loop is None:
            self._loop = asyncio.new_event_loop()
            threading.Thread(
                target=self._loop.run_forever, name="mcp-client-loop", daemon=True
            ).start()
        return self._loop

    def _submit(self, coro, timeout: float):
        """Await a loop-thread coroutine in SHORT beat-sized slices:
        response_timeout still bounds the call, but no single silent block
        may span the watchdog window while the MCP client's internals (e.g.
        its GET-stream reconnect) hold the await â€” the liveness heartbeat
        keeps firing and only the DEADLINE judges the rival (live-outage
        finding)."""
        future = asyncio.run_coroutine_threadsafe(coro, self._ensure_loop())
        expires = time.monotonic() + timeout
        while True:
            self.beat()
            window = min(self.beat_slice_sec, max(0.05, expires - time.monotonic()))
            try:
                return future.result(timeout=window)
            except concurrent.futures.TimeoutError as error:
                if time.monotonic() >= expires:
                    future.cancel()
                    raise TimeoutError(
                        f"in-flight call to {self.opponent_url} timed out"
                    ) from error

    def _sleep_beating(self, seconds: float) -> None:
        """Retry backoff in beat-sized slices (same liveness rule)."""
        while seconds > 0:
            self.beat()
            step = min(self.beat_slice_sec, seconds)
            self._sleep(step)
            seconds -= step

    def _build_client(self) -> Client:
        """Config-declared extra headers ride an explicit HTTP transport
        (ngrok's free tier answers header-less calls with an HTML
        interstitial at HTTP 200 — league best2934 door, 2026-08-16);
        with none declared the client is built exactly as before."""
        if self.extra_headers:
            return Client(StreamableHttpTransport(
                self.opponent_url, headers=dict(self.extra_headers)))
        return Client(self.opponent_url)

    async def _call_once(self, tool: str, payload: dict) -> dict:
        if self._client is None:
            client = self._build_client()
            await client.__aenter__()  # persistent session (closed on reset)
            self._client = client
        # reference tool-arg contract (interop, verified against the demo):
        # `message` everywhere except submit_audit's `payload`
        arg = "payload" if tool == "submit_audit" else "message"
        result = await self._client.call_tool(tool, {arg: payload})
        return result.data if isinstance(result.data, dict) else {"data": result.data}

    async def _reset_client(self) -> None:
        client, self._client = self._client, None
        if client is not None:
            with contextlib.suppress(Exception):  # already broken - discard
                await client.__aexit__(None, None, None)

    def call(self, tool: str, payload: dict, deadline: Deadline) -> dict:
        """Call an opponent tool, rebuilding the session and retrying
        connection-flavored failures until the deadline lapses."""
        while True:
            self.beat()  # retrying IS liveness - the deadline judges the rival
            if self._closed:
                raise DeadlineExpiredError(
                    f"transport to {self.opponent_url} closed (watchdog shutdown)"
                )
            deadline.require(f"opponent tool '{tool}' at {self.opponent_url}")
            timeout = min(self.response_timeout_sec, max(0.1, deadline.remaining()))
            try:
                return self._submit(self._call_once(tool, payload), timeout)
            except Exception as error:
                if not _is_connection_flavored(error):
                    raise
                last = error
            with contextlib.suppress(Exception):  # a wedged loop must not
                self._submit(self._reset_client(), 2.0)  # escalate past reporting
            if deadline.remaining() < self.retry_backoff_sec:
                raise DeadlineExpiredError(
                    f"opponent at {self.opponent_url} unreachable until deadline: {last}"
                )
            self._sleep_beating(self.retry_backoff_sec)

    def close(self) -> None:
        """Fast, non-blocking shutdown (watchdog-safe): flag first so callers
        fail fast, then stop the loop; never block on a wedged in-flight call."""
        self._closed = True
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._loop.stop)

    def send_agreement(self, payload: dict, deadline: Deadline) -> dict:
        return self.call("negotiate", payload, deadline)

    def send_turn(self, payload: dict, deadline: Deadline) -> dict:
        return self.call("receive_turn", payload, deadline)

    def send_audit(self, payload: dict, deadline: Deadline) -> dict:
        return self.call("submit_audit", payload, deadline)

    def send_control(self, payload: dict, deadline: Deadline) -> dict:
        return self.call("receive_control", payload, deadline)


def _is_connection_flavored(error: Exception) -> bool:
    """Transport-level failures worth a session rebuild + retry."""
    text = f"{type(error).__name__}: {error}".lower()
    return any(
        marker in text
        for marker in (
            "connect", "connection", "refused", "unreachable", "reset",
            "timeout", "timed out", "readerror", "writeerror", "closed",
            "remoteprotocol", "session terminated", "oserror",
            "502", "503", "504", "bad gateway",  # tunnel up, origin not yet
            "530",  # Cloudflare edge up, tunnel down (chaos drill field finding)
        )
    )
