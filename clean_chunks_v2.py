"""Second-pass cleaning: remove error pages, URLs, pure non-English, and improve keyword extraction."""

import json
import re
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

PROJECT_ROOT = Path(__file__).parent

# Additional URL patterns
URL_PATTERN = re.compile(r'https?://[^\s]+', re.IGNORECASE)

# Error page patterns
ERROR_PATTERNS = [
    re.compile(r'\[?ERROR[^\]]*\]?', re.IGNORECASE),
    re.compile(r'NVIDIA client error', re.IGNORECASE),
    re.compile(r'page \d+ - .* error', re.IGNORECASE),
    re.compile(r'Error processing', re.IGNORECASE),
]

# Extended keyword patterns for better coverage
EXTENDED_KEYWORDS = {
    "anatomy": re.compile(r'\b(body|head|chest|abdomen|pelvis|limb|arm|leg|foot|hand|spine|back|neck|shoulder|hip|knee|elbow|wrist|ankle|skull|rib|vein|artery|nerve|tendon|ligament|cartilage|skin|hair|nail|tooth|tongue|eye|ear|nose|throat|mouth|lip|gland|organ|viscera)\b', re.I),
    "treatment": re.compile(r'\b(treat|cure|heal|medicine|drug|prescri|therap|remedy|formula|decoction|infusion|paste|powder|oil|ghee|milk|water|juice|dose|dosage|administer|apply|anoint|massage|foment|purge|emetic|enema|blood.?let|cauteriz|surgery|incision|excision|bandage|sutur|stitch)\b', re.I),
    "disease": re.compile(r'\b(disease|disorder|illness|ailment|malady|afflict|symptom|pain|ache|swell|inflam|infect|ulcer|abscess|tumor|growth|wound|fracture|disloca|sprain|burn|bite|sting|poison|venom|paralys|palsy|convuls|spasm|tremor|faint|deliri|hallucin|bleed|hemorrh|diarrh|vomit|nausea|itch|rash|boil|blister)\b', re.I),
    "herb_extended": re.compile(r'\b(root|bark|leaf|leaves|flower|fruit|seed|stem|wood|resin|gum|sap|juice|extract|oil|decoct|infus|paste|powder|dried|fresh|plant|herb|tree|shrub|creeper|climber|bulb|tuber|rhizome)\b', re.I),
    "food_extended": re.compile(r'\b(eat|drink|cook|boil|fry|roast|bake|digest|hunger|thirst|appetite|meal|breakfast|lunch|dinner|rice|wheat|barley|millet|lentil|bean|pulse|grain|cereal|meat|fish|egg|butter|cream|cheese|curd|yogurt|sugar|salt|spice|pepper|cinnamon|cardamom|clove|cumin|coriander|fennel|garlic|onion|ginger|nutmeg|saffron|coconut|almond|walnut|sesame|mustard|olive|fruit|mango|banana|apple|grape|pomegranate|fig|date|raisin|lemon|orange|melon|cucumber|gourd|pumpkin|potato|carrot|radish|beet|spinach|cabbage)\b', re.I),
    "philosophy": re.compile(r'\b(soul|spirit|conscious|karma|dharma|moksha|liberation|rebirth|meditation|prayer|mantra|ritual|sacrifice|offering|temple|deity|god|divine|sacred|holy|spiritual|moral|ethic|virtue|sin|purity|impurity|auspicious)\b', re.I),
}


def has_enough_english(text: str, min_words: int = 5) -> bool:
    """Check if text has enough English words to be useful for English retrieval."""
    words = re.findall(r'[a-zA-Z]{3,}', text)
    return len(words) >= min_words


def is_error_page(text: str) -> bool:
    """Check if this is an error/corrupt page."""
    for pat in ERROR_PATTERNS:
        if pat.search(text[:200]):
            return True
    return False


def strip_urls(text: str) -> str:
    """Remove all URLs from text."""
    return URL_PATTERN.sub('', text)


