"""Deterministic rule-based fraud checks against claim + policy data.
Phase 1's only fraud signal (ML modules land in Phase 3 — see
docs/architecturePlan.md phased plan and its rationale)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

LATE_REPORTING_DAYS = 30


@dataclass(frozen=True)
class RuleReport:
    hits: list[str] = field(default_factory=list)

    @property
    def rejected(self) -> bool:
        return bool(self.hits)


def _parse_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def check_policy_active(claim_data: dict, policy_data: dict) -> str | None:
    if not policy_data.get("active", True):
        return "policy_inactive: claim filed against an inactive policy"
    incident = _parse_date(claim_data.get("incident_date", ""))
    effective = _parse_date(policy_data.get("effective_date", ""))
    expiry = _parse_date(policy_data.get("expiry_date", ""))
    if incident and effective and incident < effective:
        return "incident_before_coverage: incident predates policy effective date"
    if incident and expiry and incident > expiry:
        return "incident_after_expiry: incident postdates policy expiry"
    return None


def check_coverage_limit(claim_data: dict, policy_data: dict) -> str | None:
    claim_amount = claim_data.get("claim_amount")
    coverage_limit = policy_data.get("coverage_limit")
    if claim_amount is not None and coverage_limit is not None and claim_amount > coverage_limit:
        return f"exceeds_coverage_limit: claim_amount {claim_amount} > coverage_limit {coverage_limit}"
    return None


def check_late_reporting(claim_data: dict, policy_data: dict) -> str | None:
    incident = _parse_date(claim_data.get("incident_date", ""))
    reported = _parse_date(claim_data.get("reported_date", ""))
    if incident and reported and (reported - incident) > timedelta(days=LATE_REPORTING_DAYS):
        return f"late_reporting: reported {(reported - incident).days} days after incident"
    return None


def check_duplicate_claim(claim_data: dict, existing_claim_ids_for_policy: list[str]) -> str | None:
    claim_id = claim_data.get("claim_id")
    others = [c for c in existing_claim_ids_for_policy if c != claim_id]
    if others:
        return f"duplicate_claim: policy already has {len(others)} other claim(s) on record"
    return None


_CHECKS = (check_policy_active, check_coverage_limit, check_late_reporting)


def run_rule_engine(
    claim_data: dict, policy_data: dict, existing_claim_ids_for_policy: list[str] | None = None
) -> RuleReport:
    hits: list[str] = []
    for check in _CHECKS:
        result = check(claim_data, policy_data)
        if result:
            hits.append(result)
    if existing_claim_ids_for_policy is not None:
        dup = check_duplicate_claim(claim_data, existing_claim_ids_for_policy)
        if dup:
            hits.append(dup)
    return RuleReport(hits=hits)
