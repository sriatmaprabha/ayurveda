"""Smart chunker that splits document sections into retrieval-friendly chunks."""

from .base_parser import DocumentSection


class DocumentChunker:
    """Splits large sections into overlapping chunks for better retrieval."""

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 64):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, sections: list[DocumentSection]) -> list[DocumentSection]:
        """Split sections into chunks. Small sections pass through unchanged."""
        chunks = []
        for section in sections:
            words = section.text.split()

            if len(words) <= self.chunk_size:
                chunks.append(section)
                continue

            # Split into overlapping chunks
            for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
                chunk_words = words[i : i + self.chunk_size]
                if not chunk_words:
                    break

                chunk_index = i // (self.chunk_size - self.chunk_overlap)
                metadata = {**section.metadata, "chunk_index": chunk_index}

                chunks.append(DocumentSection(
                    text=" ".join(chunk_words),
                    metadata=metadata,
                    source_file=section.source_file,
                    section_title=section.section_title,
                    section_type=section.section_type,
                ))

        return chunks
