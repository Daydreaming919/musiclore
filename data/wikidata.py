"""Fetch music genre data from Wikidata SPARQL endpoint."""

import json
import time
from pathlib import Path
from SPARQLWrapper import SPARQLWrapper, JSON

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = "MusicLore/0.1.0 (musiclore@example.com)"

CACHE_DIR = Path(__file__).resolve().parent / "cache"
SEED_PATH = Path(__file__).resolve().parent / "seed_genres.json"


def _query(sparql_str: str) -> list[dict]:
    sparql = SPARQLWrapper(SPARQL_ENDPOINT, agent=USER_AGENT)
    sparql.setQuery(sparql_str)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    time.sleep(2)
    rows = []
    for b in results["results"]["bindings"]:
        row = {}
        for k, v in b.items():
            row[k] = v["value"]
        rows.append(row)
    return rows


def get_genre_artists(genre_qid: str, genre_label: str) -> list[dict]:
    """获取某流派下所有艺术家及其影响关系。"""
    q = f"""
    SELECT DISTINCT
      ?artist ?artistLabel ?mbid ?inception
      ?influencedBy ?influencedByLabel
      ?recordLabel ?recordLabelLabel
      ?country ?countryLabel
    WHERE {{
      ?artist wdt:P136 wd:{genre_qid} .
      ?artist wdt:P31/wdt:P279* wd:Q215380 .
      OPTIONAL {{ ?artist wdt:P434 ?mbid . }}
      OPTIONAL {{ ?artist wdt:P571 ?inception . }}
      OPTIONAL {{ ?artist wdt:P737 ?influencedBy .
                  ?influencedBy rdfs:label ?influencedByLabel .
                  FILTER(LANG(?influencedByLabel) = "en") }}
      OPTIONAL {{ ?artist wdt:P264 ?recordLabel .
                  ?recordLabel rdfs:label ?recordLabelLabel .
                  FILTER(LANG(?recordLabelLabel) = "en") }}
      OPTIONAL {{ ?artist wdt:P495 ?country .
                  ?country rdfs:label ?countryLabel .
                  FILTER(LANG(?countryLabel) = "en") }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    LIMIT 2000
    """
    rows = _query(q)
    out = []
    for r in rows:
        qid = r.get("artist", "").rsplit("/", 1)[-1]
        inf_qid = r.get("influencedBy", "")
        inf_qid = inf_qid.rsplit("/", 1)[-1] if inf_qid else None
        out.append({
            "qid": qid,
            "name": r.get("artistLabel", ""),
            "mbid": r.get("mbid"),
            "inception": r.get("inception"),
            "influenced_by_qid": inf_qid,
            "influenced_by_name": r.get("influencedByLabel"),
            "label_name": r.get("recordLabelLabel"),
            "country": r.get("countryLabel"),
            "genre_qid": genre_qid,
            "genre_label": genre_label,
        })
    return out


def get_subgenres(genre_qid: str) -> list[dict]:
    """获取某流派的子流派列表。"""
    q = f"""
    SELECT ?sub ?subLabel WHERE {{
      ?sub wdt:P279 wd:{genre_qid} .
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    """
    rows = _query(q)
    return [
        {"qid": r["sub"].rsplit("/", 1)[-1], "label": r.get("subLabel", "")}
        for r in rows
    ]


if __name__ == "__main__":
    with open(SEED_PATH, encoding="utf-8") as f:
        seeds = json.load(f)

    all_results = {}
    for key, info in seeds.items():
        qid, label = info["qid"], info["label"]
        print(f"Fetching artists for {label} ({qid})...")
        artists = get_genre_artists(qid, label)
        all_results[key] = artists
        print(f"  -> {label}: {len(artists)} rows")

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    out_path = CACHE_DIR / "wikidata_raw.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"Saved to {out_path}")
