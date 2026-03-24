"""Conversational diagnostic engine — every response ends with a follow-up question."""

import logging
from dataclasses import dataclass, field

from .llm_client import LLMClient, LLMConfig
from .prompts import DIAGNOSTIC_SYSTEM_PROMPT, DIAGNOSTIC_QUERY_TEMPLATE

logger = logging.getLogger(__name__)


@dataclass
class ConversationTurn:
    role: str  # "patient" or "vaidya"
    message: str


@dataclass
class DiagnosticConversation:
    """Tracks the full diagnostic conversation with dosha scoring."""
    conversation_id: str = ""
    turns: list[ConversationTurn] = field(default_factory=list)
    vata_score: float = 0.0
    pitta_score: float = 0.0
    kapha_score: float = 0.0
    level: int = 1
    findings: list[str] = field(default_factory=list)

    @property
    def dominant_dosha(self) -> str:
        scores = {"Vata": self.vata_score, "Pitta": self.pitta_score, "Kapha": self.kapha_score}
        sorted_s = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top, second = sorted_s[0], sorted_s[1]
        if top[1] > 0 and second[1] / max(top[1], 0.01) > 0.8:
            return f"{top[0]}-{second[0]}"
        return top[0]

    @property
    def history_text(self) -> str:
        lines = []
        for t in self.turns:
            label = "Patient" if t.role == "patient" else "Vaidya"
            lines.append(f"{label}: {t.message}")
        return "\n\n".join(lines)

    def add_patient_message(self, message: str):
        self.turns.append(ConversationTurn(role="patient", message=message))

    def add_vaidya_response(self, message: str):
        self.turns.append(ConversationTurn(role="vaidya", message=message))


FALLBACK_QUESTIONS = [
    "Can you describe how this affects your daily routine — particularly your sleep, appetite, and energy levels?",
    "When did you first notice these symptoms, and have they been getting better or worse over time?",
    "Do you notice any connection between your symptoms and the time of day, season, or weather?",
    "How would you describe your digestion currently — any bloating, acidity, heaviness, or irregularity?",
    "Is there anything else about your current health that you think might be related to what you've described?",
    "Would you be able to describe what your tongue looks like — its color, any coating, or marks on it?",
    "Have you noticed any changes in your skin, nails, or eyes that might be relevant?",
    "What does your typical daily diet look like — warm or cold foods, heavy or light meals?",
]


import re

# Patterns that indicate casual/greeting messages (not medical queries)
CASUAL_PATTERNS = re.compile(
    r"^\s*("
    r"hi\b|hello\b|hey\b|hii+\b|hola\b|howdy\b"
    r"|good\s*(morning|afternoon|evening|night|day)\b"
    r"|nithyanandam\b|namaste\b|namaskar\b|vanakkam\b"
    r"|thanks?\b|thank\s*you\b|ty\b|thx\b"
    r"|ok\b|okay\b|sure\b|yes\b|yeah\b|yep\b|no\b|nope\b"
    r"|bye\b|goodbye\b|see\s*you\b|take\s*care\b"
    r"|how\s*are\s*you\b|what'?s\s*up\b|sup\b"
    r"|who\s*are\s*you\b|what\s*can\s*you\s*do\b|help\b"
    r"|hmm+\b|oh\b|ah\b|wow\b|nice\b|cool\b|great\b"
    r")\s*[!?.]*\s*$",
    re.IGNORECASE,
)

CASUAL_RESPONSES = {
    "greeting": (
        "Nithyanandam! Welcome. I'm your Ayurvedic diagnostic assistant. "
        "I can help you understand your dosha constitution, recommend yoga asanas, "
        "suggest dietary guidelines, and guide you through classical Ayurvedic treatments.\n\n"
        "What would you like to explore — do you have a specific health concern, "
        "or would you like to start with a dosha assessment?"
    ),
    "thanks": (
        "You're welcome! I'm happy to help with your Ayurvedic journey.\n\n"
        "Is there anything else you'd like to know — perhaps about your diet, "
        "a specific yoga practice, or another health concern?"
    ),
    "bye": (
        "Take care! Remember to maintain a regular daily routine (dinacharya) "
        "and eat according to your constitution.\n\n"
        "Feel free to come back anytime you have questions about your health. "
        "Would you like a quick summary of what we discussed before you go?"
    ),
    "who": (
        "I'm an Ayurvedic diagnostic assistant powered by classical texts — "
        "Charaka Samhita, Sushruta Samhita, Ashtanga Hridaya, and more. "
        "I can help with dosha assessment, yoga recommendations, dietary advice, "
        "and treatment protocols grounded in authentic Ayurveda.\n\n"
        "Would you like to start with a health concern or a general dosha check?"
    ),
    "affirmative": (
        "Great! Let's continue.\n\n"
        "What specific health concern or symptom would you like to discuss?"
    ),
    "filler": (
        "I'm here to help! Feel free to describe any symptoms, health concerns, "
        "or questions about Ayurveda.\n\n"
        "Would you like to start with a dosha assessment, or do you have a specific issue in mind?"
    ),
}


