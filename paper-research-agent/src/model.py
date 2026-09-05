import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


load_dotenv()


def create_llm() -> ChatOpenAI:
    model_id = os.getenv("LLM_MODEL_ID")
    base_url = os.getenv("LLM_BASE_URL")
    api_key = os.getenv("LLM_API_KEY")

    if not model_id:
        raise ValueError("LLM_MODEL_ID is not configured")

    if not base_url:
        raise ValueError("LLM_BASE_URL is not configured")

    if not api_key:
        raise ValueError("LLM_API_KEY is not configured")

    return ChatOpenAI(
        model=model_id,
        base_url=base_url,
        api_key=api_key,
        temperature=0.2,
        timeout=60,
        max_retries=2,
    )