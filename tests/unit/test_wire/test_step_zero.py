"""The sealed step-zero declaration (book-attached 3-game-log shape): the
commit id travels as a signed record, revealed with the audit — and the
replay layers treat it as a declaration, never as an action."""

from types import SimpleNamespace

from p2p_police.domain import crypto
from p2p_police.wire import audit
from p2p_police.wire.hidden_exchange import HiddenExchange
from p2p_police.wire.step_zero import seal_step_zero

TERMS = {
    "board_and_agents": {"grid_size": 7, "cop_start": [0, 0], "thief_start": [3, 3]},
    "movement_and_barriers": {"max_barriers": 14, "max_moves": 35,
                              "survival_threshold": 2},
}


def _exchange(role_value: str) -> HiddenExchange:
    from p2p_police.domain.primitives import Role

    return HiddenExchange(Role(role_value), 1, lambda m: None, lambda *a: {},
                          turn_timeout=1, pending_cap=8)


def _runtime(exchange) -> SimpleNamespace:
    config = SimpleNamespace(group_id="anrbj666")
    return SimpleNamespace(config=config, opponent_group_id="imreeyal",
                           role=exchange.role, exchange=exchange)


def test_step_zero_is_records_zero_in_book_shape() -> None:
    exchange = _exchange("police")
    seal_step_zero(_runtime(exchange))
    record = exchange.own_records[0]
    payload = record["payload"]
    assert set(payload) == {"step", "type", "declaration_ref", "group_id",
                            "role", "sub_game_number", "github_commit"}
    assert payload["step"] == 0 and payload["type"] == "step_zero"
    assert payload["declaration_ref"] == "declaration_anrbj666-vs-imreeyal.json"
    assert payload["role"] == "police" and payload["sub_game_number"] == 1
    # sealed like a move: the commit re-verifies from payload + nonce
    assert crypto.verify_commit(payload, record["nonce"], record["commit"])


def test_move_payloads_still_demand_the_pinned_field_set() -> None:
    try:
        crypto.commit_hash({"step": 1, "role": "police"}, "aa")
    except ValueError as error:
        assert "missing fields" in str(error)
    else:  # pragma: no cover - the guard must hold
        raise AssertionError("untyped payload accepted without the field set")


def _move(step: int, role: str, move: str) -> dict:
    payload = crypto.build_step_payload(step, role, 1, "d", {"type": "move", "move": move},
                                        "h", True)
    nonce = crypto.new_nonce()
    return {"payload": payload, "nonce": nonce,
            "commit": crypto.commit_hash(payload, nonce)}


def test_reconstruct_skips_the_step_zero_declaration() -> None:
    """A typed record replays nothing: the reconstruction with and without
    the step-zero record derives the SAME digest (survival at threshold 2)."""
    thief = [_move(1, "thief", "N"), _move(2, "thief", "STAY")]
    cop = [_move(1, "police", "E")]  # the thief's 2nd step ends the game
    bare = audit.reconstruct(cop, thief, TERMS)
    exchange = _exchange("police")
    seal_step_zero(_runtime(exchange))
    with_zero = audit.reconstruct(exchange.own_records + cop, thief, TERMS)
    assert with_zero == bare and with_zero["outcome"] == "survival"
