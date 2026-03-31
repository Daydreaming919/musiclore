"""Graph schema definitions using NetworkX."""

import networkx as nx
from pathlib import Path
import json

GRAPH_PATH = Path(__file__).resolve().parent.parent / "data" / "cache" / "graph.json"

# Node types
NODE_GENRE = "Genre"
NODE_ARTIST = "Artist"
NODE_ALBUM = "Album"
NODE_TRACK = "Track"

# Edge types
EDGE_SUBGENRE_OF = "SUBGENRE_OF"
EDGE_INFLUENCED_BY = "INFLUENCED_BY"
EDGE_PLAYS_GENRE = "PLAYS_GENRE"
EDGE_RELEASED = "RELEASED"
EDGE_CONTAINS = "CONTAINS"


def create_graph() -> nx.DiGraph:
    """Create a new empty directed graph."""
    return nx.DiGraph()


def save_graph(G: nx.DiGraph, path: Path = GRAPH_PATH) -> None:
    """Persist graph to JSON using node_link_data format."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = nx.node_link_data(G)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_graph(path: Path = GRAPH_PATH) -> nx.DiGraph:
    """Load graph from JSON. Returns empty graph if file doesn't exist."""
    if not path.exists():
        return create_graph()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return nx.node_link_graph(data, directed=True)
