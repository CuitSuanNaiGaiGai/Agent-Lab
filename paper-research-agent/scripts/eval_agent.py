import json
from datetime import datetime
from pathlib import Path

from src.service import ResearchService


CASES_PATH = Path("evals/cases.json")
RESULTS_DIR = Path("evals/results")


def load_cases() -> list[dict]:
    with CASES_PATH.open(
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


def main() -> None:
    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    cases = load_cases()
    service = ResearchService()

    results = []

    for index, case in enumerate(
        cases,
        start=1,
    ):
        print(
            f"\n[{index}/{len(cases)}] "
            f"{case['id']}"
        )

        print(
            f"Query: {case['query']}"
        )

        try:
            result = service.research(
                case["query"]
            )

            results.append(
                {
                    **case,
                    "success": True,
                    "answer": result.answer,
                }
            )

            print("Status: success")

        except Exception as exc:
            results.append(
                {
                    **case,
                    "success": False,
                    "error": str(exc),
                }
            )

            print(
                f"Status: failed - {exc}"
            )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    output_path = (
        RESULTS_DIR
        / f"eval_{timestamp}.json"
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            results,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(
        f"\nEvaluation saved to: "
        f"{output_path}"
    )


if __name__ == "__main__":
    main()