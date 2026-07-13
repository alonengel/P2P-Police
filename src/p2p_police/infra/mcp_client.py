"""Outbound transport to the opponent's FastMCP server (rulebook ch. 2).

The opponent's URL is the ONLY thing we know about them. Peers start seconds
apart, so every call retries on connection errors with the configured backoff
until its deadline lapses — then the failure surfaces (rule 6: a lapsed wait
is failure, not patience).
"""

import asyncio
import time
from collections.abc import Callable

from fastmcp import Client

from p2p_police.peer.deadline import Deadline, DeadlineExpiredError


class McpTransport:
    """Synchronous facade over the async fastmcp Client.

    Input: opponent URL + retry/backoff settings (from config).
    Output: tool-call result dicts. Setup: injectable sleep for tests.
    """

    def __init__(
        self,
        opponent_url: str,
        retry_backoff_sec: float,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.opponent_url = opponent_url
        self.retry_backoff_sec = retry_backoff_sec
        self._sleep = sleep

    async def _call_async(self, tool: str, payload: dict) -> dict:
        async with Client(self.opponent_url) as client:
            result = await client.call_tool(tool, {"payload": payload})
            return result.data if isinstance(result.data, dict) else {"data": result.data}

    def call(self, tool: str, payload: dict, deadline: Deadline) -> dict:
        """Call an opponent tool, retrying connection failures until deadline.

        Turn-cadence traffic is tiny, so a fresh event loop per call is a
        deliberate simplicity trade (documented; revisit if profiling says so).
        """
        while True:
            deadline.require(f"opponent tool '{tool}' at {self.opponent_url}")
            try:
                return asyncio.run(self._call_async(tool, payload))
            except (OSError, ConnectionError, TimeoutError) as error:
                last = error
            except Exception as error:  # fastmcp wraps httpx errors variously
                if not _is_connection_flavored(error):
                    raise
                last = error
            if deadline.remaining() < self.retry_backoff_sec:
                raise DeadlineExpiredError(
                    f"opponent at {self.opponent_url} unreachable until deadline: {last}"
                )
            self._sleep(self.retry_backoff_sec)

    def send_agreement(self, payload: dict, deadline: Deadline) -> dict:
        return self.call("negotiate", payload, deadline)

    def send_turn(self, payload: dict, deadline: Deadline) -> dict:
        return self.call("receive_turn", payload, deadline)

    def send_audit(self, payload: dict, deadline: Deadline) -> dict:
        return self.call("submit_audit", payload, deadline)

    def send_control(self, payload: dict, deadline: Deadline) -> dict:
        return self.call("receive_control", payload, deadline)


def _is_connection_flavored(error: Exception) -> bool:
    """True for wrapped transport-level failures worth retrying (opponent not
    up yet, connection reset) as opposed to real protocol errors."""
    text = f"{type(error).__name__}: {error}".lower()
    return any(
        marker in text
        for marker in ("connect", "connection", "refused", "unreachable", "reset", "timeout")
    )
