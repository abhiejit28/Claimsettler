"""Compliance Agent MCP server. Every uploaded document passes through this
tool BEFORE reaching KMA. Phase 1: field-aware NER-based PII masking
targeting GDPR. Phase 2: extensible to DPDPA/SOC2/HIPAA via policies/.

Run: python -m claimsettler.mcp_servers.compliance_agent.server
"""

from __future__ import annotations

import os
from typing import Any

from mcp.server.mcpserver import MCPServer

from claimsettler.core.config import get_settings

from .pii_detector import build_pii_detector
from .scanner import scan_and_mask as _scan_and_mask

server = MCPServer(name="compliance-agent")
_settings = get_settings()
_detector = build_pii_detector(_settings.pii_detector)


@server.tool()
def scan_and_mask(document: dict[str, Any]) -> dict[str, Any]:
    """Applies field-aware masking (unmask structural IDs / NER-mask free
    text / tokenize linkable-sensitive fields) to a normalized claim
    document. Returns {masked_document, report}."""
    return _scan_and_mask(document, _detector)


if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8102"))
    server.run(transport="streamable-http", host=host, port=port)
