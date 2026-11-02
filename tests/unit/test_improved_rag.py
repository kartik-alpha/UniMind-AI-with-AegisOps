import pytest
from rag.ingestion.chunker import chunk_text
from rag.retrieval.bm25 import BM25Index, tokenize
from rag.retrieval.query_expander import expand_query
from rag.retrieval.reranker import reciprocal_rank_fusion, rerank_and_filter
from ai.llm.llm_client import calculate_groundedness_score, generate_llm_response


def test_sentence_aware_chunker():
    sample_policy = (
        "# SECTION 1: ATTENDANCE REGULATIONS\n"
        "All undergraduate students must maintain a minimum of 75% attendance in every course. "
        "Students falling below 75% will not be permitted to appear for end-semester examinations. "
        "A 10% condonation may be granted by the Dean on medical grounds with proper documentation.\n\n"
        "## SECTION 2: HOSTEL RULES\n"
        "Hostel gates will close promptly at 10:00 PM for all residents. "
        "Late entry without prior written permission from the Warden is strictly prohibited."
    )
    chunks = chunk_text(sample_policy, chunk_size=40, chunk_overlap=10, metadata={"source": "handbook.pdf"})
    assert len(chunks) >= 2
    for c in chunks:
        assert "chunk_id" in c
        assert "text" in c
        assert "metadata" in c
        assert c["metadata"]["total_chunks"] == len(chunks)
        assert "word_count" in c["metadata"]

    # Check section headings captured
    headings = [c["metadata"].get("section_heading") for c in chunks if c["metadata"].get("section_heading")]
    assert any("ATTENDANCE REGULATIONS" in h for h in headings)


def test_bm25_lexical_index():
    index = BM25Index()
    docs = [
        {
            "chunk_id": "c1",
            "text": "The minimum attendance required to appear for final semester examinations is 75%.",
            "metadata": {"doc_id": 1, "category": "attendance"},
        },
        {
            "chunk_id": "c2",
            "text": "Hostel gates close at 10:00 PM every night. Strict disciplinary action follows late arrival.",
            "metadata": {"doc_id": 2, "category": "hostel"},
        },
        {
            "chunk_id": "c3",
            "text": "Students can apply for examination grade re-evaluation within 7 days of result declaration.",
            "metadata": {"doc_id": 3, "category": "examinations"},
        },
    ]
    index.add_chunks(docs)
    assert index.total_docs == 3

    # Exact token / percentage match
    results = index.search("75% attendance", top_k=2)
    assert len(results) > 0
    assert results[0]["chunk_id"] == "c1"
    assert "75%" in results[0]["matched_keywords"] or "attendance" in results[0]["matched_keywords"]

    # Curfew match
    curfew_res = index.search("10:00 PM hostel gate", top_k=2)
    assert len(curfew_res) > 0
    assert curfew_res[0]["chunk_id"] == "c2"

    # Category filter
    filtered = index.search("policy", top_k=5, category_filter="hostel")
    for r in filtered:
        assert r["metadata"]["category"] == "hostel"


def test_query_expansion():
    exp = expand_query("What is the attendance requirement?")
    assert "attendance" in exp["normalized_query"].lower()
    assert len(exp["expanded_terms"]) > 0
    assert any("75%" in t or "minimum" in t for t in exp["expanded_terms"])
    assert len(exp["expanded_query"]) > len(exp["normalized_query"])


def test_reciprocal_rank_fusion_and_reranking():
    dense_results = [
        {"chunk_id": "c1", "text": "Minimum 75% attendance policy for semester exams.", "similarity_score": 0.92, "metadata": {"section_heading": "Attendance"}},
        {"chunk_id": "c2", "text": "Hostel in-time is 10:00 PM.", "similarity_score": 0.40, "metadata": {}},
    ]
    bm25_results = [
        {"chunk_id": "c1", "text": "Minimum 75% attendance policy for semester exams.", "bm25_score": 3.8, "matched_keywords": ["75%", "attendance"]},
        {"chunk_id": "c3", "text": "Dean approval for attendance shortage.", "bm25_score": 1.2, "matched_keywords": ["attendance"]},
    ]

    fused = reciprocal_rank_fusion(dense_results, bm25_results, k=60)
    assert len(fused) == 3
    # c1 is rank 1 in both dense and BM25, so it must have highest RRF score
    c1_item = next(item for item in fused if item["chunk_id"] == "c1")
    assert c1_item["dense_rank"] == 1
    assert c1_item["bm25_rank"] == 1

    ranked = rerank_and_filter(fused, query="75% attendance", top_k=2)
    assert len(ranked) >= 1
    assert ranked[0]["chunk_id"] == "c1"
    assert ranked[0]["similarity_score"] == 0.92


def test_groundedness_confidence_and_hallucination_prevention():
    context_chunks = [
        {
            "chunk_id": "chunk-101",
            "text": "Regulation 4: Students must maintain at least 75% attendance to sit for examinations.",
            "similarity_score": 0.88,
            "metadata": {"title": "Academic Regulations 2026", "category": "attendance", "section_heading": "Attendance Criteria"},
        }
    ]

    # Grounded query
    score = calculate_groundedness_score("What is the 75% attendance requirement?", context_chunks)
    assert score >= 0.50

    response = generate_llm_response("What is the attendance requirement?", context_chunks)
    assert response["grounded"] is True
    assert "75%" in response["answer"]
    assert len(response["sources"]) == 1
    assert response["sources"][0]["section_heading"] == "Attendance Criteria"

    # Completely ungrounded query (must NOT hallucinate)
    ungrounded_chunks = []
    ungrounded_resp = generate_llm_response("Can I park a spaceship on the university roof?", ungrounded_chunks)
    assert ungrounded_resp["grounded"] is False
    assert ungrounded_resp["answer"] == "Information not found in the university knowledge base."
    assert len(ungrounded_resp["sources"]) == 0

