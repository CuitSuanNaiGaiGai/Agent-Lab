import json
from datetime import datetime
from pathlib import Path

from src.service import ResearchService
from src.evaluation import (
    calculate_tool_metrics,
    calculate_selection_metrics,
    calculate_quality_metrics,
)

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

            # -------------------------
            # Tool Metrics
            # -------------------------

            metrics = calculate_tool_metrics(
                result.trace
            )

            # -------------------------
            # Selection Metrics
            # -------------------------

            selection_metrics = (
                calculate_selection_metrics(
                    searched_papers=(
                        metrics.searched_papers
                    ),
                    read_papers=(
                        metrics.read_papers
                    ),
                )
            )

            # -------------------------
            # Quality Metrics
            # -------------------------

            quality_metrics = (
                calculate_quality_metrics(
                    case=case,
                    read_papers=(
                        metrics.read_papers
                    ),
                )
            )

            results.append(
                {
                    **case,
                    "success": True,
                    "answer": result.answer,
                    "trace": result.trace,

                    "tool_metrics": {
                        "search_attempt_count": (
                            metrics.search_attempt_count
                        ),
                        "search_success_count": (
                            metrics.search_success_count
                        ),
                        "search_blocked_count": (
                            metrics.search_blocked_count
                        ),
                        "read_attempt_count": (
                            metrics.read_attempt_count
                        ),
                        "read_success_count": (
                            metrics.read_success_count
                        ),
                        "read_failure_count": (
                            metrics.read_failure_count
                        ),
                        "searched_papers": (
                            metrics.searched_papers
                        ),
                        "read_papers": (
                            metrics.read_papers
                        ),
                        "read_failures": (
                            metrics.read_failures
                        ),
                    },

                    "selection_metrics": {
                        "searched_unique_count": (
                            selection_metrics.searched_unique_count
                        ),
                        "read_unique_count": (
                            selection_metrics.read_unique_count
                        ),
                        "selected_from_search_count": (
                            selection_metrics.selected_from_search_count
                        ),
                        "selection_rate": round(
                            selection_metrics.selection_rate,
                            3,
                        ),
                        "unread_papers": (
                            selection_metrics.unread_papers
                        ),
                    },

                    "quality_metrics": {
                        "must_read_count": (
                            quality_metrics.must_read_count
                        ),
                        "must_read_hit_count": (
                            quality_metrics.must_read_hit_count
                        ),
                        "must_read_recall": round(
                            quality_metrics.must_read_recall,
                            3,
                        ),
                        "min_read_count": (
                            quality_metrics.min_read_count
                        ),
                        "read_count_pass": (
                            quality_metrics.read_count_pass
                        ),
                    },
                }
            )

            print("Status: success")

            print(
                "Metrics: "
                f"search_attempt="
                f"{metrics.search_attempt_count}, "
                f"search_success="
                f"{metrics.search_success_count}, "
                f"search_blocked="
                f"{metrics.search_blocked_count}, "
                f"read_attempt="
                f"{metrics.read_attempt_count}, "
                f"read_success="
                f"{metrics.read_success_count}, "
                f"read_failure="
                f"{metrics.read_failure_count}"
            )

            print(
                "Selection: "
                f"searched_unique="
                f"{selection_metrics.searched_unique_count}, "
                f"read_unique="
                f"{selection_metrics.read_unique_count}, "
                f"selection_rate="
                f"{selection_metrics.selection_rate:.2f}"
            )

            print(
                "Quality: "
                f"must_read_recall="
                f"{quality_metrics.must_read_recall:.2f}, "
                f"read_count_pass="
                f"{quality_metrics.read_count_pass}"
            )

        except Exception as exc:
            results.append(
                {
                    **case,
                    "success": False,
                    "answer": "",
                    "trace": [],

                    "tool_metrics": {
                        "search_attempt_count": 0,
                        "search_success_count": 0,
                        "search_blocked_count": 0,
                        "read_attempt_count": 0,
                        "read_success_count": 0,
                        "read_failure_count": 0,
                        "searched_papers": [],
                        "read_papers": [],
                        "read_failures": [],
                    },

                    "selection_metrics": {
                        "searched_unique_count": 0,
                        "read_unique_count": 0,
                        "selected_from_search_count": 0,
                        "selection_rate": 0.0,
                        "unread_papers": [],
                    },

                    "quality_metrics": {
                        "must_read_count": 0,
                        "must_read_hit_count": 0,
                        "must_read_recall": 0.0,
                        "min_read_count": 0,
                        "read_count_pass": False,
                    },

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