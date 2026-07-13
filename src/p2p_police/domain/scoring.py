"""The fixed scoring table (rulebook ch. 3 + Appendix VI, all values fixed).

Points come from the signed config's `scoring` block — never hardcoded here —
but the STRUCTURE (which outcome pays whom) is the rulebook's and is
parity-locked with the twin repo.
"""

from dataclasses import dataclass

from p2p_police.domain.primitives import Outcome


@dataclass(frozen=True)
class ScoreTable:
    """The agreed point values (config `scoring`, Appendix VI: all fixed).

    Input: values from the signed game.json. Output: (cop, thief) point pairs.
    """

    capture_cop: int
    capture_thief: int
    survival_cop: int
    survival_thief: int
    tie_score: int
    technical_loss: int = 0

    def __post_init__(self) -> None:
        if any(
            v < 0
            for v in (
                self.capture_cop,
                self.capture_thief,
                self.survival_cop,
                self.survival_thief,
                self.tie_score,
                self.technical_loss,
            )
        ):
            raise ValueError("score values must be non-negative")

    def points_for(self, outcome: Outcome) -> tuple[int, int]:
        """Return (cop_points, thief_points) for a finished sub-game.

        Technical loss pays 0/0 (rulebook Table 2). ONGOING has no score —
        asking for one is a caller bug, so it raises.
        """
        if outcome is Outcome.CAPTURE:
            return (self.capture_cop, self.capture_thief)
        if outcome is Outcome.SURVIVAL:
            return (self.survival_cop, self.survival_thief)
        if outcome is Outcome.TECHNICAL_LOSS:
            return (self.technical_loss, self.technical_loss)
        raise ValueError(f"no score for unfinished outcome {outcome}")

    def points_for_name(self, outcome_name: str) -> tuple[int, int]:
        """Same table keyed by the serialized outcome value (log summaries)."""
        return self.points_for(Outcome(outcome_name))

    def series_tie_points(self) -> tuple[int, int]:
        """Both sides receive the tie score when a series ends level (ch. 9)."""
        return (self.tie_score, self.tie_score)
