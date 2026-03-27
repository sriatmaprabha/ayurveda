"""Extract book-wise JSONL datasets into data/books/ folder.
Each book gets its own JSONL file with all chunks from that source."""

import json
import os
import re
import logging
from pathlib import Path
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

PROJECT_ROOT = Path(__file__).parent
BOOKS_DIR = PROJECT_ROOT / "data" / "books"
BOOKS_DIR.mkdir(parents=True, exist_ok=True)

CHUNK_FILES = [
    PROJECT_ROOT / "data" / "processed" / "chunks.jsonl",
    PROJECT_ROOT / "data" / "processed" / "ngpt_chunks.jsonl",
    PROJECT_ROOT / "data" / "processed" / "ocr_chunks.jsonl",
    PROJECT_ROOT / "data" / "processed" / "parmesha_chunks.jsonl",
]


def normalize_book_name(source_file: str) -> str:
    """Convert a source file path to a clean book name for the filename."""
    name = os.path.basename(str(source_file))

    # Remove _part_N suffixes (Parmesha multi-part books)
    name = re.sub(r'_part_\d+(\(\d+\))?\.md$', '.md', name)

    # Remove extensions for the folder name
    base = name
    for ext in ['.pdf.oneocr.txt', '.oneocr.txt', '.csv', '.md', '.pdf', '.txt', '.sql']:
        if base.lower().endswith(ext):
            base = base[:-len(ext)]
            break

    # Clean up the name for filesystem
    base = re.sub(r'[<>:"/\\|?*]', '', base)  # Remove invalid filename chars
    base = re.sub(r'\s+', '_', base.strip())    # Spaces to underscores
    base = re.sub(r'_+', '_', base)             # Collapse multiple underscores
    base = base.strip('_.')

    return base[:120]  # Cap length


def main():
    logging.info("Extracting book-wise JSONL datasets")
    logging.info(f"Output: {BOOKS_DIR}")

    # Group all records by normalized book name
    books = defaultdict(list)
    total = 0

    for chunk_file in CHUNK_FILES:
        if not chunk_file.exists():
            logging.info(f"Skipping {chunk_file.name} (not found)")
            continue

        logging.info(f"Reading {chunk_file.name}...")
        with open(chunk_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue

                total += 1

                # Get source file
                src = rec.get("metadata", {}).get("file_name", "")
                if not src:
                    src = rec.get("source_file", "")
                if not src:
                    src = "unknown"

                book_name = normalize_book_name(src)
                books[book_name].append(rec)

    logging.info(f"\nTotal records: {total}")
    logging.info(f"Unique books: {len(books)}")

    # Write each book to its own JSONL
    summary = []
    for book_name, records in sorted(books.items()):
        output_path = BOOKS_DIR / f"{book_name}.jsonl"

        with open(output_path, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

        size_kb = output_path.stat().st_size / 1024
        summary.append({
            "book": book_name,
            "chunks": len(records),
            "file": str(output_path.name),
            "size_kb": round(size_kb, 1),
        })

        if len(records) >= 100:
            logging.info(f"  {book_name}: {len(records)} chunks ({size_kb:.0f} KB)")

    # Write summary index
    summary.sort(key=lambda x: x["chunks"], reverse=True)
    summary_path = BOOKS_DIR / "_book_index.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({
            "total_books": len(summary),
            "total_chunks": total,
            "books": summary,
        }, f, ensure_ascii=False, indent=2)

    logging.info(f"\nDone! {len(summary)} book files written to {BOOKS_DIR}")
    logging.info(f"Index: {summary_path}")

    # Print top 30
    logging.info("\nTop 30 books by chunk count:")
    for s in summary[:30]:
        logging.info(f"  {s['chunks']:5d} chunks | {s['size_kb']:7.0f} KB | {s['book']}")


if __name__ == "__main__":
    main()
