"""Tests for casual message detection — greetings, thanks, etc. should not trigger retrieval."""

from src.generation.conversational import classify_casual, CASUAL_RESPONSES


def test_greetings_detected():
    assert classify_casual("Hi") == "greeting"
    assert classify_casual("hello") == "greeting"
    assert classify_casual("Hey!") == "greeting"
    assert classify_casual("hii") == "greeting"
    assert classify_casual("Good morning") == "greeting"
    assert classify_casual("good evening!") == "greeting"
    assert classify_casual("Nithyanandam") == "greeting"
    assert classify_casual("Namaste") == "greeting"
    assert classify_casual("Vanakkam") == "greeting"


def test_thanks_detected():
    assert classify_casual("Thanks") == "thanks"
    assert classify_casual("Thank you!") == "thanks"
    assert classify_casual("thanks!") == "thanks"


def test_bye_detected():
    assert classify_casual("Bye") == "bye"
    assert classify_casual("Goodbye!") == "bye"
    assert classify_casual("take care") == "bye"


def test_who_detected():
    assert classify_casual("Who are you?") == "who"
    assert classify_casual("What can you do?") == "who"
    assert classify_casual("Help") == "who"


def test_affirmative_detected():
    assert classify_casual("Ok") == "affirmative"
    assert classify_casual("yes") == "affirmative"
    assert classify_casual("Sure") == "affirmative"
    assert classify_casual("yeah") == "affirmative"


def test_filler_detected():
    assert classify_casual("Hmm") == "filler"
    assert classify_casual("nice") == "filler"
    assert classify_casual("cool") == "filler"
    assert classify_casual("wow") == "filler"


def test_medical_queries_not_casual():
    """Real medical queries should NOT be classified as casual."""
    assert classify_casual("I have joint pain") is None
    assert classify_casual("What helps with anxiety?") is None
    assert classify_casual("My skin is dry and cracking") is None
    assert classify_casual("Tell me about Triphala") is None
    assert classify_casual("What yoga asanas for back pain?") is None
    assert classify_casual("I feel bloated after meals") is None
    assert classify_casual("Hi, I have a headache") is None  # has medical content after greeting
    assert classify_casual("Good morning, my knees hurt") is None  # ditto
    assert classify_casual("What is Vata dosha?") is None
    assert classify_casual("How to balance Pitta?") is None


def test_all_casual_responses_end_with_question():
    """Every casual response should end with a question to keep conversation going."""
    for key, response in CASUAL_RESPONSES.items():
        assert response.rstrip().endswith("?"), f"Casual response '{key}' doesn't end with a question"


def test_casual_responses_all_categories_exist():
    expected = ["greeting", "thanks", "bye", "who", "affirmative", "filler"]
    for cat in expected:
        assert cat in CASUAL_RESPONSES, f"Missing casual response: {cat}"


if __name__ == "__main__":
    test_greetings_detected()
    test_thanks_detected()
    test_bye_detected()
    test_who_detected()
    test_affirmative_detected()
    test_filler_detected()
    test_medical_queries_not_casual()
    test_all_casual_responses_end_with_question()
    test_casual_responses_all_categories_exist()
    print("All casual detection tests passed!")
