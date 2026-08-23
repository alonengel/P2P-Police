"""Agreement re-push for the hidden-wire negotiate (split from
hidden_runtime.py for the 150-code-line cap; `rt` carries the state).

Live-observed failure mirrored here: our greeting lands at the opponent's
PREVIOUS sub-game peer, which acks it into a dead queue and exits — the
agreement is swallowed, the faster side runs ahead and the series drifts
into a rule-35 shape. Re-sending the SAME payload (same nonce, so the
rival's receiver dedup makes repeats harmless) every few seconds gives the
greeting fresh chances at their real peer; the turn deadline still bounds
everything and the watchdog beats keep firing inside `rt._wait`.

Bystander tolerance (live-observed, the mirror failure): the FIRST
agreement to ARRIVE may itself be a leftover rival instance greeting the
wrong window, or a same-role echo. That is a PAIRING problem — wrong game,
not you — never a protocol violation by our real counterpart, so it must
not cost us the game: log it on the record and keep waiting. Genuine
violations (terms drift, bad signature, locked-model mismatch) stay
first-offense fatal.
"""

import logging
import time

from p2p_police.peer.deadline import Deadline, DeadlineExpiredError
from p2p_police.wire.terms import PairingRefusalError

_LOG = logging.getLogger(__name__)

DEFAULT_REPUSH_SEC = 7.0  # overridden by [network] agreement_repush_sec


def repush_interval(config) -> float:
    """[network] agreement_repush_sec — seconds between agreement re-sends."""
    return float(config.private.get("network", {})
                 .get("agreement_repush_sec", DEFAULT_REPUSH_SEC))


def _acked(response) -> bool:
    """Did the rival's door accept our delivery? An explicit accepted=False
    (a retriable busy refusal — najamjad w5, 2026-08-23: our one offer hit
    their boundary 5.5s early and the old loop never re-sent) means NOT
    delivered. Any other shape — reference peers ack with whatever they
    like, or nothing — counts as delivered: conformant-peer behavior stays
    byte-identical to the pre-fix loop."""
    return not (isinstance(response, dict) and response.get("accepted") is False)


def push_agreement(rt, mine: dict, clock=time.monotonic, verify=None) -> dict:
    """Send our agreement, then RE-SEND `mine` unchanged each interval until
    BOTH deliveries hold: the rival's agreement has arrived AND ours was
    acknowledged accepted — one arrival alone is half a handshake (the w5
    deadlock: we adopted theirs, stopped pushing, and they starved). The
    overall turn deadline judges the wait (rule 6).

    With `verify(theirs)` given, each arrival is classified in the wait: a
    PairingRefusalError (bystander — wrong sub-game window or role-equal) is
    logged with the differing values and the wait CONTINUES for the real
    counterpart, still bounded by the one overall deadline (an endless
    bystander stream cannot hold the wait open). Every other verification
    error is a genuine violation and propagates fatally on first offense."""
    deadline = Deadline(rt.config.turn_timeout_seconds, clock=clock)
    interval = repush_interval(rt.config)
    theirs, delivered = None, False
    while theirs is None or not delivered:
        # Send EVERY interval until the loop exits: an accepted ack is
        # transport truth, not consumption — a dying peer acks a greeting
        # into a dead queue (the original swallowed-greeting case), so
        # only the rival's ARRIVAL proves our push reached a live pair.
        ack = rt.transport.send_agreement(
            mine, Deadline(rt.config.turn_timeout_seconds))
        delivered = delivered or _acked(ack)
        if not _acked(ack):
            _LOG.info("agreement not yet delivered (their door refused "
                      "retriably: %s) - re-offering on cadence", ack)
        if theirs is not None and delivered:
            break
        # ONE paced wait serves both halves: it delivers their agreement,
        # drains their duplicate re-offers while we keep pushing ours, and
        # carries the watchdog beats + the overall deadline check.
        window = max(0.01, min(interval, deadline.remaining()))
        try:
            candidate = rt._wait(rt.inboxes.agreements, "opponent agreement",
                                 Deadline(window, clock=clock))
        except DeadlineExpiredError:
            deadline.require("opponent agreement")  # re-raises once lapsed
            continue
        if theirs is not None:
            continue  # a re-offer duplicate drained; cadence tick complete
        try:
            if verify is not None:
                verify(candidate)
        except PairingRefusalError as refusal:
            _LOG.info("agreement refused: wrong game, not you (%s) - "
                      "still waiting for the real counterpart", refusal)
            deadline.require("opponent agreement")  # bystanders never extend it
            continue
        theirs = candidate
    rt.my_agreement = mine  # answer_reoffers re-sends this on late offers
    return theirs


def answer_reoffers(rt) -> None:
    """A rival's agreement arriving AFTER negotiate means it still lacks
    ours (its door refused our push and it is re-offering on a cadence):
    drain the late offers and send ours again — dedup-safe (same nonce),
    one send per drain batch, silent when the queue is empty."""
    mine = getattr(rt, "my_agreement", None)
    if mine is None:
        return  # negotiate still running: ITS wait owns this queue - no drain
    drained = 0
    try:
        while True:
            rt.inboxes.agreements.get_nowait()
            drained += 1
    except Exception:  # queue.Empty ends the drain; inbox always queue-like
        pass
    if drained:
        _LOG.info("late agreement re-offer heard (%d) - re-sending ours", drained)
        rt.transport.send_agreement(mine, Deadline(rt.config.turn_timeout_seconds))
