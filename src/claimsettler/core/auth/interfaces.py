from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Principal:
    user_id: str
    display_name: str
    roles: frozenset[str]
    auth_method: str  # "rbac_static" | "oauth2_ad"


class Authenticator(Protocol):
    """Resolves raw request credentials (e.g. a bearer token) into a Principal."""

    async def authenticate(self, credentials: str) -> Principal | None: ...


class Authorizer(Protocol):
    """Given a Principal and a required role, allow or deny."""

    def is_authorized(self, principal: Principal, required_role: str) -> bool: ...