def classify_casual(message: str) -> str | None:
    """Return a casual response category if the message is not a medical query, else None."""
    msg = message.strip()
    if not CASUAL_PATTERNS.match(msg):
        return None

    msg_lower = msg.lower().rstrip("!?. ")
    if any(w in msg_lower for w in ("hi", "hello", "hey", "hii", "morning", "afternoon", "evening",
                                     "night", "nithyanandam", "namaste", "namaskar", "vanakkam", "howdy", "hola")):
        return "greeting"
    if any(w in msg_lower for w in ("thank", "thanks", "ty", "thx")):
        return "thanks"
    if any(w in msg_lower for w in ("bye", "goodbye", "see you", "take care")):
        return "bye"
    if any(w in msg_lower for w in ("who are you", "what can you", "help")):
        return "who"
    if any(w in msg_lower for w in ("ok", "okay", "sure", "yes", "yeah", "yep")):
        return "affirmative"
    return "filler"


class ConversationalDiagnostic:
    """LLM-powered diagnostic conversation that always asks follow-up questions."""

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        config: LLMConfig | None = None,
    ):
        self.llm = llm_client or LLMClient(config)
        self._fallback_idx = 0

    def _ensure_ends_with_question(self, response: str) -> str:
        """Ensure the response ends with a question. Add one if missing."""
        response = response.strip()

        # Check if last sentence is a question
        sentences = response.replace("?\n", "?|||").split("|||")
        last_meaningful = ""
        for s in reversed(sentences):
            s = s.strip()
            if s:
                last_meaningful = s
                break

        if last_meaningful.rstrip().endswith("?"):
            return response

        # Response doesn't end with a question — append a contextual one
        fallback = FALLBACK_QUESTIONS[self._fallback_idx % len(FALLBACK_QUESTIONS)]
        self._fallback_idx += 1
        return f"{response}\n\n{fallback}"

    def respond(
        self,
        conversation: DiagnosticConversation,
        patient_message: str,
        context: str = "",
        asana_context: str = "",
    ) -> str:
        """Generate a diagnostic response that always ends with a follow-up question."""
        conversation.add_patient_message(patient_message)

        prompt = DIAGNOSTIC_QUERY_TEMPLATE.format(
            context=context if context else "No specific context retrieved for this turn.",
            asana_context=asana_context if asana_context else "No specific asana protocols retrieved for this turn.",
            conversation_history=conversation.history_text,
            message=patient_message,
            vata_score=conversation.vata_score,
            pitta_score=conversation.pitta_score,
            kapha_score=conversation.kapha_score,
            dominant_dosha=conversation.dominant_dosha,
            level=conversation.level,
        )

        try:
            response = self.llm.generate(
                prompt=prompt,
                system_prompt=DIAGNOSTIC_SYSTEM_PROMPT,
            )
        except ConnectionError:
            # LLM unavailable — generate a structured text response
            response = self._offline_response(conversation, patient_message)

        response = self._ensure_ends_with_question(response)
        conversation.add_vaidya_response(response)

        return response

    def _offline_response(self, conv: DiagnosticConversation, message: str) -> str:
        """Generate a basic response when LLM is not available."""
        turn_count = len([t for t in conv.turns if t.role == "patient"])
        dominant = conv.dominant_dosha

        if turn_count <= 1:
            return (
                "Thank you for sharing that. I'd like to understand your condition better. "
                "Let me ask you some questions to help identify the root cause.\n\n"
                "First, can you tell me — do you tend to feel more cold, hot, or heavy in your body generally?"
            )
        elif turn_count <= 3:
            return (
                f"Based on what you've described so far, I'm seeing indications of {dominant} involvement. "
                "Let me dig a little deeper to confirm.\n\n"
                "How is your digestion currently? Do you experience gas, acidity, or sluggishness after meals?"
            )
        else:
            return (
                f"Your responses suggest a {dominant} pattern. To personalize the recommendations, "
                "I need a few more details.\n\n"
                "Can you describe your sleep pattern — what time do you sleep, do you wake up during the night, "
                "and how do you feel when you wake up in the morning?"
            )
