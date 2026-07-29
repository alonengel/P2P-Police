"""Rule 52 structural guard: at most ONE counted (league-reported) series
per rival pairing. The ledger under results/local/ remembers every series
whose report email actually reached the league; the guard refuses a NEW
game_uid for a pairing already on it and stays permissive otherwise."""

import pytest

from p2p_police.sdk import counted_ledger as series
from p2p_police.sdk.series import SeriesSettlementError


def test_no_ledger_is_permissive(tmp_path) -> None:
    series.refuse_repeat_counted(tmp_path, "a-vs-b", "uid-1")  # no raise


def test_same_series_reclose_is_allowed(tmp_path) -> None:
    series.record_counted(tmp_path, "a-vs-b", "uid-1", "msg-1")
    series.refuse_repeat_counted(tmp_path, "a-vs-b", "uid-1")  # email retry


def test_second_counted_series_same_rival_is_refused(tmp_path) -> None:
    series.record_counted(tmp_path, "a-vs-b", "uid-1", "msg-1")
    with pytest.raises(SeriesSettlementError, match="rule 52"):
        series.refuse_repeat_counted(tmp_path, "a-vs-b", "uid-2")


def test_other_pairing_is_unaffected(tmp_path) -> None:
    series.record_counted(tmp_path, "a-vs-b", "uid-1", "msg-1")
    series.refuse_repeat_counted(tmp_path, "a-vs-c", "uid-9")  # no raise


def test_ledger_records_identity(tmp_path) -> None:
    import json

    series.record_counted(tmp_path, "a-vs-b", "uid-1", "msg-1")
    ledger = json.loads(
        (tmp_path / "local" / "counted_series.json").read_text(encoding="utf-8"))
    entry = ledger["a-vs-b"]
    assert entry["game_uid"] == "uid-1"
    assert entry["message_id"] == "msg-1"
    assert entry["reported_at"]
