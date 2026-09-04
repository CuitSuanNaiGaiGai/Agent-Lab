import os
import re
import sys
from dotenv import load_dotenv

# 将项目根目录加入 sys.path，以便导入根目录下的 Hello_Agent_LLM
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ToolExecutor import ToolExecutor
from search import search
from Hello_Agent_LLM import HelloAgentsLLM

load_dotenv()

REACT_PROMPT_TEMPLATE = """你是一个能够通过 "思考-行动-观察" 循环来解决问题的智能体。

你可以使用以下工具:
{tools}

请严格按照以下格式回答问题，每一轮只输出一个 Thought 和一个 Action:

Thought: 思考下一步该做什么
Action: 工具名称[工具输入参数]

当你已经得到最终答案时，请使用如下格式结束:
Thought: 我已经得到了最终答案
Action: Finish[最终答案]

当前问题: {question}

之前的推理历史:
{history}

请继续你的推理。
"""


class ReActAgent:
    def __init__(self, llm_client: HelloAgentsLLM, tool_executor: ToolExecutor, max_steps: int = 5):
        self.llm_client = llm_client
        self.tool_executor = tool_executor
        self.max_steps = max_steps
        self.history = []

    # 核心循环的实现
    def run(self, question: str):
        """
        运行ReAct智能体来回答一个问题。
        """
        self.history = [] # 每次运行时重置历史记录
        current_step = 0

        while current_step < self.max_steps:
            current_step += 1
            print(f"--- 第 {current_step} 步 ---")

            # 1. 格式化提示词
            tools_desc = self.tool_executor.getAvailableTools()
            history_str = "\n".join(self.history)
            prompt = REACT_PROMPT_TEMPLATE.format(
                tools=tools_desc,
                question=question,
                history=history_str
            )

            # 2. 调用LLM进行思考
            messages = [{"role": "user", "content": prompt}]
            response_text = self.llm_client.think(messages=messages)
            
            if not response_text:
                print("错误:LLM未能返回有效响应。")
                break
            
            # 3. 解析LLM的输出
            thought, action = self._parse_output(response_text)
            
            if thought:
                print(f"思考: {thought}")

            if not action:
                print("警告:未能解析出有效的Action，流程终止。")
                break

            # 4. 执行Action
            if action.startswith("Finish"):
                # 如果是Finish指令，提取最终答案并结束
                final_answer = re.match(r"Finish\[(.*)\]", action).group(1)
                print(f"🎉 最终答案: {final_answer}")
                return final_answer
            
            tool_name, tool_input = self._parse_action(action)
            if not tool_name or not tool_input:
                # ... 处理无效Action格式 ...
                continue

            print(f"🎬 行动: {tool_name}[{tool_input}]")
            
            tool_function = self.tool_executor.getTool(tool_name)
            if not tool_function:
                observation = f"错误:未找到名为 '{tool_name}' 的工具。"
            else:
                observation = tool_function(tool_input) # 调用真实工具
            
            # (这段逻辑紧随工具调用之后，在 while 循环的末尾)
            print(f"👀 观察: {observation}")
            
            # 将本轮的Action和Observation添加到历史记录中
            self.history.append(f"Action: {action}")
            self.history.append(f"Observation: {observation}")

        # 循环结束
        print("已达到最大步数，流程终止。")
        return None



    # 解析LLM的输出，提取Thought和Action
    def _parse_output(self, text: str):
        """解析LLM的输出，提取Thought和Action。
        """
        # Thought: 匹配到 Action: 或文本末尾
        thought_match = re.search(r"Thought:\s*(.*?)(?=\nAction:|$)", text, re.DOTALL)
        # Action: 匹配到文本末尾
        action_match = re.search(r"Action:\s*(.*?)$", text, re.DOTALL)
        thought = thought_match.group(1).strip() if thought_match else None
        action = action_match.group(1).strip() if action_match else None
        return thought, action

    def _parse_action(self, action_text: str):
        """解析Action字符串，提取工具名称和输入。
        """
        match = re.match(r"(\w+)\[(.*)\]", action_text, re.DOTALL)
        if match:
            return match.group(1), match.group(2)
        return None, None


if __name__ == '__main__':
    # 1. 初始化 LLM 客户端（从 .env 读取配置）
    llm_client = HelloAgentsLLM()

    # 2. 初始化工具执行器并注册 Search 工具
    tool_executor = ToolExecutor()
    toolExecutor.registerTool(
        "Search",
        "一个网页搜索引擎。当你需要回答关于时事、事实以及在你的知识库中找不到的信息时，应使用此工具。",
        search,
    )
    toolExecutor.registerTool(
        "Calculator",
        "一个算术表达式计算器。当你需要进行精确数值计算（加减乘除、幂、括号）时使用，输入为合法的算术表达式，例如: 3 * (2 + 4)。",
        calculator,
    )
    toolExecutor.registerTool(
        "Weather",
        "一个天气查询工具。当你需要查询某个城市的当前天气情况时使用，输入为城市名称（中英文均可）。",
        weather,
    )

    # 3. 创建 ReAct 智能体
    agent = ReActAgent(llm_client, tool_executor, max_steps=5)

    # 4. 运行智能体
    question = input("请输入您的问题：")
    print(f"\n🚀 启动 ReAct 智能体，问题: {question}")
    final_answer = agent.run(question)

    if final_answer:
        print(f"\n✅ 完成! 最终答案: {final_answer}")
    else:
        print("\n❌ 未能获得最终答案。")