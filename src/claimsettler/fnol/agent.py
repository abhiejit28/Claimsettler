"""FNOL Agent. Phase 1: JSON-only intake, in-process/direct call from
FNOLController. Normalizes via a modality skill, sends the result through
Compliance Agent (MCP, masking) BEFORE it reaches KMA (MCP, storage) —
NER-based PII detection needs text, not raw bytes, so masking happens after
normalization."""

from __future__ import annotations

from dataclasses import dataclass

from claimsettler.core.audit.interfaces import AuditSink
from claimsettler.core.audit.models import AuditEvent
from claimsettler.core.mcp_client import MCPClient
from claimsettler.shared.correlation import get_trace_id
from claimsettler.shared.types import ClaimDocument

from .skills.base import JSONSkill


@dataclass
class FNOLResult:
    claim_document: ClaimDocument
    masking_report: dict[str, str]
    kma_document_id: str | None


class FNOLAgent:
    def __init__(self, mcp: MCPClient, audit: AuditSink) -> None:
        self._mcp = mcp
        self._audit = audit
        self._skill = JSONSkill()

    async def process_claim(self, raw_input: dict) -> FNOLResult:
        trace_id = get_trace_id()
        claim_document = self._skill.normalize(raw_input)

        mask_result = await self._mcp.call_tool(
            "compliance_agent", "scan_and_mask", {"document": claim_document.model_dump()}
        )
        masked_document = mask_result["masked_document"]

        store_result = await self._mcp.call_tool(
            "kma",
            "store_document",
            {
                "document": masked_document,
                "document_type": "claim",
                "claim_id": claim_document.claim_id,
                "policy_id": claim_document.policy_id,
                "product_id": claim_document.product_id,
            },
        )

        await self._audit.write(
            AuditEvent(
                trace_id=trace_id,
                actor_type="agent",
                actor_id="fnol_agent",
                action="claim.fnol.received",
                entity_type="claim",
                entity_id=claim_document.claim_id,
                after_state={"status": "claim_reported"},
                metadata={"masking_report": mask_result["report"]},
            )
        )

        return FNOLResult(
            claim_document=claim_document,
            masking_report=mask_result["report"],
            kma_document_id=store_result.get("document_id"),
        )
