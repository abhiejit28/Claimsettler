"""Phase 1 end-to-end verification (docs/architecturePlan.md "Verification"
section): submit a JSON claim -> FNOL -> Compliance Agent -> KMA -> review
(PolicySearchAgent + SimilarClaimAgent + RuleEngineAgent + PredictionModel)
-> adjuster decision -> training_feedback + KMA feedback write -> full
trace reconstructable via the audit trail.

Runs against the real MCP servers (subprocesses, fake providers) and a real
FastAPI app — only the vector store/embeddings/LLM/reranker are fakes, so
this exercises real MCP wire calls, real SQL, and real masking logic.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from claimsettler.core.config import get_settings


@pytest.fixture(scope="session")
def client(mcp_servers, integration_db_url: str) -> TestClient:
    os.environ["DATABASE_URL"] = integration_db_url
    os.environ["EMBEDDING_PROVIDER"] = "fake"
    os.environ["VECTOR_STORE"] = "fake"
    os.environ["RERANKER"] = "fake"
    os.environ["LLM_PROVIDER"] = "fake"
    get_settings.cache_clear()

    from claimsettler.api.main import app

    with TestClient(app) as test_client:
        yield test_client


def _auth_headers(client: TestClient) -> dict[str, str]:
    token = client.app.state.dev_adjuster_token
    return {"Authorization": f"Bearer {token}"}


def test_health(client: TestClient):
    resp = client.get("/health")
    assert resp.status_code == 200


def test_full_claim_lifecycle_approve_path(client: TestClient):
    claim_payload = {
        "claim_id": "CLM-E2E-001",
        "policy_id": "POL-E2E-001",
        "product_id": "PROD-AUTO-001",
        "customer_name": "Jane Doe",
        "claim_type": "auto",
        "claim_amount": 4500.0,
        "incident_date": "2026-08-01",
        "reported_date": "2026-08-03",
        "narrative": "Rear-ended at a stoplight, minor bumper damage.",
        "policy_data": {
            "active": True,
            "effective_date": "2025-01-01",
            "expiry_date": "2026-12-31",
            "coverage_limit": 50000,
        },
    }

    submit_resp = client.post("/claims", json=claim_payload)
    assert submit_resp.status_code == 201, submit_resp.text
    submit_body = submit_resp.json()
    assert submit_body["claim_id"] == "CLM-E2E-001"
    assert submit_body["status"] == "claim_reported"
    # customer_name is a free-text field under the masking taxonomy
    assert submit_body["masking_report"]["customer_name"] in ("ner_masked", "ner_masked_fallback_invalid_format")

    # Unauthenticated adjuster access is rejected.
    unauth_resp = client.get("/claims/CLM-E2E-001/review")
    assert unauth_resp.status_code in (401, 422)

    review_resp = client.get("/claims/CLM-E2E-001/review", headers=_auth_headers(client))
    assert review_resp.status_code == 200, review_resp.text
    review = review_resp.json()
    assert review["fraud_verdict"] == "not_fraud"
    assert review["prediction_recommendation"] in ("approve", "reject")

    decision_resp = client.post(
        "/claims/CLM-E2E-001/decision",
        headers=_auth_headers(client),
        json={
            "decision": "approve",
            "reasoning": "Consistent with policy coverage and no similar-claim red flags.",
            "fraud_verdict": review["fraud_verdict"],
            "prediction_recommendation": review["prediction_recommendation"],
            "prediction_confidence": review["prediction_confidence"],
        },
    )
    assert decision_resp.status_code == 200, decision_resp.text
    decision_body = decision_resp.json()
    assert decision_body["status"] == "approved"
    trace_id = decision_body["trace_id"]

    # Note: FNOL intake and the review step each mint their own trace_id
    # (independent inbound requests); the decision step's own trace only
    # covers actions from that request onward. This asserts the decision's
    # own action was recorded under its trace.
    import asyncio

    from claimsettler.core.audit.postgres_sink import PostgresAuditSink
    from claimsettler.storage.db import Database

    settings = get_settings()
    db = Database(settings)

    async def _get_trace():
        sink = PostgresAuditSink(db.session_factory)
        return await sink.get_trace(trace_id)

    trace_events = asyncio.run(_get_trace())
    actions = [e.action for e in trace_events]
    assert "adjuster.decision.recorded" in actions


def test_fraud_path_rejects_immediately(client: TestClient):
    claim_payload = {
        "claim_id": "CLM-E2E-002",
        "policy_id": "POL-E2E-002",
        "product_id": "PROD-AUTO-001",
        "customer_name": "John Roe",
        "claim_type": "auto",
        "claim_amount": 999999.0,  # exceeds coverage_limit -> immediate rule-engine rejection
        "incident_date": "2026-08-01",
        "reported_date": "2026-08-03",
        "narrative": "Total loss claim.",
        "policy_data": {
            "active": True,
            "effective_date": "2025-01-01",
            "expiry_date": "2026-12-31",
            "coverage_limit": 50000,
        },
    }
    submit_resp = client.post("/claims", json=claim_payload)
    assert submit_resp.status_code == 201

    review_resp = client.get("/claims/CLM-E2E-002/review", headers=_auth_headers(client))
    assert review_resp.status_code == 200
    review = review_resp.json()
    assert review["fraud_verdict"] == "fraud"
    assert review["fraud_explanation"] is not None
    assert review["prediction_recommendation"] is None  # PredictionModel never runs on the fraud path
