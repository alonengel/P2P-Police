"""Peer per-window token usage from its sealed step-zero chain.

Decoded live against najamjad (2026-08-22): each side's step-zero carries
its CUMULATIVE usage at window start, per role process — so one window's
usage is the NEXT same-role window's snapshot minus its own, and the last
window of each chain has no successor seal. The numbers below are the real
series: the four checkable deltas reproduce their emailed per-window
claims digit-for-digit (5010/4273/5073/4163); the two tails are in-band
unknowable and must file null — our reports filed a false 0 against their
truthful 27,866 (the exact reader bug their own doc §9.5 warns about).
"""

import json

from p2p_police.domain.scoring import ScoreTable
from p2p_police.report.peer_tokens import series_total, usage_by_slot
from p2p_police.sdk.series import aggregate_series


def _slot(our_role: str, their_step0_tokens):
    zero = None if their_step0_tokens is None else {
        "tokens_total": their_step0_tokens}
    return {"summary": {"role": our_role, "opponent_step_zero": zero}}


NAJAMJAD = {  # our role alternates; snapshots are the real wire values
    1: _slot("police", 97), 2: _slot("thief", 97),
    3: _slot("police", 5107), 4: _slot("thief", 4370),
    5: _slot("police", 10180), 6: _slot("thief", 8533),
}


def test_deltas_reproduce_najamjad_emailed_claims_with_null_tails() -> None:
    assert usage_by_slot(NAJAMJAD) == {1: 5010, 2: 4273, 3: 5073, 4: 4163,
                                       5: None, 6: None}


def test_missing_snapshot_nulls_both_windows_it_would_settle() -> None:
    slots = {1: _slot("police", 97), 3: _slot("police", None),
             5: _slot("police", 10180)}
    assert usage_by_slot(slots) == {1: None, 3: None, 5: None}


def test_negative_delta_is_refused_never_a_negative_claim() -> None:
    slots = {1: _slot("police", 5000), 3: _slot("police", 97),
             5: _slot("police", 6000)}
    assert usage_by_slot(slots)[1] is None
    assert usage_by_slot(slots)[3] == 5903


def test_series_total_claims_only_when_every_window_is_known() -> None:
    assert series_total({1: 5010, 2: 4273}) == 9283
    assert series_total({1: 5010, 2: None}) is None
    assert series_total({}) is None


def test_single_window_series_has_no_successor_hence_null() -> None:
    assert usage_by_slot({1: _slot("police", 97)}) == {1: None}


TABLE = ScoreTable(capture_cop=20, capture_thief=5, survival_cop=5,
                   survival_thief=10, tie_score=2)
IDENTITY = {"group_id": "alpha", "repos": {}, "github_commit": "abc",
            "counted_games_played": 0}


def _write(directory, n, outcome, role, their_step0, our_tokens=None):
    summary = {"outcome": outcome, "turns_completed": 10,
               "audit": "Verified OK", "group_id": "alpha",
               "opponent_group_id": "beta", "role": role,
               "opponent_info": {"terms": {"num_games": 4}},
               "opponent_step_zero": {"tokens_total": their_step0}}
    if our_tokens is not None:
        summary["tokens_total"] = our_tokens
    doc = {"game_uid": "u-1", "sub_game_number": n, "summary": summary}
    (directory / f"log_a-vs-b_g{n:02d}.json").write_text(
        json.dumps(doc), encoding="utf-8")


def test_series_report_prices_peer_windows_and_never_fakes_totals(tmp_path) -> None:
    """End to end through the settled report: deltas fill the checkable
    windows, tails file null, and the peer's series total is null rather
    than an understating partial sum; our own column reads each window's
    summary meter (najamjad diff 2026-08-22: 0 filed vs truthful 27,866)."""
    _write(tmp_path, 1, "survival", "police", 97, our_tokens=11)
    _write(tmp_path, 2, "capture", "thief", 97)
    _write(tmp_path, 3, "survival", "police", 5107, our_tokens=4)
    _write(tmp_path, 4, "capture", "thief", 4370)
    doc, _ = aggregate_series(tmp_path, "a-vs-b", TABLE, 4, IDENTITY)
    assert [e["tokens"]["beta"] for e in doc["sub_games"]] == \
        [5010, 4273, None, None]
    assert [e["tokens"]["alpha"] for e in doc["sub_games"]] == [11, 0, 4, 0]
    assert doc["final_result"]["tokens_total_series"] == \
        {"alpha": 15, "beta": None}
