from langchain.tools import tool


@tool
def get_current_research_topic(keyword: str) -> str:
    """
    Return a mock research result for a given academic keyword.
    Use this tool when the user asks to search for a research topic.
    """
    return (
        f"Mock search result for '{keyword}': "
        "Recent research focuses on planning, memory, tool use, "
        "self-improvement, and multi-agent collaboration."
    )