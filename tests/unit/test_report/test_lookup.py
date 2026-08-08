"""lookup: config-artifact resolution, physics re-simulation, geometry."""

import pytest

from p2p_police.domain import protocol
from p2p_police.domain.errors import GameRuleError
from p2p_police.domain.primitives import Move, Role
from p2p_police.report import lookup
from p2p_police.sdk.sdk import SimulationSdk

TERMS = {
    "board_and_agents": {"grid_size": 7, "cop_start": [0, 0], "thief_start": [3, 3]},
    "movement_and_barriers": {"max_barriers": 14, "max_moves": 35,
                              "survival_threshold": 35},
    "pheromones": {"pheromone_center_intensity": 0.9, "pheromone_decay": 0.1,
                   "pheromone_grid_size": 5},
}


def _doc(moves: list[tuple[str, str]]) -> dict:
    records = []
    for step, (role, move) in enumerate(moves, start=1):
        records.append({"payload": {"step": step, "role": role,
                                    "action": {"type": "move", "move": move}}})
    return {"records": records, "opponent_records": []}


def test_recompute_digest_matches_direct_engine_run() -> None:
    doc = _doc([("police", "E"), ("thief", "W"), ("police", "S"), ("thief", "STAY")])
    engine = lookup.build_engine(TERMS)
    for payload in (r["payload"] for r in doc["records"]):
        protocol.apply_action(engine, Role(payload["role"]), payload["action"])
    assert lookup.recompute_digest(doc, TERMS) == protocol.end_state_digest(engine)
    assert Move  # imported for readers: actions are the protocol's move dicts


def test_recompute_digest_raises_on_illegal_logged_move() -> None:
    doc = _doc([("police", "N")])  # off-board from (0,0): tampering evidence
    with pytest.raises(GameRuleError):
        lookup.recompute_digest(doc, TERMS)


def test_geometry_from_terms_and_fallback() -> None:
    assert lookup.geometry(TERMS) == (7, (0, 0), (3, 3))
    assert lookup.geometry(None) == (7, (0, 0), (3, 3))


def test_verify_log_on_real_artifact_runs_physics_path() -> None:
    """The committed E2E log + its archived config: crypto AND physics pass."""
    assert SimulationSdk.verify_log(
        "results/dev-history/results/log_anrbj666-vs-anrbj666_g01.json") == "Verified OK"


def _foreign_doc(positions: list) -> dict:
    """A completed hidden-wire game whose rival half is FOREIGN-schema
    (reference keys: step/position/move — no role, no action)."""
    theirs = [{"payload": {"step": step, "position": list(cell), "move": "E"},
               "nonce": "0" * 32, "commit": "c" * 64}
              for step, cell in enumerate(positions, start=1)]
    return {"wire_shape": "reference", "records": [], "opponent_records": theirs,
            "summary": {"outcome": "survival", "end_state_digest": "ab" * 32}}


def test_recompute_hidden_tolerates_a_foreign_schema_half() -> None:
    """Per-team payload schema: the log's own digest stands; the strict
    reconstruction never judges keys it does not own."""
    doc = _foreign_doc([(3, 3), (3, 4), (3, 5)])
    terms = dict(TERMS)
    assert lookup.recompute_hidden(doc, terms) == "ab" * 32


def test_recompute_hidden_still_convicts_derivable_violations() -> None:
    with pytest.raises(GameRuleError):  # (3,3) -> (0,0) is no legal step
        lookup.recompute_hidden(_foreign_doc([(3, 3), (0, 0)]), TERMS)


def test_verify_log_flags_digest_mismatch(tmp_path) -> None:
    import json
    from pathlib import Path

    doc = json.loads(Path("results/dev-history/results/log_anrbj666-vs-anrbj666_g01.json")
                     .read_text(encoding="utf-8"))
    doc["summary"]["end_state_digest"] = "0" * 64  # forged final state
    (tmp_path / "config" / "games").mkdir(parents=True)
    src = Path("results/dev-history/config/games")
    for artifact in src.glob("config_*.json"):
        (tmp_path / "config" / "games" / artifact.name).write_text(
            artifact.read_text(encoding="utf-8"), encoding="utf-8")
    log = tmp_path / "results" / "log.json"
    log.parent.mkdir()
    forged = dict(doc, game_id=doc["game_id"])
    log.write_text(json.dumps(forged), encoding="utf-8")
    assert SimulationSdk.verify_log(str(log)) == "TAMPERED"


def test_terms_resolve_from_the_friendlies_subdir(tmp_path) -> None:
    """config/games/ top level means COUNTED; uncounted sets live in
    config/games/friendlies/ — the replay verifier must find both, so a
    committed friendly log never degrades to seals-only verification."""
    import json

    name = "config_a-vs-b_g01.json"
    sub = tmp_path / "config" / "games" / "friendlies"
    sub.mkdir(parents=True)
    (sub / name).write_text(json.dumps(TERMS), encoding="utf-8")
    results = tmp_path / "results"
    results.mkdir()
    doc = {"game_id": "a-vs-b", "sub_game_number": 1}
    resolved = lookup.terms_for_log(doc, results / "log_a-vs-b_g01.json")
    assert resolved is not None and resolved["board_and_agents"]["grid_size"] == 7
