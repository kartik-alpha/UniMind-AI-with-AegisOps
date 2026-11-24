import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.document import Document
from rag.ingestion.extractor import extract_text_from_file
from rag.ingestion.chunker import chunk_text
from rag.vector_store.chroma_service import get_chroma_store
from rag.retrieval.bm25 import get_bm25_index
from rag.retrieval.query_expander import expand_query
from rag.retrieval.reranker import reciprocal_rank_fusion, rerank_and_filter

logger = logging.getLogger(__name__)


def get_vector_adapter():
    """
    Resolves the active VectorDatabaseAdapter via AdapterFactory (Stage H architecture).
    Provides pluggable support for ChromaDB and Qdrant with seamless backward compatibility.
    """
    try:
        from app.adapters.factory import AdapterFactory
        return AdapterFactory.get_vector()
    except Exception as e:
        logger.warning(f"Could not load AdapterFactory vector adapter: {e}. Falling back to LocalChromaAdapter.")
        from app.adapters.vector import LocalChromaAdapter
        adapter = LocalChromaAdapter()
        adapter.connect()
        return adapter


def sync_bm25_from_vector_store(tenant_id: int = 1) -> int:
    """
    Synchronizes the in-memory BM25 index with persistent vector storage for the specified tenant.
    Runs idempotently on startup or first search if the BM25 index is empty.
    """
    bm25 = get_bm25_index(tenant_id=tenant_id)
    if bm25.total_docs > 0:
        return bm25.total_docs

    try:
        adapter = get_vector_adapter()
        chunks_to_index = adapter.get_all_chunks(tenant_id=tenant_id)
        if chunks_to_index:
            bm25.add_chunks(chunks_to_index)
            logger.info(f"[Tenant {tenant_id}] Synchronized {len(chunks_to_index)} chunks from vector adapter into BM25 index.")
        return bm25.total_docs
    except Exception as e:
        logger.warning(f"[Tenant {tenant_id}] Could not sync BM25 from vector store via adapter: {e}")
        try:
            chroma_store = get_chroma_store(tenant_id=tenant_id)
            data = chroma_store.collection.get()
            if not data or not data.get("ids"):
                return 0
            ids = data.get("ids", [])
            documents = data.get("documents", [])
            metadatas = data.get("metadatas", []) or [{}] * len(ids)

            chunks_to_index = []
            for cid, text, meta in zip(ids, documents, metadatas):
                chunks_to_index.append({
                    "chunk_id": cid,
                    "text": text,
                    "metadata": meta or {},
                })
            bm25.add_chunks(chunks_to_index)
            return bm25.total_docs
        except Exception:
            return 0


