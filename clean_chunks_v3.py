"""Third pass: Add Sanskrit/Devanagari/Tamil keyword tags to ALL records."""

import json
import re
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

PROJECT_ROOT = Path(__file__).parent

# =============================================================================
# SANSKRIT / DEVANAGARI keyword patterns
# =============================================================================
SANSKRIT_KEYWORDS = {
    # Dosha terms in Sanskrit
    "dosha": re.compile(r'(वात|पित्त|कफ|त्रिदोष|दोष|प्रकृति|विकृति|vāta|pitta|kapha)', re.I),
    # Dhatu terms
    "dhatu": re.compile(r'(रस|रक्त|मांस|मेद|अस्थि|मज्जा|शुक्र|ओजस|dhātu|rasa|rakta|māṃsa|meda|asthi|majjā|śukra|ojas)', re.I),
    # Agni terms
    "agni": re.compile(r'(अग्नि|जठराग्नि|पाचक|agni|jāṭharāgni)', re.I),
    # Treatment terms in Sanskrit
    "chikitsa": re.compile(r'(चिकित्सा|चिकित्स|औषध|भेषज|उपचार|cikitsā|auṣadha|bheṣaja)', re.I),
    # Panchakarma Sanskrit
    "panchakarma": re.compile(r'(पञ्चकर्म|वमन|विरेचन|बस्ति|नस्य|रक्तमोक्षण|स्नेहन|स्वेदन|vamana|virecana|basti|nasya|raktamokṣaṇa|snehana|svedana)', re.I),
    # Body parts Sanskrit
    "sharira": re.compile(r'(शरीर|शिर|उदर|हृदय|यकृत|प्लीहा|वृक्क|आमाशय|śarīra|śiras|udara|hṛdaya|yakṛt|plīhā)', re.I),
    # Disease terms Sanskrit
    "roga": re.compile(r'(रोग|ज्वर|कास|श्वास|प्रमेह|कुष्ठ|पाण्डु|अर्श|शोथ|व्रण|अतिसार|roga|jvara|kāsa|śvāsa|prameha|kuṣṭha|pāṇḍu|arśa|śotha|vraṇa|atisāra)', re.I),
    # Herb terms Sanskrit
    "dravya": re.compile(r'(द्रव्य|औषधि|अश्वगन्धा|ब्राह्मी|त्रिफला|गुग्गुलु|निम्ब|तुलसी|शतावरी|हरीतकी|आमलकी|गुडूची|dravya|auṣadhi|aśvagandhā|brāhmī|triphalā|guggulu|nimba|tulasī|śatāvarī|harītakī|āmalakī|guḍūcī)', re.I),
    # Formulation types Sanskrit
    "kalpana": re.compile(r'(चूर्ण|क्वाथ|अरिष्ट|आसव|अवलेह|घृत|तैल|वटी|गुटिका|भस्म|पिष्टी|cūrṇa|kvātha|ariṣṭa|āsava|avaleha|ghṛta|taila|vaṭī|guṭikā|bhasma|piṣṭī)', re.I),
    # Rasa/taste Sanskrit
    "rasa_sanskrit": re.compile(r'(मधुर|अम्ल|लवण|कटु|तिक्त|कषाय|वीर्य|विपाक|madhura|amla|lavaṇa|kaṭu|tikta|kaṣāya|vīrya|vipāka)', re.I),
    # Srotas
    "srotas": re.compile(r'(स्रोतस|प्राणवह|अन्नवह|रसवह|रक्तवह|मांसवह|मेदोवह|अस्थिवह|मज्जावह|शुक्रवह|मूत्रवह|पुरीषवह|स्वेदवह|srotas|prāṇavaha|annavaha|rasavaha)', re.I),
    # Chapters/sections
    "adhyaya": re.compile(r'(अध्याय|स्थान|सूत्र|निदान|चिकित्सा|कल्प|शारीर|उत्तर|adhyāya|sthāna|sūtra|nidāna|cikitsā|kalpa|śārīra|uttara)', re.I),
    # Yoga Sanskrit
    "yoga_sanskrit": re.compile(r'(आसन|प्राणायाम|कुम्भक|मुद्रा|बन्ध|ध्यान|योग|āsana|prāṇāyāma|kumbhaka|mudrā|bandha|dhyāna|yoga)', re.I),
    # Diet Sanskrit
    "ahara": re.compile(r'(आहार|पथ्य|अपथ्य|अन्न|भोजन|दुग्ध|घृत|मधु|āhāra|pathya|apathya|anna|bhojana|dugdha|ghṛta|madhu)', re.I),
    # Lifestyle Sanskrit
    "vihara": re.compile(r'(विहार|दिनचर्या|ऋतुचर्या|निद्रा|व्यायाम|स्नान|अभ्यंग|vihāra|dinacaryā|ṛtucaryā|nidrā|vyāyāma|snāna|abhyaṅga)', re.I),
}

