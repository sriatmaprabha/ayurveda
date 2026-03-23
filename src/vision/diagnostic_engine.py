"""Multi-level Ayurvedic diagnostic engine combining text Q&A with image-based Pariksha."""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from .image_processor import ImageProcessor
from .pariksha_prompts import PARIKSHA_PROMPTS
from src.embeddings import VectorStore
from src.retrieval import QueryEngine

logger = logging.getLogger(__name__)


@dataclass
class DoshaScore:
    """Tracks dosha imbalance scores across diagnostic levels."""
    vata: float = 0.0
    pitta: float = 0.0
    kapha: float = 0.0

    def dominant(self) -> str:
        scores = {"Vata": self.vata, "Pitta": self.pitta, "Kapha": self.kapha}
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top = sorted_scores[0]
        second = sorted_scores[1]

        # Check for dual dosha (within 20% of each other)
        if top[1] > 0 and second[1] / top[1] > 0.8:
            third = sorted_scores[2]
            # Check for tridosha
            if top[1] > 0 and third[1] / top[1] > 0.6:
                return "Sannipata (Tridosha)"
            return f"{top[0]}-{second[0]}"
        return top[0]

    def as_dict(self) -> dict:
        return {
            "vata": round(self.vata, 2),
            "pitta": round(self.pitta, 2),
            "kapha": round(self.kapha, 2),
            "dominant": self.dominant(),
        }


@dataclass
class DiagnosticSession:
    """Tracks a complete diagnostic session across all levels."""
    session_id: str = ""
    level: int = 1
    dosha_scores: DoshaScore = field(default_factory=DoshaScore)
    text_responses: list[dict] = field(default_factory=list)
    image_analyses: list[dict] = field(default_factory=list)
    kb_references: list[dict] = field(default_factory=list)
    current_assessment: str = ""
    recommended_next: list[str] = field(default_factory=list)


# =============================================================================
# Level 1: Initial symptom questions
# =============================================================================
LEVEL1_QUESTIONS = [
    {
        "id": "L1Q1",
        "question": "What is your primary complaint or concern right now?",
        "type": "open",
        "purpose": "Identify the main symptom area",
    },
    {
        "id": "L1Q2",
        "question": "How would you describe your body temperature preference?",
        "type": "choice",
        "options": [
            {"text": "I feel cold easily, prefer warmth", "score": {"vata": 2}},
            {"text": "I feel hot easily, prefer cool environments", "score": {"pitta": 2}},
            {"text": "I'm comfortable in most temperatures but dislike cold & damp", "score": {"kapha": 2}},
        ],
        "purpose": "Temperature preference maps to dominant dosha",
    },
    {
        "id": "L1Q3",
        "question": "How is your digestion currently?",
        "type": "choice",
        "options": [
            {"text": "Irregular — sometimes hungry, sometimes not, gas/bloating", "score": {"vata": 2}},
            {"text": "Strong hunger, acidity, heartburn if I skip meals", "score": {"pitta": 2}},
            {"text": "Slow, heavy feeling after meals, low appetite", "score": {"kapha": 2}},
            {"text": "Gas/bloating WITH acidity", "score": {"vata": 1, "pitta": 1}},
            {"text": "Low appetite WITH heaviness and bloating", "score": {"vata": 1, "kapha": 1}},
        ],
        "purpose": "Agni (digestive fire) assessment — central to Ayurvedic diagnosis",
    },
    {
        "id": "L1Q4",
        "question": "How is your sleep?",
        "type": "choice",
        "options": [
            {"text": "Light/disturbed, wake up between 2-6 AM, hard to fall asleep", "score": {"vata": 2}},
            {"text": "Moderate, wake up hot/sweating, vivid dreams", "score": {"pitta": 2}},
            {"text": "Deep/heavy, hard to wake up, sleep more than 8 hours", "score": {"kapha": 2}},
            {"text": "Insomnia with racing/angry thoughts", "score": {"vata": 1, "pitta": 1}},
        ],
        "purpose": "Sleep pattern reveals dominant dosha and Manas (mind) state",
    },
    {
        "id": "L1Q5",
        "question": "What is your predominant emotional state recently?",
        "type": "choice",
        "options": [
            {"text": "Anxious, fearful, worried, restless", "score": {"vata": 2}},
            {"text": "Irritable, angry, critical, impatient", "score": {"pitta": 2}},
            {"text": "Lethargic, attached, sad, unmotivated", "score": {"kapha": 2}},
            {"text": "Anxious AND irritable", "score": {"vata": 1, "pitta": 1}},
            {"text": "Anxious AND depressed", "score": {"vata": 1, "kapha": 1}},
            {"text": "Angry AND stubborn/heavy", "score": {"pitta": 1, "kapha": 1}},
        ],
        "purpose": "Manas Pariksha — mental/emotional dosha assessment",
    },
    {
        "id": "L1Q6",
        "question": "How are your bowel movements?",
        "type": "choice",
        "options": [
            {"text": "Constipated, dry, hard, irregular", "score": {"vata": 2}},
            {"text": "Loose, frequent, burning, urgent", "score": {"pitta": 2}},
            {"text": "Heavy, sticky, mucus-like, sluggish", "score": {"kapha": 2}},
            {"text": "Alternating constipation and loose stools", "score": {"vata": 1, "pitta": 1}},
            {"text": "Constipated with mucus", "score": {"vata": 1, "kapha": 1}},
        ],
        "purpose": "Mala Pariksha — waste assessment (Apana Vata region)",
    },
]

