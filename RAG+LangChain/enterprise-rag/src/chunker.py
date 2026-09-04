from dataclasses import dataclass

from src.models import Document


@dataclass(slots=True)
class ChunkConfig:
    chunk_size: int = 500
    chunk_overlap: int = 100

    def __post_init__(self) -> None:
        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be greater than 0")

        if self.chunk_overlap < 0:
            raise ValueError("chunk_overlap cannot be negative")

        if self.chunk_overlap >= self.chunk_size:
            raise ValueError(
                "chunk_overlap must be smaller than chunk_size"
            )


def chunk_document(
    document: Document,
    config: ChunkConfig,
) -> list[Document]:

    text = document.content

    step = config.chunk_size - config.chunk_overlap

    chunks: list[Document] = []

    chunk_index = 0
    start = 0

    while start < len(text):

        end = min(
            start + config.chunk_size,
            len(text),
        )

        chunk_text = text[start:end].strip()

        if chunk_text:

            chunk_id = (
                f"{document.id}"
                f":chunk:{chunk_index}"
                f":{start}-{end}"
            )

            chunk = Document(
                id=chunk_id,
                content=chunk_text,
                metadata={
                    **document.metadata,
                    "parent_document_id": document.id,
                    "chunk_index": chunk_index,
                    "chunk_start": start,
                    "chunk_end": end,
                    "chunk_size": len(chunk_text),
                },
            )

            chunks.append(chunk)

            chunk_index += 1

        start += step

    return chunks