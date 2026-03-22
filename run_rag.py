"""Interactive Ayurveda RAG system — ask questions, get grounded answers."""

import argparse
import logging
from pathlib import Path

from src.generation import LLMConfig
from src.orchestrator import RAGPipeline

logging.basicConfig(level=logging.WARNING)

PROJECT_ROOT = Path(__file__).parent


def main():
    parser = argparse.ArgumentParser(description="Ayurveda RAG System")
    parser.add_argument("--model", default="llama3", help="LLM model name")
    parser.add_argument("--base-url", default="http://localhost:11434/v1", help="LLM API base URL")
    parser.add_argument("--api-key", default="ollama", help="API key (if needed)")
    parser.add_argument("--top-k", type=int, default=5, help="Number of sources to retrieve")
    parser.add_argument("--temperature", type=float, default=0.3, help="LLM temperature")
    parser.add_argument("--max-tokens", type=int, default=1024, help="Max response tokens")
    parser.add_argument("--status", action="store_true", help="Check pipeline status and exit")
    args = parser.parse_args()

    llm_config = LLMConfig(
        base_url=args.base_url,
        model=args.model,
        api_key=args.api_key,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
    )

    pipeline = RAGPipeline(
        vector_store_dir=PROJECT_ROOT / "data" / "vector_store",
        llm_config=llm_config,
        top_k=args.top_k,
    )

    if args.status:
        status = pipeline.check_status()
        print("\n=== Pipeline Status ===")
        print(f"Vector Store: {status['vector_store']['status']} "
              f"({status['vector_store']['chunks']} chunks)")
        print(f"LLM: {status['llm']['status']} "
              f"({status['llm']['model']} @ {status['llm']['base_url']})")
        if status["llm"]["available_models"]:
            print(f"Available models: {', '.join(status['llm']['available_models'])}")
        return

    print(f"\nAyurveda RAG System")
    print(f"Model: {args.model} @ {args.base_url}")
    print(f"Knowledge base: {pipeline.store.count} chunks")
    print(f"Type 'quit' to exit, 'status' to check health\n")

    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not question:
            continue
        if question.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break
        if question.lower() == "status":
            status = pipeline.check_status()
            print(f"  Vector Store: {status['vector_store']['chunks']} chunks")
            print(f"  LLM: {status['llm']['status']}")
            continue

        result = pipeline.ask(question)

        if result["error"]:
            print(f"\nError: {result['error']}\n")
            continue

        print(f"\n{'─'*60}")
        print(f"Answer ({result['model']}):\n")
        print(result["answer"])
        print(f"\n{'─'*60}")
        print(f"Sources ({result['num_sources']}):")
        for i, src in enumerate(result["sources"], 1):
            print(f"  {i}. {src['file']} — {src['section']} (score: {src['score']:.2f})")
        print()


if __name__ == "__main__":
    main()