def ingest_document_to_rag(db: Session, document_id: int, tenant_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Ingests an uploaded university/enterprise document into both:
    1. Persistent Vector Store (ChromaDB/Qdrant dense embeddings, partitioned per tenant via AdapterFactory)
    2. BM25 Lexical Index (sparse token frequencies, partitioned per tenant)
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise ValueError(f"Document {document_id} not found in database.")

    t_id = tenant_id if tenant_id is not None else (getattr(doc, "tenant_id", None) or 1)

    raw_text = extract_text_from_file(doc.file_path)
    metadata = {
        "doc_id": doc.id,
        "title": doc.title,
        "category": doc.category,
        "filename": doc.filename,
        "source": doc.filename,
        "tenant_id": t_id,
    }

    chunks = chunk_text(raw_text, chunk_size=300, chunk_overlap=40, metadata=metadata)

    # 1. Add to vector store for this tenant via Vector Database Adapter
    adapter = get_vector_adapter()
    adapter.upsert_chunks(tenant_id=t_id, chunks=chunks)

    # 2. Add to BM25 index for this tenant
    bm25 = get_bm25_index(tenant_id=t_id)
    bm25.add_chunks(chunks)

    # 3. Update chunk count in document record
    doc.chunk_count = len(chunks)
    db.commit()

    return {
        "document_id": doc.id,
        "title": doc.title,
        "category": doc.category,
        "tenant_id": t_id,
        "chunks_indexed": len(chunks),
    }


def delete_document_from_rag(document_id: int, tenant_id: int = 1):
    """
    Deletes all chunks belonging to a document from both Vector Store and BM25.
    """
    adapter = get_vector_adapter()
    adapter.delete_document_chunks(tenant_id=tenant_id, doc_id=document_id)

    bm25 = get_bm25_index(tenant_id=tenant_id)
    bm25.remove_by_doc_id(document_id)


def search_knowledge_base(
    query: str,
    top_k: int = 4,
    category_filter: Optional[str] = None,
    mode: str = "hybrid",
    use_expansion: bool = True,
    tenant_id: int = 1,
) -> List[Dict[str, Any]]:
    """
    High-performance Knowledge Base Retrieval partitioned by tenant.
    Supports:
      - 'hybrid' (Default): Dense Vector + BM25 Lexical + Reciprocal Rank Fusion + Re-ranking
      - 'dense': Dense Vector Search (ChromaDB)
      - 'bm25': BM25 Okapi Lexical Search
    """
    # Ensure BM25 has documents synced for this tenant
    sync_bm25_from_vector_store(tenant_id=tenant_id)

    # Query expansion
    expanded_info = expand_query(query) if use_expansion else {"expanded_query": query, "expanded_terms": []}
    search_query = expanded_info.get("expanded_query") or query

    adapter = get_vector_adapter()
    bm25 = get_bm25_index(tenant_id=tenant_id)

    mode_lower = mode.lower().strip()

    if mode_lower == "bm25":
        results = bm25.search(query=search_query, top_k=top_k, category_filter=category_filter)
        return results

    if mode_lower == "dense":
        return adapter.query_similar(tenant_id=tenant_id, query_text=query, top_k=top_k, category_filter=category_filter)

    # Default: Hybrid Mode
    candidate_k = min(top_k * 3, 12)

    # 1. Fetch dense candidates
    dense_candidates = adapter.query_similar(
        tenant_id=tenant_id,
        query_text=query,
        top_k=candidate_k,
        category_filter=category_filter,
    )

    # 2. Fetch BM25 candidates using expanded query for maximum recall
    bm25_candidates = bm25.search(
        query=search_query,
        top_k=candidate_k,
        category_filter=category_filter,
    )

    # If BM25 has no results (e.g. index newly created or no lexical matches), fallback to dense
    if not bm25_candidates:
        final_ranked = dense_candidates[:top_k]
    # If Dense has no results, fallback to BM25
    elif not dense_candidates:
        final_ranked = bm25_candidates[:top_k]
    else:
        # 3. Reciprocal Rank Fusion (RRF)
        fused_candidates = reciprocal_rank_fusion(
            dense_results=dense_candidates,
            bm25_results=bm25_candidates,
            k=60,
        )

        # 4. Multi-factor Re-ranking and Threshold Filtering
        final_ranked = rerank_and_filter(
            candidates=fused_candidates,
            query=query,
            top_k=top_k,
        )

    # 5. Enrich all results with structured verifiable citations
    for item in final_ranked:
        meta = item.get("metadata", {})
        title = meta.get("title") or meta.get("filename") or "Institutional Document"
        section = meta.get("section_heading") or "General"
        doc_id = meta.get("doc_id")
        citation_str = f"[{title} - {section}]" if title else "[Document Citation]"
        item["citation"] = {
            "source_title": title,
            "section_heading": section,
            "document_id": doc_id,
            "category": meta.get("category", "general"),
            "relevance_score": item.get("similarity_score", 0.0),
            "citation_tag": citation_str,
        }
        item["citation_text"] = citation_str

    return final_ranked


def reindex_tenant_knowledge_base(db: Session, tenant_id: int) -> Dict[str, Any]:
    """
    Full re-indexing of all active documents for a tenant into both Vector Store and BM25 index.
    Clears existing indices for this tenant and repopulates them cleanly from disk.
    """
    from pathlib import Path
    adapter = get_vector_adapter()
    bm25 = get_bm25_index(tenant_id=tenant_id)

    # 1. Clear existing index structures for tenant
    try:
        bm25.clear()
    except Exception as e:
        logger.warning(f"Error clearing BM25 index for tenant {tenant_id}: {e}")

    try:
        adapter.clear_tenant_store(tenant_id=tenant_id)
    except Exception as e:
        try:
            store = get_chroma_store(tenant_id=tenant_id)
            store.clear_all()
        except Exception as e2:
            logger.warning(f"Error clearing vector store for tenant {tenant_id}: {e2}")

    # 2. Fetch all documents for this tenant
    docs = db.query(Document).filter(Document.tenant_id == tenant_id).all()
    total_indexed = 0
    total_chunks = 0

    for doc in docs:
        try:
            if not Path(doc.file_path).exists():
                logger.warning(f"File {doc.file_path} for doc {doc.id} does not exist on disk. Skipping.")
                continue
            res = ingest_document_to_rag(db=db, document_id=doc.id, tenant_id=tenant_id)
            total_indexed += 1
            total_chunks += res.get("chunks_indexed", 0)
        except Exception as ex:
            logger.error(f"Failed to reindex document {doc.id} ({doc.title}): {ex}")

    return {
        "tenant_id": tenant_id,
        "documents_found": len(docs),
        "documents_indexed": total_indexed,
        "total_chunks_indexed": total_chunks,
        "status": "COMPLETED",
    }
