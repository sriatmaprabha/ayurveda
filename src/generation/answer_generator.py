"""Answer generator that combines retrieved context with LLM generation."""

import logging

from .llm_client import LLMClient, LLMConfig
from .prompts import SYSTEM_PROMPT, QUERY_TEMPLATE, SUMMARY_TEMPLATE

logger = logging.getLogger(__name__)


class AnswerGenerator:
    """Generates grounded answers using retrieved context and an LLM."""

    def __init__(self, llm_client: LLMClient | None = None, config: LLMConfig | None = None):
        self.llm = llm_client or LLMClient(config)

    def generate_answer(self, question: str, context: str) -> dict:
        """Generate an answer for a question using provided context."""
        prompt = QUERY_TEMPLATE.format(context=context, question=question)

        try:
            answer = self.llm.generate(
                prompt=prompt,
                system_prompt=SYSTEM_PROMPT,
            )
        except ConnectionError as e:
            return {
                "answer": None,
                "error": str(e),
                "question": question,
                "model": self.llm.config.model,
            }

        return {
            "answer": answer,
            "error": None,
            "question": question,
            "model": self.llm.config.model,
        }

    def summarize(self, topic: str, context: str) -> dict:
        """Summarize context about a given topic."""
        prompt = SUMMARY_TEMPLATE.format(context=context, topic=topic)

        try:
            summary = self.llm.generate(
                prompt=prompt,
                system_prompt=SYSTEM_PROMPT,
            )
        except ConnectionError as e:
            return {"summary": None, "error": str(e), "topic": topic}

        return {
            "summary": summary,
            "error": None,
            "topic": topic,
            "model": self.llm.config.model,
        }
