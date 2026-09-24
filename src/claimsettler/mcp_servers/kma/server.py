"""KMA (Knowledge Management Agent) MCP server. Pure RAG store: takes claim
documents, policy documents, product rulebooks; chunking/embedding/
vectorizing pipeline; VSA hybrid search + rerank + grounded generation.

Run: python -m claimsettler.mcp_servers.kma.server
"""

from __future__ import annotations

import os
import uuid
from typing import Any

from mcp.server.mcpserver import MCPServer

from claimsettler.core.audit.models import AuditEvent
from claimsettler.core.audit.postgres_sink import PostgresAuditSink
from claimsettler.core.config import get_settings
from claimsettler.core.llm import build_llm_client
from claimsettler.shared.correlation import get_trace_id
from claimsettler.storage.db import Database

from .document_links import build_link_metadata
from .ingestion.chunking import chunk_text
from .ingestion.embedding import build_embedding_provider
from .ingestion.store import VectorRecord, build_vector_store
from .vsa.hybrid_search import hybrid_search
from .vsa.query_rewrite import rewrite_query
from .vsa.reranker import build_reranker
from .vsa.response_generation import generate_grounded_response

server = MCPServer(name="kma")
_settings = get_settings()
_db = Database(_settings)
_embedding_provider = build_embedding_provider(_settings.embedding_provider)
_vector_store = build_vector_store(
    _settings.vector_store,
    api_key=_settings.pinecone_api_key,
    index_name=_settings.pinecone_index,
    dimensions=_embedding_provider.dimensions,
)
_reranker = build_reranker(_settings.reranker)
_llm = build_llm_client(_settings)
_audit: PostgresAuditSink = PostgresAuditSink(_db.session_factory)


@server.tool()
async def store_document(
    document: dict[str, Any],
    document_type: str,
    claim_id: str | None = None,
    policy_id: str | None = None,
    product_id: str | None = None,
) -> dict[str, Any]:
    """Chunks, embeds, and upserts a (already Compliance-Agent-masked)
    document into the vector store, linked to claim/policy/product IDs."""
    text = "\n".join(f"{k}: {v}" for k, v in document.items() if isinstance(v, str))
    chunks = chunk_text(
        text,
        chunk_size_tokens=_settings.chunk_size_tokens,
        overlap_tokens=_settings.chunk_overlap_tokens,
    )
    if not chunks:
        return {"document_id": None, "chunks_stored": 0}

    embeddings = await _embedding_provider.embed_documents([c.text for c in chunks])
    metadata = build_link_metadata(
        document_type=document_type, claim_id=claim_id, policy_id=policy_id, product_id=product_id
    )
    document_id = uuid.uuid4().hex
    records = [
        VectorRecord(
            id=f"{document_id}:{c.index}",
            embedding=embeddings[i],
            text=c.text,
            metadata={**metadata, "chunk_index": c.index},
        )
        for i, c in enumerate(chunks)
    ]
    await _vector_store.upsert(records)

    await _audit.write(
        AuditEvent(
            trace_id=get_trace_id(),
            actor_type="agent",
            actor_id="kma",
            action="kma.document.ingested",
            entity_type=document_type,
            entity_id=claim_id or policy_id or document_id,
            metadata={"chunks_stored": len(records), "embedding_model": _embedding_provider.model_name},
        )
    )
    return {"document_id": document_id, "chunks_stored": len(records)}


@server.tool()
async def search(
    query: str, top_k: int = 5, metadata_filter: dict[str, Any] | None = None
) -> dict[str, Any]:
    """VSA: query rewrite -> hybrid (semantic + BM25) search -> rerank ->
    grounded, cited response generation."""
    normalized_query = await rewrite_query(query, _llm)
    matches = await hybrid_search(
        normalized_query,
        embedding_provider=_embedding_provider,
        vector_store=_vector_store,
        reranker=_reranker,
        top_k=top_k,
        metadata_filter=metadata_filter,
    )
    answer, citations = await generate_grounded_response(normalized_query, matches, _llm)

    await _audit.write(
        AuditEvent(
            trace_id=get_trace_id(),
            actor_type="agent",
            actor_id="kma.vsa",
            action="kma.search.completed",
            entity_type="search_query",
            entity_id=normalized_query[:64],
            metadata={
                "original_query": query,
                "rewritten_query": normalized_query,
                "matches": len(matches),
                "llm_model": getattr(_llm, "_model", "fake"),
            },
        )
    )
    return {
        "answer": answer,
        "citations": citations,
        "matches": [
            {"text": m.record.text, "score": m.score, "metadata": m.record.metadata} for m in matches
        ],
    }


if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8100"))
    server.run(transport="streamable-http", host=host, port=port)
