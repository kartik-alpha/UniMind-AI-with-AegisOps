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


def sync_bm25_from_vector_store() -> int:
    """
    Synchronizes the in-memory BM25 index with persistent ChromaDB.
    Runs idempotently on startup or first search if the BM25 index is empty.
    """
    bm25 = get_bm25_index()
    if bm25.total_docs > 0:
        return bm25.total_docs

    chroma_store = get_chroma_store()
    try:
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
        logger.info(f"Synchronized {len(chunks_to_index)} chunks from ChromaDB into BM25 index.")
        return bm25.total_docs
    except Exception as e:
        logger.warning(f"Could not sync BM25 from ChromaDB: {e}")
        return 0


def ingest_document_to_rag(db: Session, document_id: int) -> Dict[str, Any]:
    """
    Ingests an uploaded university document into both:
    1. Persistent ChromaDB Vector Store (dense embeddings)
    2. BM25 Lexical Index (sparse token frequencies)
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise ValueError(f"Document {document_id} not found in database.")

    raw_text = extract_text_from_file(doc.file_path)
    metadata = {
        "doc_id": doc.id,
        "title": doc.title,
        "category": doc.category,
        "filename": doc.filename,
        "source": doc.filename,
    }

    chunks = chunk_text(raw_text, chunk_size=300, chunk_overlap=40, metadata=metadata)

    # 1. Add to ChromaDB vector store
    chroma_store = get_chroma_store()
    chroma_store.add_chunks(chunks)

    # 2. Add to BM25 index
    bm25 = get_bm25_index()
    bm25.add_chunks(chunks)

    # 3. Update chunk count in document record
    doc.chunk_count = len(chunks)
    db.commit()

    return {
        "document_id": doc.id,
        "title": doc.title,
        "category": doc.category,
        "chunks_indexed": len(chunks),
    }


def delete_document_from_rag(document_id: int):
    """
    Deletes all chunks belonging to a document from both ChromaDB and BM25.
    """
    chroma_store = get_chroma_store()
    chroma_store.delete_document_chunks(document_id)

    bm25 = get_bm25_index()
    bm25.remove_by_doc_id(document_id)


def search_knowledge_base(
    query: str,
    top_k: int = 4,
    category_filter: Optional[str] = None,
    mode: str = "hybrid",
    use_expansion: bool = True,
) -> List[Dict[str, Any]]:
    """
    High-performance Knowledge Base Retrieval.
    Supports:
      - 'hybrid' (Default): Dense Vector + BM25 Lexical + Reciprocal Rank Fusion + Re-ranking
      - 'dense': Dense Vector Search (ChromaDB)
      - 'bm25': BM25 Okapi Lexical Search
    """
    # Ensure BM25 has documents synced
    sync_bm25_from_vector_store()

    # Query expansion
    expanded_info = expand_query(query) if use_expansion else {"expanded_query": query, "expanded_terms": []}
    search_query = expanded_info.get("expanded_query") or query

    chroma_store = get_chroma_store()
    bm25 = get_bm25_index()

    mode_lower = mode.lower().strip()

    if mode_lower == "bm25":
        results = bm25.search(query=search_query, top_k=top_k, category_filter=category_filter)
        return results

    if mode_lower == "dense":
        return chroma_store.query(query_text=query, top_k=top_k, category_filter=category_filter)

    # Default: Hybrid Mode
    candidate_k = min(top_k * 3, 12)

    # 1. Fetch dense candidates
    dense_candidates = chroma_store.query(
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
        return dense_candidates[:top_k]

    # If Dense has no results, fallback to BM25
    if not dense_candidates:
        return bm25_candidates[:top_k]

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

    return final_ranked
