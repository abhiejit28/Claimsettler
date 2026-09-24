"""Adjuster Agent — supervisor agent, domain-expert in claim validation.
Orchestrates PolicySearchAgent + SimilarClaimAgent as in-process subagents,
calls FraudAgent via MCP (independent server), and PredictionModel as a
direct in-process LLM call."""

from __future__ import annotations

from dataclasses import dataclass

from claimsettler.core.audit.interfaces import AuditSink
from claimsettler.core.audit.models import AuditEvent
from claimsettler.core.llm import LLMClient
from claimsettler.core.mcp_client import MCPClient
from claimsettler.prediction.reasoner import predict
from claimsettler.shared.correlation import get_trace_id
from claimsettler.shared.types import PredictionDecision

from .subagents.policy_search_agent import search_policy
from .subagents.similar_claim_agent import search_similar_claims


@dataclass
class ClaimReview:
    claim_id: str
    policy_summary: str
    similar_claims_summary: str
    fraud_verdict: str
    fraud_confidence: float
    fraud_rule_hits: list[str]
    fraud_explanation: str | None
    prediction: PredictionDecision | None


class AdjusterAgent:
    def __init__(self, mcp: MCPClient, llm: LLMClient, audit: AuditSink) -> None:
        self._mcp = mcp
        self._llm = llm
        self._audit = audit

    async def review_claim(
        self,
        claim_id: str,
        policy_id: str,
        claim_type: str,
        narrative: str,
        claim_data: dict,
        policy_data: dict,
        existing_claim_ids_for_policy: list[str] | None = None,
    ) -> ClaimReview:
        trace_id = get_trace_id()

        policy_result = await search_policy(self._mcp, policy_id, claim_type)
        similar_result = await search_similar_claims(self._mcp, narrative, claim_type)
        combined_summary = (
            f"Policy coverage: {policy_result['summary']}\n\n"
            f"Similar past claims ({similar_result['similar_count']} found): {similar_result['summary']}"
        )

        fraud_result = await self._mcp.call_tool(
            "fraud_agent",
            "assess_claim",
            {
                "claim_id": claim_id,
                "claim_data": claim_data,
                "policy_data": policy_data,
                "existing_claim_ids_for_policy": existing_claim_ids_for_policy or [],
            },
        )

        await self._audit.write(
            AuditEvent(
                trace_id=trace_id,
                actor_type="agent",
                actor_id="adjuster_agent",
                action="adjuster.review.subagents_completed",
                entity_type="claim",
                entity_id=claim_id,
                metadata={"policy_citations": policy_result["citations"]},
            )
        )

        if fraud_result["verdict"] == "fraud":
            explanation_result = await self._mcp.call_tool(
                "fraud_agent", "explain_fraud", {"claim_id": claim_id}
            )
            await self._audit.write(
                AuditEvent(
                    trace_id=trace_id,
                    actor_type="agent",
                    actor_id="adjuster_agent",
                    action="adjuster.review.fraud_rejected",
                    entity_type="claim",
                    entity_id=claim_id,
                    metadata={"rule_hits": fraud_result["rule_hits"]},
                )
            )
            return ClaimReview(
                claim_id=claim_id,
                policy_summary=policy_result["summary"],
                similar_claims_summary=similar_result["summary"],
                fraud_verdict="fraud",
                fraud_confidence=fraud_result["confidence"],
                fraud_rule_hits=fraud_result["rule_hits"],
                fraud_explanation=explanation_result["explanation"],
                prediction=None,
            )

        prediction = await predict(combined_summary, self._llm)
        await self._audit.write(
            AuditEvent(
                trace_id=trace_id,
                actor_type="agent",
                actor_id="prediction_model",
                action="prediction.completed",
                entity_type="claim",
                entity_id=claim_id,
                # Explainability for denials: the rationale is captured here,
                # independent of the adjuster's own notes.
                metadata={
                    "recommendation": prediction.recommendation,
                    "confidence": prediction.confidence,
                    "rationale": prediction.rationale,
                },
            )
        )
        return ClaimReview(
            claim_id=claim_id,
            policy_summary=policy_result["summary"],
            similar_claims_summary=similar_result["summary"],
            fraud_verdict="not_fraud",
            fraud_confidence=fraud_result["confidence"],
            fraud_rule_hits=[],
            fraud_explanation=None,
            prediction=prediction,
        )
