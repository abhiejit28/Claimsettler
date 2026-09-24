from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Protocol

from .models import AuditEvent


class AuditSink(Protocol):
    """Storage-agnostic audit trail. Postgres is the only Phase 1 implementation;
    callers never depend on it directly — see postgres_sink.py and core/config.py."""

    async def write(self, event: AuditEvent) -> None: ...

    async def write_batch(self, events: Iterable[AuditEvent]) -> None: ...

    async def query(
        self,
        *,
        entity_type: str | None = None,
        entity_id: str | None = None,
        trace_id: str | None = None,
        actor_id: str | None = None,
        action: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditEvent]: ...

    async def get_trace(self, trace_id: str) -> list[AuditEvent]:
        """Full chronological event chain for one claim's journey — the
        regulatory 'show your work' reconstruction path."""
        ...
