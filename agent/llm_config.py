"""LLM configuration for Qwen via OpenAI-compatible API."""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


def get_agent_llm() -> ChatOpenAI:
    load_dotenv()
    return ChatOpenAI(
        model=os.getenv("QWEN_MODEL", "qwen-plus"),
        openai_api_key=os.getenv("QWEN_API_KEY"),
        openai_api_base=os.getenv("QWEN_BASE_URL"),
        temperature=0.3,
        max_tokens=4096,
    )


def get_cheap_llm() -> ChatOpenAI:
    load_dotenv()
    return ChatOpenAI(
        model="qwen-turbo",
        openai_api_key=os.getenv("QWEN_API_KEY"),
        openai_api_base=os.getenv("QWEN_BASE_URL"),
        temperature=0.2,
        max_tokens=512,
    )


if __name__ == "__main__":
    llm = get_agent_llm()
    resp = llm.invoke("请用一句话介绍 Joy Division 这个乐队")
    print(resp.content)
    print("LLM 连通性测试通过")
