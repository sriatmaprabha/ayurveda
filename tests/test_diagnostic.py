"""Tests for the multi-level diagnostic engine."""

from src.vision.diagnostic_engine import (
    DiagnosticEngine,
    DiagnosticSession,
    DoshaScore,
    LEVEL1_QUESTIONS,
    LEVEL2_FOLLOWUPS,
    LEVEL3_QUESTIONS,
)
from src.vision.pariksha_prompts import PARIKSHA_PROMPTS


def test_dosha_score_single_dominant():
    score = DoshaScore(vata=8, pitta=3, kapha=2)
    assert score.dominant() == "Vata"

    score = DoshaScore(vata=2, pitta=9, kapha=3)
    assert score.dominant() == "Pitta"

    score = DoshaScore(vata=1, pitta=2, kapha=10)
    assert score.dominant() == "Kapha"


def test_dosha_score_dual_dominant():
    # Within 20% of each other = dual
    score = DoshaScore(vata=8, pitta=7, kapha=2)
    assert "Vata" in score.dominant() and "Pitta" in score.dominant()

    score = DoshaScore(vata=7, pitta=2, kapha=8)
    assert "Kapha" in score.dominant() and "Vata" in score.dominant()


def test_dosha_score_tridosha():
    score = DoshaScore(vata=7, pitta=6, kapha=5)
    assert "Sannipata" in score.dominant() or "Tridosha" in score.dominant()


def test_dosha_score_as_dict():
    score = DoshaScore(vata=5.5, pitta=3.2, kapha=1.8)
    d = score.as_dict()
    assert d["vata"] == 5.5
    assert d["pitta"] == 3.2
    assert d["kapha"] == 1.8
    assert d["dominant"] == "Vata"


def test_level1_questions_exist():
    assert len(LEVEL1_QUESTIONS) >= 5
    for q in LEVEL1_QUESTIONS:
        assert "id" in q
        assert "question" in q
        assert "purpose" in q


def test_level2_followups_all_doshas_covered():
    expected = ["Vata", "Pitta", "Kapha", "Vata-Pitta", "Vata-Kapha", "Pitta-Kapha", "Sannipata (Tridosha)"]
    for dosha in expected:
        assert dosha in LEVEL2_FOLLOWUPS, f"Missing Level 2 for {dosha}"
        assert "questions" in LEVEL2_FOLLOWUPS[dosha]
        assert "image_requests" in LEVEL2_FOLLOWUPS[dosha]
        assert "kb_search" in LEVEL2_FOLLOWUPS[dosha]


def test_level3_questions_exist():
    assert len(LEVEL3_QUESTIONS) >= 4
    ids = [q["id"] for q in LEVEL3_QUESTIONS]
    assert "L3Q1" in ids  # age
    assert "L3Q2" in ids  # season
    assert "L3Q3" in ids  # prakriti


def test_pariksha_prompts_all_types():
    expected_types = ["tongue", "eyes", "nails", "face", "skin", "body", "lips"]
    for t in expected_types:
        assert t in PARIKSHA_PROMPTS, f"Missing pariksha: {t}"
        assert "prompt" in PARIKSHA_PROMPTS[t]
        assert "name" in PARIKSHA_PROMPTS[t]
        assert "level" in PARIKSHA_PROMPTS[t]
        # Each prompt should be substantial
        assert len(PARIKSHA_PROMPTS[t]["prompt"]) > 500, f"{t} prompt too short"


def test_pariksha_prompts_contain_dosha_indicators():
    for ptype, pinfo in PARIKSHA_PROMPTS.items():
        prompt = pinfo["prompt"]
        assert "Vata" in prompt, f"{ptype} prompt missing Vata indicators"
        assert "Pitta" in prompt, f"{ptype} prompt missing Pitta indicators"
        assert "Kapha" in prompt, f"{ptype} prompt missing Kapha indicators"


def test_process_level1_vata():
    """Simulate a Vata-dominant Level 1 assessment."""
    engine = DiagnosticEngine.__new__(DiagnosticEngine)
    engine.image_processor = None
    engine.store = None
    engine.query_engine = None

    responses = [
        {"id": "L1Q2", "answer": "cold", "score": {"vata": 2}},
        {"id": "L1Q3", "answer": "irregular", "score": {"vata": 2}},
        {"id": "L1Q4", "answer": "insomnia", "score": {"vata": 2}},
        {"id": "L1Q5", "answer": "anxious", "score": {"vata": 2}},
        {"id": "L1Q6", "answer": "constipated", "score": {"vata": 2}},
    ]

    session = engine.process_level1(responses)
    assert session.dosha_scores.vata == 10
    assert session.dosha_scores.dominant() == "Vata"
    assert "Vata" in session.current_assessment


def test_process_level1_dual_dosha():
    """Simulate a Vata-Pitta dual dosha assessment."""
    engine = DiagnosticEngine.__new__(DiagnosticEngine)
    engine.image_processor = None
    engine.store = None
    engine.query_engine = None

    responses = [
        {"id": "L1Q2", "answer": "cold", "score": {"vata": 1, "pitta": 1}},
        {"id": "L1Q3", "answer": "gas with acidity", "score": {"vata": 1, "pitta": 1}},
        {"id": "L1Q4", "answer": "insomnia with racing thoughts", "score": {"vata": 1, "pitta": 1}},
        {"id": "L1Q5", "answer": "anxious and irritable", "score": {"vata": 1, "pitta": 1}},
        {"id": "L1Q6", "answer": "alternating", "score": {"vata": 1, "pitta": 1}},
    ]

    session = engine.process_level1(responses)
    dominant = session.dosha_scores.dominant()
    assert "Vata" in dominant and "Pitta" in dominant


def test_diagnostic_session_defaults():
    session = DiagnosticSession()
    assert session.level == 1
    assert session.dosha_scores.vata == 0
    assert len(session.text_responses) == 0
    assert len(session.image_analyses) == 0


if __name__ == "__main__":
    test_dosha_score_single_dominant()
    test_dosha_score_dual_dominant()
    test_dosha_score_tridosha()
    test_dosha_score_as_dict()
    test_level1_questions_exist()
    test_level2_followups_all_doshas_covered()
    test_level3_questions_exist()
    test_pariksha_prompts_all_types()
    test_pariksha_prompts_contain_dosha_indicators()
    test_process_level1_vata()
    test_process_level1_dual_dosha()
    test_diagnostic_session_defaults()
    print("All diagnostic tests passed!")
