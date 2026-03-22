"""Interactive query test for the Ayurveda RAG retrieval system."""

import logging
from pathlib import Path

from src.embeddings import VectorStore
from src.retrieval import QueryEngine

logging.basicConfig(level=logging.WARNING)

PROJECT_ROOT = Path(__file__).parent


def main():
    store = VectorStore(
        persist_dir=PROJECT_ROOT / "data" / "vector_store",
        collection_name="ayurveda_knowledge",
    )

    if store.count == 0:
        print("Vector store is empty. Run 'python build_vector_store.py' first.")
        return

    engine = QueryEngine(vector_store=store, top_k=5)

    print(f"Ayurveda Knowledge Base — {store.count} chunks indexed")
    print("Type your question (or 'quit' to exit):\n")

    while True:
        question = input("Q: ").strip()
        if not question or question.lower() in ("quit", "exit", "q"):
            break

        result = engine.answer_with_sources(question)

        print(f"\n{'='*60}")
        print(f"Found {result['num_results']} relevant sources:\n")

        for i, source in enumerate(result["sources"], 1):
            print(f"  {i}. {source['file']} — {source['section']} "
                  f"(score: {source['score']:.2f})")

        print(f"\n{'─'*60}")
        print("Context retrieved:\n")
        print(result["context"][:2000])
        if len(result["context"]) > 2000:
            print(f"\n... ({len(result['context'])} chars total)")
        print(f"\n{'='*60}\n")


if __name__ == "__main__":
    main()
