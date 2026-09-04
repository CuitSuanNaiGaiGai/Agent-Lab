"""
AutoGen 软件开发团队协作案例

协作流程：

ProductManager
      ↓
Engineer
      ↓
CodeReviewer
      ↓
REVIEW_FAILED
      ↓
Engineer 修复
      ↓
CodeReviewer
      ↓
REVIEW_PASSED
      ↓
结束
"""

import os
import asyncio
import shutil
from pathlib import Path
from typing import Sequence

from dotenv import load_dotenv

from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.models import ModelInfo
from autogen_core.tools import FunctionTool

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import FunctionalTermination
from autogen_agentchat.messages import (
    BaseAgentEvent,
    BaseChatMessage,
    TextMessage,
)
from autogen_agentchat.ui import Console


# ============================================================
# 1. 环境初始化
# ============================================================

load_dotenv()

WORKSPACE = Path("./workspace").resolve()


def reset_workspace() -> None:
    """
    清空并重新创建 workspace。

    这样可以避免上一次运行生成的文件残留，
    导致 Reviewer 错误地认为本轮已经实现了某些文件。
    """

    if WORKSPACE.exists():
        shutil.rmtree(WORKSPACE)

    WORKSPACE.mkdir(
        parents=True,
        exist_ok=True,
    )


# ============================================================
# 2. Workspace 文件工具
# ============================================================

def _safe_workspace_path(filename: str) -> Path:
    """
    将相对路径转换成 workspace 内的绝对路径。

    同时阻止：
        ../xxx
        ../../xxx

    等目录穿越行为。
    """

    file_path = (WORKSPACE / filename).resolve()

    if file_path != WORKSPACE and WORKSPACE not in file_path.parents:
        raise ValueError(
            f"禁止访问 workspace 外部路径: {filename}"
        )

    return file_path


def write_file(filename: str, content: str) -> str:
    """
    将完整文件保存到 workspace。

    Args:
        filename:
            相对于 workspace 的路径，
            例如：
                app.py
                requirements.txt
                weather_app/service.py

        content:
            文件完整内容。
    """

    file_path = _safe_workspace_path(filename)

    file_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_path.write_text(
        content,
        encoding="utf-8",
    )

    return (
        f"SUCCESS: 已保存文件 {filename}\n"
        f"完整路径: {file_path}\n"
        f"字符数: {len(content)}"
    )


def read_file(filename: str) -> str:
    """
    读取 workspace 中指定文件。
    """

    file_path = _safe_workspace_path(filename)

    if not file_path.exists():
        raise FileNotFoundError(
            f"文件不存在: {filename}"
        )

    if not file_path.is_file():
        raise IsADirectoryError(
            f"目标不是文件: {filename}"
        )

    return file_path.read_text(
        encoding="utf-8"
    )


def list_files() -> str:
    """
    列出 workspace 中当前真实存在的所有文件。

    Reviewer 必须优先调用这个工具，
    而不是猜测 main.py、Home.py 等文件是否存在。
    """

    if not WORKSPACE.exists():
        return "workspace 不存在"

    files = []

    for path in WORKSPACE.rglob("*"):
        if path.is_file():
            files.append(
                str(path.relative_to(WORKSPACE))
            )

    files.sort()

    if not files:
        return "workspace 当前为空"

    return "\n".join(files)


def file_exists(filename: str) -> str:
    """
    检查指定文件是否真实存在。
    """

    file_path = _safe_workspace_path(filename)

    if file_path.exists() and file_path.is_file():
        return f"EXISTS: {filename}"

    return f"NOT_FOUND: {filename}"


# ============================================================
# 3. 注册工具
# ============================================================

write_file_tool = FunctionTool(
    write_file,
    description=(
        "将完整文件内容保存到 workspace。"
        "filename 必须为相对路径。"
        "例如 app.py、requirements.txt、weather_app/service.py。"
    ),
)

read_file_tool = FunctionTool(
    read_file,
    description=(
        "读取 workspace 内一个已经存在的文件。"
        "读取前建议使用 list_files 查看真实文件列表。"
    ),
)

list_files_tool = FunctionTool(
    list_files,
    description=(
        "列出 workspace 中当前真实存在的全部文件。"
        "进行项目检查时应优先调用此工具。"
    ),
)

