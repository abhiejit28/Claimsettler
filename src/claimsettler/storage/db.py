from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from claimsettler.core.config import Settings


class Database:
    """Owns the SQLAlchemy async engine/session factory. One instance per process
    (API process, each MCP server process). Works against Postgres (production)
    or SQLite (local dev/test) via the same DATABASE_URL-driven engine."""

    def __init__(self, settings: Settings) -> None:
        self.engine: AsyncEngine = create_async_engine(settings.database_url, future=True)
        self.session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            self.engine, expire_on_commit=False
        )

    async def create_all(self) -> None:
        """Dev/test convenience — Phase 1 production uses alembic migrations instead."""
        from claimsettler.storage.models import Base

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def dispose(self) -> None:
        await self.engine.dispose()
