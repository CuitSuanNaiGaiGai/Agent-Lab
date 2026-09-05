from src.tools.papernotes import (
    search_papernotes_raw,
    tokenize_query,
)


def main() -> None:
    query = "LLM Agent Memory"

    print(
        "Query tokens:",
        tokenize_query(query),
    )
    print()

    results = search_papernotes_raw(
        query=query,
        max_results=5,
    )

    print(
        f"Found {len(results)} results\n"
    )

    for index, result in enumerate(
        results,
        start=1,
    ):
        print(f"=== Result {index} ===")

        print("Title:")
        print(result["title"])

        print(
            "Matched:",
            result["matched_terms"],
        )

        print(
            "Unmatched:",
            result["unmatched_terms"],
        )

        print(
            "Site Missing:",
            result["site_missing_terms"],
        )

        print("URL:")
        print(result["url"])

        print()


if __name__ == "__main__":
    main()