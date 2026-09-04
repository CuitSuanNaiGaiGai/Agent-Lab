import json
from pathlib import Path

from src.chunker import ChunkConfig, chunk_document
from src.embedding import EmbeddingModel
from src.parser import parse_pdf
from src.retriever import DenseRetriever


DATA_DIR = Path("data/raw")
EVAL_PATH = Path("data/eval/retrieval.json")


def load_chunks():
    config = ChunkConfig(
        chunk_size=500,
        chunk_overlap=100,
    )

    chunks = []

    for pdf_path in DATA_DIR.glob("*.pdf"):
        pages = parse_pdf(pdf_path)

        for page in pages:
            chunks.extend(
                chunk_document(page, config)
            )

    return chunks


def load_eval_dataset():
    with EVAL_PATH.open(
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


def is_relevant(document, relevant_sources):
    source = document.metadata["source"]
    page = document.metadata["page"]

    for target in relevant_sources:
        if (
            source == target["source"]
            and page in target["pages"]
        ):
            return True

    return False


def reciprocal_rank(
    results,
    relevant_sources,
):
    for rank, result in enumerate(
        results,
        start=1,
    ):
        if is_relevant(
            result.document,
            relevant_sources,
        ):
            return 1.0 / rank

    return 0.0


def main():

    print("Loading chunks...")
    chunks = load_chunks()

    print(f"Chunks: {len(chunks)}")

    model = EmbeddingModel()

    embeddings = model.encode_documents(
        [chunk.content for chunk in chunks]
    )

    retriever = DenseRetriever(
        documents=chunks,
        embeddings=embeddings,
    )

    dataset = load_eval_dataset()

    hit_1 = 0
    hit_3 = 0
    hit_5 = 0
    rr_sum = 0.0

    for item in dataset:

        query_embedding = model.encode_query(
            item["query"]
        )

        results = retriever.search(
            query_embedding,
            top_k=5,
        )

        relevances = [
            is_relevant(
                result.document,
                item["relevant_sources"],
            )
            for result in results
        ]

        hit_1 += int(any(relevances[:1]))
        hit_3 += int(any(relevances[:3]))
        hit_5 += int(any(relevances[:5]))

        rr = reciprocal_rank(
            results,
            item["relevant_sources"],
        )

        rr_sum += rr

        print("=" * 80)
        print(item["query"])

        for rank, result in enumerate(
            results,
            start=1,
        ):
            mark = (
                "✅"
                if relevances[rank - 1]
                else "❌"
            )

            print(
                f"{rank}. {mark} "
                f"{result.score:.4f} "
                f"{result.document.metadata['source']} "
                f"page={result.document.metadata['page']}"
            )

    total = len(dataset)

    print("\n" + "=" * 80)
    print("Dense Retrieval Baseline")
    print("=" * 80)

    print(f"Queries : {total}")
    print(f"Hit@1   : {hit_1 / total:.3f}")
    print(f"Hit@3   : {hit_3 / total:.3f}")
    print(f"Hit@5   : {hit_5 / total:.3f}")
    print(f"MRR     : {rr_sum / total:.3f}")


if __name__ == "__main__":
    main()