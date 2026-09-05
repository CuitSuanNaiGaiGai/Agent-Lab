import argparse

from src.service import ResearchService
from src.trace import print_trace

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Paper Research Agent"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="显示 Agent 搜索、阅读和工具调用过程",
    )

    args = parser.parse_args()

    service = ResearchService()

    print("Paper Research Agent")
    print("输入你的研究问题，输入 exit 退出。\n")

    while True:
        query = input("You: ").strip()

        if not query:
            continue

        if query.lower() in {
            "exit",
            "quit",
        }:
            break

        result = service.research(query)

        if args.debug:
            print_trace(result.messages)

        print("\nAgent:")
        print(result.answer)
        print()


if __name__ == "__main__":
    main()