from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_roles
from app.api.tenant_deps import get_current_tenant
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.schemas.rag import (
    RAGQueryRequest,
    RAGQueryResponse,
    RAGIngestResponse,
    RAGChunkResponse,
)
from rag.retrieval.retriever import ingest_document_to_rag, search_knowledge_base
from rag.vector_store.chroma_service import get_chroma_store
from rag.retrieval.query_expander import expand_query

router = APIRouter(prefix="/rag", tags=["RAG Management"])


@router.post("/ingest/{document_id}", response_model=RAGIngestResponse)
def ingest_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.FACULTY)),
    current_tenant: Organization = Depends(get_current_tenant),
):
    """
    Ingest an uploaded university/enterprise document into ChromaDB vector store and BM25 index for current tenant.
    """
    try:
        result = ingest_document_to_rag(db=db, document_id=document_id, tenant_id=current_tenant.id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest document: {str(e)}",
        )


@router.post("/query", response_model=RAGQueryResponse)
def query_knowledge_base(
    payload: RAGQueryRequest,
    current_user: User = Depends(get_current_user),
    current_tenant: Organization = Depends(get_current_tenant),
):
    """
    Perform hybrid/dense/BM25 search query against the knowledge base partitioned by tenant.
    """
    exp_info = expand_query(payload.query) if payload.use_expansion else {"expanded_terms": []}

    results = search_knowledge_base(
        query=payload.query,
        top_k=payload.top_k,
        category_filter=payload.category,
        mode=payload.mode or "hybrid",
        use_expansion=payload.use_expansion if payload.use_expansion is not None else True,
        tenant_id=current_tenant.id,
    )
    formatted = [RAGChunkResponse(**r) for r in results]
    return RAGQueryResponse(
        query=payload.query,
        results=formatted,
        total_found=len(formatted),
        mode=payload.mode or "hybrid",
        expanded_terms=exp_info.get("expanded_terms", []),
    )


@router.get("/stats")
def get_rag_stats(
    current_user: User = Depends(get_current_user),
    current_tenant: Organization = Depends(get_current_tenant),
):
    """
    Get RAG vector store and BM25 statistics for current tenant.
    """
    store = get_chroma_store(tenant_id=current_tenant.id)
    stats = store.get_stats()
    try:
        from rag.retrieval.bm25 import get_bm25_index
        bm25 = get_bm25_index(tenant_id=current_tenant.id)
        stats["bm25_total_docs"] = bm25.total_docs
        stats["bm25_vocabulary_size"] = len(bm25.doc_freqs)
    except Exception:
        pass
    stats["tenant_id"] = current_tenant.id
    stats["tenant_name"] = current_tenant.name
    return stats
