import argparse
import json
from dataclasses import asdict
from pathlib import Path

from src.benchmarks.financebench import (
    FinanceBenchSample,
    load_financebench,
)
from src.chunker import (
    ChunkConfig,
    chunk_document,
)
from src.embedding import EmbeddingModel
from src.parser import parse_pdf
from src.retriever import DenseRetriever


BENCHMARK_DIR = Path(
    "data/benchmarks/financebench"
)

DATASET_PATH = (
    BENCHMARK_DIR
    / "financebench_open_source.jsonl"
)

PDF_DIR = BENCHMARK_DIR / "pdfs"

EXPERIMENT_DIR = Path("experiments")


def build_retriever_for_document(
    doc_name: str,
    embedding_model: EmbeddingModel,
    chunk_config: ChunkConfig,
) -> DenseRetriever:
    """
    对一个 FinanceBench PDF：
    parse -> chunk -> embedding -> retriever
    """

    pdf_path = PDF_DIR / f"{doc_name}.pdf"

    if not pdf_path.exists():
        raise FileNotFoundError(
            f"PDF not found: {pdf_path}"
        )

    pages = parse_pdf(pdf_path)

    chunks = []

    for page in pages:
        chunks.extend(
            chunk_document(
                page,
                chunk_config,
            )
        )

    embeddings = (
        embedding_model.encode_documents(
            [
                chunk.content
                for chunk in chunks
            ]
        )
    )

    return DenseRetriever(
        documents=chunks,
        embeddings=embeddings,
    )


def get_gold_pages(
    sample: FinanceBenchSample,
) -> set[int]:

    return {
        evidence.page
        for evidence in sample.evidences
    }


def get_retrieved_pages(
    results,
    top_k: int,
) -> set[int]:

    return {
        result.document.metadata["page"]
        for result in results[:top_k]
    }


def hit_at_k(
    results,
    gold_pages: set[int],
    k: int,
) -> int:

    retrieved_pages = get_retrieved_pages(
        results,
        k,
    )

    return int(
        bool(
            retrieved_pages
            & gold_pages
        )
    )


def evidence_recall_at_k(
    results,
    gold_pages: set[int],
    k: int,
) -> float:

    if not gold_pages:
        return 0.0

    retrieved_pages = get_retrieved_pages(
        results,
        k,
    )

    matched_pages = (
        retrieved_pages
        & gold_pages
    )

    return (
        len(matched_pages)
        / len(gold_pages)
    )


def all_evidence_at_k(
    results,
    gold_pages: set[int],
    k: int,
) -> int:

    retrieved_pages = get_retrieved_pages(
        results,
        k,
    )

    return int(
        gold_pages.issubset(
            retrieved_pages
        )
    )


def reciprocal_rank(
    results,
    gold_pages: set[int],
) -> float:

    for rank, result in enumerate(
        results,
        start=1,
    ):

        page = (
            result
            .document
            .metadata["page"]
        )

        if page in gold_pages:
            return 1.0 / rank

    return 0.0


def parse_args():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only evaluate first N questions.",
    )

    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
    )

    return parser.parse_args()


