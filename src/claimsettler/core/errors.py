class ClaimSettlerError(Exception):
    """Base class for all ClaimSettler application errors."""


class NotFoundError(ClaimSettlerError):
    """Requested entity does not exist."""


class ValidationError(ClaimSettlerError):
    """Input failed domain validation (distinct from Pydantic request validation)."""


class MCPCallError(ClaimSettlerError):
    """An MCP tool call failed or returned an unexpected shape."""

    def __init__(self, server: str, tool: str, detail: str) -> None:
        self.server = server
        self.tool = tool
        self.detail = detail
        super().__init__(f"MCP call {server}.{tool} failed: {detail}")
