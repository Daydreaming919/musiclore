"""Graph query functions using NetworkX."""

from __future__ import annotations
from collections import deque
from typing import Any
import networkx as nx
from .build_graph import load_graph

_G: nx.DiGraph | None = None


def _get_graph() -> nx.DiGraph:
    global _G
    if _G is None:
        _G = load_graph()
    return _G


def _find_artist_node(name: str) -> str | None:
    """Find artist node id by name (case-insensitive)."""
    G = _get_graph()
    name_lower = name.lower()
    for nid, d in G.nodes(data=True):
        if d.get("node_type") == "Artist" and d.get("name", "").lower() == name_lower:
            return nid
    return None


def genre_timeline(genre_name: str) -> list[dict]:
    """获取某流派的所有艺术家，按 begin_year 排序。"""
    G = _get_graph()
    genre_nid = f"genre:{genre_name}"
    if genre_nid not in G:
        return []

    artists = []
    for src, dst, d in G.edges(data=True):
        if dst == genre_nid and d.get("edge_type") == "PLAYS_GENRE":
            nd = G.nodes[src]
            if nd.get("node_type") == "Artist":
                artists.append({
                    "artist": nd.get("name"),
                    "start_year": nd.get("begin_year"),
                    "end_year": nd.get("end_year"),
                    "country": nd.get("country"),
                    "listeners": nd.get("listeners"),
                    "tier": nd.get("popularity_tier"),
                    "qid": nd.get("wikidata_qid"),
                })

    artists.sort(key=lambda x: (x["start_year"] is None, x["start_year"]))
    return artists[:100]


def influence_chain(artist_name: str) -> list[dict]:
    """从某艺术家出发，通过 1-2 跳影响关系找到小众乐队。"""
    G = _get_graph()
    start = _find_artist_node(artist_name)
    if not start:
        return []

    visited = {start: [G.nodes[start]["name"]]}
    queue = deque([(start, [G.nodes[start]["name"]])])
    depth = {start: 0}

    while queue:
        current, path = queue.popleft()
        if depth[current] >= 2:
            continue

        for _, nbr, d in G.out_edges(current, data=True):
            if d.get("edge_type") == "INFLUENCED_BY" and nbr not in visited:
                new_path = path + [G.nodes[nbr]["name"]]
                visited[nbr] = new_path
                depth[nbr] = depth[current] + 1
                queue.append((nbr, new_path))

        for src, _, d in G.in_edges(current, data=True):
            if d.get("edge_type") == "INFLUENCED_BY" and src not in visited:
                new_path = path + [G.nodes[src]["name"]]
                visited[src] = new_path
                depth[src] = depth[current] + 1
                queue.append((src, new_path))

    results = []
    for nid, inf_path in visited.items():
        if nid == start:
            continue
        nd = G.nodes[nid]
        tier = nd.get("popularity_tier")
        if tier not in ("niche", "underground"):
            continue
        results.append({
            "name": nd.get("name"),
            "listeners": nd.get("listeners"),
            "year": nd.get("begin_year"),
            "country": nd.get("country"),
            "qid": nd.get("wikidata_qid"),
            "influence_path": inf_path,
        })

    results.sort(key=lambda x: (x["listeners"] is None, x["listeners"] or 0))
    return results[:20]


def artist_context(artist_name: str) -> list[dict]:
    """获取某艺术家的完整上下文。"""
    G = _get_graph()
    nid = _find_artist_node(artist_name)
    if not nid:
        return []

    nd = G.nodes[nid]
    genres = []
    labels = []
    influenced_by = []
    influenced = []

    for _, dst, d in G.out_edges(nid, data=True):
        etype = d.get("edge_type")
        if etype == "PLAYS_GENRE":
            genres.append(G.nodes[dst].get("name"))
        elif etype == "SIGNED_TO":
            labels.append(G.nodes[dst].get("name"))
        elif etype == "INFLUENCED_BY":
            influenced_by.append(G.nodes[dst].get("name"))

    for src, _, d in G.in_edges(nid, data=True):
        if d.get("edge_type") == "INFLUENCED_BY":
            influenced.append(G.nodes[src].get("name"))

    return [{
        "name": nd.get("name"),
        "begin_year": nd.get("begin_year"),
        "end_year": nd.get("end_year"),
        "country": nd.get("country"),
        "listeners": nd.get("listeners"),
        "qid": nd.get("wikidata_qid"),
        "genres": genres,
        "labels": labels,
        "influenced_by": influenced_by,
        "influenced": influenced,
    }]


def genre_subgraph(genre_name: str) -> list[dict]:
    """获取某流派内部的影响关系网络。"""
    G = _get_graph()
    genre_nid = f"genre:{genre_name}"
    if genre_nid not in G:
        return []

    artist_nids = set()
    for src, dst, d in G.edges(data=True):
        if dst == genre_nid and d.get("edge_type") == "PLAYS_GENRE":
            if G.nodes[src].get("node_type") == "Artist":
                artist_nids.add(src)

    results = []
    for src, dst, d in G.edges(data=True):
        if d.get("edge_type") == "INFLUENCED_BY" and src in artist_nids and dst in artist_nids:
            s = G.nodes[src]
            t = G.nodes[dst]
            results.append({
                "source": s.get("name"),
                "target": t.get("name"),
                "source_year": s.get("begin_year"),
                "target_year": t.get("begin_year"),
                "source_listeners": s.get("listeners"),
            })

    return results


def run_query(template_name: str, params: dict) -> list[dict]:
    """根据 template_name 调用对应的查询函数。"""
    templates = {
        "genre_timeline": lambda p: genre_timeline(p["genre_name"]),
        "influence_chain": lambda p: influence_chain(p["artist_name"]),
        "artist_context": lambda p: artist_context(p["artist_name"]),
        "genre_subgraph": lambda p: genre_subgraph(p["genre_name"]),
    }
    fn = templates.get(template_name)
    if not fn:
        raise ValueError(f"Unknown template: {template_name}. Available: {list(templates)}")
    return fn(params)


if __name__ == "__main__":
    import json

    print("=== 1. genre_timeline('Post-Punk') - first 5 ===")
    r1 = genre_timeline("Post-Punk")
    for item in r1[:5]:
        print(f"  {item['start_year']} - {item['artist']} ({item['country']}, {item['tier']})")
    print(f"  ... total {len(r1)} artists")

    jd = _find_artist_node("Joy Division")
    test_artist = "Joy Division"
    if not jd:
        print("\nJoy Division not found. Post-Punk artists in graph:")
        for item in r1[:20]:
            print(f"  - {item['artist']}")
        test_artist = r1[0]["artist"] if r1 else None

    if test_artist:
        print(f"\n=== 2. influence_chain('{test_artist}') ===")
        r2 = influence_chain(test_artist)
        if r2:
            for item in r2[:5]:
                print(f"  {item['name']} (listeners={item['listeners']}, path={item['influence_path']})")
        else:
            print("  No influence chain found")
        print(f"  ... total {len(r2)} results")

        print(f"\n=== 3. artist_context('{test_artist}') ===")
        r3 = artist_context(test_artist)
        if r3:
            print(json.dumps(r3[0], indent=2, ensure_ascii=False))

    print("\n=== 4. genre_subgraph('Post-Punk') ===")
    r4 = genre_subgraph("Post-Punk")
    for item in r4[:5]:
        print(f"  {item['source']} -> {item['target']}")
    print(f"  ... total {len(r4)} influence edges within Post-Punk")