def main():

    args = parse_args()

    samples = load_financebench(
        DATASET_PATH
    )

    if args.limit is not None:
        samples = samples[:args.limit]

    print(
        f"Questions: {len(samples)}"
    )

    embedding_model = EmbeddingModel()

    chunk_config = ChunkConfig(
        chunk_size=500,
        chunk_overlap=100,
    )

    # 同一个 PDF 可能对应多个问题。
    # 避免重复 parse / chunk / embedding。
    retriever_cache = {}

    metrics = {
        "hit@1": 0.0,
        "hit@3": 0.0,
        "hit@5": 0.0,
        "hit@10": 0.0,
        "mrr": 0.0,
        "evidence_recall@5": 0.0,
        "evidence_recall@10": 0.0,
        "all_evidence@5": 0.0,
        "all_evidence@10": 0.0,
    }

    evaluation_results = []

    for index, sample in enumerate(
        samples,
        start=1,
    ):

        print()
        print("=" * 80)

        print(
            f"[{index}/{len(samples)}] "
            f"{sample.id}"
        )

        print(
            f"Document: {sample.doc_name}"
        )

        print(
            f"Question: {sample.question}"
        )

        # --------------------------------
        # Retriever Cache
        # --------------------------------

        if sample.doc_name not in retriever_cache:

            print(
                f"Building index: "
                f"{sample.doc_name}"
            )

            retriever_cache[
                sample.doc_name
            ] = build_retriever_for_document(
                doc_name=sample.doc_name,
                embedding_model=embedding_model,
                chunk_config=chunk_config,
            )

        retriever = retriever_cache[
            sample.doc_name
        ]

        # --------------------------------
        # Query
        # --------------------------------

        query_embedding = (
            embedding_model.encode_query(
                sample.question
            )
        )

        results = retriever.search(
            query_embedding=query_embedding,
            top_k=args.top_k,
        )

        gold_pages = get_gold_pages(
            sample
        )

        # --------------------------------
        # Metrics
        # --------------------------------

        sample_metrics = {
            "hit@1": hit_at_k(
                results,
                gold_pages,
                1,
            ),
            "hit@3": hit_at_k(
                results,
                gold_pages,
                3,
            ),
            "hit@5": hit_at_k(
                results,
                gold_pages,
                5,
            ),
            "hit@10": hit_at_k(
                results,
                gold_pages,
                10,
            ),
            "mrr": reciprocal_rank(
                results,
                gold_pages,
            ),
            "evidence_recall@5":
                evidence_recall_at_k(
                    results,
                    gold_pages,
                    5,
                ),
            "evidence_recall@10":
                evidence_recall_at_k(
                    results,
                    gold_pages,
                    10,
                ),
            "all_evidence@5":
                all_evidence_at_k(
                    results,
                    gold_pages,
                    5,
                ),
            "all_evidence@10":
                all_evidence_at_k(
                    results,
                    gold_pages,
                    10,
                ),
        }

        for key, value in (
            sample_metrics.items()
        ):
            metrics[key] += value

        # --------------------------------
        # Print Top Results
        # --------------------------------

        print(
            f"Gold pages: "
            f"{sorted(gold_pages)}"
        )

        for rank, result in enumerate(
            results[:5],
            start=1,
        ):

            page = (
                result
                .document
                .metadata["page"]
            )

            mark = (
                "✅"
                if page in gold_pages
                else "❌"
            )

            print(
                f"{rank}. {mark} "
                f"score={result.score:.4f} "
                f"page={page}"
            )

        evaluation_results.append(
            {
                "id": sample.id,
                "document": sample.doc_name,
                "question": sample.question,
                "gold_pages": sorted(
                    gold_pages
                ),
                "metrics": sample_metrics,
                "top_results": [
                    {
                        "rank": rank,
                        "page": (
                            result
                            .document
                            .metadata["page"]
                        ),
                        "score": result.score,
                        "content": (
                            result
                            .document
                            .content[:500]
                        ),
                    }
                    for rank, result
                    in enumerate(
                        results,
                        start=1,
                    )
                ],
            }
        )

    # --------------------------------
    # Final Metrics
    # --------------------------------

    total = len(samples)

    final_metrics = {
        key: value / total
        for key, value
        in metrics.items()
    }

    print()
    print("=" * 80)
    print(
        "FinanceBench Dense Retrieval Baseline"
    )
    print("=" * 80)

    print(
        f"Questions          : {total}"
    )

    print(
        f"Documents indexed  : "
        f"{len(retriever_cache)}"
    )

    print()

    for key, value in (
        final_metrics.items()
    ):
        print(
            f"{key:<20}: "
            f"{value:.4f}"
        )

    # --------------------------------
    # Save experiment
    # --------------------------------

    EXPERIMENT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        EXPERIMENT_DIR
        / "financebench_dense_baseline.json"
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            {
                "config": {
                    "embedding_model":
                        embedding_model.model_name,
                    "chunk_size":
                        chunk_config.chunk_size,
                    "chunk_overlap":
                        chunk_config.chunk_overlap,
                    "retrieval":
                        "dense_bruteforce_cosine",
                },
                "metrics":
                    final_metrics,
                "samples":
                    evaluation_results,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print(
        f"Saved results to: "
        f"{output_path}"
    )


if __name__ == "__main__":
    main()