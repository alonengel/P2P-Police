"""End-of-game audit for the hidden wire: reveal, verify, RECONSTRUCT.

Live messages carried only commits, so the audit boundary is where the game
becomes checkable: each side transmits its full sealed records (payloads +
nonces revealed TOGETHER, rule 18); the receiver re-hashes every reveal
against the commits received live (HiddenExchange.audit_reveals), then
replays BOTH sides' revealed actions through the domain physics (Board
legality, the barrier law, the boundary clock) and derives the end digest
in the protocol's canonical shape.

Deliberate deviation from the engine replay (documented): GameEngine calls
ANY co-location an instant capture, but under this wire a thief that walks
onto the cop's cell is unobservable live — capture is claim-mediated. The
replay therefore treats co-location as capture ONLY when the cop's own
action created it (landing or barrier), which is exactly what the wire can
prove; and it enforces the truth duty (rules 21-22): a cop action that
captures MUST be followed by the thief's action-free concession — a game
that played on past it is tampering evidence.
"""

import hashlib

from p2p_police.domain.board import Board
from p2p_police.domain.crypto import canonical
from p2p_police.domain.errors import GameRuleError
from p2p_police.domain.primitives import Move, Outcome, Role
from p2p_police.domain.rules import RuleSet, validate_barrier_placement
from p2p_police.report.lookup import geometry

_CLOSURE_ACTION = {"type": "move", "move": "STAY"}


def build_audit_payload(exchange, sender: str, outcome: str) -> dict:
    """The reveal we transmit at game end: full records incl. the nonces —
    in the REFERENCE AuditPayload envelope EXACTLY (sender / records /
    result_claim, nothing else). The reference parser is strict (a dataclass
    built via cls(**data)): a missing `sender` is rejected outright and any
    extra key of ours would reject the whole audit (2026-07-24 live cross-
    team finding — our envelope without `sender` was refused, voiding an
    otherwise clean 35-turn game on the counterparty's side)."""
    return {
        "sender": sender,
        "records": list(exchange.own_records),
        "result_claim": outcome,
    }


def _sealed_barrier(payload: dict) -> list | None:
    action = payload.get("action")
    if not (isinstance(action, dict) and action.get("type") == "barrier"):
        return None
    return [action["cell"][0], action["cell"][1]]


def verify_declared(record: dict) -> dict:
    """Rules 15-16: what a peer DECLARED live beside its commit must match
    what its reveal proves it sealed. Returns the declared block ({} when
    the record carries none — commit-only halves, geometric records and
    pre-upgrade logs derive nothing, they are not refused)."""
    payload, declared = record.get("payload"), record.get("declared")
    if not isinstance(payload, dict) or not isinstance(declared, dict):
        return {}
    placed = declared.get("barrier_placed")
    if (list(placed) if placed is not None else None) != _sealed_barrier(payload):
        raise GameRuleError(
            f"step {payload.get('step')}: live barrier declaration {placed} "
            "does not match the sealed action - tampering evidence")
    hint = declared.get("hint")
    if hint is not None and hint != payload.get("hint"):
        raise GameRuleError(
            f"step {payload.get('step')}: live hint differs from the sealed "
            "hint - tampering evidence")
    return declared


def _rules_from(terms: dict) -> RuleSet:
    block = terms["movement_and_barriers"]
    return RuleSet(int(block["max_barriers"]), int(block["max_moves"]),
                   int(block["survival_threshold"]))


def _apply(payload: dict, board: Board, positions: dict, rules: RuleSet) -> None:
    actor, action = Role(payload["role"]), payload["action"]
    try:
        if action["type"] == "barrier":
            if actor is not Role.POLICE:
                raise GameRuleError("only the police may place barriers")
            target = (action["cell"][0], action["cell"][1])
            validate_barrier_placement(board, rules, positions[Role.POLICE], target)
            board.add_barrier(target)
        else:
            positions[actor] = board.apply_move(positions[actor], Move[action["move"]])
    except GameRuleError:
        raise
    except Exception as error:
        raise GameRuleError(
            f"illegal revealed action at step {payload['step']}: {error}"
        ) from error


