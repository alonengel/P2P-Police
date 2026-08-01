"""Capture-claim flow — the truth duty is STRUCTURAL (rules 21-22).

The thief's answer to a capture claim is a pure function of its OWN state
and the claimed cell. No strategy object, brain, config flag or RNG appears
in any signature here, so no strategy code can alter the answer: the
truthful path is the only path. The automatic capture families
(barrier-on-thief, fully-blocked thief) stay automatic per the book — the
concession here only SAYS what the physics already decided.
"""

from p2p_police.wire.own_state import OwnState


def answer_capture_claim(own: OwnState, claim_cell) -> dict:
    """Honest {"claim": [r, c], "caught": bool} computed from the true cell."""
    caught = (claim_cell[0], claim_cell[1]) == tuple(own.cell)
    return {"claim": [claim_cell[0], claim_cell[1]], "caught": caught}


def concede_declaration(own: OwnState) -> dict:
    """The automatic-capture self-declaration (barrier on my cell / fully
    surrounded): an honest caught=True naming my own final cell."""
    return {"claim": [own.cell[0], own.cell[1]], "caught": True}


def capture_claim_for(action: dict, own: OwnState, perception=None,
                      config=None) -> list | None:
    """Police only: claim my landing cell after a move (demo protocol).
    A barrier placement forgoes the move, so it claims nothing — barrier
    captures resolve automatically on the thief's side.

    GATED on belief (rule 27 is not the issue; information is). The claim
    names our TRUE cell, so an unconditional claim every turn hands the rival
    our exact position every turn — and a claim-reading thief collapses its
    estimate onto it. Claim only when the belief says the cell plausibly
    holds the thief; below the threshold the move goes out unclaimed. Truth
    duty untouched: what we DO say is always our real cell.
    """
    if action.get("type") != "move":
        return None
    cell = [own.cell[0], own.cell[1]]
    if perception is None or config is None:
        return cell  # unfiltered (tests, replay): the historical behaviour
    from p2p_police.shared.tuning import claim_table

    threshold = claim_table(config.private)["threshold"]
    return cell if perception.belief.value_at(own.cell) >= threshold else None
