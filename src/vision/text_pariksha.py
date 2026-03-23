"""Text-based Pariksha alternatives — users describe symptoms instead of uploading images."""

# =============================================================================
# Each Pariksha has multiple-choice questions that mirror what
# the vision model would detect from an image
# =============================================================================

TONGUE_TEXT_QUESTIONS = [
    {
        "id": "TP_T1",
        "question": "What color is your tongue?",
        "options": [
            {"text": "Pale or whitish", "score": {"kapha": 2}, "finding": "Kapha/Rasa dhatu deficiency"},
            {"text": "Normal pink", "score": {}, "finding": "Balanced"},
            {"text": "Red or dark red", "score": {"pitta": 2}, "finding": "Pitta aggravation"},
            {"text": "Purplish or bluish", "score": {"vata": 2}, "finding": "Vata/poor circulation"},
        ],
    },
    {
        "id": "TP_T2",
        "question": "Does your tongue have a coating? What does it look like?",
        "options": [
            {"text": "No coating, clean", "score": {}, "finding": "Healthy Agni, no Ama"},
            {"text": "Thick white coating", "score": {"kapha": 2}, "finding": "Kapha imbalance, Ama accumulation"},
            {"text": "Yellow or greenish coating", "score": {"pitta": 2}, "finding": "Pitta imbalance, liver involvement"},
            {"text": "Brown or dark coating", "score": {"vata": 1, "pitta": 1}, "finding": "Chronic toxicity"},
            {"text": "Coating mostly at the back", "score": {"kapha": 1}, "finding": "Deep-seated Ama"},
        ],
    },
    {
        "id": "TP_T3",
        "question": "Do you notice any marks or texture on your tongue?",
        "options": [
            {"text": "Tooth marks on the edges", "score": {"kapha": 2}, "finding": "Malabsorption, Kapha accumulation"},
            {"text": "Cracks or fissures", "score": {"vata": 2}, "finding": "Chronic Vata, Rasa dhatu depletion"},
            {"text": "A deep crack down the center", "score": {"vata": 1}, "finding": "Spinal/emotional stress, Majja dhatu"},
            {"text": "Tongue trembles when extended", "score": {"vata": 2}, "finding": "Vata in nervous system"},
            {"text": "Smooth, no special marks", "score": {}, "finding": "Normal"},
        ],
    },
    {
        "id": "TP_T4",
        "question": "How does your tongue feel in terms of moisture?",
        "options": [
            {"text": "Very dry", "score": {"vata": 2}, "finding": "Vata aggravation, dehydration"},
            {"text": "Normal moisture", "score": {}, "finding": "Balanced"},
            {"text": "Excessively moist or slimy", "score": {"kapha": 2}, "finding": "Kapha/Ama excess"},
        ],
    },
]

EYES_TEXT_QUESTIONS = [
    {
        "id": "TP_E1",
        "question": "What does the white of your eyes look like?",
        "options": [
            {"text": "Clear white", "score": {}, "finding": "Balanced"},
            {"text": "Yellowish tint", "score": {"pitta": 2}, "finding": "Pitta, liver involvement"},
            {"text": "Reddish or bloodshot", "score": {"pitta": 2}, "finding": "Pitta in Rakta dhatu"},
            {"text": "Muddy or dull", "score": {"kapha": 1}, "finding": "Kapha, Ama"},
            {"text": "Bluish tint", "score": {"vata": 2}, "finding": "Vata, poor oxygenation"},
        ],
    },
    {
        "id": "TP_E2",
        "question": "How do your eyes feel?",
        "options": [
            {"text": "Dry, gritty, tired", "score": {"vata": 2}, "finding": "Vata, Alochaka Pitta depleted"},
            {"text": "Burning, sensitive to light", "score": {"pitta": 2}, "finding": "Pitta aggravation"},
            {"text": "Watery, heavy, itchy", "score": {"kapha": 2}, "finding": "Kapha excess"},
            {"text": "Fine, no complaints", "score": {}, "finding": "Balanced"},
        ],
    },
    {
        "id": "TP_E3",
        "question": "What do you notice around your eyes?",
        "options": [
            {"text": "Dark bluish circles", "score": {"vata": 2}, "finding": "Vata aggravation, disturbed Vyana Vata"},
            {"text": "Dark brownish circles", "score": {"pitta": 1}, "finding": "Pitta, liver/blood involvement"},
            {"text": "Puffy or swollen under-eyes", "score": {"kapha": 2}, "finding": "Kapha accumulation, kidney involvement"},
            {"text": "Sunken or hollow", "score": {"vata": 2}, "finding": "Vata, tissue depletion"},
            {"text": "Normal, no circles or puffiness", "score": {}, "finding": "Healthy"},
        ],
    },
    {
        "id": "TP_E4",
        "question": "How would you describe the brightness of your eyes?",
        "options": [
            {"text": "Bright and alert", "score": {}, "finding": "Strong Ojas"},
            {"text": "Dull and lifeless", "score": {"vata": 1, "kapha": 1}, "finding": "Depleted Ojas"},
            {"text": "Sharp, intense, piercing", "score": {"pitta": 1}, "finding": "Pitta excess, elevated Tejas"},
        ],
    },
]

