"""LLM-driven query rewriting/normalization to improve retrieval quality by
normalizing insurance terminology (e.g. 'fender bender' -> 'collision
damage claim')."""

from __future__ import annotations

from claimsettler.core.llm import LLMClient

_SYSTEM_PROMPT = (
    "You rewrite insurance-domain search queries to improve retrieval against a "
    "policy/claims knowledge base. Normalize colloquial terms to standard insurance "
    "terminology. Return only the rewritten query, nothing else."
)


async def rewrite_query(query: str, llm: LLMClient) -> str:
    rewritten = await llm.complete(system=_SYSTEM_PROMPT, prompt=query, max_tokens=128)
    return rewritten.strip() or query
