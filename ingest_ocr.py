"""Ingest OCR'd text files from 1OCR into the vector store."""

import json
import logging
from pathlib import Path
from src.ingestion import IngestionPipeline
from src.embeddings import VectorStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

PROJECT_ROOT = Path(__file__).parent
NGPT_DIR = PROJECT_ROOT / "knowledge_base" / "NGPT"


def main():
    # Find all combined OCR text files
    ocr_files = sorted(NGPT_DIR.rglob("*.oneocr.txt"))
    print(f"Found {len(ocr_files)} OCR'd text files\n")

    if not ocr_files:
        print("No OCR files found. Run 1OCR first.")
        return

    pipeline = IngestionPipeline(
        chunk_size=512,
        chunk_overlap=64,
        output_dir=PROJECT_ROOT / "data" / "processed",
    )

    all_chunks = []
    for f in ocr_files:
        chunks = pipeline.ingest_file(f)
        all_chunks.extend(chunks)

    # Also ingest the "Need to OCR" batch PDFs that have text
    batch_dir = NGPT_DIR / "Need to ocr"
    if batch_dir.exists():
        batch_pdfs = sorted(batch_dir.rglob("*.pdf"))
        print(f"\nFound {len(batch_pdfs)} batch PDFs to ingest")
        for f in batch_pdfs:
            chunks = pipeline.ingest_file(f)
            all_chunks.extend(chunks)

    # Save chunks
    output = pipeline.output_dir / "ocr_chunks.jsonl"
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
    batch_size = 500
    added = 0
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        ids = [f"ocr_{offset + i + j}" for j in range(len(batch))]
        documents = [r["text"] for r in batch]
        metadatas = [{
            "source_file": r.get("source_file", ""),
            "section_title": r.get("section_title", ""),
            "section_type": r.get("section_type", ""),
            "file_name": r.get("metadata", {}).get("file_name", ""),
            "file_type": r.get("metadata", {}).get("file_type", ""),
        } for r in batch]
        metadatas = [{k: v for k, v in m.items() if isinstance(v, (str, int, float, bool))} for m in metadatas]
        store.collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
        added += len(batch)
        print(f"  Added {added}/{len(records)}")

    print(f"\nDone! Store now has {store.count} chunks")


if __name__ == "__main__":
    main()
