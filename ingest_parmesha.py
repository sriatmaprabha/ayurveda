"""Ingest new unique books from knowledge_base/Parmesha — skip duplicates."""

import json
import logging
import hashlib
from pathlib import Path
from src.ingestion import IngestionPipeline
from src.embeddings import VectorStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

PROJECT_ROOT = Path(__file__).parent
PARMESHA_DIR = PROJECT_ROOT / "knowledge_base" / "Parmesha"

# Books already in our knowledge base — skip these
DUPLICATE_STEMS = {
    "2015.312381.sushruta-samhita",
    "2015.405963.sushruta-samhita",
    "sushruta samhita vol 1  kunja lal bhishagratna",
    "sushruta samhita vol 2  kunja lal bhishagratna",
    "sushruta samhita vol 3  kunja lal bhishagratna",
    "sushruta samhita vol 3  kunja lal bhishagratna  (1)",
    "sushruta samhita jivanand vidyasagar 1889",
    "sushruta samhita jivanand vidyasagar 1889 alt",
}

# Track files already processed to skip duplicates across the two subfolders
seen_hashes = set()


def get_file_hash(filepath: Path) -> str:
    """Quick hash to detect duplicate files."""
    h = hashlib.md5()
    with open(filepath, "rb") as f:
        h.update(f.read(4096))  # First 4KB is enough
    return h.hexdigest()


def is_duplicate_book(filename: str) -> bool:
    """Check if this book is already in our knowledge base."""
    name_lower = filename.lower()
    for dup in DUPLICATE_STEMS:
        if dup in name_lower:
            return True
    return False


def main():
    # Collect all .md files, dedup across folders
    all_files = []
    for md_file in sorted(PARMESHA_DIR.rglob("*.md")):
        basename = md_file.name.lower()

        # Skip duplicates of existing books
        book_stem = basename.rsplit("_part_", 1)[0] if "_part_" in basename else basename.replace(".md", "")
        if is_duplicate_book(book_stem):
            continue

        # Skip duplicate files across OCR'd and Ready subfolders
        fhash = get_file_hash(md_file)
        if fhash in seen_hashes:
            continue
        seen_hashes.add(fhash)

        all_files.append(md_file)

    print(f"New unique files to ingest: {len(all_files)}")

    # Group by book name
    books = {}
    for f in all_files:
        book_name = f.name.rsplit("_part_", 1)[0] if "_part_" in f.name else f.stem
        if book_name not in books:
            books[book_name] = []
        books[book_name].append(f)

    print(f"Unique new books: {len(books)}")
    for name, parts in sorted(books.items()):
        print(f"  {name}: {len(parts)} parts")

    # Ingest
    pipeline = IngestionPipeline(
        chunk_size=512,
        chunk_overlap=64,
        output_dir=PROJECT_ROOT / "data" / "processed",
    )

    all_chunks = []
    for f in all_files:
        chunks = pipeline.ingest_file(f)
        all_chunks.extend(chunks)

    # Save to JSONL
    output = pipeline.output_dir / "parmesha_chunks.jsonl"
    with open(output, "w", encoding="utf-8") as out:
        for chunk in all_chunks:
            record = {
                "text": chunk.text,
                "metadata": chunk.metadata,
                "source_file": chunk.source_file,
                "section_title": chunk.section_title,
                "section_type": chunk.section_type,
            }
            out.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"\n{len(all_chunks)} chunks saved to {output}")

    # Add to vector store
    store = VectorStore(persist_dir=PROJECT_ROOT / "data" / "vector_store")
    print(f"Current store: {store.count} chunks")

    records = []
    with open(output, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    offset = store.count
    batch_size = 100
    added = 0
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        ids = [f"par_{offset + i + j}" for j in range(len(batch))]
        documents = [r["text"] for r in batch]
        metadatas = [{
            "source_file": r.get("source_file", ""),
            "section_title": r.get("section_title", ""),
            "section_type": r.get("section_type", ""),
            "file_name": r.get("metadata", {}).get("file_name", ""),
            "file_type": r.get("metadata", {}).get("file_type", ""),
        } for r in batch]
        metadatas = [{k: v for k, v in m.items() if isinstance(v, (str, int, float, bool))} for m in metadatas]

        try:
            store.collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
        except Exception as e:
            logging.warning(f"Batch {i} failed: {e}, retrying with smaller batch...")
            for j, rec in enumerate(batch):
                try:
                    store.collection.upsert(
                        ids=[f"par_{offset + i + j}"],
                        documents=[rec["text"]],
                        metadatas=[metadatas[j]],
                    )
                except Exception as e2:
                    logging.warning(f"  Record {i+j} failed: {e2}")
                    continue

        added += len(batch)
        if added % 500 == 0 or added == len(records):
            print(f"  Added {added}/{len(records)}")

    print(f"\nDone! Store now has {store.count} chunks")


if __name__ == "__main__":
    main()
