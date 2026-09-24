import pytest

from claimsettler.mcp_servers.fraud_agent.fraud_detector import detect
from claimsettler.mcp_servers.fraud_agent.rule_engine_agent import run_rule_engine

CLEAN_POLICY = {
    "active": True,
    "effective_date": "2025-01-01",
    "expiry_date": "2026-12-31",
    "coverage_limit": 100_000,
}


def test_clean_claim_passes():
    claim = {
        "claim_id": "CLM-1",
        "claim_amount": 5_000,
        "incident_date": "2026-01-10",
        "reported_date": "2026-01-12",
    }
    report = run_rule_engine(claim, CLEAN_POLICY, [])
    assert not report.rejected
    detection = detect(report)
    assert detection.verdict == "not_fraud"


def test_exceeds_coverage_limit_is_rejected_immediately():
    claim = {
        "claim_id": "CLM-2",
        "claim_amount": 500_000,
        "incident_date": "2026-01-10",
        "reported_date": "2026-01-12",
    }
    report = run_rule_engine(claim, CLEAN_POLICY, [])
    detection = detect(report)
    assert detection.verdict == "fraud"
    assert detection.confidence == 1.0
    assert any("exceeds_coverage_limit" in hit for hit in detection.rule_hits)


def test_inactive_policy_is_rejected():
    claim = {"claim_id": "CLM-3", "claim_amount": 1000, "incident_date": "2026-01-10"}
    policy = {**CLEAN_POLICY, "active": False}
    report = run_rule_engine(claim, policy, [])
    assert report.rejected
    assert any("policy_inactive" in hit for hit in report.hits)


def test_late_reporting_flagged():
    claim = {
        "claim_id": "CLM-4",
        "claim_amount": 1000,
        "incident_date": "2026-01-01",
        "reported_date": "2026-06-01",
    }
    report = run_rule_engine(claim, CLEAN_POLICY, [])
    assert any("late_reporting" in hit for hit in report.hits)


def test_no_ml_scores_means_not_fraud_when_rules_pass():
    claim = {"claim_id": "CLM-5", "claim_amount": 100, "incident_date": "2026-01-01", "reported_date": "2026-01-02"}
    report = run_rule_engine(claim, CLEAN_POLICY, [])
    detection = detect(report, ml_scores=None)
    assert detection.verdict == "not_fraud"


def test_ml_scores_combine_when_provided():
    claim = {"claim_id": "CLM-6", "claim_amount": 100, "incident_date": "2026-01-01", "reported_date": "2026-01-02"}
    report = run_rule_engine(claim, CLEAN_POLICY, [])
    detection = detect(report, ml_scores={"supervised": 0.9, "anomaly": 0.8})
    assert detection.verdict == "fraud"
    assert detection.confidence == pytest.approx(0.85)
