"""Tests for text-based Pariksha alternatives."""

from src.vision.text_pariksha import (
    TEXT_PARIKSHA,
    process_text_pariksha,
    TONGUE_TEXT_QUESTIONS,
    EYES_TEXT_QUESTIONS,
    NAILS_TEXT_QUESTIONS,
    FACE_TEXT_QUESTIONS,
    SKIN_TEXT_QUESTIONS,
    BODY_TEXT_QUESTIONS,
)


def test_all_pariksha_types_have_text():
    """All major Pariksha types should have text alternatives."""
    expected = ["tongue", "eyes", "nails", "face", "skin", "body"]
    for t in expected:
        assert t in TEXT_PARIKSHA, f"Missing text pariksha: {t}"
        assert "questions" in TEXT_PARIKSHA[t]
        assert len(TEXT_PARIKSHA[t]["questions"]) >= 2


def test_all_questions_have_dosha_scores():
    """Every option in every question should have a score dict."""
    for ptype, pdata in TEXT_PARIKSHA.items():
        for q in pdata["questions"]:
            assert "id" in q, f"Missing id in {ptype}"
            assert "question" in q, f"Missing question in {ptype}"
            assert "options" in q, f"Missing options in {ptype} {q['id']}"
            for opt in q["options"]:
                assert "text" in opt, f"Missing text in {ptype} {q['id']}"
                assert "score" in opt, f"Missing score in {ptype} {q['id']}"
                assert "finding" in opt, f"Missing finding in {ptype} {q['id']}"


def test_process_tongue_vata():
    """Simulate a Vata-dominant tongue assessment."""
    responses = [
        {"id": "TP_T1", "answer": "purplish", "score": {"vata": 2}, "finding": "Vata/poor circulation"},
        {"id": "TP_T3", "answer": "cracks", "score": {"vata": 2}, "finding": "Chronic Vata"},
        {"id": "TP_T4", "answer": "dry", "score": {"vata": 2}, "finding": "Vata aggravation"},
    ]
    result = process_text_pariksha("tongue", responses)
    assert result["dosha_scores"]["vata"] == 6
    assert result["input_mode"] == "text"
    assert len(result["findings"]) == 3


def test_process_eyes_pitta():
    responses = [
        {"id": "TP_E1", "answer": "bloodshot", "score": {"pitta": 2}, "finding": "Pitta in Rakta"},
        {"id": "TP_E2", "answer": "burning", "score": {"pitta": 2}, "finding": "Pitta aggravation"},
    ]
    result = process_text_pariksha("eyes", responses)
    assert result["dosha_scores"]["pitta"] == 4
    assert result["pariksha_type"] == "eyes"


def test_process_body_kapha():
    responses = [
        {"id": "TP_B1", "answer": "heavy", "score": {"kapha": 2}, "finding": "Kapha frame"},
        {"id": "TP_B2", "answer": "gains easily", "score": {"kapha": 2}, "finding": "Meda excess"},
        {"id": "TP_B3", "answer": "stiff", "score": {"kapha": 2}, "finding": "Kapha in joints"},
    ]
    result = process_text_pariksha("body", responses)
    assert result["dosha_scores"]["kapha"] == 6


def test_process_invalid_type():
    result = process_text_pariksha("pulse", [])
    assert "error" in result


def test_tongue_questions_count():
    assert len(TONGUE_TEXT_QUESTIONS) == 4


def test_eyes_questions_count():
    assert len(EYES_TEXT_QUESTIONS) == 4


def test_nails_questions_count():
    assert len(NAILS_TEXT_QUESTIONS) == 3


def test_face_questions_count():
    assert len(FACE_TEXT_QUESTIONS) == 4


if __name__ == "__main__":
    test_all_pariksha_types_have_text()
    test_all_questions_have_dosha_scores()
    test_process_tongue_vata()
    test_process_eyes_pitta()
    test_process_body_kapha()
    test_process_invalid_type()
    test_tongue_questions_count()
    test_eyes_questions_count()
    test_nails_questions_count()
    test_face_questions_count()
    print("All text pariksha tests passed!")
