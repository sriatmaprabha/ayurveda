"""Query engine that retrieves relevant chunks and formats context for LLM."""

import logging
from pathlib import Path

from src.embeddings.vector_store import VectorStore

logger = logging.getLogger(__name__)


class QueryEngine:
    """Retrieves relevant Ayurveda knowledge for a given question."""

    def __init__(self, vector_store: VectorStore, top_k: int = 5):
        self.vector_store = vector_store
        self.top_k = top_k

    def retrieve(self, question: str, top_k: int | None = None) -> list[dict]:
        """Retrieve the most relevant chunks for a question."""
        k = top_k or self.top_k
        results = self.vector_store.query(query_text=question, top_k=k)

        for r in results:
            # Convert distance to similarity score (cosine: lower distance = more similar)
            r["score"] = 1 - r["distance"] if r["distance"] is not None else 0

        return results

    def build_context(self, question: str, top_k: int | None = None) -> str:
        """Build a context string from retrieved chunks for LLM consumption."""
        results = self.retrieve(question, top_k)

        if not results:
            return "No relevant information found in the knowledge base."

        context_parts = []
        for i, r in enumerate(results, 1):
            source = r["metadata"].get("file_name", "Unknown")
            section = r["metadata"].get("section_title", "")
            score = r["score"]

            header = f"[Source {i}: {source}"
            if section:
                header += f" — {section}"
            header += f" (relevance: {score:.2f})]"

            # Trim each chunk to max 300 words to reduce LLM input size
            text = r["text"]
            words = text.split()
            if len(words) > 300:
                text = " ".join(words[:300]) + "..."
            context_parts.append(f"{header}\n{text}")

        return "\n\n---\n\n".join(context_parts)

    def answer_with_sources(self, question: str, top_k: int | None = None) -> dict:
        """Return structured result with context and source references."""
        results = self.retrieve(question, top_k)
        context = self.build_context(question, top_k)

        sources = []
        for r in results:
            sources.append({
                "file": r["metadata"].get("file_name", "Unknown"),
                "section": r["metadata"].get("section_title", ""),
                "type": r["metadata"].get("section_type", ""),
                "score": r["score"],
            })

        return {
            "question": question,
            "context": context,
            "sources": sources,
            "num_results": len(results),
        }
