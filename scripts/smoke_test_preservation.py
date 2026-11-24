import sys
import time
from pathlib import Path

# Setup paths
backend_dir = Path("backend").resolve()
root_dir = Path(".").resolve()
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(root_dir))

import numpy as np
from fastapi.testclient import TestClient
from app.main import app
from ml.models.anomaly_detector import AegisOpsAnomalyDetector

def run_smoke_test():
    print("=" * 70)
    print("            STAGE F FINAL APPLICATION PRESERVATION SMOKE TEST")
    print("=" * 70)
    client = TestClient(app)

    results = {}

    # 1. Backend Startup & Health
    r1 = client.get("/")
    r2 = client.get("/health")
    assert r1.status_code == 200, f"Root failed: {r1.status_code}"
    assert r2.status_code == 200, f"Health failed: {r2.status_code}"
    assert r2.json().get("database") == "connected"
    results["Backend Startup & Health"] = "PASS (HTTP 200, database connected)"
    print("[PASS] 1. Backend Starts Successfully & Readiness is OK")

    # 2. Frontend Assets Verification
    dist_html = Path("frontend/dist/index.html")
    assert dist_html.exists(), "frontend/dist/index.html missing"
    html_content = dist_html.read_text(encoding="utf-8")
    assert '<div id="root">' in html_content or 'id="root"' in html_content
    results["Frontend Production Assets"] = f"PASS (dist/index.html exists, {len(html_content)} bytes)"
    print("[PASS] 2. Frontend Assets Load & Render Valid Root Container")

    # 3. Authentication
    login_res = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "password123"},
    )
    if login_res.status_code != 200:
        # Fallback to demo default
        login_res = client.post(
            "/api/v1/auth/login",
            data={"username": "admin", "password": "admin123"},
        )
    assert login_res.status_code == 200, f"Login failed: {login_res.status_code} {login_res.text}"
    token = login_res.json().get("access_token")
    assert token, "No access token in response"
    headers = {"Authorization": f"Bearer {token}"}
    results["Authentication"] = "PASS (JWT token successfully issued for admin)"
    print("[PASS] 3. Authentication Works (JWT Token Acquired)")

    # 4. Tenant-Aware Agent Execution
    agent_res = client.post(
        "/api/v1/agent/run",
        json={"prompt": "Check my examination attendance requirement"},
        headers=headers,
    )
    assert agent_res.status_code == 200, f"Agent failed: {agent_res.status_code} {agent_res.text}"
    agent_data = agent_res.json()
    assert "agent_response" in agent_data
    results["Tenant-Aware Agent"] = f"PASS (Tool: {agent_data.get('tool_used')})"
    print(f"[PASS] 4. Tenant-Aware Agent Execution Works (Tool: {agent_data.get('tool_used')})")

    # 5. Knowledge Retrieval
    rag_res = client.post(
        "/api/v1/rag/query",
        json={"query": "What is the minimum attendance requirement for examinations?"},
        headers=headers,
    )
    assert rag_res.status_code == 200, f"RAG query failed: {rag_res.status_code}"
    rag_data = rag_res.json()
    chunks = rag_data.get("results", [])
    assert len(chunks) > 0, f"No chunks found in RAG response: {rag_data}"
    top_chunk = chunks[0]
    meta = top_chunk.get("metadata", {})
    results["Knowledge Retrieval"] = f"PASS ({len(chunks)} chunks retrieved, Source: {meta.get('source')})"
    print(f"[PASS] 5. Knowledge Retrieval Works ({len(chunks)} chunks retrieved from {meta.get('source')})")

    # 6. Ticket Creation
    ticket_res = client.post(
        "/api/v1/tickets",
        json={
            "title": "Smoke Test IT Ticket",
            "description": "Preservation verification automated smoke test ticket.",
            "category": "it",
            "priority": "LOW",
        },
        headers=headers,
    )
    assert ticket_res.status_code == 201, f"Ticket creation failed: {ticket_res.status_code} {ticket_res.text}"
    ticket_data = ticket_res.json()
    assert ticket_data.get("ticket_code").startswith("TICK-1-"), f"Unexpected ticket code: {ticket_data}"
    results["Ticket Creation"] = f"PASS (Created code: {ticket_data.get('ticket_code')})"
    print(f"[PASS] 6. Ticket Creation Works (Ticket Code: {ticket_data.get('ticket_code')})")

    # 7. AegisOps Dashboard
    aegis_res = client.get("/api/v1/aegisops/services", headers=headers)
    assert aegis_res.status_code == 200, f"AegisOps services failed: {aegis_res.status_code}"
    aegis_data = aegis_res.json()
    results["AegisOps Dashboard Status"] = f"PASS ({len(aegis_data)} services monitored)"
    print(f"[PASS] 7. AegisOps Dashboard Loads ({len(aegis_data)} services monitored)")

    # 8. Anomaly Scoring
    detector = AegisOpsAnomalyDetector()
    normal_vec = np.array([[25.0, 35.0, 400.0, 110.0, 0.0]])
    anom_vec = np.array([[95.0, 92.0, 1200.0, 850.0, 15.0]])
    normal_score, is_norm_anom = detector.predict_anomaly_score(normal_vec)
    anom_score, is_spike_anom = detector.predict_anomaly_score(anom_vec)
    assert not is_norm_anom, f"Normal vector flagged as anomaly: score={normal_score}"
    assert is_spike_anom, f"Spike vector not flagged as anomaly: score={anom_score}"
    results["Anomaly Scoring"] = f"PASS (Normal Score: {normal_score}, Spike Score: {anom_score})"
    print(f"[PASS] 8. Anomaly Scoring Works (Normal: {normal_score} [Anomaly: {is_norm_anom}], Spike: {anom_score} [Anomaly: {is_spike_anom}])")

    print("=" * 70)
    print("                ALL 8 SMOKE TEST CHECKS PASSED")
    print("=" * 70)

if __name__ == "__main__":
    run_smoke_test()
