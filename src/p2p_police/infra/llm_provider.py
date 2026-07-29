"""Trash-talk providers (Appendix VI Table 21). The MOVE is always Python -
these only render hint TEXT. Every call passes through the ApiGatekeeper;
every failure falls back to the free template so a game is never blocked.
"""

import json
import os
import subprocess

import httpx

from p2p_police.shared.gatekeeper import ApiGatekeeper, TransientProviderError


class TokenMeter:
    """Accumulates LLM token spend (rule 54: totals are sealed + reported)."""

    def __init__(self) -> None:
        self.input_tokens = 0
        self.output_tokens = 0

    def add(self, input_tokens: int, output_tokens: int) -> None:
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens

    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens


def _prompt(claim: str, arena: str, max_words: int) -> str:
    where = f" around {arena}" if arena else ""
    return (
        f"You are a cocky game agent{where}. In ONE sentence of at most "
        f"{max_words} words, taunt your rival while claiming you just moved "
        f"{claim}. Never mention numbers, digits, coordinates or grid "
        "positions. Output only the sentence."
    )


class LlmTalkProvider:
    """Base: subclasses implement _complete(prompt) -> (text, in_tok, out_tok)."""

    service = "default"

    def __init__(self, gatekeeper: ApiGatekeeper, meter: TokenMeter, model: str = "") -> None:
        self.gatekeeper = gatekeeper
        self.meter = meter
        self.model = model

    def generate(self, claim: str, arena: str, max_words: int) -> str:
        def call() -> str:
            text, tokens_in, tokens_out = self._complete(_prompt(claim, arena, max_words))
            self.meter.add(tokens_in, tokens_out)
            return text

        text = str(self.gatekeeper.execute(self.service, call)).strip()
        # rule 27 hardening: free text may taunt, never carry coordinates —
        # digits are scrubbed no matter what the model produced
        text = "".join(ch for ch in text if not ch.isdigit())
        return " ".join(text.split()[:max_words])  # the cap binds EVERY provider

    def _complete(self, prompt: str) -> tuple[str, int, int]:
        raise NotImplementedError

    def _post_json(self, url: str, payload: dict, headers: dict) -> dict:
        try:
            response = httpx.post(url, json=payload, headers=headers, timeout=20)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, json.JSONDecodeError) as error:
            raise TransientProviderError(f"{self.service}: {error}") from error


class OllamaProvider(LlmTalkProvider):
    service = "ollama"

    def _complete(self, prompt: str) -> tuple[str, int, int]:
        base = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        data = self._post_json(
            f"{base}/api/generate",
            {"model": self.model or "llama3.2", "prompt": prompt, "stream": False},
            {},
        )
        return data.get("response", ""), 0, 0  # local: zero API tokens


class ClaudeApiProvider(LlmTalkProvider):
    service = "claude"

    def _complete(self, prompt: str) -> tuple[str, int, int]:
        key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not key:
            raise TransientProviderError("claude: ANTHROPIC_API_KEY not set")
        data = self._post_json(
            "https://api.anthropic.com/v1/messages",
            {
                "model": self.model or "claude-haiku-4-5-20251001",
                "max_tokens": 60,
                "messages": [{"role": "user", "content": prompt}],
            },
            {"x-api-key": key, "anthropic-version": "2023-06-01"},
        )
        usage = data.get("usage", {})
        text = "".join(b.get("text", "") for b in data.get("content", []))
        return text, usage.get("input_tokens", 0), usage.get("output_tokens", 0)


class OpenRouterProvider(LlmTalkProvider):
    service = "openrouter"

    def _complete(self, prompt: str) -> tuple[str, int, int]:
        key = os.environ.get("OPENROUTER_API_KEY", "")
        if not key:
            raise TransientProviderError("openrouter: OPENROUTER_API_KEY not set")
        data = self._post_json(
            "https://openrouter.ai/api/v1/chat/completions",
            {
                "model": self.model or "openai/gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
            },
            {"Authorization": f"Bearer {key}"},
        )
        usage = data.get("usage", {})
        text = data["choices"][0]["message"]["content"]
        return text, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)


class ClaudeCliProvider(LlmTalkProvider):
    service = "claude"

    def _complete(self, prompt: str) -> tuple[str, int, int]:
        try:
            result = subprocess.run(
                ["claude", "-p", prompt],
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise TransientProviderError(f"claude_cli: {error}") from error
        return result.stdout, 0, 0  # subscription: metered by the account

PROVIDERS = {
    "ollama": OllamaProvider,
    "claude_api": ClaudeApiProvider,
    "claude_cli": ClaudeCliProvider,
    "openrouter": OpenRouterProvider,
}
