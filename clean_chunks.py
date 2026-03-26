"""Clean and improve all chunks:
1. Remove base64/image strings
2. Remove image URLs (pinimg, etc.)
3. Remove too-short records (<50 chars of useful text)
4. Remove BOM characters
5. Add keyword tags for better retrieval
6. Normalize text (strip noise, fix whitespace)
7. Rebuild all JSONL files in data/processed/ and data1/
"""

import json
import re
import logging
import sys
from pathlib import Path
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

PROJECT_ROOT = Path(__file__).parent

# =====================================================================
# CLEANING RULES
# =====================================================================

# Patterns to strip from text
STRIP_PATTERNS = [
    # base64 image data
    re.compile(r"image_base64:\s*[^\n]+", re.IGNORECASE),
    re.compile(r"data:image/[^;]+;base64,[A-Za-z0-9+/=\s]+", re.IGNORECASE),
    # Pinterest and other image URLs
    re.compile(r"https?://[^\s]*\.(?:jpg|jpeg|png|gif|webp|bmp|svg)[^\s]*", re.IGNORECASE),
    re.compile(r"https?://i\.pinimg\.com/[^\s]+", re.IGNORECASE),
    re.compile(r"image_url:\s*https?://[^\s]+", re.IGNORECASE),
    # BOM
    re.compile(r"\ufeff"),
    # Excessive whitespace
    re.compile(r"\n{3,}"),
    re.compile(r"[ \t]{3,}"),
    # Page metadata noise (standalone page numbers with nothing else)
    re.compile(r"^\s*page_number:\s*\d+\s*$", re.MULTILINE),
]

# Ayurveda keyword extraction patterns
KEYWORD_PATTERNS = {
    # Doshas
    "dosha": re.compile(r"\b(vata|pitta|kapha|tridosh[ai]|vata-pitta|pitta-kapha|vata-kapha)\b", re.I),
    # Sub-doshas
    "sub_dosha": re.compile(r"\b(prana|udana|vyana|samana|apana|pachaka|ranjaka|sadhaka|alochaka|bhrajaka|tarpaka|avalambaka|kledaka|bodhaka|shleshaka)\b", re.I),
    # Dhatus
    "dhatu": re.compile(r"\b(rasa|rakta|mamsa|meda|asthi|majja|shukra|ojas|tejas)\b", re.I),
    # Agni types
    "agni": re.compile(r"\b(agni|jatharagni|dhatvagni|bhutagni|mandagni|tikshna|vishama|sama)\b", re.I),
    # Treatments
    "treatment": re.compile(r"\b(chikitsa|treatment|therapy|cure|remedy|aushadh|prescription)\b", re.I),
    # Panchakarma
    "panchakarma": re.compile(r"\b(panchakarma|vamana|virechana|basti|nasya|raktamokshan|shodhana|shamana|snehana|swedana|abhyanga)\b", re.I),
    # Herbs (common names)
    "herbs": re.compile(r"\b(ashwagandh|brahmi|triphala|guggul|neem|tulsi|shatavar|haritaki|amalaki|bibhitaki|pippali|guduchi|turmeric|ginger|shunthi|maricha|pepper|yashtimadhu|licorice|arjuna|kutki|shankhapushpi|jatamansi|vacha|vidanga|chitraka|punarnava|gokshura|bhringraj|manjishtha|khadira|sariva|dashamoola|trikatu)\b", re.I),
    # Formulation types
    "formulation": re.compile(r"\b(churna|kwath|kashaya|arishta|asava|avaleha|lehya|ghrita|taila|vati|gutika|bhasma|pishti|mandura|lauh|guggulu|rasayana|rasa)\b", re.I),
    # Diseases
    "disease": re.compile(r"\b(jwara|fever|kasa|cough|shwasa|asthma|prameha|diabetes|kushtha|skin|pandu|anemia|arsha|piles|shotha|edema|vrana|wound|atisara|diarrhea|vibandha|constipation|amlapitta|acidity|shirahshoola|headache|hridroga|heart|sthaulya|obes|sandhivata|arthritis|unmada|apasmara|epilepsy|anidra|insomnia|khalitya|baldness|timira|eye)\b", re.I),
    # Yoga/Asana
    "yoga": re.compile(r"\b(asana|pranayama|kumbhaka|mudra|bandha|yoga|dhyana|meditation|surya namaskar|kapalabhati|bhastrika|nadi shodhan)\b", re.I),
    # Tastes
    "rasa_taste": re.compile(r"\b(madhura|sweet|amla|sour|lavana|salty|katu|pungent|tikta|bitter|kashaya|astringent)\b", re.I),
    # Diagnosis
    "diagnosis": re.compile(r"\b(pariksha|nidan|diagnosis|examination|pulse|nadi|tongue|jihva|eye|netra|nail|nakha|mala|mutra|ashtavidha|dashavidha)\b", re.I),
    # Body/Anatomy
    "anatomy": re.compile(r"\b(srotas|marma|nadi|dhatu|organ|tissue|bone|muscle|blood|liver|kidney|heart|brain|stomach|intestine|lung|spleen|uterus|joint)\b", re.I),
    # Lifestyle
    "lifestyle": re.compile(r"\b(dinacharya|ritucharya|routine|daily|seasonal|sleep|exercise|bath|diet|ahara|food|fasting)\b", re.I),
}


