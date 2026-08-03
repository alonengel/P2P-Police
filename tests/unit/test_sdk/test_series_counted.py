"""Rule 52 structural guard: at most ONE counted (league-reported) series
per rival pairing. The ledger is COMMITTED (results/counted_series.json)
so the guard survives fresh clones and the sibling repo closing the
series; reads consult every supplied results dir plus the legacy
gitignored results/local/ copy (imreeyal review 2026-08-03, #4)."""

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


def test_ledger_records_identity_in_the_committed_path(tmp_path) -> None:
    import json

    series.record_counted(tmp_path, "a-vs-b", "uid-1", "msg-1")
    ledger = json.loads(
        (tmp_path / "counted_series.json").read_text(encoding="utf-8"))
    entry = ledger["a-vs-b"]
    assert entry["game_uid"] == "uid-1"
    assert entry["message_id"] == "msg-1"
    assert entry["reported_at"]


def test_sibling_repo_ledger_also_refuses(tmp_path) -> None:
    """The series may have been closed FROM the sibling repo: the guard
    reads every supplied results dir, not just ours."""
    ours, sibling = tmp_path / "ours", tmp_path / "sibling"
    ours.mkdir(), sibling.mkdir()
    series.record_counted(sibling, "a-vs-b", "uid-1", "msg-1")
    with pytest.raises(SeriesSettlementError, match="rule 52"):
        series.refuse_repeat_counted([ours, sibling], "a-vs-b", "uid-2")
    assert series.first_meeting([ours, sibling], "a-vs-b", "uid-2") is False


def test_legacy_gitignored_ledger_still_read(tmp_path) -> None:
    """Pre-durability ledgers under results/local/ keep protecting."""
    import json

    legacy = tmp_path / "local"
    legacy.mkdir()
    (legacy / "counted_series.json").write_text(json.dumps(
        {"a-vs-b": {"game_uid": "uid-1", "reported_at": "then"}}),
        encoding="utf-8")
    with pytest.raises(SeriesSettlementError, match="rule 52"):
        series.refuse_repeat_counted(tmp_path, "a-vs-b", "uid-2")
