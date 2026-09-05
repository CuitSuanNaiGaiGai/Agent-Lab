from typing import Any


def print_trace(messages: list[Any]) -> None:
    print("\n=== Agent Trace ===")

    # 最后一条通常是最终回答，
    # 最终回答由 CLI 单独输出。
    trace_messages = messages[:-1]

    for message in trace_messages:
        message_type = getattr(
            message,
            "type",
            "unknown",
        )

        print(f"\n[{message_type}]")

        tool_calls = getattr(
            message,
            "tool_calls",
            None,
        )

        if tool_calls:
            print(
                "Tool calls:",
                tool_calls,
            )

        content = getattr(
            message,
            "content",
            None,
        )

        if content:
            print(content)