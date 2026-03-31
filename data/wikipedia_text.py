"""Fetch Wikipedia text for genres and top artists."""

import json
import time
from pathlib import Path

import wikipedia

wikipedia.set_lang("en")

CACHE_DIR = Path(__file__).resolve().parent / "cache"
WIKI_OUT = CACHE_DIR / "wiki_texts.json"
MERGED_ARTISTS = CACHE_DIR / "merged_artists.json"
SEED_PATH = Path(__file__).resolve().parent / "seed_genres.json"

GENRE_SEARCH_VARIANTS = {
    "Post-Punk": ["Post-punk", "Post-punk music", "Post punk"],
    "Shoegaze": ["Shoegaze", "Shoegazing", "Shoegaze music"],
    "Krautrock": ["Krautrock", "Krautrock music", "Kosmische Musik"],
}


def _fetch_page(title: str) -> dict | None:
    try:
        page = wikipedia.page(title, auto_suggest=False)
        time.sleep(0.5)
        return {
            "title": page.title,
            "url": page.url,
            "content": page.content,
        }
    except wikipedia.exceptions.DisambiguationError:
        return None
    except wikipedia.exceptions.PageError:
        return None
    except Exception as e:
        print(f"  Unexpected error for '{title}': {e}")
        return None


def fetch_genre_pages() -> list[dict]:
    results = []
    for genre, variants in GENRE_SEARCH_VARIANTS.items():
        print(f"Fetching genre: {genre}")
        for variant in variants:
            page = _fetch_page(variant)
            if page:
                page["entity_name"] = genre
                page["entity_type"] = "genre"
                results.append(page)
                print(f"  Found: {page['title']} ({len(page['content'])} chars)")
                break
            print(f"  '{variant}' not found, trying next...")
        else:
            print(f"  WARNING: No page found for {genre}")
    return results


def fetch_artist_pages(top_n: int = 30) -> list[dict]:
    with open(MERGED_ARTISTS, encoding="utf-8") as f:
        artists = json.load(f)

    # Sort by listeners descending, filter out None
    ranked = [a for a in artists if a.get("listeners") is not None]
    ranked.sort(key=lambda x: x["listeners"], reverse=True)
    top = ranked[:top_n]

    results = []
    for i, a in enumerate(top, 1):
        name = a["name"]
        print(f"[{i}/{len(top)}] Fetching: {name}...")
        page = _fetch_page(name)
        if page:
            page["entity_name"] = name
            page["entity_type"] = "artist"
            results.append(page)
            print(f"  Found: {page['title']} ({len(page['content'])} chars)")
        else:
            # Try with "(band)" suffix
            page = _fetch_page(f"{name} (band)")
            if page:
                page["entity_name"] = name
                page["entity_type"] = "artist"
                results.append(page)
                print(f"  Found: {page['title']} ({len(page['content'])} chars)")
            else:
                print(f"  Not found")
    return results


if __name__ == "__main__":
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    genre_pages = fetch_genre_pages()
    artist_pages = fetch_artist_pages(top_n=30)

    all_pages = genre_pages + artist_pages
    with open(WIKI_OUT, "w", encoding="utf-8") as f:
        json.dump(all_pages, f, ensure_ascii=False, indent=2)

    print(f"\nTotal articles: {len(all_pages)} ({len(genre_pages)} genres + {len(artist_pages)} artists)")
    print(f"Saved to {WIKI_OUT}")
