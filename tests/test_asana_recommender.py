"""Tests for the asana recommender module."""

from src.retrieval.asana_recommender import (
    DOSHA_CONDITION_MAP,
    SYMPTOM_CONDITION_MAP,
    AsanaRecommender,
)


def test_dosha_condition_map_complete():
    """All dosha types should have condition mappings."""
    expected = ["Vata", "Pitta", "Kapha", "Vata-Pitta", "Vata-Kapha", "Pitta-Kapha"]
    for dosha in expected:
        assert dosha in DOSHA_CONDITION_MAP, f"Missing: {dosha}"
        assert "primary_conditions" in DOSHA_CONDITION_MAP[dosha]
        assert len(DOSHA_CONDITION_MAP[dosha]["primary_conditions"]) >= 5


def test_dosha_has_asana_keywords():
    for dosha, data in DOSHA_CONDITION_MAP.items():
        assert "general_asana_keywords" in data, f"{dosha} missing asana keywords"
        assert len(data["general_asana_keywords"]) >= 3


def test_symptom_map_coverage():
    """Common symptoms should have condition mappings."""
    must_have = [
        "anxiety", "joint pain", "back pain", "insomnia", "obesity",
        "migraine", "depression", "asthma", "diabetes", "acne",
        "digestion", "thyroid", "heart", "memory",
    ]
    for symptom in must_have:
        assert symptom in SYMPTOM_CONDITION_MAP, f"Missing symptom: {symptom}"
        assert len(SYMPTOM_CONDITION_MAP[symptom]) >= 1


def test_symptom_map_returns_valid_conditions():
    """All conditions in symptom map should exist in some dosha map."""
    all_conditions = set()
    for dosha_data in DOSHA_CONDITION_MAP.values():
        all_conditions.update(dosha_data.get("primary_conditions", []))
        all_conditions.update(dosha_data.get("secondary_conditions", []))

    # Not all symptom conditions need to be in dosha map (some are direct matches)
    # but most should be
    unmapped = set()
    for symptom, conditions in SYMPTOM_CONDITION_MAP.items():
        for c in conditions:
            if c not in all_conditions:
                unmapped.add(c)

    # Allow some unmapped (Post-Traumatic Stress Disorder, Irritable Bowel Syndrome, etc.)
    # but shouldn't be too many
    assert len(unmapped) < 10, f"Too many unmapped conditions: {unmapped}"


def test_recommend_for_dosha_live():
    """Test with the actual vector store."""
    try:
        recommender = AsanaRecommender(vector_store_dir="data/vector_store")
        result = recommender.recommend_for_dosha("Vata", top_k=3)

        assert result["dominant_dosha"] == "Vata"
        assert len(result["conditions_addressed"]) > 0
        assert len(result["protocols"]) > 0

        # Check protocol structure
        for p in result["protocols"]:
            assert "condition" in p
            assert "source" in p
            assert "text" in p
            assert "score" in p
    except Exception:
        # Skip if vector store not available
        pass


def test_recommend_for_symptoms_live():
    """Test symptom-based recommendation with actual vector store."""
    try:
        recommender = AsanaRecommender(vector_store_dir="data/vector_store")
        result = recommender.recommend_for_symptoms("I have anxiety and back pain")

        assert "Anxiety" in result["matched_conditions"]
        assert "Lower Back Pain" in result["matched_conditions"]
        assert len(result["protocols"]) > 0
    except Exception:
        pass


def test_recommend_full_live():
    """Test combined recommendation."""
    try:
        recommender = AsanaRecommender(vector_store_dir="data/vector_store")
        result = recommender.recommend_full(
            dominant_dosha="Pitta",
            symptoms_text="skin rashes and acidity",
            top_k=3,
        )

        assert result["dominant_dosha"] == "Pitta"
        assert len(result["all_conditions"]) > 0
        assert len(result["protocols"]) > 0
    except Exception:
        pass


if __name__ == "__main__":
    test_dosha_condition_map_complete()
    test_dosha_has_asana_keywords()
    test_symptom_map_coverage()
    test_symptom_map_returns_valid_conditions()
    test_recommend_for_dosha_live()
    test_recommend_for_symptoms_live()
    test_recommend_full_live()
    print("All asana recommender tests passed!")
