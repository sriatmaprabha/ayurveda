"""Tests for prakriti profiling and protocol mapping."""

from src.generation.prakriti_profiler import (
    PrakritiProfile, get_next_questions, format_question_for_chat,
    parse_answer, PRAKRITI_QUESTIONS,
)
from src.retrieval.protocol_mapper import ProtocolMapper, CONDITION_ALIASES


def test_prakriti_profile_scoring():
    p = PrakritiProfile()
    p.score_answer("vata")
    p.score_answer("vata")
    p.score_answer("pitta")
    assert p.vata == 2
    assert p.pitta == 1
    assert p.kapha == 0


def test_prakriti_not_determined_early():
    p = PrakritiProfile()
    p.score_answer("vata")
    p.score_answer("vata")
    assert not p.is_determined  # Only 2 answers


def test_prakriti_determined_after_enough():
    p = PrakritiProfile()
    for _ in range(5):
        p.score_answer("vata")
    p.score_answer("pitta")
    p.answers_given = {f"q{i}": "v" for i in range(6)}
    assert p.is_determined
    assert p.dominant == "Vata"


def test_prakriti_dual_dosha():
    p = PrakritiProfile()
    for _ in range(5):
        p.score_answer("vata")
    for _ in range(4):
        p.score_answer("pitta")
    assert "Vata" in p.dominant and "Pitta" in p.dominant


def test_prakriti_percentages():
    p = PrakritiProfile()
    p.vata = 10
    p.pitta = 5
    p.kapha = 5
    pcts = p.percentages
    assert pcts["vata"] == 50
    assert pcts["pitta"] == 25


def test_get_next_questions_priority():
    p = PrakritiProfile()
    qs = get_next_questions(p, count=3)
    assert len(qs) == 3
    # First questions should be priority 1
    assert all(q["priority"] == 1 for q in qs)


def test_get_next_skips_asked():
    p = PrakritiProfile()
    p.questions_asked = ["body_frame", "digestion", "skin"]
    qs = get_next_questions(p, count=2)
    ids = [q["id"] for q in qs]
    assert "body_frame" not in ids
    assert "digestion" not in ids


def test_format_question():
    q = PRAKRITI_QUESTIONS[0]
    text = format_question_for_chat(q)
    assert "body frame" in text.lower()
    assert "A)" in text
    assert "B)" in text
    assert "C)" in text


def test_parse_answer_letter():
    q = PRAKRITI_QUESTIONS[0]  # body frame
    assert parse_answer("A", q) == "vata"
    assert parse_answer("b", q) == "pitta"
    assert parse_answer("C", q) == "kapha"


def test_parse_answer_keyword():
    q = PRAKRITI_QUESTIONS[0]  # body frame
    assert parse_answer("I'm thin and lean", q) == "vata"
    assert parse_answer("medium moderate build", q) == "pitta"
    assert parse_answer("broad and sturdy", q) == "kapha"


def test_parse_answer_dosha_name():
    q = PRAKRITI_QUESTIONS[0]
    assert parse_answer("I think vata", q) == "vata"


def test_parse_answer_no_match():
    q = PRAKRITI_QUESTIONS[0]
    assert parse_answer("I like pizza", q) is None


def test_all_questions_have_required_fields():
    for q in PRAKRITI_QUESTIONS:
        assert "id" in q
        assert "question" in q
        assert "options" in q
        assert "priority" in q
        for key in ("a", "b", "c"):
            assert key in q["options"]
            assert "text" in q["options"][key]
            assert "dosha" in q["options"][key]


def test_twenty_questions_total():
    assert len(PRAKRITI_QUESTIONS) == 20


# Protocol mapper tests

def test_protocol_mapper_loads():
    mapper = ProtocolMapper()
    assert len(mapper.protocols) > 50


def test_protocol_get_care():
    mapper = ProtocolMapper()
    p = mapper.get_protocol("Anxiety", "care")
    assert p is not None
    assert "Care" in p["name"]


def test_protocol_get_cure():
    mapper = ProtocolMapper()
    p = mapper.get_protocol("Anxiety", "cure")
    assert p is not None
    assert "Cure" in p["name"]


def test_protocol_consistency():
    """Same condition should always return the same protocol."""
    mapper = ProtocolMapper()
    p1 = mapper.get_protocol("Arthritis", "cure")
    p2 = mapper.get_protocol("Arthritis", "cure")
    assert p1["steps_summary"] == p2["steps_summary"]
    assert p1["step_details"] == p2["step_details"]


def test_symptom_matching():
    mapper = ProtocolMapper()
    conditions = mapper.match_symptoms("I have anxiety and back pain")
    assert "Anxiety" in conditions
    assert "Lower Back Pain" in conditions


def test_symptom_matching_no_match():
    mapper = ProtocolMapper()
    conditions = mapper.match_symptoms("I like cooking")
    assert len(conditions) == 0


def test_dosha_defaults():
    mapper = ProtocolMapper()
    protocols = mapper.get_protocols_for_dosha("Vata", max_protocols=2)
    assert len(protocols) >= 1
    assert all("name" in p for p in protocols)


def test_format_protocol():
    mapper = ProtocolMapper()
    p = mapper.get_protocol("Anxiety", "cure")
    text = mapper.format_protocol_for_chat(p)
    assert "Cure For Anxiety" in text
    assert "Step 1" in text


if __name__ == "__main__":
    test_prakriti_profile_scoring()
    test_prakriti_not_determined_early()
    test_prakriti_determined_after_enough()
    test_prakriti_dual_dosha()
    test_prakriti_percentages()
    test_get_next_questions_priority()
    test_get_next_skips_asked()
    test_format_question()
    test_parse_answer_letter()
    test_parse_answer_keyword()
    test_parse_answer_dosha_name()
    test_parse_answer_no_match()
    test_all_questions_have_required_fields()
    test_twenty_questions_total()
    test_protocol_mapper_loads()
    test_protocol_get_care()
    test_protocol_get_cure()
    test_protocol_consistency()
    test_symptom_matching()
    test_symptom_matching_no_match()
    test_dosha_defaults()
    test_format_protocol()
    print("All prakriti + protocol tests passed!")
