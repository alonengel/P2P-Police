"""Scoring tests encode the fixed table (rule 48): capture 20/5, survival 5/10,
technical loss 0/0, series tie 2/2. Values flow from config, never code."""

import pytest

from p2p_police.domain.primitives import Outcome
from p2p_police.domain.scoring import ScoreTable

TABLE = ScoreTable(
    capture_cop=20, capture_thief=5, survival_cop=5, survival_thief=10, tie_score=2
)


def test_capture_pays_cop_20_thief_5() -> None:
    assert TABLE.points_for(Outcome.CAPTURE) == (20, 5)


def test_survival_pays_cop_5_thief_10() -> None:
    assert TABLE.points_for(Outcome.SURVIVAL) == (5, 10)


def test_technical_loss_pays_zero_zero() -> None:
    assert TABLE.points_for(Outcome.TECHNICAL_LOSS) == (0, 0)


def test_series_tie_pays_both_sides_2() -> None:
    assert TABLE.series_tie_points() == (2, 2)


def test_ongoing_has_no_score() -> None:
    with pytest.raises(ValueError):
        TABLE.points_for(Outcome.ONGOING)


def test_negative_values_are_rejected() -> None:
    with pytest.raises(ValueError):
        ScoreTable(
            capture_cop=-1, capture_thief=5, survival_cop=5, survival_thief=10, tie_score=2
        )
