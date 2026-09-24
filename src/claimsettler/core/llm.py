"""Shared LLM-call abstraction, used by PredictionModel (prediction/reasoner.py)
and VSA's query rewrite / grounded response generation (mcp_servers/kma/vsa/*).

Config-selected like the KMA/VSA providers: LLM_PROVIDER=anthropic|fake.
"""

from __future__ import annotations

from typing import Protocol

from claimsettler.core.config import Settings


class LLMClient(Protocol):
    async def complete(self, *, system: str, prompt: str, max_tokens: int = 1024) -> str: ...


class AnthropicLLMClient:
    """Real implementation — requires ANTHROPIC_API_KEY."""

    def __init__(self, api_key: str, model: str) -> None:
        import anthropic

        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model

    async def complete(self, *, system: str, prompt: str, max_tokens: int = 1024) -> str:
        response = await self._client.messages.create(
            model=self._model,
            system=system,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in response.content if block.type == "text")


class FakeLLMClient:
    """In-memory stand-in so the full Phase 1 flow runs without an API key.
    Deterministic, rule-of-thumb behavior — good enough for demos/tests, not
    a substitute for the real model's judgment. Recognizes the three prompt
    shapes used in this codebase (PredictionModel's structured recommendation
    format, VSA's query rewrite, and grounded response generation) so every
    call site gets a usable response rather than one canned string leaking
    into contexts it doesn't fit (e.g. polluting a rewritten search query)."""

    async def complete(self, *, system: str, prompt: str, max_tokens: int = 1024) -> str:
        if "RECOMMENDATION:" in system:
            return (
                "RECOMMENDATION: APPROVE\n"
                "CONFIDENCE: 0.6\n"
                "RATIONALE: [fake-llm] No contradicting evidence found in the policy or similar-claims "
                "summary provided. This is a placeholder response from FakeLLMClient — set "
                "LLM_PROVIDER=anthropic and ANTHROPIC_API_KEY to use a real model."
            )
        if "rewrite" in system.lower():
            # Identity rewrite: safest fake behavior for a query-rewrite call
            # is to pass the query through unchanged, not synthesize new text.
            return prompt
        return (
            "[fake-llm] Based on the provided context, here is a placeholder grounded response. "
            "Set LLM_PROVIDER=anthropic and ANTHROPIC_API_KEY to use a real model."
        )


def build_llm_client(settings: Settings) -> LLMClient:
    if settings.llm_provider == "anthropic":
        if not settings.anthropic_api_key:
            raise ValueError("LLM_PROVIDER=anthropic requires ANTHROPIC_API_KEY")
        return AnthropicLLMClient(api_key=settings.anthropic_api_key, model=settings.anthropic_model)
    return FakeLLMClient()
