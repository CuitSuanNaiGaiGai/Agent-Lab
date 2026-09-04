import pytest

from src.chunker import (
    ChunkConfig,
    chunk_document,
)
from src.models import Document


def create_document(content: str) -> Document:
    return Document(
        id="doc-1",
        content=content,
        metadata={
            "source": "test.pdf",
            "page": 1,
        },
    )


def test_chunk_without_overlap():

    document = create_document(
        "abcdefghij"
    )

    config = ChunkConfig(
        chunk_size=5,
        chunk_overlap=0,
    )

    chunks = chunk_document(
        document,
        config,
    )

    assert len(chunks) == 2

    assert chunks[0].content == "abcde"
    assert chunks[1].content == "fghij"


def test_chunk_with_overlap():

    document = create_document(
        "abcdefghij"
    )

    config = ChunkConfig(
        chunk_size=6,
        chunk_overlap=2,
    )

    chunks = chunk_document(
        document,
        config,
    )

    assert chunks[0].content == "abcdef"
    assert chunks[1].content == "efghij"


def test_chunk_metadata():

    document = create_document(
        "abcdefghij"
    )

    config = ChunkConfig(
        chunk_size=5,
        chunk_overlap=0,
    )

    chunks = chunk_document(
        document,
        config,
    )

    assert (
        chunks[0]
        .metadata["parent_document_id"]
        == "doc-1"
    )

    assert chunks[0].metadata["chunk_index"] == 0


def test_invalid_chunk_config():

    with pytest.raises(ValueError):
        ChunkConfig(
            chunk_size=500,
            chunk_overlap=500,
        )