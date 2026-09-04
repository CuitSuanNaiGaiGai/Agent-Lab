import numpy as np

from src.models import Document
from src.retriever import DenseRetriever


def create_document(
    doc_id: str,
    content: str,
) -> Document:

    return Document(
        id=doc_id,
        content=content,
        metadata={},
    )


def test_dense_retriever_returns_most_similar():

    documents = [
        create_document(
            "1",
            "document one",
        ),
        create_document(
            "2",
            "document two",
        ),
        create_document(
            "3",
            "document three",
        ),
    ]

    embeddings = np.array(
        [
            [1.0, 0.0],
            [0.0, 1.0],
            [0.7, 0.7],
        ],
        dtype=np.float32,
    )

    query_embedding = np.array(
        [1.0, 0.0],
        dtype=np.float32,
    )

    retriever = DenseRetriever(
        documents=documents,
        embeddings=embeddings,
    )

    results = retriever.search(
        query_embedding,
        top_k=2,
    )

    assert len(results) == 2

    assert (
        results[0].document.id
        == "1"
    )


def test_top_k_does_not_exceed_documents():

    documents = [
        create_document(
            "1",
            "document one",
        )
    ]

    embeddings = np.array(
        [
            [1.0, 0.0],
        ],
        dtype=np.float32,
    )

    retriever = DenseRetriever(
        documents,
        embeddings,
    )

    query_embedding = np.array(
        [1.0, 0.0],
        dtype=np.float32,
    )

    results = retriever.search(
        query_embedding,
        top_k=10,
    )

    assert len(results) == 1