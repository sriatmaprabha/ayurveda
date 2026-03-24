"""Add new chunks (from NGPT ingestion) to the existing vector store."""

import logging
from pathlib import Path
from src.embeddings import VectorStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

PROJECT_ROOT = Path(__file__).parent


def main():
    chunks_path = PROJECT_ROOT / "data" / "processed" / "ngpt_chunks.jsonl"

    if not chunks_path.exists():
        print("No NGPT chunks found. Run 'python ingest_ngpt.py' first.")
        return

    store = VectorStore(
        persist_dir=PROJECT_ROOT / "data" / "vector_store",
        collection_name="ayurveda_knowledge",
    )

    print(f"Current vector store size: {store.count}")
    print(f"Adding new chunks from {chunks_path}...")

    # Use offset IDs so they don't collide with existing chunk_0, chunk_1, etc.
    import json
    records = []
    with open(chunks_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    print(f"Loaded {len(records)} new chunks")

    batch_size = 500
    added = 0
    offset = store.count  # Start IDs after existing chunks

    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]

        ids = [f"ngpt_{offset + i + j}" for j in range(len(batch))]
        documents = [r["text"] for r in batch]
        metadatas = []
        for r in batch:
            meta = {
                "source_file": r.get("source_file", ""),
                "section_title": r.get("section_title", ""),
                "section_type": r.get("section_type", ""),
                "file_name": r.get("metadata", {}).get("file_name", ""),
                "file_type": r.get("metadata", {}).get("file_type", ""),
            }
            meta = {k: v for k, v in meta.items() if isinstance(v, (str, int, float, bool))}
            metadatas.append(meta)

        store.collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )
        added += len(batch)
        print(f"  Added {added}/{len(records)} chunks")

    print(f"\nDone! Vector store now contains {store.count} chunks")


if __name__ == "__main__":
    main()
