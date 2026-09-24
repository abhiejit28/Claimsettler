"""Phase 2 stub.

OAuth2ADAuthenticator will implement the same `Authenticator` Protocol
(core/auth/interfaces.py), validating a JWT against the AD/SSO issuer and
mapping AD groups to internal roles. Once implemented, the only change
needed elsewhere is rebinding `get_authenticator()` in core/config.py /
core/auth/dependencies.py — no controller code changes.
"""
