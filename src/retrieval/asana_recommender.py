"""Maps dosha imbalances and health conditions to specific yoga asana protocols."""

import logging
from pathlib import Path

from src.embeddings import VectorStore
from src.retrieval.query_engine import QueryEngine

logger = logging.getLogger(__name__)

# =============================================================================
# Dosha → Common Conditions mapping
# Based on classical Ayurvedic texts (Charaka, Sushruta, Ashtanga Hridaya)
# =============================================================================
DOSHA_CONDITION_MAP = {
    "Vata": {
        "primary_conditions": [
            "Anxiety", "Arthritis", "Insomnia", "Lower Back Pain",
            "Depression", "Stiff Knees & Knee Pain", "Memory Problems",
            "Epilepsy", "Vertigo", "Tinnitus",
        ],
        "secondary_conditions": [
            "Digestive Disorders", "Baldness", "Schizophrenia",
            "Attention Deficit Disorder", "Bipolar Disorder",
        ],
        "general_asana_keywords": [
            "grounding", "calming", "seated", "forward bend",
            "hip opener", "warm", "gentle", "restorative",
        ],
    },
    "Pitta": {
        "primary_conditions": [
            "Anger", "Skin Problems", "Acidity", "Hypertension",
            "Migraine", "Heart Diseases", "Ulcerative Colitis And Crohn's Disease",
            "Hot Flashes in Menopause", "Eczema", "Excessive Sweating Of Palms And Feet",
        ],
        "secondary_conditions": [
            "Diabetes", "Infection", "Food Allergies", "Fungal Infection",
            "Dandruff", "Achromatopsia",
        ],
        "general_asana_keywords": [
            "cooling", "relaxing", "moon", "forward bend",
            "twist", "moderate", "non-competitive",
        ],
    },
    "Kapha": {
        "primary_conditions": [
            "Obesity", "Diabetes", "Asthma", "Sinusitis",
            "Hypothyroidism", "Pulmonary Disease", "Depression",
            "Low Self Esteem", "Nephrotic Syndrome", "Kidney Stones",
        ],
        "secondary_conditions": [
            "Hernia", "Polycystic Ovaries", "Autoimmune Disorders",
            "Addiction", "Thyroid Problems",
        ],
        "general_asana_keywords": [
            "energizing", "vigorous", "standing", "backbend",
            "sun salutation", "dynamic", "heating", "stimulating",
        ],
    },
    "Vata-Pitta": {
        "primary_conditions": [
            "Anxiety", "Migraine", "Insomnia", "Skin Problems",
            "Irritable Bowel Syndrome", "Bipolar Disorder",
        ],
        "general_asana_keywords": ["calming", "cooling", "gentle", "restorative"],
    },
    "Vata-Kapha": {
        "primary_conditions": [
            "Asthma", "Depression", "Obesity", "Arthritis",
            "Lower Back Pain", "Memory Problems",
        ],
        "general_asana_keywords": ["warming", "stimulating", "grounding", "dynamic"],
    },
    "Pitta-Kapha": {
        "primary_conditions": [
            "Diabetes", "Obesity", "Hypertension", "Heart Diseases",
            "Skin Problems", "Thyroid Problems",
        ],
        "general_asana_keywords": ["cooling", "light", "drying", "moderate"],
    },
}

