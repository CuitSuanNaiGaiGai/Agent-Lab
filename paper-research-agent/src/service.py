from dataclasses import dataclass
from typing import Any

from src.agent import create_research_agent


@dataclass
class ResearchResult:
    query: str
    answer: str
    messages: list[Any]


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
        )