# Tamil Siddha keywords
TAMIL_KEYWORDS = {
    "siddha_medicine": re.compile(r'(சித்த|மருந்து|நோய்|குணம்|வாதம்|பித்தம்|கபம்|சூரணம்)', re.I),
    "siddha_herbs": re.compile(r'(மூலிகை|பூண்டு|மஞ்சள்|இஞ்சி|கற்பம்|நெல்லி|துளசி)', re.I),
    "siddha_yoga": re.compile(r'(யோகம்|ஆசனம்|பிராணாயாமம்|தியானம்|குண்டலினி)', re.I),
}

# Transliteration patterns (IAST/Harvard-Kyoto found in academic texts)
TRANSLITERATION_KEYWORDS = {
    "iast_dosha": re.compile(r'(vāta|pitta|kapha|tridoṣa|doṣa|prakṛti|vikṛti)', re.I),
    "iast_dhatu": re.compile(r'(dhātu|māṃsa|majjā|śukra|tejas)', re.I),
    "iast_disease": re.compile(r'(jvara|kāsa|śvāsa|prameha|kuṣṭha|pāṇḍu|śotha|vraṇa|atisāra|unmāda|apasmāra)', re.I),
    "iast_treatment": re.compile(r'(cikitsā|auṣadha|bheṣaja|śodhana|śamana|rasāyana|pañcakarma)', re.I),
    "iast_herb": re.compile(r'(aśvagandhā|brāhmī|triphalā|guḍūcī|harītakī|āmalakī|bibhītakī|pippalī|śatāvarī|guggulu)', re.I),
    "iast_anatomy": re.compile(r'(śarīra|srotas|marma|nāḍī|koṣṭha|āśaya|dhātu)', re.I),
    "iast_yoga": re.compile(r'(āsana|prāṇāyāma|kumbhaka|mudrā|bandha|dhāraṇā|dhyāna|samādhi)', re.I),
}

# Source file to topic mapping
SOURCE_TOPIC_MAP = {
    "caraka": ["charaka_samhita", "internal_medicine", "classical_text"],
    "sushrut": ["sushruta_samhita", "surgery", "classical_text"],
    "astanga": ["ashtanga_hridaya", "eight_branches", "classical_text"],
    "ashtang": ["ashtanga_hridaya", "eight_branches", "classical_text"],
    "food-guidelines": ["diet", "food", "nutrition", "ahara"],
    "insert_asanas": ["yoga", "asana", "posture", "technique"],
    "asana_recommendation": ["yoga", "therapy", "kriya", "protocol"],
    "panchakarma": ["panchakarma", "detox", "purification"],
    "afi": ["formulary", "formulation", "drug", "ayush"],
    "siddha": ["siddha", "tamil_medicine"],
    "bogar": ["siddha", "alchemy", "tamil_medicine"],
    "tirumantiram": ["siddha", "spiritual", "tamil"],
    "thirumanthiram": ["siddha", "spiritual", "tamil"],
    "tibetan": ["tibetan_medicine", "buddhist_medicine"],
    "alchemy": ["rasa_shastra", "metallic_medicine", "alchemy"],
    "dhatuparinama": ["metabolism", "dhatu", "tissue"],
    "nadi_pariksha": ["pulse_diagnosis", "nadi", "pariksha"],
    "svastha": ["preventive_health", "daily_routine", "dinacharya"],
    "ethics": ["medical_ethics", "vaidya_dharma"],
    "vriksha": ["plant_medicine", "botanical", "vriksha_ayurveda"],
    "kashyapa": ["pediatrics", "kashyapa_samhita"],
    "vikriti": ["vikriti", "imbalance", "diagnosis"],
    "prakriti": ["prakriti", "constitution", "body_type"],
    "herb_reference": ["herb", "treatment", "condition_mapping"],
    "asana_protocol": ["yoga", "asana", "therapeutic_sequence"],
    "asana_detail": ["yoga", "asana", "technique", "benefits"],
}


