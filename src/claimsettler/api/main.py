from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from claimsettler.adjuster.agent import AdjusterAgent
from claimsettler.core.audit.postgres_sink import PostgresAuditSink
from claimsettler.core.auth.rbac import SimpleRoleAuthorizer, StaticRBACAuthenticator, hash_token
from claimsettler.core.config import get_settings
from claimsettler.core.llm import build_llm_client
from claimsettler.core.mcp_client import MCPClient
from claimsettler.fnol.agent import FNOLAgent
from claimsettler.storage.db import Database
from claimsettler.storage.models import UserRow

from . import adjuster_controller, fnol_controller


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    db = Database(settings)
    await db.create_all()  # Phase 1 dev convenience; production uses alembic migrations.

    audit = PostgresAuditSink(db.session_factory)
    authenticator = StaticRBACAuthenticator(db.session_factory)
    authorizer = SimpleRoleAuthorizer()
    mcp = MCPClient(settings)
    llm = build_llm_client(settings)

    app.state.settings = settings
    app.state.db = db
    app.state.audit = audit
    app.state.authenticator = authenticator
    app.state.authorizer = authorizer
    app.state.mcp = mcp
    app.state.fnol_agent = FNOLAgent(mcp, audit)
    app.state.adjuster_agent = AdjusterAgent(mcp, llm, audit)

    app.state.dev_adjuster_token = await _seed_dev_adjuster(db)

    yield

    await db.dispose()


async def _seed_dev_adjuster(db: Database) -> str | None:
    """Phase 1 convenience: ensures a default adjuster user exists so the
    API is usable out of the box. Token is printed once at startup and
    exposed on app.state (for tests); real user provisioning is out of
    scope for Phase 1 (see docs/architecturePlan.md)."""
    async with db.session_factory() as session:
        existing = await session.get(UserRow, "dev-adjuster")
        if existing is not None:
            return None
        raw_token = f"cs_dev_{uuid.uuid4().hex}"
        session.add(
            UserRow(
                user_id="dev-adjuster",
                display_name="Dev Adjuster",
                roles="adjuster",
                api_key_hash=hash_token(raw_token),
            )
        )
        await session.commit()
        print(f"[claimsettler] seeded dev adjuster user — bearer token: {raw_token}")
        return raw_token


def create_app() -> FastAPI:
    app = FastAPI(title="ClaimSettler", lifespan=lifespan)

    cors_settings = get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in cors_settings.cors_allow_origins.split(",") if o.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(fnol_controller.router)
    app.include_router(adjuster_controller.router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
