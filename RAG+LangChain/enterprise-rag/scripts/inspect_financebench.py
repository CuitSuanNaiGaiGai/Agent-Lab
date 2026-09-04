from pathlib import Path

from src.benchmarks.financebench import (
    load_financebench,
)


BENCHMARK_DIR = Path(
    "data/benchmarks/financebench"
)

DATASET_PATH = (
    BENCHMARK_DIR
    / "financebench_open_source.jsonl"
)

PDF_DIR = BENCHMARK_DIR / "pdfs"


def main() -> None:

    samples = load_financebench(
        DATASET_PATH
    )

    print(
        f"Total questions: {len(samples)}"
    )

    doc_names = {
        sample.doc_name
        for sample in samples
    }

    print(
        f"Unique documents: {len(doc_names)}"
    )

    missing_pdfs = []

    for doc_name in sorted(doc_names):

        pdf_path = (
            PDF_DIR
            / f"{doc_name}.pdf"
        )

        if not pdf_path.exists():
            missing_pdfs.append(
                pdf_path.name
            )

    print(
        f"Missing PDFs: {len(missing_pdfs)}"
    )

    if missing_pdfs:

        for name in missing_pdfs:
            print(
                f"  - {name}"
            )

    print("\nFirst 3 samples:\n")

    for sample in samples[:3]:

        print("=" * 80)

        print(
            f"ID: {sample.id}"
        )

        print(
            f"Document: {sample.doc_name}"
        )

        print(
            f"Question: {sample.question}"
        )

        print(
            f"Answer: {sample.answer}"
        )

        print("Gold Evidence:")

        for evidence in sample.evidences:

            print(
                f"  page={evidence.page}"
            )

            print(
                f"  {evidence.text[:300]}"
            )


if __name__ == "__main__":
    main()