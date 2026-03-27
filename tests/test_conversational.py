"""Tests for conversational diagnostic engine."""

from unittest.mock import MagicMock

from src.generation.conversational import (
    ConversationalDiagnostic,
    DiagnosticConversation,
    ConversationTurn,
    FALLBACK_QUESTIONS,
)
from src.generation.llm_client import LLMClient, LLMConfig


def test_conversation_tracks_turns():
    conv = DiagnosticConversation(conversation_id="test1")
    conv.add_patient_message("I have joint pain")
    conv.add_vaidya_response("Tell me more. When did it start?")
    conv.add_patient_message("About 2 weeks ago")

    assert len(conv.turns) == 3
    assert conv.turns[0].role == "patient"
    assert conv.turns[1].role == "vaidya"


def test_conversation_history_text():
    conv = DiagnosticConversation()
    conv.add_patient_message("I feel anxious")
    conv.add_vaidya_response("When does the anxiety peak?")

    history = conv.history_text
    assert "Patient: I feel anxious" in history
    assert "Vaidya: When does the anxiety peak?" in history


def test_dominant_dosha():
    conv = DiagnosticConversation()
    conv.vata_score = 8
    conv.pitta_score = 2
    conv.kapha_score = 1
    assert conv.dominant_dosha == "Vata"

    conv.pitta_score = 7
    assert "Vata" in conv.dominant_dosha and "Pitta" in conv.dominant_dosha


def test_ensure_ends_with_question():
    diag = ConversationalDiagnostic.__new__(ConversationalDiagnostic)
    diag.llm = None
    diag._fallback_idx = 0

    # Already ends with question
    result = diag._ensure_ends_with_question("Here is some info. What time do you sleep?")
    assert result.endswith("?")

    # Does NOT end with question — should append one
    result = diag._ensure_ends_with_question("Here is some information about Vata dosha.")
    assert result.endswith("?")
    assert "daily routine" in result or "sleep" in result or "symptoms" in result


def test_ensure_question_with_multiline():
    diag = ConversationalDiagnostic.__new__(ConversationalDiagnostic)
    diag.llm = None
    diag._fallback_idx = 0

    text = "Line 1.\nLine 2.\nLine 3 some statement."
    result = diag._ensure_ends_with_question(text)
    assert result.rstrip().endswith("?")


def test_ensure_question_preserves_existing():
    diag = ConversationalDiagnostic.__new__(ConversationalDiagnostic)
    diag.llm = None
    diag._fallback_idx = 0

    text = "Your symptoms suggest Vata.\n\nDo you feel cold in your extremities?"
    result = diag._ensure_ends_with_question(text)
    assert result == text  # Should not modify — already ends with question


def test_offline_response_always_invites():
    diag = ConversationalDiagnostic.__new__(ConversationalDiagnostic)
    diag.llm = None
    diag._fallback_idx = 0

    conv = DiagnosticConversation()

    # Turn 1
    conv.add_patient_message("test")
    resp = diag._offline_response(conv, "test")
    assert resp.rstrip().endswith("?") or "tell" in resp.lower() or "share" in resp.lower()

    # Turn 3
    conv.add_patient_message("test2")
    conv.add_patient_message("test3")
    resp = diag._offline_response(conv, "test3")
    assert resp.rstrip().endswith("?") or "tell" in resp.lower()

    # Turn 5
    conv.add_patient_message("test4")
    conv.add_patient_message("test5")
    resp = diag._offline_response(conv, "test5")
    assert resp.rstrip().endswith(".") or resp.rstrip().endswith("?")  # Natural ending


def test_respond_with_mock_llm():
    mock_client = MagicMock(spec=LLMClient)
    mock_client.config = LLMConfig()
    # LLM response that already ends with a question
    mock_client.generate.return_value = (
        "Based on what you've described, this sounds like Vata aggravation in the joints. "
        "Do you notice the pain worsening in cold weather or during windy days?"
    )

    diag = ConversationalDiagnostic(llm_client=mock_client)
    conv = DiagnosticConversation(conversation_id="test_mock")

    response = diag.respond(conv, "My joints are cracking and painful", context="some context")

    assert response.rstrip().endswith("?")
    assert len(conv.turns) == 2  # patient + vaidya
    mock_client.generate.assert_called_once()


def test_respond_appends_question_if_llm_forgets():
    mock_client = MagicMock(spec=LLMClient)
    mock_client.config = LLMConfig()
    # LLM response that does NOT end with a question
    mock_client.generate.return_value = (
        "Triphala is a classical Ayurvedic formulation of three fruits."
    )

    diag = ConversationalDiagnostic(llm_client=mock_client)
    conv = DiagnosticConversation(conversation_id="test_fix")

    response = diag.respond(conv, "Tell me about Triphala", context="some context")

    # Should have appended a fallback question
    assert response.rstrip().endswith("?")
    assert len(response) > len("Triphala is a classical Ayurvedic formulation of three fruits.")


def test_fallback_questions_exist():
    assert len(FALLBACK_QUESTIONS) >= 5
    for q in FALLBACK_QUESTIONS:
        assert q.endswith("?")


if __name__ == "__main__":
    test_conversation_tracks_turns()
    test_conversation_history_text()
    test_dominant_dosha()
    test_ensure_ends_with_question()
    test_ensure_question_with_multiline()
    test_ensure_question_preserves_existing()
    test_offline_response_always_has_question()
    test_respond_with_mock_llm()
    test_respond_appends_question_if_llm_forgets()
    test_fallback_questions_exist()
    print("All conversational tests passed!")
