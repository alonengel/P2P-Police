"""TalkChain: the configured provider with an unconditional template fallback
and the every_n_steps throttle (Appendix VI Table 21). A whole series can run
at zero tokens on the template; an LLM failure NEVER blocks a game.
"""

import random

from p2p_police.infra.llm_provider import PROVIDERS, TokenMeter
from p2p_police.shared.gatekeeper import ApiGatekeeper
from p2p_police.strategy.hints import TAUNTS, TEMPLATES, enforce_word_limit


class TalkChain:
    """Input: claim + step number. Output: hint text (<= max_words, always)."""

    def __init__(
        self,
        provider,
        every_n_steps: int,
        arena: str,
        max_words: int,
        rng: random.Random,
        opaque: bool = False,
    ) -> None:
        self.provider = provider  # None => template only
        self.every_n_steps = max(1, every_n_steps)
        self.arena = arena
        self.max_words = max_words
        self.rng = rng
        self.opaque = opaque  # taunts only: never narrate our heading
        self.meter = provider.meter if provider else TokenMeter()

    def _template_text(self, claim: str) -> str:
        bank = TAUNTS if self.opaque else TEMPLATES[claim]
        return enforce_word_limit(self.rng.choice(bank), self.max_words)

    def render(self, claim: str, step: int) -> str:
        """LLM only every N steps; template otherwise and on ANY failure."""
        if self.opaque or self.provider is None or step % self.every_n_steps != 0:
            return self._template_text(claim)
        try:
            text = self.provider.generate(claim, self.arena, self.max_words)
            return text or self._template_text(claim)
        except Exception:  # any provider trouble -> free template, game goes on
            return self._template_text(claim)


def build_talk_chain(config, rng: random.Random, gatekeeper=None) -> TalkChain:
    """Assemble from [trash_talk]/[llm] (private) + world (signed) config.
    ONE gatekeeper per run when the caller passes it (single call_log)."""
    trash = config.private.get("trash_talk", {})
    provider_name = trash.get("provider", "template")
    world = config.shared["world"]
    provider = None
    if provider_name in PROVIDERS:
        gatekeeper = gatekeeper or ApiGatekeeper(config.rate_limits)
        model = config.private.get("llm", {}).get("model", "")
        provider = PROVIDERS[provider_name](gatekeeper, TokenMeter(), model)
    return TalkChain(
        provider,
        int(trash.get("every_n_steps", 1)),
        world.get("map_area", ""),
        int(world["hint_max_words"]),
        rng,
        opaque=str(trash.get("hint_mode", "candid")).lower() == "opaque",
    )
