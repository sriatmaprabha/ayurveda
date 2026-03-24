"""Prakriti profiling engine — asks gradual questions to determine user's body constitution.

Based on the 20-question Prakriti assessment covering:
- Physical attributes (Q1-5): body frame, weight, skin, hair, eyes
- Physiological traits (Q6-11): digestion, hunger, bowels, sweat, temperature, energy
- Sleep & activity (Q12-14): sleep, walking pace, dreams
- Psychological (Q15-20): speech, learning, stress, emotions, impatience, decisions
"""

from dataclasses import dataclass, field


@dataclass
class PrakritiProfile:
    """Tracks a user's prakriti (constitution) scores across the session."""
    vata: int = 0
    pitta: int = 0
    kapha: int = 0
    questions_asked: list[str] = field(default_factory=list)
    answers_given: dict = field(default_factory=dict)

    @property
    def total_answered(self) -> int:
        return len(self.answers_given)

    @property
    def is_determined(self) -> bool:
        """Prakriti is determined after at least 6 answers with clear dominance."""
        if self.total_answered < 6:
            return False
        total = self.vata + self.pitta + self.kapha
        if total == 0:
            return False
        top = max(self.vata, self.pitta, self.kapha)
        return top / total >= 0.45  # Clear enough dominance

    @property
    def dominant(self) -> str:
        scores = {"Vata": self.vata, "Pitta": self.pitta, "Kapha": self.kapha}
        sorted_s = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top, second = sorted_s[0], sorted_s[1]
        if top[1] > 0 and second[1] > 0 and (top[1] - second[1]) <= 2:
            return f"{top[0]}-{second[0]}"
        return top[0]

    @property
    def percentages(self) -> dict:
        total = max(self.vata + self.pitta + self.kapha, 1)
        return {
            "vata": round(self.vata / total * 100),
            "pitta": round(self.pitta / total * 100),
            "kapha": round(self.kapha / total * 100),
        }

    def score_answer(self, dosha: str):
        if dosha == "vata":
            self.vata += 1
        elif dosha == "pitta":
            self.pitta += 1
        elif dosha == "kapha":
            self.kapha += 1

    def as_dict(self) -> dict:
        return {
            "vata": self.vata,
            "pitta": self.pitta,
            "kapha": self.kapha,
            "dominant": self.dominant,
            "percentages": self.percentages,
            "total_answered": self.total_answered,
            "is_determined": self.is_determined,
        }


