"""Full RAG pipeline: query → retrieve → generate → respond."""

import logging
from pathlib import Path

from src.embeddings import VectorStore
from src.retrieval import QueryEngine
from src.generation import LLMClient, LLMConfig, AnswerGenerator

logger = logging.getLogger(__name__)


class RAGPipeline:
    """End-to-end Retrieval-Augmented Generation pipeline for Ayurveda."""

    def __init__(
        self,
        vector_store_dir: str | Path = "data/vector_store",
        llm_config: LLMConfig | None = None,
        top_k: int = 5,
    ):
        self.store = VectorStore(persist_dir=vector_store_dir)
        self.query_engine = QueryEngine(vector_store=self.store, top_k=top_k)

        self.llm_config = llm_config or LLMConfig()
        self.llm_client = LLMClient(self.llm_config)
        self.generator = AnswerGenerator(llm_client=self.llm_client)

        logger.info(
            f"RAG pipeline initialized — "
            f"{self.store.count} chunks indexed, "
            f"LLM: {self.llm_config.model} @ {self.llm_config.base_url}"
        )

    def ask(self, question: str, top_k: int | None = None) -> dict:
        """Ask a question and get a grounded answer with sources."""
        # Step 1: Retrieve relevant context
        retrieval = self.query_engine.answer_with_sources(question, top_k)
        context = retrieval["context"]
        sources = retrieval["sources"]

        # Step 2: Generate answer with asana context
        asana_context = retrieval.get("asana_context", "")
        generation = self.generator.generate_answer(question, context, asana_context)

        return {
            "question": question,
            "answer": generation.get("answer"),
            "error": generation.get("error"),
            "sources": sources,
            "model": generation.get("model"),
            "num_sources": retrieval["num_results"],
        }

    def summarize(self, topic: str, top_k: int | None = None) -> dict:
        """Get a summary about a topic from the knowledge base."""
        retrieval = self.query_engine.answer_with_sources(topic, top_k)
        context = retrieval["context"]

        generation = self.generator.summarize(topic, context)

        return {
            "topic": topic,
            "summary": generation.get("summary"),
            "error": generation.get("error"),
            "sources": retrieval["sources"],
            "model": generation.get("model"),
        }

    def check_status(self) -> dict:
        """Check the health of all pipeline components."""
        return {
            "vector_store": {
                "status": "ok" if self.store.count > 0 else "empty",
                "chunks": self.store.count,
            },
            "llm": {
                "status": "ok" if self.llm_client.is_available() else "unavailable",
                "model": self.llm_config.model,
                "base_url": self.llm_config.base_url,
                "available_models": self.llm_client.list_models(),
            },
        }
