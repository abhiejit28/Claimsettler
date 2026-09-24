"""In-process subagent. Searches historically similar claims and what
actions were taken on them, via VSA."""

from __future__ import annotations

from claimsettler.core.mcp_client import MCPClient


async def search_similar_claims(mcp: MCPClient, narrative: str, claim_type: str) -> dict:
    query = f"Past {claim_type} claims similar to: {narrative}"
    result = await mcp.call_tool(
        "kma",
        "search",
        {"query": query, "top_k": 5, "metadata_filter": {"document_type": "adjuster_feedback"}},
    )
    return {
        "summary": result.get("answer", ""),
        "citations": result.get("citations", []),
        "similar_count": len(result.get("matches", [])),
    }
