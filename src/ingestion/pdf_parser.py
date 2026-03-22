"""Parser for PDF documents (Ayurveda texts, Sushruta Samhita, etc.)."""

from pathlib import Path

from .base_parser import BaseParser, DocumentSection


class PDFParser(BaseParser):
    """Extracts text from PDF files page by page."""

    supported_extensions = [".pdf"]

    def parse(self, file_path: Path) -> list[DocumentSection]:
        import pymupdf

        file_path = Path(file_path)
        sections = []

        doc = pymupdf.open(str(file_path))
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text().strip()
            if not text:
                continue

            metadata = self._base_metadata(file_path)
            metadata["page_number"] = page_num
            metadata["total_pages"] = len(doc)

            sections.append(DocumentSection(
                text=text,
                metadata=metadata,
                source_file=str(file_path),
                section_title=f"Page {page_num}",
                section_type="page",
            ))

        doc.close()
        return sections
