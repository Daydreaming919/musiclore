"""Chunk Wikipedia texts for RAG ingestion."""

import json
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter

WIKI_TEXTS = Path(__file__).resolve().parent.parent / "data" / "cache" / "wiki_texts.json"


def chunk_texts() -> tuple[list[str], list[dict], list[str]]:
    """Read wiki_texts.json, split into chunks, return (texts, metadatas, ids)."""
    with open(WIKI_TEXTS, encoding="utf-8") as f:
        pages = json.load(f)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
    )

    texts = []
    metadatas = []
    ids = []

    for page in pages:
        chunks = splitter.split_text(page["content"])
        for j, chunk in enumerate(chunks):
            texts.append(chunk)
            metadatas.append({
                "source_url": page.get("url", ""),
                "entity_name": page.get("entity_name", ""),
                "entity_type": page.get("entity_type", ""),
            })
            # Sanitize entity name for id
            safe_name = page.get("entity_name", "unknown").replace(" ", "_")
            ids.append(f"{safe_name}_{j}")

    return texts, metadatas, ids
