"""LangGraph-based agent for MusicLore."""

import json
import re
from typing import Annotated, TypedDict

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from .llm_config import get_agent_llm
from .prompts import SYSTEM_PROMPT
from .tools import (
    query_knowledge_graph,
    search_knowledge_base,
    web_search,
    get_embed_player_url,
)

TOOLS = [query_knowledge_graph, search_knowledge_base, web_search, get_embed_player_url]
MAX_ITERATIONS = 5


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


def _agent_node(state: AgentState) -> dict:
    llm = get_agent_llm().bind_tools(TOOLS)
    response = llm.invoke(state["messages"])
    return {"messages": [response]}


def _should_continue(state: AgentState) -> str:
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        # Count how many agent turns we've had
        agent_turns = sum(1 for m in state["messages"] if isinstance(m, AIMessage) and not isinstance(m, ToolMessage))
        if agent_turns >= MAX_ITERATIONS:
            return "end"
        return "tools"
    return "end"


def build_agent():
    tool_node = ToolNode(TOOLS)
    graph = StateGraph(AgentState)
    graph.add_node("agent", _agent_node)
    graph.add_node("tools", tool_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", _should_continue, {"tools": "tools", "end": END})
    graph.add_edge("tools", "agent")
    return graph.compile()


agent_executor = build_agent()


def _extract_json_block(text: str) -> dict | None:
    m = re.search(r'```json\s*\n?(.*?)\n?\s*```', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            return None
    return None


def _extract_sources(text: str) -> list[str]:
    urls = re.findall(r'https?://[^\s\)>\]]+', text)
    return list(dict.fromkeys(urls))


def chat(message: str) -> dict:
    """Send a message to the agent and get a structured response."""
    result = agent_executor.invoke({
        "messages": [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=message),
        ]
    })

    # Find the last AI message (not a ToolMessage)
    ai_text = ""
    for msg in reversed(result["messages"]):
        if isinstance(msg, AIMessage) and not isinstance(msg, ToolMessage):
            ai_text = msg.content
            break

    return {
        "text": ai_text,
        "structured_data": _extract_json_block(ai_text),
        "sources": _extract_sources(ai_text),
    }


if __name__ == "__main__":
    questions = [
        "后朋克（Post-Punk）是什么？简要介绍一下这个流派。",
        "我很喜欢 Joy Division，请推荐一些类似但更小众的乐队。",
        "给我一个后朋克的发展时间线。",
    ]

    for i, q in enumerate(questions, 1):
        print(f"\n{'='*60}")
        print(f"Q{i}: {q}")
        print('='*60)
        resp = chat(q)
        print(resp["text"])
        if resp["structured_data"]:
            print("\n--- Structured Data ---")
            print(json.dumps(resp["structured_data"], ensure_ascii=False, indent=2)[:1000])
        if resp["sources"]:
            print("\n--- Sources ---")
            for s in resp["sources"][:5]:
                print(f"  {s}")
