from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware

from src.model import create_llm
from src.tools.papernotes import search_papernotes
from src.tools.reader import read_paper_note

def main() -> None:
    llm = create_llm()

    agent = create_agent(
    model=llm,
    tools=[
        search_papernotes,
        read_paper_note,
    ],
    middleware=[
        ToolCallLimitMiddleware(
            tool_name="search_papernotes",
            run_limit=3,
            exit_behavior="continue",
        ),
    ],
    system_prompt="""
你是一个 AI 论文研究助手。

你的任务是根据用户的问题搜索并阅读相关论文，
最终基于实际读取到的论文内容给出研究分析。

工作流程：

1. 先使用 search_papernotes 搜索候选论文。
2. 搜索关键词尽量简短，通常使用 1～4 个核心英文关键词。
3. 根据 title、keywords、missing_terms 判断论文相关性。
4. 从候选论文中选择真正相关的论文，再使用 read_paper_note 阅读。
5. 搜索结果只能用于发现候选论文，不能作为论文方法或实验结论的证据。
6. 只有 read_paper_note 返回的内容才可以作为研究结论的证据。
7. 不要根据论文标题猜测论文的方法、实验结果或贡献。
8. 如果论文内容不足以支持某个结论，应明确说明证据不足。
9. 区分 LLM Agent Memory 和单纯的 Long Context / Attention 研究。

搜索预算有限。
不要重复使用相似关键词。
在已有搜索结果中优先选择最相关论文进行阅读。

最终回答需要说明：
- 阅读了哪些论文
- 每篇论文解决什么问题
- 核心方法是什么
- 得到了什么关键结论
- 当前能够观察到什么研究趋势
"""
)

    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "帮我找一下 LLM Agent Memory "
                        "相关的最新研究方向。"
                    ),
                }
            ]
        }
    )

    print("\n=== Agent Trace ===")

    for message in result["messages"]:
        print(
            f"\n[{message.type}]"
        )

        if getattr(
            message,
            "tool_calls",
            None,
        ):
            print(
                "Tool calls:",
                message.tool_calls,
            )

        if message.content:
            print(message.content)


if __name__ == "__main__":
    main()