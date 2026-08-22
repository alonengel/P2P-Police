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
    talk = SimpleNamespace(meter=SimpleNamespace(total=7))
    return SimpleNamespace(config=config, opponent_group_id="imreeyal",
                           role=exchange.role, exchange=exchange, talk=talk)


def test_step_zero_is_records_zero_in_book_shape() -> None:
    exchange = _exchange("police")
    seal_step_zero(_runtime(exchange))
    record = exchange.own_records[0]
    payload = record["payload"]
    assert set(payload) == {"step", "type", "declaration_ref", "group_id",
                            "role", "sub_game_number", "github_commit",
                            "tokens_total"}
    assert payload["step"] == 0 and payload["type"] == "step_zero"
    assert payload["declaration_ref"] == "declaration_anrbj666-vs-imreeyal.json"
    assert payload["role"] == "police" and payload["sub_game_number"] == 1
    # cumulative usage AT SEAL TIME (the najamjad chain semantics): the
    # rival prices our window as next window's snapshot minus this one's
    assert payload["tokens_total"] == 7
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


def test_read_theirs_two_channel_verdict() -> None:
    """The rival's revealed step-zero vs its negotiate identity: same commit
    = no finding; different = a recorded finding; absent = (None, None)."""
    from p2p_police.wire.step_zero import read_theirs

    revealed = [{"payload": {"step": 0, "type": "step_zero",
                             "github_commit": "abc123"}, "nonce": "n", "commit": "c"}]
    zero, finding = read_theirs(revealed, {"github_commit": "abc123"})
    assert zero["github_commit"] == "abc123" and finding is None
    zero, finding = read_theirs(revealed, {"github_commit": "fff999"})
    assert zero is not None and "differs" in finding
    assert read_theirs([], {"github_commit": "abc123"}) == (None, None)
    # the repo-set spelling reads too (imreeyal's step-0 is type system_spec)
    foreign = [{"payload": {"step": 0, "type": "system_spec",
                            "github_commit": "abc123"}, "nonce": "n", "commit": "c"}]
    zero, finding = read_theirs(foreign, {"github_commit": "abc123"})
    assert zero["github_commit"] == "abc123" and finding is None


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
