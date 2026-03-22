"""Vision-enhanced RAG: process images, then query the knowledge base with extracted content."""

import json
import logging
from pathlib import Path

from src.ingestion.base_parser import DocumentSection
from src.ingestion.chunker import DocumentChunker
from src.embeddings import VectorStore
from src.retrieval import QueryEngine
from src.generation import LLMClient, LLMConfig, AnswerGenerator
from .image_processor import ImageProcessor

logger = logging.getLogger(__name__)

IMAGE_QUERY_PROMPT = """I have an image from an Ayurveda context. Here is the extracted content from the image:

{image_content}

Based on this extracted content and the knowledge base context below, answer the user's question.

Knowledge base context:
{kb_context}

Question: {question}

Provide a detailed answer combining insights from both the image content and knowledge base. Cite sources using [Source N] for knowledge base references and [Image] for image-derived information."""


class VisionRAG:
    """Combines vision processing with RAG for image-based Ayurveda queries."""

    def __init__(
        self,
        vector_store_dir: str | Path = "data/vector_store",
        vision_model: str = "llama4",
        vision_base_url: str = "http://localhost:11434/v1",
        llm_config: LLMConfig | None = None,
        top_k: int = 5,
    ):
        self.image_processor = ImageProcessor(
            base_url=vision_base_url,
            model=vision_model,
        )

        self.store = VectorStore(persist_dir=vector_store_dir)
        self.query_engine = QueryEngine(vector_store=self.store, top_k=top_k)

        llm_config = llm_config or LLMConfig()
        self.llm_client = LLMClient(llm_config)
        self.generator = AnswerGenerator(llm_client=self.llm_client)

    def ask_about_image(
        self,
        image_path: str | Path,
        question: str = "What does this image show and what is its Ayurvedic significance?",
        top_k: int | None = None,
    ) -> dict:
        """Process an image, retrieve related knowledge, and generate an answer."""
        # Step 1: Extract content from image
        vision_result = self.image_processor.process_image(image_path)

        if vision_result["error"]:
            return {
                "answer": None,
                "error": f"Vision processing failed: {vision_result['error']}",
                "image_content": None,
                "sources": [],
            }

        image_content = vision_result["content"]

        # Step 2: Use extracted content to search knowledge base
        search_query = f"{question} {image_content[:200]}"
        retrieval = self.query_engine.answer_with_sources(search_query, top_k)

        # Step 3: Generate answer combining image content + KB context
        prompt = IMAGE_QUERY_PROMPT.format(
            image_content=image_content,
            kb_context=retrieval["context"],
            question=question,
        )

        generation = self.generator.llm.generate(
            prompt=prompt,
            system_prompt="You are an Ayurveda expert. Answer using both image content and knowledge base sources.",
        )

        return {
            "answer": generation,
            "error": None,
            "image_content": image_content,
            "sources": retrieval["sources"],
            "vision_model": vision_result["model"],
            "image_file": vision_result["file_name"],
        }

    def ingest_image_to_kb(
        self,
        image_path: str | Path,
        chunk_size: int = 512,
    ) -> int:
        """Extract content from an image and add it to the vector store."""
        vision_result = self.image_processor.process_image(image_path)

        if vision_result["error"] or not vision_result["content"]:
            logger.error(f"Cannot ingest image {image_path}: {vision_result.get('error')}")
            return 0

        # Create document sections from extracted content
        section = DocumentSection(
            text=vision_result["content"],
            metadata={
                "source_file": str(image_path),
                "file_name": Path(image_path).name,
                "file_type": Path(image_path).suffix.lower(),
                "extraction_model": vision_result["model"],
            },
            source_file=str(image_path),
            section_title=f"Image: {Path(image_path).name}",
            section_type="image_extraction",
        )

        # Chunk if needed
        chunker = DocumentChunker(chunk_size=chunk_size)
        chunks = chunker.chunk([section])

        # Add to vector store
        for i, chunk in enumerate(chunks):
            self.store.collection.upsert(
                ids=[f"img_{Path(image_path).stem}_{i}"],
                documents=[chunk.text],
                metadatas=[{
                    "source_file": chunk.source_file,
                    "section_title": chunk.section_title,
                    "section_type": chunk.section_type,
                    "file_name": chunk.metadata.get("file_name", ""),
                    "file_type": chunk.metadata.get("file_type", ""),
                }],
            )

        logger.info(f"Ingested {len(chunks)} chunks from image {Path(image_path).name}")
        return len(chunks)

    def check_status(self) -> dict:
        return {
            "vision_llm": {
                "status": "ok" if self.image_processor.is_available() else "unavailable",
                "model": self.image_processor.model,
            },
            "vector_store": {
                "chunks": self.store.count,
            },
            "answer_llm": {
                "status": "ok" if self.llm_client.is_available() else "unavailable",
                "model": self.llm_client.config.model,
            },
        }
