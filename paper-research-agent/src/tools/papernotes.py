import json
import re
from langchain.tools import tool
from playwright.sync_api import sync_playwright


PAPERNOTES_URL = "https://papernotes.org/"

def tokenize_query(
    query: str,
) -> list[str]:
    """
    Convert a search query into normalized English keywords.
    """

    tokens = re.findall(
        r"[a-zA-Z0-9]+",
        query.lower(),
    )

    stopwords = {
        "the",
        "a",
        "an",
        "of",
        "for",
        "and",
        "or",
        "in",
        "on",
        "with",
    }

    return [
        token
        for token in tokens
        if token not in stopwords
    ]


def calculate_relevance(
    query: str,
    title: str,
    keywords: str,
) -> tuple[float, list[str]]:
    query_terms = tokenize_query(query)
    print(
        "[DEBUG relevance]",
        query,
        "->",
        query_terms,
    )
    if not query_terms:
        return 0.0, []

    title_text = title.lower()
    keywords_text = keywords.lower()

    matched_terms: list[str] = []

    score = 0.0

    for term in query_terms:
        matched = False

        if term in title_text:
            # 标题命中权重大
            score += 2.0
            matched = True

        elif term in keywords_text:
            # keywords 命中权重较小
            score += 1.0
            matched = True

        if matched:
            matched_terms.append(term)

    # 每个 query term 最高可以贡献 2 分
    max_score = len(query_terms) * 2.0

    normalized_score = score / max_score

    return normalized_score, matched_terms

def search_papernotes_raw(
    query: str,
    max_results: int = 5,
) -> list[dict[str, str]]:
    """
    Search PaperNotes and return raw search results.
    """

    results: list[dict[str, str]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
        )

        page = browser.new_page()

        page.goto(
            PAPERNOTES_URL,
            wait_until="domcontentloaded",
            timeout=60_000,
        )

        search_input = page.locator(
            "input.md-search__input:visible"
        )

        search_input.wait_for(
            state="visible",
            timeout=10_000,
        )

        search_input.fill(query)

        search_items = page.locator(
            ".md-search-result__item"
        )

        try:
            search_items.first.wait_for(
                state="visible",
                timeout=10_000,
            )
        except Exception:
            return []

        count = min(
            search_items.count(),
            max_results,
        )

        for index in range(count):
            item = search_items.nth(index)

            title_locator = item.locator(
                ".md-search-result__article"
            )

            link_locator = item.locator("a")

            raw_text = (
                title_locator
                .inner_text()
                .strip()
            )

            lines = [
                line.strip()
                for line in raw_text.splitlines()
                if line.strip()
            ]

            title = lines[0] if lines else ""

            keywords = ""
            missing_terms = ""

            for line in lines[1:]:
                if line.startswith("缺少:"):
                    missing_terms = (
                        line
                        .removeprefix("缺少:")
                        .strip()
                    )
                elif not keywords:
                    keywords = line

            href = link_locator.get_attribute(
                "href"
            )

            if not href:
                continue

            if href.startswith("/"):
                url = (
                    "https://papernotes.org"
                    + href
                )
            else:
                url = href

            relevance_score, matched_terms = (
                calculate_relevance(
                    query=query,
                    title=title,
                    keywords=keywords,
                )
            )

            results.append(
                {
                    "title": title,
                    "keywords": keywords,
                    "missing_terms": missing_terms,
                    "matched_terms": matched_terms,
                    "relevance_score": round(
                        relevance_score,
                        3,
                    ),
                    "url": url,
                }
            )

        browser.close()
    results.sort(
        key=lambda item: item[
            "relevance_score"
        ],
        reverse=True,
    )
    return results


@tool
def search_papernotes(
    query: str,
    max_results: int = 5,
) -> str:
    """
    Search PaperNotes for academic papers related to a research topic.

    Use this tool when the user asks about recent academic research,
    papers, methods, or research trends.

    Args:
        query: Academic search keywords.
        max_results: Maximum number of search results to return.
    """

    results = search_papernotes_raw(
        query=query,
        max_results=max_results,
    )

    if not results:
        return json.dumps(
            {
                "query": query,
                "results": [],
                "message": "No papers found.",
            },
            ensure_ascii=False,
        )

    return json.dumps(
        {
            "query": query,
            "results": results,
        },
        ensure_ascii=False,
        indent=2,
    )