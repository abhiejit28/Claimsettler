import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from claimsettler.core.auth.interfaces import Principal
from claimsettler.core.auth.rbac import SimpleRoleAuthorizer, StaticRBACAuthenticator, hash_token
from claimsettler.storage.models import Base, UserRow


@pytest.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with factory() as session:
        session.add(
            UserRow(
                user_id="u1",
                display_name="Adjuster One",
                roles="adjuster",
                api_key_hash=hash_token("secret-token"),
            )
        )
        await session.commit()
    yield factory
    await engine.dispose()


@pytest.mark.asyncio
async def test_valid_token_resolves_principal(session_factory):
    authenticator = StaticRBACAuthenticator(session_factory)
    principal = await authenticator.authenticate("secret-token")
    assert principal is not None
    assert principal.user_id == "u1"
    assert "adjuster" in principal.roles


@pytest.mark.asyncio
async def test_invalid_token_returns_none(session_factory):
    authenticator = StaticRBACAuthenticator(session_factory)
    principal = await authenticator.authenticate("wrong-token")
    assert principal is None


def test_authorizer_checks_role_membership():
    authorizer = SimpleRoleAuthorizer()
    principal = Principal(user_id="u1", display_name="x", roles=frozenset({"adjuster"}), auth_method="rbac_static")
    assert authorizer.is_authorized(principal, "adjuster")
    assert not authorizer.is_authorized(principal, "admin")
