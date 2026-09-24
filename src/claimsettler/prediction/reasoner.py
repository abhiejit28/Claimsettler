"""PredictionModel — a direct in-process call (never MCP, never a subagent
orchestrator). It is an LLM-based reasoning step (confirmed with the user:
not a trained tabular classifier), reasoning over the combined
PolicySearchAgent + SimilarClaimAgent text summary directly — no
feature-engineering bridge needed.
"""

from __future__ import annotations

import re

from claimsettler.core.llm import LLMClient
from claimsettler.shared.types import PredictionDecision

from .prompts import SYSTEM_PROMPT, build_prediction_prompt

_RESPONSE_PATTERN = re.compile(
    r"RECOMMENDATION:\s*(?P<rec>APPROVE|REJECT).*?"
    r"CONFIDENCE:\s*(?P<conf>[0-9.]+).*?"
    r"RATIONALE:\s*(?P<rationale>.+)",
    re.IGNORECASE | re.DOTALL,
)


async def predict(combined_summary: str, llm: LLMClient) -> PredictionDecision:
    raw = await llm.complete(
        system=SYSTEM_PROMPT, prompt=build_prediction_prompt(combined_summary), max_tokens=512
    )
    match = _RESPONSE_PATTERN.search(raw)
    if not match:
        # LLM didn't follow the format — fail safe to a low-confidence REJECT
        # so an ambiguous model response never silently becomes an approval.
        return PredictionDecision(recommendation="reject", confidence=0.0, rationale=raw.strip())

    recommendation = match.group("rec").lower()
    try:
        confidence = max(0.0, min(1.0, float(match.group("conf"))))
    except ValueError:
        confidence = 0.0
    rationale = match.group("rationale").strip()
    return PredictionDecision(recommendation=recommendation, confidence=confidence, rationale=rationale)