# =============================================================================
# Level 2: Targeted follow-ups based on Level 1 + Image requests
# =============================================================================
LEVEL2_FOLLOWUPS = {
    "Vata": {
        "questions": [
            {"id": "L2V1", "question": "Where is the pain/discomfort concentrated?",
             "options": ["Joints", "Lower back", "Abdomen (gas/bloating)", "Head (headaches)", "Whole body (generalized pain)"],
             "purpose": "Localize Vata sub-type (Vyana, Apana, Samana, Prana, Udana)"},
            {"id": "L2V2", "question": "Do your symptoms worsen at specific times?",
             "options": ["2-6 AM or 2-6 PM (Vata time)", "During or after windy/cold weather", "During autumn/early winter", "After travel or erratic schedule", "No specific pattern"],
             "purpose": "Confirm Vata timing patterns (Kala Pariksha)"},
            {"id": "L2V3", "question": "How is your skin and hair currently?",
             "options": ["Very dry, cracking", "Rough but not cracking", "Normal", "Thin/falling hair"],
             "purpose": "Assess Rasa and Asthi dhatu (fluid and bone tissue)"},
        ],
        "image_requests": ["tongue", "face"],
        "kb_search": "Vata vikriti symptoms treatment sub-types Charaka",
    },
    "Pitta": {
        "questions": [
            {"id": "L2P1", "question": "Where is the heat/burning concentrated?",
             "options": ["Stomach/upper abdomen", "Skin (rashes/acne)", "Eyes (burning/red)", "Head (migraines)", "Urinary tract"],
             "purpose": "Localize Pitta sub-type (Pachaka, Bhrajaka, Alochaka, Sadhaka, Ranjaka)"},
            {"id": "L2P2", "question": "Do your symptoms worsen at specific times?",
             "options": ["10 AM-2 PM or 10 PM-2 AM (Pitta time)", "During summer/hot weather", "After spicy/sour food or alcohol", "When stressed/competitive", "No specific pattern"],
             "purpose": "Confirm Pitta timing patterns"},
            {"id": "L2P3", "question": "Have you noticed any bleeding or inflammation?",
             "options": ["Bleeding gums", "Nosebleeds", "Heavy menstruation", "Blood in stool", "Inflammatory skin conditions", "None"],
             "purpose": "Assess Rakta dhatu involvement"},
        ],
        "image_requests": ["tongue", "eyes"],
        "kb_search": "Pitta vikriti symptoms treatment sub-types Pachaka Bhrajaka",
    },
    "Kapha": {
        "questions": [
            {"id": "L2K1", "question": "Where is the heaviness/congestion concentrated?",
             "options": ["Sinuses/respiratory", "Stomach/whole body weight", "Chest/lungs", "Joints (stiffness)", "Head (brain fog)"],
             "purpose": "Localize Kapha sub-type (Tarpaka, Avalambaka, Kledaka, Shleshaka, Bodhaka)"},
            {"id": "L2K2", "question": "Do your symptoms worsen at specific times?",
             "options": ["6-10 AM or 6-10 PM (Kapha time)", "During spring/cold-damp weather", "After heavy/sweet/oily food", "After daytime sleep", "No specific pattern"],
             "purpose": "Confirm Kapha timing patterns"},
            {"id": "L2K3", "question": "How is your energy throughout the day?",
             "options": ["Consistently low/lethargic", "Low in morning, better by afternoon", "Crash after meals", "Generally okay but unmotivated", "Low with breathlessness"],
             "purpose": "Assess Agni and Meda dhatu"},
        ],
        "image_requests": ["tongue", "face"],
        "kb_search": "Kapha vikriti symptoms treatment congestion heaviness",
    },
    "Vata-Pitta": {
        "questions": [
            {"id": "L2VP1", "question": "Which came first — the anxiety/restlessness or the anger/burning?",
             "options": ["Anxiety came first, then irritability developed", "Burning/acidity came first, then anxiety", "They appeared together", "Unsure"],
             "purpose": "Identify primary vs secondary dosha (treat primary first per Ashtanga Hridaya)"},
        ],
        "image_requests": ["tongue", "eyes", "nails"],
        "kb_search": "Vata Pitta dual dosha treatment sequence",
    },
    "Vata-Kapha": {
        "questions": [
            {"id": "L2VK1", "question": "Which bothers you more — the anxiety/dryness or the heaviness/congestion?",
             "options": ["Anxiety and dryness dominate", "Heaviness and congestion dominate", "Both equally", "They alternate"],
             "purpose": "Identify primary dosha and Agni state"},
        ],
        "image_requests": ["tongue", "face", "nails"],
        "kb_search": "Vata Kapha dual dosha Agni treatment",
    },
    "Pitta-Kapha": {
        "questions": [
            {"id": "L2PK1", "question": "Is your congestion/mucus clear or colored (yellow/green)?",
             "options": ["Clear/white mucus", "Yellow/green mucus", "No mucus, but inflammation with weight gain", "Unsure"],
             "purpose": "Colored mucus = Pitta involvement in Kapha, indicates Ama with heat"},
        ],
        "image_requests": ["tongue", "skin"],
        "kb_search": "Pitta Kapha dual dosha Ama treatment",
    },
    "Sannipata (Tridosha)": {
        "questions": [
            {"id": "L2S1", "question": "Are your symptoms contradictory (e.g., feeling hot and cold at the same time)?",
             "options": ["Yes, contradictory symptoms", "Symptoms change rapidly", "Multiple systems affected", "All of the above"],
             "purpose": "Confirm Sannipata — requires experienced Vaidya"},
        ],
        "image_requests": ["tongue", "eyes", "face", "nails"],
        "kb_search": "Sannipata Tridosha treatment Sushruta",
    },
}

