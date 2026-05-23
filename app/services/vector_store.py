import uuid
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings
from app.services.embeddings import embed_texts

COLLECTION_NAME = "company_docs"


class VectorStore:
    def __init__(self) -> None:
        settings.chroma_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=str(settings.chroma_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def add_chunks(self, chunks: list[dict], filename: str) -> int:
        if not chunks:
            return 0

        self.delete_document(filename)

        texts = [c["text"] for c in chunks]
        embeddings = embed_texts(texts)
        ids = [f"{filename}::{uuid.uuid4().hex[:8]}" for _ in chunks]
        metadatas = [c["metadata"] for c in chunks]

        self._collection.add(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        return len(chunks)

    def delete_document(self, filename: str) -> None:
        existing = self._collection.get(where={"filename": filename})
        if existing["ids"]:
            self._collection.delete(ids=existing["ids"])

    def search(self, query: str, top_k: int | None = None) -> list[dict]:
        from app.services.embeddings import embed_query

        k = top_k or settings.top_k
        if self._collection.count() == 0:
            return []

        query_embedding = embed_query(query)
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=min(k, self._collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        hits: list[dict] = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            hits.append(
                {
                    "text": doc,
                    "filename": meta.get("filename", "unknown"),
                    "score": round(1 - dist, 4),
                }
            )
        return hits

    def list_documents(self) -> list[dict]:
        if self._collection.count() == 0:
            return []

        all_meta = self._collection.get(include=["metadatas"])["metadatas"]
        counts: dict[str, int] = {}
        for meta in all_meta:
            name = meta.get("filename", "unknown")
            counts[name] = counts.get(name, 0) + 1

        return [
            {"filename": name, "chunk_count": count}
            for name, count in sorted(counts.items())
        ]

    @property
    def total_chunks(self) -> int:
        return self._collection.count()


_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    global _store
    if _store is None:
        _store = VectorStore()
    return _store
