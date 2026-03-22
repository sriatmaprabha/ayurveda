"""Vector store using ChromaDB for document chunk storage and retrieval."""

import json
import logging
from pathlib import Path

import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)


class VectorStore:
    """Manages ChromaDB vector store for Ayurveda document chunks."""

    def __init__(
        self,
        persist_dir: str | Path = "data/vector_store",
        collection_name: str = "ayurveda_knowledge",
    ):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    @property
    def count(self) -> int:
        return self.collection.count()

    def add_chunks(
        self,
        chunks_path: str | Path,
        batch_size: int = 500,
    ) -> int:
        """Load chunks from JSONL and add to the vector store."""
        chunks_path = Path(chunks_path)
        records = []

        with open(chunks_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))

        logger.info(f"Loaded {len(records)} chunks from {chunks_path}")

        added = 0
        for i in range(0, len(records), batch_size):
            batch = records[i : i + batch_size]

            ids = [f"chunk_{i + j}" for j in range(len(batch))]
            documents = [r["text"] for r in batch]
            metadatas = []
            for r in batch:
                meta = {
                    "source_file": r.get("source_file", ""),
                    "section_title": r.get("section_title", ""),
                    "section_type": r.get("section_type", ""),
                    "file_name": r.get("metadata", {}).get("file_name", ""),
                    "file_type": r.get("metadata", {}).get("file_type", ""),
                }
                # ChromaDB metadata values must be str, int, float, or bool
                meta = {k: v for k, v in meta.items() if isinstance(v, (str, int, float, bool))}
                metadatas.append(meta)

            self.collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
            )
            added += len(batch)
            logger.info(f"  Added {added}/{len(records)} chunks")

        logger.info(f"Vector store now contains {self.count} chunks")
        return added

    def query(
        self,
        query_text: str,
        top_k: int = 5,
        where: dict | None = None,
    ) -> list[dict]:
        """Search for relevant chunks given a query string."""
        kwargs = {
            "query_texts": [query_text],
            "n_results": top_k,
        }
        if where:
            kwargs["where"] = where

        results = self.collection.query(**kwargs)

        output = []
        for i in range(len(results["ids"][0])):
            output.append({
                "id": results["ids"][0][i],
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "distance": results["distances"][0][i] if results["distances"] else None,
            })

        return output

    def delete_all(self):
        """Clear the entire collection."""
        self.client.delete_collection(self.collection.name)
        self.collection = self.client.get_or_create_collection(
            name="ayurveda_knowledge",
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("Vector store cleared")
