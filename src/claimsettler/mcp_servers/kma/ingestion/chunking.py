"""Semantic chunking: 500-700 tokens with 100 token overlap.

Phase 1 uses a whitespace-token approximation (no extra tokenizer
dependency) rather than a model-specific tokenizer — close enough for
chunk-sizing purposes and avoids coupling chunking to one embedding
provider's tokenizer.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    text: str
    index: int


def chunk_text(text: str, *, chunk_size_tokens: int = 600, overlap_tokens: int = 100) -> list[Chunk]:
    words = text.split()
    if not words:
        return []

    step = max(chunk_size_tokens - overlap_tokens, 1)
    chunks: list[Chunk] = []
    index = 0
    start = 0
    while start < len(words):
        window = words[start : start + chunk_size_tokens]
        chunks.append(Chunk(text=" ".join(window), index=index))
        index += 1
        if start + chunk_size_tokens >= len(words):
            break
        start += step
    return chunks
