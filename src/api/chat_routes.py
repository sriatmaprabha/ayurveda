"""Conversational diagnostic chat API — every response ends with a follow-up question."""

import os
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.generation import LLMConfig, LLMClient, ConversationalDiagnostic, DiagnosticConversation
from src.generation.prompts import DIAGNOSTIC_SYSTEM_PROMPT, DIAGNOSTIC_QUERY_TEMPLATE
from src.embeddings import VectorStore
from src.retrieval import QueryEngine

router = APIRouter(prefix="/chat", tags=["Diagnostic Chat"])

PROJECT_ROOT = Path(__file__).parent.parent.parent

# In-memory session store (for production, use Redis or DB)
_sessions: dict[str, dict] = {}
_diagnostic: ConversationalDiagnostic | None = None
_query_engine: QueryEngine | None = None


def _get_diagnostic() -> ConversationalDiagnostic:
    global _diagnostic
    if _diagnostic is None:
        config = LLMConfig(
            base_url=os.getenv("LLM_BASE_URL", "http://localhost:11434/v1"),
            model=os.getenv("LLM_MODEL", "llama3"),
            api_key=os.getenv("LLM_API_KEY", "ollama"),
        )
        _diagnostic = ConversationalDiagnostic(config=config)
    return _diagnostic


def _get_query_engine() -> QueryEngine:
    global _query_engine
    if _query_engine is None:
        store = VectorStore(persist_dir=PROJECT_ROOT / "data" / "vector_store")
        _query_engine = QueryEngine(vector_store=store, top_k=5)
    return _query_engine


# === Schemas ===

class ChatStartResponse(BaseModel):
    session_id: str
    message: str


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    session_id: str
    response: str
    dosha_scores: dict
    dominant_dosha: str
    turn_number: int
    sources: list[dict] = []


# === Endpoints ===

@router.post("/start", response_model=ChatStartResponse)
async def start_chat():
    """Start a new diagnostic conversation."""
    session_id = str(uuid.uuid4())[:8]
    conversation = DiagnosticConversation(conversation_id=session_id)

    _sessions[session_id] = {
        "conversation": conversation,
    }

    opening = (
        "Namaste! I am your Ayurvedic diagnostic assistant. I will help identify "
        "your dosha imbalance and guide you toward a personalized treatment plan "
        "based on classical Ayurvedic texts.\n\n"
        "I'll ask you a series of questions to understand your condition. "
        "You can describe your symptoms, share how you're feeling, or even "
        "describe what your tongue, skin, or nails look like.\n\n"
        "To begin — what is your primary health concern or symptom that brought you here today?"
    )

    conversation.add_vaidya_response(opening)

    return ChatStartResponse(
        session_id=session_id,
        message=opening,
    )


@router.post("/message", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """Send a message in the diagnostic conversation. Response always ends with a follow-up question."""
    if request.session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found. Start a new chat with POST /chat/start")

    session = _sessions[request.session_id]
    conversation: DiagnosticConversation = session["conversation"]
    diagnostic = _get_diagnostic()
    engine = _get_query_engine()

    # Retrieve relevant context from knowledge base
    context = ""
    sources = []
    try:
        retrieval = engine.answer_with_sources(request.message)
        context = retrieval["context"]
        sources = [
            {"file": s["file"], "section": s["section"], "score": s["score"]}
            for s in retrieval["sources"]
        ]
    except Exception as e:
        context = ""
        sources = []

    # Generate response (always ends with a question)
    response = diagnostic.respond(
        conversation=conversation,
        patient_message=request.message,
        context=context,
    )

    turn_number = len([t for t in conversation.turns if t.role == "patient"])

    # Auto-advance diagnostic level based on conversation depth
    if turn_number >= 8:
        conversation.level = 4
    elif turn_number >= 5:
        conversation.level = 3
    elif turn_number >= 3:
        conversation.level = 2

    return ChatResponse(
        session_id=request.session_id,
        response=response,
        dosha_scores={
            "vata": conversation.vata_score,
            "pitta": conversation.pitta_score,
            "kapha": conversation.kapha_score,
        },
        dominant_dosha=conversation.dominant_dosha,
        turn_number=turn_number,
        sources=sources,
    )


@router.post("/stream")
async def stream_message(request: ChatRequest):
    """Stream a diagnostic response token-by-token. Much faster perceived response time."""
    if request.session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found. Start with POST /chat/start")

    session = _sessions[request.session_id]
    conversation: DiagnosticConversation = session["conversation"]
    engine = _get_query_engine()

    # Retrieve context
    context = ""
    try:
        retrieval = engine.answer_with_sources(request.message, top_k=3)
        context = retrieval["context"]
    except Exception:
        context = ""

    conversation.add_patient_message(request.message)

    # Build the prompt
    prompt = DIAGNOSTIC_QUERY_TEMPLATE.format(
        context=context if context else "No specific context retrieved.",
        conversation_history=conversation.history_text,
        message=request.message,
        vata_score=conversation.vata_score,
        pitta_score=conversation.pitta_score,
        kapha_score=conversation.kapha_score,
        dominant_dosha=conversation.dominant_dosha,
        level=conversation.level,
    )

    config = LLMConfig(
        base_url=os.getenv("LLM_BASE_URL", "http://localhost:11434/v1"),
        model=os.getenv("LLM_MODEL", "llama3"),
        api_key=os.getenv("LLM_API_KEY", "ollama"),
        max_tokens=512,
    )
    client = LLMClient(config)

    def token_generator():
        full_response = ""
        try:
            for token in client.generate_stream(
                prompt=prompt,
                system_prompt=DIAGNOSTIC_SYSTEM_PROMPT,
            ):
                full_response += token
                yield token
        except ConnectionError as e:
            yield f"\n\n[Error: {e}]"
        finally:
            # Save the full response to conversation history
            if full_response:
                # Ensure it ends with a question
                diagnostic = _get_diagnostic()
                checked = diagnostic._ensure_ends_with_question(full_response)
                if checked != full_response:
                    extra = checked[len(full_response):]
                    yield extra
                    full_response = checked
                conversation.add_vaidya_response(full_response)

    return StreamingResponse(
        token_generator(),
        media_type="text/plain",
        headers={"X-Session-Id": request.session_id},
    )


@router.get("/history/{session_id}")
async def get_chat_history(session_id: str):
    """Get the full conversation history for a session."""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    conversation: DiagnosticConversation = _sessions[session_id]["conversation"]

    return {
        "session_id": session_id,
        "turns": [
            {"role": t.role, "message": t.message}
            for t in conversation.turns
        ],
        "dosha_scores": {
            "vata": conversation.vata_score,
            "pitta": conversation.pitta_score,
            "kapha": conversation.kapha_score,
        },
        "dominant_dosha": conversation.dominant_dosha,
        "level": conversation.level,
        "total_turns": len(conversation.turns),
    }
