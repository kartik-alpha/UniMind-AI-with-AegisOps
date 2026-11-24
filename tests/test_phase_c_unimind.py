import os
import pytest
from pathlib import Path
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.document import Document
from app.models.ticket import Ticket, TicketPriority, TicketStatus
from app.models.user import User, UserRole
from app.models.audit import AuditLog
from rag.ingestion.extractor import extract_text_from_file, extract_text_and_metadata_from_file, calculate_sha256
from rag.ingestion.chunker import chunk_text
from rag.retrieval.query_expander import expand_query, ENTERPRISE_SYNONYM_MAP
from rag.retrieval.retriever import search_knowledge_base, reindex_tenant_knowledge_base
from app.services.ticket_service import auto_triage_ticket, create_ticket
from app.services.document_service import update_document_approval_status, reindex_document
from ai.agents.unimind_agent import UniMindAgent
from ai.agents.agent_tools import TOOL_REGISTRY, execute_whitelisted_tool


@pytest.fixture(scope="module")
def db_session():
    session = SessionLocal()
    yield session
    session.close()


def test_phase_c_document_ingestion_and_sha256(tmp_path):
    """Test 1: Ingestion parser for TXT and CSV with SHA-256 and metadata extraction."""
    # 1. Create temporary text document
    sample_text = (
        "# Institutional Examination Regulations\n\n"
        "Section 1: Minimum Attendance Mandate.\n"
        "All candidates must achieve a minimum of 75% aggregate attendance.\n\n"
        "Section 2: Medical Leave Policy.\n"
        "Absences up to 10% may be condoned by the Dean upon receipt of medical proof."
    )
    txt_file = tmp_path / "exam_policy.txt"
    txt_file.write_text(sample_text, encoding="utf-8")

    text, meta = extract_text_and_metadata_from_file(str(txt_file))
    assert "Minimum Attendance Mandate" in text
    assert meta["char_count"] > 50
    assert meta["word_count"] > 10
    assert "sha256" in meta and len(meta["sha256"]) == 64
    assert meta["mime_type"] == "text/plain"

    # 2. Create temporary CSV document
    csv_file = tmp_path / "grading_matrix.csv"
    csv_file.write_text("Grade,ScoreRange,GradePoint\nA+,90-100,10.0\nA,80-89,9.0\nB,70-79,8.0\n", encoding="utf-8")

    csv_text, csv_meta = extract_text_and_metadata_from_file(str(csv_file))
    assert "GradePoint" in csv_text
    assert "Row 1: Grade: A+, ScoreRange: 90-100, GradePoint: 10.0" in csv_text
    assert csv_meta["mime_type"] == "text/csv"
    assert len(csv_meta["sha256"]) == 64


def test_phase_c_semantic_chunking_with_hashing():
    """Test 2: Semantic sentence-aware chunking with heading preservation, chunk hashing, and overlap."""
    text = (
        "SECTION 1: HOSTEL REGULATIONS\n\n"
        "The hostel curfew is strictly enforced at 10:00 PM every night. "
        "Residents returning after curfew must present valid gate pass to the warden. "
        "Unauthorized absence results in disciplinary review and parental notification.\n\n"
        "SECTION 2: MESS AND DINING FACILITIES\n\n"
        "Breakfast is served from 07:30 to 09:00 daily. "
        "Dinner concludes at 21:30 sharp without exception. "
        "Special dietary requests must be filed with the mess supervisor 48 hours in advance."
    )
    meta = {"doc_id": 999, "title": "Hostel Code of Conduct", "tenant_id": 1}
    chunks = chunk_text(text, chunk_size=30, chunk_overlap=10, metadata=meta)

    assert len(chunks) >= 2
    for idx, c in enumerate(chunks):
        assert "chunk_id" in c
        c_meta = c["metadata"]
        assert c_meta["doc_id"] == 999
        assert "chunk_hash" in c_meta and len(c_meta["chunk_hash"]) == 16
        assert c_meta["chunk_index"] == idx
        assert c_meta["total_chunks"] == len(chunks)
        assert c_meta["section_heading"] is not None


def test_phase_c_multi_domain_query_expansion():
    """Test 3: Cross-domain query expansion across academic, cloud, and healthcare terminology."""
    # Academic expansion
    exp_acad = expand_query("What is the attendance condonation rule?")
    assert "75% attendance" in exp_acad["expanded_query"] or "minimum attendance" in exp_acad["expanded_query"]

    # Cloud/DevOps expansion
    exp_cloud = expand_query("How is the kubernetes cluster secured?")
    assert any(term in exp_cloud["expanded_query"].lower() for term in ["k8s", "service mesh", "istio", "pods"])

    # Healthcare expansion
    exp_health = expand_query("What is the pediatric morphine dosage in ICU triage?")
    assert any(term in exp_health["expanded_query"].lower() for term in ["controlled substance", "intensive care unit", "critical care", "telemetry", "opioid protocol"])


