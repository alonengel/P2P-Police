"""Transport liveness (live-outage regression): every wait path inside the
MCP client beats the watchdog in short slices — a hung in-flight call (the
client's internal GET-stream reconnect) or a long retry backoff must never
starve the liveness window. Only the DEADLINE judges the rival."""

import asyncio
import time

import pytest

from p2p_police.infra.duplicate_transport import DuplicatingTransport
from p2p_police.infra.mcp_client import McpTransport
from p2p_police.peer.deadline import Deadline, DeadlineExpiredError

DEAD_URL = "http://127.0.0.1:9/mcp"  # discard port: never answers


def _hung_call(self, _tool, _payload):
    async def never() -> dict:
        await asyncio.Event().wait()  # a reconnect-forever in-flight await
        return {}

    return never()


def test_hung_inflight_call_keeps_beating_until_the_deadline(monkeypatch):
    monkeypatch.setattr(McpTransport, "_call_once", _hung_call)
    transport = McpTransport(DEAD_URL, retry_backoff_sec=0.05,
                             response_timeout_sec=10.0, sleep=lambda _s: None,
                             beat_slice_sec=0.05)
    beats: list[float] = []
    transport.beat = lambda: beats.append(time.monotonic())
    with pytest.raises(DeadlineExpiredError):
        transport.call("receive_turn", {}, Deadline(0.6))
    assert len(beats) >= 5, "the in-flight wait must beat per slice, not per call"
    gaps = [later - earlier
            for earlier, later in zip(beats, beats[1:], strict=False)]
    assert max(gaps) < 0.5, "no silent block may approach the watchdog window"


def test_retry_backoff_sleeps_in_beat_sized_slices_fake_clock(monkeypatch):
    def fail_fast(self, _tool, _payload):
        async def boom() -> dict:
            raise ConnectionError("refused")

        return boom()

    monkeypatch.setattr(McpTransport, "_call_once", fail_fast)
    clock = {"t": 0.0}
    naps: list[float] = []

    def fake_sleep(seconds: float) -> None:
        clock["t"] += seconds
        naps.append(seconds)

    beats: list[int] = []
    transport = McpTransport(DEAD_URL, retry_backoff_sec=1.0,
                             response_timeout_sec=5.0, sleep=fake_sleep,
                             beat_slice_sec=0.25)
    transport.beat = lambda: beats.append(1)
    with pytest.raises(DeadlineExpiredError):
        transport.call("receive_turn", {}, Deadline(3.0, clock=lambda: clock["t"]))
    assert naps, "the backoff path must have run"
    assert all(nap <= 0.25 for nap in naps), "backoff must sleep in beat slices"
    assert len(beats) >= len(naps), "every backoff slice is preceded by a beat"


def test_a_call_raised_timeout_is_a_transport_error_not_a_spin(monkeypatch):
    """A TimeoutError raised BY the coroutine (httpx/asyncio family) must
    surface as a normal connection-flavored failure — never loop inside the
    slice wait re-reading a completed future."""

    def raise_timeout(self, _tool, _payload):
        async def boom() -> dict:
            raise TimeoutError("read timed out")

        return boom()

    monkeypatch.setattr(McpTransport, "_call_once", raise_timeout)
    transport = McpTransport(DEAD_URL, retry_backoff_sec=0.05,
                             response_timeout_sec=10.0, sleep=lambda _s: None,
                             beat_slice_sec=0.05)
    started = time.monotonic()
    with pytest.raises(DeadlineExpiredError):
        transport.call("receive_turn", {}, Deadline(0.4))
    assert time.monotonic() - started < 5.0  # bounded by the deadline, no 10s hold


def test_duplicate_wrapper_forwards_beat_to_the_inner_transport():
    inner = McpTransport(DEAD_URL, retry_backoff_sec=0.05)
    wrapper = DuplicatingTransport(inner, evidence=None)
    calls: list[int] = []
    wrapper.beat = lambda: calls.append(1)  # SDK wires the wrapper...
    inner.beat()  # ...but the INNER retry loop does the beating
    assert calls == [1]
    assert wrapper.beat is inner.beat
