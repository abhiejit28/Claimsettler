# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

ClaimSettler: an agentic AI platform for insurance claim processing (Auto/Home/Commercial). Phase 1 is implemented — see `docs/architecturePlan.md` for the full design rationale, the "Decisions confirmed" list, and the "Phase 1 — As Built" section documenting every deviation from the original plan. Read that file before making architectural changes; this file is a condensed map for day-to-day work.

## Setup

```bash
uv venv --python 3.13.7 .venv && source .venv/bin/activate
uv pip install -e ".[dev]"
python -m spacy download en_core_web_sm   # needed for PII_DETECTOR=presidio (the default)
cp .env.example .env                      # defaults to fake providers + SQLite, zero credentials needed
```

Python is pinned to 3.13 (not the system default 3.14 release candidate) for stable wheel compatibility with Presidio/spaCy.

## Commands

```bash
pytest tests -q                                    # full suite: unit + integration + MCP contract
pytest tests/unit -q                                # unit only, no subprocesses, fast
pytest tests/unit/test_rule_engine.py::test_clean_claim_passes -q   # single test
pytest tests/integration -q                         # spins up real MCP servers as subprocesses
ruff check src tests                                # lint
ruff check --fix src tests

# Run the full stack locally without Docker (4 separate processes):
python -m claimsettler.mcp_servers.kma.server               # port 8100
python -m claimsettler.mcp_servers.fraud_agent.server        # port 8101
python -m claimsettler.mcp_servers.compliance_agent.server   # port 8102
uvicorn claimsettler.api.main:app --reload                   # port 8000

# Full stack via Docker (real Postgres):
docker compose up -d --build
docker compose logs api | grep 'bearer token'   # dev-adjuster token, printed once on first boot

# DB migrations (alembic/env.py reads DATABASE_URL from Settings, not alembic.ini)
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## Architecture

**Request flow is controller → in-process agent → MCP server**, not a flat call graph:

- `api/fnol_controller.py` and `api/adjuster_controller.py` are the only HTTP entry points. They hold no business logic — they load/persist `ClaimRow`, then delegate to an agent from `app.state`.
- `fnol/agent.py` and `adjuster/agent.py` are **in-process** orchestrators (plain Python objects on `app.state`, not separate services). `adjuster/agent.py`'s subagents (`adjuster/subagents/*`) are also in-process — they call KMA's `search` tool, they do not get their own MCP server.
- `mcp_servers/{kma,fraud_agent,compliance_agent}/server.py` are the only three components that run as **separate processes**, each exposing tools over real Streamable HTTP (the `mcp` SDK, major version 2.x — note the v2 API differs from most online examples: `mcp.server.mcpserver.MCPServer` not `fastmcp.FastMCP`, `streamable_http_client` not `streamablehttp_client`). `core/mcp_client.py` is the only place that opens MCP client sessions; agents call it, never the SDK directly.
- `prediction/reasoner.py` (PredictionModel) is a **direct LLM call**, not an agent and not an MCP server — it reasons over Adjuster Agent's combined text summary, no feature-vector step.

**Data flow**: FNOL intake → Compliance Agent (`scan_and_mask`, field-aware masking) → KMA (`store_document`) → `claims` row. Adjuster review → PolicySearchAgent + SimilarClaimAgent (both call KMA `search`) → FraudAgent `assess_claim` → if fraud, `explain_fraud` and stop; if not, PredictionModel → human decision → dual-write to KMA (`store_document`, type `adjuster_feedback`) and `training_feedback`.

**Provider pluggability**: every swappable component is a `Protocol` with a `build_x(kind)` factory, selected by env var in `core/config.py` (`EMBEDDING_PROVIDER`, `VECTOR_STORE`, `RERANKER`, `LLM_PROVIDER`, `PII_DETECTOR`). Every one defaults to an in-memory/no-credential "fake" implementation, so the entire lifecycle runs with zero external services — real implementations (Pinecone, BGE-M3, BGE-reranker, Anthropic, Presidio) are opt-in via `.env`. When adding a new provider kind, add both a real and a fake implementation and wire the factory the same way; don't special-case call sites.

**Audit trail**: `core/audit/interfaces.py`'s `AuditSink` Protocol, `PostgresAuditSink` is the only implementation. Every agent/controller action writes an `AuditEvent` tagged with the current `trace_id` (`shared/correlation.py`, a contextvar set once per inbound request) — `get_trace(trace_id)` reconstructs a claim's full journey. When adding a new agent action, write an audit event for it; that's how Phase 1 satisfies the explainability requirement, not app-level logging.

**Auth**: FastAPI dependency-injection (`core/auth/dependencies.py`'s `require_role("adjuster")`), not middleware — this is deliberate so Phase 2's OAuth2/AD swap only touches `core/auth/*` and the DI binding in `api/main.py`, never controllers. `StaticRBACAuthenticator` checks a SHA-256-hashed bearer token against the `users` table; there's no user-provisioning flow, only a dev-adjuster auto-seeded on first API boot.

**Storage**: `storage/models.py` SQLAlchemy models work against Postgres (docker-compose) or SQLite (tests/local dev) via the same `DATABASE_URL`-driven engine (`storage/db.py`) — no Postgres schema-level separation despite that language in the original plan (see "As Built" deviations in `docs/architecturePlan.md`). `ClaimRow` carries a `policy_data` JSON blob supplied at intake, standing in for a Phase 2 policy-management system.

**MCP servers are long-running singletons with in-process state where relevant** — e.g. `mcp_servers/fraud_agent/server.py` caches the last `assess_claim` result per `claim_id` in a module-level dict for the subsequent `explain_fraud` call. This breaks if FraudAgent is ever horizontally scaled; revisit then.

**Tests**: `tests/conftest.py`'s `mcp_servers` fixture launches the three real MCP servers as subprocesses (fake providers, shared temp SQLite) — `tests/integration` and `tests/contract` exercise real MCP wire calls, not mocks. `tests/unit` has no subprocess dependency and runs in ~0.2s.
