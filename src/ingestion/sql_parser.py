"""Parser for SQL files (asana insert statements)."""

import re
from pathlib import Path

from .base_parser import BaseParser, DocumentSection


class SQLParser(BaseParser):
    """Extracts individual INSERT records from SQL files."""

    supported_extensions = [".sql"]

    def parse(self, file_path: Path) -> list[DocumentSection]:
        file_path = Path(file_path)

        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        sections = []

        # Extract INSERT statements
        insert_pattern = re.compile(
            r"INSERT\s+INTO\s+(\w+)\s*\([^)]+\)\s*VALUES\s*\((.*?)\);",
            re.DOTALL | re.IGNORECASE,
        )

        for match in insert_pattern.finditer(content):
            table_name = match.group(1)
            values_str = match.group(2)

            # Extract quoted string values
            values = re.findall(r"'((?:[^'\\]|\\.)*)'", values_str)

            if not values:
                continue

            # For asanas table, build structured text
            if table_name.lower() == "asanas" and len(values) >= 8:
                text_parts = [
                    f"Name: {values[0]}",
                    f"Sanskrit: {values[1]}",
                    f"Description: {values[2]}",
                    f"Difficulty: {values[4]}" if len(values) > 4 else "",
                    f"Stage: {values[7]}" if len(values) > 7 else "",
                    f"Instructions: {values[8]}" if len(values) > 8 else "",
                    f"Benefits: {values[9]}" if len(values) > 9 else "",
                ]
                text = "\n".join(p for p in text_parts if p)
                title = values[0]
                section_type = "asana"
            else:
                text = " | ".join(values)
                title = values[0] if values else ""
                section_type = "record"

            metadata = self._base_metadata(file_path)
            metadata["table_name"] = table_name

            sections.append(DocumentSection(
                text=text,
                metadata=metadata,
                source_file=str(file_path),
                section_title=title,
                section_type=section_type,
            ))

        return sections
