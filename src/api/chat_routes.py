"""Conversational diagnostic chat API — prakriti-aware, consistent asana protocols."""

import os
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.generation import LLMConfig, LLMClient, ConversationalDiagnostic, DiagnosticConversation
from src.generation.conversational import classify_casual, CASUAL_RESPONSES
from src.generation.prompts import DIAGNOSTIC_SYSTEM_PROMPT, DIAGNOSTIC_QUERY_TEMPLATE
from src.generation.prakriti_profiler import (
    PrakritiProfile, get_next_questions, format_question_for_chat, parse_answer,
)
from src.embeddings import VectorStore
from src.retrieval import QueryEngine, AsanaRecommender
from src.retrieval.protocol_mapper import ProtocolMapper

router = APIRouter(prefix="/chat", tags=["Diagnostic Chat"])

PROJECT_ROOT = Path(__file__).parent.parent.parent

# In-memory session store
_sessions: dict[str, dict] = {}
_diagnostic: ConversationalDiagnostic | None = None
_query_engine: QueryEngine | None = None
_asana_recommender: AsanaRecommender | None = None
_protocol_mapper: ProtocolMapper | None = None


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


def _get_asana_recommender() -> AsanaRecommender:
    global _asana_recommender
    if _asana_recommender is None:
        _asana_recommender = AsanaRecommender(
            vector_store_dir=PROJECT_ROOT / "data" / "vector_store"
        )
    return _asana_recommender


def _get_protocol_mapper() -> ProtocolMapper:
    global _protocol_mapper
    if _protocol_mapper is None:
        _protocol_mapper = ProtocolMapper()
    return _protocol_mapper


def _build_protocol_context(message: str, dosha: str) -> str:
    """Get fixed, consistent asana protocols for the user's symptoms + dosha."""
    mapper = _get_protocol_mapper()

    # Match symptoms from user message
    protocols = mapper.get_protocols_for_text(message, max_protocols=2)

    # If no symptom match, use dosha defaults
    if not protocols and dosha:
        protocols = mapper.get_protocols_for_dosha(dosha, max_protocols=1)

    if not protocols:
        return ""

    parts = ["--- PRESCRIBED YOGA PROTOCOLS (use these exact instructions) ---\n"]
    for p in protocols:
        parts.append(mapper.format_protocol_for_chat(p))

    return "\n".join(parts)


def _get_prakriti_question_text(profile: PrakritiProfile) -> str:
    """Get the next prakriti question -- woven naturally, not as a quiz."""
    questions = get_next_questions(profile, count=1)
    if not questions:
        return ""

    q = questions[0]
    profile.questions_asked.append(q["id"])
    opts = q["options"]
    return (
        f"\n\nTo see your design more clearly -- {q['question'].lower()}\n"
        f"  A) {opts['a']['text']}\n"
        f"  B) {opts['b']['text']}\n"
        f"  C) {opts['c']['text']}"
    )


def _try_parse_prakriti_answer(message: str, profile: PrakritiProfile) -> bool:
    """Try to parse the user's message as an answer to a pending prakriti question."""
    if not profile.questions_asked:
        return False

    # Import the questions list
    from src.generation.prakriti_profiler import PRAKRITI_QUESTIONS

    last_asked_id = profile.questions_asked[-1]
    question = next((q for q in PRAKRITI_QUESTIONS if q["id"] == last_asked_id), None)
    if not question:
        return False

    # Only try parsing if last question hasn't been answered yet
    if last_asked_id in profile.answers_given:
        return False

    dosha = parse_answer(message, question)
    if dosha:
        profile.score_answer(dosha)
        profile.answers_given[last_asked_id] = dosha
        return True

    return False


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
    prakriti: dict = {}
    turn_number: int
    sources: list[dict] = []


# === Endpoints ===

@router.post("/start", response_model=ChatStartResponse)
async def start_chat():
    """Start a new diagnostic conversation with prakriti profiling."""
    session_id = str(uuid.uuid4())[:8]
    conversation = DiagnosticConversation(conversation_id=session_id)
    prakriti = PrakritiProfile()

    _sessions[session_id] = {
        "conversation": conversation,
        "prakriti": prakriti,
    }

    from src.generation.prompts import OPENING_MESSAGE
    opening = OPENING_MESSAGE

    conversation.add_vaidya_response(opening)

    return ChatStartResponse(session_id=session_id, message=opening)


