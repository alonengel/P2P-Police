"""TalkChain tests: template default at zero tokens, every_n_steps throttle,
unconditional fallback on provider failure, word cap on every path."""

import random
from pathlib import Path

from p2p_police.infra.llm_provider import TokenMeter
from p2p_police.shared.config import Config
from p2p_police.strategy.talk_providers import TalkChain, build_talk_chain


class BoomProvider:
    def __init__(self) -> None:
        self.meter = TokenMeter()
        self.calls = 0

    def generate(self, claim: str, arena: str, max_words: int) -> str:
        self.calls += 1
        raise RuntimeError("provider down")


class ChattyProvider(BoomProvider):
    def generate(self, claim: str, arena: str, max_words: int) -> str:
        self.calls += 1
        return " ".join(["word"] * 50)[: max_words * 5]


def test_template_only_chain_costs_zero_tokens() -> None:
    chain = TalkChain(None, 1, "New York", 15, random.Random(0))
    for step in range(1, 6):
        assert len(chain.render("N", step).split()) <= 15
    assert chain.meter.total == 0


def test_provider_failure_falls_back_to_template() -> None:
    provider = BoomProvider()
    chain = TalkChain(provider, 1, "", 15, random.Random(0))
    text = chain.render("E", 1)
    assert text and len(text.split()) <= 15
    assert provider.calls == 1


def test_every_n_steps_throttles_llm_calls() -> None:
    provider = ChattyProvider()
    chain = TalkChain(provider, 3, "", 15, random.Random(0))
    for step in range(1, 10):
        chain.render("S", step)
    assert provider.calls == 3  # steps 3, 6, 9


def test_build_talk_chain_defaults_to_template(config_dir: Path) -> None:
    chain = build_talk_chain(Config.load(config_dir), random.Random(0))
    assert chain.provider is None
    assert chain.max_words == 15
