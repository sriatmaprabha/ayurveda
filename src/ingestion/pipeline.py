"""Main ingestion pipeline — scans directories, parses, chunks, and outputs processed docs."""

import json
import logging
from pathlib import Path

from .base_parser import BaseParser, DocumentSection
from .pdf_parser import PDFParser
from .csv_parser import CSVParser
from .md_parser import MarkdownParser
from .sql_parser import SQLParser
from .txt_parser import TxtParser
from .chunker import DocumentChunker

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """Orchestrates document ingestion: parse → chunk → save."""

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
        output_dir: str | Path = "data/processed",
    ):
        self.parsers: list[BaseParser] = [
            PDFParser(),
            CSVParser(),
            MarkdownParser(),
            SQLParser(),
            TxtParser(),
        ]
        self.chunker = DocumentChunker(chunk_size, chunk_overlap)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _get_parser(self, file_path: Path) -> BaseParser | None:
        for parser in self.parsers:
            if parser.can_parse(file_path):
                return parser
        return None

    def ingest_file(self, file_path: str | Path) -> list[DocumentSection]:
        """Parse and chunk a single file."""
        file_path = Path(file_path)
        parser = self._get_parser(file_path)

        if parser is None:
            logger.warning(f"No parser found for {file_path}")
            return []

        logger.info(f"Parsing {file_path.name} with {parser.__class__.__name__}")

        try:
            sections = parser.parse(file_path)
        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            return []

        chunks = self.chunker.chunk(sections)
        logger.info(f"  → {len(sections)} sections → {len(chunks)} chunks")
        return chunks

    def ingest_directory(self, dir_path: str | Path) -> list[DocumentSection]:
        """Parse and chunk all supported files in a directory (recursive)."""
        dir_path = Path(dir_path)
        all_chunks = []

        supported = {ext for p in self.parsers for ext in p.supported_extensions}
        files = sorted(
            f for f in dir_path.rglob("*") if f.is_file() and f.suffix.lower() in supported
        )

        logger.info(f"Found {len(files)} supported files in {dir_path}")

        for file_path in files:
            chunks = self.ingest_file(file_path)
            all_chunks.extend(chunks)

        logger.info(f"Total: {len(all_chunks)} chunks from {len(files)} files")
        return all_chunks

    def save_chunks(self, chunks: list[DocumentSection], filename: str = "chunks.jsonl"):
        """Save processed chunks to a JSONL file."""
        output_path = self.output_dir / filename

        with open(output_path, "w", encoding="utf-8") as f:
            for chunk in chunks:
                record = {
                    "text": chunk.text,
                    "metadata": chunk.metadata,
                    "source_file": chunk.source_file,
                    "section_title": chunk.section_title,
                    "section_type": chunk.section_type,
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

        logger.info(f"Saved {len(chunks)} chunks to {output_path}")
        return output_path

    def run(self, input_paths: list[str | Path]) -> Path:
        """Full pipeline: ingest all paths → chunk → save."""
        all_chunks = []

        for path in input_paths:
            path = Path(path)
            if path.is_dir():
                all_chunks.extend(self.ingest_directory(path))
            elif path.is_file():
                all_chunks.extend(self.ingest_file(path))
            else:
                logger.warning(f"Path not found: {path}")

        return self.save_chunks(all_chunks)