# =============================================================================
# Level 3: Deep personalization
# =============================================================================
LEVEL3_QUESTIONS = [
    {"id": "L3Q1", "question": "What is your age group?",
     "options": ["Under 16 (Kapha stage of life)", "16-50 (Pitta stage of life)", "Over 50 (Vata stage of life)"],
     "purpose": "Age affects dosha predominance (Vayah Pariksha)"},
    {"id": "L3Q2", "question": "What is the current season where you are?",
     "options": ["Spring (Vasanta — Kapha)", "Summer (Grishma — Pitta)", "Monsoon (Varsha — Vata)", "Autumn (Sharad — Pitta)", "Early Winter (Hemanta)", "Late Winter (Shishira — Kapha)"],
     "purpose": "Season affects treatment approach (Ritu Pariksha)"},
    {"id": "L3Q3", "question": "What is your birth constitution (Prakriti) if known?",
     "options": ["Vata Prakriti", "Pitta Prakriti", "Kapha Prakriti", "Dual Prakriti", "Don't know"],
     "purpose": "Treatment differs based on Prakriti vs Vikriti gap"},
    {"id": "L3Q4", "question": "How long have you had these symptoms?",
     "options": ["Days (recent/acute)", "Weeks (sub-acute)", "Months (chronic)", "Years (deep-seated)"],
     "purpose": "Duration determines treatment intensity and dhatu depth"},
    {"id": "L3Q5", "question": "How is your physical strength currently?",
     "options": ["Strong — can handle intensive treatment", "Moderate", "Weak — need gentle approach", "Very weak/debilitated"],
     "purpose": "Bala Pariksha — determines if Panchakarma is appropriate or only Shamana (palliative)"},
]