file_exists_tool = FunctionTool(
    file_exists,
    description=(
        "检查 workspace 中指定文件是否真实存在。"
    ),
)


# ============================================================
# 4. 创建模型客户端
# ============================================================

def create_openai_model_client():
    """
    创建 OpenAI-Compatible 模型客户端。

    可用于：
    Qwen
    DeepSeek
    OpenAI-Compatible API
    其他兼容 OpenAI Chat Completion 协议的模型。
    """

    model_id = os.getenv("LLM_MODEL_ID")
    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL")

    if not model_id:
        raise ValueError(
            "缺少环境变量 LLM_MODEL_ID"
        )

    if not api_key:
        raise ValueError(
            "缺少环境变量 LLM_API_KEY"
        )

    if not base_url:
        raise ValueError(
            "缺少环境变量 LLM_BASE_URL"
        )

    return OpenAIChatCompletionClient(
        model=model_id,
        api_key=api_key,
        base_url=base_url,

        model_info=ModelInfo(
            vision=True,
            function_calling=True,
            json_output=True,
            structured_output=True,
            family="unknown",
        ),
    )


# ============================================================
# 5. Product Manager
# ============================================================

def create_product_manager(model_client):
    """
    创建产品经理 Agent。
    """

    system_message = """
你是一位经验丰富的软件产品经理。

你的任务不是编写代码，而是将用户需求转化为明确、可执行的软件开发方案。

你的职责包括：

1. 需求分析
2. 核心功能定义
3. 功能边界分析
4. 技术方案规划
5. 项目文件规划
6. 风险分析
7. 验收标准定义

请按照下面结构输出：

## 1. 需求理解
明确用户真正需要的软件是什么。

## 2. 核心功能
列出必须实现的核心功能。

## 3. 技术方案
说明推荐的实现方式。

## 4. 项目结构
明确建议创建哪些核心文件。

尤其明确：
- app.py
- requirements.txt
- 其他必要模块

## 5. 实现优先级
优先保证最小可运行项目，
禁止为了架构完整性而延迟核心功能实现。

## 6. 验收标准
必须给出可以被 CodeReviewer 实际检查的标准。

原则：

核心功能 > 可运行性 > 异常处理 > 代码结构 > 扩展设计。

禁止过度设计。

分析完成后最后输出：

请工程师开始实现
"""

    return AssistantAgent(
        name="ProductManager",
        model_client=model_client,
        system_message=system_message,
        model_client_stream=True,
    )


# ============================================================
# 6. Engineer
# ============================================================

def create_engineer(model_client):
    """
    创建软件工程师 Agent。
    """

    system_message = """
你是一位资深 Python 软件工程师。

你的任务是根据：

1. 用户原始需求
2. ProductManager 的开发方案
3. CodeReviewer 上一轮反馈

持续实现并修复一个完整、可运行的软件项目。

==================================================
最重要原则
==================================================

你不是来讨论代码的。

你必须真正使用工具修改 workspace。

禁止只在聊天中输出代码。

==================================================
第一优先级：建立最小可运行闭环
==================================================

开始实现后，必须优先保证：

1. workspace/app.py 存在
2. workspace/requirements.txt 存在
3. app.py 可以作为项目入口
4. 用户核心功能已经接入 app.py

只有完成这些以后，
才允许继续拆分 service、provider、utils、ui 等模块。

禁止先创建大量辅助模块，
最后却没有 app.py。

==================================================
文件操作规则
==================================================

1. 必须使用 write_file 创建和修改文件。

2. write_file 的 content 必须是完整文件内容。

禁止：

...
省略代码
同上
TODO
pass 代替真实实现

3. 修改已有文件之前，可以使用：

list_files
read_file

检查真实项目状态。

4. 禁止假设某文件已经存在。

5. 每次收到 CodeReviewer 的 REVIEW_FAILED 后：

第一步调用 list_files。

第二步读取 Reviewer 指出的相关文件。

第三步逐项解决 Reviewer 提出的阻断问题。

禁止无视 Reviewer 反馈重新设计整个项目。

==================================================
实现策略
==================================================

按照以下顺序工作：

Step 1：
检查 workspace 当前文件。

Step 2：
确保 app.py。

Step 3：
确保 requirements.txt。

Step 4：
完成用户核心功能。

Step 5：
补充必要模块。

Step 6：
修复模块引用。

Step 7：
补充错误处理。

Step 8：
检查全部文件是否完整。

==================================================
结束本轮前必须检查
==================================================

在结束一次 Engineer 回合前必须：

1. 调用 list_files
2. 确认 app.py 存在
3. 确认 requirements.txt 存在
4. 确认不存在你自己创建却未实现的 import
5. 确认用户核心功能已经有实际代码

如果项目尚未完整：

继续调用工具修改。

不要提前结束。
"""

    return AssistantAgent(
        name="Engineer",
        model_client=model_client,
        system_message=system_message,

        tools=[
            list_files_tool,
            file_exists_tool,
            read_file_tool,
            write_file_tool,
        ],

        # Engineer 需要连续创建多个文件
        max_tool_iterations=20,

        # 工具执行后不要额外让模型重新总结工具调用内容
        reflect_on_tool_use=False,

        tool_call_summary_format="{result}",

        model_client_stream=True,
    )


