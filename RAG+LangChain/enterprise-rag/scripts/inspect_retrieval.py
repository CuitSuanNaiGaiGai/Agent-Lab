from pathlib import Path

from src.chunker import (
    ChunkConfig,
    chunk_document,
)
from src.embedding import EmbeddingModel
from src.parser import parse_pdf
from src.retriever import DenseRetriever


DATA_DIR = Path("data/raw")


def load_chunks():

    config = ChunkConfig(
        chunk_size=500,
        chunk_overlap=100,
    )

    all_chunks = []

    for pdf_path in DATA_DIR.glob("*.pdf"):

        pages = parse_pdf(pdf_path)

        for page in pages:

            chunks = chunk_document(
                page,
                config,
            )

            all_chunks.extend(chunks)

    return all_chunks


def main() -> None:

    print("Loading documents...")

    chunks = load_chunks()

    print(
        f"Total chunks: {len(chunks)}"
    )

    print("Loading embedding model...")

    embedding_model = EmbeddingModel()

    print("Encoding documents...")

    document_embeddings = (
        embedding_model.encode_documents(
            [
                chunk.content
                for chunk in chunks
            ]
        )
    )

    print(
        "Embedding shape:",
        document_embeddings.shape,
    )

    retriever = DenseRetriever(
        documents=chunks,
        embeddings=document_embeddings,
    )

    while True:

        query = input(
            "\nQuery (type 'exit' to quit): "
        ).strip()

        if query.lower() in {
            "exit",
            "quit",
        }:
            break

        query_embedding = (
            embedding_model.encode_query(query)
        )

        results = retriever.search(
            query_embedding=query_embedding,
            top_k=5,
        )

        print()

        for rank, result in enumerate(
            results,
            start=1,
        ):

            document = result.document

            print("=" * 80)

            print(
                f"Rank: {rank}"
            )

            print(
                f"Score: {result.score:.4f}"
            )

            print(
                f"Source: "
                f"{document.metadata['source']}"
            )

            print(
                f"Page: "
                f"{document.metadata['page']}"
            )

            print(
                f"Chunk: "
                f"{document.metadata['chunk_index']}"
            )

            print()

            print(
                document.content[:1000]
            )


if __name__ == "__main__":
    main()