class DiagnosticEngine:
    """Multi-level Ayurvedic diagnostic engine with image-based Pariksha."""

    def __init__(
        self,
        image_processor: ImageProcessor | None = None,
        vector_store_dir: str | Path = "data/vector_store",
        vision_model: str = "llama4",
        vision_base_url: str = "http://localhost:11434/v1",
    ):
        self.image_processor = image_processor or ImageProcessor(
            base_url=vision_base_url,
            model=vision_model,
        )
        self.store = VectorStore(persist_dir=vector_store_dir)
        self.query_engine = QueryEngine(vector_store=self.store, top_k=5)

    def get_level1_questions(self) -> list[dict]:
        """Return Level 1 diagnostic questions."""
        return LEVEL1_QUESTIONS

    def process_level1(self, responses: list[dict]) -> DiagnosticSession:
        """Process Level 1 text responses and determine dominant dosha."""
        session = DiagnosticSession(level=1)
        scores = session.dosha_scores

        for resp in responses:
            session.text_responses.append(resp)
            if "score" in resp:
                score = resp["score"]
                scores.vata += score.get("vata", 0)
                scores.pitta += score.get("pitta", 0)
                scores.kapha += score.get("kapha", 0)

        dominant = scores.dominant()
        session.current_assessment = (
            f"Level 1 Assessment: {dominant} vikriti indicated. "
            f"Scores — Vata: {scores.vata:.1f}, Pitta: {scores.pitta:.1f}, Kapha: {scores.kapha:.1f}"
        )

        # Determine what Level 2 needs
        followup = LEVEL2_FOLLOWUPS.get(dominant, LEVEL2_FOLLOWUPS.get("Vata"))
        session.recommended_next = followup["image_requests"]

        return session

    def get_level2_questions(self, session: DiagnosticSession) -> dict:
        """Return Level 2 questions and image requests based on Level 1 results."""
        dominant = session.dosha_scores.dominant()
        followup = LEVEL2_FOLLOWUPS.get(dominant, LEVEL2_FOLLOWUPS.get("Vata"))

        return {
            "dominant_dosha": dominant,
            "text_questions": followup["questions"],
            "image_requests": [
                {
                    "type": img_type,
                    "name": PARIKSHA_PROMPTS[img_type]["name"],
                    "instruction": f"Please upload a clear photo of your {img_type} for {PARIKSHA_PROMPTS[img_type]['name']}",
                }
                for img_type in followup["image_requests"]
            ],
            "kb_search_query": followup["kb_search"],
        }

    def analyze_image(self, image_path: str | Path, pariksha_type: str) -> dict:
        """Run a specific Pariksha on an uploaded image."""
        if pariksha_type not in PARIKSHA_PROMPTS:
            return {"error": f"Unknown pariksha type: {pariksha_type}. Valid: {list(PARIKSHA_PROMPTS.keys())}"}

        prompt_info = PARIKSHA_PROMPTS[pariksha_type]
        result = self.image_processor.process_image(
            image_path=image_path,
            prompt=prompt_info["prompt"],
            system_prompt="",  # prompt already contains full instructions
        )

        result["pariksha_type"] = pariksha_type
        result["pariksha_name"] = prompt_info["name"]
        result["diagnostic_level"] = prompt_info["level"]
        return result

    def process_level2(
        self,
        session: DiagnosticSession,
        text_responses: list[dict],
        image_results: list[dict],
    ) -> DiagnosticSession:
        """Process Level 2 responses (text + images) and refine diagnosis."""
        session.level = 2

        for resp in text_responses:
            session.text_responses.append(resp)

        for img_result in image_results:
            if img_result.get("error"):
                continue
            session.image_analyses.append(img_result)

        # Search knowledge base for grounded references
        dominant = session.dosha_scores.dominant()
        followup = LEVEL2_FOLLOWUPS.get(dominant, {})
        if followup.get("kb_search"):
            kb_result = self.query_engine.answer_with_sources(followup["kb_search"])
            session.kb_references = kb_result["sources"]

        session.current_assessment = (
            f"Level 2 Assessment: {dominant} vikriti confirmed. "
            f"{len(session.image_analyses)} Pariksha images analyzed. "
            f"{len(session.kb_references)} knowledge base references found."
        )

        return session

    def get_level3_questions(self) -> list[dict]:
        """Return Level 3 personalization questions."""
        return LEVEL3_QUESTIONS

    def process_level3(
        self,
        session: DiagnosticSession,
        responses: list[dict],
    ) -> DiagnosticSession:
        """Process Level 3 personalization and prepare final recommendation."""
        session.level = 3

        for resp in responses:
            session.text_responses.append(resp)

        # Build detailed KB query for personalized treatment
        dominant = session.dosha_scores.dominant()
        age_info = ""
        season_info = ""
        duration_info = ""

        for resp in responses:
            if resp.get("id") == "L3Q1":
                age_info = resp.get("answer", "")
            elif resp.get("id") == "L3Q2":
                season_info = resp.get("answer", "")
            elif resp.get("id") == "L3Q4":
                duration_info = resp.get("answer", "")

        kb_query = f"{dominant} vikriti treatment {age_info} {season_info} {duration_info} diet herbs therapy"
        kb_result = self.query_engine.answer_with_sources(kb_query)
        session.kb_references.extend(kb_result["sources"])

        session.current_assessment = (
            f"Level 3 Assessment: {dominant} vikriti — personalized for "
            f"{age_info}, {season_info}, duration: {duration_info}. "
            f"Ready for Level 4 treatment protocol."
        )

        return session

    def generate_protocol(self, session: DiagnosticSession) -> dict:
        """Generate Level 4 final treatment protocol from all collected data."""
        session.level = 4
        dominant = session.dosha_scores.dominant()

        # Collect all image findings
        image_summary = []
        for img in session.image_analyses:
            if img.get("content"):
                image_summary.append(f"{img['pariksha_name']}: {img['content'][:300]}")

        # Collect KB references
        kb_summary = []
        for ref in session.kb_references:
            kb_summary.append(f"{ref['file']} — {ref['section']}")

        return {
            "session_level": 4,
            "dominant_vikriti": dominant,
            "dosha_scores": session.dosha_scores.as_dict(),
            "total_questions_answered": len(session.text_responses),
            "total_images_analyzed": len(session.image_analyses),
            "image_findings": image_summary,
            "knowledge_base_references": kb_summary,
            "assessment": session.current_assessment,
            "recommendation_context": (
                f"Patient presents with {dominant} vikriti. "
                f"Based on {len(session.text_responses)} responses and "
                f"{len(session.image_analyses)} Pariksha examinations. "
                f"Grounded in {len(session.kb_references)} classical text references."
            ),
        }

    def get_available_pariksha(self) -> list[dict]:
        """List all available Pariksha examinations."""
        return [
            {
                "type": key,
                "name": val["name"],
                "level": val["level"],
            }
            for key, val in PARIKSHA_PROMPTS.items()
        ]
