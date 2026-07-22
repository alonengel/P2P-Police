"""Tests for the CLI shell — argument surface only, no business logic here."""

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


def test_peer_parses_sparring_wire_shape_and_duplicate_flags() -> None:
    args = build_parser().parse_args(
        ["peer", "--sparring", "--wire-shape", "reference", "--duplicate-outbound"])
    assert args.sparring is True
    assert args.wire_shape == "reference"
    assert args.duplicate_outbound is True
