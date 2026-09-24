from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select

from claimsettler.adjuster.agent import AdjusterAgent
from claimsettler.core.audit.models import AuditEvent
from claimsettler.core.auth.dependencies import require_role
from claimsettler.core.auth.interfaces import Principal
from claimsettler.core.errors import NotFoundError
from claimsettler.shared.correlation import get_trace_id, new_trace_id, set_trace_id
from claimsettler.shared.types import ClaimStatus
from claimsettler.storage.models import ClaimRow, TrainingFeedbackRow

from .schemas import ClaimReviewResponse, DecisionRequest, DecisionResponse

router = APIRouter(prefix="/claims", tags=["adjuster"])


async def _load_claim(request: Request, claim_id: str) -> ClaimRow:
    session_factory = request.app.state.db.session_factory
    async with session_factory() as session:
        row = await session.get(ClaimRow, claim_id)
    if row is None:
        raise NotFoundError(f"claim {claim_id} not found")
    return row


@router.get("/{claim_id}/review", response_model=ClaimReviewResponse)
async def review_claim(
    claim_id: str,
    request: Request,
    principal: Principal = Depends(require_role("adjuster")),
) -> ClaimReviewResponse:
    set_trace_id(new_trace_id())
    trace_id = get_trace_id()

    try:
        claim_row = await _load_claim(request, claim_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    session_factory = request.app.state.db.session_factory
    async with session_factory() as session:
        other_claim_ids = (
            await session.scalars(
                select(ClaimRow.claim_id).where(ClaimRow.policy_id == claim_row.policy_id)
            )
        ).all()

    adjuster_agent: AdjusterAgent = request.app.state.adjuster_agent
    review = await adjuster_agent.review_claim(
        claim_id=claim_id,
        policy_id=claim_row.policy_id,
        claim_type=claim_row.raw_claim_data.get("claim_type", "auto"),
        narrative=claim_row.raw_claim_data.get("narrative", ""),
        claim_data=claim_row.raw_claim_data,
        policy_data=claim_row.policy_data,
        existing_claim_ids_for_policy=list(other_claim_ids),
    )

    async with session_factory() as session:
        db_row = await session.get(ClaimRow, claim_id)
        db_row.status = ClaimStatus.UNDER_REVIEW.value
        await session.commit()

    await request.app.state.audit.write(
        AuditEvent(
            trace_id=trace_id,
            actor_type="user",
            actor_id=principal.user_id,
            action="adjuster.review.opened",
            entity_type="claim",
            entity_id=claim_id,
        )
    )

    return ClaimReviewResponse(
        claim_id=review.claim_id,
        policy_summary=review.policy_summary,
        similar_claims_summary=review.similar_claims_summary,
        fraud_verdict=review.fraud_verdict,
        fraud_confidence=review.fraud_confidence,
        fraud_rule_hits=review.fraud_rule_hits,
        fraud_explanation=review.fraud_explanation,
        prediction_recommendation=review.prediction.recommendation if review.prediction else None,
        prediction_confidence=review.prediction.confidence if review.prediction else None,
        prediction_rationale=review.prediction.rationale if review.prediction else None,
    )


@router.post("/{claim_id}/decision", response_model=DecisionResponse)
async def submit_decision(
    claim_id: str,
    body: DecisionRequest,
    request: Request,
    principal: Principal = Depends(require_role("adjuster")),
) -> DecisionResponse:
    set_trace_id(new_trace_id())
    trace_id = get_trace_id()

    try:
        claim_row = await _load_claim(request, claim_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if body.decision not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="decision must be 'approve' or 'reject'")

    new_status = ClaimStatus.APPROVED.value if body.decision == "approve" else ClaimStatus.REJECTED.value

    session_factory = request.app.state.db.session_factory
    async with session_factory() as session:
        db_row = await session.get(ClaimRow, claim_id)
        db_row.status = new_status
        session.add(
            TrainingFeedbackRow(
                claim_id=claim_id,
                trace_id=trace_id,
                fraud_verdict=body.fraud_verdict,
                prediction_recommendation=body.prediction_recommendation or "",
                prediction_confidence=body.prediction_confidence or 0.0,
                adjuster_decision=body.decision,
                adjuster_reasoning=body.reasoning,
                adjuster_id=principal.user_id,
                synthetic=True,  # Phase 1 data is synthetic; see docs/architecturePlan.md
            )
        )
        await session.commit()

    # Human feedback is dual-written to KMA (for future retrieval/retraining
    # context) and Postgres (training_feedback, above) per the spec.
    mcp = request.app.state.mcp
    await mcp.call_tool(
        "kma",
        "store_document",
        {
            "document": {
                "claim_id": claim_id,
                "decision": body.decision,
                "reasoning": body.reasoning,
            },
            "document_type": "adjuster_feedback",
            "claim_id": claim_id,
            "policy_id": claim_row.policy_id,
        },
    )

    await request.app.state.audit.write(
        AuditEvent(
            trace_id=trace_id,
            actor_type="user",
            actor_id=principal.user_id,
            action="adjuster.decision.recorded",
            entity_type="claim",
            entity_id=claim_id,
            before_state={"status": claim_row.status},
            after_state={"status": new_status},
            metadata={"reasoning": body.reasoning, "fraud_verdict": body.fraud_verdict},
        )
    )

    return DecisionResponse(claim_id=claim_id, status=new_status, trace_id=trace_id)
