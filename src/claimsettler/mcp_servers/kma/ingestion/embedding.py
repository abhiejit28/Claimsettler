"""EmbeddingProvider Protocol + implementations. Config-selected
(EMBEDDING_PROVIDER=bge_m3|fake) so swapping is a config change, not a
rewrite — see core/config.py and docs/architecturePlan.md.
"""

from __future__ import annotations

import hashlib
from typing import Protocol


class EmbeddingProvider(Protocol):
    model_name: str
    dimensions: int

    async def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    async def embed_query(self, text: str) -> list[float]: ...


class BGEM3EmbeddingProvider:
    """Real implementation — self-hosted via FlagEmbedding (`pip install
    claimsettler[ml]`). Not exercised by default Phase 1 tests/dev, which
    use FakeEmbeddingProvider, since it requires a ~2GB model download."""

    model_name = "BAAI/bge-m3"
    dimensions = 1024

    def __init__(self) -> None:
        from FlagEmbedding import BGEM3FlagModel

        self._model = BGEM3FlagModel(self.model_name, use_fp16=True)

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        output = self._model.encode(texts, return_dense=True)
        return [vec.tolist() for vec in output["dense_vecs"]]

    async def embed_query(self, text: str) -> list[float]:
        result = await self.embed_documents([text])
        return result[0]


class FakeEmbeddingProvider:
    """Deterministic, dependency-free embedding for local dev/test — hashes
    text into a fixed-size vector. Not semantically meaningful; good enough
    to exercise chunking/store/retrieval plumbing without a model download
    or GPU."""

    model_name = "fake-hash-embedding"
    dimensions = 64

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    async def embed_query(self, text: str) -> list[float]:
        return self._embed_one(text)

    def _embed_one(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        # Expand the 32-byte digest into `dimensions` floats in [-1, 1].
        values = (digest * ((self.dimensions // len(digest)) + 1))[: self.dimensions]
        return [(b - 127.5) / 127.5 for b in values]


def build_embedding_provider(kind: str) -> EmbeddingProvider:
    if kind == "bge_m3":
        return BGEM3EmbeddingProvider()
    return FakeEmbeddingProvider()
