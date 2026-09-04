import re
from constants import EXECUTOR_PROMPT_TEMPLATE


class Executor:
    def __init__(self, llm_client, tool_executor=None):
        self.llm_client = llm_client
        self.tool_executor = tool_executor

    def execute(self, question: str, plan: list[str]) -> str:
        """
        根据计划，逐步执行并解决问题。每个步骤内可以选择性调用外部工具。
        """
        history = ""  # 用于存储历史步骤和结果的字符串
        tools_desc = self.tool_executor.getAvailableTools() if self.tool_executor else "无可用工具"

        print("\n--- 正在执行计划 ---")

        for i, step in enumerate(plan):
            print(f"\n-> 正在执行步骤 {i+1}/{len(plan)}: {step}")

            step_result = ""  # 当前步骤的中间结果
            sub_iter = 0
            max_sub_iter = 3  # 防止单个步骤无限调工具

            while sub_iter < max_sub_iter:
                sub_iter += 1
                prompt = EXECUTOR_PROMPT_TEMPLATE.format(
                    question=question,
                    plan=plan,
                    history=history if history else "无",
                    current_step=step,
                    tools=tools_desc,
                    step_result=step_result if step_result else "无",
                )
                messages = [{"role": "user", "content": prompt}]
                response_text = self.llm_client.think(messages=messages) or ""

                # 检查 LLM 是否要求调用工具
                tool_match = re.search(r"TOOL\[(\w+)\]\[(.*?)\]", response_text, re.DOTALL)
                if tool_match and self.tool_executor:
                    tool_name = tool_match.group(1)
                    tool_input = tool_match.group(2).strip()
                    print(f"   🔧 调用工具: {tool_name}[{tool_input}]")
                    tool_func = self.tool_executor.getTool(tool_name)
                    if tool_func:
                        observation = tool_func(tool_input)
                    else:
                        observation = f"错误: 未找到工具 '{tool_name}'"
                    obs_preview = observation if len(observation) <= 200 else observation[:200] + "..."
                    print(f"   👀 观察: {obs_preview}")
                    step_result += f"调用了工具 {tool_name}[{tool_input}]\n观察结果: {observation}\n\n"
                    continue  # 让 LLM 基于观察结果继续推理
                else:
                    # LLM 给出了直接答案，作为步骤结果
                    step_result = response_text
                    break

            if sub_iter >= max_sub_iter:
                print(f"   ⚠️ 步骤 {i+1} 达到最大子迭代次数，使用当前结果。")

            history += f"步骤 {i+1}: {step}\n结果: {step_result}\n\n"
            print(f"✅ 步骤 {i+1} 已完成，结果: {step_result}")

        final_answer = step_result
        return final_answer
