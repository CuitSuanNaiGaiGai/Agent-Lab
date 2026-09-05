from src.agent import create_research_agent


def main():
    agent = create_research_agent()

    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "帮我找一下 LLM Agent Memory 相关的最新研究方向。",
                }
            ]
        }
    )

    for message in result["messages"]:
        print(message)


if __name__ == "__main__":
    main()