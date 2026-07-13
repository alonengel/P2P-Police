"""Watchdog tests (rule 7): alive while beating, persists + shuts down on
freeze, best-effort persistence never blocks the shutdown."""

from pathlib import Path

import pytest

from p2p_police.peer.watchdog import Watchdog


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_alive_while_heartbeats_arrive(tmp_path: Path) -> None:
    clock = FakeClock()
    dog = Watchdog(60, dict, lambda: None, tmp_path / "d.json", clock)
    clock.now += 59
    dog.beat()
    clock.now += 59
    assert dog.check() == "ALIVE" and not dog.fired


def test_freeze_persists_state_and_shuts_down(tmp_path: Path) -> None:
    clock = FakeClock()
    events = []
    dump = tmp_path / "dump.json"
    dog = Watchdog(60, lambda: {"turn": 7}, lambda: events.append("stop"), dump, clock)
    clock.now += 61
    assert dog.check() == "SHUTDOWN"
    assert dog.fired and events == ["stop"]
    assert '"turn": 7' in dump.read_text()


def test_broken_state_provider_still_shuts_down(tmp_path: Path) -> None:
    clock = FakeClock()
    events = []

    def boom() -> dict:
        raise RuntimeError("no state")

    dog = Watchdog(60, boom, lambda: events.append("stop"), tmp_path / "d.json", clock)
    clock.now += 61
    assert dog.check() == "SHUTDOWN" and events == ["stop"]


def test_bad_timeout_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        Watchdog(0, dict, lambda: None, tmp_path / "d.json")
