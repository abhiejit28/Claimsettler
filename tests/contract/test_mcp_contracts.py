"""MCP contract tests: connect as a real MCP client to each running server
and assert its tool schemas haven't silently drifted. Guards the boundary
between MCP servers and their multiple consumers (Adjuster Agent, FNOL
Agent) — a server-side rename/reshape should fail here, not in production.
"""

from __future__ import annotations

import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

pytestmark = pytest.mark.usefixtures("mcp_servers")


async def _list_tool_names(url: str) -> set[str]:
    async with streamable_http_client(url) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()
            return {tool.name for tool in result.tools}


@pytest.mark.asyncio
async def test_kma_exposes_store_document_and_search():
    names = await _list_tool_names("http://127.0.0.1:8100/mcp")
    assert {"store_document", "search"} <= names


@pytest.mark.asyncio
async def test_fraud_agent_exposes_assess_and_explain():
    names = await _list_tool_names("http://127.0.0.1:8101/mcp")
    assert {"assess_claim", "explain_fraud"} <= names


@pytest.mark.asyncio
async def test_compliance_agent_exposes_scan_and_mask():
    names = await _list_tool_names("http://127.0.0.1:8102/mcp")
    assert "scan_and_mask" in names


@pytest.mark.asyncio
async def test_fraud_agent_assess_claim_input_schema_has_expected_fields():
    async with streamable_http_client("http://127.0.0.1:8101/mcp") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()
            tool = next(t for t in result.tools if t.name == "assess_claim")
            properties = tool.input_schema.get("properties", {})
            assert {"claim_id", "claim_data", "policy_data"} <= set(properties)
