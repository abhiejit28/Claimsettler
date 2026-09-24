"""FraudAgent MCP server — independent MCP server (not a subagent), invoked
by Adjuster Agent. Two tools per the confirmed design: `assess_claim`
(verdict + confidence + rule hits, no ML detail) and `explain_fraud`
(detailed reasoning, called only when the verdict is fraud).

Run: python -m claimsettler.mcp_servers.fraud_agent.server
"""

from __future__ import annotations

import os
from typing import Any

from mcp.server.mcpserver import MCPServer

from claimsettler.core.audit.models import AuditEvent
from claimsettler.core.audit.postgres_sink import PostgresAuditSink
from claimsettler.core.config import get_settings
from claimsettler.shared.correlation import get_trace_id
from claimsettler.storage.db import Database

from .fraud_detector import FraudDetection, detect
from .rule_engine_agent import run_rule_engine

server = MCPServer(name="fraud-agent")
_settings = get_settings()
_db = Database(_settings)
_audit = PostgresAuditSink(_db.session_factory)

# Phase 1: in-process cache of the last assessment per claim, so explain_fraud
# doesn't need to recompute or accept the full claim payload again. Fine at
# this scale for a single long-running MCP server process.
_last_assessment: dict[str, FraudDetection] = {}


@server.tool()
async def assess_claim(
    claim_id: str,
    claim_data: dict[str, Any],
    policy_data: dict[str, Any],
    existing_claim_ids_for_policy: list[str] | None = None,
) -> dict[str, Any]:
    """Step 1: RuleEngineAgent. A rejection is immediate and final (Phase 1
    has no ML modules yet — see docs/architecturePlan.md phased plan)."""
    rule_report = run_rule_engine(claim_data, policy_data, existing_claim_ids_for_policy)
    detection = detect(rule_report)
    _last_assessment[claim_id] = detection

    await _audit.write(
        AuditEvent(
            trace_id=get_trace_id(),
            actor_type="agent",
            actor_id="fraud_agent",
            action="fraud.assessment.completed",
            entity_type="claim",
            entity_id=claim_id,
            metadata={
                "verdict": detection.verdict,
                "confidence": detection.confidence,
                "rule_hits": detection.rule_hits,
            },
        )
    )
    return {
        "verdict": detection.verdict,
        "confidence": detection.confidence,
        "rule_hits": detection.rule_hits,
    }


@server.tool()
async def explain_fraud(claim_id: str) -> dict[str, Any]:
    """Step 2, fraud path only: detailed 'why fraud' reasoning report for
    the human adjuster."""
    detection = _last_assessment.get(claim_id)
    if detection is None:
        return {
            "verdict": "unknown",
            "explanation": f"No assessment on record for claim {claim_id}; call assess_claim first.",
            "rule_hits": [],
            "evidence": {},
        }

    explanation = (
        "Claim rejected by deterministic rule checks: " + "; ".join(detection.rule_hits)
        if detection.rule_hits
        else "No rule violations recorded for this claim."
    )
    return {
        "verdict": detection.verdict,
        "explanation": explanation,
        "rule_hits": detection.rule_hits,
        "evidence": {"confidence": detection.confidence, "ml_scores": detection.ml_scores},
    }


if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8101"))
    server.run(transport="streamable-http", host=host, port=port)
