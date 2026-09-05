import json
from dataclasses import dataclass, field


@dataclass
class ToolMetrics:
    search_attempt_count: int = 0
    search_success_count: int = 0
    search_blocked_count: int = 0

    read_attempt_count: int = 0
    read_success_count: int = 0
    read_failure_count: int = 0

    searched_papers: list[dict] = field(
        default_factory=list
    )

    read_papers: list[dict] = field(
        default_factory=list
    )

    read_failures: list[dict] = field(
        default_factory=list
    )


@dataclass
class SelectionMetrics:
    searched_unique_count: int = 0
    read_unique_count: int = 0

    selected_from_search_count: int = 0

    selection_rate: float = 0.0

    unread_papers: list[dict] = field(
        default_factory=list
    )


@dataclass
class QualityMetrics:
    must_read_count: int = 0
    must_read_hit_count: int = 0
    must_read_recall: float = 1.0

    min_read_count: int = 0
    read_count_pass: bool = True

def calculate_tool_metrics(
    trace: list[dict],
) -> ToolMetrics:
    metrics = ToolMetrics()

    tool_call_names: dict[str, str] = {}

    # --------------------------------
    # 第一遍：
    # 记录 Agent 发出的所有 Tool Call
    # --------------------------------

    for message in trace:
        tool_calls = message.get(
            "tool_calls",
            [],
        )

        for call in tool_calls:
            name = call.get("name")
            call_id = call.get("id")

            if call_id and name:
                tool_call_names[call_id] = name

            if name == "search_papernotes":
                metrics.search_attempt_count += 1

            elif name == "read_paper_note":
                metrics.read_attempt_count += 1

    # --------------------------------
    # 第二遍：
    # 根据 tool_call_id 分析 Tool Result
    # --------------------------------

    for message in trace:
        if message.get("type") != "tool":
            continue

        tool_call_id = message.get(
            "tool_call_id"
        )

        tool_name = tool_call_names.get(
            tool_call_id
        )

        content = message.get(
            "content",
            "",
        )

        # ================================
        # Search Tool
        # ================================

        if tool_name == "search_papernotes":

            if (
                isinstance(content, str)
                and "Tool call limit exceeded"
                in content
            ):
                metrics.search_blocked_count += 1
                continue

            try:
                data = json.loads(content)
            except (
                json.JSONDecodeError,
                TypeError,
            ):
                continue

            if data.get("success") is True:
                metrics.search_success_count += 1

                for paper in data.get(
                    "results",
                    [],
                ):
                    metrics.searched_papers.append(
                        {
                            "query": data.get(
                                "query",
                                "",
                            ),
                            "title": paper.get(
                                "title",
                                "",
                            ),
                            "url": paper.get(
                                "url",
                                "",
                            ),
                            "relevance_score": (
                                paper.get(
                                    "relevance_score",
                                    0.0,
                                )
                            ),
                        }
                    )

        # ================================
        # Reader Tool
        # ================================

        elif tool_name == "read_paper_note":

            try:
                data = json.loads(content)
            except (
                json.JSONDecodeError,
                TypeError,
            ):
                continue

            if data.get("success") is True:
                metrics.read_success_count += 1

                metrics.read_papers.append(
                    {
                        "title": data.get(
                            "title",
                            "",
                        ),
                        "url": data.get(
                            "url",
                            "",
                        ),
                    }
                )

            elif data.get("success") is False:
                metrics.read_failure_count += 1

                metrics.read_failures.append(
                    {
                        "url": data.get(
                            "url",
                            "",
                        ),
                        "error": data.get(
                            "error",
                            "",
                        ),
                        "message": data.get(
                            "message",
                            "",
                        ),
                    }
                )

    return metrics


def calculate_selection_metrics(
    searched_papers: list[dict],
    read_papers: list[dict],
) -> SelectionMetrics:
    metrics = SelectionMetrics()

    # -------------------------
    # Search 候选按 URL 去重
    # -------------------------

    searched_by_url: dict[str, dict] = {}

    for paper in searched_papers:
        url = paper.get("url", "")

        if not url:
            continue

        # 同一篇论文可能被多个 query 搜到
        # 保留 relevance_score 最高的一次
        old_paper = searched_by_url.get(url)

        if old_paper is None:
            searched_by_url[url] = paper
            continue

        old_score = old_paper.get(
            "relevance_score",
            0.0,
        )

        new_score = paper.get(
            "relevance_score",
            0.0,
        )

        if new_score > old_score:
            searched_by_url[url] = paper

    # -------------------------
    # Read 论文按 URL 去重
    # -------------------------

    read_by_url: dict[str, dict] = {}

    for paper in read_papers:
        url = paper.get("url", "")

        if not url:
            continue

        read_by_url[url] = paper

    searched_urls = set(
        searched_by_url.keys()
    )

    read_urls = set(
        read_by_url.keys()
    )

    metrics.searched_unique_count = len(
        searched_urls
    )

    metrics.read_unique_count = len(
        read_urls
    )

    selected_urls = (
        searched_urls & read_urls
    )

    metrics.selected_from_search_count = len(
        selected_urls
    )

    if metrics.searched_unique_count > 0:
        metrics.selection_rate = (
            metrics.selected_from_search_count
            / metrics.searched_unique_count
        )

    # -------------------------
    # 搜到了，但没有读
    # -------------------------

    unread_urls = (
        searched_urls - read_urls
    )

    metrics.unread_papers = [
        searched_by_url[url]
        for url in unread_urls
    ]

    return metrics

def calculate_quality_metrics(
    case: dict,
    read_papers: list[dict],
) -> QualityMetrics:
    metrics = QualityMetrics()

    must_read = case.get(
        "must_read",
        [],
    )

    min_read_count = case.get(
        "min_read_count",
        0,
    )

    metrics.must_read_count = len(
        must_read
    )

    metrics.min_read_count = (
        min_read_count
    )

    read_titles = [
        paper.get(
            "title",
            "",
        ).lower()
        for paper in read_papers
    ]

    hit_count = 0

    for expected_title in must_read:
        expected = (
            expected_title.lower()
        )

        if any(
            expected in title
            for title in read_titles
        ):
            hit_count += 1

    metrics.must_read_hit_count = (
        hit_count
    )

    if metrics.must_read_count > 0:
        metrics.must_read_recall = (
            hit_count
            / metrics.must_read_count
        )

    metrics.read_count_pass = (
        len(read_papers)
        >= min_read_count
    )

    return metrics