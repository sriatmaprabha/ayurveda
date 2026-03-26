# Ayurveda RAG System

A multi-LLM Retrieval-Augmented Generation system for Ayurveda knowledge. Ask questions about Ayurveda and get personalized, dosha-aware answers grounded in 134 classical texts -- Charaka Samhita, Sushruta Samhita, Ashtanga Hridaya, Siddha texts, and more.

**55,560 knowledge chunks | 134 source files | 48,667 structured records | 96 tests**

## Features

- **Prakriti-Aware Chat** -- Gradually asks body constitution questions and personalizes all answers to your dosha type
- **Consistent Asana Protocols** -- 112 fixed therapeutic yoga sequences with full step-by-step instructions
- **Herb-to-Condition Mapping** -- 27 conditions mapped to specific herbs, formulations, and dosages from classical texts
- **Visual Diagnosis (Pariksha)** -- 7 body-part examinations via Llama 4 image analysis or text questions
- **Multi-Level Diagnostic Flow** -- 5-layer question tree narrowing from general dosha to personalized treatment
- **Streaming Responses** -- Token-by-token output for fast perceived response time
- **ChatGPT-Style Web UI** -- Dark/light theme, Ayurveda color scheme, mobile responsive
- **Casual Message Detection** -- "Hi" gets an instant greeting, not a wall of Ayurveda text

## Architecture

```
User (text/image)
       |
       v
 Casual? ----yes----> Instant response (no LLM needed)
       |
       no
       |
       v
 Parse prakriti answer (if pending question)
       |
       v
 Fixed Protocol Mapper -----> Deterministic asana protocols (JSON lookup)
       |
       v
 Vector Store (55K chunks) --> Retrieve relevant book context
       |
       v
 LLM (streaming) -----------> Generate answer + append prakriti question
       |
       v
 Response (answer + asana steps + follow-up question)
```

### LLM Roles

| Model | Role |
|-------|------|
| Meta Llama 4 | Image input processing (book scans, herb photos, Pariksha) |
| Llama 3 / GPT-OSS | Answer generation with source citations |
| Mistral / Kimi K2 | Pipeline monitoring and quality evaluation |

## Knowledge Base (134 sources, 55,560 chunks)

### Classical Texts
- **Charaka Samhita** -- 3 volumes + individual sthanas (Prathama through Shashtham)
- **Sushruta Samhita** -- 3 English volumes + all 6 sections (Sutra, Nidana, Sharira, Chikitsa, Kalpa, Uttara)
- **Ashtanga Hridaya** -- Sutrasthana handbook + full English translation
- **Kashyapa Samhita** -- Vimana section

