from __future__ import annotations

from fastapi import APIRouter, Request

from claimsettler.core.audit.models import AuditEvent
from claimsettler.fnol.agent import FNOLAgent
from claimsettler.shared.correlation import get_trace_id, new_trace_id, set_trace_id
from claimsettler.shared.types import ClaimStatus
from claimsettler.storage.models import ClaimRow

from .schemas import FNOLClaimRequest, FNOLClaimResponse

router = APIRouter(prefix="/claims", tags=["fnol"])


@router.post("", response_model=FNOLClaimResponse, status_code=201)
async def submit_claim(body: FNOLClaimRequest, request: Request) -> FNOLClaimResponse:
    set_trace_id(new_trace_id())
    trace_id = get_trace_id()

    fnol_agent: FNOLAgent = request.app.state.fnol_agent
    result = await fnol_agent.process_claim(body.model_dump(exclude={"policy_data"}))

    session_factory = request.app.state.db.session_factory
    async with session_factory() as session:
        session.add(
            ClaimRow(
                claim_id=body.claim_id,
                policy_id=body.policy_id,
                customer_name=body.customer_name,
                status=ClaimStatus.CLAIM_REPORTED.value,
                raw_claim_data={**body.model_dump(exclude={"policy_data"})},
                policy_data=body.policy_data,
            )
        )
        await session.commit()

    await request.app.state.audit.write(
        AuditEvent(
            trace_id=trace_id,
            actor_type="system",
            actor_id="fnol_controller",
            action="claim.fnol.controller_persisted",
            entity_type="claim",
            entity_id=body.claim_id,
            after_state={"status": ClaimStatus.CLAIM_REPORTED.value},
        )
    )

    return FNOLClaimResponse(
        claim_id=result.claim_document.claim_id,
        status=ClaimStatus.CLAIM_REPORTED.value,
        masking_report=result.masking_report,
        kma_document_id=result.kma_document_id,
    )
