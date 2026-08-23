"""push_agreement: BOTH deliveries make a handshake (najamjad w5,
2026-08-23). Live-observed deadlock mirrored here: our one offer landed
5.5s before the rival's window boundary and was answered with an
explicit retriable busy refusal ({"accepted": false}); their offer then
arrived and the old loop adopted it and STOPPED pushing - so the rival
never held ours, refused to open turn 1, and re-offered eleven times
into a queue nobody read while we waited 611s for a turn that could
never come. The loop must keep pushing until OUR send is acknowledged
accepted; an ack WITHOUT the accepted key (unknown reference shapes)
counts as delivered, so conformant-peer behavior is unchanged. Late
re-offers arriving after negotiate mean the rival still lacks ours:
answer_reoffers re-sends from the wait loop.
"""

import queue
from types import SimpleNamespace

from p2p_police.peer.deadline import Deadline
from p2p_police.wire import repush

THEIRS = {"terms": {"k": 1}, "nonce": "n", "signature": "s"}


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def _runtime(acks, clock, arrivals):
    """Runtime stub: each send_agreement pops the next ack; `arrivals`
    maps send-count -> message to drop in the agreements inbox."""
    inbox: queue.Queue = queue.Queue()
    sends: list = []

    def send(payload, deadline):
        sends.append(dict(payload))
        if len(sends) in arrivals:
            inbox.put(arrivals[len(sends)])
        clock.now += 1.0  # each round advances the fake clock
        return acks[min(len(sends), len(acks)) - 1]

    def wait(box, what, deadline=None):
        clock.now += 0.5
        try:
            return box.get_nowait()
        except queue.Empty as empty:
            from p2p_police.peer.deadline import DeadlineExpiredError

            raise DeadlineExpiredError(what) from empty

    rt = SimpleNamespace(
        config=SimpleNamespace(turn_timeout_seconds=60,
                               private={"network": {"agreement_repush_sec": 1.0}}),
        transport=SimpleNamespace(send_agreement=send),
        inboxes=SimpleNamespace(agreements=inbox),
        _wait=wait,
    )
    return rt, sends


def test_busy_refusal_keeps_pushing_until_accepted() -> None:
    """The w5 shape: ack 1-2 refuse, theirs arrives after send 1 - the
    loop must NOT return on their arrival alone; it pushes until an
    accepted ack, then returns theirs."""
    clock = _Clock()
    acks = [{"accepted": False, "reason": "busy - ask again at the boundary"},
            {"accepted": False, "reason": "busy"},
            {"accepted": True}]
    rt, sends = _runtime(acks, clock, arrivals={1: dict(THEIRS)})
    theirs = repush.push_agreement(rt, {"terms": {}, "nonce": "x"}, clock)
    assert theirs == THEIRS
    assert len(sends) == 3  # kept pushing past their arrival until accepted


def test_unknown_ack_shape_is_delivered_reference_compat() -> None:
    """A reference peer acks with an unknown shape (no 'accepted' key):
    treated as delivered - one send, return on their arrival, exactly
    the pre-fix behavior against conformant peers."""
    clock = _Clock()
    rt, sends = _runtime([{"ok": 1}], clock, arrivals={1: dict(THEIRS)})
    theirs = repush.push_agreement(rt, {"terms": {}, "nonce": "x"}, clock)
    assert theirs == THEIRS and len(sends) == 1


def test_answer_reoffers_resends_ours_on_late_agreement() -> None:
    """A rival re-offering AFTER negotiate still lacks our agreement:
    drain the late offer and push ours again; an empty queue sends
    nothing (the hot wait path stays free)."""
    inbox: queue.Queue = queue.Queue()
    sends: list = []
    rt = SimpleNamespace(
        config=SimpleNamespace(turn_timeout_seconds=60, private={}),
        transport=SimpleNamespace(
            send_agreement=lambda payload, deadline: sends.append(dict(payload))),
        inboxes=SimpleNamespace(agreements=inbox),
        my_agreement={"terms": {}, "nonce": "x"},
    )
    repush.answer_reoffers(rt)
    assert sends == []  # nothing pending: no traffic
    inbox.put(dict(THEIRS))
    inbox.put(dict(THEIRS))
    repush.answer_reoffers(rt)
    assert len(sends) == 1  # one drain batch -> one re-send, dedup-safe
    # DURING negotiate (my_agreement unset) the queue belongs to
    # push_agreement's wait: no drain, no send - the guard that keeps this
    # helper from eating the very agreement negotiate is waiting for.
    del rt.my_agreement
    inbox.put(dict(THEIRS))
    repush.answer_reoffers(rt)
    assert inbox.qsize() == 1 and len(sends) == 1
    assert Deadline(1).remaining() > 0  # smoke: deadline import used
