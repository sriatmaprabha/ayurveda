"""Parser for Markdown files (Ayurveda texts converted to markdown)."""

import re
from pathlib import Path

from .base_parser import BaseParser, DocumentSection


class MarkdownParser(BaseParser):
    """Splits markdown files by headings into sections."""

    supported_extensions = [".md"]

    def parse(self, file_path: Path) -> list[DocumentSection]:
        file_path = Path(file_path)

        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        if not content.strip():
            return []

        # Split by markdown headings (## or ### level)
        heading_pattern = re.compile(r"^(#{1,4})\s+(.+)$", re.MULTILINE)
        matches = list(heading_pattern.finditer(content))

        sections = []

        if not matches:
            # No headings — treat entire file as one section
            metadata = self._base_metadata(file_path)
            sections.append(DocumentSection(
                text=content.strip(),
                metadata=metadata,
                source_file=str(file_path),
                section_title=file_path.stem,
                section_type="full_document",
            ))
            return sections

        # Text before first heading
        preamble = content[:matches[0].start()].strip()
        if preamble:
            metadata = self._base_metadata(file_path)
            metadata["heading_level"] = 0
            sections.append(DocumentSection(
                text=preamble,
                metadata=metadata,
                source_file=str(file_path),
                section_title="Preamble",
                section_type="preamble",
            ))

        # Each heading section
        for i, match in enumerate(matches):
            heading_level = len(match.group(1))
            heading_text = match.group(2).strip()
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            body = content[start:end].strip()

            if not body:
                continue

            metadata = self._base_metadata(file_path)
            metadata["heading_level"] = heading_level

            sections.append(DocumentSection(
                text=f"{heading_text}\n\n{body}",
                metadata=metadata,
                source_file=str(file_path),
                section_title=heading_text,
                section_type="section",
            ))

        return sections
