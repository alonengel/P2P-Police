"""Tests for the CLI shell — argument surface only, no business logic here."""

import json

import pytest

from p2p_police.cli import build_parser, main


def test_main_with_no_args_returns_zero() -> None:
    assert main([]) == 0


def test_version_flag_reports_code_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        build_parser().parse_args(["--version"])
    assert excinfo.value.code == 0
    assert "1.00" in capsys.readouterr().out


def test_peer_defaults_leave_sparring_and_drill_knobs_off() -> None:
    args = build_parser().parse_args(["peer"])
    assert args.sparring is False
    assert args.wire_shape is None
    assert args.duplicate_outbound is False
    assert args.counted is False  # lecturer-address interlock stays unarmed


def test_counted_flag_parses_on_peer_and_series_result() -> None:
    assert build_parser().parse_args(["peer", "--counted"]).counted is True
    series = build_parser().parse_args(
        ["series-result", "--game-id", "a-vs-b", "--counted"])
    assert series.counted is True
    assert build_parser().parse_args(
        ["series-result", "--game-id", "a-vs-b"]).counted is False


def test_peer_parses_sparring_wire_shape_and_duplicate_flags() -> None:
    args = build_parser().parse_args(
        ["peer", "--sparring", "--wire-shape", "reference", "--duplicate-outbound"])
    assert args.sparring is True
    assert args.wire_shape == "reference"
    assert args.duplicate_outbound is True


def test_series_result_accepts_repeated_results_dirs() -> None:
    args = build_parser().parse_args(
        ["series-result", "--game-id", "a-vs-b",
         "--results-dir", "police-results", "--results-dir", "thief-results"])
    assert args.results_dir == ["police-results", "thief-results"]
    assert build_parser().parse_args(
        ["series-result", "--game-id", "a-vs-b"]).results_dir is None


def _settled_log(directory, game_id: str, n: int) -> None:
    doc = {"game_uid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", "sub_game_number": n,
           "summary": {"outcome": "survival", "turns_completed": 35,
                       "audit": "Verified OK", "group_id": "anrbj666",
                       "opponent_group_id": "beta", "role": "police",
                       "ended_at": "2026-07-24T14:00:00+00:00",
                       "opponent_info": {"terms": {"num_games": 1},
                                         "identity": {"group_id": "beta"}}}}
    (directory / f"log_{game_id}_g{n:02d}.json").write_text(json.dumps(doc), encoding="utf-8")


def test_series_result_command_emits_the_conformant_result(tmp_path, config_dir, capsys) -> None:
    results = tmp_path / "results"
    results.mkdir()
    _settled_log(results, "anrbj666-vs-beta", 1)  # fixture config plays num_games=1
    code = main(["series-result", "--game-id", "anrbj666-vs-beta",
                 "--results-dir", str(results), "--config-dir", str(config_dir)])
    assert code == 0
    written = results / "result_anrbj666-vs-beta.json"
    doc = json.loads(written.read_text(encoding="utf-8"))
    assert doc["game_uid"] == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    assert doc["report_type"] == "final_game_result"
    assert "total_score" in capsys.readouterr().out


def test_series_result_command_refuses_unsettled_series(tmp_path, config_dir, capsys) -> None:
    results = tmp_path / "results"
    results.mkdir()
    code = main(["series-result", "--game-id", "anrbj666-vs-beta",
                 "--results-dir", str(results), "--config-dir", str(config_dir)])
    assert code == 1
    assert "REFUSED" in capsys.readouterr().out
    assert not (results / "result_anrbj666-vs-beta.json").exists()
