"""Rule 27 hardening: LLM free text may taunt, never carry coordinates —
digits are scrubbed from every provider's output and the prompt itself
forbids numbers, so no cloud model can leak a grid position."""

from types import SimpleNamespace

from p2p_police.infra.llm_provider import LlmTalkProvider, TokenMeter, _prompt


class LeakyProvider(LlmTalkProvider):
    """A model that (against instructions) names coordinates and numbers."""

    def _complete(self, prompt: str) -> tuple[str, int, int]:
        return "Catch me at (3,4) if you dare, I move north in 2 steps!", 5, 5


def passthrough_gatekeeper() -> SimpleNamespace:
    return SimpleNamespace(execute=lambda _service, call: call())


def test_generate_scrubs_every_digit() -> None:
    provider = LeakyProvider(passthrough_gatekeeper(), TokenMeter())
    text = provider.generate("north", "", 15)
    assert not any(ch.isdigit() for ch in text)
    assert "north" in text  # the directional claim survives the scrub


def test_word_cap_still_binds_after_scrub() -> None:
    provider = LeakyProvider(passthrough_gatekeeper(), TokenMeter())
    assert len(provider.generate("north", "", 5).split()) <= 5


def test_prompt_forbids_coordinates() -> None:
    prompt = _prompt("north", "", 15)
    assert "coordinates" in prompt and "digits" in prompt
