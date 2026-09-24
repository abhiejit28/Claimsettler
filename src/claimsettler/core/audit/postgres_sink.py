from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from claimsettler.storage.models import AuditEventRow

from .models import AuditEvent


class PostgresAuditSink:
    """Append-only AuditSink implementation. Works against Postgres in
    production and SQLite in local dev/test — both go through the same
    SQLAlchemy async session factory (see storage/db.py)."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def write(self, event: AuditEvent) -> None:
        await self.write_batch([event])

    async def write_batch(self, events: Iterable[AuditEvent]) -> None:
        async with self._session_factory() as session:
            for event in events:
                session.add(AuditEventRow.from_domain(event))
            await session.commit()

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
    ) -> list[AuditEvent]:
        stmt = select(AuditEventRow).order_by(AuditEventRow.timestamp.asc())
        if entity_type is not None:
            stmt = stmt.where(AuditEventRow.entity_type == entity_type)
        if entity_id is not None:
            stmt = stmt.where(AuditEventRow.entity_id == entity_id)
        if trace_id is not None:
            stmt = stmt.where(AuditEventRow.trace_id == trace_id)
        if actor_id is not None:
            stmt = stmt.where(AuditEventRow.actor_id == actor_id)
        if action is not None:
            stmt = stmt.where(AuditEventRow.action == action)
        if since is not None:
            stmt = stmt.where(AuditEventRow.timestamp >= since)
        if until is not None:
            stmt = stmt.where(AuditEventRow.timestamp <= until)
        stmt = stmt.limit(limit).offset(offset)

        async with self._session_factory() as session:
            rows = (await session.scalars(stmt)).all()
        return [row.to_domain() for row in rows]

    async def get_trace(self, trace_id: str) -> list[AuditEvent]:
        return await self.query(trace_id=trace_id, limit=10_000)
