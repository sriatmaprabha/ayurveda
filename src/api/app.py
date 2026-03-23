"""FastAPI application for the Ayurveda RAG system."""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

from src.generation import LLMConfig
from src.orchestrator import MonitoredRAGPipeline
from src.vision import ImageProcessor
from .schemas import (
    QueryRequest,
    QueryResponse,
    StatusResponse,
    StatsResponse,
    IngestResponse,
    ImageQueryRequest,
    ImageQueryResponse,
)

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent

# Global pipeline instance
pipeline: MonitoredRAGPipeline | None = None
image_processor: ImageProcessor | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize pipeline on startup."""
    global pipeline, image_processor

    llm_config = LLMConfig(
        base_url=os.getenv("LLM_BASE_URL", "http://localhost:11434/v1"),
        model=os.getenv("LLM_MODEL", "llama3"),
        api_key=os.getenv("LLM_API_KEY", "ollama"),
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.3")),
        max_tokens=int(os.getenv("LLM_MAX_TOKENS", "1024")),
    )

    pipeline = MonitoredRAGPipeline(
        vector_store_dir=PROJECT_ROOT / "data" / "vector_store",
        llm_config=llm_config,
        monitor_model=os.getenv("MONITOR_MODEL", "mistral"),
        monitor_base_url=os.getenv("MONITOR_BASE_URL", "http://localhost:11434/v1"),
        enable_monitoring=os.getenv("ENABLE_MONITORING", "true").lower() == "true",
        log_file=str(PROJECT_ROOT / "data" / "pipeline_logs.jsonl"),
    )

    image_processor = ImageProcessor(
        base_url=os.getenv("VISION_BASE_URL", "http://localhost:11434/v1"),
        model=os.getenv("VISION_MODEL", "llama4"),
    )

    logger.info(f"Pipeline ready — {pipeline.store.count} chunks indexed")
    yield
    logger.info("Shutting down pipeline")


from .diagnostic_routes import router as diagnostic_router

app = FastAPI(
    title="Ayurveda RAG API",
    description="Ask questions about Ayurveda, grounded in classical texts like "
                "Charaka Samhita, Sushruta Samhita, and Ashtanga Hridaya.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(diagnostic_router)


def _get_pipeline() -> MonitoredRAGPipeline:
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
    return pipeline


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """Ask a question about Ayurveda."""
    pipe = _get_pipeline()
    result = pipe.ask(
        question=request.question,
        top_k=request.top_k,
        evaluate=request.evaluate,
    )

    if result.get("error"):
        raise HTTPException(status_code=502, detail=result["error"])

    return QueryResponse(
        question=result["question"],
        answer=result["answer"],
        sources=[
            {"file": s["file"], "section": s["section"], "score": s["score"]}
            for s in result["sources"]
        ],
        model=result["model"],
        latency_ms=result["latency_ms"],
        evaluation=result.get("evaluation"),
    )


@app.post("/vision/query", response_model=ImageQueryResponse)
async def vision_query(
    file: UploadFile = File(...),
    question: str = "What does this image show and what is its Ayurvedic significance?",
):
    """Ask a question about an uploaded image."""
    if image_processor is None:
        raise HTTPException(status_code=503, detail="Vision processor not initialized")

    # Save uploaded file temporarily
    import tempfile
    suffix = Path(file.filename).suffix if file.filename else ".png"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # Process image
        vision_result = image_processor.process_image(tmp_path, prompt=question)

        if vision_result["error"]:
            raise HTTPException(status_code=502, detail=vision_result["error"])

        # Search knowledge base with extracted content
        pipe = _get_pipeline()
        search_query = f"{question} {vision_result['content'][:200]}"
        retrieval = pipe.query_engine.answer_with_sources(search_query)

        return ImageQueryResponse(
            image_content=vision_result["content"],
            sources=[
                {"file": s["file"], "section": s["section"], "score": s["score"]}
                for s in retrieval["sources"]
            ],
            vision_model=vision_result["model"],
        )
    finally:
        os.unlink(tmp_path)


@app.post("/ingest/image", response_model=IngestResponse)
async def ingest_image(file: UploadFile = File(...)):
    """Ingest an image into the knowledge base via vision extraction."""
    if image_processor is None:
        raise HTTPException(status_code=503, detail="Vision processor not initialized")

    import tempfile
    suffix = Path(file.filename).suffix if file.filename else ".png"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        vision_result = image_processor.process_image(tmp_path)

        if vision_result["error"] or not vision_result["content"]:
            raise HTTPException(
                status_code=502,
                detail=f"Vision extraction failed: {vision_result.get('error')}",
            )

        # Add to vector store
        pipe = _get_pipeline()
        filename = file.filename or "uploaded_image"
        pipe.store.collection.upsert(
            ids=[f"img_upload_{filename}"],
            documents=[vision_result["content"]],
            metadatas=[{
                "source_file": filename,
                "section_title": f"Image: {filename}",
                "section_type": "image_extraction",
                "file_name": filename,
                "file_type": suffix,
            }],
        )

        return IngestResponse(
            message=f"Ingested image: {filename}",
            chunks_added=1,
            total_chunks=pipe.store.count,
        )
    finally:
        os.unlink(tmp_path)


@app.get("/status", response_model=StatusResponse)
async def status():
    """Check the health of all pipeline components."""
    pipe = _get_pipeline()
    s = pipe.check_status()
    return StatusResponse(
        vector_store=s["vector_store"],
        answer_llm=s["answer_llm"],
        monitor_llm=s["monitor_llm"],
    )


@app.get("/stats", response_model=StatsResponse)
async def stats():
    """Get pipeline performance statistics."""
    pipe = _get_pipeline()
    s = pipe.get_stats()
    return StatsResponse(**s)
