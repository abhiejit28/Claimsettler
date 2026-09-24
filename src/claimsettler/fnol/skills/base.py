"""Modality-specific normalization skills. Phase 1 ships only JSON intake
(json_skill below); OCR/doc-parsing (Phase 2) and voice/video-to-text
(Phase 3) implement the same Skill Protocol without touching FNOL Agent or
downstream components — nothing past normalization cares how the claim
arrived."""

from __future__ import annotations

from typing import Any, Protocol

from claimsettler.core.errors import ValidationError
from claimsettler.shared.types import ClaimDocument

_REQUIRED_FIELDS = (
    "claim_id",
    "policy_id",
    "product_id",
    "customer_name",
    "claim_type",
    "claim_amount",
    "incident_date",
    "narrative",
)


class Skill(Protocol):
    def normalize(self, raw_input: Any) -> ClaimDocument: ...


class JSONSkill:
    """Phase 1's only skill: the input already arrives as structured JSON,
    so normalization is validation, not extraction."""

    def normalize(self, raw_input: dict[str, Any]) -> ClaimDocument:
        missing = [f for f in _REQUIRED_FIELDS if f not in raw_input]
        if missing:
            raise ValidationError(f"claim JSON missing required fields: {missing}")
        known = set(_REQUIRED_FIELDS)
        extra_fields = {k: v for k, v in raw_input.items() if k not in known}
        return ClaimDocument(
            claim_id=raw_input["claim_id"],
            policy_id=raw_input["policy_id"],
            product_id=raw_input["product_id"],
            customer_name=raw_input["customer_name"],
            claim_type=raw_input["claim_type"],
            claim_amount=raw_input["claim_amount"],
            incident_date=raw_input["incident_date"],
            narrative=raw_input["narrative"],
            fields=extra_fields,
        )