NAILS_TEXT_QUESTIONS = [
    {
        "id": "TP_N1",
        "question": "What color are your nails?",
        "options": [
            {"text": "Pale or whitish", "score": {"kapha": 1}, "finding": "Anemia, Rasa dhatu deficiency"},
            {"text": "Healthy pink", "score": {}, "finding": "Balanced Rakta dhatu"},
            {"text": "Reddish", "score": {"pitta": 1}, "finding": "Pitta, Rakta aggravation"},
            {"text": "Yellowish", "score": {"pitta": 2}, "finding": "Pitta, liver involvement"},
            {"text": "Bluish or purplish", "score": {"vata": 2}, "finding": "Vata, poor circulation"},
        ],
    },
    {
        "id": "TP_N2",
        "question": "How would you describe your nail texture?",
        "options": [
            {"text": "Brittle, break easily, thin", "score": {"vata": 2}, "finding": "Vata, Asthi dhatu depletion"},
            {"text": "Flexible and medium strength", "score": {}, "finding": "Pitta constitution, balanced"},
            {"text": "Thick, strong, hard", "score": {"kapha": 1}, "finding": "Kapha constitution"},
            {"text": "Vertical ridges visible", "score": {"vata": 2}, "finding": "Vata, malabsorption"},
            {"text": "Horizontal ridges (grooves)", "score": {"vata": 1, "pitta": 1}, "finding": "Past severe illness, dhatu disruption"},
            {"text": "Splitting or peeling", "score": {"vata": 2}, "finding": "Vata, dryness, depleted"},
        ],
    },
    {
        "id": "TP_N3",
        "question": "Check the half-moon (lunula) at the base of your nails. Where can you see them?",
        "options": [
            {"text": "Visible on most or all fingers", "score": {}, "finding": "Strong Agni, good metabolism"},
            {"text": "Only visible on thumbs", "score": {"vata": 1, "kapha": 1}, "finding": "Weak Agni, compromised digestion"},
            {"text": "Not visible on any finger", "score": {"vata": 2, "kapha": 1}, "finding": "Severely depleted Agni"},
            {"text": "Very large moons", "score": {"kapha": 2}, "finding": "Kapha excess, possible thyroid"},
        ],
    },
]