# ============================================================
# 7. Code Reviewer
# ============================================================

def create_code_reviewer(model_client):
    """
    创建严格代码审查 Agent。
    """

    system_message = """
你是一名严格的软件 Code Reviewer。

Engineer 已经把代码真正保存到了 workspace。

你的工作是审查真实文件，
而不是相信 Engineer 的文字描述。

==================================================
审查流程
==================================================

每次开始审查，第一步必须调用：

list_files

获得 workspace 当前真实文件列表。

禁止：

- 猜文件名
- 连续尝试不存在的文件
- 猜测 main.py
- 猜测 Home.py
- 猜测 streamlit_app.py
- 猜测 tests/*
- 猜测其他可能存在的入口

只有 list_files 中真实存在的文件才读取。

==================================================
必须检查
==================================================

至少检查：

1. app.py 是否存在
2. requirements.txt 是否存在
3. 用户核心需求是否完整实现
4. app.py 是否是真正入口
5. 核心业务代码是否存在
6. import 的内部模块是否真实存在
7. 是否存在明显 ModuleNotFoundError 风险
8. 是否存在明显语法或逻辑 Bug
9. 是否有基本错误处理
10. 项目是否具备实际可运行性

==================================================
审查原则
==================================================

只把“阻止软件运行或阻止核心需求完成”的问题
定义为阻断性问题。

不要把下面这些非必要内容当成必须失败的理由：

- 没有 Dockerfile
- 没有 run.sh
- 没有复杂测试体系
- 没有 README
- 没有 CI/CD
- 没有过度完善的工程架构

除非用户原始需求明确要求。

避免需求膨胀。

==================================================
如果发现问题
==================================================

必须输出：

## 审查结论

### 阻断问题

列出真正导致项目不能运行
或者不能满足用户核心需求的问题。

### Engineer 下一轮修改要求

明确告诉 Engineer：

- 修改哪个文件
- 增加什么
- 删除什么
- 修复什么

最后一行必须严格输出失败状态标记。

==================================================
如果项目已经通过
==================================================

明确说明：

- app.py 存在
- requirements.txt 存在
- 核心需求已经实现
- 模块依赖完整
- 没有发现阻断性问题

最后一行必须严格输出成功状态标记。

==================================================
状态协议
==================================================

正文中不要书写、引用、解释或讨论状态标记。

只能在整个回复的最后一行写一个状态标记。

失败时使用失败标记。

成功时使用成功标记。

不得同时输出两个状态。

不得在分析正文中提前出现成功状态标记。
"""

    return AssistantAgent(
        name="CodeReviewer",
        model_client=model_client,
        system_message=system_message,

        tools=[
            list_files_tool,
            file_exists_tool,
            read_file_tool,
        ],

        # Reviewer 只负责检查，不应该无限调用工具
        max_tool_iterations=12,

        reflect_on_tool_use=False,

        tool_call_summary_format="{result}",

        # 非常重要：
        # Reviewer 关闭流式输出。
        #
        # 避免模型 reasoning / streaming chunk
        # 被 termination condition 处理。
        model_client_stream=False,
    )


# ============================================================
# 8. Review 状态解析
# ============================================================

REVIEW_PASSED = "REVIEW_PASSED"
REVIEW_FAILED = "REVIEW_FAILED"


