from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class RAGQueryRequest(BaseModel):
    query: str
    top_k: int = 4
    category: Optional[str] = None
    mode: Optional[str] = "hybrid"  # "hybrid", "dense", "bm25"
    use_expansion: Optional[bool] = True


class RAGChunkResponse(BaseModel):
    chunk_id: str
    text: str
    metadata: Dict[str, Any]
    similarity_score: float
    bm25_score: Optional[float] = None
    rrf_score: Optional[float] = None
    matched_keywords: Optional[List[str]] = None


class RAGQueryResponse(BaseModel):
    query: str
    results: List[RAGChunkResponse]
    total_found: int
    mode: Optional[str] = "hybrid"
    expanded_terms: Optional[List[str]] = None


class RAGIngestResponse(BaseModel):
    document_id: int
    title: str
    category: str
    chunks_indexed: int
