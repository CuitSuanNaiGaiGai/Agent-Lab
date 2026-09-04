import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class FinanceBenchEvidence:
    doc_name: str
    page: int
    text: str


@dataclass(slots=True)
class FinanceBenchSample:
    id: str
    question: str
    answer: str
    doc_name: str
    evidences: list[FinanceBenchEvidence]


def load_financebench(
    dataset_path: str | Path,
) -> list[FinanceBenchSample]:

    path = Path(dataset_path)

    if not path.exists():
        raise FileNotFoundError(
            f"FinanceBench dataset not found: {path}"
        )

    samples: list[FinanceBenchSample] = []

    with path.open(
        "r",
        encoding="utf-8",
    ) as f:

        for line in f:

            line = line.strip()

            if not line:
                continue

            raw = json.loads(line)

            evidences = []

            for evidence in raw["evidence"]:

                # FinanceBench: 0-based
                # Our parser: 1-based
                page = (
                    evidence["evidence_page_num"]
                    + 1
                )

                evidences.append(
                    FinanceBenchEvidence(
                        doc_name=evidence["doc_name"],
                        page=page,
                        text=evidence["evidence_text"],
                    )
                )

            samples.append(
                FinanceBenchSample(
                    id=raw["financebench_id"],
                    question=raw["question"],
                    answer=raw["answer"],
                    doc_name=raw["doc_name"],
                    evidences=evidences,
                )
            )

    return samples