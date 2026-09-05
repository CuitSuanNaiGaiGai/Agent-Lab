from dataclasses import dataclass
from typing import Any

from src.agent import create_research_agent


@dataclass
class ResearchResult:
    query: str
    answer: str
    messages: list[Any]
    trace: list[dict]


def build_trace(
    messages: list[Any],
) -> list[dict]:
    trace = []

    for message in messages:
        item = {
            "type": getattr(
                message,
                "type",
                "unknown",
            ),
            "content": getattr(
                message,
                "content",
                "",
            ),
        }

        tool_calls = getattr(
            message,
            "tool_calls",
            None,
        )

        if tool_calls:
            item["tool_calls"] = tool_calls

        tool_call_id = getattr(
            message,
            "tool_call_id",
            None,
        )

        if tool_call_id:
            item["tool_call_id"] = tool_call_id

        trace.append(item)

    return trace

class ResearchService:

    def __init__(self) -> None:
        self.agent = create_research_agent()

    def research(
        self,
        query: str,
    ) -> ResearchResult:
        result = self.agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": query,
                    }
                ]
            }
        )

        messages = result["messages"]
        final_message = messages[-1]

        return ResearchResult(
            query=query,
            answer=final_message.content,
            messages=messages,
            trace=build_trace(messages),
        )