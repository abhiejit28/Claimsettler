from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, Header, HTTPException, Request

from .interfaces import Authenticator, Authorizer, Principal


async def get_current_principal(
    request: Request,
    authorization: str = Header(...),
) -> Principal:
    """Resolves the bearer token via the Authenticator bound on app state.
    Swapping RBAC -> OAuth2/AD means rebinding app.state.authenticator, not
    touching this function or any controller."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="expected 'Bearer <token>' authorization header")
    token = authorization.removeprefix("Bearer ").strip()

    authenticator: Authenticator = request.app.state.authenticator
    principal = await authenticator.authenticate(token)
    if principal is None:
        raise HTTPException(status_code=401, detail="unauthenticated")
    return principal


def require_role(role: str) -> Callable:
    """Composable, per-route authorization — the filter-chain equivalent.
    Usage: `principal: Principal = Depends(require_role("adjuster"))`."""

    def _dependency(
        request: Request,
        principal: Principal = Depends(get_current_principal),
    ) -> Principal:
        authorizer: Authorizer = request.app.state.authorizer
        if not authorizer.is_authorized(principal, role):
            raise HTTPException(status_code=403, detail=f"requires role: {role}")
        return principal

    return _dependency