# Symptom keyword → condition mapping for natural language matching
SYMPTOM_CONDITION_MAP = {
    "anxiety": ["Anxiety"],
    "stress": ["Anxiety"],
    "worried": ["Anxiety"],
    "fearful": ["Anxiety"],
    "joint pain": ["Arthritis", "Stiff Knees & Knee Pain"],
    "knee pain": ["Stiff Knees & Knee Pain"],
    "back pain": ["Lower Back Pain"],
    "lower back": ["Lower Back Pain"],
    "can't sleep": ["Insomnia"],
    "insomnia": ["Insomnia"],
    "sleep problem": ["Insomnia"],
    "weight gain": ["Obesity"],
    "overweight": ["Obesity"],
    "obesity": ["Obesity"],
    "headache": ["Migraine"],
    "migraine": ["Migraine"],
    "anger": ["Anger"],
    "irritable": ["Anger"],
    "sad": ["Depression"],
    "depression": ["Depression"],
    "depressed": ["Depression"],
    "breathing": ["Asthma", "Pulmonary Disease"],
    "asthma": ["Asthma"],
    "sinus": ["Sinusitis"],
    "congestion": ["Sinusitis"],
    "skin rash": ["Skin Problems", "Eczema"],
    "acne": ["Skin Problems"],
    "eczema": ["Eczema"],
    "acidity": ["Digestive Disorders"],
    "digestion": ["Digestive Disorders"],
    "bloating": ["Digestive Disorders", "Irritable Bowel Syndrome"],
    "diabetes": ["Diabetes"],
    "blood sugar": ["Diabetes"],
    "blood pressure": ["Hypertension"],
    "high bp": ["Hypertension"],
    "heart": ["Heart Diseases"],
    "thyroid": ["Thyroid Problems", "Hypothyroidism"],
    "hair loss": ["Baldness"],
    "baldness": ["Baldness"],
    "memory": ["Memory Problems"],
    "forgetful": ["Memory Problems"],
    "vertigo": ["Vertigo"],
    "dizzy": ["Vertigo"],
    "tinnitus": ["Tinnitus"],
    "ear ringing": ["Tinnitus"],
    "infertility": ["Infertility/Impotence"],
    "menopause": ["Hot Flashes in Menopause"],
    "hot flashes": ["Hot Flashes in Menopause"],
    "addiction": ["Addiction"],
    "sweating": ["Excessive Sweating Of Palms And Feet"],
    "epilepsy": ["Epilepsy"],
    "seizure": ["Epilepsy"],
    "autism": ["Autism"],
    "adhd": ["Attention Deficit Disorder"],
    "focus": ["Attention Deficit Disorder"],
    "concentration": ["Attention Deficit Disorder", "Memory Problems"],
    "cancer": ["Cancer"],
    "hernia": ["Hernia"],
    "kidney": ["Nephrotic Syndrome", "Kidney Stones"],
    "urinary": ["Urinary Problems"],
    "dandruff": ["Dandruff"],
    "fungal": ["Fungal Infection"],
    "allergy": ["Food Allergies"],
    "ibs": ["Irritable Bowel Syndrome"],
    "colitis": ["Ulcerative Colitis And Crohn's Disease"],
    "ptsd": ["Post-Traumatic Stress Disorder"],
    "trauma": ["Post-Traumatic Stress Disorder"],
    "eye sight": ["Short-Sightedness", "Long Sight"],
    "vision": ["Short-Sightedness", "Long Sight", "Achromatopsia"],
    "self esteem": ["Low Self Esteem"],
    "confidence": ["Low Self Esteem"],
}


