"""Parser for plain text files (Sushruta Samhita volumes, etc.)."""

import re
from pathlib import Path

from .base_parser import BaseParser, DocumentSection


class TxtParser(BaseParser):
    """Splits text files into sections by blank-line-separated paragraphs or chapter markers."""

    supported_extensions = [".txt"]

    # Common chapter/section patterns in Ayurveda texts
    CHAPTER_PATTERNS = [
        re.compile(r"^(CHAPTER|Chapter|SECTION|Section|BOOK|Book)\s+[\dIVXLCDM]+", re.MULTILINE),
        re.compile(r"^(Adhyaya|ADHYAYA|Sthana|STHANA)\s+[\dIVXLCDM]+", re.MULTILINE),
    ]

    def parse(self, file_path: Path) -> list[DocumentSection]:
        file_path = Path(file_path)

        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        if not content.strip():
            return []

        # Try to split by chapter markers first
        for pattern in self.CHAPTER_PATTERNS:
            matches = list(pattern.finditer(content))
            if matches:
                return self._split_by_matches(content, matches, file_path)

        # Fall back to paragraph-based splitting
        return self._split_by_paragraphs(content, file_path)

    def _split_by_matches(
        self, content: str, matches: list, file_path: Path
    ) -> list[DocumentSection]:
        sections = []

        for i, match in enumerate(matches):
            title = match.group(0).strip()
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            text = content[start:end].strip()

            if not text:
                continue

            metadata = self._base_metadata(file_path)
            metadata["chapter_index"] = i + 1

            sections.append(DocumentSection(
                text=text,
                metadata=metadata,
                source_file=str(file_path),
                section_title=title,
                section_type="chapter",
            ))

        return sections

    def _split_by_paragraphs(
        self, content: str, file_path: Path, min_length: int = 100
    ) -> list[DocumentSection]:
        """Split by double newlines, merging short paragraphs."""
        raw_paragraphs = re.split(r"\n\s*\n", content)
        sections = []
        buffer = ""

        for para in raw_paragraphs:
            para = para.strip()
            if not para:
                continue

            buffer = f"{buffer}\n\n{para}".strip() if buffer else para

            if len(buffer) >= min_length:
                metadata = self._base_metadata(file_path)
                metadata["paragraph_index"] = len(sections) + 1

                sections.append(DocumentSection(
                    text=buffer,
                    metadata=metadata,
                    source_file=str(file_path),
                    section_title=buffer[:80].replace("\n", " "),
                    section_type="paragraph",
                ))
                buffer = ""

        # Remaining buffer
        if buffer.strip():
            metadata = self._base_metadata(file_path)
            metadata["paragraph_index"] = len(sections) + 1
            sections.append(DocumentSection(
                text=buffer,
                metadata=metadata,
                source_file=str(file_path),
                section_title=buffer[:80].replace("\n", " "),
                section_type="paragraph",
            ))

        return sections