FACE_TEXT_QUESTIONS = [
    {
        "id": "TP_F1",
        "question": "How would you describe your facial skin?",
        "options": [
            {"text": "Dry, thin, cool to touch", "score": {"vata": 2}, "finding": "Vata skin type"},
            {"text": "Warm, sensitive, prone to redness", "score": {"pitta": 2}, "finding": "Pitta skin type"},
            {"text": "Oily, thick, smooth, cool", "score": {"kapha": 2}, "finding": "Kapha skin type"},
            {"text": "Combination — oily T-zone, dry cheeks", "score": {"vata": 1, "kapha": 1}, "finding": "Vata-Kapha dual"},
        ],
    },
    {
        "id": "TP_F2",
        "question": "If you have acne or blemishes, where do they appear most?",
        "options": [
            {"text": "Forehead", "score": {"pitta": 1, "vata": 1}, "finding": "Digestive issues — Pachaka Pitta / Samana Vata"},
            {"text": "Between eyebrows", "score": {"pitta": 2}, "finding": "Liver stress — Ranjaka Pitta"},
            {"text": "Cheeks", "score": {"kapha": 2}, "finding": "Respiratory/stomach — Avalambaka Kapha"},
            {"text": "Jawline and chin", "score": {"vata": 1}, "finding": "Hormonal/reproductive — Apana Vata"},
            {"text": "Nose area", "score": {"pitta": 1}, "finding": "Cardiovascular — Sadhaka Pitta"},
            {"text": "No acne or blemishes", "score": {}, "finding": "Healthy skin"},
        ],
    },
    {
        "id": "TP_F3",
        "question": "How does your complexion look overall?",
        "options": [
            {"text": "Dull, grayish, lifeless", "score": {"vata": 1, "kapha": 1}, "finding": "Ama present, poor digestion"},
            {"text": "Bright, lustrous, glowing", "score": {}, "finding": "Strong Ojas, healthy"},
            {"text": "Flushed, reddish, hot-looking", "score": {"pitta": 2}, "finding": "Pitta in Rakta dhatu"},
            {"text": "Pale, washed out", "score": {"kapha": 1}, "finding": "Kapha, possible anemia (Pandu)"},
        ],
    },
    {
        "id": "TP_F4",
        "question": "How are your lips?",
        "options": [
            {"text": "Dry, cracked, peeling", "score": {"vata": 2}, "finding": "Vata aggravation"},
            {"text": "Red, inflamed, or burning", "score": {"pitta": 2}, "finding": "Pitta in Rasa/Rakta"},
            {"text": "Pale, swollen, or moist", "score": {"kapha": 1}, "finding": "Kapha, Rasa deficiency"},
            {"text": "Normal — soft and pink", "score": {}, "finding": "Balanced"},
            {"text": "Cracks at the corners (angular cheilitis)", "score": {"vata": 1, "pitta": 1}, "finding": "Vata-Pitta, B-vitamin deficiency"},
        ],
    },
]

SKIN_TEXT_QUESTIONS = [
    {
        "id": "TP_S1",
        "question": "How is your skin's texture and moisture overall?",
        "options": [
            {"text": "Dry, rough, cracked, flaky", "score": {"vata": 2}, "finding": "Vata aggravation"},
            {"text": "Warm, slightly oily, sensitive", "score": {"pitta": 1}, "finding": "Pitta skin"},
            {"text": "Thick, oily, cool, smooth", "score": {"kapha": 2}, "finding": "Kapha skin"},
            {"text": "Normal — not too dry, not too oily", "score": {}, "finding": "Balanced"},
        ],
    },
    {
        "id": "TP_S2",
        "question": "Do you have any skin conditions currently?",
        "options": [
            {"text": "Eczema or psoriasis (dry, scaling, itchy)", "score": {"vata": 2}, "finding": "Vata-dominant Kushtha"},
            {"text": "Rashes, hives, burning redness", "score": {"pitta": 2}, "finding": "Pitta-dominant Kushtha"},
            {"text": "Cystic acne, fungal infections, oozing", "score": {"kapha": 2}, "finding": "Kapha-dominant Kushtha"},
            {"text": "Vitiligo (white patches)", "score": {"pitta": 1, "vata": 1}, "finding": "Bhrajaka Pitta disturbed"},
            {"text": "No skin conditions", "score": {}, "finding": "Healthy skin"},
        ],
    },
    {
        "id": "TP_S3",
        "question": "Any other skin signs you've noticed?",
        "options": [
            {"text": "Stretch marks", "score": {"vata": 1}, "finding": "Vata in Mamsa/Meda dhatu"},
            {"text": "Spider veins or broken capillaries", "score": {"pitta": 1, "vata": 1}, "finding": "Pitta in Rakta, Vyana Vata"},
            {"text": "Swelling or water retention in skin", "score": {"kapha": 2}, "finding": "Kapha, Meda/Kleda excess"},
            {"text": "New moles or skin growths", "score": {"kapha": 1}, "finding": "Kapha accumulation"},
            {"text": "None of these", "score": {}, "finding": "Normal"},
        ],
    },
]

