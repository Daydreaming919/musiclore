"""Ingest data into the NetworkX graph."""

import networkx as nx
from .schema import (
    NODE_GENRE, NODE_ARTIST, NODE_ALBUM, NODE_TRACK,
    EDGE_SUBGENRE_OF, EDGE_INFLUENCED_BY, EDGE_PLAYS_GENRE,
    EDGE_RELEASED, EDGE_CONTAINS,
    load_graph, save_graph,
)


def add_genre(G: nx.DiGraph, qid: str, label: str, **attrs) -> None:
    G.add_node(qid, type=NODE_GENRE, label=label, **attrs)


def add_artist(G: nx.DiGraph, mbid: str, name: str, **attrs) -> None:
    G.add_node(mbid, type=NODE_ARTIST, label=name, **attrs)


def add_album(G: nx.DiGraph, mbid: str, title: str, **attrs) -> None:
    G.add_node(mbid, type=NODE_ALBUM, label=title, **attrs)


def add_track(G: nx.DiGraph, mbid: str, title: str, **attrs) -> None:
    G.add_node(mbid, type=NODE_TRACK, label=title, **attrs)


def link_subgenre(G: nx.DiGraph, child_qid: str, parent_qid: str) -> None:
    G.add_edge(child_qid, parent_qid, type=EDGE_SUBGENRE_OF)


def link_influence(G: nx.DiGraph, genre_qid: str, influenced_by_qid: str) -> None:
    G.add_edge(genre_qid, influenced_by_qid, type=EDGE_INFLUENCED_BY)


def link_artist_genre(G: nx.DiGraph, artist_id: str, genre_qid: str) -> None:
    G.add_edge(artist_id, genre_qid, type=EDGE_PLAYS_GENRE)


def link_artist_album(G: nx.DiGraph, artist_id: str, album_id: str) -> None:
    G.add_edge(artist_id, album_id, type=EDGE_RELEASED)


def link_album_track(G: nx.DiGraph, album_id: str, track_id: str) -> None:
    G.add_edge(album_id, track_id, type=EDGE_CONTAINS)


def ingest_and_save(G: nx.DiGraph) -> None:
    """Save the current graph state to disk."""
    save_graph(G)
