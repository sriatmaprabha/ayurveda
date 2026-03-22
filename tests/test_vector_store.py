"""Tests for vector store and query engine."""

import json
import tempfile
from pathlib import Path

from src.embeddings.vector_store import VectorStore
from src.retrieval.query_engine import QueryEngine


def test_vector_store_add_and_query():
    """Test adding chunks and querying the vector store."""
    tmpdir = tempfile.mkdtemp()

    # Create test chunks
    chunks_file = Path(tmpdir) / "test_chunks.jsonl"
    test_data = [
        {
            "text": "Triphala is an Ayurvedic herbal formulation consisting of three fruits: Amalaki, Bibhitaki, and Haritaki.",
            "metadata": {"file_name": "test.md", "file_type": ".md"},
            "source_file": "test.md",
            "section_title": "Triphala",
            "section_type": "section",
        },
        {
            "text": "Padmasana is a cross-legged sitting meditation pose used in yoga and Ayurveda practice.",
            "metadata": {"file_name": "asanas.sql", "file_type": ".sql"},
            "source_file": "asanas.sql",
            "section_title": "Padmasana",
            "section_type": "asana",
        },
        {
            "text": "Vata dosha is composed of air and ether elements. It governs movement in the body.",
            "metadata": {"file_name": "charaka.md", "file_type": ".md"},
            "source_file": "charaka.md",
            "section_title": "Vata Dosha",
            "section_type": "section",
        },
    ]

    with open(chunks_file, "w") as f:
        for record in test_data:
            f.write(json.dumps(record) + "\n")

    # Build store
    store = VectorStore(
        persist_dir=Path(tmpdir) / "vector_store",
        collection_name="test_collection",
    )
    added = store.add_chunks(chunks_file)
    assert added == 3
    assert store.count == 3

    # Query
    results = store.query("What is Triphala?", top_k=2)
    assert len(results) == 2
    assert "Triphala" in results[0]["text"]

    # Query engine
    engine = QueryEngine(vector_store=store, top_k=2)
    result = engine.answer_with_sources("meditation pose")
    assert result["num_results"] == 2
    assert any("Padmasana" in s["section"] for s in result["sources"])


def test_vector_store_empty():
    """Test querying an empty store."""
    tmpdir = tempfile.mkdtemp()

    store = VectorStore(
        persist_dir=Path(tmpdir) / "vector_store",
        collection_name="empty_test",
    )
    assert store.count == 0

    engine = QueryEngine(vector_store=store, top_k=3)
    context = engine.build_context("anything")
    assert "No relevant information" in context


if __name__ == "__main__":
    test_vector_store_add_and_query()
    test_vector_store_empty()
    print("All vector store tests passed!")
