"""Fetch artist info from Last.fm API."""

import argparse
import json
import os
import sqlite3
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

CACHE_DIR = Path(__file__).resolve().parent / "cache"
WIKIDATA_RAW = CACHE_DIR / "wikidata_raw.json"
LASTFM_CACHE_DB = CACHE_DIR / "lastfm_cache.db"
LASTFM_RAW_OUT = CACHE_DIR / "lastfm_raw.json"
LASTFM_BASE = "https://ws.audioscrobbler.com/2.0/"


def _init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS lastfm_cache "
        "(artist_name TEXT PRIMARY KEY, data TEXT, fetched_at TEXT DEFAULT CURRENT_TIMESTAMP)"
    )
    conn.commit()


def _get_cached(conn: sqlite3.Connection, name: str) -> dict | None:
    row = conn.execute("SELECT data FROM lastfm_cache WHERE artist_name=?", (name,)).fetchone()
    if row:
        return json.loads(row[0])
    return None


def _set_cached(conn: sqlite3.Connection, name: str, data: dict) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO lastfm_cache (artist_name, data) VALUES (?, ?)",
        (name, json.dumps(data, ensure_ascii=False)),
    )
    conn.commit()


def fetch_artist_info(conn: sqlite3.Connection, artist_name: str, api_key: str) -> dict | None:
    cached = _get_cached(conn, artist_name)
    if cached:
        return cached

    resp = httpx.get(
        LASTFM_BASE,
        params={
            "method": "artist.getinfo",
            "artist": artist_name,
            "api_key": api_key,
            "format": "json",
        },
        timeout=15,
    )
    data = resp.json()

    if "error" in data:
        info = {"name": artist_name, "error": data.get("message", "unknown")}
        _set_cached(conn, artist_name, info)
        return info

    a = data.get("artist", {})
    stats = a.get("stats", {})
    tags = [t["name"] for t in a.get("tags", {}).get("tag", [])]

    info = {
        "name": a.get("name", artist_name),
        "listeners": int(stats.get("listeners", 0)),
        "playcount": int(stats.get("playcount", 0)),
        "tags": tags,
    }
    _set_cached(conn, artist_name, info)
    time.sleep(0.35)
    return info


def load_unique_artists() -> list[str]:
    with open(WIKIDATA_RAW, encoding="utf-8") as f:
        data = json.load(f)
    seen = set()
    names = []
    for genre_rows in data.values():
        for row in genre_rows:
            name = row.get("name", "").strip()
            if name and name not in seen:
                seen.add(name)
                names.append(name)
    return names


if __name__ == "__main__":
    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    api_key = os.getenv("LASTFM_API_KEY", "")
    if not api_key:
        print("ERROR: LASTFM_API_KEY is empty. Please set it in .env")
        raise SystemExit(1)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(LASTFM_CACHE_DB)
    _init_db(conn)

    artists = load_unique_artists()
    if args.limit:
        artists = artists[: args.limit]

    total = len(artists)
    results = []
    t0 = time.time()

    for i, name in enumerate(artists, 1):
        print(f"[{i}/{total}] Fetching: {name}...")
        try:
            info = fetch_artist_info(conn, name, api_key)
            if info:
                results.append(info)
        except Exception as e:
            print(f"  ERROR: {e}")

    conn.close()

    with open(LASTFM_RAW_OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    elapsed = time.time() - t0
    print(f"\nDone: {len(results)}/{total} artists in {elapsed:.1f}s")
    print(f"Saved to {LASTFM_RAW_OUT}")
