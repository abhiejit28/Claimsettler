"""Grounded, explainable response generation. Every response includes
citations to originating documents; retrieved chunks/model version/
confidence should be captured in the audit trail by the caller (VSA itself
is a library used by both MCP tool handlers and in-proc subagents, so it
does not write audit events directly — see mcp_servers/kma/server.py)."""

from __future__ import annotations

from claimsettler.core.llm import LLMClient
from claimsettler.mcp_servers.kma.ingestion.store import VectorMatch

_SYSTEM_PROMPT = (
    "You are an insurance claims assistant. Answer the question using ONLY the "
    "provided context chunks. If the context does not contain the answer, say so "
    "explicitly rather than guessing. Cite which chunk(s) support each claim."
)


async def generate_grounded_response(
    query: str, matches: list[VectorMatch], llm: LLMClient
) -> tuple[str, list[dict]]:
    if not matches:
        return "No relevant documents found.", []

    context = "\n\n".join(f"[chunk {i}] {m.record.text}" for i, m in enumerate(matches))
    prompt = f"Context:\n{context}\n\nQuestion: {query}"
    answer = await llm.complete(system=_SYSTEM_PROMPT, prompt=prompt, max_tokens=512)

    citations = [
        {"chunk_index": i, "document_type": m.record.metadata.get("document_type"), "score": m.score}
        for i, m in enumerate(matches)
    ]
    return answer, citations
