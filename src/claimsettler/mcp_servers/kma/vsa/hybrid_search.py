"""Hybrid search: semantic vector similarity + BM25 lexical search +
metadata filtering, merged, then passed through the cross-encoder reranker.
"""

from __future__ import annotations

from typing import Any

from claimsettler.mcp_servers.kma.ingestion.embedding import EmbeddingProvider
from claimsettler.mcp_servers.kma.ingestion.store import VectorMatch, VectorStore

from .reranker import Reranker


async def hybrid_search(
    query: str,
    *,
    embedding_provider: EmbeddingProvider,
    vector_store: VectorStore,
    reranker: Reranker,
    top_k: int,
    metadata_filter: dict[str, Any] | None = None,
    candidate_pool: int = 20,
) -> list[VectorMatch]:
    query_embedding = await embedding_provider.embed_query(query)
    semantic_matches = await vector_store.query(query_embedding, candidate_pool, metadata_filter)
    lexical_matches = await vector_store.bm25_query(query, candidate_pool, metadata_filter)

    merged: dict[str, VectorMatch] = {m.record.id: m for m in semantic_matches}
    for match in lexical_matches:
        if match.record.id not in merged:
            merged[match.record.id] = match

    candidates = list(merged.values())
    if not candidates:
        return []

    texts = [c.record.text for c in candidates]
    reranked = await reranker.rerank(query, texts, top_k)
    return [candidates[i] for i, _score in reranked]
