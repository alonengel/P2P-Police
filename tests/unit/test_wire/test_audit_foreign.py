"""Judging a FOREIGN-schema rival's audit half fairly (2026-07-24 finding).

The record shapes here reproduce the foreign-schema rival's REAL reveal
form from the first full cross-team games: reference sealing — per-step
payloads keyed step/state/position/move/intent/verdict/hint/
prompt_discussion/model/tokens/... (no role, no action) plus the step-0
system_spec record whose commit never crosses the live turn wire. Only the
COMMIT construction (SHA256(canonical(payload)+'|'+nonce)) is the shared
contract; the payload schema is per-team. The audit must verify such a half
clean, degrade to derivable checks, and report the digest tier as
not-comparable — while a genuinely forged commit still reads TAMPERED."""

import hashlib

from p2p_police.domain import crypto
from p2p_police.domain.primitives import Role
from p2p_police.wire import audit_foreign
from p2p_police.wire.hidden_exchange import HiddenExchange


def _seal(payload: dict) -> dict:
    nonce = crypto.new_nonce()
    material = f"{crypto.canonical(payload)}|{nonce}"
    commit = hashlib.sha256(material.encode("utf-8")).hexdigest()
    return {"payload": payload, "nonce": nonce, "commit": commit}


def reference_step_record(step: int, position: tuple, move: str) -> dict:
    """One rival half-turn sealed the way the reference sealing module does."""
    return _seal({
        "step": step,
        "state": f"grid=7x7;self={list(position)};barriers=[]",
        "position": list(position),
        "move": move,
        "intent": True,
        "verdict": True,
        "hint": "Crowds near the docks hide anyone.",
        "prompt_discussion": {"llm_prompt": "", "llm_reasoning": "",
                              "bluff_classification": True},
        "model": "none", "tokens_step": 0, "tokens_total": 0,
        "response_seconds": 0.1, "random_move": False,
    })


def reference_spec_record() -> dict:
    """The step-0 system_spec record: sealed at construction, revealed at
    audit, its commit NEVER sent inside a live TurnMessage."""
    return _seal({"step": 0, "type": "system_spec", "spec": {"os": "Windows"},
                  "model": "none", "code_version": "3.0", "group_name": "rival",
                  "sub_game_number": 1})


def rival_walk(steps: int = 5) -> list[dict]:
    cells = [(3, 3 + (i % 2)) for i in range(steps)]  # E/W shuffle: legal
    return [reference_step_record(i + 1, cells[i], "E" if i % 2 == 0 else "W")
            for i in range(steps)]


def exchange_with_live_commits(records: list[dict]) -> HiddenExchange:
    feed = [{"step": r["payload"]["step"], "sender": "thief", "commit": r["commit"],
             "kind": "turn", "turn": r["payload"]["step"]} for r in records]
    exchange = HiddenExchange(Role.POLICE, 1, [].append,
                              lambda _w, _d=None: feed.pop(0), turn_timeout=5)
    for record in records:
        exchange.receive_turn(record["payload"]["step"])
    return exchange


def test_foreign_schema_rival_reveals_verify_ok() -> None:
    """Commit-clean reference reveals — including the extra step-0 spec
    record — must verify, and the payloads must merge for the later tiers."""
    walk = rival_walk()
    exchange = exchange_with_live_commits(walk)
    reveals = [reference_spec_record(), *walk]
    assert exchange.audit_reveals(reveals) == "Verified OK"
    assert exchange.their_records[0]["payload"] == walk[0]["payload"]
    assert exchange.their_records[-1]["nonce"] == walk[-1]["nonce"]


def test_forged_commit_in_the_same_reveal_set_is_tampered() -> None:
    walk = rival_walk()
    exchange = exchange_with_live_commits(walk)
    forged = dict(walk[2], payload=dict(walk[2]["payload"], position=[6, 6]))
    reveals = [reference_spec_record(), *walk[:2], forged, *walk[3:]]
    assert exchange.audit_reveals(reveals) == "TAMPERED"


def test_a_live_commit_left_unrevealed_is_tampered() -> None:
    walk = rival_walk()
    exchange = exchange_with_live_commits(walk)
    assert exchange.audit_reveals([reference_spec_record(), *walk[:-1]]) == "TAMPERED"


def test_reference_schema_does_not_parse_as_ours_but_our_records_do() -> None:
    assert not audit_foreign.parses_as_ours(rival_walk())
    payload = crypto.build_step_payload(1, "thief", 1, "d" * 64,
                                        {"type": "move", "move": "E"}, "h", True)
    ours = [{"payload": payload, "commit": "c" * 64}]
    assert audit_foreign.parses_as_ours(ours)


def test_step_continuity_derivable_from_foreign_steps() -> None:
    walk = rival_walk()
    assert audit_foreign.continuity_ok([reference_spec_record(), *walk])
    gapped = [reference_spec_record(), *walk[:2], *walk[3:]]
    assert not audit_foreign.continuity_ok(gapped)


def test_movement_legality_derivable_from_revealed_positions() -> None:
    walk = rival_walk()
    assert audit_foreign.movement_ok(walk, grid=7)
    teleport = dict(walk[3], payload=dict(walk[3]["payload"], position=[0, 0]))
    assert not audit_foreign.movement_ok([*walk[:3], teleport, *walk[4:]], grid=7)
    off_board = dict(walk[0], payload=dict(walk[0]["payload"], position=[7, 3]))
    assert not audit_foreign.movement_ok([off_board, *walk[1:]], grid=7)


def test_judge_reports_digest_as_not_comparable_never_false() -> None:
    """Different per-team digest constructions cannot be compared: the tier
    reports None (JSON null), not a false accusation."""
    verdict = audit_foreign.judge(rival_walk(), grid=7)
    assert verdict == {"audit": "Verified OK", "digest_match": None,
                       "disputed_capture": None}
    broken = rival_walk()
    broken[1]["payload"]["position"] = [6, 0]  # underivable jump
    assert audit_foreign.judge(broken, grid=7)["audit"] == "TAMPERED"


def test_commit_clean_is_schema_agnostic() -> None:
    assert audit_foreign.commit_clean(reference_spec_record())
    sealed = reference_step_record(1, (3, 3), "STAY")
    assert audit_foreign.commit_clean(sealed)
    assert not audit_foreign.commit_clean(dict(sealed, nonce="00" * 16))
    assert not audit_foreign.commit_clean({"commit": sealed["commit"]})
