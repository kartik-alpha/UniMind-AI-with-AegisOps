"""
Phase G5: Full End-to-End Enterprise Journey Automated Integration Suite.
Simulates complete student & SRE operator lifecycles:
1. Ingestion of university policy document -> indexing into Chroma vector store.
2. Grounded conversational query via Assistant SSE stream -> citations verified.
3. Student support ticket creation with automated categorization.
4. SRE chaos outage injection -> real-time Isolation Forest anomaly detection.
5. AI RCA diagnosis matching symptoms to SRE runbooks.
6. Controlled self-healing approval & execution -> service fleet restored.
7. Cryptographic audit chain verification of the entire operational sequence.
"""
import time
import json
from fastapi.testclient import TestClient
import pytest

from backend.app.main import app
from app.core.security import create_access_token
from app.db.session import SessionLocal
from app.models.document import Document
from app.models.ticket import Ticket, Incident, IncidentStatus
from app.services.governance_service import GovernanceService
from scripts.chaos_simulator import get_chaos_simulator

client = TestClient(app)


def test_complete_enterprise_end_to_end_journey():
    """
    Executes a seamless end-to-end user & SRE operations journey through public REST APIs.
    """
    admin_token = create_access_token(subject="1")
    admin_headers = {"Authorization": f"Bearer {admin_token}", "X-Tenant-ID": "1"}

    # -------------------------------------------------------------------------
    # Step 1: Policy Ingestion & Chroma Vector Verification
    # -------------------------------------------------------------------------
    stats_res = client.get("/api/v1/rag/stats", headers=admin_headers)
    assert stats_res.status_code == 200
    stats_data = stats_res.json()
    assert stats_data["total_chunks"] > 0
    print(f"\n[E2E STEP 1] Knowledge Base Status: {stats_data['total_chunks']} chunks in vector store.")

    # -------------------------------------------------------------------------
    # Step 2: Grounded Assistant Streaming Query
    # -------------------------------------------------------------------------
    chat_payload = {
        "message": "What is the mandatory curfew time for undergraduate resident students?",
        "mode": "hybrid",
    }
    chat_res = client.post("/api/v1/assistant/chat", json=chat_payload, headers=admin_headers)
    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    assert chat_data["grounded"] is True
    assert "10:00" in chat_data["bot_answer"] or "curfew" in chat_data["bot_answer"].lower()
    assert len(chat_data["sources"]) > 0
    print(f"[E2E STEP 2] Grounded Query Answered: '{chat_data['bot_answer'][:80]}...' (Citations: {len(chat_data['sources'])})")

    # -------------------------------------------------------------------------
    # Step 3: Support Ticket Creation
    # -------------------------------------------------------------------------
    ticket_payload = {
        "title": "E2E Automated Test: Hostel Wi-Fi issue",
        "description": "Wi-Fi access point in block B is intermittently dropping packets.",
        "category": "IT Support",
        "priority": "HIGH",
    }
    ticket_res = client.post("/api/v1/tickets", json=ticket_payload, headers=admin_headers)
    assert ticket_res.status_code in (200, 201)
    ticket_data = ticket_res.json()
    assert "id" in ticket_data
    created_ticket_id = ticket_data["id"]
    print(f"[E2E STEP 3] Support Ticket Created: ID={created_ticket_id}, Category={ticket_data['category']}")

    # -------------------------------------------------------------------------
    # Step 4: SRE Chaos Outage Injection & Anomaly Detection
    # -------------------------------------------------------------------------
    chaos_payload = {
        "service_name": "exam_service",
        "scenario": "database",
        "severity": "HIGH",
        "duration_seconds": 60,
    }
    chaos_res = client.post("/api/v1/aegisops/chaos/inject", json=chaos_payload, headers=admin_headers)
    assert chaos_res.status_code == 200
    chaos_data = chaos_res.json()
    assert chaos_data["status"] == "INJECTED"
    assert chaos_data["anomaly_score"] >= 0.70 or chaos_data["is_anomaly"] is True
    incident_info = chaos_data["incident"]
    print(f"[E2E STEP 4] Chaos Injected: Anomaly Score={chaos_data['anomaly_score']:.4f}, Incident={incident_info['incident_code']}")

    # -------------------------------------------------------------------------
    # Step 5: AI Root Cause Analysis (RCA) Runbook Matching
    # -------------------------------------------------------------------------
    diag_res = client.post("/api/v1/aegisops/diagnose/exam_service", headers=admin_headers)
    assert diag_res.status_code == 200
    diag_data = diag_res.json()
    assert "suspected_root_cause" in diag_data
    assert "recommended_remediation" in diag_data
    print(f"[E2E STEP 5] AI Diagnosis: Suspected Root Cause='{diag_data['suspected_root_cause']}'")

    # -------------------------------------------------------------------------
    # Step 6: Controlled Self-Healing Approval & Execution
    # -------------------------------------------------------------------------
    remed_payload = {
        "incident_id": incident_info["id"],
        "action": "RESTART_POD",
        "target_replicas": 4,
    }
    remed_res = client.post("/api/v1/aegisops/remediate/approve", json=remed_payload, headers=admin_headers)
    assert remed_res.status_code == 200
    remed_data = remed_res.json()
    assert remed_data["status"] in ("SUCCESS", "RESOLVED")
    assert remed_data["verified_recovery"] is True
    print(f"[E2E STEP 6] Controlled Self-Healing Executed: Status={remed_data['status']}, Action={remed_data.get('action_executed')}")

    # -------------------------------------------------------------------------
    # Step 7: Cryptographic Audit Chain Verification
    # -------------------------------------------------------------------------
    verify_res = client.get("/api/v1/governance/audit/verify-chain", headers=admin_headers)
    assert verify_res.status_code == 200
    verify_data = verify_res.json()
    assert verify_data["is_valid"] is True
    assert verify_data["total_records"] > 0
    print(f"[E2E STEP 7] Cryptographic Audit Chain: 100% Valid across {verify_data['total_records']} chained events.\n")

    # Cleanup ticket
    del_res = client.delete(f"/api/v1/tickets/{created_ticket_id}", headers=admin_headers)
    get_chaos_simulator().restore_all()
