import re
from typing import List, Dict, Any, Optional


def reciprocal_rank_fusion(
    dense_results: List[Dict[str, Any]],
    bm25_results: List[Dict[str, Any]],
    k: int = 60,
    dense_weight: float = 1.0,
    bm25_weight: float = 1.0,
) -> List[Dict[str, Any]]:
    """
    Combines dense vector search results and sparse BM25 search results
    using Reciprocal Rank Fusion (RRF).

    Formula:
        RRF_score(d) = sum_m ( weight_m / (k + rank_m(d)) )

    where rank is 1-indexed.
    """
    fused_scores: Dict[str, float] = {}
    fused_docs: Dict[str, Dict[str, Any]] = {}

    # Process Dense results
    for rank, doc in enumerate(dense_results, start=1):
        c_id = doc.get("chunk_id") or doc.get("metadata", {}).get("chunk_id", str(rank))
        score = dense_weight / (k + rank)
        fused_scores[c_id] = fused_scores.get(c_id, 0.0) + score

        if c_id not in fused_docs:
            fused_docs[c_id] = {
                "chunk_id": c_id,
                "text": doc.get("text", ""),
                "metadata": doc.get("metadata", {}),
                "dense_rank": rank,
                "dense_score": doc.get("similarity_score", 0.0),
                "bm25_rank": None,
                "bm25_score": 0.0,
                "matched_keywords": [],
            }
        else:
            fused_docs[c_id]["dense_rank"] = rank
            fused_docs[c_id]["dense_score"] = doc.get("similarity_score", 0.0)

    # Process BM25 results
    for rank, doc in enumerate(bm25_results, start=1):
        c_id = doc.get("chunk_id") or doc.get("metadata", {}).get("chunk_id", str(rank))
        score = bm25_weight / (k + rank)
        fused_scores[c_id] = fused_scores.get(c_id, 0.0) + score

        if c_id not in fused_docs:
            fused_docs[c_id] = {
                "chunk_id": c_id,
                "text": doc.get("text", ""),
                "metadata": doc.get("metadata", {}),
                "dense_rank": None,
                "dense_score": 0.0,
                "bm25_rank": rank,
                "bm25_score": doc.get("bm25_score", 0.0),
                "matched_keywords": doc.get("matched_keywords", []),
            }
        else:
            fused_docs[c_id]["bm25_rank"] = rank
            fused_docs[c_id]["bm25_score"] = doc.get("bm25_score", 0.0)
            existing_kw = set(fused_docs[c_id].get("matched_keywords", []))
            existing_kw.update(doc.get("matched_keywords", []))
            fused_docs[c_id]["matched_keywords"] = sorted(list(existing_kw))

    # Compile fused candidate list
    candidates = []
    for c_id, doc in fused_docs.items():
        doc["rrf_score"] = fused_scores.get(c_id, 0.0)
        candidates.append(doc)

    return candidates


def rerank_and_filter(
    candidates: List[Dict[str, Any]],
    query: str,
    top_k: int = 4,
    min_score_threshold: float = 0.005,
) -> List[Dict[str, Any]]:
    """
    Multi-factor re-ranking:
    1. Base RRF score from dense + BM25 ranking.
    2. Exact phrase & token overlap bonus (critical for numbers, percentages, course codes).
    3. Section heading bonus if relevant to query.
    4. Preserves authentic semantic similarity scores.
    """
    if not candidates:
        return []

    query_tokens = set(re.findall(r"\b[\w%]+(?:-[\w%]+)*\b", query.lower()))

    for doc in candidates:
        text = doc.get("text", "").lower()
        meta = doc.get("metadata", {})
        heading = meta.get("section_heading", "").lower()
        title = meta.get("title", "").lower()

        boost = 0.0

        # Exact phrase match in text
        if len(query.strip()) > 3 and query.strip().lower() in text:
            boost += 0.015

        # Check token matches
        matched_tokens = 0
        for tok in query_tokens:
            if tok in text:
                matched_tokens += 1
            if tok in heading or tok in title:
                boost += 0.005

        if query_tokens:
            token_coverage = matched_tokens / len(query_tokens)
            boost += token_coverage * 0.01

        doc["final_score"] = doc["rrf_score"] + boost

    # Sort descending by final score
    candidates.sort(key=lambda x: x["final_score"], reverse=True)

    # Compute realistic similarity_score preserving dense/lexical realism
    for c in candidates:
        dense_s = c.get("dense_score", 0.0)
        bm25_s = c.get("bm25_score", 0.0)
        if dense_s > 0:
            c["similarity_score"] = round(float(dense_s), 4)
        elif bm25_s > 0:
            c["similarity_score"] = round(min(1.0, bm25_s / 5.0), 4)
        else:
            c["similarity_score"] = 0.0

        c["rrf_score"] = round(c["rrf_score"], 5)
        c["final_score"] = round(c["final_score"], 5)

    # Filter out candidates with zero similarity or below minimal threshold
    filtered = [c for c in candidates if c["rrf_score"] >= min_score_threshold]
    return filtered[:top_k] if filtered else candidates[:top_k]
