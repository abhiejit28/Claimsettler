import pytest

from claimsettler.mcp_servers.kma.ingestion.store import InMemoryVectorStore, VectorRecord


@pytest.mark.asyncio
async def test_upsert_and_query_returns_closest_match():
    store = InMemoryVectorStore()
    await store.upsert(
        [
            VectorRecord(id="a", embedding=[1.0, 0.0], text="alpha", metadata={"document_type": "claim"}),
            VectorRecord(id="b", embedding=[0.0, 1.0], text="beta", metadata={"document_type": "claim"}),
        ]
    )
    matches = await store.query([1.0, 0.0], top_k=1)
    assert matches[0].record.id == "a"


@pytest.mark.asyncio
async def test_metadata_filter_scopes_results():
    store = InMemoryVectorStore()
    await store.upsert(
        [
            VectorRecord(id="a", embedding=[1.0, 0.0], text="alpha", metadata={"policy_id": "P1"}),
            VectorRecord(id="b", embedding=[1.0, 0.0], text="beta", metadata={"policy_id": "P2"}),
        ]
    )
    matches = await store.query([1.0, 0.0], top_k=5, metadata_filter={"policy_id": "P2"})
    assert len(matches) == 1
    assert matches[0].record.id == "b"


@pytest.mark.asyncio
async def test_bm25_query_matches_lexical_overlap():
    store = InMemoryVectorStore()
    await store.upsert(
        [VectorRecord(id="a", embedding=[0.0], text="collision damage claim auto", metadata={})]
    )
    matches = await store.bm25_query("collision claim", top_k=5)
    assert len(matches) == 1


@pytest.mark.asyncio
async def test_delete_removes_record():
    store = InMemoryVectorStore()
    await store.upsert([VectorRecord(id="a", embedding=[1.0], text="x", metadata={})])
    await store.delete(["a"])
    matches = await store.query([1.0], top_k=5)
    assert matches == []
