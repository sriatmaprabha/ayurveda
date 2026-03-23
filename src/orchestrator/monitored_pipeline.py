"""Monitored RAG pipeline — wraps the base pipeline with quality monitoring."""

import logging
from pathlib import Path

from src.generation import LLMConfig
from src.embeddings import VectorStore
from src.retrieval import QueryEngine
from src.generation import LLMClient, AnswerGenerator
from .monitor import PipelineMonitor

logger = logging.getLogger(__name__)


class MonitoredRAGPipeline:
    """RAG pipeline with integrated quality monitoring."""

    def __init__(
        self,
        vector_store_dir: str | Path = "data/vector_store",
        llm_config: LLMConfig | None = None,
        monitor_model: str = "mistral",
        monitor_base_url: str = "http://localhost:11434/v1",
        enable_monitoring: bool = True,
        top_k: int = 5,
        log_file: str = "data/pipeline_logs.jsonl",
    ):
        # Core RAG components
        self.store = VectorStore(persist_dir=vector_store_dir)
        self.query_engine = QueryEngine(vector_store=self.store, top_k=top_k)

        llm_config = llm_config or LLMConfig()
        self.llm_client = LLMClient(llm_config)
        self.generator = AnswerGenerator(llm_client=self.llm_client)

        # Monitor
        self.monitor = PipelineMonitor(
            base_url=monitor_base_url,
            model=monitor_model,
            enable_llm_eval=enable_monitoring,
            log_file=log_file,
        )

        logger.info(
            f"Monitored RAG pipeline ready — "
            f"{self.store.count} chunks, "
            f"LLM: {llm_config.model}, "
            f"Monitor: {monitor_model}"
        )

    def ask(self, question: str, top_k: int | None = None, evaluate: bool = True) -> dict:
        """Ask a question with full monitoring."""
        start = self.monitor.start_timer()

        # Retrieve
        retrieval = self.query_engine.answer_with_sources(question, top_k)
        context = retrieval["context"]

        # Generate with asana context
        asana_context = retrieval.get("asana_context", "")
        generation = self.generator.generate_answer(question, context, asana_context)

        latency_ms = self.monitor.end_timer(start)

        result = {
            "question": question,
            "answer": generation.get("answer"),
            "error": generation.get("error"),
            "sources": retrieval["sources"],
            "model": generation.get("model"),
            "num_sources": retrieval["num_results"],
            "latency_ms": round(latency_ms, 2),
        }

        # Log
        log = self.monitor.log_query(question, result, latency_ms)

        # Evaluate (if answer was generated and evaluation requested)
        if evaluate and result["answer"] and not result["error"]:
            evaluation = self.monitor.evaluate_response(
                question=question,
                context=context,
                answer=result["answer"],
            )
            log.evaluation = evaluation
            result["evaluation"] = evaluation

        return result

    def get_stats(self) -> dict:
        return self.monitor.get_stats()

    def check_status(self) -> dict:
        return {
            "vector_store": {
                "status": "ok" if self.store.count > 0 else "empty",
                "chunks": self.store.count,
            },
            "answer_llm": {
                "status": "ok" if self.llm_client.is_available() else "unavailable",
                "model": self.llm_client.config.model,
            },
            "monitor_llm": {
                "status": "ok" if self.monitor.is_available() else "unavailable",
                "model": self.monitor.model,
            },
        }
