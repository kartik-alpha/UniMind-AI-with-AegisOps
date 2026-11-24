import sys
import os
from pathlib import Path

# Ensure project root and backend are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

import time
from typing import List, Dict, Any
import pytest

from rag.retrieval.retriever import search_knowledge_base
from ai.llm.llm_client import generate_llm_response, calculate_groundedness_score


# Formal Evaluation Dataset containing Ground Truth Policy Targets
EVALUATION_DATASET = [
    {
        "query": "What is the mandatory curfew time for undergraduate hostel residents?",
        "expected_category": "hostel",
        "expected_keywords": ["10:00 pm", "curfew", "hostel"],
        "is_grounded": True,
    },
    {
        "query": "What is the minimum attendance required to appear in final semester examinations?",
        "expected_category": "attendance",
        "expected_keywords": ["75%", "attendance", "examinations"],
        "is_grounded": True,
    },
    {
        "query": "Can a student with 68% attendance sit for exams on medical grounds?",
        "expected_category": "attendance",
        "expected_keywords": ["65%", "medical", "appeal", "7 working days"],
        "is_grounded": True,
    },
    {
        "query": "What is the minimum CGPA required for undergraduate degree conferral?",
        "expected_category": "academic",
        "expected_keywords": ["5.0", "cgpa", "degree"],
        "is_grounded": True,
    },
    {
        "query": "What are the rules regarding cryptocurrency mining and network sniffing in IT labs?",
        "expected_category": "it",
        "expected_keywords": ["cryptocurrency", "sniffing", "prohibited", "suspension"],
        "is_grounded": True,
    },
    {
        "query": "Within how many days must a student lodge an exam grade dispute appeal?",
        "expected_category": "academic",
        "expected_keywords": ["10 days", "grade", "appeal", "dispute"],
        "is_grounded": True,
    },
    # Out-of-Domain / Hallucination Trap Queries (Must be refused)
    {
        "query": "What is the university scholarship policy for interstellar astronaut training?",
        "expected_category": None,
        "expected_keywords": [],
        "is_grounded": False,
    },
    {
        "query": "What are the campus guidelines for keeping pet lions in hostel rooms?",
        "expected_category": None,
        "expected_keywords": [],
        "is_grounded": False,
    },
]


def ensure_knowledge_base_seeded():
    """Ensures all standard policy documents are present in ChromaDB and BM25."""
    from app.db.session import SessionLocal
    from app.models.document import Document
    from rag.ingestion.extractor import extract_text_from_file
    from rag.ingestion.chunker import chunk_text
    from rag.vector_store.chroma_service import get_chroma_store
    from rag.retrieval.bm25 import get_bm25_index

    db = SessionLocal()
    docs = db.query(Document).filter((Document.tenant_id == 1) | (Document.tenant_id.is_(None))).all()
    chroma_store = get_chroma_store(tenant_id=1)
    bm25 = get_bm25_index(tenant_id=1)

    for doc in docs:
        if os.path.exists(doc.file_path):
            raw_text = extract_text_from_file(doc.file_path)
            meta = {
                "doc_id": doc.id,
                "title": doc.title,
                "category": doc.category,
                "filename": doc.filename,
                "source": doc.filename,
            }
            chunks = chunk_text(raw_text, chunk_size=300, chunk_overlap=40, metadata=meta)
            chroma_store.add_chunks(chunks)
            bm25.add_chunks(chunks)
    db.close()


