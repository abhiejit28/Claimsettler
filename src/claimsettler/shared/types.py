"""DTOs shared across controllers, agents, and MCP servers."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ClaimStatus(StrEnum):
    CLAIM_REPORTED = "claim_reported"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class ClaimDocument(BaseModel):
    """FNOL Agent's normalized output — the shape every intake modality converges to."""

    claim_id: str
    policy_id: str
    product_id: str
    customer_name: str
    claim_type: str  # "auto" | "home" | "commercial"
    claim_amount: float
    incident_date: str
    narrative: str
    fields: dict[str, Any] = Field(default_factory=dict)  # extra structured fields (VIN, etc.)


class FraudVerdict(BaseModel):
    verdict: str  # "fraud" | "not_fraud"
    confidence: float
    rule_hits: list[str] = Field(default_factory=list)
    ml_scores: dict[str, float] | None = None


class FraudExplanation(BaseModel):
    verdict: str
    explanation: str
    rule_hits: list[str] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)


class PredictionDecision(BaseModel):
    recommendation: str  # "approve" | "reject"
    confidence: float
    rationale: str


class RetrievalMatch(BaseModel):
    text: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResult(BaseModel):
    answer: str
    citations: list[dict[str, Any]] = Field(default_factory=list)
    matches: list[RetrievalMatch] = Field(default_factory=list)
