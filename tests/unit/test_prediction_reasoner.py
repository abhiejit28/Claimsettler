import pytest

from claimsettler.core.llm import FakeLLMClient
from claimsettler.prediction.reasoner import predict


@pytest.mark.asyncio
async def test_fake_llm_produces_parseable_recommendation():
    decision = await predict("Policy summary: clean. Similar claims: none flagged.", FakeLLMClient())
    assert decision.recommendation in ("approve", "reject")
    assert 0.0 <= decision.confidence <= 1.0
    assert decision.rationale


@pytest.mark.asyncio
async def test_unparseable_response_fails_safe_to_reject():
    class BrokenLLM:
        async def complete(self, *, system: str, prompt: str, max_tokens: int = 1024) -> str:
            return "I cannot help with that."

    decision = await predict("summary", BrokenLLM())
    assert decision.recommendation == "reject"
    assert decision.confidence == 0.0
