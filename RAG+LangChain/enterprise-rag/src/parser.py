import hashlib
from pathlib import Path

from pypdf import PdfReader

from src.models import Document


def calculate_file_hash(file_path: Path) -> str:
    """计算文件 SHA256，用于稳定识别文档。"""

    sha256 = hashlib.sha256()

    with file_path.open("rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)

    return sha256.hexdigest()


def build_document_id(
    file_hash: str,
    page_number: int,
) -> str:
    """根据文件内容和页码生成稳定 Document ID。"""

    raw_id = f"{file_hash}:page:{page_number}"

    return hashlib.sha256(
        raw_id.encode("utf-8")
    ).hexdigest()


def parse_pdf(file_path: str | Path) -> list[Document]:

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"PDF file not found: {path}"
        )

    if path.suffix.lower() != ".pdf":
        raise ValueError(
            f"Expected PDF file, got: {path.suffix}"
        )

    file_hash = calculate_file_hash(path)

    reader = PdfReader(path)

    documents: list[Document] = []

    for page_number, page in enumerate(
        reader.pages,
        start=1,
    ):
        text = page.extract_text()

        if text is None:
            continue

        text = text.strip()

        if not text:
            continue

        document_id = build_document_id(
            file_hash=file_hash,
            page_number=page_number,
        )

        document = Document(
            id=document_id,
            content=text,
            metadata={
                "source": path.name,
                "file_path": str(path),
                "page": page_number,
                "document_id": document_id,
                "file_hash": file_hash,
                "content_length": len(text),
                "document_type": "pdf",
            },
        )

        documents.append(document)

    return documents