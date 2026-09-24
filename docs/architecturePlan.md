# ClaimSettler — Architecture & Phase 1 Build Plan

> **Status: Phase 1 implemented and verified.** See "Phase 1 — As Built" at
> the end of this document for what actually shipped, where it deviated
> from the plan below, and how to run it. The original plan is left intact
> above/below as the design record.

## Context

ClaimSettler is a greenfield agentic AI platform for insurance claim processing (Auto/Home/Commercial), ~50k claims/year growing ~10% YoY. Goal: cut manual effort/processing time while catching fraud and duplicate claims. The repo today is an empty skeleton (README.md with domain narrative, bare pyproject.toml, hello-world main.py) — nothing to preserve, this plan defines the system from scratch.

The user supplied a fixed, detailed architecture (controllers, agents, MCP boundaries, phased rollout) and asked for: a consistency check, a list of open questions, a repo/module structure, storage-agnostic audit-trail and auth abstractions, a pluggable KMA/VSA interface, an MLOps boundary, and a justified phased plan. A design pass was done and four genuinely open architectural decisions were resolved with the user (below); everything else in this plan is either the user's fixed spec or a low-controversy recommended default they can override on read-through.

### Decisions confirmed with the user this session

1. **PredictionModel = LLM-based reasoning step** (PlannerAgent-style), not a trained tabular classifier. It remains a direct in-process call (never MCP, never a subagent orchestrator) — it just means "direct call to an LLM" rather than "direct call to XGBoost." It reasons over the combined PolicySearchAgent + SimilarClaimAgent text summary directly; **no feature-engineering bridge needed**. This resolves the README-vs-spec naming conflict: the "PlannerAgent" behavior README describes and the "PredictionModel, direct model invocation" wording in the user's spec are the same component.
2. **FraudAgent exposes two MCP tools**, not one: `assess_claim` (verdict + confidence + rule hits, no ML detail) and `explain_fraud` (detailed reasoning, called by Adjuster Agent only when verdict is fraud) — two round trips, matching the literal flow in the spec.
3. **Compliance Agent uses field-aware, schema-driven masking**: structured linking IDs pass through unmasked (with format validation), free-text narrative fields get full NER masking, and sensitive-but-linkable fields (e.g. VIN) get reversible tokenization rather than full masking — so KMA's claim→policy→product reference graph never breaks and cross-claim fraud-graph linkage still works on tokenized fields.
4. **Vector DB is Pinecone from day one** (user's original lean, kept over the pgvector-first recommendation). Embedding (BGE-M3) and reranker (BGE-reranker) stay as the user's original lean — no divergence there. Note: BGE-M3 natively emits dense+sparse+ColBERT-style vectors, which pairs well with Pinecone's hybrid (sparse+dense) index support for the hybrid-search requirement, so no separate BM25 store is needed.

### Other defaults adopted (low-controversy, flag if you disagree on read-through)

- **Web framework: FastAPI** — DI-based auth (`Depends()`) matches the "filter chain" requirement precisely, async-native, Pydantic DTOs double as MCP tool schemas.
- **MCP hosting: Streamable HTTP**, each MCP server (KMA, FraudAgent, ComplianceAgent) its own long-running process/container, addressed via a static config map (`MCP_SERVERS = {"kma": "http://kma:8100/mcp", ...}`) — no service registry needed at this scale.
- **Postgres, one instance, three schemas**: `claims` (operational state), `audit` (append-only trail), `training_feedback` (adjuster decisions for retraining).
- **FNOLController ↔ FNOL Agent: blocking call in Phase 1** (JSON-only intake, nothing long-running yet). A job queue (arq/Redis or Postgres-queue) is deferred to Phase 2 when OCR/voice/video skills land — but the FNOLController API shape should anticipate `202 + pollable status` so this doesn't require a controller rewrite later.
- **Repo layout: single monorepo**, not separate repos per MCP server — MCP already gives runtime/process decoupling; multiple repos would only add cross-repo PR overhead with no current payoff. Revisit if a server is ever consumed outside ClaimSettler.
- **MLOps: `mlops/` subproject inside the monorepo**, own `pyproject.toml`/deps, split into its own repo only if a separate team forms. Scope is now narrower than originally sketched: since PredictionModel is LLM-based (no training), the model-registry/artifact-promotion contract applies only to **Phase 3 FraudAgent ML modules** (supervised/anomaly/graph), not PredictionModel.
- **Deployment: docker-compose for Phase 1** (Postgres, KMA, FraudAgent, ComplianceAgent, API) — no k8s needed at this scale yet.
- **RBAC source of truth: minimal `users`/`roles` Postgres table** for Phase 1, swapped for OAuth2/AD in Phase 2 behind the same `Authenticator` interface.
- **Testing/CI**: `pytest` + `pytest-asyncio`, `httpx.AsyncClient` for FastAPI endpoint tests, the `mcp` SDK's client for MCP contract tests; GitHub Actions running lint (`ruff`) + type-check + tests.
- **Neo4j deferred entirely to Phase 3** — not stood up as unused Phase 1 infra.

## Consistency check — resolved

Playing back the full graph (FNOLController → FNOL Agent → skills → Compliance Agent → KMA → Postgres row; AdjusterController → Adjuster Agent → {PolicySearchAgent, SimilarClaimAgent} → VSA → FraudAgent (assess_claim, then explain_fraud only if fraud) → PredictionModel (LLM call on combined summary) → AdjusterController → human approval → dual-write to KMA + Postgres) is now internally consistent. One remaining note, not a blocker: **Compliance Agent runs after FNOL Agent's modality skills normalize input to text**, before the KMA-store MCP call — NER-based PII detection needs text, not raw audio/video bytes. Confirm this ordering is what you intended; it's assumed throughout this plan.

## Repo / module structure

```
claimsettler/
├── pyproject.toml
├── docker-compose.yml              # postgres, kma, fraud_agent, compliance_agent, api
├── alembic/                        # migrations for claims/audit/training_feedback schemas
├── src/claimsettler/
│   ├── api/
│   │   ├── main.py                  # FastAPI app factory, router mounting
│   │   ├── fnol_controller.py       # POST /claims
│   │   ├── adjuster_controller.py   # GET/POST /claims/{id}/decision
│   │   └── schemas.py               # Pydantic DTOs
│   ├── core/
│   │   ├── config.py                 # MCP server URLs, DB DSN, provider config — the one place Phase 2 swaps happen
│   │   ├── auth/
│   │   │   ├── interfaces.py         # Authenticator / Authorizer Protocols
│   │   │   ├── rbac.py               # Phase 1: StaticRBACAuthenticator, SimpleRoleAuthorizer
│   │   │   ├── oauth2.py             # Phase 2 stub
│   │   │   └── dependencies.py       # get_current_principal, require_role("adjuster")
│   │   ├── audit/
│   │   │   ├── interfaces.py         # AuditSink Protocol
│   │   │   ├── models.py             # AuditEvent
│   │   │   └── postgres_sink.py      # Phase 1 impl
│   │   ├── mcp_client.py             # wraps mcp SDK client, resolves logical name -> URL via config
│   │   └── errors.py
│   ├── fnol/
│   │   ├── agent.py                   # FNOLAgent.process_claim(...)
│   │   └── skills/
│   │       ├── base.py                # Skill Protocol: normalize(input) -> ClaimDocument
│   │       ├── voice_to_text.py        # Phase 3
│   │       ├── video_to_text.py        # Phase 3
│   │       ├── ocr_form.py             # Phase 2
│   │       └── doc_parser.py           # Phase 2 (pdf/word/text)
│   ├── adjuster/
│   │   ├── agent.py                    # supervisor: orchestrates subagents, calls FraudAgent MCP, PredictionModel
│   │   └── subagents/
│   │       ├── policy_search_agent.py  # calls VSA
│   │       └── similar_claim_agent.py  # calls VSA
│   ├── prediction/
│   │   ├── reasoner.py                 # PredictionModel: LLM call over combined summary -> Decision
│   │   └── prompts.py
│   ├── mcp_servers/
│   │   ├── kma/
│   │   │   ├── server.py
│   │   │   ├── ingestion/
│   │   │   │   ├── chunking.py         # semantic chunking, 500-700 tok / 100 overlap
│   │   │   │   ├── embedding.py         # EmbeddingProvider Protocol + BGEM3/OpenAI impls
│   │   │   │   └── store.py              # VectorStore Protocol + PineconeVectorStore (Phase 1), PgVectorStore (optional alt)
│   │   │   ├── vsa/
│   │   │   │   ├── query_rewrite.py
│   │   │   │   ├── hybrid_search.py      # Pinecone sparse+dense hybrid (BGE-M3 sparse vectors)
│   │   │   │   └── reranker.py            # Reranker Protocol + BGEReranker/Cohere impls
│   │   │   └── document_links.py         # claim->policy->product reference graph
│   │   ├── fraud_agent/
│   │   │   ├── server.py                  # MCP tools: assess_claim, explain_fraud
│   │   │   ├── rule_engine_agent.py        # in-proc, deterministic checks (Phase 1)
│   │   │   ├── fraud_detector.py           # combined confidence scoring
│   │   │   └── ml_modules/                  # Phase 3: supervised_model.py, anomaly_detection.py, graph_analysis.py (Neo4j)
│   │   └── compliance_agent/
│   │       ├── server.py                    # MCP tool: scan_and_mask
│   │       ├── pii_detector.py               # NER-based detection (e.g. Protecto)
│   │       ├── masking_policy.py             # field-aware allow-list / NER-mask / tokenize (see below)
│   │       └── policies/                     # Phase 2: gdpr.py, dpdpa.py, hipaa.py, soc2.py
│   ├── storage/
│   │   ├── db.py                              # SQLAlchemy engine/session, schema-aware
│   │   └── models.py                          # Claim, AuditEvent, TrainingFeedback ORM models
│   └── shared/
│       ├── types.py                            # ClaimDocument, ClaimStatus, etc.
│       └── correlation.py                      # trace/correlation id propagation
├── tests/
│   ├── unit/
│   ├── integration/                            # MCP servers spun up in-proc against test doubles
│   └── contract/                                # MCP tool-schema contract tests per server
└── mlops/                                        # Phase 3 scope only (FraudAgent ML modules); own pyproject.toml
```

Notes:
- `mcp_servers/*/server.py` is each an independently deployable unit (`python -m claimsettler.mcp_servers.kma.server`, etc.), one container each in docker-compose, communicating over Streamable HTTP.
- `adjuster/subagents/*` and `fraud_agent/rule_engine_agent.py` / `ml_modules/*` are plain importable classes — never given their own `server.py`, per the spec's "subagent, not MCP" distinction.
- `prediction/reasoner.py` sits at the top level, sibling to `fnol/`/`adjuster/`, to keep visually clear it's a direct call, not an agent package.

## Compliance Agent masking taxonomy (starter list — refine with legal/compliance before Phase 1 ships)

- **Unmasked, format-validated** (needed for KMA linking): `claim_id`, `policy_id`, `product_id`, `adjuster_id`, timestamps, claim status.
- **Fully masked via NER** (free-text fields: claim narrative, adjuster notes, witness statements): customer name, address, phone, email, SSN, date of birth, driver's license number, medical record references.
- **Reversibly tokenized** (sensitive but needed for cross-claim/fraud-graph linkage): VIN, and similar entity-linking identifiers (repair shop ID, provider ID) if fraud-ring analysis needs them in Phase 3.

`compliance_agent/masking_policy.py` encodes this as the allow-list/NER-scope/tokenize-scope config; `pii_detector.py` runs NER only against the free-text scope, never the whole flattened document, so structural IDs can never be accidentally masked.

## Audit trail interface (storage-agnostic)

```python
# core/audit/models.py
@dataclass(frozen=True)
class AuditEvent:
    event_id: UUID
    trace_id: str                 # correlation id across controller -> agent -> MCP calls
    timestamp: datetime
    actor_type: str               # "user" | "system" | "agent"
    actor_id: str
    action: str                   # e.g. "claim.fnol.received", "fraud.assessment.completed"
    entity_type: str              # "claim" | "policy" | "fraud_assessment" | "prediction" ...
    entity_id: str
    before_state: dict | None = None
    after_state: dict | None = None
    metadata: dict = field(default_factory=dict)   # model/LLM version, confidence, prompts, chunks used

# core/audit/interfaces.py
class AuditSink(Protocol):
    async def write(self, event: AuditEvent) -> None: ...
    async def write_batch(self, events: Iterable[AuditEvent]) -> None: ...
    async def query(self, *, entity_type=None, entity_id=None, trace_id=None,
                     actor_id=None, action=None, since=None, until=None,
                     limit=100, offset=0) -> list[AuditEvent]: ...
    async def get_trace(self, trace_id: str) -> list[AuditEvent]: ...   # full claim journey reconstruction
```

`PostgresAuditSink` is the only Phase 1 implementation. All call sites depend on `AuditSink`, injected via `core/config.py`, never on the Postgres class directly — swapping to Splunk/S3 later is a new implementation class + one config binding.

## Auth / filter abstraction

FastAPI dependency-injection-based (not raw ASGI middleware) — composes per-route, typed, testable, and matches the "filter chain" requirement without hand-rolled ASGI plumbing. Light ASGI middleware is still used, but only for correlation-id propagation (applies uniformly to every request), not for auth.

```python
# core/auth/interfaces.py
@dataclass(frozen=True)
class Principal:
    user_id: str
    display_name: str
    roles: frozenset[str]
    auth_method: str        # "rbac_static" | "oauth2_ad"

class Authenticator(Protocol):
    async def authenticate(self, credentials: str) -> Principal | None: ...

class Authorizer(Protocol):
    def is_authorized(self, principal: Principal, required_role: str) -> bool: ...

# core/auth/dependencies.py
def require_role(role: str):
    def _dep(principal: Principal = Depends(get_current_principal),
              authorizer: Authorizer = Depends(get_authorizer)) -> Principal:
        if not authorizer.is_authorized(principal, role):
            raise HTTPException(403, f"requires role: {role}")
        return principal
    return _dep

# api/adjuster_controller.py
@router.post("/claims/{claim_id}/decision")
async def submit_decision(claim_id: str, body: DecisionRequest,
                           principal: Principal = Depends(require_role("adjuster"))): ...
```

Phase 2 = implement `OAuth2ADAuthenticator(Authenticator)`, rebind `get_authenticator` in `core/config.py`. Zero controller changes.

## KMA/VSA pluggability

`EmbeddingProvider`, `VectorStore`, `Reranker` are each a `Protocol`, selected by config (`EMBEDDING_PROVIDER=bge_m3`, `VECTOR_STORE=pinecone`, `RERANKER=bge_reranker`). Phase 1 concrete choices: `BGEM3EmbeddingProvider` (self-hosted), `PineconeVectorStore`, `BGERerankerProvider` (self-hosted, pairs with BGE-M3). Swapping any later is a new class + one config value, not a rewrite.

## Phased build plan

**Phase 1 (this plan's scope)** — JSON-only intake end to end:
1. Postgres up (`claims`/`audit`/`training_feedback` schemas).
2. Audit trail (`AuditSink` + `PostgresAuditSink`) — built early since every other component logs to it.
3. Auth module (`core/auth`, `StaticRBACAuthenticator`) — needed before AdjusterController exists.
4. JSON claim intake: FNOLController → FNOL Agent (in-proc, no skills needed for JSON) → Compliance Agent (MCP, field-aware masking) → KMA (MCP: chunk / BGE-M3 embed / Pinecone store).
5. VSA: hybrid (Pinecone sparse+dense) search + BGE-reranker + grounded response with citations, audit-logged.
6. Adjuster flow: AdjusterController (RBAC-gated) → Adjuster Agent → PolicySearchAgent + SimilarClaimAgent (call VSA) → combined summary.
7. FraudAgent (MCP): `assess_claim` backed by RuleEngineAgent only (ML modules deferred to Phase 3); `explain_fraud` for the fraud path.
8. PredictionModel: LLM call over the combined summary → approve/reject recommendation + rationale.
9. Human adjuster approval endpoint; feedback written to KMA + Postgres `training_feedback`.

*Why RuleEngine-only fraud before ML fraud*: deterministic, needs no training data, independently testable/explainable from day one, and there's no real historic data yet (Phase 1 is synthetic) to train supervised/anomaly models against.
*Why JSON-only intake before multimodal*: exercises the full downstream pipeline (Compliance → KMA → VSA → Adjuster → Fraud → Prediction → audit) without the orthogonal complexity of voice/video/OCR integrations, each of which is its own project with its own failure modes.

**Phase 2**: OCR + doc-parsing skills (higher-value, lower-risk than voice/video) → job-queue async intake → FNOL Agent becomes MCP client invoking Adjuster Agent directly → OAuth2/AD auth swap → Compliance Agent extended to DPDPA/SOC2/HIPAA → real historic claims data ingestion begins, PredictionModel prompts/PII-masking recalibrated against real data.

**Phase 3+**: voice/video-to-text skills → FraudAgent ML modules (supervised → anomaly → graph/Neo4j, in that order — graph fraud-ring detection needs real volume/density Phase 1-2 won't have) → `mlops/` split to its own repo if a separate team forms → k8s if docker-compose stops being sufficient.

## Definition of done + test strategy (Phase 1)

- **End-to-end**: JSON claim → row in `claims` with correct status transitions → retrievable via VSA with citations → adjuster (RBAC) sees combined summary + rule-engine fraud verdict + PredictionModel recommendation → approve/reject recorded → feedback in KMA + `training_feedback` → full journey reconstructable via `get_trace(trace_id)`.
- **RAG groundedness**: a small synthetic eval set (question → expected source doc + facts), assert VSA cites the right document and doesn't introduce facts absent from retrieved chunks — repeatable, not one-off, since embedding/reranker swaps need a regression baseline.
- **MCP contract tests**: per server (KMA, FraudAgent, ComplianceAgent), connect as an MCP client, validate tool input/output schemas stay stable.
- **Fraud-path correctness**: rule-engine test cases with known rule violations assert correct verdict + explanation fields.
- **Latency**: at ~50k claims/yr (~140/day, bursty), target sub-2s for a single VSA retrieval+rerank+generation, sub-5s for full Adjuster Agent orchestration (two VSA calls + FraudAgent MCP round trips + PredictionModel LLM call) — generous, since this is human-in-the-loop, not real-time.
- **Synthetic data**: generate via LLM-assisted generator, tag every synthetic record with `metadata.synthetic=true` so Phase 2 real-data retraining/recalibration can exclude it cleanly.

## Domain risks to carry forward

- **Explainability for denials**: PredictionModel's LLM output should include its stated rationale in the audit event `metadata` (not just the raw decision) from Phase 1 on — denied claims need a reconstructable "why" independent of the adjuster's own notes, given regulatory appeal exposure.
- **PII leakage**: Compliance Agent's NER pass can miss atypical PII. Recommend KMA run a lightweight secondary regex-based check (SSN/credit-card/phone patterns) immediately before persisting, quarantining (not silently dropping) anything that fires — cheap defense-in-depth against the most likely failure mode.
- **Synthetic-to-real transfer**: tag synthetic data explicitly (above), treat Phase 1 rule-engine thresholds as provisional, and gate a recalibration step at the start of Phase 2 before real adjuster decisions depend on them.

## Verification

- Run the full docker-compose stack locally; submit a synthetic JSON claim through FNOLController; confirm it lands in `claims` (Postgres) and is retrievable via a VSA query with correct citations.
- As an RBAC "adjuster" user, call AdjusterController for that claim; confirm PolicySearchAgent/SimilarClaimAgent/RuleEngineAgent/PredictionModel all execute and return a coherent combined view; confirm a non-adjuster user gets 403.
- Submit approve/reject; confirm rows appear in `training_feedback` and KMA, and `get_trace(trace_id)` returns the complete event chain from intake through decision.
- Run `pytest` (unit + integration + MCP contract suites) and the RAG groundedness eval set; all green before calling Phase 1 done.

---

## Phase 1 — As Built

Implemented in `src/claimsettler/`, verified both via `pytest` (33 tests: unit + integration + MCP contract) and live against the full `docker-compose` stack (real Postgres, real MCP wire calls over Streamable HTTP, real Presidio PII masking) — a JSON claim was submitted, reviewed, and decided end-to-end with every audit event landing in Postgres. The design above held up with no architectural surprises; the deviations below are implementation-level refinements, not scope changes.

### Deviations / refinements from the plan above

1. **MCP SDK is now major version 2.x** (`mcp==2.2.0` at build time), which renamed the v1 API the plan implicitly assumed: `mcp.server.fastmcp.FastMCP` → `mcp.server.mcpserver.MCPServer`, client `streamablehttp_client` → `streamable_http_client`, `CallToolResult.isError` → `.is_error`. Code targets the actual installed 2.x API. `CallToolResult.structured_content` is used directly when present (typed dict return from a tool), falling back to parsing `content[0].text` otherwise — see `core/mcp_client.py`.
2. **`adjuster/feature_extractor.py` was dropped.** Once PredictionModel was confirmed as an LLM-reasoning step (not a tabular classifier — decision #1 above), there's no feature vector to build; `prediction/reasoner.py` reasons directly over the Adjuster Agent's combined text summary via `prediction/prompts.py`.
3. **Every provider Protocol has both a real and a "fake" implementation**, config-selected (`EMBEDDING_PROVIDER`, `VECTOR_STORE`, `RERANKER`, `LLM_PROVIDER` = real-name | `fake`, default `fake`): `PineconeVectorStore`/`InMemoryVectorStore`, `BGEM3EmbeddingProvider`/`FakeEmbeddingProvider`, `BGERerankerProvider`/`FakeReranker`, `AnthropicLLMClient`/`FakeLLMClient`. This means the full claim lifecycle runs with zero external credentials out of the box; flipping to real backends is purely a `.env` change. `FakeLLMClient` sniffs the system prompt to return a shape-appropriate fake response (structured recommendation vs. identity query-rewrite vs. generic grounded answer) rather than one canned string for every call site — an early version leaked a canned "grounded response" string into VSA's query-rewrite step, which was caught and fixed during live docker-compose verification (see audit trail entries with `kma.search.completed` for the before/after).
4. **Compliance Agent's PII detector is Microsoft Presidio** (open-source, spaCy `en_core_web_sm`-backed), confirmed with the user in place of the commercial "Protecto" named in the original brief — swappable behind the same `PIIDetector` Protocol. A `RegexOnlyPIIDetector` fallback also exists (`PII_DETECTOR=regex_only`) and is what the automated test suite uses by default, since it needs no model load.
5. **Postgres "one instance, three schemas" was implemented as three plain tables** (`claims`, `audit_events`, `training_feedback`) plus `users`, all in the default schema/database — not true Postgres `CREATE SCHEMA` separation. This keeps the SQLAlchemy models portable across Postgres (production, via docker-compose) and SQLite (local dev/test, per the user's confirmed choice), which was worth more than schema-level isolation at Phase 1. Revisit if/when a backing-store split (e.g. audit → Splunk) actually happens — the `AuditSink` interface doesn't change either way.
6. **Auth is opaque bearer API keys (SHA-256 hashed), not JWTs** — the simplest thing that satisfies "simple RBAC" and the `Authenticator`/`Authorizer` Protocol boundary. The API auto-seeds one `dev-adjuster` user on first startup and prints its token once (also on `app.state.dev_adjuster_token`) — there is no user-provisioning flow in Phase 1 by design.
7. **Phase 1 has no policy-management system**, so `ClaimRow` carries a `policy_data` JSON blob supplied alongside the claim at intake (synthetic, per the Phase 1 data plan) so RuleEngineAgent has something concrete to check. This is the explicit Phase 2 replacement point: real policy lookups (likely via KMA/VSA against ingested policy documents) replace client-supplied `policy_data`.
8. **`FraudAgent.explain_fraud` reads an in-process cache** (`{claim_id: FraudDetection}`) populated by the preceding `assess_claim` call, rather than recomputing or requiring the full claim payload again — valid because FraudAgent is one long-running singleton process per the MCP hosting design; revisit if FraudAgent is ever horizontally scaled.
9. **`AdjusterController.POST /decision` round-trips fraud/prediction context from the client** (i.e. whatever the earlier `GET /review` response returned) rather than the server re-caching review state — the simplest Phase 1 choice that keeps the decision endpoint stateless.
10. Project renamed `claudebasic` → `claimsettler` in `pyproject.toml`; the venv is pinned to **Python 3.13.7** (not the repo's default 3.14 release candidate) for stable wheel availability against Presidio/spaCy.

### Repo layout (what actually exists)

Matches the "Repo / module structure" tree above, with `prediction/` containing `reasoner.py` + `prompts.py` (no `model_loader.py`/`ModelRegistry` — that MLOps contract now applies only to Phase 3 FraudAgent ML modules, not PredictionModel, per deviation #2). `docker-compose.yml` + one shared `Dockerfile` build all four services (api, kma, fraud_agent, compliance_agent) plus Postgres. `alembic/` holds one migration (`initial schema: claims, audit_events, training_feedback, users`) generated via `alembic revision --autogenerate`.

### How to run it

```bash
cp .env.example .env               # defaults to fake providers + SQLite, zero credentials needed
uv venv --python 3.13.7 .venv && source .venv/bin/activate
uv pip install -e ".[dev]"
python -m spacy download en_core_web_sm   # only needed if PII_DETECTOR=presidio (default)
pytest tests -q                    # 33 tests: unit + integration (real MCP servers as subprocesses) + contract

# Full stack, real Postgres:
docker compose up -d --build
curl -X POST localhost:8000/claims -H 'Content-Type: application/json' -d '{...}'
docker compose logs api | grep 'bearer token'     # dev-adjuster token, printed once on first boot
curl localhost:8000/claims/<id>/review -H "Authorization: Bearer <token>"
curl -X POST localhost:8000/claims/<id>/decision -H "Authorization: Bearer <token>" -d '{...}'
```

To use real backends instead of fakes, set in `.env`: `EMBEDDING_PROVIDER=bge_m3`, `VECTOR_STORE=pinecone` + `PINECONE_API_KEY`, `RERANKER=bge_reranker`, `LLM_PROVIDER=anthropic` + `ANTHROPIC_API_KEY`. `BGEM3EmbeddingProvider`/`BGERerankerProvider` need the `ml` extra (`uv pip install -e ".[ml]"`) and download multi-GB model weights on first use — not exercised in this session's verification.

### Not yet done

Everything explicitly scoped to Phase 2/3 in the plan above (multimodal FNOL skills, OAuth2/AD, FraudAgent ML modules, DPDPA/SOC2/HIPAA policies, `mlops/` subproject). Also not done in this pass: the RAG groundedness eval set and synthetic data generator described in "Definition of done + test strategy" — the integration/contract tests verify plumbing correctness (masking, rule engine, MCP contracts, full lifecycle), not retrieval quality, which needs a real embedding/reranker backend and a curated eval set to mean anything.
