"""Fetch artist details from MusicBrainz API."""

import argparse
import json
import sqlite3
import time
from pathlib import Path

import musicbrainzngs

musicbrainzngs.set_useragent("MusicLore", "0.1.0", "musiclore@example.com")

CACHE_DIR = Path(__file__).resolve().parent / "cache"
WIKIDATA_RAW = CACHE_DIR / "wikidata_raw.json"
MB_CACHE_DB = CACHE_DIR / "mb_cache.db"
MB_RAW_OUT = CACHE_DIR / "musicbrainz_raw.json"


def _init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS mb_cache "
        "(mbid TEXT PRIMARY KEY, data TEXT, fetched_at TEXT DEFAULT CURRENT_TIMESTAMP)"
    )
    conn.commit()


def _get_cached(conn: sqlite3.Connection, mbid: str) -> dict | None:
    row = conn.execute("SELECT data FROM mb_cache WHERE mbid=?", (mbid,)).fetchone()
    if row:
        return json.loads(row[0])
    return None


def _set_cached(conn: sqlite3.Connection, mbid: str, data: dict) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO mb_cache (mbid, data) VALUES (?, ?)",
        (mbid, json.dumps(data, ensure_ascii=False)),
    )
    conn.commit()


def _extract_info(raw: dict) -> dict:
    artist = raw.get("artist", raw)
    tags = [t["name"] for t in artist.get("tag-list", [])]

    life = artist.get("life-span", {})
    begin = life.get("begin")
    end = life.get("end")

    area = artist.get("area", {}).get("name")

    members = []
    label_rels = []
    for rel_list in artist.get("artist-relation-list", []):
        if isinstance(rel_list, dict):
            rel_list = [rel_list]
        for rel in (rel_list if isinstance(rel_list, list) else []):
            if rel.get("type") == "member of band":
                target = rel.get("artist", {})
                members.append({
                    "name": target.get("name"),
                    "mbid": target.get("id"),
                    "direction": rel.get("direction"),
                })
    for rel_list in artist.get("label-relation-list", []):
        if isinstance(rel_list, dict):
            rel_list = [rel_list]
        for rel in (rel_list if isinstance(rel_list, list) else []):
            target = rel.get("label", {})
            label_rels.append({
                "name": target.get("name"),
                "type": rel.get("type"),
            })

    return {
        "mbid": artist.get("id"),
        "name": artist.get("name"),
        "type": artist.get("type"),
        "begin": begin,
        "end": end,
        "area": area,
        "tags": tags,
        "members": members,
        "label_rels": label_rels,
    }


def fetch_artist(conn: sqlite3.Connection, mbid: str) -> dict:
    cached = _get_cached(conn, mbid)
    if cached:
        return cached

    raw = musicbrainzngs.get_artist_by_id(
        mbid, includes=["artist-rels", "label-rels", "tags"]
    )
    info = _extract_info(raw)
    _set_cached(conn, mbid, info)
    return info


def load_unique_artists() -> list[dict]:
    with open(WIKIDATA_RAW, encoding="utf-8") as f:
        data = json.load(f)
    seen = {}
    for genre_rows in data.values():
        for row in genre_rows:
            mbid = row.get("mbid")
            if mbid and mbid not in seen:
                seen[mbid] = {"mbid": mbid, "name": row.get("name", "")}
    return list(seen.values())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(MB_CACHE_DB)
    _init_db(conn)

    artists = load_unique_artists()
    if args.limit:
        artists = artists[: args.limit]

    total = len(artists)
    results = []
    t0 = time.time()

    for i, a in enumerate(artists, 1):
        print(f"[{i}/{total}] Fetching: {a['name']}...")
        try:
            info = fetch_artist(conn, a["mbid"])
            results.append(info)
        except Exception as e:
            print(f"  ERROR: {e}")

    conn.close()

    with open(MB_RAW_OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    elapsed = time.time() - t0
    print(f"\nDone: {len(results)}/{total} artists in {elapsed:.1f}s")
    print(f"Saved to {MB_RAW_OUT}")