class AsanaRecommender:
    """Recommends yoga asana protocols based on dosha and symptoms."""

    def __init__(self, vector_store_dir: str | Path = "data/vector_store"):
        self.store = VectorStore(persist_dir=vector_store_dir)
        self.query_engine = QueryEngine(vector_store=self.store, top_k=5)

    def recommend_for_dosha(self, dominant_dosha: str, top_k: int = 3) -> dict:
        """Get asana recommendations for a specific dosha imbalance."""
        dosha_info = DOSHA_CONDITION_MAP.get(dominant_dosha, {})
        conditions = dosha_info.get("primary_conditions", [])[:5]

        recommendations = []
        for condition in conditions:
            # Search for both Care and Cure protocols
            for prefix in ["Care For", "Cure For"]:
                query = f"{prefix} {condition} asana yoga kriya"
                results = self.query_engine.retrieve(query, top_k=2)
                for r in results:
                    if r["score"] > 0.35:
                        recommendations.append({
                            "condition": condition,
                            "protocol_type": prefix.split()[0].lower(),
                            "source": r["metadata"].get("file_name", ""),
                            "section": r["metadata"].get("section_title", ""),
                            "text": r["text"][:500],
                            "score": r["score"],
                        })

        # Deduplicate by section title
        seen = set()
        unique_recs = []
        for r in sorted(recommendations, key=lambda x: x["score"], reverse=True):
            key = r["section"]
            if key not in seen:
                seen.add(key)
                unique_recs.append(r)

        return {
            "dominant_dosha": dominant_dosha,
            "conditions_addressed": conditions,
            "keywords": dosha_info.get("general_asana_keywords", []),
            "protocols": unique_recs[:top_k * 2],
        }

    def recommend_for_symptoms(self, symptoms_text: str, top_k: int = 5) -> dict:
        """Match symptoms to conditions and return asana recommendations."""
        symptoms_lower = symptoms_text.lower()

        # Find matching conditions from symptom keywords
        matched_conditions = set()
        for keyword, conditions in SYMPTOM_CONDITION_MAP.items():
            if keyword in symptoms_lower:
                matched_conditions.update(conditions)

        recommendations = []

        # Search for each matched condition
        for condition in matched_conditions:
            for prefix in ["Care For", "Cure For"]:
                query = f"{prefix} {condition} asana yoga"
                results = self.query_engine.retrieve(query, top_k=2)
                for r in results:
                    if r["score"] > 0.30:
                        recommendations.append({
                            "condition": condition,
                            "protocol_type": prefix.split()[0].lower(),
                            "source": r["metadata"].get("file_name", ""),
                            "section": r["metadata"].get("section_title", ""),
                            "text": r["text"][:500],
                            "score": r["score"],
                        })

        # Also do a direct search with the raw symptoms text
        direct_results = self.query_engine.retrieve(
            f"yoga asana for {symptoms_text}", top_k=top_k
        )
        for r in direct_results:
            if r["score"] > 0.35:
                recommendations.append({
                    "condition": "Direct match",
                    "protocol_type": "general",
                    "source": r["metadata"].get("file_name", ""),
                    "section": r["metadata"].get("section_title", ""),
                    "text": r["text"][:500],
                    "score": r["score"],
                })

        # Deduplicate and sort
        seen = set()
        unique_recs = []
        for r in sorted(recommendations, key=lambda x: x["score"], reverse=True):
            key = r["section"]
            if key not in seen:
                seen.add(key)
                unique_recs.append(r)

        return {
            "symptoms": symptoms_text,
            "matched_conditions": sorted(matched_conditions),
            "protocols": unique_recs[:top_k * 2],
        }

    def recommend_full(
        self,
        dominant_dosha: str,
        symptoms_text: str = "",
        top_k: int = 5,
    ) -> dict:
        """Combined recommendation using both dosha and symptom matching."""
        dosha_recs = self.recommend_for_dosha(dominant_dosha, top_k)
        symptom_recs = (
            self.recommend_for_symptoms(symptoms_text, top_k)
            if symptoms_text
            else {"matched_conditions": [], "protocols": []}
        )

        # Merge and deduplicate
        all_protocols = dosha_recs["protocols"] + symptom_recs["protocols"]
        seen = set()
        merged = []
        for r in sorted(all_protocols, key=lambda x: x["score"], reverse=True):
            key = r["section"]
            if key not in seen:
                seen.add(key)
                merged.append(r)

        all_conditions = set(dosha_recs["conditions_addressed"])
        all_conditions.update(symptom_recs.get("matched_conditions", []))

        return {
            "dominant_dosha": dominant_dosha,
            "all_conditions": sorted(all_conditions),
            "dosha_keywords": dosha_recs["keywords"],
            "protocols": merged[:top_k * 2],
            "total_recommendations": len(merged),
        }
