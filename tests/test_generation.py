"""Tests for the generation module."""

from unittest.mock import patch, MagicMock

from src.generation.llm_client import LLMClient, LLMConfig
from src.generation.answer_generator import AnswerGenerator
from src.generation.prompts import SYSTEM_PROMPT, QUERY_TEMPLATE


def test_llm_config_defaults():
    config = LLMConfig()
    assert config.base_url == "http://localhost:11434/v1"
    assert config.model == "llama3"
    assert config.temperature == 0.3


def test_query_template_formatting():
    context = "Triphala is a herbal formulation."
    question = "What is Triphala?"
    prompt = QUERY_TEMPLATE.format(context=context, asana_context="Padmasana: sit cross-legged", question=question)
    assert "Triphala is a herbal formulation" in prompt
    assert "What is Triphala?" in prompt
    assert "Padmasana" in prompt


def test_answer_generator_with_mock_llm():
    """Test answer generation with a mocked LLM response."""
    mock_client = MagicMock(spec=LLMClient)
    mock_client.config = LLMConfig()
    mock_client.generate.return_value = (
        "Triphala is a classical Ayurvedic formulation [Source 1]."
    )

    generator = AnswerGenerator(llm_client=mock_client)
    result = generator.generate_answer(
        question="What is Triphala?",
        context="[Source 1: charaka.md]\nTriphala is a combination of three fruits.",
    )

    assert result["answer"] is not None
    assert "Triphala" in result["answer"]
    assert result["error"] is None
    mock_client.generate.assert_called_once()


def test_answer_generator_connection_error():
    """Test graceful handling when LLM is unavailable."""
    mock_client = MagicMock(spec=LLMClient)
    mock_client.config = LLMConfig()
    mock_client.generate.side_effect = ConnectionError("LLM not available")

    generator = AnswerGenerator(llm_client=mock_client)
    result = generator.generate_answer(
        question="What is Triphala?",
        context="Some context.",
    )

    assert result["answer"] is None
    assert result["error"] is not None
    assert "not available" in result["error"]


def test_summarize_with_mock_llm():
    mock_client = MagicMock(spec=LLMClient)
    mock_client.config = LLMConfig()
    mock_client.generate.return_value = "Vata governs movement in the body."

    generator = AnswerGenerator(llm_client=mock_client)
    result = generator.summarize(
        topic="Vata dosha",
        context="[Source 1]\nVata is composed of air and ether.",
    )

    assert result["summary"] is not None
    assert result["error"] is None


if __name__ == "__main__":
    test_llm_config_defaults()
    test_query_template_formatting()
    test_answer_generator_with_mock_llm()
    test_answer_generator_connection_error()
    test_summarize_with_mock_llm()
    print("All generation tests passed!")
