"""Tests for the document ingestion pipeline."""

import tempfile
from pathlib import Path

from src.ingestion.base_parser import DocumentSection
from src.ingestion.csv_parser import CSVParser
from src.ingestion.md_parser import MarkdownParser
from src.ingestion.sql_parser import SQLParser
from src.ingestion.txt_parser import TxtParser
from src.ingestion.chunker import DocumentChunker


def test_csv_parser():
    parser = CSVParser()
    content = "name,description\nAsana1,A test asana\nAsana2,Another asana\n"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(content)
        f.flush()
        sections = parser.parse(Path(f.name))

    assert len(sections) == 2
    assert "Asana1" in sections[0].text


def test_md_parser():
    parser = MarkdownParser()
    content = "# Chapter 1\n\nSome text here.\n\n## Section 1.1\n\nMore text.\n"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(content)
        f.flush()
        sections = parser.parse(Path(f.name))

    assert len(sections) == 2
    assert "Chapter 1" in sections[0].section_title


def test_sql_parser():
    parser = SQLParser()
    content = """INSERT INTO asanas (english_name, sanskrit_name, description, goal_tags, difficulty_level, time_minutes, contraindications, sequence_stage, technique_instructions, benefits, image_url) VALUES (
        'Test Asana', 'Test Sanskrit', 'A test description', '["flexibility"]', 'beginner', 30, NULL, 'seated', 'Sit and relax', 'Improves flexibility', 'http://example.com/img.jpg'
    );"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
        f.write(content)
        f.flush()
        sections = parser.parse(Path(f.name))

    assert len(sections) == 1
    assert "Test Asana" in sections[0].text


def test_txt_parser():
    parser = TxtParser()
    content = "First paragraph with enough text to pass the minimum length threshold for splitting.\n\nSecond paragraph also with enough text to be meaningful on its own as a standalone section.\n"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(content)
        f.flush()
        sections = parser.parse(Path(f.name))

    assert len(sections) >= 1


def test_chunker():
    chunker = DocumentChunker(chunk_size=10, chunk_overlap=2)
    sections = [
        DocumentSection(
            text=" ".join(f"word{i}" for i in range(25)),
            metadata={"source_file": "test.txt"},
            source_file="test.txt",
            section_title="Test",
            section_type="test",
        )
    ]
    chunks = chunker.chunk(sections)
    assert len(chunks) > 1


if __name__ == "__main__":
    test_csv_parser()
    test_md_parser()
    test_sql_parser()
    test_txt_parser()
    test_chunker()
    print("All tests passed!")