def extract_extended_keywords(text: str) -> dict:
    """Extract keywords using extended patterns."""
    keywords = {}
    for category, pattern in EXTENDED_KEYWORDS.items():
        matches = set(m.lower() for m in pattern.findall(text))
        if matches:
            # Limit to top 10 per category
            keywords[category] = sorted(matches)[:10]
    return keywords


def process_file(filepath: Path) -> dict:
    """Second pass cleaning on a JSONL file."""
    records = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    stats = {'total': len(records), 'removed_error': 0, 'removed_noeng': 0, 'urls_stripped': 0, 'keywords_added': 0, 'kept': 0}
    cleaned = []

    for rec in records:
        text = rec.get('text', '')

        # Remove error pages
        if is_error_page(text):
            stats['removed_error'] += 1
            continue

        # Strip remaining URLs
        if 'http' in text:
            text = strip_urls(text).strip()
            rec['text'] = text
            stats['urls_stripped'] += 1

        # Remove pure non-English (less than 5 English words)
        if not has_enough_english(text, min_words=5):
            # Keep if it has Sanskrit terms we recognize
            if not has_enough_english(text, min_words=2):
                stats['removed_noeng'] += 1
                continue

        # Skip if too short after cleaning
        if len(text.strip()) < 50:
            stats['removed_noeng'] += 1
            continue

        # Improve keywords if empty
        existing_kw = rec.get('keywords', {})
        if not existing_kw:
            extended = extract_extended_keywords(text)
            if extended:
                rec['keywords'] = extended
                all_tags = []
                for tags in extended.values():
                    all_tags.extend(tags)
                rec['keyword_tags'] = sorted(set(all_tags))
                stats['keywords_added'] += 1
        else:
            # Merge extended keywords with existing
            extended = extract_extended_keywords(text)
            for cat, tags in extended.items():
                if cat not in existing_kw:
                    existing_kw[cat] = tags
            rec['keywords'] = existing_kw
            all_tags = []
            for tags in existing_kw.values():
                all_tags.extend(tags)
            rec['keyword_tags'] = sorted(set(all_tags))

        cleaned.append(rec)
        stats['kept'] += 1

    # Write back
    with open(filepath, 'w', encoding='utf-8') as f:
        for rec in cleaned:
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')

    return stats


def main():
    logging.info("SECOND PASS CLEANING")
    logging.info("=" * 50)

    total = {'total': 0, 'removed_error': 0, 'removed_noeng': 0, 'urls_stripped': 0, 'keywords_added': 0, 'kept': 0}

    for fname in ['chunks.jsonl', 'ngpt_chunks.jsonl', 'ocr_chunks.jsonl']:
        filepath = PROJECT_ROOT / 'data' / 'processed' / fname
        if not filepath.exists():
            continue
        logging.info(f"\nCleaning {fname}...")
        stats = process_file(filepath)
        for k, v in stats.items():
            total[k] += v
        logging.info(f"  {stats}")

    logging.info(f"\nTOTAL: {total}")
    logging.info(f"Removed: {total['total'] - total['kept']} records")
    logging.info(f"URLs stripped: {total['urls_stripped']}")
    logging.info(f"Keywords added to previously empty: {total['keywords_added']}")

    # Verify
    logging.info("\nVerifying...")
    remaining_issues = {'no_keywords': 0, 'errors': 0, 'urls': 0, 'total': 0}
    for fname in ['chunks.jsonl', 'ngpt_chunks.jsonl', 'ocr_chunks.jsonl']:
        filepath = PROJECT_ROOT / 'data' / 'processed' / fname
        if not filepath.exists():
            continue
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                rec = json.loads(line)
                remaining_issues['total'] += 1
                if not rec.get('keyword_tags'):
                    remaining_issues['no_keywords'] += 1
                if is_error_page(rec.get('text', '')):
                    remaining_issues['errors'] += 1
                if 'http' in rec.get('text', ''):
                    remaining_issues['urls'] += 1

    logging.info(f"Remaining: {remaining_issues}")


if __name__ == '__main__':
    main()
