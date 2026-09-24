"""Thin wrapper around the MCP SDK client. Resolves a logical server name
(configured in core/config.py) to a Streamable HTTP URL and calls a tool.

Each MCP server (KMA, FraudAgent, ComplianceAgent) is its own long-running
process; this client opens a short-lived session per call, which is fine at
this scale (50k claims/yr) and keeps call sites simple.
"""

from __future__ import annotations

import json
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from claimsettler.core.config import Settings
from claimsettler.core.errors import MCPCallError


class MCPClient:
    def __init__(self, settings: Settings) -> None:
        self._server_urls = {
            "kma": settings.mcp_kma_url,
            "fraud_agent": settings.mcp_fraud_agent_url,
            "compliance_agent": settings.mcp_compliance_agent_url,
        }

    async def call_tool(self, server: str, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        url = self._server_urls.get(server)
        if url is None:
            raise MCPCallError(server, tool, f"unknown MCP server '{server}'")

        try:
            async with streamable_http_client(url) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool, arguments)
        except Exception as exc:
            raise MCPCallError(server, tool, str(exc)) from exc

        if result.is_error:
            detail = result.content[0].text if result.content else "unknown MCP error"
            raise MCPCallError(server, tool, detail)

        if result.structured_content is not None:
            return dict(result.structured_content)

        text = result.content[0].text if result.content else "{}"
        return json.loads(text)
