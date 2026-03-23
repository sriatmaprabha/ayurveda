"""API routes for the multi-level diagnostic engine."""

import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field

from src.vision import DiagnosticEngine, DiagnosticSession, PARIKSHA_PROMPTS

router = APIRouter(prefix="/diagnose", tags=["Diagnosis"])

PROJECT_ROOT = Path(__file__).parent.parent.parent

# Lazy-init engine
_engine: DiagnosticEngine | None = None


def _get_engine() -> DiagnosticEngine:
    global _engine
    if _engine is None:
        _engine = DiagnosticEngine(
            vector_store_dir=PROJECT_ROOT / "data" / "vector_store",
            vision_model=os.getenv("VISION_MODEL", "llama4"),
            vision_base_url=os.getenv("VISION_BASE_URL", "http://localhost:11434/v1"),
        )
    return _engine


# === Schemas ===

class Level1Response(BaseModel):
    id: str
    answer: str
    score: dict = Field(default_factory=dict)


class Level1Request(BaseModel):
    responses: list[Level1Response]


class Level1Result(BaseModel):
    dosha_scores: dict
    dominant: str
    assessment: str
    level2_questions: list[dict]
    image_requests: list[dict]


class ParikshaResult(BaseModel):
    pariksha_type: str
    pariksha_name: str
    content: str | None
    error: str | None
    diagnostic_level: int


class AvailablePariksha(BaseModel):
    type: str
    name: str
    level: int


# === Endpoints ===

@router.get("/level1/questions")
async def get_level1_questions():
    """Get Level 1 diagnostic questions."""
    engine = _get_engine()
    return {"questions": engine.get_level1_questions()}


@router.post("/level1/submit", response_model=Level1Result)
async def submit_level1(request: Level1Request):
    """Submit Level 1 responses and get Level 2 plan."""
    engine = _get_engine()
    responses = [r.model_dump() for r in request.responses]
    session = engine.process_level1(responses)
    level2 = engine.get_level2_questions(session)

    return Level1Result(
        dosha_scores=session.dosha_scores.as_dict(),
        dominant=session.dosha_scores.dominant(),
        assessment=session.current_assessment,
        level2_questions=level2["text_questions"],
        image_requests=level2["image_requests"],
    )


@router.post("/pariksha/{pariksha_type}", response_model=ParikshaResult)
async def run_pariksha(pariksha_type: str, file: UploadFile = File(...)):
    """Run a specific Pariksha examination on an uploaded image."""
    if pariksha_type not in PARIKSHA_PROMPTS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown pariksha type: {pariksha_type}. "
                   f"Valid types: {list(PARIKSHA_PROMPTS.keys())}",
        )

    engine = _get_engine()

    suffix = Path(file.filename).suffix if file.filename else ".png"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = engine.analyze_image(tmp_path, pariksha_type)
        return ParikshaResult(
            pariksha_type=result.get("pariksha_type", pariksha_type),
            pariksha_name=result.get("pariksha_name", ""),
            content=result.get("content"),
            error=result.get("error"),
            diagnostic_level=result.get("diagnostic_level", 0),
        )
    finally:
        os.unlink(tmp_path)


@router.get("/level3/questions")
async def get_level3_questions():
    """Get Level 3 personalization questions."""
    engine = _get_engine()
    return {"questions": engine.get_level3_questions()}


@router.get("/pariksha/types", response_model=list[AvailablePariksha])
async def list_pariksha_types():
    """List all available Pariksha examination types."""
    engine = _get_engine()
    return [AvailablePariksha(**p) for p in engine.get_available_pariksha()]
