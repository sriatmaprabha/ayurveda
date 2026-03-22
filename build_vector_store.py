"""Build the vector store from processed chunks."""

import logging
from pathlib import Path

from src.embeddings import VectorStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

PROJECT_ROOT = Path(__file__).parent


def main():
    chunks_path = PROJECT_ROOT / "data" / "processed" / "chunks.jsonl"

    if not chunks_path.exists():
        print("No chunks found. Run 'python run_ingestion.py' first.")
        return

    store = VectorStore(
        persist_dir=PROJECT_ROOT / "data" / "vector_store",
        collection_name="ayurveda_knowledge",
    )

    print(f"Current vector store size: {store.count}")
    print("Building vector store (this may take a few minutes on first run)...")

    added = store.add_chunks(chunks_path)
    print(f"\nDone! Added {added} chunks. Total in store: {store.count}")


if __name__ == "__main__":
    main()
