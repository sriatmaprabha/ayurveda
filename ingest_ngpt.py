"""Ingest new NGPT books into the knowledge base — text-extractable, non-duplicate PDFs only."""

import logging
import pymupdf
from pathlib import Path
from src.ingestion import IngestionPipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

PROJECT_ROOT = Path(__file__).parent
NGPT_DIR = PROJECT_ROOT / "knowledge_base" / "NGPT"

# Files already in the main knowledge_base (skip duplicates)
DUPLICATES = {
    "2015.63710.the-caraka-samhita1",
    "sushruta_chikitsa", "sushruta_kalpa", "sushruta_nidana",
    "sushruta_sharira", "sushruta_sutra", "sushruta_uttara",
}

SKIP_DIRS = {"Need to ocr", "Batch"}


def is_text_extractable(pdf_path: Path, min_text: int = 200) -> bool:
    try:
        doc = pymupdf.open(str(pdf_path))
        total = sum(len(page.get_text().strip()) for page in doc[:5])
        doc.close()
        return total > min_text
    except Exception:
        return False


def get_ingestable_files() -> list[Path]:
    files = []
    for pdf in sorted(NGPT_DIR.rglob("*.pdf")):
        # Skip OCR folders
        if any(skip in str(pdf) for skip in SKIP_DIRS):
            continue
        # Skip duplicates
        if pdf.stem.lower() in DUPLICATES:
            continue
        # Skip image-only
        if not is_text_extractable(pdf):
            logging.info(f"  Skipping (image-only): {pdf.name}")
            continue
        files.append(pdf)
    return files


def main():
    files = get_ingestable_files()
    print(f"\nFound {len(files)} new text-extractable PDFs to ingest\n")

    pipeline = IngestionPipeline(
        chunk_size=512,
        chunk_overlap=64,
        output_dir=PROJECT_ROOT / "data" / "processed",
    )

    all_chunks = []
    for f in files:
        chunks = pipeline.ingest_file(f)
        all_chunks.extend(chunks)

    # Save to a separate JSONL so we can add to vector store
    output = pipeline.output_dir / "ngpt_chunks.jsonl"
    import json
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

    print(f"\nDone! {len(all_chunks)} new chunks saved to {output}")
    print("Next: run 'python add_to_vector_store.py' to add these to the search index")


if __name__ == "__main__":
    main()
