from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from claimsettler.core.audit.models import AuditEvent


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(UTC)


class ClaimRow(Base):
    """Operational claim state. Logically the 'claims' schema."""

    __tablename__ = "claims"

    claim_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    policy_id: Mapped[str] = mapped_column(String(64), index=True)
    customer_name: Mapped[str] = mapped_column(String(256))
    status: Mapped[str] = mapped_column(String(32), default="claim_reported")
    # Phase 1 has no separate policy-management system; the raw claim payload
    # and its (synthetic, Phase 1) policy data are kept here so AdjusterAgent
    # can re-load them for RuleEngineAgent/PredictionModel without a second
    # intake round-trip. Real policy lookups replace `policy_data` in Phase 2.
    raw_claim_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    policy_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class AuditEventRow(Base):
    """Append-only audit trail. Logically the 'audit' schema."""

    __tablename__ = "audit_events"

    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    trace_id: Mapped[str] = mapped_column(String(64), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    actor_type: Mapped[str] = mapped_column(String(16))
    actor_id: Mapped[str] = mapped_column(String(128))
    action: Mapped[str] = mapped_column(String(128), index=True)
    entity_type: Mapped[str] = mapped_column(String(64), index=True)
    entity_id: Mapped[str] = mapped_column(String(64), index=True)
    before_state: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    after_state: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    event_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    @classmethod
    def from_domain(cls, event: AuditEvent) -> AuditEventRow:
        return cls(
            event_id=str(event.event_id),
            trace_id=event.trace_id,
            timestamp=event.timestamp,
            actor_type=event.actor_type,
            actor_id=event.actor_id,
            action=event.action,
            entity_type=event.entity_type,
            entity_id=event.entity_id,
            before_state=event.before_state,
            after_state=event.after_state,
            event_metadata=event.metadata,
        )

    def to_domain(self) -> AuditEvent:
        return AuditEvent(
            event_id=uuid.UUID(self.event_id),
            trace_id=self.trace_id,
            timestamp=self.timestamp,
            actor_type=self.actor_type,
            actor_id=self.actor_id,
            action=self.action,
            entity_type=self.entity_type,
            entity_id=self.entity_id,
            before_state=self.before_state,
            after_state=self.after_state,
            metadata=self.event_metadata,
        )


class TrainingFeedbackRow(Base):
    """Adjuster decisions captured for future retraining/recalibration.
    Logically the 'training_feedback' schema."""

    __tablename__ = "training_feedback"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: uuid.uuid4().hex)
    claim_id: Mapped[str] = mapped_column(String(64), index=True)
    trace_id: Mapped[str] = mapped_column(String(64), index=True)
    fraud_verdict: Mapped[str] = mapped_column(String(16))
    prediction_recommendation: Mapped[str] = mapped_column(String(16))
    prediction_confidence: Mapped[float] = mapped_column(Float)
    adjuster_decision: Mapped[str] = mapped_column(String(16))
    adjuster_reasoning: Mapped[str] = mapped_column(Text)
    adjuster_id: Mapped[str] = mapped_column(String(128))
    synthetic: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class UserRow(Base):
    """Phase 1 RBAC source of truth — minimal users/roles table.
    Phase 2: superseded by OAuth2/AD, behind the same Authenticator interface."""

    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(256))
    roles: Mapped[str] = mapped_column(String(256))  # comma-separated, e.g. "adjuster,admin"
    api_key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