def get_source_tags(source_file: str) -> list:
    """Get topic tags based on source file name."""
    src_lower = str(source_file).lower()
    tags = []
    for keyword, topic_tags in SOURCE_TOPIC_MAP.items():
        if keyword in src_lower:
            tags.extend(topic_tags)
    return list(set(tags))


def extract_all_keywords(text: str, source_file: str = "") -> tuple:
    """Extract keywords from Sanskrit, Tamil, IAST, and English text."""
    keywords = {}

    # Sanskrit/Devanagari
    for cat, pattern in SANSKRIT_KEYWORDS.items():
        matches = set(m if isinstance(m, str) else m for m in pattern.findall(text))
        if matches:
            keywords[cat] = sorted(set(m.lower() if m.isascii() else m for m in matches))[:10]

    # Tamil
    for cat, pattern in TAMIL_KEYWORDS.items():
        matches = set(pattern.findall(text))
        if matches:
            keywords[cat] = sorted(matches)[:10]

    # IAST transliteration
    for cat, pattern in TRANSLITERATION_KEYWORDS.items():
        matches = set(m.lower() for m in pattern.findall(text))
        if matches:
            keywords[cat] = sorted(matches)[:10]

    # Source-based tags
    src_tags = get_source_tags(source_file)
    if src_tags:
        keywords["source_topic"] = src_tags

    # Flatten all tags
    all_tags = []
    for tag_list in keywords.values():
        all_tags.extend(tag_list)

    return keywords, sorted(set(all_tags))


def process_file(filepath: Path) -> dict:
    records = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    stats = {'total': len(records), 'tags_improved': 0, 'new_tags_added': 0}

    for rec in records:
        text = rec.get('text', '')
        src = rec.get('source_file', rec.get('metadata', {}).get('file_name', ''))

        # Extract new keywords
        new_kw, new_tags = extract_all_keywords(text, src)

        # Merge with existing
        existing_kw = rec.get('keywords', {})
        existing_tags = set(rec.get('keyword_tags', []))

        had_tags = bool(existing_tags)

        for cat, tags in new_kw.items():
            if cat not in existing_kw:
                existing_kw[cat] = tags
            else:
                existing_kw[cat] = sorted(set(existing_kw[cat] + tags))[:15]

        all_tags = set(new_tags)
        all_tags.update(existing_tags)

        rec['keywords'] = existing_kw
        rec['keyword_tags'] = sorted(all_tags)

        if not had_tags and all_tags:
            stats['new_tags_added'] += 1
        elif had_tags and len(all_tags) > len(existing_tags):
            stats['tags_improved'] += 1

    # Write back
    with open(filepath, 'w', encoding='utf-8') as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')

    return stats


def main():
    logging.info("THIRD PASS: Sanskrit/Tamil/IAST keyword tagging")
    logging.info("=" * 50)

    total = {'total': 0, 'tags_improved': 0, 'new_tags_added': 0}

    for fname in ['chunks.jsonl', 'ngpt_chunks.jsonl', 'ocr_chunks.jsonl']:
        filepath = PROJECT_ROOT / 'data' / 'processed' / fname
        if not filepath.exists():
            continue
        logging.info(f"\nProcessing {fname}...")
        stats = process_file(filepath)
        for k, v in stats.items():
            total[k] += v
        logging.info(f"  {stats}")

    logging.info(f"\nTOTAL: {total}")

    # Final count
    with_tags = 0
    without_tags = 0
    total_recs = 0
    for fname in ['chunks.jsonl', 'ngpt_chunks.jsonl', 'ocr_chunks.jsonl']:
        filepath = PROJECT_ROOT / 'data' / 'processed' / fname
        if not filepath.exists():
            continue
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                rec = json.loads(line)
                total_recs += 1
                if rec.get('keyword_tags'):
                    with_tags += 1
                else:
                    without_tags += 1

    logging.info(f"\nFinal: {total_recs} records | With tags: {with_tags} ({with_tags*100//total_recs}%) | No tags: {without_tags}")


if __name__ == '__main__':
    main()
