"""In-process subagent (never its own MCP server). Retrieves policy/claim
rule documents from VSA via prompt-driven retrieval."""

from __future__ import annotations

from claimsettler.core.mcp_client import MCPClient


async def search_policy(mcp: MCPClient, policy_id: str, claim_type: str) -> dict:
    query = f"Coverage terms, exclusions, and limits for policy {policy_id}, claim type {claim_type}"
    result = await mcp.call_tool(
        "kma",
        "search",
        {"query": query, "top_k": 5, "metadata_filter": {"policy_id": policy_id}},
    )
    return {
        "policy_id": policy_id,
        "summary": result.get("answer", ""),
        "citations": result.get("citations", []),
    }