def extract_review_status(content: str) -> str | None:
    """
    只检查 Reviewer 最后一行。

    不进行 substring 判断。

    例如：

        当前不能输出 REVIEW_PASSED
        REVIEW_FAILED

    最终结果仍然是 failed，
    不会因为正文包含 REVIEW_PASSED 而误判。
    """

    if not isinstance(content, str):
        return None

    lines = [
        line.strip()
        for line in content.strip().splitlines()
        if line.strip()
    ]

    if not lines:
        return None

    last_line = lines[-1]

    if last_line == REVIEW_PASSED:
        return "passed"

    if last_line == REVIEW_FAILED:
        return "failed"

    return None


# ============================================================
# 9. 自定义终止条件
# ============================================================

def review_passed_termination(
    messages: Sequence[
        BaseAgentEvent | BaseChatMessage
    ],
) -> bool:
    """
    只有满足以下全部条件时才结束团队循环：

    1. 消息必须是 TextMessage
    2. source 必须是 CodeReviewer
    3. Reviewer 最后一行必须严格等于 REVIEW_PASSED

    ToolCallExecutionEvent
    ModelClientStreamingChunkEvent
    Engineer TextMessage
    Reviewer 工具调用

    全部不会触发终止。
    """

    for message in messages:

        # 只检查最终 TextMessage
        if not isinstance(message, TextMessage):
            continue

        # 只允许 CodeReviewer 决定项目通过
        if message.source != "CodeReviewer":
            continue

        status = extract_review_status(
            message.content
        )

        if status == "passed":
            return True

    return False


# ============================================================
# 10. 最终结果判断
# ============================================================

def is_project_success(result) -> bool:
    """
    从最终团队消息中寻找 CodeReviewer
    最近一次有效审查结果。

    仍然只检查最后一行，
    不做全文 substring 搜索。
    """

    for message in reversed(result.messages):

        if not isinstance(message, TextMessage):
            continue

        if message.source != "CodeReviewer":
            continue

        status = extract_review_status(
            message.content
        )

        if status == "passed":
            return True

        if status == "failed":
            return False

    return False


def get_last_review_message(result) -> str | None:
    """
    获取最后一次 Reviewer 的正式文本回复。
    """

    for message in reversed(result.messages):

        if not isinstance(message, TextMessage):
            continue

        if message.source != "CodeReviewer":
            continue

        return message.content

    return None


# ============================================================
# 11. 软件开发团队主流程
# ============================================================

