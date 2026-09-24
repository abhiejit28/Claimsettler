from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class AuditEvent:
    trace_id: str
    actor_type: str  # "user" | "system" | "agent"
    actor_id: str
    action: str  # e.g. "claim.fnol.received", "fraud.assessment.completed"
    entity_type: str  # "claim" | "policy" | "fraud_assessment" | "prediction" ...
    entity_id: str
    event_id: uuid.UUID = field(default_factory=uuid.uuid4)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    before_state: dict[str, Any] | None = None
    after_state: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
