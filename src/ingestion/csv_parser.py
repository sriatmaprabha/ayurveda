"""Parser for CSV files (asana recommendations, food guidelines, samhita extracts)."""

import csv
import sys
from pathlib import Path

# Some Ayurveda texts have very large fields
csv.field_size_limit(sys.maxsize)

from .base_parser import BaseParser, DocumentSection


class CSVParser(BaseParser):
    """Parses CSV files into document sections, one per row."""

    supported_extensions = [".csv"]

    def parse(self, file_path: Path) -> list[DocumentSection]:
        file_path = Path(file_path)
        sections = []

        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            # Sniff dialect for flexible CSV handling
            sample = f.read(4096)
            f.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample)
            except csv.Error:
                dialect = csv.excel

            reader = csv.reader(f, dialect)
            rows = list(reader)

        if not rows:
            return sections

        # Use first row as headers if it looks like a header
        headers = rows[0] if rows[0] and not rows[0][0].isdigit() else None
        data_rows = rows[1:] if headers else rows

        for row_idx, row in enumerate(data_rows, start=1):
            # Skip empty rows
            if not any(cell.strip() for cell in row):
                continue

            # Build text from row
            if headers:
                parts = []
                for header, value in zip(headers, row):
                    value = value.strip()
                    if value and value.lower() != "none":
                        header_clean = header.strip()
                        if header_clean:
                            parts.append(f"{header_clean}: {value}")
                        else:
                            parts.append(value)
                text = "\n".join(parts)
            else:
                text = " | ".join(cell.strip() for cell in row if cell.strip())

            if not text.strip():
                continue

            # Try to extract a title from the row
            title = ""
            if len(row) > 1 and row[1].strip():
                title = row[1].strip()
            elif row[0].strip():
                title = row[0].strip()

            metadata = self._base_metadata(file_path)
            metadata["row_number"] = row_idx

            sections.append(DocumentSection(
                text=text,
                metadata=metadata,
                source_file=str(file_path),
                section_title=title[:100],
                section_type="row",
            ))

        return sections
