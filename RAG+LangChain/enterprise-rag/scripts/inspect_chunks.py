from pathlib import Path

from src.chunker import (
    ChunkConfig,
    chunk_document,
)
from src.parser import parse_pdf


DATA_DIR = Path("data/raw")


def main() -> None:

    pdf_files = list(DATA_DIR.glob("*.pdf"))

    if not pdf_files:
        print("No PDF files found.")
        return

    config = ChunkConfig(
        chunk_size=500,
        chunk_overlap=100,
    )

    pdf_path = pdf_files[0]

    print(f"PDF: {pdf_path.name}")

    pages = parse_pdf(pdf_path)

    all_chunks = []

    for page in pages:
        chunks = chunk_document(
            page,
            config,
        )

        all_chunks.extend(chunks)

    print(f"Pages: {len(pages)}")
    print(f"Chunks: {len(all_chunks)}")

    for chunk in all_chunks[:10]:

        print("=" * 80)

        print(
            f"Page: {chunk.metadata['page']} | "
            f"Chunk: {chunk.metadata['chunk_index']} | "
            f"Range: "
            f"{chunk.metadata['chunk_start']}"
            f"-"
            f"{chunk.metadata['chunk_end']}"
        )

        print()

        print(chunk.content)


if __name__ == "__main__":
    main()