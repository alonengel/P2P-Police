"""Outbound transport to the opponent's FastMCP server (rulebook ch. 2).

ONE persistent MCP session lives on a dedicated event-loop thread and is
reused across calls — per-call sessions churn through tunnels/proxies and get
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
    ) -> None:
        self.opponent_url = opponent_url
        self.retry_backoff_sec = retry_backoff_sec
        self.response_timeout_sec = response_timeout_sec
        self._sleep = sleep
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
        future = asyncio.run_coroutine_threadsafe(coro, self._ensure_loop())
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError as error:
            future.cancel()
            raise TimeoutError(f"in-flight call to {self.opponent_url} timed out") from error

    async def _call_once(self, tool: str, payload: dict) -> dict:
        if self._client is None:
            client = Client(self.opponent_url)
            await client.__aenter__()  # persistent session (closed on reset)
            self._client = client
        result = await self._client.call_tool(tool, {"payload": payload})
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
            self._sleep(self.retry_backoff_sec)

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
        )
    )