# All 20 questions organized by priority — ask the most diagnostic ones first
# Each question has: id, text, category, options (A=vata, B=pitta, C=kapha)
PRAKRITI_QUESTIONS = [
    # High priority — these 6 questions are most discriminating
    {
        "id": "body_frame", "category": "physical", "priority": 1,
        "question": "How would you describe your body frame?",
        "options": {
            "a": {"text": "Thin, lean, or narrow", "dosha": "vata"},
            "b": {"text": "Medium and moderate", "dosha": "pitta"},
            "c": {"text": "Broad, large, or sturdy", "dosha": "kapha"},
        },
    },
    {
        "id": "digestion", "category": "physiological", "priority": 1,
        "question": "How is your digestion?",
        "options": {
            "a": {"text": "Irregular — sometimes good, sometimes not", "dosha": "vata"},
            "b": {"text": "Strong — can digest almost anything", "dosha": "pitta"},
            "c": {"text": "Slow but steady", "dosha": "kapha"},
        },
    },
    {
        "id": "skin", "category": "physical", "priority": 1,
        "question": "How would you describe your skin?",
        "options": {
            "a": {"text": "Dry, rough, or cool to touch", "dosha": "vata"},
            "b": {"text": "Warm, oily, or prone to rashes/acne", "dosha": "pitta"},
            "c": {"text": "Thick, smooth, moist, and cool", "dosha": "kapha"},
        },
    },
    {
        "id": "sleep", "category": "sleep", "priority": 1,
        "question": "How would you describe your sleep?",
        "options": {
            "a": {"text": "Light, tend to wake up easily or disturbed sleep", "dosha": "vata"},
            "b": {"text": "Moderate, sound but don't need much", "dosha": "pitta"},
            "c": {"text": "Deep and heavy, difficult to wake up", "dosha": "kapha"},
        },
    },
    {
        "id": "stress_response", "category": "psychological", "priority": 1,
        "question": "How do you respond to stress?",
        "options": {
            "a": {"text": "Become anxious, worried, or fearful", "dosha": "vata"},
            "b": {"text": "Become irritable, angry, or aggressive", "dosha": "pitta"},
            "c": {"text": "Become withdrawn and avoid confrontation", "dosha": "kapha"},
        },
    },
    {
        "id": "temperature", "category": "physiological", "priority": 1,
        "question": "What is your natural body temperature preference?",
        "options": {
            "a": {"text": "Dislike cold, prefer warmth", "dosha": "vata"},
            "b": {"text": "Dislike heat, prefer cool environments", "dosha": "pitta"},
            "c": {"text": "Comfortable in most conditions, dislike damp/cold", "dosha": "kapha"},
        },
    },
    # Medium priority — refining questions
    {
        "id": "weight", "category": "physical", "priority": 2,
        "question": "How would you describe your body weight?",
        "options": {
            "a": {"text": "Low, difficult to gain weight", "dosha": "vata"},
            "b": {"text": "Moderate, can gain or lose easily", "dosha": "pitta"},
            "c": {"text": "Heavy, easy to gain, difficult to lose", "dosha": "kapha"},
        },
    },
    {
        "id": "energy", "category": "physiological", "priority": 2,
        "question": "How would you describe your energy levels?",
        "options": {
            "a": {"text": "Comes in bursts, quick to start, quick to tire", "dosha": "vata"},
            "b": {"text": "Moderate and focused, goal-driven", "dosha": "pitta"},
            "c": {"text": "Steady and sustained, high endurance", "dosha": "kapha"},
        },
    },
    {
        "id": "bowel", "category": "physiological", "priority": 2,
        "question": "How would you describe your bowel movements?",
        "options": {
            "a": {"text": "Irregular, tendency towards constipation", "dosha": "vata"},
            "b": {"text": "Regular, tendency towards loose stools", "dosha": "pitta"},
            "c": {"text": "Regular, heavy and slow", "dosha": "kapha"},
        },
    },
    {
        "id": "emotions", "category": "psychological", "priority": 2,
        "question": "How would you describe your emotional nature?",
        "options": {
            "a": {"text": "Enthusiastic but anxious, mood changes quickly", "dosha": "vata"},
            "b": {"text": "Passionate but short-tempered", "dosha": "pitta"},
            "c": {"text": "Calm, composed, but can become attached", "dosha": "kapha"},
        },
    },
    # Lower priority — confirming questions
    {
        "id": "hair", "category": "physical", "priority": 3,
        "question": "How would you describe your hair?",
        "options": {
            "a": {"text": "Dry, thin, frizzy, or brittle", "dosha": "vata"},
            "b": {"text": "Fine, soft, or prone to early greying", "dosha": "pitta"},
            "c": {"text": "Thick, oily, wavy, and lustrous", "dosha": "kapha"},
        },
    },
    {
        "id": "eyes", "category": "physical", "priority": 3,
        "question": "How would you describe your eyes?",
        "options": {
            "a": {"text": "Small, dry, or restless", "dosha": "vata"},
            "b": {"text": "Sharp, bright, or sensitive to light", "dosha": "pitta"},
            "c": {"text": "Large, calm, and attractive", "dosha": "kapha"},
        },
    },
    {
        "id": "hunger", "category": "physiological", "priority": 3,
        "question": "How often do you feel hungry?",
        "options": {
            "a": {"text": "Irregularly", "dosha": "vata"},
            "b": {"text": "Frequently, cannot skip meals", "dosha": "pitta"},
            "c": {"text": "Can easily skip meals without discomfort", "dosha": "kapha"},
        },
    },
    {
        "id": "sweat", "category": "physiological", "priority": 3,
        "question": "How do you sweat?",
        "options": {
            "a": {"text": "Minimal sweating", "dosha": "vata"},
            "b": {"text": "Profuse sweating, even in mild heat", "dosha": "pitta"},
            "c": {"text": "Moderate sweating, mostly with exertion", "dosha": "kapha"},
        },
    },
    {
        "id": "speech", "category": "psychological", "priority": 3,
        "question": "How would you describe your speech pattern?",
        "options": {
            "a": {"text": "Fast, talkative, may go off-topic", "dosha": "vata"},
            "b": {"text": "Sharp, clear, and convincing", "dosha": "pitta"},
            "c": {"text": "Slow, calm, and thoughtful", "dosha": "kapha"},
        },
    },
    {
        "id": "learning", "category": "psychological", "priority": 3,
        "question": "How do you learn new things?",
        "options": {
            "a": {"text": "Quickly, but tend to forget quickly too", "dosha": "vata"},
            "b": {"text": "Moderately, focused and analytical", "dosha": "pitta"},
            "c": {"text": "Slowly, but retain for a long time", "dosha": "kapha"},
        },
    },
    {
        "id": "walking", "category": "sleep", "priority": 3,
        "question": "What is your natural walking pace?",
        "options": {
            "a": {"text": "Fast and light", "dosha": "vata"},
            "b": {"text": "Determined and purposeful", "dosha": "pitta"},
            "c": {"text": "Slow and steady", "dosha": "kapha"},
        },
    },
    {
        "id": "dreams", "category": "sleep", "priority": 3,
        "question": "What type of dreams do you usually have?",
        "options": {
            "a": {"text": "Active, fearful, or flying-related", "dosha": "vata"},
            "b": {"text": "Intense, vivid, or conflict-related", "dosha": "pitta"},
            "c": {"text": "Calm, romantic, or water-related", "dosha": "kapha"},
        },
    },
    {
        "id": "decisions", "category": "psychological", "priority": 3,
        "question": "How do you make decisions?",
        "options": {
            "a": {"text": "Quickly, but may change your mind often", "dosha": "vata"},
            "b": {"text": "Decisively and confidently", "dosha": "pitta"},
            "c": {"text": "Slowly and carefully after much thought", "dosha": "kapha"},
        },
    },
    {
        "id": "impatience", "category": "psychological", "priority": 3,
        "question": "Do you struggle with impatience or feelings of jealousy?",
        "options": {
            "a": {"text": "Rarely", "dosha": "vata"},
            "b": {"text": "Sometimes", "dosha": "pitta"},
            "c": {"text": "Often", "dosha": "kapha"},
        },
    },
]


