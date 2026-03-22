"""Run the document ingestion pipeline on all Ayurveda source documents."""

import logging
from pathlib import Path

from src.ingestion import IngestionPipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

PROJECT_ROOT = Path(__file__).parent


def main():
    pipeline = IngestionPipeline(
        chunk_size=512,
        chunk_overlap=64,
        output_dir=PROJECT_ROOT / "data" / "processed",
    )

    input_paths = [
        PROJECT_ROOT / "knowledge_base",
        PROJECT_ROOT / "insert_asanas.sql",
        PROJECT_ROOT / "asana_recommendations.csv",
    ]

    existing = [p for p in input_paths if p.exists()]
    if not existing:
        logging.error("No input paths found. Check your data directories.")
        return

    output_path = pipeline.run(existing)
    print(f"\nDone! Processed chunks saved to: {output_path}")


if __name__ == "__main__":
    main()
