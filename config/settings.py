"""Central configuration for the Ayurveda RAG system."""

from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
KNOWLEDGE_BASE_DIR = PROJECT_ROOT / "knowledge_base"

# Ingestion
CHUNK_SIZE = 512          # words per chunk
CHUNK_OVERLAP = 64        # overlapping words between chunks

# Embedding
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
VECTOR_DB_DIR = DATA_DIR / "vector_store"

# LLM Configuration
LLM_CONFIG = {
    "vision": {
        "model": "meta-llama/Llama-4",
        "role": "Image processing and text extraction",
    },
    "interpreter": {
        "model": "gpt-oss",
        "role": "Document interpretation and answer generation",
    },
    "orchestrator": {
        "model": "mistral",  # or kimi-k2
        "role": "Pipeline monitoring and query routing",
    },
}

# Retrieval
TOP_K_RESULTS = 3         # number of chunks to retrieve per query (reduced for speed)
SIMILARITY_THRESHOLD = 0.3
