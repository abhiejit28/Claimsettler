from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class FNOLClaimRequest(BaseModel):
    claim_id: str
    policy_id: str
    product_id: str
    customer_name: str
    claim_type: str
    claim_amount: float
    incident_date: str
    reported_date: str
    narrative: str
    # Phase 1 has no separate policy-management system yet; synthetic policy
    # data is supplied alongside the claim so RuleEngineAgent has something
    # to check against. Real policy lookups replace this in Phase 2.
    policy_data: dict[str, Any] = Field(default_factory=dict)


class FNOLClaimResponse(BaseModel):
    claim_id: str
    status: str
    masking_report: dict[str, str]
    kma_document_id: str | None


class ClaimReviewResponse(BaseModel):
    claim_id: str
    policy_summary: str
    similar_claims_summary: str
    fraud_verdict: str
    fraud_confidence: float
    fraud_rule_hits: list[str]
    fraud_explanation: str | None
    prediction_recommendation: str | None
    prediction_confidence: float | None
    prediction_rationale: str | None


class DecisionRequest(BaseModel):
    decision: str  # "approve" | "reject"
    reasoning: str
    fraud_verdict: str
    prediction_recommendation: str | None = None
    prediction_confidence: float | None = None


class DecisionResponse(BaseModel):
    claim_id: str
    status: str
    trace_id: str
