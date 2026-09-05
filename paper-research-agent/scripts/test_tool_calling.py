from langchain.agents import create_agent

from src.model import create_llm
from src.tools.demo import get_current_research_topic


def main() -> None:
    llm = create_llm()

    agent = create_agent(
        model=llm,
        tools=[
            get_current_research_topic,
        ],
        system_prompt=(
            "你是一个论文研究助手。"
            "当用户要求搜索或调研某个研究主题时，"
            "必须调用提供的工具获取信息，"
            "不要依赖你自己的知识直接回答。"
        ),
    )

    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "帮我搜索一下 LLM Agent Memory 的研究方向。",
                }
            ]
        }
    )

    print("\n=== Messages ===")

    for message in result["messages"]:
        print(
            f"\n[{message.type}]"
        )
        print(message.content)

        if getattr(
            message,
            "tool_calls",
            None,
        ):
            print(
                "Tool calls:",
                message.tool_calls,
            )


if __name__ == "__main__":
    main()