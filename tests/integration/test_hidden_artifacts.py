"""League artifacts for hidden (reference-v3) games: the four Table-20 files
emitted from a hidden game's records verify through verify-log AND the pair
verifier, and every tamper family the hidden replay must catch is caught."""

import json
from pathlib import Path

import pytest
from hidden_helpers import ScriptedBrain, hidden_config, move, play_pair

from p2p_police.domain import crypto
from p2p_police.domain.primitives import Role
from p2p_police.report.pair_verify import verify_pair
from p2p_police.sdk.reporting import emit_artifacts
from p2p_police.sdk.sdk import SimulationSdk

pytestmark = pytest.mark.slow

COP_WALK = [move(d) for d in ("S", "S", "S", "E", "E", "E")]


def _emit_side(monkeypatch, config, runtime, report, into: Path) -> dict[str, Path]:
    into.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(into)  # artifacts land under this side's own tree
    return {Path(p).name: (into / p).resolve()
            for p in emit_artifacts(config, runtime, report)}


@pytest.fixture
def hidden_pair(config_dir, tmp_path, monkeypatch):
    """One finished hidden capture game, both sides' artifacts on disk."""
    config = hidden_config(config_dir)
    reports, _wire, police, thief = play_pair(
        config, ScriptedBrain(Role.POLICE, COP_WALK), ScriptedBrain(Role.THIEF, []))
    sides = {}
    for name, runtime in (("police", police), ("thief", thief)):
        sides[name] = _emit_side(monkeypatch, config, runtime, reports[name],
                                 tmp_path / name)
    return reports, sides


def test_hidden_game_emits_four_artifacts_that_verify(hidden_pair):
    reports, sides = hidden_pair
    for side in ("police", "thief"):
        names = sorted(sides[side])
        assert names == ["config_anrbj666-vs-anrbj666_g01.json",
                         "declaration_anrbj666-vs-anrbj666.json",
                         "log_anrbj666-vs-anrbj666_g01.json",
                         "result_anrbj666-vs-anrbj666.json"]
        log_path = sides[side]["log_anrbj666-vs-anrbj666_g01.json"]
        doc = json.loads(log_path.read_text(encoding="utf-8"))
        assert doc["wire_shape"] == "reference"  # routes verify-log (ADR-0008)
        assert doc["summary"]["outcome"] == "capture"
        assert SimulationSdk.verify_log(str(log_path)) == "Verified OK"


def test_both_sides_logs_pair_verify_as_one_game(hidden_pair):
    _reports, sides = hidden_pair
    row = verify_pair(sides["police"]["log_anrbj666-vs-anrbj666_g01.json"],
                      sides["thief"]["log_anrbj666-vs-anrbj666_g01.json"])
    assert row["overall"] == "Verified OK", row
    assert row["verdict_a"] == row["verdict_b"] == "Verified OK"
    assert row["problems"] == []
    assert row["sides"] == ["anrbj666", "anrbj666"]


def _reseal(record: dict) -> None:
    """Forge consistently: fresh nonce + commit over the doctored payload, so
    only the PHYSICS replay can catch it (the commit math reads clean)."""
    record["nonce"] = crypto.new_nonce()
    record["commit"] = crypto.commit_hash(record["payload"], record["nonce"])


def _rewritten(log_path: Path, mutate) -> Path:
    doc = json.loads(log_path.read_text(encoding="utf-8"))
    mutate(doc)
    out = log_path.with_name("log_tampered.json")
    out.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    return out


def test_illegal_revealed_action_is_tampering(hidden_pair):
    _reports, sides = hidden_pair

    def mutate(doc):
        doc["records"][0]["payload"]["action"] = {"type": "move", "move": "N"}  # off-board
        _reseal(doc["records"][0])

    bad = _rewritten(sides["police"]["log_anrbj666-vs-anrbj666_g01.json"], mutate)
    assert SimulationSdk.verify_log(str(bad)) == "TAMPERED"


def test_playing_past_a_capture_violates_the_concede_duty(hidden_pair):
    """Rules 21-22 at the audit: after the cop's capturing action the ONLY
    legal thief record is the action-free concession."""
    _reports, sides = hidden_pair

    def mutate(doc):
        closure = max((r for r in doc["records"] if r["payload"]["role"] == "thief"),
                      key=lambda r: r["payload"]["step"])
        closure["payload"]["action"] = {"type": "move", "move": "W"}  # played on
        _reseal(closure)

    bad = _rewritten(sides["thief"]["log_anrbj666-vs-anrbj666_g01.json"], mutate)
    assert SimulationSdk.verify_log(str(bad)) == "TAMPERED"


def test_dropping_the_wire_shape_marker_cannot_dodge_the_replay(hidden_pair):
    """Guard both routes: a hidden log stripped of its marker falls into the
    engine replay, where the post-capture closure is an illegal action —
    relabeling can only invalidate a log, never launder one (ADR-0008)."""
    _reports, sides = hidden_pair
    bad = _rewritten(sides["police"]["log_anrbj666-vs-anrbj666_g01.json"],
                     lambda doc: doc.pop("wire_shape"))
    assert SimulationSdk.verify_log(str(bad)) == "TAMPERED"
