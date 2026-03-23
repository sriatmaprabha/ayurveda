"""LLM client supporting OpenAI-compatible APIs (Ollama, vLLM, LM Studio, etc.)."""

import json
import logging
from collections.abc import Generator
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """Configuration for an LLM endpoint."""
    base_url: str = "http://localhost:11434/v1"  # Ollama default
    model: str = "llama3"
    api_key: str = "ollama"  # Ollama doesn't need a real key
    temperature: float = 0.3
    max_tokens: int = 512  # Reduced from 1024 — faster responses
    timeout: float = 180.0
    extra_params: dict = field(default_factory=dict)


class LLMClient:
    """Client for OpenAI-compatible LLM APIs."""

    def __init__(self, config: LLMConfig | None = None):
        self.config = config or LLMConfig()
        self._client = httpx.Client(timeout=self.config.timeout)

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Generate a response from the LLM."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        return self.chat(messages, temperature, max_tokens)

    def chat(
        self,
        messages: list[dict],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Send a chat completion request."""
        url = f"{self.config.base_url}/chat/completions"

        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
            **self.config.extra_params,
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
        }

        try:
            response = self._client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except httpx.ConnectError:
            logger.error(
                f"Cannot connect to LLM at {self.config.base_url}. "
                "Make sure your LLM server (Ollama/vLLM/LM Studio) is running."
            )
            raise ConnectionError(
                f"LLM server not reachable at {self.config.base_url}. "
                "Start your LLM server first. For Ollama: 'ollama serve'"
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"LLM API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"LLM request failed: {e}")
            raise

    def stream(
        self,
        messages: list[dict],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Generator[str, None, None]:
        """Stream a chat completion response token by token."""
        url = f"{self.config.base_url}/chat/completions"

        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
            "stream": True,
            **self.config.extra_params,
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
        }

        try:
            with self._client.stream("POST", url, json=payload, headers=headers) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:]  # strip "data: "
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk["choices"][0].get("delta", {})
                        token = delta.get("content", "")
                        if token:
                            yield token
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
        except httpx.ConnectError:
            raise ConnectionError(
                f"LLM server not reachable at {self.config.base_url}. "
                "Start your LLM server first."
            )

    def generate_stream(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Generator[str, None, None]:
        """Stream a generation response token by token."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        yield from self.stream(messages, temperature, max_tokens)

    def is_available(self) -> bool:
        """Check if the LLM server is reachable."""
        try:
            url = f"{self.config.base_url}/models"
            headers = {"Authorization": f"Bearer {self.config.api_key}"}
            response = self._client.get(url, headers=headers)
            return response.status_code == 200
        except Exception:
            return False

    def list_models(self) -> list[str]:
        """List available models on the server."""
        try:
            url = f"{self.config.base_url}/models"
            headers = {"Authorization": f"Bearer {self.config.api_key}"}
            response = self._client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            return [m["id"] for m in data.get("data", [])]
        except Exception as e:
            logger.warning(f"Could not list models: {e}")
            return []

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
