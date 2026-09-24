"""Central settings and provider selection.

This is the one place Phase 2 swaps happen: change an env var here, not
call sites. See docs/architecturePlan.md for the pluggability design.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Database ---
    # postgresql+asyncpg://user:pass@host:port/db for Phase 1 production,
    # sqlite+aiosqlite:///path/to.db for local dev/test.
    database_url: str = "sqlite+aiosqlite:///./claimsettler.db"

    # --- MCP server addresses (Streamable HTTP) ---
    mcp_kma_url: str = "http://localhost:8100/mcp"
    mcp_fraud_agent_url: str = "http://localhost:8101/mcp"
    mcp_compliance_agent_url: str = "http://localhost:8102/mcp"

    # --- Provider selection: real backends need credentials; "fake" is the
    # in-memory/no-credential default so the system runs end-to-end locally. ---
    embedding_provider: str = "fake"  # "bge_m3" | "fake"
    vector_store: str = "fake"  # "pinecone" | "fake"
    reranker: str = "fake"  # "bge_reranker" | "fake"
    llm_provider: str = "fake"  # "anthropic" | "fake"
    pii_detector: str = "presidio"  # "presidio" | "regex_only"

    # --- Pinecone ---
    pinecone_api_key: str | None = None
    pinecone_index: str = "claimsettler-kma"

    # --- Anthropic ---
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-5"

    # --- Auth ---
    auth_token_prefix: str = "cs_"  # opaque bearer token prefix, Phase 1 static RBAC

    # --- CORS (frontend) ---
    # Comma-separated list of allowed origins for the Next.js frontend.
    cors_allow_origins: str = "http://localhost:3000"

    # --- Chunking ---
    chunk_size_tokens: int = 600
    chunk_overlap_tokens: int = 100


@lru_cache
def get_settings() -> Settings:
    return Settings()
