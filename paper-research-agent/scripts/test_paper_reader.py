from src.tools.reader import read_paper_note_raw


def main() -> None:
    url = (
        "https://papernotes.org/"
        "ACL2025/llm_safety/"
        "mextra_agent_memory_privacy/"
    )

    paper = read_paper_note_raw(url)

    print("=== Title ===")
    print(paper["title"])

    print("\n=== URL ===")
    print(paper["url"])

    print("\n=== Content ===")
    print(paper["content"])


if __name__ == "__main__":
    main()