def reconstruct(own_records: list, their_records: list, shared_terms: dict,
                expected_sub_game: int | None = None) -> dict:
    """Replay both sides' revealed actions; returns the reconstructed
    {digest, outcome, turns_completed}. Raises GameRuleError on illegal
    physics, a violated capture-truth duty, a live declaration the reveal
    contradicts, or a record sealed for another sub-game — all tampering."""
    grid, cop_start, thief_start = geometry(shared_terms)
    board, rules = Board(grid), _rules_from(shared_terms)
    positions = {Role.POLICE: cop_start, Role.THIEF: thief_start}
    turns, outcome = 0, Outcome.ONGOING
    # Per-sender numbering: BOTH sides seal steps 1, 2, 3... — the game
    # order is (step, actor) with the thief first at equal step numbers
    # (reference cadence: the thief opens every round).
    entries = sorted(
        ((r["payload"], verify_declared(r))
         for r in list(own_records) + list(their_records)
         # typed records (the sealed step-zero declaration) are not actions:
         # they replay nothing and their key set is their own
         if "payload" in r and "type" not in r["payload"]),
        key=lambda e: (e[0]["step"], 0 if e[0]["role"] == Role.THIEF.value else 1))
    for payload, declared in entries:
        if expected_sub_game is not None \
                and payload.get("sub_game") != expected_sub_game:
            raise GameRuleError(
                f"step {payload['step']}: sealed for sub-game "
                f"{payload.get('sub_game')!r} but this audit is sub-game "
                f"{expected_sub_game!r} - a re-presented record from another "
                "game is tampering evidence")
        if outcome is not Outcome.ONGOING:
            if payload["action"] != _CLOSURE_ACTION or Role(payload["role"]) is Role.POLICE:
                raise GameRuleError(
                    f"step {payload['step']}: a real action after game end - tampering evidence")
            continue
        _apply(payload, board, positions, rules)
        cop_cell, thief_cell = positions[Role.POLICE], positions[Role.THIEF]
        if Role(payload["role"]) is Role.POLICE:
            claim = declared.get("capture_claim")
            if claim is not None and [cop_cell[0], cop_cell[1]] != list(claim):
                raise GameRuleError(
                    f"step {payload['step']}: live capture claim {list(claim)} "
                    "names a cell the revealed action never reached - a false "
                    "claim (rules 21-22) is tampering evidence")
            # Only the cop's OWN action can prove a capture live (claim or
            # barrier declaration); the truth duty makes the thief concede.
            if cop_cell == thief_cell or board.is_barrier(thief_cell) \
                    or board.is_surrounded(thief_cell):
                outcome = Outcome.CAPTURE
        else:
            if board.is_surrounded(thief_cell) or board.is_barrier(thief_cell):
                outcome = Outcome.CAPTURE  # walked into a pocket: must concede
                continue
            turns += 1  # the thief's step ticks the round clock (it opens)
            if turns >= rules.survival_threshold or turns >= rules.max_moves:
                outcome = Outcome.SURVIVAL  # survival counts the thief's own steps
    if outcome is Outcome.ONGOING:
        raise GameRuleError("revealed records end with the game still ongoing")
    state = {
        "positions": {role.value: list(cell) for role, cell in positions.items()},
        "barriers": sorted([list(cell) for cell in board.barriers]),
        "turns_completed": turns,
        "outcome": outcome.value,
    }
    return {
        "digest": hashlib.sha256(canonical(state).encode("utf-8")).hexdigest(),
        "outcome": outcome.value,
        "turns_completed": turns,
    }


def consistent(reconstruction: dict, outcome: Outcome, turns_completed: int) -> bool:
    """Does the revealed physics reproduce the game this peer lived?"""
    return (reconstruction["outcome"] == outcome.value
            and reconstruction["turns_completed"] == turns_completed)
