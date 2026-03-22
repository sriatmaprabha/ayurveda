"""Tests for the pipeline monitor."""

from src.orchestrator.monitor import PipelineMonitor, QueryLog


def test_monitor_logging():
    monitor = PipelineMonitor(enable_llm_eval=False, log_file="data/test_logs.jsonl")

    result = {
        "answer": "Triphala is a herbal formulation.",
        "error": None,
        "sources": [{"file": "charaka.md", "section": "Triphala", "score": 0.9}],
        "model": "llama3",
        "num_sources": 1,
    }

    log = monitor.log_query("What is Triphala?", result, latency_ms=150.5)

    assert log.query_id == "q_000001"
    assert log.question == "What is Triphala?"
    assert log.latency_ms == 150.5
    assert log.num_sources == 1


def test_monitor_stats():
    monitor = PipelineMonitor(enable_llm_eval=False, log_file="data/test_logs2.jsonl")

    for i in range(3):
        result = {"error": None, "sources": [], "model": "test", "num_sources": 0}
        monitor.log_query(f"question {i}", result, latency_ms=100.0 + i * 10)

    stats = monitor.get_stats()
    assert stats["total_queries"] == 3
    assert stats["total_errors"] == 0
    assert stats["avg_latency_ms"] > 0


def test_monitor_error_tracking():
    monitor = PipelineMonitor(enable_llm_eval=False, log_file="data/test_logs3.jsonl")

    monitor.log_query("q1", {"error": "timeout", "sources": [], "model": "test", "num_sources": 0}, 500)
    monitor.log_query("q2", {"error": None, "sources": [], "model": "test", "num_sources": 0}, 100)

    stats = monitor.get_stats()
    assert stats["total_errors"] == 1
    assert stats["error_rate"] == 0.5


def test_evaluate_when_offline():
    monitor = PipelineMonitor(
        base_url="http://localhost:99999/v1",
        enable_llm_eval=True,
        log_file="data/test_logs4.jsonl",
    )
    result = monitor.evaluate_response("question", "context", "answer")
    assert result.get("skipped") is True


if __name__ == "__main__":
    test_monitor_logging()
    test_monitor_stats()
    test_monitor_error_tracking()
    test_evaluate_when_offline()
    print("All monitor tests passed!")