def get_next_questions(profile: PrakritiProfile, count: int = 2) -> list[dict]:
    """Get the next batch of prakriti questions to ask (not yet asked)."""
    asked = set(profile.questions_asked)
    remaining = [q for q in PRAKRITI_QUESTIONS if q["id"] not in asked]
    # Sort by priority (1 first), then return count
    remaining.sort(key=lambda q: q["priority"])
    return remaining[:count]


def format_question_for_chat(question: dict) -> str:
    """Format a prakriti question for natural chat insertion."""
    opts = question["options"]
    return (
        f"{question['question']}\n"
        f"  A) {opts['a']['text']}\n"
        f"  B) {opts['b']['text']}\n"
        f"  C) {opts['c']['text']}"
    )


def parse_answer(answer_text: str, question: dict) -> str | None:
    """Try to parse user's answer to match a dosha option. Returns dosha or None."""
    answer = answer_text.strip().lower()
    opts = question["options"]

    # Direct letter match
    if answer in ("a", "a)", "option a"):
        return opts["a"]["dosha"]
    if answer in ("b", "b)", "option b"):
        return opts["b"]["dosha"]
    if answer in ("c", "c)", "option c"):
        return opts["c"]["dosha"]

    # Keyword match in answer text
    for key, opt in opts.items():
        # Strip punctuation from option words
        opt_words = opt["text"].lower().replace(",", "").replace("/", " ").split()
        significant = [w for w in opt_words if len(w) > 2]
        matches = sum(1 for w in significant if w in answer)
        if matches >= 2 or (len(significant) <= 2 and matches >= 1):
            return opt["dosha"]

    # Dosha name direct match
    if "vata" in answer:
        return "vata"
    if "pitta" in answer:
        return "pitta"
    if "kapha" in answer:
        return "kapha"

    return None
