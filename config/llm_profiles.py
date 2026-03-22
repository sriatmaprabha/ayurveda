"""Pre-configured LLM profiles for different providers and models."""

from src.generation import LLMConfig

# === Ollama (local, default) ===

OLLAMA_LLAMA3 = LLMConfig(
    base_url="http://localhost:11434/v1",
    model="llama3",
    api_key="ollama",
    temperature=0.3,
    max_tokens=1024,
)

OLLAMA_LLAMA4 = LLMConfig(
    base_url="http://localhost:11434/v1",
    model="llama4",
    api_key="ollama",
    temperature=0.3,
    max_tokens=1024,
)

OLLAMA_MISTRAL = LLMConfig(
    base_url="http://localhost:11434/v1",
    model="mistral",
    api_key="ollama",
    temperature=0.3,
    max_tokens=1024,
)

# === vLLM (local or remote) ===

VLLM_DEFAULT = LLMConfig(
    base_url="http://localhost:8000/v1",
    model="meta-llama/Llama-4",
    api_key="token-placeholder",
    temperature=0.3,
    max_tokens=1024,
)

# === LM Studio (local) ===

LMSTUDIO_DEFAULT = LLMConfig(
    base_url="http://localhost:1234/v1",
    model="local-model",
    api_key="lm-studio",
    temperature=0.3,
    max_tokens=1024,
)

# === OpenAI-compatible remote (GPT-OSS, Together, Groq, etc.) ===

TOGETHER_AI = LLMConfig(
    base_url="https://api.together.xyz/v1",
    model="meta-llama/Meta-Llama-4-8B-Instruct",
    api_key="YOUR_TOGETHER_API_KEY",
    temperature=0.3,
    max_tokens=1024,
)

GROQ = LLMConfig(
    base_url="https://api.groq.com/openai/v1",
    model="llama-3.3-70b-versatile",
    api_key="YOUR_GROQ_API_KEY",
    temperature=0.3,
    max_tokens=1024,
)
