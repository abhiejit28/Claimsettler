import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from claimsettler.core.audit.models import AuditEvent
from claimsettler.core.audit.postgres_sink import PostgresAuditSink
from claimsettler.storage.models import Base


@pytest.fixture
async def sink():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield PostgresAuditSink(factory)
    await engine.dispose()


@pytest.mark.asyncio
async def test_write_and_query_roundtrip(sink):
    event = AuditEvent(
        trace_id="trace-1",
        actor_type="system",
        actor_id="test",
        action="claim.fnol.received",
        entity_type="claim",
        entity_id="CLM-1",
        metadata={"foo": "bar"},
    )
    await sink.write(event)
    results = await sink.query(entity_id="CLM-1")
    assert len(results) == 1
    assert results[0].action == "claim.fnol.received"
    assert results[0].metadata == {"foo": "bar"}


@pytest.mark.asyncio
async def test_get_trace_reconstructs_full_journey(sink):
    for action in ("claim.fnol.received", "adjuster.review.opened", "adjuster.decision.recorded"):
        await sink.write(
            AuditEvent(
                trace_id="trace-2",
                actor_type="system",
                actor_id="test",
                action=action,
                entity_type="claim",
                entity_id="CLM-2",
            )
        )
    trace = await sink.get_trace("trace-2")
    assert [e.action for e in trace] == [
        "claim.fnol.received",
        "adjuster.review.opened",
        "adjuster.decision.recorded",
    ]
