from ToolExecutor import ToolExecutor
from search import search
from calculator import calculator
from weather import weather

if __name__ == "__main__":
    toolExecutor = ToolExecutor()

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

    print("\n--- 可用的工具 ---")
    print(toolExecutor.getAvailableTools())

    tests = [
        ("Calculator", "(3 + 4) * 2 - 10 / 5"),
        ("Weather", "北京"),
        ("Weather", "Tokyo"),
    ]
    for name, inp in tests:
        print(f"\n--- 执行 {name}[{inp}] ---")
        fn = toolExecutor.getTool(name)
        if fn:
            print(fn(inp))
        else:
            print(f"错误: 未找到工具 '{name}'")