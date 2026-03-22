"""Process images through the Ayurveda Vision RAG pipeline."""

import argparse
import logging
from pathlib import Path

from src.generation import LLMConfig
from src.vision import VisionRAG

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

PROJECT_ROOT = Path(__file__).parent


def main():
    parser = argparse.ArgumentParser(description="Ayurveda Vision RAG")
    parser.add_argument("image", nargs="?", help="Path to an image file")
    parser.add_argument("--question", "-q", default=None, help="Question about the image")
    parser.add_argument("--ingest", action="store_true", help="Ingest image into knowledge base")
    parser.add_argument("--ingest-dir", help="Ingest all images from a directory")
    parser.add_argument("--vision-model", default="llama4", help="Vision model name")
    parser.add_argument("--vision-url", default="http://localhost:11434/v1", help="Vision LLM URL")
    parser.add_argument("--llm-model", default="llama3", help="Answer generation model")
    parser.add_argument("--llm-url", default="http://localhost:11434/v1", help="Answer LLM URL")
    parser.add_argument("--status", action="store_true", help="Check status")
    args = parser.parse_args()

    llm_config = LLMConfig(base_url=args.llm_url, model=args.llm_model)

    vision_rag = VisionRAG(
        vector_store_dir=PROJECT_ROOT / "data" / "vector_store",
        vision_model=args.vision_model,
        vision_base_url=args.vision_url,
        llm_config=llm_config,
    )

    if args.status:
        status = vision_rag.check_status()
        print("\n=== Vision RAG Status ===")
        for component, info in status.items():
            print(f"{component}: {info}")
        return

    if args.ingest_dir:
        dir_path = Path(args.ingest_dir)
        images = list(dir_path.rglob("*.png")) + list(dir_path.rglob("*.jpg")) + \
                 list(dir_path.rglob("*.jpeg")) + list(dir_path.rglob("*.webp"))
        print(f"Found {len(images)} images in {dir_path}")
        total = 0
        for img in sorted(images):
            chunks = vision_rag.ingest_image_to_kb(img)
            total += chunks
            print(f"  {img.name}: {chunks} chunks")
        print(f"\nTotal: {total} chunks ingested")
        return

    if not args.image:
        parser.print_help()
        return

    image_path = Path(args.image)
    if not image_path.exists():
        print(f"Image not found: {image_path}")
        return

    if args.ingest:
        chunks = vision_rag.ingest_image_to_kb(image_path)
        print(f"Ingested {chunks} chunks from {image_path.name}")
        return

    # Ask about the image
    question = args.question or "What does this image show and what is its Ayurvedic significance?"
    print(f"\nProcessing: {image_path.name}")
    print(f"Question: {question}\n")

    result = vision_rag.ask_about_image(image_path, question)

    if result["error"]:
        print(f"Error: {result['error']}")
        return

    print(f"{'─'*60}")
    print(f"Image content ({result['vision_model']}):\n")
    print(result["image_content"][:500])
    if len(result["image_content"]) > 500:
        print(f"\n... ({len(result['image_content'])} chars total)")

    print(f"\n{'─'*60}")
    print(f"Answer:\n")
    print(result["answer"])

    print(f"\n{'─'*60}")
    print("Sources:")
    for i, src in enumerate(result["sources"], 1):
        print(f"  {i}. {src['file']} — {src['section']} (score: {src['score']:.2f})")
    print()


if __name__ == "__main__":
    main()