### Specialized Texts
- **Ayurvedic Formulary of India (AFI)** -- Single drug formulary + Part II formulations + appendices
- **Panchakarma Guide** (MAM)
- **Alchemy & Metallic Medicines** -- Vaidya Bhagavan Dash
- **Dhatuparinama** -- Ayurvedic concepts of metabolism
- **Nadi Pariksha** -- Pulse diagnosis (OCR'd)
- **Svastha Vritta** -- Preventive health textbook (OCR'd)
- **Medical Ethics in Classical Ayurveda** -- Dagmar Wujastyk

### Siddha & Related Systems
- **Bogar 7000 Sapthakaandam**, Thirumanthiram, Tirumantiram
- **Siddha Pharmacopoeia of India**
- **Tibetan Medicine Principles** -- Tamdin Sither Bradley
- Tamil Siddha texts (Konkanavar, Kuthambaisiththar, Sivavaakkiyam, etc.)

### Yoga & Asana Data
- **195 yoga asanas** with full techniques, benefits, difficulty (from insert_asanas.sql)
- **112 therapeutic protocols** for 50+ conditions (from asana_recommendations.csv)
- **Food Guidelines** -- Ayurvedic dietary recommendations

### Historical & Academic
- History of Aryan Medical Science (1896), Antiquity of Hindu Medicine (1837)
- Interpretation of Ancient Hindu Medicine (1923 & 2008 editions)
- Ayurveda as Eastern Philosophy of Medicine

## Project Structure

```
Ayurveda/
├── knowledge_base/           # 134 source documents (PDF, CSV, MD, TXT, SQL)
│   └── NGPT/                 # 43 additional books + 42 OCR'd text outputs
├── src/
│   ├── ingestion/            # Parsers for PDF, CSV, MD, SQL, TXT + chunking
│   ├── embeddings/           # ChromaDB vector store (55,560 chunks)
│   ├── retrieval/            # Query engine + Protocol mapper + Asana recommender
│   ├── generation/           # LLM client + Answer generator + Prakriti profiler
│   │                         #   + Conversational diagnostic + Casual detection
│   ├── vision/               # Image processor + 7 Pariksha prompts
│   │                         #   + Text Pariksha + Diagnostic engine
│   └── api/                  # FastAPI + Chat routes + Diagnostic routes
├── static/                   # ChatGPT-style web frontend (single HTML)
├── config/                   # Settings + LLM profiles
├── data/                     # Processed chunks, protocols, herb references
│   ├── processed/            # JSONL chunks (chunks.jsonl, ngpt, ocr)
│   ├── asana_protocols.json  # 112 fixed therapeutic protocols
│   ├── asana_full_details.json # 153 asanas with techniques
│   ├── herb_references.json  # 278 herb-condition references from books
│   └── *.xlsx                # Diagnosis tree + Vikriti guide (6 sheets each)
├── data1/                    # Structured JSONL by category (13 files, 313MB)
│   ├── disease_treatment.jsonl     # 6,505 records
│   ├── herb_knowledge.jsonl        # 3,244 records
│   ├── dosha_knowledge.jsonl       # 3,128 records
│   ├── food_diet_knowledge.jsonl   # 5,110 records
│   ├── asana_knowledge.jsonl       # 1,371 records
│   ├── formulations.jsonl          # 1,623 records
│   ├── ... (+ 7 more categories)
│   └── master_index.jsonl          # 48,667 records (complete dataset)
├── tests/                    # 96 tests
├── run_server.py             # Start API + Web UI
├── run_rag.py                # CLI chat interface
├── run_ingestion.py          # Parse all documents
├── build_vector_store.py     # Build ChromaDB embeddings
├── ingest_ngpt.py            # Ingest NGPT books
├── ingest_ocr.py             # Ingest OCR'd books
├── extract_structured_data.py # Generate data1/ category JSONL files
├── generate_prakriti_diagnosis_tree.py  # Generate diagnosis Excel
├── generate_vikriti_sheet.py            # Generate vikriti Excel
└── update_diagnosis_herbs.py            # Add herb mappings to Excel
```

## Quick Start

```bash
# Clone
git clone https://github.com/sriatmaprabha/ayurveda.git
cd ayurveda

# Install
python -m venv venv
venv\Scripts\activate     # Windows
pip install -r requirements.txt

# Start (requires Ollama with llama3)
python run_server.py
# Open http://localhost:8000
```

## Usage

### Web UI (Recommended)

```bash
python run_server.py
# Open http://localhost:8000 in browser
```

ChatGPT-style interface with:
- Streaming responses
- Prakriti profiling (asks body constitution questions gradually)
- Dosha score visualization in sidebar
- Quick action buttons (Recommend Asanas, Check Dosha, etc.)
- Dark/light theme

### CLI

```bash
python run_rag.py --model llama3
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/chat/start` | Start diagnostic conversation |
| POST | `/chat/stream` | Stream a response (token-by-token) |
| POST | `/chat/message` | Send message (non-streaming) |
| GET | `/chat/history/{id}` | Get conversation history |
| POST | `/chat/recommend/asana` | Get asana protocols by dosha/symptoms |
| POST | `/query` | Direct knowledge base query |
| POST | `/diagnose/level1/submit` | Submit diagnostic answers |
| POST | `/diagnose/pariksha/{type}` | Image-based Pariksha (tongue/eyes/nails/face/skin/body/lips) |
| GET | `/diagnose/pariksha/text/{type}` | Text-based Pariksha questions |
| POST | `/vision/query` | Ask about an uploaded image |
| GET | `/status` | Pipeline health check |
| GET | `/stats` | Performance metrics |
| GET | `/docs` | Swagger API documentation |

### Environment Variables

```bash
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=llama3
VISION_MODEL=llama4
MONITOR_MODEL=mistral
ENABLE_MONITORING=true
```

### Data Extraction

```bash
# Regenerate structured JSONL files in data1/
python extract_structured_data.py

# Regenerate diagnosis Excel
python generate_prakriti_diagnosis_tree.py
python update_diagnosis_herbs.py
python update_asana_mapping.py
```

### Tests

```bash
python -m pytest tests/ -v
# 96 tests covering: ingestion, vector store, generation, conversation,
# casual detection, prakriti profiling, protocol mapping, diagnostics,
# text pariksha, vision, API endpoints, asana recommender
```

## Diagnostic Flow

```
User: "I have joint pain and anxiety"

1. Casual check: Not casual -> proceed
2. Protocol mapper: Matches "Arthritis" + "Anxiety" -> fixed Cure protocols
3. Vector search: Retrieves relevant Charaka/Sushruta verses
4. LLM generates: Answer with full asana instructions + herb recommendations
5. Prakriti question appended: "How would you describe your body frame?"

User: "Thin and lean"

6. Prakriti scored: Vata +1
7. Next response personalized for Vata body type
8. Next prakriti question: "How is your digestion?"

...after 6 answers...

9. Prakriti determined: Vata dominant
10. All future answers personalized: Vata-specific diet, herbs, asanas, lifestyle
```

## Excel Diagnosis Sheets

### Prakriti_Dosha_Diagnosis_Tree_v2.xlsx (6 sheets)

1. **Prakriti Diagnosis Tree** -- 5-layer, 18-question progressive diagnosis
2. **Disease Protocols** -- 25+ conditions with herbs, yoga, Panchakarma
3. **Dosha Diet Reference** -- 13 food categories x 3 doshas
4. **Herb-Condition Map** -- 27 conditions with herbs, dosages, classical verses
5. **Asana Details (Top 50)** -- Full technique instructions for most-used asanas
6. **Condition-Asana Map** -- All 111 protocols with complete step-by-step

### Vikriti_Dosha_Diagnosis_Guide.xlsx (4 sheets)

1. **Single Dosha Vikriti** -- Vata/Pitta/Kapha symptoms + cures + follow-up questions
2. **Dual Dosha Vikriti** -- Vata-Pitta, Vata-Kapha, Pitta-Kapha
3. **Tridosha Vikriti (Sannipata)** -- Emergency protocols
4. **Diagnostic Flowchart** -- 10-step decision tree

## Roadmap

- [x] Phase 1 -- Document ingestion (PDF, CSV, MD, SQL, TXT)
- [x] Phase 2 -- Vector store (ChromaDB, 55,560 chunks)
- [x] Phase 3 -- LLM answer generation (streaming, OpenAI-compatible)
- [x] Phase 4 -- Vision pipeline (Llama 4 image processing)
- [x] Phase 5 -- Orchestrator monitoring (quality evaluation + logging)
- [x] Phase 6 -- FastAPI REST API + ChatGPT-style Web UI
- [x] Phase 7 -- Prakriti profiling + consistent asana protocols
- [x] Phase 8 -- 7 Pariksha types (image + text) + diagnostic engine
- [x] Phase 9 -- OCR ingestion (42 books via 1OCR)
- [x] Phase 10 -- Structured data extraction (13 categories, 48,667 records)
- [ ] Phase 11 -- Multi-turn memory across sessions (Redis/DB)
- [ ] Phase 12 -- Deployment (Docker + cloud hosting)

## License

This project is for educational and research purposes.
