import os
import sys
import json
import requests
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"

def log_step(name, status, details=None):
    mark = "PASS" if status else "FAIL"
    print(f"[{mark}] {name}")
    if details:
        print(f"       -> {details}")

def run_verification():
    print("=" * 80)
    print("  RUNNING UNIMIND AI + AEGISOPS LIVE E2E VERIFICATION SUITE")
    print(f"  Target Server: {BASE_URL}")
    print("=" * 80)

    results = {}
    
    # --------------------------------------------------------------------------
    # PHASE 1: APPLICATION STARTUP & HEALTH
    # --------------------------------------------------------------------------
    print("\n--- PHASE 1: Application Startup & Health Endpoints ---")
    
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        health_data = r.json()
        status_ok = r.status_code == 200 and health_data.get("status") == "ok" and health_data.get("database") == "connected"
        log_step("Root /health endpoint", status_ok, health_data)
        results["phase1_health"] = status_ok
    except Exception as e:
        log_step("Root /health endpoint", False, str(e))
        results["phase1_health"] = False

    try:
        r = requests.get(f"{BASE_URL}/api/v1/health", timeout=5)
        api_health = r.json()
        status_ok = r.status_code == 200 and api_health.get("status") == "ok" and api_health.get("database") == "connected"
        log_step("API v1 /health endpoint", status_ok, api_health)
        results["phase1_api_health"] = status_ok
    except Exception as e:
        log_step("API v1 /health endpoint", False, str(e))
        results["phase1_api_health"] = False

    # --------------------------------------------------------------------------
    # PHASE 2: UNIMIND AI LIVE WORKFLOW
    # --------------------------------------------------------------------------
    print("\n--- PHASE 2: UniMind AI Live Workflow ---")
    
    # 1. Admin Login
    admin_token = None
    try:
        r = requests.post(f"{BASE_URL}/api/v1/auth/login", data={"username": "admin", "password": "admin123"}, timeout=5)
        if r.status_code == 200:
            token_data = r.json()
            admin_token = token_data.get("access_token")
            log_step("Admin Login (admin / admin123)", True, f"Token received: {admin_token[:15]}...")
            results["admin_login"] = True
        else:
            log_step("Admin Login", False, f"Status: {r.status_code}, Body: {r.text}")
            results["admin_login"] = False
    except Exception as e:
        log_step("Admin Login", False, str(e))
        results["admin_login"] = False

    # 2. Student Login
    student_token = None
    try:
        r = requests.post(f"{BASE_URL}/api/v1/auth/login", data={"username": "student", "password": "student123"}, timeout=5)
        if r.status_code == 200:
            token_data = r.json()
            student_token = token_data.get("access_token")
            log_step("Student Login (student / student123)", True, f"Token received: {student_token[:15]}...")
            results["student_login"] = True
        else:
            log_step("Student Login", False, f"Status: {r.status_code}, Body: {r.text}")
            results["student_login"] = False
    except Exception as e:
        log_step("Student Login", False, str(e))
        results["student_login"] = False

    admin_headers = {"Authorization": f"Bearer {admin_token}"} if admin_token else {}
    student_headers = {"Authorization": f"Bearer {student_token}"} if student_token else {}

    # 3. RBAC Enforcement: Student cannot upload documents
    pdf_path = Path("data/sample_institutional_policy.pdf")
    try:
        with open(pdf_path, "rb") as f:
            r = requests.post(
                f"{BASE_URL}/api/v1/documents/upload",
                headers=student_headers,
                data={"title": "Unauthorized Student Doc", "category": "policies"},
                files={"file": ("unauthorized.pdf", f, "application/pdf")},
                timeout=5,
            )
        student_blocked = r.status_code == 403
        log_step("RBAC Check: Student document upload blocked (HTTP 403)", student_blocked, f"Status: {r.status_code}")
        results["student_upload_blocked"] = student_blocked
    except Exception as e:
        log_step("RBAC Check: Student document upload blocked", False, str(e))
        results["student_upload_blocked"] = False

    # 4. Admin Uploads Institutional PDF
    uploaded_doc_id = None
    try:
        with open(pdf_path, "rb") as f:
            r = requests.post(
                f"{BASE_URL}/api/v1/documents/upload",
                headers=admin_headers,
                data={"title": "Institutional Academic Regulations 2026", "category": "policies"},
                files={"file": ("sample_institutional_policy.pdf", f, "application/pdf")},
                timeout=10,
            )
        if r.status_code in [200, 201]:
            doc_data = r.json()
            uploaded_doc_id = doc_data.get("id")
            log_step("Admin Upload Institutional PDF", True, f"Doc ID: {uploaded_doc_id}, Title: {doc_data.get('title')}")
            results["admin_upload_pdf"] = True
        else:
            log_step("Admin Upload Institutional PDF", False, f"Status: {r.status_code}, Body: {r.text}")
            results["admin_upload_pdf"] = False
    except Exception as e:
        log_step("Admin Upload Institutional PDF", False, str(e))
        results["admin_upload_pdf"] = False

    # 5. Ingestion and ChromaDB Chunk Persistence
    if uploaded_doc_id:
        try:
            r = requests.post(
                f"{BASE_URL}/api/v1/rag/ingest/{uploaded_doc_id}",
                headers=admin_headers,
                timeout=60,
            )
            if r.status_code == 200:
                ingest_res = r.json()
                chunks_indexed = ingest_res.get("chunks_indexed", 0)
                status_ok = chunks_indexed > 0 and ingest_res.get("title") is not None
                log_step("Document Ingestion & ChromaDB Vector Indexing", status_ok, f"Chunks: {chunks_indexed}, Title: {ingest_res.get('title')}")
                results["rag_ingestion"] = status_ok
            else:
                log_step("Document Ingestion & ChromaDB Vector Indexing", False, f"Status: {r.status_code}, Body: {r.text}")
                results["rag_ingestion"] = False
        except Exception as e:
            log_step("Document Ingestion & ChromaDB Vector Indexing", False, str(e))
            results["rag_ingestion"] = False
    else:
        results["rag_ingestion"] = False

    # 6. RAG Query: Answer Present in Uploaded PDF
    present_query = "What is the minimum attendance required for semester examinations?"
    try:
        r = requests.post(
            f"{BASE_URL}/api/v1/rag/query",
            headers=admin_headers,
            json={"query": present_query, "top_k": 3, "mode": "hybrid", "use_expansion": True},
            timeout=15,
        )
        if r.status_code == 200:
            query_res = r.json()
            matched_chunks = query_res.get("results", [])
            has_relevant = any("75 percent" in c.get("text", "") or "75%" in c.get("text", "") or "attendance" in c.get("text", "").lower() for c in matched_chunks)
            top_score = matched_chunks[0].get("similarity_score", 0) if matched_chunks else 0
            log_step(f"RAG Hybrid Search for Grounded Content ('{present_query}')", has_relevant, f"Found {len(matched_chunks)} chunks; Top score: {top_score:.3f}")
            results["rag_grounded_search"] = has_relevant
        else:
            log_step("RAG Hybrid Search", False, f"Status: {r.status_code}, Body: {r.text}")
            results["rag_grounded_search"] = False
    except Exception as e:
        log_step("RAG Hybrid Search", False, str(e))
        results["rag_grounded_search"] = False

    # 7. Student Assistant Chat: Grounded Answer & Citations
    try:
        r = requests.post(
            f"{BASE_URL}/api/v1/assistant/chat",
            headers=admin_headers,
            json={"message": present_query, "category_filter": "policies"},
            timeout=20,
        )
        if r.status_code == 200:
            chat_res = r.json()
            is_grounded = chat_res.get("grounded", False)
            sources = chat_res.get("sources", [])
            bot_answer = chat_res.get("bot_answer", "").lower()
            has_attendance_info = "75" in bot_answer or "attendance" in bot_answer
            status_ok = has_attendance_info and is_grounded and len(sources) > 0
            log_step("Assistant Grounded Answer & Citations Verification", status_ok, f"Grounded: {is_grounded}, Citations/Sources: {len(sources)}, Text: '{chat_res.get('bot_answer', '')[:70]}...'")
            results["assistant_grounded_answer"] = status_ok
        else:
            log_step("Assistant Grounded Answer", False, f"Status: {r.status_code}, Body: {r.text}")
            results["assistant_grounded_answer"] = False
    except Exception as e:
        log_step("Assistant Grounded Answer", False, str(e))
        results["assistant_grounded_answer"] = False

    # 8. Student Assistant Chat: Absent Information (Refusal / Non-hallucination)
    absent_query = "What is the university policy on interstellar warp drive research?"
    try:
        r = requests.post(
            f"{BASE_URL}/api/v1/assistant/chat",
            headers=admin_headers,
            json={"message": absent_query},
            timeout=15,
        )
        if r.status_code == 200:
            absent_res = r.json()
            is_grounded = absent_res.get("grounded", False)
            bot_answer = absent_res.get("bot_answer", "").lower()
            refusal_observed = not is_grounded or any(w in bot_answer for w in ["could not find", "unable to find", "no information", "cannot find", "not available", "not found"])
            log_step(f"Assistant Refusal on Absent Info ('{absent_query}')", refusal_observed, f"Grounded: {is_grounded}, Response: '{absent_res.get('bot_answer', '')[:80]}...'")
            results["assistant_refusal_nonhallucination"] = refusal_observed
        else:
            log_step("Assistant Refusal", False, f"Status: {r.status_code}, Body: {r.text}")
            results["assistant_refusal_nonhallucination"] = False
    except Exception as e:
        log_step("Assistant Refusal", False, str(e))
        results["assistant_refusal_nonhallucination"] = False

    # --------------------------------------------------------------------------
    # PHASE 3: AEGISOPS LIVE VERIFICATION
    # --------------------------------------------------------------------------
    print("\n--- PHASE 3: AegisOps Live Verification ---")

    # 1. Services Inspection
    try:
        r = requests.get(f"{BASE_URL}/api/v1/aegisops/services", headers=admin_headers, timeout=5)
        services = r.json()
        expected = {"exam service", "lms", "student portal", "library service"}
        found = {s.get("name", "").lower() for s in services}
        has_all_services = expected.issubset(found)
        log_step("Inspect All 4 Campus Demo Services", has_all_services, f"Found: {found}")
        results["services_inspection"] = has_all_services
    except Exception as e:
        log_step("Inspect Demo Services", False, str(e))
        results["services_inspection"] = False

    # 2. Inject Chaos Scenario A: CPU Saturation on exam_service
    chaos_incident_id = None
    try:
        r = requests.post(
            f"{BASE_URL}/api/v1/aegisops/chaos/inject",
            headers=admin_headers,
            json={"service_name": "exam_service", "scenario": "cpu", "severity": "CRITICAL", "duration_seconds": 60},
            timeout=10,
        )
        if r.status_code == 200:
            chaos_res = r.json()
            incident_info = chaos_res.get("incident")
            chaos_incident_id = incident_info.get("id") if incident_info else None
            anomaly_score = chaos_res.get("anomaly_score", 0)
            log_step("Inject Chaos CPU Saturation (CRITICAL)", True, f"Incident ID: {chaos_incident_id}, Anomaly Score: {anomaly_score:.3f}")
            results["chaos_injection"] = True
        else:
            log_step("Inject Chaos CPU Saturation", False, f"Status: {r.status_code}, Body: {r.text}")
            results["chaos_injection"] = False
    except Exception as e:
        log_step("Inject Chaos CPU Saturation", False, str(e))
        results["chaos_injection"] = False

    # 3. Telemetry Reflection & Synthetic Tag Verification
    try:
        r = requests.get(f"{BASE_URL}/api/v1/aegisops/metrics", headers=admin_headers, timeout=5)
        all_metrics = r.json()
        exam_metrics = next((m for m in all_metrics if "exam" in m.get("service", "").lower()), None)
        cpu_val = int(exam_metrics.get("cpu", "0%").replace("%", "")) if exam_metrics else 0
        cpu_elevated = cpu_val > 70
        synthetic_flagged = exam_metrics and exam_metrics.get("is_synthetic") is True
        status_ok = cpu_elevated and synthetic_flagged
        log_step("Verify Telemetry Reflection & Synthetic Tagging", status_ok, f"CPU: {cpu_val}%, Synthetic: {exam_metrics.get('is_synthetic') if exam_metrics else None}")
        results["telemetry_reflection"] = status_ok
    except Exception as e:
        log_step("Verify Telemetry Reflection", False, str(e))
        results["telemetry_reflection"] = False

    # 4. Anomaly Detection & Incident Deduplication Check
    try:
        r = requests.post(
            f"{BASE_URL}/api/v1/aegisops/chaos/inject",
            headers=admin_headers,
            json={"service_name": "exam_service", "scenario": "cpu", "severity": "HIGH", "duration_seconds": 60},
            timeout=10,
        )
        if r.status_code == 200:
            chaos_res2 = r.json()
            incident_id2 = chaos_res2.get("incident", {}).get("id")
            dedup_ok = incident_id2 == chaos_incident_id
            log_step("Incident Deduplication on Active Failure", dedup_ok, f"Original ID: {chaos_incident_id}, Deduplicated ID: {incident_id2}")
            results["incident_deduplication"] = dedup_ok
        else:
            log_step("Incident Deduplication", False, f"Status: {r.status_code}")
            results["incident_deduplication"] = False
    except Exception as e:
        log_step("Incident Deduplication", False, str(e))
        results["incident_deduplication"] = False

    # 5. AI Diagnosis & Runbook Evidence Retrieval
    try:
        r = requests.post(
            f"{BASE_URL}/api/v1/aegisops/diagnose/exam_service",
            headers=admin_headers,
            timeout=15,
        )
        if r.status_code == 200:
            diag_res = r.json()
            root_cause = diag_res.get("suspected_root_cause", "")
            has_runbook = "runbook" in diag_res.get("matched_runbook_title", "").lower() or diag_res.get("confidence_score", 0) > 0.5
            has_cpu_mention = any(w in root_cause.lower() for w in ["cpu", "saturation", "throttling", "compute"])
            status_ok = has_cpu_mention and has_runbook
            log_step("AI Root Cause Analysis & Runbook Evidence", status_ok, f"Runbook: '{diag_res.get('matched_runbook_title')}', Conf: {diag_res.get('confidence_score')}")
            results["ai_diagnosis_runbook"] = status_ok
        else:
            log_step("AI Root Cause Analysis", False, f"Status: {r.status_code}, Body: {r.text}")
            results["ai_diagnosis_runbook"] = False
    except Exception as e:
        log_step("AI Root Cause Analysis", False, str(e))
        results["ai_diagnosis_runbook"] = False

    # 6. Unauthorized Student Remediation Block (HTTP 403)
    try:
        r = requests.post(
            f"{BASE_URL}/api/v1/aegisops/remediate/approve",
            headers=student_headers,
            json={"incident_id": chaos_incident_id, "action": "SCALE_DEPLOYMENT"},
            timeout=5,
        )
        student_blocked = r.status_code == 403
        log_step("RBAC Check: Unauthorized student remediation blocked (HTTP 403)", student_blocked, f"Status: {r.status_code}")
        results["student_remediation_blocked"] = student_blocked
    except Exception as e:
        log_step("RBAC Check: Student remediation block", False, str(e))
        results["student_remediation_blocked"] = False

    # 7. Remediation Rejection Workflow
    try:
        r = requests.post(
            f"{BASE_URL}/api/v1/aegisops/remediate/reject",
            headers=admin_headers,
            json={"incident_id": chaos_incident_id, "reason": "Testing admin rejection protocol"},
            timeout=5,
        )
        if r.status_code == 200:
            rej_data = r.json()
            status_open = rej_data.get("status") == "OPEN"
            log_step("Admin Rejection Workflow (Transition to OPEN)", status_open, f"Status: {rej_data.get('status')}")
            results["remediation_rejection"] = status_open
        else:
            log_step("Admin Rejection Workflow", False, f"Status: {r.status_code}, Body: {r.text}")
            results["remediation_rejection"] = False
    except Exception as e:
        log_step("Admin Rejection Workflow", False, str(e))
        results["remediation_rejection"] = False

    # 8. Restore Service Telemetry to Nominal Baseline
    try:
        r = requests.post(
            f"{BASE_URL}/api/v1/aegisops/chaos/restore",
            headers=admin_headers,
            json={"service_name": "exam_service"},
            timeout=5,
        )
        restored = r.status_code == 200 and r.json().get("status") == "HEALTHY"
        log_step("Restore Service Telemetry Baseline", restored, f"Status: {r.json().get('status')}")
        results["chaos_restore"] = restored
    except Exception as e:
        log_step("Restore Service Telemetry", False, str(e))
        results["chaos_restore"] = False

    # 9. Admin Approves Controlled Remediation
    try:
        r = requests.post(
            f"{BASE_URL}/api/v1/aegisops/remediate/approve",
            headers=admin_headers,
            json={"incident_id": chaos_incident_id, "action": "SCALE_DEPLOYMENT", "target_replicas": 4},
            timeout=10,
        )
        if r.status_code == 200:
            rem_res = r.json()
            is_resolved = rem_res.get("status") == "RESOLVED"
            verified_rec = rem_res.get("verified_recovery") is True
            status_ok = is_resolved and verified_rec
            log_step("Admin Approve Controlled Remediation & Post-Verification", status_ok, f"Status: {rem_res.get('status')}, Verified: {verified_rec}")
            results["remediation_approval_resolved"] = status_ok
        else:
            log_step("Admin Approve Controlled Remediation", False, f"Status: {r.status_code}, Body: {r.text}")
            results["remediation_approval_resolved"] = False
    except Exception as e:
        log_step("Admin Approve Controlled Remediation", False, str(e))
        results["remediation_approval_resolved"] = False

    # 10. Audit Log & Incident Final State in Database
    try:
        r = requests.get(f"{BASE_URL}/api/v1/incidents", headers=admin_headers, timeout=5)
        incidents = r.json()
        inc = next((i for i in incidents if i.get("id") == chaos_incident_id), None)
        is_final_resolved = inc is not None and inc.get("status") == "RESOLVED"
        log_step("Database Independent Verification: Incident RESOLVED", is_final_resolved, f"Incident {chaos_incident_id} final status: {inc.get('status') if inc else 'not found'}")
        results["db_incident_resolved"] = is_final_resolved
    except Exception as e:
        log_step("Database Incident State Verification", False, str(e))
        results["db_incident_resolved"] = False

    # --------------------------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------------------------
    print("\n" + "=" * 80)
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    print(f"  LIVE VERIFICATION SUITE RESULTS: {passed}/{total} Passed ({(passed/total)*100:.1f}%)")
    print("=" * 80)
    
    with open("data/live_verification_results.json", "w") as f:
        json.dump(results, f, indent=2)

    return passed == total

if __name__ == "__main__":
    success = run_verification()
    sys.exit(0 if success else 1)
