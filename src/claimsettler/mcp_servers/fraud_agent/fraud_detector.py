"""Combines rule-engine (Phase 1) and ML-module (Phase 3) signals into a
final confidence score and fraud/no-fraud call."""

from __future__ import annotations

from dataclasses import dataclass

from .rule_engine_agent import RuleReport


@dataclass(frozen=True)
class FraudDetection:
    verdict: str  # "fraud" | "not_fraud"
    confidence: float
    rule_hits: list[str]
    ml_scores: dict[str, float] | None = None


def detect(rule_report: RuleReport, ml_scores: dict[str, float] | None = None) -> FraudDetection:
    if rule_report.rejected:
        # Spec: a rule-engine rejection is immediate and final — no further
        # (Phase 3) ML checks needed.
        return FraudDetection(verdict="fraud", confidence=1.0, rule_hits=rule_report.hits, ml_scores=None)

    if ml_scores:
        combined = sum(ml_scores.values()) / len(ml_scores)
        verdict = "fraud" if combined >= 0.5 else "not_fraud"
        return FraudDetection(verdict=verdict, confidence=combined, rule_hits=[], ml_scores=ml_scores)

    # Phase 1: rule engine passed, no ML modules yet -> not fraud.
    return FraudDetection(verdict="not_fraud", confidence=0.0, rule_hits=[], ml_scores=None)