def evaluate_retrieval(mode: str = "hybrid") -> Dict[str, Any]:
    """
    Evaluates retrieval performance across Recall@K, MRR, latency, and groundedness.
    """
    ensure_knowledge_base_seeded()
    grounded_queries = [item for item in EVALUATION_DATASET if item["is_grounded"]]
    total_grounded = len(grounded_queries)

    hits_at_1 = 0
    hits_at_2 = 0
    hits_at_4 = 0
    reciprocal_ranks = []
    latencies = []
    groundedness_scores = []

    for item in grounded_queries:
        query = item["query"]
        t_start = time.perf_counter()
        results = search_knowledge_base(query=query, top_k=4, mode=mode)
        t_elapsed = (time.perf_counter() - t_start) * 1000.0  # ms
        latencies.append(t_elapsed)

        # Check rankings
        found_rank = 0
        for rank, res in enumerate(results, start=1):
            text_lower = res["text"].lower()
            cat = res.get("metadata", {}).get("category", "").lower()
            keyword_match = any(kw in text_lower for kw in item["expected_keywords"])
            category_match = cat == item["expected_category"]

            if keyword_match or category_match:
                found_rank = rank
                break

        if found_rank == 1:
            hits_at_1 += 1
        if 1 <= found_rank <= 2:
            hits_at_2 += 1
        if 1 <= found_rank <= 4:
            hits_at_4 += 1

        reciprocal_ranks.append(1.0 / found_rank if found_rank > 0 else 0.0)

        # Groundedness of top retrieved chunks
        g_score = calculate_groundedness_score(query, results)
        groundedness_scores.append(g_score)

    recall_at_1 = hits_at_1 / total_grounded
    recall_at_2 = hits_at_2 / total_grounded
    recall_at_4 = hits_at_4 / total_grounded
    mrr = sum(reciprocal_ranks) / total_grounded
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
    avg_groundedness = sum(groundedness_scores) / len(groundedness_scores) if groundedness_scores else 0.0

    return {
        "mode": mode,
        "queries_evaluated": total_grounded,
        "recall@1": round(recall_at_1, 4),
        "recall@2": round(recall_at_2, 4),
        "recall@4": round(recall_at_4, 4),
        "mrr": round(mrr, 4),
        "avg_latency_ms": round(avg_latency, 2),
        "avg_groundedness": round(avg_groundedness, 4),
    }


def evaluate_ungrounded_refusal() -> Dict[str, Any]:
    """
    Evaluates system refusal rate on out-of-domain and adversarial questions.
    """
    ungrounded_queries = [item for item in EVALUATION_DATASET if not item["is_grounded"]]
    total_ungrounded = len(ungrounded_queries)
    refusals = 0

    for item in ungrounded_queries:
        query = item["query"]
        results = search_knowledge_base(query=query, top_k=4, mode="hybrid")
        # Apply LLM response generation with guardrail
        resp = generate_llm_response(query=query, context_chunks=results)
        if resp["grounded"] is False and "Information not found" in resp["answer"]:
            refusals += 1

    refusal_rate = refusals / total_ungrounded if total_ungrounded > 0 else 1.0
    return {
        "total_adversarial_queries": total_ungrounded,
        "correctly_refused": refusals,
        "refusal_rate": round(refusal_rate, 4),
    }


# Pytest automated test cases ensuring CI/CD regression protection
def test_hybrid_rag_benchmark_metrics():
    metrics = evaluate_retrieval(mode="hybrid")
    # Strict quality thresholds mandated by Directive 6
    assert metrics["recall@4"] >= 0.85, f"Recall@4 below threshold: {metrics['recall@4']}"
    assert metrics["mrr"] >= 0.75, f"MRR below threshold: {metrics['mrr']}"
    assert metrics["avg_groundedness"] >= 0.50, f"Groundedness below threshold: {metrics['avg_groundedness']}"


def test_adversarial_refusal_rate():
    refusal_metrics = evaluate_ungrounded_refusal()
    # 100% refusal required for out-of-domain / hallucination prevention
    assert refusal_metrics["refusal_rate"] == 1.0, f"Hallucination leak detected: {refusal_metrics}"


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print(" UNIMIND AI — EMPIRICAL RAG BENCHMARK & EVALUATION HARNESS")
    print("=" * 70)

    modes = ["bm25", "dense", "hybrid"]
    results = []
    for m in modes:
        print(f"[*] Benchmarking Mode: {m.upper()}...")
        metrics = evaluate_retrieval(mode=m)
        results.append(metrics)

    print("\n--- RETRIEVAL QUALITY COMPARISON TABLE ---")
    header = f"{'Mode':<10} | {'Recall@1':<10} | {'Recall@2':<10} | {'Recall@4':<10} | {'MRR':<8} | {'Avg Latency':<14} | {'Groundedness'}"
    print(header)
    print("-" * len(header))
    for r in results:
        print(f"{r['mode'].upper():<10} | {r['recall@1']:<10.2%} | {r['recall@2']:<10.2%} | {r['recall@4']:<10.2%} | {r['mrr']:<8.4f} | {r['avg_latency_ms']:<10.2f} ms | {r['avg_groundedness']:<12.4f}")

    refusals = evaluate_ungrounded_refusal()
    print("\n--- ADVERSARIAL & OUT-OF-DOMAIN REFUSAL HARNESS ---")
    print(f"Total Out-of-Domain Queries : {refusals['total_adversarial_queries']}")
    print(f"Correctly Refused (Zero-Hallucination) : {refusals['correctly_refused']}")
    print(f"Unsupported-Answer Refusal Rate : {refusals['refusal_rate']:.2%}")
    print("=" * 70 + "\n")
