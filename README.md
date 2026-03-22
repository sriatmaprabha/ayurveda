# Ayurveda RAG System

A multi-LLM Retrieval-Augmented Generation (RAG) system for Ayurveda knowledge. Ask questions about Ayurveda and get answers grounded in authentic classical texts — Charaka Samhita, Sushruta Samhita, Ashtanga Hridaya, yoga asanas, and more.

## Architecture

```
User Query (text/image)
        │
        ▼
┌─────────────────────────┐
│  Orchestrator            │  Mistral / Kimi K2
│  (monitors & routes)     │
└────────┬────────────────┘
    ┌────┴────┐
    ▼         ▼
 Llama 4     Text Query
 (vision)    Processing
    └────┬────┘
         ▼
  Vector DB (ChromaDB)  ←  Chunked & embedded documents
         │
         ▼
    GPT-OSS (Answer Generation with source citations)
```

### LLM Roles

| Model | Role |
|-------|------|
| Meta Llama 4 | Image input processing (book scans, diagrams, herb photos) |
| GPT-OSS | Document interpretation and answer generation |
| Mistral / Kimi K2 | Pipeline orchestration and monitoring |

## Knowledge Base

Classical Ayurveda texts included:

- **Charaka Samhita** (Volumes 1, 2, 6)
- **Sushruta Samhita** (Volumes 1-3, all sections: Sutra, Nidana, Sharira, Chikitsa, Kalpa, Uttara)
- **Ashtanga Hridaya** (Sutrasthana Handbook)
- **Food Guidelines** (Ayurvedic dietary recommendations)
- **Yoga Asanas** (195 asanas with techniques, benefits, difficulty levels)
- **Asana Recommendations** (114 therapeutic protocols for 50+ health conditions)

Documents are available in PDF, CSV, MD, TXT, and SQL formats.

## Project Structure

```
Ayurveda/
├── knowledge_base/        # Source documents (PDF, CSV, MD, TXT)
├── src/
│   ├── ingestion/         # Document parsers & chunking pipeline
│   │   ├── base_parser.py    # Base parser interface
│   │   ├── pdf_parser.py     # PDF extraction (PyMuPDF)
│   │   ├── csv_parser.py     # CSV row parsing
│   │   ├── md_parser.py      # Markdown section splitting
│   │   ├── sql_parser.py     # SQL INSERT extraction
│   │   ├── txt_parser.py     # Plain text chapter/paragraph splitting
│   │   ├── chunker.py        # Overlapping chunk splitter
│   │   └── pipeline.py       # Main ingestion orchestrator
│   ├── embeddings/        # Vector embedding logic (Phase 2)
│   ├── retrieval/         # Query & retrieval pipeline (Phase 3)
│   ├── generation/        # LLM answer generation (Phase 3)
│   ├── vision/            # Llama 4 image processing (Phase 4)
│   ├── orchestrator/      # Pipeline monitoring (Phase 5)
│   └── api/               # FastAPI endpoints (Phase 6)
├── config/
│   └── settings.py        # Central configuration
├── data/
│   ├── raw/               # Additional raw documents
│   └── processed/         # Generated chunks (JSONL)
├── tests/
├── run_ingestion.py       # Entry point for ingestion
├── requirements.txt
└── .gitignore
```

## Setup

```bash
# Clone the repository
git clone https://github.com/sriatmaprabha/ayurveda.git
cd ayurveda

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Run Document Ingestion (Phase 1)

```bash
python run_ingestion.py
```

This parses all documents in `knowledge_base/`, `insert_asanas.sql`, and `asana_recommendations.csv`, then saves processed chunks to `data/processed/chunks.jsonl`.

### Build Vector Store (Phase 2)

```bash
python build_vector_store.py
```

Embeds all chunks and stores them in ChromaDB at `data/vector_store/`.

### Test Retrieval (Phase 2)

```bash
python query_test.py
```

Interactive CLI to test querying the knowledge base.

### Ask Questions — Full RAG (Phase 3)

```bash
# Using Ollama (default, local)
python run_rag.py --model llama3

# Using a different provider
python run_rag.py --model llama4 --base-url http://localhost:11434/v1

# Check pipeline health
python run_rag.py --status
```

Requires an LLM server running locally (Ollama, vLLM, or LM Studio) or a remote OpenAI-compatible API. See `config/llm_profiles.py` for pre-configured profiles.

**Supported LLM providers:**
- [Ollama](https://ollama.com) — `ollama serve` then `ollama pull llama3`
- [vLLM](https://vllm.ai) — for GPU-accelerated inference
- [LM Studio](https://lmstudio.ai) — GUI-based local inference
- Any OpenAI-compatible API (Together AI, Groq, etc.)

### Run Tests

```bash
python -m pytest tests/ -v
```

## Roadmap

- [x] **Phase 1** — Document ingestion pipeline (parsers for PDF, CSV, MD, SQL, TXT + chunking)
- [x] **Phase 2** — Vector store (ChromaDB + sentence-transformer embeddings)
- [x] **Phase 3** — Retrieval + answer generation (OpenAI-compatible LLMs)
- [ ] **Phase 4** — Vision pipeline (Llama 4 image processing)
- [ ] **Phase 5** — Orchestrator (Mistral/Kimi K2 monitoring)
- [ ] **Phase 6** — FastAPI endpoints + deployment

## License

This project is for educational and research purposes.