async def run_software_development_team():

    print("🔧 初始化 workspace...")

    # 每次任务从干净 workspace 开始。
    reset_workspace()

    print(f"📁 Workspace: {WORKSPACE}")

    print("\n🔧 初始化模型客户端...")

    model_client = create_openai_model_client()

    # --------------------------------------------------------
    # 创建 Agent
    # --------------------------------------------------------

    product_manager = create_product_manager(
        model_client
    )

    engineer = create_engineer(
        model_client
    )

    code_reviewer = create_code_reviewer(
        model_client
    )

    # --------------------------------------------------------
    # 用户原始任务
    # --------------------------------------------------------

    task = """
开发一个城市天气状态显示应用。

核心功能：

1. 实时显示用户输入城市的当前天气状况。
2. 显示未来几天的天气预报。
3. 提供天气数据刷新功能。

技术要求：

1. 使用 Streamlit。
2. 界面简洁。
3. 提供错误处理。
4. 网络请求期间提供加载状态。
5. 项目必须能够通过：

   streamlit run app.py

   启动。
"""

    try:

        # ====================================================
        # Stage 1
        # Product Manager
        # ====================================================

        print()
        print("=" * 80)
        print("📋 Stage 1：产品经理分析需求")
        print("=" * 80)

        pm_result = await Console(
            product_manager.run_stream(
                task=task
            ),
            output_stats=True,
        )

        # 获取 PM 最终文本
        pm_plan = ""

        for message in reversed(pm_result.messages):

            content = getattr(
                message,
                "content",
                None,
            )

            if isinstance(content, str):
                pm_plan = content
                break

        if not pm_plan:
            raise RuntimeError(
                "ProductManager 未生成有效开发方案"
            )

        # ====================================================
        # Stage 2
        # Engineer <-> Reviewer
        # ====================================================

        print()
        print("=" * 80)
        print("💻 Stage 2：Engineer / Reviewer 迭代")
        print("=" * 80)

        development_task = f"""
==================================================
用户原始需求
==================================================

{task}

==================================================
ProductManager 开发方案
==================================================

{pm_plan}

==================================================
协作规则
==================================================

Engineer：

根据用户需求和产品经理方案，
完整实现软件项目。

所有代码必须真正写入 workspace。

第一优先级：

1. app.py
2. requirements.txt
3. 最小可运行核心功能

之后再进行模块拆分和架构优化。

如果上一轮 CodeReviewer 提出问题，
下一轮必须优先解决这些问题。

--------------------------------------------------

CodeReviewer：

必须基于 workspace 中真实存在的文件进行审查。

第一步必须调用 list_files。

如果存在阻断问题：

给 Engineer 明确修改意见，
并使用失败状态结束本轮 Review。

如果所有核心需求真正满足：

使用成功状态结束 Review。

项目只有在 CodeReviewer 最终确认通过时，
整个团队才可以停止。
"""

        # ----------------------------------------------------
        # 自定义终止条件
        # ----------------------------------------------------

        termination = FunctionalTermination(
            review_passed_termination
        )

        # ----------------------------------------------------
        # Round Robin
        #
        # 轮次：
        #
        # Engineer     turn 1
        # Reviewer     turn 2
        # Engineer     turn 3
        # Reviewer     turn 4
        # ...
        #
        # max_turns=12
        # 最多允许约 6 次 Engineer / Review
        # ----------------------------------------------------

        team = RoundRobinGroupChat(
            participants=[
                engineer,
                code_reviewer,
            ],
            termination_condition=termination,
            max_turns=12,
        )

        result = await Console(
            team.run_stream(
                task=development_task
            ),
            output_stats=True,
        )

        # ====================================================
        # Stage 3
        # 最终验收
        # ====================================================

        success = is_project_success(
            result
        )

        print()
        print("=" * 80)
        print("📦 Stage 3：最终结果")
        print("=" * 80)

        if success:
            print(
                "✅ 项目开发成功，并通过 CodeReviewer 验收"
            )
        else:
            print(
                "❌ 项目尚未通过 CodeReviewer 验收"
            )

        print(
            f"停止原因：{result.stop_reason}"
        )

        # ----------------------------------------------------
        # 打印最终项目文件
        # ----------------------------------------------------

        print()
        print("📁 最终 workspace 文件：")
        print("-" * 80)

        print(
            list_files()
        )

        # ----------------------------------------------------
        # 最后一次 Review
        # ----------------------------------------------------

        last_review = get_last_review_message(
            result
        )

        if last_review:

            print()
            print("🔎 最后一次 Code Review：")
            print("-" * 80)

            print(last_review)

        return result

    finally:

        # OpenAIChatCompletionClient 支持异步关闭。
        close_method = getattr(
            model_client,
            "close",
            None,
        )

        if close_method is not None:

            close_result = close_method()

            if asyncio.iscoroutine(close_result):
                await close_result


# ============================================================
# 12. 主程序入口
# ============================================================

if __name__ == "__main__":

    try:

        result = asyncio.run(
            run_software_development_team()
        )

        success = is_project_success(
            result
        )

        print()
        print("=" * 80)
        print("📋 协作结果摘要")
        print("=" * 80)

        print(
            "- Agent 数量：3"
        )

        print(
            "- ProductManager：需求规划"
        )

        print(
            "- Engineer：开发与修复"
        )

        print(
            "- CodeReviewer：代码审查"
        )

        if success:
            print(
                "- 最终状态：✅ REVIEW PASSED"
            )
        else:
            print(
                "- 最终状态：❌ REVIEW FAILED"
            )

    except ValueError as e:

        print(
            f"❌ 配置错误：{e}"
        )

        print(
            "请检查 .env 中的："
        )

        print(
            "LLM_MODEL_ID"
        )

        print(
            "LLM_API_KEY"
        )

        print(
            "LLM_BASE_URL"
        )

    except KeyboardInterrupt:

        print(
            "\n⚠️ 用户主动中断运行"
        )

    except Exception as e:

        print(
            f"❌ 运行错误：{e}"
        )

        import traceback

        traceback.print_exc()