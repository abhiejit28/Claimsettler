"""Reranker Protocol + implementations. Config-selected (RERANKER=
bge_reranker|fake)."""

from __future__ import annotations

from typing import Protocol


class Reranker(Protocol):
    async def rerank(self, query: str, candidates: list[str], top_k: int) -> list[tuple[int, float]]:
        """Returns (original_index, score), sorted desc by score."""
        ...


class BGERerankerProvider:
    """Real implementation — self-hosted cross-encoder, pairs with BGE-M3.
    Not exercised by default Phase 1 tests/dev (model download required)."""

    model_name = "BAAI/bge-reranker-v2-m3"

    def __init__(self) -> None:
        from FlagEmbedding import FlagReranker

        self._model = FlagReranker(self.model_name, use_fp16=True)

    async def rerank(self, query: str, candidates: list[str], top_k: int) -> list[tuple[int, float]]:
        pairs = [[query, c] for c in candidates]
        scores = self._model.compute_score(pairs)
        ranked = sorted(enumerate(scores), key=lambda pair: pair[1], reverse=True)
        return ranked[:top_k]


class FakeReranker:
    """Pass-through: keeps incoming order (assumed already similarity-sorted
    by the vector store), truncated to top_k. No model download."""

    async def rerank(self, query: str, candidates: list[str], top_k: int) -> list[tuple[int, float]]:
        return [(i, 1.0 - (i / max(len(candidates), 1))) for i in range(min(top_k, len(candidates)))]


def build_reranker(kind: str) -> Reranker:
    if kind == "bge_reranker":
        return BGERerankerProvider()
    return FakeReranker()
