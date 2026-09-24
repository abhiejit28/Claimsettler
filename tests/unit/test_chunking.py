from claimsettler.mcp_servers.kma.ingestion.chunking import chunk_text


def test_empty_text_produces_no_chunks():
    assert chunk_text("") == []


def test_short_text_produces_one_chunk():
    chunks = chunk_text("hello world", chunk_size_tokens=600, overlap_tokens=100)
    assert len(chunks) == 1
    assert chunks[0].text == "hello world"


def test_long_text_is_split_with_overlap():
    words = [f"word{i}" for i in range(1500)]
    text = " ".join(words)
    chunks = chunk_text(text, chunk_size_tokens=600, overlap_tokens=100)
    assert len(chunks) > 1
    # consecutive chunks overlap
    first_words = chunks[0].text.split()
    second_words = chunks[1].text.split()
    assert first_words[-1] in second_words[: len(second_words) // 2 + 1] or set(first_words[-50:]) & set(
        second_words[:50]
    )
