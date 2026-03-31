"""RAG retriever using ChromaDB in local persistent mode."""

from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions

from .chunker import chunk_texts

CHROMA_DB_PATH = str(Path(__file__).resolve().parent.parent / "data" / "chroma_db")
COLLECTION_NAME = "musiclore_knowledge"


def _get_collection():
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef,
    )


def build_rag() -> None:
    """Chunk wiki texts and ingest into ChromaDB."""
    texts, metadatas, ids = chunk_texts()
    collection = _get_collection()

    # Upsert in batches (ChromaDB limit ~5000 per call)
    batch_size = 500
    for i in range(0, len(texts), batch_size):
        end = min(i + batch_size, len(texts))
        collection.upsert(
            ids=ids[i:end],
            documents=texts[i:end],
            metadatas=metadatas[i:end],
        )
        print(f"  Upserted {end}/{len(texts)} chunks")

    print(f"RAG index built: {collection.count()} chunks in collection '{COLLECTION_NAME}'")


def query_rag(query: str, n: int = 5) -> list[dict]:
    """Semantic search over the knowledge base."""
    collection = _get_collection()
    results = collection.query(query_texts=[query], n_results=n)

    out = []
    for i in range(len(results["ids"][0])):
        meta = results["metadatas"][0][i] if results["metadatas"] else {}
        dist = results["distances"][0][i] if results["distances"] else None
        out.append({
            "text": results["documents"][0][i],
            "source_url": meta.get("source_url", ""),
            "entity_name": meta.get("entity_name", ""),
            "score": round(1 - dist, 4) if dist is not None else None,
        })
    return out


if __name__ == "__main__":
    print("Building RAG index...")
    build_rag()

    queries = [
        "what is post-punk music and where did it originate",
        "shoegaze guitar effects and sound",
        "krautrock motorik beat",
    ]

    for q in queries:
        print(f"\n=== Query: {q} ===")
        results = query_rag(q, n=2)
        for r in results:
            print(f"  [{r['entity_name']}] (score={r['score']}) {r['source_url']}")
            print(f"  {r['text'][:200]}...")
            print()