def clean_text(text: str) -> str:
    """Apply all cleaning rules to text."""
    for pattern in STRIP_PATTERNS:
        text = pattern.sub(" ", text)

    # Clean up results
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)  # Max 2 newlines
    text = re.sub(r"[ \t]+", " ", text)  # Collapse spaces
    text = text.strip()
    return text


def extract_keywords(text: str) -> dict:
    """Extract Ayurveda-specific keywords from text for tagging."""
    keywords = {}
    for category, pattern in KEYWORD_PATTERNS.items():
        matches = set(m.lower() for m in pattern.findall(text))
        if matches:
            keywords[category] = sorted(matches)
    return keywords


def is_useful(text: str, min_length: int = 50) -> bool:
    """Check if text has enough meaningful content."""
    clean = text.strip()
    if len(clean) < min_length:
        return False
    # Check it's not just metadata
    if re.match(r"^\s*page_number:\s*\d+\s*$", clean):
        return False
    if re.match(r"^\s*\d+\s*$", clean):
        return False
    # Has at least some alphabetic words
    words = re.findall(r"[a-zA-Z]{3,}", clean)
    return len(words) >= 3


def process_file(input_path: Path, output_path: Path) -> dict:
    """Clean a single JSONL file and write improved version."""
    stats = {"total": 0, "kept": 0, "removed_base64": 0, "removed_short": 0, "removed_noise": 0}

    records = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    stats["total"] = len(records)

    cleaned = []
    for rec in records:
        text = rec.get("text", "")
        original_len = len(text)

        # Clean
        text = clean_text(text)

        # Check if base64/image was removed
        if original_len - len(text) > 100:
            if "base64" in rec.get("text", "").lower() or "data:image" in rec.get("text", "").lower():
                stats["removed_base64"] += 1
                if not is_useful(text):
                    continue

        # Check usefulness
        if not is_useful(text):
            if len(text.strip()) < 50:
                stats["removed_short"] += 1
            else:
                stats["removed_noise"] += 1
            continue

        # Update text
        rec["text"] = text

        # Extract and add keywords
        keywords = extract_keywords(text)
        if keywords:
            rec["keywords"] = keywords
            # Create flat tag list for easy filtering
            all_tags = []
            for cat_tags in keywords.values():
                all_tags.extend(cat_tags)
            rec["keyword_tags"] = sorted(set(all_tags))

        cleaned.append(rec)

    stats["kept"] = len(cleaned)

    # Write
    with open(output_path, "w", encoding="utf-8") as f:
        for rec in cleaned:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    return stats


def main():
    logging.info("=" * 60)
    logging.info("CLEANING & IMPROVING ALL CHUNKS")
    logging.info("=" * 60)

    processed_dir = PROJECT_ROOT / "data" / "processed"
    data1_dir = PROJECT_ROOT / "data1"

    total_stats = defaultdict(int)

    # Clean processed JSONL files
    for fname in ["chunks.jsonl", "ngpt_chunks.jsonl", "ocr_chunks.jsonl"]:
        input_path = processed_dir / fname
        if not input_path.exists():
            continue

        # Backup original
        backup = processed_dir / f"{fname}.backup"
        if not backup.exists():
            import shutil
            shutil.copy2(input_path, backup)
            logging.info(f"Backed up {fname} -> {fname}.backup")

        logging.info(f"\nCleaning {fname}...")
        stats = process_file(input_path, input_path)
        for k, v in stats.items():
            total_stats[k] += v
        logging.info(f"  Total: {stats['total']} -> Kept: {stats['kept']}")
        logging.info(f"  Removed: base64={stats['removed_base64']}, short={stats['removed_short']}, noise={stats['removed_noise']}")

    # Now regenerate data1/ from cleaned chunks
    logging.info("\n" + "=" * 60)
    logging.info("REGENERATING data1/ FROM CLEANED CHUNKS")
    logging.info("=" * 60)

    # Import and run the extraction
    import importlib.util
    spec = importlib.util.spec_from_file_location("extract", str(PROJECT_ROOT / "extract_structured_data.py"))
    extract_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(extract_mod)
    extract_mod.main()

    logging.info("\n" + "=" * 60)
    logging.info("CLEANUP COMPLETE")
    logging.info("=" * 60)
    logging.info(f"Total records processed: {total_stats['total']}")
    logging.info(f"Total kept: {total_stats['kept']}")
    logging.info(f"Removed base64: {total_stats['removed_base64']}")
    logging.info(f"Removed short: {total_stats['removed_short']}")
    logging.info(f"Removed noise: {total_stats['removed_noise']}")
    logging.info(f"Net reduction: {total_stats['total'] - total_stats['kept']} records ({(total_stats['total'] - total_stats['kept']) / max(total_stats['total'], 1) * 100:.1f}%)")


if __name__ == "__main__":
    main()
