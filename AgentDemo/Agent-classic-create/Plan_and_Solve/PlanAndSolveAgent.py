import os
import sys
from dotenv import load_dotenv

# 将项目根目录加入 sys.path，以便导入根目录下的 Hello_Agent_LLM
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# 将 ReAct 目录加入 sys.path，以便复用其 ToolExecutor 与 search 工具
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ReAct"))

from Hello_Agent_LLM import HelloAgentsLLM
from Planner import Planner
from Executor import Executor
from ToolExecutor import ToolExecutor
from search import search

load_dotenv()


class PlanAndSolveAgent:
    def __init__(self, llm_client, tool_executor=None):
        """
        初始化智能体，同时创建规划器和执行器实例。
        """
        self.llm_client = llm_client
        self.planner = Planner(self.llm_client)
        self.executor = Executor(self.llm_client, tool_executor)

    def run(self, question: str):
        """
        运行智能体的完整流程:先规划，后执行。
        """
        print(f"\n--- 开始处理问题 ---\n问题: {question}")
        
        # 1. 调用规划器生成计划
        plan = self.planner.plan(question)
        
        # 检查计划是否成功生成
        if not plan:
            print("\n--- 任务终止 --- \n无法生成有效的行动计划。")
            return

        # 2. 调用执行器执行计划
        final_answer = self.executor.execute(question, plan)
        
        print(f"\n--- 任务完成 ---\n最终答案: {final_answer}")


if __name__ == '__main__':
    # 1. 初始化 LLM 客户端（从 .env 读取配置）
    llm_client = HelloAgentsLLM()

    # 2. 初始化工具执行器并注册 Search 工具
    tool_executor = ToolExecutor()
    tool_executor.registerTool(
        "Search",
        "一个网页搜索引擎。当你需要回答关于时事、事实以及在你的知识库中找不到的信息时，应使用此工具。",
        search,
    )

    # 3. 创建 Plan-And-Solve 智能体
    agent = PlanAndSolveAgent(llm_client, tool_executor)

    # 3. 运行智能体
    question = input("请输入您的问题：")
    print(f"\n🚀 启动 Plan-And-Solve 智能体，问题: {question}")
    agent.run(question)