def test_phase_c_hybrid_retrieval_and_citations(db_session: Session):
    """Test 4: Hybrid RAG retrieval with Reciprocal Rank Fusion ($k=60$) and verifiable citations."""
    results = search_knowledge_base(
        query="What is the minimum attendance requirement for final examinations?",
        top_k=3,
        tenant_id=1,
    )
    assert len(results) > 0
    top = results[0]
    assert "text" in top
    assert "similarity_score" in top
    # Verify structured citation
    assert "citation" in top
    citation = top["citation"]
    assert "source_title" in citation
    assert "section_heading" in citation
    assert "relevance_score" in citation
    assert "citation_text" in top


def test_phase_c_document_workflow_and_reindexing(db_session: Session):
    """Test 5: Document lifecycle workflow (DRAFT -> PENDING_REVIEW -> APPROVED) and re-indexing."""
    doc = db_session.query(Document).filter(Document.tenant_id == 1).first()
    if not doc:
        pytest.skip("No document found in tenant 1 for testing")

    # 1. Update workflow status to PENDING_REVIEW
    updated = update_document_approval_status(
        db=db_session,
        document_id=doc.id,
        approval_status="PENDING_REVIEW",
        approver_username="faculty_reviewer",
        tenant_id=1,
        notes="Awaiting departmental head sign-off",
    )
    assert updated.meta_info["approval_status"] == "PENDING_REVIEW"
    assert updated.meta_info["last_reviewed_by"] == "faculty_reviewer"

    # 2. Approve document
    approved = update_document_approval_status(
        db=db_session,
        document_id=doc.id,
        approval_status="APPROVED",
        approver_username="admin",
        tenant_id=1,
        notes="Curriculum verified",
    )
    assert approved.meta_info["approval_status"] == "APPROVED"
    assert len(approved.meta_info["workflow_history"]) >= 2

    # 3. Re-index document
    reindex_res = reindex_document(db=db_session, document_id=doc.id, tenant_id=1)
    assert reindex_res["status"] == "REINDEXED"
    assert reindex_res["document_id"] == doc.id


def test_phase_c_ticket_auto_triaging():
    """Test 6: Intelligent NLP auto-triaging for tickets."""
    # Critical issue
    crit_triage = auto_triage_ticket(
        title="Emergency ICU ventilator telemetry outage",
        description="Room 402 ICU telemetry monitor dropped connection to centralized nurse station.",
    )
    assert crit_triage["priority"] == TicketPriority.CRITICAL
    assert crit_triage["urgency_score"] >= 0.8
    assert crit_triage["recommended_department"] == "Clinical Informatics"

    # Academic hostel issue
    hostel_triage = auto_triage_ticket(
        title="Hostel room key broken and mess timing inquiry",
        description="Cannot unlock room 204 in Block B. Need duplicate key from warden.",
    )
    assert hostel_triage["priority"] == TicketPriority.HIGH or hostel_triage["priority"] == TicketPriority.MEDIUM
    assert hostel_triage["category"] == "Hostel & Facilities"
    assert hostel_triage["recommended_department"] == "Hostel Administration"

    # Minor inquiry
    minor_triage = auto_triage_ticket(
        title="Minor typo in library catalog search page",
        description="Suggestion to fix cosmetic label spelling on search button.",
    )
    assert minor_triage["priority"] == TicketPriority.LOW
    assert minor_triage["urgency_score"] <= 0.35


def test_phase_c_multi_agent_execution_and_audit(db_session: Session):
    """Test 7: Controlled multi-agent execution loop with whitelisted tools and audit logging."""
    # Verify tool registry
    assert "search_university_documents" in TOOL_REGISTRY
    assert "create_support_ticket" in TOOL_REGISTRY
    assert "check_service_status" in TOOL_REGISTRY
    assert "get_policy_details" in TOOL_REGISTRY

    # Execute whitelisted tool execution wrapper
    exec_res = execute_whitelisted_tool(
        tool_name="check_service_status",
        service_name="exam_service",
    )
    assert exec_res["success"] is True
    assert exec_res["latency_ms"] >= 0
    assert exec_res["result"]["service"] == "Exam Service"

    # Run UniMindAgent with service status prompt
    agent = UniMindAgent(db=db_session, user_id=1, tenant_id=1)
    res = agent.execute_task("What is the current health status and latency of the exam service?")

    assert res["tool_used"] == "check_service_status"
    assert "Service Status for Exam Service" in res["agent_response"]
    assert len(res["execution_trace"]) >= 1
    assert "duration_ms" in res["execution_trace"][0]
    assert res["total_latency_ms"] > 0

    # Verify audit log was recorded in DB
    audit = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "AGENT_EXECUTION", AuditLog.tenant_id == 1)
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert audit is not None
    assert audit.status == "SUCCESS"
    assert "trace" in audit.details
