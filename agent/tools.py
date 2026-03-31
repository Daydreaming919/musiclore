"""Agent tools for MusicLore."""

import json
import re
from langchain_core.tools import tool


@tool
def query_knowledge_graph(template_name: str, params: dict) -> str:
    """Query the music knowledge graph.

    template_name must be one of:
      - "genre_timeline": params={"genre_name": str} — artists in a genre sorted by year
      - "influence_chain": params={"artist_name": str} — find niche artists via influence links (1-2 hops)
      - "artist_context": params={"artist_name": str} — full context for an artist
      - "genre_subgraph": params={"genre_name": str} — influence network within a genre
    """
    from graph.queries import run_query
    results = run_query(template_name, params)
    return json.dumps(results, ensure_ascii=False, default=str)


@tool
def search_knowledge_base(query: str, n_results: int = 5) -> str:
    """Semantic search over the MusicLore knowledge base (Wikipedia texts about genres and artists).

    Args:
        query: natural language search query
        n_results: number of results to return (default 5)
    """
    from rag.retriever import query_rag
    results = query_rag(query, n=n_results)
    return json.dumps(results, ensure_ascii=False)


@tool
def web_search(query: str) -> str:
    """Search the web using DuckDuckGo. Returns top 5 results with title, snippet, and url."""
    try:
        from ddgs import DDGS
        ddgs = DDGS()
        results = []
        for r in ddgs.text(query, max_results=5):
            results.append({
                "title": r.get("title", ""),
                "snippet": r.get("body", ""),
                "url": r.get("href", ""),
            })
        return json.dumps(results, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"搜索暂时不可用: {e}"}, ensure_ascii=False)


@tool
def get_embed_player_url(artist_name: str) -> str:
    """Get a YouTube embed URL for an artist's full album.

    Args:
        artist_name: the artist to search for
    Returns:
        YouTube embed URL or empty string if not found
    """
    try:
        from ddgs import DDGS
        ddgs = DDGS()
        for r in ddgs.text(f"{artist_name} youtube full album", max_results=5):
                url = r.get("href", "")
                m = re.search(r'(?:v=|youtu\.be/)([\w-]{11})', url)
                if m:
                    return f"https://www.youtube.com/embed/{m.group(1)}"
    except Exception:
        pass
    return ""


if __name__ == "__main__":
    print("=== 1. query_knowledge_graph ===")
    r1 = query_knowledge_graph.invoke({
        "template_name": "genre_timeline",
        "params": {"genre_name": "Post-Punk"},
    })
    print(r1[:500])

    print("\n=== 2. search_knowledge_base ===")
    r2 = search_knowledge_base.invoke({"query": "what is post-punk"})
    print(r2[:500])

    print("\n=== 3. web_search ===")
    r3 = web_search.invoke({"query": "Joy Division band"})
    print(r3[:500])

    print("\n=== 4. get_embed_player_url ===")
    r4 = get_embed_player_url.invoke({"artist_name": "Joy Division"})
    print(r4)
