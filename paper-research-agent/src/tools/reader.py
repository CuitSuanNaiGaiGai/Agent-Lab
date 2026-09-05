import json
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from langchain.tools import tool


def read_paper_note_raw(
    url: str,
) -> dict[str, str]:
    """
    Read the main content of a PaperNotes paper page.
    """

    parsed_url = urlparse(url)

    if parsed_url.netloc not in {
        "papernotes.org",
        "www.papernotes.org",
    }:
        raise ValueError(
            "Only PaperNotes URLs are allowed."
        )

    response = httpx.get(
        url,
        follow_redirects=True,
        timeout=30.0,
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    article = soup.select_one(
        "article.md-content__inner"
    )

    if article is None:
        raise ValueError(
            "Could not find paper content."
        )

    # 删除 MkDocs 标题后的 ¶ 锚点
    for headerlink in article.select(
        "a.headerlink"
    ):
        headerlink.decompose()

    title_element = article.find("h1")

    title = (
        title_element.get_text(
            " ",
            strip=True,
        )
        if title_element
        else ""
    )

    content = article.get_text(
        "\n",
        strip=True,
    )

    return {
        "title": title,
        "url": url,
        "content": content,
    }


@tool
def read_paper_note(
    url: str,
) -> str:
    """
    Read the detailed PaperNotes content of a specific academic paper.

    Use this tool after search_papernotes when you have identified
    a potentially relevant paper and need evidence about its method,
    experiments, findings, limitations, or contributions.

    Args:
        url: The PaperNotes URL of the paper to read.
    """

    paper = read_paper_note_raw(url)

    return json.dumps(
        paper,
        ensure_ascii=False,
        indent=2,
    )