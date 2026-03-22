"""Pipeline monitor using Mistral/Kimi K2 for operation oversight and quality control."""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

MONITOR_SYSTEM_PROMPT = """You are a quality control monitor for an Ayurveda RAG system.
Your job is to evaluate whether the system's responses are:
1. Grounded in the provided sources (no hallucination)
2. Relevant to the user's question
3. Safe — no dangerous medical advice without disclaimers
4. Complete — using available context effectively

Respond with a JSON object:
{
  "quality_score": 0.0 to 1.0,
  "is_grounded": true/false,
  "is_safe": true/false,
  "issues": ["list of any issues found"],
  "suggestion": "optional improvement suggestion"
}"""

EVALUATION_PROMPT = """Evaluate this RAG interaction:

Question: {question}

Retrieved Context (from knowledge base):
{context}

Generated Answer:
{answer}

Check for: hallucination, relevance, safety, completeness. Return JSON only."""


@dataclass
class QueryLog:
    """Log entry for a single query through the pipeline."""
    query_id: str
    timestamp: str
    question: str
    num_sources: int
    source_files: list[str]
    model: str
    latency_ms: float
    evaluation: dict | None = None
    error: str | None = None


class PipelineMonitor:
    """Monitors and evaluates RAG pipeline operations."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434/v1",
        model: str = "mistral",
        api_key: str = "ollama",
        enable_llm_eval: bool = True,
        log_file: str = "data/pipeline_logs.jsonl",
    ):
        self.base_url = base_url
        self.model = model
        self.api_key = api_key
        self.enable_llm_eval = enable_llm_eval
        self.log_file = log_file
        self._client = httpx.Client(timeout=60.0)
        self._query_count = 0
        self._error_count = 0
        self._total_latency = 0.0
        self._logs: list[QueryLog] = []

    def start_timer(self) -> float:
        return time.perf_counter()

    def end_timer(self, start: float) -> float:
        return (time.perf_counter() - start) * 1000  # ms

    def log_query(
        self,
        question: str,
        result: dict,
        latency_ms: float,
    ) -> QueryLog:
        """Log a query and its result."""
        self._query_count += 1
        self._total_latency += latency_ms

        if result.get("error"):
            self._error_count += 1

        log = QueryLog(
            query_id=f"q_{self._query_count:06d}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            question=question,
            num_sources=result.get("num_sources", 0),
            source_files=[s.get("file", "") for s in result.get("sources", [])],
            model=result.get("model", "unknown"),
            latency_ms=round(latency_ms, 2),
            error=result.get("error"),
        )

        self._logs.append(log)
        self._persist_log(log)

        return log

    def evaluate_response(
        self,
        question: str,
        context: str,
        answer: str,
    ) -> dict:
        """Use the monitor LLM to evaluate a response for quality."""
        if not self.enable_llm_eval:
            return {"skipped": True, "reason": "LLM evaluation disabled"}

        prompt = EVALUATION_PROMPT.format(
            question=question,
            context=context[:2000],
            answer=answer,
        )

        try:
            url = f"{self.base_url}/chat/completions"
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": MONITOR_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.1,
                "max_tokens": 512,
            }
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            }

            response = self._client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]

            # Parse JSON from response
            try:
                evaluation = json.loads(content)
            except json.JSONDecodeError:
                # Try to extract JSON from markdown code block
                if "```" in content:
                    json_str = content.split("```")[1].strip()
                    if json_str.startswith("json"):
                        json_str = json_str[4:].strip()
                    evaluation = json.loads(json_str)
                else:
                    evaluation = {"raw_response": content, "parse_error": True}

            return evaluation

        except httpx.ConnectError:
            return {"error": "Monitor LLM not available", "skipped": True}
        except Exception as e:
            logger.warning(f"Evaluation failed: {e}")
            return {"error": str(e), "skipped": True}

    def get_stats(self) -> dict:
        """Get pipeline statistics."""
        avg_latency = self._total_latency / self._query_count if self._query_count > 0 else 0

        evaluated = [l for l in self._logs if l.evaluation and not l.evaluation.get("skipped")]
        avg_quality = 0.0
        if evaluated:
            scores = [l.evaluation.get("quality_score", 0) for l in evaluated]
            avg_quality = sum(scores) / len(scores)

        return {
            "total_queries": self._query_count,
            "total_errors": self._error_count,
            "error_rate": self._error_count / self._query_count if self._query_count > 0 else 0,
            "avg_latency_ms": round(avg_latency, 2),
            "avg_quality_score": round(avg_quality, 3),
            "evaluated_queries": len(evaluated),
        }

    def _persist_log(self, log: QueryLog):
        """Append a log entry to the log file."""
        try:
            from pathlib import Path
            Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_file, "a", encoding="utf-8") as f:
                entry = {
                    "query_id": log.query_id,
                    "timestamp": log.timestamp,
                    "question": log.question,
                    "num_sources": log.num_sources,
                    "source_files": log.source_files,
                    "model": log.model,
                    "latency_ms": log.latency_ms,
                    "error": log.error,
                    "evaluation": log.evaluation,
                }
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning(f"Failed to persist log: {e}")

    def is_available(self) -> bool:
        try:
            url = f"{self.base_url}/models"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = self._client.get(url, headers=headers)
            return response.status_code == 200
        except Exception:
            return False

    def close(self):
        self._client.close()
