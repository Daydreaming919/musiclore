"""Build NetworkX knowledge graph from merged data."""

import json
from pathlib import Path
import networkx as nx

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache"
GRAPH_PATH = CACHE_DIR / "graph.json"


def build_graph() -> nx.DiGraph:
    with open(CACHE_DIR / "merged_artists.json", encoding="utf-8") as f:
        artists = json.load(f)
    with open(CACHE_DIR / "merged_influences.json", encoding="utf-8") as f:
        influences = json.load(f)
    with open(CACHE_DIR / "merged_genres.json", encoding="utf-8") as f:
        genres = json.load(f)

    G = nx.DiGraph()

    # Genre nodes
    for g in genres:
        nid = f"genre:{g['label']}"
        G.add_node(nid, node_type="Genre", name=g["label"], wikidata_qid=g["qid"])

    # Collect all genre/label names for node creation
    all_labels = set()
    all_genre_names = set()
    for a in artists:
        for lb in a.get("labels", []):
            all_labels.add(lb)
        for gn in a.get("genres", []):
            all_genre_names.add(gn)

    # Extra genre nodes from artist tags (not in seed genres)
    existing_genres = {d["name"] for _, d in G.nodes(data=True) if d.get("node_type") == "Genre"}
    for gn in all_genre_names:
        if gn not in existing_genres:
            G.add_node(f"genre:{gn}", node_type="Genre", name=gn, wikidata_qid=None)

    # Label nodes
    for lb in all_labels:
        G.add_node(f"label:{lb}", node_type="Label", name=lb)

    # Artist nodes + edges
    qid_to_nid = {}
    for a in artists:
        qid = a["wikidata_qid"]
        nid = f"artist:{qid}"
        qid_to_nid[qid] = nid
        G.add_node(nid,
                   node_type="Artist",
                   name=a["name"],
                   wikidata_qid=qid,
                   mbid=a.get("mbid"),
                   type=a.get("type"),
                   begin_year=a.get("begin_year"),
                   end_year=a.get("end_year"),
                   country=a.get("country"),
                   listeners=a.get("listeners"),
                   popularity_tier=a.get("popularity_tier"),
                   genres=a.get("genres", []),
                   labels=a.get("labels", []),
                   source_genre=a.get("source_genre"))

        # PLAYS_GENRE edges
        for gn in a.get("genres", []):
            G.add_edge(nid, f"genre:{gn}", edge_type="PLAYS_GENRE")
        # Also link to source_genre
        sg = a.get("source_genre")
        if sg:
            sg_nid = f"genre:{sg}"
            if sg_nid in G:
                G.add_edge(nid, sg_nid, edge_type="PLAYS_GENRE")

        # SIGNED_TO edges
        for lb in a.get("labels", []):
            G.add_edge(nid, f"label:{lb}", edge_type="SIGNED_TO")

    # INFLUENCED_BY edges
    for inf in influences:
        src = qid_to_nid.get(inf["from_qid"])
        dst = qid_to_nid.get(inf["to_qid"])
        if src and dst:
            G.add_edge(src, dst, edge_type="INFLUENCED_BY")

    return G


def save_graph(G: nx.DiGraph, path: Path = GRAPH_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = nx.node_link_data(G)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_graph(path: Path = GRAPH_PATH) -> nx.DiGraph:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return nx.node_link_graph(data, directed=True)


if __name__ == "__main__":
    G = build_graph()
    save_graph(G)

    # Stats
    n_artist = sum(1 for _, d in G.nodes(data=True) if d.get("node_type") == "Artist")
    n_genre = sum(1 for _, d in G.nodes(data=True) if d.get("node_type") == "Genre")
    n_label = sum(1 for _, d in G.nodes(data=True) if d.get("node_type") == "Label")
    n_inf = sum(1 for _, _, d in G.edges(data=True) if d.get("edge_type") == "INFLUENCED_BY")
    n_plays = sum(1 for _, _, d in G.edges(data=True) if d.get("edge_type") == "PLAYS_GENRE")
    n_signed = sum(1 for _, _, d in G.edges(data=True) if d.get("edge_type") == "SIGNED_TO")

    print(f"Nodes total:        {G.number_of_nodes()}")
    print(f"  Artist:           {n_artist}")
    print(f"  Genre:            {n_genre}")
    print(f"  Label:            {n_label}")
    print(f"Edges total:        {G.number_of_edges()}")
    print(f"  INFLUENCED_BY:    {n_inf}")
    print(f"  PLAYS_GENRE:      {n_plays}")
    print(f"  SIGNED_TO:        {n_signed}")

    # Verify: artists under Post-Punk
    pp_nid = "genre:Post-Punk"
    pp_artists = [G.nodes[src]["name"]
                  for src, dst, d in G.edges(data=True)
                  if dst == pp_nid and d.get("edge_type") == "PLAYS_GENRE"]
    print(f"\nPost-Punk artists (first 5): {pp_artists[:5]}")
    print(f"Saved to {GRAPH_PATH}")
