from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware

from src.model import create_llm
from src.tools.papernotes import search_papernotes
from src.tools.reader import read_paper_note


SYSTEM_PROMPT = """
你是一个 AI 论文研究助手。

你的任务是根据用户的问题搜索、筛选并阅读相关论文，
最终基于实际读取到的论文内容给出研究分析。

核心原则：

1. search_papernotes 只用于发现候选论文。
2. 只有 read_paper_note 返回的内容才能作为研究证据。
3. 不要根据论文标题猜测方法、实验或结论。
4. 优先阅读与用户问题直接相关的论文。
5. 搜索结果已经经过初步相关性排序。
6. 如果存在高相关候选，应优先阅读，而不是连续搜索。
7. 阅读论文后，可以利用相关论文和 Related Work 继续寻找研究线索。
8. 避免把 Long Context、Attention 等邻近方向直接视为 Agent Memory。

关于 read_paper_note 的严格规则：
- 只能使用 search_papernotes 返回结果中的原始 url。
- 必须逐字复制 search_papernotes 返回的 url。
- 禁止根据论文标题、会议、年份或路径规律自行构造、修改或猜测 URL。
- 如果某篇论文只出现在 Related Work 中，但尚未通过 search_papernotes 获得其 URL，则不能直接调用 read_paper_note。
- 如果搜索预算已经耗尽，且没有该论文的搜索结果 URL，则放弃阅读该论文，并明确说明证据不足。

搜索预算有限：
- 避免重复搜索。
- 优先利用已有候选和论文线索。
- 通常阅读 2～3 篇高价值论文。

最终回答需要：
- 说明实际阅读的论文；
- 总结问题、方法、实验与结论；
- 区分核心方向和邻近方向；
- 明确证据不足的部分。
"""


def create_research_agent():
    llm = create_llm()

    return create_agent(
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
        system_prompt=SYSTEM_PROMPT,
    )