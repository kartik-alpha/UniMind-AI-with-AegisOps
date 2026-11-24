import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import settings
from rag.embeddings.embedding_service import generate_embeddings, generate_embedding


_shared_chroma_client: Optional[chromadb.PersistentClient] = None


def get_shared_chroma_client(persist_dir: str) -> chromadb.PersistentClient:
    global _shared_chroma_client
    if _shared_chroma_client is None:
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        _shared_chroma_client = chromadb.PersistentClient(path=persist_dir)
    return _shared_chroma_client


class ChromaStore:
    def __init__(self, persist_directory: Optional[str] = None, tenant_id: int = 1):
        self.persist_dir = persist_directory or settings.CHROMA_PERSIST_DIR
        self.client = get_shared_chroma_client(self.persist_dir)
        self.tenant_id = tenant_id

        # Tenant-dedicated collection partitioning
        if tenant_id == 1:
            # Default / legacy collection name for 100% backward compatibility
            self.collection_name = "university_knowledge_base"
        else:
            self.collection_name = f"tenant_{tenant_id}_kb"

        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": f"Tenant {tenant_id} Enterprise Knowledge Base", "tenant_id": tenant_id}
        )

    def add_chunks(self, chunks: List[Dict[str, Any]]):
        if not chunks:
            return

        ids = [c["chunk_id"] for c in chunks]
        documents = [c["text"] for c in chunks]
        metadatas = []

        for c in chunks:
            meta = c.get("metadata", {}).copy()
            # Ensure tenant_id is always stamped in metadata
            meta["tenant_id"] = self.tenant_id
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
        self,
        query_text: str,
        top_k: int = 4,
        category_filter: Optional[str] = None,
        tenant_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        query_embedding = generate_embedding(query_text)

        # Defense-in-depth: strictly enforce tenant_id in query filter
        tid = tenant_id or self.tenant_id
        if category_filter:
            where_clause = {
                "$and": [
                    {"category": {"$eq": category_filter}},
                    {"tenant_id": {"$eq": tid}},
                ]
            }
        else:
            where_clause = {"tenant_id": {"$eq": tid}}

        try:
            if self.collection.count() == 0:
                return []
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_clause,
            )
        except Exception as e:
            # Fallback to collection.get() if HNSW segment is pending compaction on disk
            try:
                get_results = self.collection.get(where=where_clause, limit=top_k)
                if get_results and get_results.get("documents"):
                    docs = get_results["documents"]
                    metas = get_results.get("metadatas") or [{}] * len(docs)
                    ids = get_results.get("ids") or [""] * len(docs)
                    retrieved = []
                    for doc, meta, cid in zip(docs, metas, ids):
                        retrieved.append({
                            "chunk_id": cid,
                            "text": doc,
                            "metadata": meta,
                            "similarity_score": 0.5,
                        })
                    return retrieved
            except Exception:
                pass
            return []

        retrieved = []
        if results and results["documents"]:
            docs = results["documents"][0]
            metas = results["metadatas"][0] if results["metadatas"] else [{}] * len(docs)
            distances = results["distances"][0] if results["distances"] else [0.0] * len(docs)
            ids = results["ids"][0] if results["ids"] else [""] * len(docs)

            for doc, meta, dist, cid in zip(docs, metas, distances, ids):
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
                metadata={"description": f"Tenant {self.tenant_id} Enterprise Knowledge Base"}
            )
        except Exception:
            pass

    def get_stats(self) -> Dict[str, Any]:
        return {
            "collection_name": self.collection_name,
            "tenant_id": self.tenant_id,
            "total_chunks": self.collection.count(),
            "persist_dir": self.persist_dir,
        }


# Per-tenant ChromaStore registry (prevents cross-tenant collection collisions)
_tenant_chroma_registry: Dict[int, ChromaStore] = {}


def get_chroma_store(tenant_id: int = 1) -> ChromaStore:
    global _tenant_chroma_registry
    if tenant_id not in _tenant_chroma_registry:
        _tenant_chroma_registry[tenant_id] = ChromaStore(tenant_id=tenant_id)
    return _tenant_chroma_registry[tenant_id]
