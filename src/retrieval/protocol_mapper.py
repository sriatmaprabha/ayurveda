"""Fixed asana protocol mapper — deterministic condition-to-protocol mapping.

Instead of vector search (which gives different results each time),
this uses exact condition matching from asana_recommendations.csv.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent
PROTOCOLS_PATH = PROJECT_ROOT / "data" / "asana_protocols.json"

# Condition name normalization — maps user symptoms/conditions to exact protocol names
CONDITION_ALIASES = {
    # Anxiety
    "anxiety": "Anxiety",
    "anxious": "Anxiety",
    "worry": "Anxiety",
    "panic": "Anxiety",
    "nervous": "Anxiety",
    "fear": "Anxiety",
    # Joint/pain
    "joint pain": "Arthritis",
    "arthritis": "Arthritis",
    "knee pain": "Stiff Knees & Knee Pain",
    "knee": "Stiff Knees & Knee Pain",
    "back pain": "Lower Back Pain",
    "lower back": "Lower Back Pain",
    "back": "Lower Back Pain",
    # Sleep
    "insomnia": "Insomnia",
    "sleep": "Insomnia",
    "can't sleep": "Insomnia",
    # Weight
    "obesity": "Obesity",
    "weight": "Obesity",
    "overweight": "Obesity",
    "weight loss": "Obesity",
    # Mental
    "depression": "Depression",
    "depressed": "Depression",
    "sad": "Depression",
    "anger": "Anger",
    "angry": "Anger",
    "irritable": "Anger",
    # Head
    "migraine": "Migraine",
    "headache": "Migraine",
    # Digestion
    "digestion": "Digestive Disorders",
    "digestive": "Digestive Disorders",
    "bloating": "Digestive Disorders",
    "gas": "Digestive Disorders",
    "acidity": "Digestive Disorders",
    "ibs": "Irritable Bowel Syndrome",
    # Respiratory
    "asthma": "Asthma",
    "breathing": "Asthma",
    "sinus": "Sinusitis",
    "sinusitis": "Sinusitis",
    "congestion": "Sinusitis",
    "pulmonary": "Pulmonary Disease",
    # Skin
    "skin": "Skin Problems",
    "acne": "Skin Problems",
    "rash": "Skin Problems",
    "eczema": "Eczema",
    # Metabolic
    "diabetes": "Diabetes",
    "blood sugar": "Diabetes",
    "thyroid": "Thyroid Problems",
    "hypothyroid": "Hypothyroidism",
    # Heart
    "heart": "Heart Diseases",
    "hypertension": "Hypertension",
    "blood pressure": "Hypertension",
    "bp": "Hypertension",
    # Eyes
    "eye": "Short-Sightedness",
    "vision": "Short-Sightedness",
    "short sight": "Short-Sightedness",
    "long sight": "Long Sight",
    # Others
    "memory": "Memory Problems",
    "focus": "Attention Deficit Disorder",
    "concentration": "Memory Problems",
    "vertigo": "Vertigo",
    "dizzy": "Vertigo",
    "tinnitus": "Tinnitus",
    "ear ringing": "Tinnitus",
    "baldness": "Baldness",
    "hair loss": "Baldness",
    "dandruff": "Dandruff",
    "epilepsy": "Epilepsy",
    "seizure": "Epilepsy",
    "infection": "Infection",
    "fungal": "Fungal Infection",
    "allergy": "Food Allergies",
    "hernia": "Hernia",
    "kidney": "Kidney Stones",
    "urinary": "Urinary Problems",
    "menopause": "Hot Flashes in Menopause",
    "hot flashes": "Hot Flashes in Menopause",
    "addiction": "Addiction",
    "colitis": "Ulcerative Colitis And Crohn's Disease",
    "crohn": "Ulcerative Colitis And Crohn's Disease",
    "sweating": "Excessive Sweating Of Palms And Feet",
    "low self esteem": "Low Self Esteem",
    "confidence": "Low Self Esteem",
    "cancer": "Cancer",
    "autism": "Autism",
    "adhd": "Attention Deficit Disorder",
    "bipolar": "Bipolar Disorder",
    "schizophrenia": "Schizophrenia",
    "ptsd": "Post-Traumatic Stress Disorder",
    "trauma": "Post-Traumatic Stress Disorder",
    "ageing": "Ageing",
    "aging": "Ageing",
    "recovery": "Rapid Recovery From Illness",
    "infertility": "Infertility/Impotence",
    "impotence": "Infertility/Impotence",
    "polycystic": "Polycystic Ovaries",
    "pcos": "Polycystic Ovaries",
    "autoimmune": "Autoimmune Disorders",
    "nephrotic": "Nephrotic Syndrome",
    "stress": "Anxiety",
}

# Dosha → default conditions to recommend when no specific symptom matches
DOSHA_DEFAULT_CONDITIONS = {
    "Vata": ["Anxiety", "Arthritis", "Insomnia", "Lower Back Pain"],
    "Pitta": ["Anger", "Skin Problems", "Migraine", "Digestive Disorders"],
    "Kapha": ["Obesity", "Diabetes", "Sinusitis", "Depression"],
    "Vata-Pitta": ["Anxiety", "Migraine", "Insomnia"],
    "Vata-Kapha": ["Arthritis", "Depression", "Asthma"],
    "Pitta-Kapha": ["Diabetes", "Skin Problems", "Hypertension"],
}


class ProtocolMapper:
    """Maps conditions/symptoms to fixed asana protocols from the CSV data."""

    def __init__(self, protocols_path: str | Path = PROTOCOLS_PATH):
        self.protocols = {}
        self._load_protocols(Path(protocols_path))

    def _load_protocols(self, path: Path):
        if not path.exists():
            logger.warning(f"Protocols file not found: {path}")
            return
        with open(path, "r", encoding="utf-8") as f:
            self.protocols = json.load(f)
        logger.info(f"Loaded {len(self.protocols)} asana protocols")

    def get_protocol(self, condition: str, protocol_type: str = "care") -> dict | None:
        """Get a specific Care/Cure protocol for a condition."""
        prefix = "Care For" if protocol_type == "care" else "Cure For"

        # Try exact match
        key = f"{prefix} {condition}"
        if key in self.protocols:
            return {"name": key, **self.protocols[key]}

        # Try case-insensitive
        for k, v in self.protocols.items():
            if k.lower() == key.lower():
                return {"name": k, **v}

        return None

    def match_symptoms(self, text: str) -> list[str]:
        """Extract condition names from user text using keyword matching."""
        text_lower = text.lower()
        matched = set()
        for keyword, condition in CONDITION_ALIASES.items():
            if keyword in text_lower:
                matched.add(condition)
        return sorted(matched)

    def get_protocols_for_text(self, text: str, max_protocols: int = 2) -> list[dict]:
        """Get fixed protocols matching the user's symptom description."""
        conditions = self.match_symptoms(text)
        results = []

        for condition in conditions[:max_protocols]:
            # Prefer "Cure" for direct symptoms, "Care" for general health
            for ptype in ["cure", "care"]:
                protocol = self.get_protocol(condition, ptype)
                if protocol:
                    results.append({
                        "condition": condition,
                        "protocol_type": ptype,
                        **protocol,
                    })
                    break  # One protocol per condition

        return results

    def get_protocols_for_dosha(self, dosha: str, max_protocols: int = 2) -> list[dict]:
        """Get default protocols for a dosha type."""
        conditions = DOSHA_DEFAULT_CONDITIONS.get(dosha, [])
        results = []

        for condition in conditions[:max_protocols]:
            protocol = self.get_protocol(condition, "care")
            if protocol:
                results.append({
                    "condition": condition,
                    "protocol_type": "care",
                    **protocol,
                })

        return results

    def format_protocol_for_chat(self, protocol: dict) -> str:
        """Format a protocol into readable chat text with full instructions."""
        lines = [f"**{protocol['name']}**\n"]

        if protocol.get("steps_summary"):
            lines.append(f"Asanas in sequence: {protocol['steps_summary']}\n")

        for i, step in enumerate(protocol.get("step_details", []), 1):
            # Clean up the step text
            step_clean = step.strip()
            if step_clean:
                lines.append(f"**Step {i}:**\n{step_clean}\n")

        return "\n".join(lines)
