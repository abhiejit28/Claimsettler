"""VectorStore Protocol + implementations. Config-selected (VECTOR_STORE=
pinecone|fake). Pinecone is the Phase 1 production choice (confirmed with
the user); the in-memory fake lets the full flow run locally without an
account/API key."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class VectorRecord:
    id: str
    embedding: list[float]
    text: str
    metadata: dict[str, Any]


@dataclass
class VectorMatch:
    record: VectorRecord
    score: float


class VectorStore(Protocol):
    async def upsert(self, records: list[VectorRecord]) -> None: ...

    async def query(
        self, embedding: list[float], top_k: int, metadata_filter: dict[str, Any] | None = None
    ) -> list[VectorMatch]: ...

    async def bm25_query(
        self, text: str, top_k: int, metadata_filter: dict[str, Any] | None = None
    ) -> list[VectorMatch]: ...

    async def delete(self, ids: list[str]) -> None: ...


class PineconeVectorStore:
    """Real implementation. BGE-M3 emits dense+sparse vectors, which pairs
    with Pinecone's native hybrid (sparse+dense) index support — no
    separate BM25 store needed. Requires PINECONE_API_KEY."""

    def __init__(self, api_key: str, index_name: str, dimensions: int) -> None:
        from pinecone import Pinecone, ServerlessSpec

        self._client = Pinecone(api_key=api_key)
        if index_name not in [i.name for i in self._client.list_indexes()]:
            self._client.create_index(
                name=index_name,
                dimension=dimensions,
                metric="dotproduct",  # required for sparse+dense hybrid queries
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )
        self._index = self._client.Index(index_name)

    async def upsert(self, records: list[VectorRecord]) -> None:
        vectors = [
            {"id": r.id, "values": r.embedding, "metadata": {**r.metadata, "text": r.text}}
            for r in records
        ]
        self._index.upsert(vectors=vectors)

    async def query(
        self, embedding: list[float], top_k: int, metadata_filter: dict[str, Any] | None = None
    ) -> list[VectorMatch]:
        result = self._index.query(
            vector=embedding, top_k=top_k, filter=metadata_filter, include_metadata=True
        )
        return [
            VectorMatch(
                record=VectorRecord(
                    id=m.id,
                    embedding=[],
                    text=m.metadata.get("text", ""),
                    metadata=m.metadata,
                ),
                score=m.score,
            )
            for m in result.matches
        ]

    async def bm25_query(
        self, text: str, top_k: int, metadata_filter: dict[str, Any] | None = None
    ) -> list[VectorMatch]:
        # Phase 1: Pinecone hybrid search is driven by sparse vectors from the
        # embedding provider, not a separate lexical query path. Real hybrid
        # scoring is wired in vsa/hybrid_search.py; this fallback keeps the
        # VectorStore contract complete for providers without native hybrid.
        return []

    async def delete(self, ids: list[str]) -> None:
        self._index.delete(ids=ids)


class InMemoryVectorStore:
    """Fake — cosine similarity over an in-process dict. No credentials, no
    network; used for local dev/test and as the Phase 1 fallback default."""

    def __init__(self) -> None:
        self._records: dict[str, VectorRecord] = {}

    async def upsert(self, records: list[VectorRecord]) -> None:
        for record in records:
            self._records[record.id] = record

    async def query(
        self, embedding: list[float], top_k: int, metadata_filter: dict[str, Any] | None = None
    ) -> list[VectorMatch]:
        candidates = self._filtered(metadata_filter)
        scored = [
            VectorMatch(record=r, score=_cosine_similarity(embedding, r.embedding)) for r in candidates
        ]
        scored.sort(key=lambda m: m.score, reverse=True)
        return scored[:top_k]

    async def bm25_query(
        self, text: str, top_k: int, metadata_filter: dict[str, Any] | None = None
    ) -> list[VectorMatch]:
        query_terms = set(text.lower().split())
        candidates = self._filtered(metadata_filter)
        scored = []
        for record in candidates:
            doc_terms = record.text.lower().split()
            overlap = sum(1 for term in doc_terms if term in query_terms)
            if overlap:
                scored.append(VectorMatch(record=record, score=overlap / max(len(doc_terms), 1)))
        scored.sort(key=lambda m: m.score, reverse=True)
        return scored[:top_k]

    async def delete(self, ids: list[str]) -> None:
        for record_id in ids:
            self._records.pop(record_id, None)

    def _filtered(self, metadata_filter: dict[str, Any] | None) -> list[VectorRecord]:
        if not metadata_filter:
            return list(self._records.values())
        return [
            r
            for r in self._records.values()
            if all(r.metadata.get(k) == v for k, v in metadata_filter.items())
        ]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def build_vector_store(kind: str, *, api_key: str | None, index_name: str, dimensions: int) -> VectorStore:
    if kind == "pinecone":
        if not api_key:
            raise ValueError("VECTOR_STORE=pinecone requires PINECONE_API_KEY")
        return PineconeVectorStore(api_key=api_key, index_name=index_name, dimensions=dimensions)
    return InMemoryVectorStore()
