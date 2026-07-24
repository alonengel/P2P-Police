"""Post-settlement inbound refusal: once a peer's own sub-game settles, its
four tool doors refuse instead of enqueueing into a queue nobody reads — a
dying peer must never swallow the rival's next-sub-game greeting (the
rival's transport retry then reaches our next instance)."""

from p2p_police.infra.mcp_server import SETTLED_REFUSAL, PeerInboxes, deliver


def test_doors_accept_and_enqueue_before_settlement():
    inboxes = PeerInboxes()
    assert inboxes.settled is False  # fresh peer: accepting
    for box, payload in [
        (inboxes.agreements, {"terms": {}}),
        (inboxes.turns, {"step": 1}),
        (inboxes.audits, {"records": []}),
        (inboxes.controls, {"kind": "ping"}),
    ]:
        assert deliver(inboxes, box, payload) == {"accepted": True}
        assert box.get_nowait() == payload


def test_all_four_doors_refuse_after_settlement_without_enqueueing():
    inboxes = PeerInboxes()
    inboxes.settled = True
    for box in (inboxes.agreements, inboxes.turns,
                inboxes.audits, inboxes.controls):
        assert deliver(inboxes, box, {"late": True}) == {
            "accepted": False, "reason": "sub-game settled"}
        assert box.empty()  # refused means NOT enqueued anywhere


def test_refusal_shape_matches_the_agreed_wire_contract():
    assert SETTLED_REFUSAL == {"accepted": False, "reason": "sub-game settled"}
