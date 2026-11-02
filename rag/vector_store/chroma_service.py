import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import settings
from rag.embeddings.embedding_service import generate_embeddings, generate_embedding


class ChromaStore:
    def __init__(self, persist_directory: Optional[str] = None):
        self.persist_dir = persist_directory or settings.CHROMA_PERSIST_DIR
        Path(self.persist_dir).mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=self.persist_dir)
        self.collection_name = "university_knowledge_base"
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "UniMind University Support Knowledge Base"}
        )

    def add_chunks(self, chunks: List[Dict[str, Any]]):
        if not chunks:
            return

        ids = [c["chunk_id"] for c in chunks]
        documents = [c["text"] for c in chunks]
        metadatas = []

        for c in chunks:
            meta = c.get("metadata", {})
            # Ensure all metadata values are primitive types for ChromaDB
            clean_meta = {}
            for k, v in meta.items():
                if isinstance(v, (str, int, float, bool)):
                    clean_meta[k] = v
                else:
                    clean_meta[k] = str(v)
            metadatas.append(clean_meta)

        embeddings = generate_embeddings(documents)

        self.collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )

    def query(
        self, query_text: str, top_k: int = 4, category_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        query_embedding = generate_embedding(query_text)
        where_clause = {"category": category_filter} if category_filter else None

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_clause,
        )

        retrieved = []
        if results and results["documents"]:
            docs = results["documents"][0]
            metas = results["metadatas"][0] if results["metadatas"] else [{}] * len(docs)
            distances = results["distances"][0] if results["distances"] else [0.0] * len(docs)
            ids = results["ids"][0] if results["ids"] else [""] * len(docs)

            for doc, meta, dist, cid in zip(docs, metas, distances, ids):
                # Convert distance to similarity score
                similarity = round(max(0.0, 1.0 - (dist / 2.0)), 4)
                retrieved.append({
                    "chunk_id": cid,
                    "text": doc,
                    "metadata": meta,
                    "similarity_score": similarity,
                })

        return retrieved

    def delete_document_chunks(self, doc_id: int):
        try:
            self.collection.delete(where={"doc_id": doc_id})
        except Exception:
            pass

    def clear_all(self):
        try:
            self.client.delete_collection(self.collection_name)
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "UniMind University Support Knowledge Base"}
            )
        except Exception:
            pass

    def get_stats(self) -> Dict[str, Any]:
        return {
            "collection_name": self.collection_name,
            "total_chunks": self.collection.count(),
            "persist_dir": self.persist_dir,
        }


_chroma_instance = None


def get_chroma_store() -> ChromaStore:
    global _chroma_instance
    if _chroma_instance is None:
        _chroma_instance = ChromaStore()
    return _chroma_instance
