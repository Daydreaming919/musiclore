"""One-click data initialization for MusicLore.

Run: python scripts/seed_data.py
"""

import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable

STEPS = [
    ("Wikidata: fetch genre artists", [PYTHON, "data/wikidata.py"]),
    ("MusicBrainz: fetch artist details (full)", [PYTHON, "data/musicbrainz.py"]),
    ("Last.fm: fetch listeners & tags (full)", [PYTHON, "data/lastfm.py"]),
    ("Entity resolver: merge all sources", [PYTHON, "data/entity_resolver.py"]),
    ("Graph: build knowledge graph", [PYTHON, "graph/build_graph.py"]),
    ("Wikipedia: fetch texts", [PYTHON, "data/wikipedia_text.py"]),
    ("RAG: build vector index", [PYTHON, "-c",
     "import sys; sys.path.insert(0,'.'); from rag.retriever import build_rag; build_rag()"]),
]


def main():
    total = len(STEPS)
    t0 = time.time()

    for i, (desc, cmd) in enumerate(STEPS, 1):
        print(f"\n{'='*60}")
        print(f"[{i}/{total}] {desc}")
        print('='*60)

        step_t0 = time.time()
        result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))

        elapsed = time.time() - step_t0
        if result.returncode != 0:
            print(f"\nERROR: Step {i} failed (exit code {result.returncode})")
            print("Fix the error above and re-run this script.")
            sys.exit(1)

        print(f"  Done in {elapsed:.1f}s")

    total_time = time.time() - t0
    print(f"\n{'='*60}")
    print(f"All {total} steps completed in {total_time:.1f}s ({total_time/60:.1f} min)")
    print(f"{'='*60}")
    print("\nYou can now start the app:")
    print("  1. python api/server.py")
    print("  2. streamlit run frontend/app.py --server.port 8501")


if __name__ == "__main__":
    main()