BODY_TEXT_QUESTIONS = [
    {
        "id": "TP_B1",
        "question": "What is your body frame like?",
        "options": [
            {"text": "Thin, light, narrow shoulders, prominent joints", "score": {"vata": 2}, "finding": "Vata Prakriti frame"},
            {"text": "Medium, athletic, well-proportioned", "score": {"pitta": 2}, "finding": "Pitta Prakriti frame"},
            {"text": "Heavy, broad, large bones, stocky", "score": {"kapha": 2}, "finding": "Kapha Prakriti frame"},
        ],
    },
    {
        "id": "TP_B2",
        "question": "How is your weight pattern?",
        "options": [
            {"text": "Underweight, hard to gain weight", "score": {"vata": 2}, "finding": "Vata, low Meda dhatu"},
            {"text": "Moderate, maintain weight easily", "score": {"pitta": 1}, "finding": "Pitta, good metabolism"},
            {"text": "Overweight, gain easily especially in abdomen", "score": {"kapha": 2}, "finding": "Kapha, Meda dhatu excess"},
            {"text": "Weight fluctuates a lot", "score": {"vata": 2}, "finding": "Vata instability"},
        ],
    },
    {
        "id": "TP_B3",
        "question": "How are your joints?",
        "options": [
            {"text": "Prominent, knobby, cracking sounds", "score": {"vata": 2}, "finding": "Vata in Asthi/Shleshaka Kapha depleted"},
            {"text": "Normal, no issues", "score": {}, "finding": "Balanced"},
            {"text": "Inflamed, hot, swollen", "score": {"pitta": 2}, "finding": "Pitta in joints (Amavata with Pitta)"},
            {"text": "Stiff, heavy, swollen without heat", "score": {"kapha": 2}, "finding": "Kapha in joints"},
        ],
    },
]

# =============================================================================
# Registry mapping pariksha type → text questions
# =============================================================================
TEXT_PARIKSHA = {
    "tongue": {
        "name": "Jihva Pariksha (Tongue) — Text",
        "questions": TONGUE_TEXT_QUESTIONS,
    },
    "eyes": {
        "name": "Netra Pariksha (Eyes) — Text",
        "questions": EYES_TEXT_QUESTIONS,
    },
    "nails": {
        "name": "Nakha Pariksha (Nails) — Text",
        "questions": NAILS_TEXT_QUESTIONS,
    },
    "face": {
        "name": "Mukha Pariksha (Face) — Text",
        "questions": FACE_TEXT_QUESTIONS,
    },
    "skin": {
        "name": "Tvacha Pariksha (Skin) — Text",
        "questions": SKIN_TEXT_QUESTIONS,
    },
    "body": {
        "name": "Shareera Pariksha (Body) — Text",
        "questions": BODY_TEXT_QUESTIONS,
    },
}


def process_text_pariksha(pariksha_type: str, responses: list[dict]) -> dict:
    """Process text-based Pariksha responses and return dosha scores + findings."""
    if pariksha_type not in TEXT_PARIKSHA:
        return {"error": f"Unknown type: {pariksha_type}. Valid: {list(TEXT_PARIKSHA.keys())}"}

    scores = {"vata": 0.0, "pitta": 0.0, "kapha": 0.0}
    findings = []

    for resp in responses:
        if "score" in resp:
            for dosha, val in resp["score"].items():
                scores[dosha] = scores.get(dosha, 0) + val
        if "finding" in resp:
            findings.append(resp["finding"])

    return {
        "pariksha_type": pariksha_type,
        "pariksha_name": TEXT_PARIKSHA[pariksha_type]["name"],
        "dosha_scores": scores,
        "findings": findings,
        "input_mode": "text",
    }
