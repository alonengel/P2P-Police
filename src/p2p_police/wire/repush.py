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


def push_agreement(rt, mine: dict, clock=time.monotonic, verify=None) -> dict:
    """Send our agreement, then RE-SEND `mine` unchanged each interval until
    the rival's agreement arrives; the overall turn deadline judges the wait
    (a lapsed deadline is failure, not patience — rule 6).

    With `verify(theirs)` given, each arrival is classified in the wait: a
    PairingRefusalError (bystander — wrong sub-game window or role-equal) is
    logged with the differing values and the wait CONTINUES for the real
    counterpart, still bounded by the one overall deadline (an endless
    bystander stream cannot hold the wait open). Every other verification
    error is a genuine violation and propagates fatally on first offense."""
    deadline = Deadline(rt.config.turn_timeout_seconds, clock=clock)
    interval = repush_interval(rt.config)
    while True:
        rt.transport.send_agreement(
            mine, Deadline(rt.config.turn_timeout_seconds))
        window = max(0.01, min(interval, deadline.remaining()))
        try:
            theirs = rt._wait(rt.inboxes.agreements, "opponent agreement",
                              Deadline(window, clock=clock))
        except DeadlineExpiredError:
            deadline.require("opponent agreement")  # re-raises once lapsed
            continue
        if verify is None:
            return theirs
        try:
            verify(theirs)
        except PairingRefusalError as refusal:
            _LOG.info("agreement refused: wrong game, not you (%s) - "
                      "still waiting for the real counterpart", refusal)
            deadline.require("opponent agreement")  # bystanders never extend it
            continue
        return theirs
