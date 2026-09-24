from __future__ import annotations

import hashlib

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from claimsettler.storage.models import UserRow

from .interfaces import Principal


def hash_token(raw_token: str) -> str:
    """Bearer tokens are opaque API keys; only the SHA-256 hash is stored/compared."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


class StaticRBACAuthenticator:
    """Phase 1: looks up a bearer token against the users table -> Principal with roles.

    Phase 2 swap: implement OAuth2ADAuthenticator against the same Authenticator
    Protocol and rebind get_authenticator() in core/config.py — no controller changes.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def authenticate(self, credentials: str) -> Principal | None:
        token_hash = hash_token(credentials)
        async with self._session_factory() as session:
            row = (
                await session.scalars(select(UserRow).where(UserRow.api_key_hash == token_hash))
            ).one_or_none()
        if row is None:
            return None
        return Principal(
            user_id=row.user_id,
            display_name=row.display_name,
            roles=frozenset(row.roles.split(",")) if row.roles else frozenset(),
            auth_method="rbac_static",
        )


class SimpleRoleAuthorizer:
    def is_authorized(self, principal: Principal, required_role: str) -> bool:
        return required_role in principal.roles