@router.post("/message", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """Send a message — responses include prakriti questions and consistent asana protocols."""
    if request.session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found. Start with POST /chat/start")

    session = _sessions[request.session_id]
    conversation: DiagnosticConversation = session["conversation"]
    prakriti: PrakritiProfile = session["prakriti"]
    diagnostic = _get_diagnostic()
    engine = _get_query_engine()

    # Check if casual
    casual_type = classify_casual(request.message)
    if casual_type:
        response = CASUAL_RESPONSES.get(casual_type, CASUAL_RESPONSES["filler"])
        conversation.add_patient_message(request.message)
        conversation.add_vaidya_response(response)
        turn_number = len([t for t in conversation.turns if t.role == "patient"])
        return ChatResponse(
            session_id=request.session_id, response=response,
            dosha_scores={"vata": conversation.vata_score, "pitta": conversation.pitta_score, "kapha": conversation.kapha_score},
            dominant_dosha=conversation.dominant_dosha, prakriti=prakriti.as_dict(),
            turn_number=turn_number, sources=[],
        )

    # Try to parse prakriti answer from user message
    _try_parse_prakriti_answer(request.message, prakriti)

    # Update conversation dosha scores from prakriti
    conversation.vata_score = prakriti.vata
    conversation.pitta_score = prakriti.pitta
    conversation.kapha_score = prakriti.kapha

    # Get fixed asana protocols (limit for GPU memory)
    protocol_context = _build_protocol_context(request.message, prakriti.dominant)
    if protocol_context and len(protocol_context) > 500:
        protocol_context = protocol_context[:500] + "..."

    # Get knowledge base context (top_k=2 for GPU memory)
    context = ""
    sources = []
    try:
        retrieval = engine.answer_with_sources(request.message, top_k=2)
        context = retrieval["context"]
        if len(context) > 1500:
            context = context[:1500] + "..."
        sources = [{"file": s["file"], "section": s["section"], "score": s["score"]} for s in retrieval["sources"]]
    except Exception:
        context = ""

    # Combine: KB context + fixed protocols
    combined_context = context
    if protocol_context:
        combined_context = f"{context}\n\n{protocol_context}"

    # Generate LLM response
    response = diagnostic.respond(
        conversation=conversation,
        patient_message=request.message,
        context=combined_context,
    )

    # Append prakriti question if not yet determined
    if not prakriti.is_determined:
        prakriti_q = _get_prakriti_question_text(prakriti)
        if prakriti_q:
            response += prakriti_q

    turn_number = len([t for t in conversation.turns if t.role == "patient"])
    if turn_number >= 8:
        conversation.level = 4
    elif turn_number >= 5:
        conversation.level = 3
    elif turn_number >= 3:
        conversation.level = 2

    return ChatResponse(
        session_id=request.session_id, response=response,
        dosha_scores={"vata": conversation.vata_score, "pitta": conversation.pitta_score, "kapha": conversation.kapha_score},
        dominant_dosha=prakriti.dominant, prakriti=prakriti.as_dict(),
        turn_number=turn_number, sources=sources,
    )


@router.post("/stream")
async def stream_message(request: ChatRequest):
    """Stream a diagnostic response with prakriti questions and fixed protocols."""
    if request.session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found. Start with POST /chat/start")

    session = _sessions[request.session_id]
    conversation: DiagnosticConversation = session["conversation"]
    prakriti: PrakritiProfile = session["prakriti"]
    engine = _get_query_engine()

    # Check casual — instant response, no LLM
    casual_type = classify_casual(request.message)
    if casual_type:
        response = CASUAL_RESPONSES.get(casual_type, CASUAL_RESPONSES["filler"])
        conversation.add_patient_message(request.message)
        conversation.add_vaidya_response(response)

        def casual_stream():
            yield response

        return StreamingResponse(casual_stream(), media_type="text/plain",
                                 headers={"X-Session-Id": request.session_id})

    # Try to parse prakriti answer
    _try_parse_prakriti_answer(request.message, prakriti)
    conversation.vata_score = prakriti.vata
    conversation.pitta_score = prakriti.pitta
    conversation.kapha_score = prakriti.kapha

    # Get fixed asana protocols (limit to 1 for GPU memory)
    protocol_context = _build_protocol_context(request.message, prakriti.dominant)
    # Trim protocol context to max 500 chars
    if protocol_context and len(protocol_context) > 500:
        protocol_context = protocol_context[:500] + "..."

    # Get KB context (top_k=2 to fit GPU)
    context = ""
    try:
        retrieval = engine.answer_with_sources(request.message, top_k=2)
        context = retrieval["context"]
        # Hard cap context to 1500 chars
        if len(context) > 1500:
            context = context[:1500] + "..."
    except Exception:
        context = ""

    combined_context = context
    if protocol_context:
        combined_context = f"{context}\n\n{protocol_context}"

    # Build prakriti question suffix
    prakriti_suffix = ""
    if not prakriti.is_determined:
        prakriti_suffix = _get_prakriti_question_text(prakriti)

    conversation.add_patient_message(request.message)

    # Trim conversation history to last 4 turns to fit GPU memory
    recent_turns = conversation.turns[-4:] if len(conversation.turns) > 4 else conversation.turns
    history_text = "\n\n".join(
        f"{'Patient' if t.role == 'patient' else 'Vaidya'}: {t.message[:200]}"
        for t in recent_turns
    )

    # Build prompt
    prompt = DIAGNOSTIC_QUERY_TEMPLATE.format(
        context=combined_context if combined_context else "No specific context retrieved.",
        asana_context="Asana protocols are included in the context above." if protocol_context else "No protocols.",
        conversation_history=history_text,
        message=request.message,
        vata_score=conversation.vata_score,
        pitta_score=conversation.pitta_score,
        kapha_score=conversation.kapha_score,
        dominant_dosha=prakriti.dominant,
        level=conversation.level,
    )

    config = LLMConfig(
        base_url=os.getenv("LLM_BASE_URL", "http://localhost:11434/v1"),
        model=os.getenv("LLM_MODEL", "llama3"),
        api_key=os.getenv("LLM_API_KEY", "ollama"),
        max_tokens=384,
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
        except (ConnectionError, RuntimeError) as e:
            yield f"\n\n[Error: {e}]"
        finally:
            if full_response:
                diagnostic = _get_diagnostic()
                checked = diagnostic._ensure_ends_with_question(full_response)
                if checked != full_response:
                    extra = checked[len(full_response):]
                    yield extra
                    full_response = checked
                # Append prakriti question
                if prakriti_suffix:
                    yield prakriti_suffix
                    full_response += prakriti_suffix
                conversation.add_vaidya_response(full_response)

    return StreamingResponse(
        token_generator(), media_type="text/plain",
        headers={"X-Session-Id": request.session_id},
    )


@router.get("/history/{session_id}")
async def get_chat_history(session_id: str):
    """Get full conversation history with prakriti profile."""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = _sessions[session_id]
    conversation: DiagnosticConversation = session["conversation"]
    prakriti: PrakritiProfile = session["prakriti"]

    return {
        "session_id": session_id,
        "turns": [{"role": t.role, "message": t.message} for t in conversation.turns],
        "dosha_scores": {"vata": conversation.vata_score, "pitta": conversation.pitta_score, "kapha": conversation.kapha_score},
        "dominant_dosha": prakriti.dominant,
        "prakriti": prakriti.as_dict(),
        "level": conversation.level,
        "total_turns": len(conversation.turns),
    }


# === Asana Recommendation Endpoints ===

class AsanaRequest(BaseModel):
    dosha: str = Field("", description="Dominant dosha")
    symptoms: str = Field("", description="Symptoms in natural language")
    top_k: int = Field(5, ge=1, le=20)


@router.post("/recommend/asana")
async def recommend_asana(request: AsanaRequest):
    """Get consistent yoga asana protocols based on dosha and/or symptoms."""
    mapper = _get_protocol_mapper()

    if request.symptoms:
        protocols = mapper.get_protocols_for_text(request.symptoms, request.top_k)
    elif request.dosha:
        protocols = mapper.get_protocols_for_dosha(request.dosha, request.top_k)
    else:
        raise HTTPException(status_code=400, detail="Provide 'dosha' or 'symptoms'")

    return {
        "dosha": request.dosha,
        "symptoms": request.symptoms,
        "protocols": [
            {"condition": p["condition"], "protocol_type": p["protocol_type"],
             "name": p["name"], "steps_summary": p.get("steps_summary", ""),
             "step_count": len(p.get("step_details", []))}
            for p in protocols
        ],
        "full_protocols": [mapper.format_protocol_for_chat(p) for p in protocols],
    }


@router.get("/recommend/asana/{session_id}")
async def recommend_asana_for_session(session_id: str):
    """Get consistent asana recommendations based on the session's prakriti + symptoms."""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = _sessions[session_id]
    conversation: DiagnosticConversation = session["conversation"]
    prakriti: PrakritiProfile = session["prakriti"]
    mapper = _get_protocol_mapper()

    # Collect all patient messages
    patient_text = " ".join(t.message for t in conversation.turns if t.role == "patient")

    # Get symptom-based protocols
    protocols = mapper.get_protocols_for_text(patient_text, max_protocols=3)

    # Add dosha-based defaults if few symptom matches
    if len(protocols) < 2:
        dosha_protocols = mapper.get_protocols_for_dosha(prakriti.dominant, max_protocols=2)
        seen = {p["name"] for p in protocols}
        for p in dosha_protocols:
            if p["name"] not in seen:
                protocols.append(p)

    return {
        "dominant_dosha": prakriti.dominant,
        "prakriti": prakriti.as_dict(),
        "protocols": [
            {"condition": p["condition"], "protocol_type": p["protocol_type"],
             "name": p["name"], "steps_summary": p.get("steps_summary", "")}
            for p in protocols
        ],
        "full_protocols": [mapper.format_protocol_for_chat(p) for p in protocols],
    }
