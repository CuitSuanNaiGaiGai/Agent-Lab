from pathlib import Path

from src.parser import parse_pdf


DATA_DIR = Path("data/raw")


def main() -> None:

    pdf_files = list(DATA_DIR.glob("*.pdf"))

    if not pdf_files:
        print("No PDF files found.")
        return

    for pdf_path in pdf_files:

        print("=" * 80)
        print(f"PDF: {pdf_path.name}")

        documents = parse_pdf(pdf_path)

        print(f"Parsed pages: {len(documents)}")

        total_chars = sum(
            len(doc.content)
            for doc in documents
        )

        print(f"Total characters: {total_chars}")

        for document in documents[:3]:

            print("-" * 80)

            print(
                f"Page: {document.metadata['page']}"
            )

            print(
                f"ID: {document.id[:16]}..."
            )

            print(
                f"Length: {document.metadata['content_length']}"
            )

            print()

            print(document.content[:500])


if __name__ == "__main__":
    main()