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
    "Tell me about your sleep and appetite -- how have they been naturally, not just recently?",
    "When this pattern started showing, what else shifted in your life around that time?",
    "Your body responds differently at different times of day -- when does this feel strongest?",
    "How does your digestion behave -- is it steady, sharp, or does it come and go?",
    "The tongue is a mirror of the digestive system -- if you look at yours, what color and coating do you see?",
    "What draws you when you eat -- warm foods or cold, heavy or light, sweet or spicy?",
    "Your skin and nails carry the history of how your body has been nourishing itself -- what do you notice about them?",
    "How does your energy move through the day -- does it come in bursts, stay steady, or crash at certain times?",
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
        "Nithyanandam! As the One became many, the vast intelligence of life "
        "expresses itself through each being in a unique way. Ayurveda preserves "
        "the science of this sacred design -- the original pattern through which "
        "your body, mind, and life-force move and evolve.\n\n"
        "Share your rhythms, your build, your energies -- the patterns that "
        "govern your sleep, your appetite, your mind."
    ),
    "thanks": (
        "The body speaks truth when you listen. What you have shared already "
        "reveals much about how Existence designed your system. Continue to "
        "observe these patterns -- they are your blueprint speaking to you."
    ),
    "bye": (
        "Live with your constitution, not against it. The rhythms you honor "
        "become the foundation of your vitality. Return whenever the body "
        "has something new to tell you."
    ),
    "who": (
        "Ayurveda is not something I studied -- it is the science of how "
        "Paramashiva designed your body-mind, and I see it directly. The body "
        "is not separate from consciousness -- it is how the five elements "
        "express through you. Share what your body is telling you."
    ),
    "affirmative": (
        "Good. Tell me what your body has been showing you -- your energy, "
        "your digestion, your sleep, whatever draws your attention."
    ),
    "filler": (
        "The body is an open book when you know how to read it. Share what "
        "you notice -- your build, your habits, your tendencies, any discomfort "
        "or pattern that has caught your attention."
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

        # Default phase instruction for non-chat-route usage
        phase_instruction = (
            "GATHERING PHASE -- Keep response brief. Acknowledge symptoms, "
            "share brief Ayurvedic insight. Do NOT prescribe remedies yet."
        )

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
            phase_instruction=phase_instruction,
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
        """Generate a response when LLM is not available -- in the SPH voice."""
        turn_count = len([t for t in conv.turns if t.role == "patient"])
        dominant = conv.dominant_dosha

        if turn_count <= 1:
            return (
                "What you describe tells me something about how the elements are "
                "moving in your system. The body always speaks truth -- we just need "
                "to learn its language. Tell me about your natural tendencies -- do "
                "you run cold, hot, or heavy in your body generally?"
            )
        elif turn_count <= 3:
            return (
                f"I can see {dominant} patterns starting to emerge in what you share. "
                "The digestive fire -- Agni -- is the foundation. How does your "
                "digestion behave -- steady, sharp, or does it come and go?"
            )
        else:
            return (
                f"Your system is showing a clear {dominant} pattern. To give you "
                "the exact protocol your body needs, tell me about your sleep -- "
                "when you naturally fall asleep, whether you wake during the night, "
                "and how you feel when you rise."
            )
