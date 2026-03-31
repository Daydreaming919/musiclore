"""Merge Wikidata, MusicBrainz, and Last.fm data into unified artist records."""

import json
from collections import Counter
from pathlib import Path

CACHE_DIR = Path(__file__).resolve().parent / "cache"
WIKIDATA_RAW = CACHE_DIR / "wikidata_raw.json"
MB_RAW = CACHE_DIR / "musicbrainz_raw.json"
LASTFM_RAW = CACHE_DIR / "lastfm_raw.json"

MERGED_ARTISTS = CACHE_DIR / "merged_artists.json"
MERGED_INFLUENCES = CACHE_DIR / "merged_influences.json"
MERGED_GENRES = CACHE_DIR / "merged_genres.json"


def _popularity_tier(listeners: int | None) -> str:
    if listeners is None:
        return "unknown"
    if listeners < 50_000:
        return "niche"
    if listeners < 500_000:
        return "underground"
    if listeners < 5_000_000:
        return "mid"
    return "mainstream"


def _parse_year(val: str | None) -> int | None:
    if not val:
        return None
    try:
        return int(val[:4])
    except (ValueError, TypeError):
        return None


def merge():
    # --- Load raw data ---
    with open(WIKIDATA_RAW, encoding="utf-8") as f:
        wd_data = json.load(f)
    with open(MB_RAW, encoding="utf-8") as f:
        mb_list = json.load(f)
    with open(LASTFM_RAW, encoding="utf-8") as f:
        lastfm_list = json.load(f)

    # --- Index MusicBrainz by mbid ---
    mb_by_mbid = {r["mbid"]: r for r in mb_list if r.get("mbid")}

    # --- Index Last.fm by lowercase name ---
    lastfm_by_name = {}
    for r in lastfm_list:
        if "error" not in r:
            lastfm_by_name[r["name"].lower()] = r

    # --- Deduplicate wikidata artists by qid, collect influences ---
    artists_by_qid = {}
    influences = []
    genre_set = {}

    for genre_key, rows in wd_data.items():
        for row in rows:
            qid = row["qid"]
            # Collect genre info
            gqid = row.get("genre_qid")
            if gqid and gqid not in genre_set:
                genre_set[gqid] = {"qid": gqid, "label": row.get("genre_label", "")}

            # Collect influence edges
            if row.get("influenced_by_qid"):
                influences.append({
                    "from_name": row.get("name", ""),
                    "from_qid": qid,
                    "to_name": row.get("influenced_by_name", ""),
                    "to_qid": row["influenced_by_qid"],
                })

            if qid not in artists_by_qid:
                artists_by_qid[qid] = {
                    "name": row.get("name", ""),
                    "wikidata_qid": qid,
                    "mbid": row.get("mbid"),
                    "inception": row.get("inception"),
                    "country_wd": row.get("country"),
                    "label_wd": row.get("label_name"),
                    "source_genre": row.get("genre_label", ""),
                    "_influenced_by": [],
                    "_genres": set(),
                    "_labels": set(),
                }
            a = artists_by_qid[qid]
            if row.get("influenced_by_qid"):
                a["_influenced_by"].append({
                    "name": row.get("influenced_by_name", ""),
                    "qid": row["influenced_by_qid"],
                })
            if row.get("label_name"):
                a["_labels"].add(row["label_name"])

    # --- Merge ---
    merged = []
    for qid, a in artists_by_qid.items():
        mbid = a["mbid"]
        mb = mb_by_mbid.get(mbid, {}) if mbid else {}
        lfm = lastfm_by_name.get(a["name"].lower(), {})

        # Genres: combine MB tags + lastfm tags
        genres = set()
        for t in mb.get("tags", []):
            genres.add(t)
        for t in lfm.get("tags", []):
            genres.add(t)

        # Labels: combine WD + MB
        labels = set(a["_labels"])
        for lr in mb.get("label_rels", []):
            if lr.get("name"):
                labels.add(lr["name"])

        # Year: prefer MB, fallback WD
        begin_year = _parse_year(mb.get("begin")) or _parse_year(a.get("inception"))
        end_year = _parse_year(mb.get("end"))

        # Country: prefer MB, fallback WD
        country = mb.get("area") or a.get("country_wd")

        listeners = lfm.get("listeners")

        # Deduplicate influences
        seen_inf = set()
        unique_inf = []
        for inf in a["_influenced_by"]:
            k = inf["qid"]
            if k not in seen_inf:
                seen_inf.add(k)
                unique_inf.append(inf)

        merged.append({
            "name": a["name"],
            "wikidata_qid": qid,
            "mbid": mbid,
            "type": mb.get("type"),
            "begin_year": begin_year,
            "end_year": end_year,
            "country": country,
            "genres": sorted(genres),
            "listeners": listeners,
            "popularity_tier": _popularity_tier(listeners),
            "influenced_by": unique_inf,
            "labels": sorted(labels),
            "source_genre": a["source_genre"],
        })

    # Deduplicate influences
    seen_edges = set()
    unique_influences = []
    for inf in influences:
        key = (inf["from_qid"], inf["to_qid"])
        if key not in seen_edges:
            seen_edges.add(key)
            unique_influences.append(inf)

    # --- Save ---
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(MERGED_ARTISTS, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    with open(MERGED_INFLUENCES, "w", encoding="utf-8") as f:
        json.dump(unique_influences, f, ensure_ascii=False, indent=2)
    with open(MERGED_GENRES, "w", encoding="utf-8") as f:
        json.dump(list(genre_set.values()), f, ensure_ascii=False, indent=2)

    # --- Stats ---
    total = len(merged)
    has_mbid = sum(1 for a in merged if a["mbid"])
    has_listeners = sum(1 for a in merged if a["listeners"] is not None)
    tiers = Counter(a["popularity_tier"] for a in merged)

    print(f"Total artists:      {total}")
    print(f"With MBID:          {has_mbid}")
    print(f"With listeners:     {has_listeners}")
    print(f"Influence edges:    {len(unique_influences)}")
    print(f"Genres:             {len(genre_set)}")
    print(f"\nPopularity tiers:")
    for tier in ["mainstream", "mid", "underground", "niche", "unknown"]:
        print(f"  {tier:>12s}: {tiers.get(tier, 0)}")

    print(f"\nSaved to:")
    print(f"  {MERGED_ARTISTS}")
    print(f"  {MERGED_INFLUENCES}")
    print(f"  {MERGED_GENRES}")


if __name__ == "__main__":
    merge()
