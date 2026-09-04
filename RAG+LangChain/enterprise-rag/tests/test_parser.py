from pathlib import Path

from src.parser import (
    build_document_id,
    calculate_file_hash,
    parse_pdf,
)


def test_file_hash_is_deterministic():
    path = Path("data/raw/DeepSeekv2.pdf")

    hash_1 = calculate_file_hash(path)
    hash_2 = calculate_file_hash(path)

    assert hash_1 == hash_2


def test_document_id_is_deterministic():

    document_id_1 = build_document_id(
        "abc123",
        1,
    )

    document_id_2 = build_document_id(
        "abc123",
        1,
    )

    assert document_id_1 == document_id_2


def test_different_pages_have_different_ids():

    document_id_1 = build_document_id(
        "abc123",
        1,
    )

    document_id_2 = build_document_id(
        "abc123",
        2,
    )

    assert document_id_1 != document_id_2