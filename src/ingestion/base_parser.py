"""Base parser interface for all document types."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DocumentSection:
    """A single section extracted from a document."""
    text: str
    metadata: dict = field(default_factory=dict)
    source_file: str = ""
    section_title: str = ""
    section_type: str = ""  # e.g., "asana", "condition", "chapter", "verse"


class BaseParser(ABC):
    """Base class for all document parsers."""

    supported_extensions: list[str] = []

    def can_parse(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in self.supported_extensions

    @abstractmethod
    def parse(self, file_path: Path) -> list[DocumentSection]:
        """Parse a file and return a list of document sections."""
        ...

    def _base_metadata(self, file_path: Path) -> dict:
        return {
            "source_file": str(file_path),
            "file_name": file_path.name,
            "file_type": file_path.suffix.lower(),
        }
