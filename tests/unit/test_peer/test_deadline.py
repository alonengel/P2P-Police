"""Deadline tests encode rule 6 / ch. 8: expiry on a monotonic clock, lapse is
failure. A fake clock keeps tests instant."""

import pytest

from p2p_police.peer.deadline import Deadline, DeadlineExpiredError


class FakeClock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def test_not_expired_before_window_ends() -> None:
    clock = FakeClock()
    deadline = Deadline(30, clock=clock)
    clock.now += 29.9
    assert not deadline.expired
    deadline.require("opponent move")


def test_expired_at_window_end() -> None:
    clock = FakeClock()
    deadline = Deadline(30, clock=clock)
    clock.now += 30.0
    assert deadline.expired


def test_require_raises_naming_the_awaited_thing() -> None:
    clock = FakeClock()
    deadline = Deadline(5, clock=clock)
    clock.now += 6
    with pytest.raises(DeadlineExpiredError, match="opponent move"):
        deadline.require("opponent move")


def test_remaining_counts_down_and_floors_at_zero() -> None:
    clock = FakeClock()
    deadline = Deadline(10, clock=clock)
    clock.now += 4
    assert deadline.remaining() == 6.0
    clock.now += 100
    assert deadline.remaining() == 0.0


def test_non_positive_deadline_is_rejected() -> None:
    with pytest.raises(ValueError):
        Deadline(0)
