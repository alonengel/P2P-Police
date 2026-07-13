"""Opponent honesty profiler - the advisory layer over lie detection.

Algorithmic core: after every audit the rival's TRUE intent flags are
revealed (apply_revealed_verdicts); this profiler accumulates their honesty
rate across games and advises the belief map how hard to weigh their claims.
An optional LLM pass (behind the gatekeeper, off by default) can classify a
single hint's tone as a tiebreaker - ADVISORY ONLY: it can never override
the scent evidence, and moves stay pure Python (rule 25).
"""

import json
from pathlib import Path

PROFILE_PATH = Path("results/opponent_profiles.json")
NEUTRAL_HONESTY = 0.5


class OpponentProfiler:
    """Input: audited intent flags per opponent. Output: honesty rate and
    advised claim weights. Persists across games (league memory)."""

    def __init__(self, path: Path = PROFILE_PATH) -> None:
        self._path = path
        self._profiles: dict[str, dict] = {}
        if path.is_file():
            self._profiles = json.loads(path.read_text(encoding="utf-8"))

    def record_audited_verdicts(self, opponent: str, verdicts: list[bool]) -> None:
        profile = self._profiles.setdefault(opponent, {"truths": 0, "hints": 0})
        profile["truths"] += sum(1 for v in verdicts if v)
        profile["hints"] += len(verdicts)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._profiles, indent=2), encoding="utf-8")

    def honesty_rate(self, opponent: str) -> float:
        profile = self._profiles.get(opponent)
        if not profile or not profile["hints"]:
            return NEUTRAL_HONESTY
        return profile["truths"] / profile["hints"]

    def advised_weights(self, opponent: str) -> tuple[float, float]:
        """(inside, outside) claim weights for BeliefMap.observe_hint.

        A chronic liar's claims get INVERTED weight even before the per-hint
        scent check; a saint's claims get amplified. Bounded so the scent
        evidence always remains the dominant signal.
        """
        honesty = self.honesty_rate(opponent)
        inside = 0.4 + 2.6 * honesty       # 0.4 (liar) .. 3.0 (honest)
        outside = 3.0 - 2.6 * honesty      # mirrored
        return (inside, outside)
