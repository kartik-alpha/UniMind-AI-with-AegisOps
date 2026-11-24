"""
Stage F Independent Security & Cross-Tenant Isolation Verification Script.
Executes comprehensive negative and positive security tests across all layers.
"""

import sys
import os
import io
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

# Set up paths
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import text
import chromadb

from app.main import app
from app.db.session import engine, SessionLocal
from app.models.organization import (
    Organization,
    OrganizationMembership,
    TenantStatus,
    TenantIndustry,
    TenantRole,
)
from app.models.user import User, UserRole
from app.models.document import Document
from app.models.ticket import Ticket, TicketStatus, Incident, IncidentStatus, IncidentSeverity
from app.models.conversation import Conversation, Message
from app.models.audit import AuditLog
from app.core.security import create_access_token, get_password_hash
from app.adapters.factory import AdapterFactory
from app.adapters.exceptions import TenantIsolationViolationError
from rag.retrieval.retriever import ingest_document_to_rag, search_knowledge_base, get_bm25_index
from rag.vector_store.chroma_service import get_chroma_store


class SecurityVerificationRunner:
    def __init__(self):
        self.client = TestClient(app)
        self.db: Session = SessionLocal()
        self.results = []
        self.platform_admin_token = ""
        self.tenant_a = None
        self.tenant_b = None
        self.user_a_token = ""
        self.admin_a_token = ""
        self.user_b_token = ""
        self.admin_b_token = ""
        self.doc_a = None
        self.doc_b = None
        self.ticket_b = None

    def record(self, test_name: str, passed: bool, evidence: str, limitation: str = "None"):
        status_str = "PASS" if passed else "FAIL"
        self.results.append({
            "test_name": test_name,
            "status": status_str,
            "evidence": evidence,
            "limitation": limitation,
        })
        print(f"[{status_str}] {test_name}")
        if not passed:
            print(f"       EVIDENCE: {evidence}")

    def setup_tenants_and_users(self):
        print("\n--- Setting up Independent Verification Tenants ---")
        # Ensure default organization and schema
        default_org = self.db.query(Organization).filter(Organization.id == 1).first()
        if not default_org:
            from app.db.seed_data import seed_initial_data
            seed_initial_data()

        # Ensure platform admin
        admin = self.db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin = User(
                email="admin@unimind.edu",
                username="admin",
                full_name="Platform Administrator",
                hashed_password=get_password_hash("admin123"),
                role=UserRole.ADMIN,
                tenant_id=1,
                is_active=True,
            )
            self.db.add(admin)
            self.db.commit()
            self.db.refresh(admin)

        self.platform_admin_token = create_access_token(admin.username)

        # Cleanup any pre-existing verification tenants
        for slug in ["alpha-corp-sec", "beta-health-sec"]:
            org = self.db.query(Organization).filter(Organization.slug == slug).first()
            if org:
                self.db.query(Ticket).filter(Ticket.tenant_id == org.id).delete()
                self.db.query(Incident).filter(Incident.tenant_id == org.id).delete()
                self.db.query(Document).filter(Document.tenant_id == org.id).delete()
                self.db.query(AuditLog).filter(AuditLog.tenant_id == org.id).delete()
                self.db.query(OrganizationMembership).filter(OrganizationMembership.tenant_id == org.id).delete()
                self.db.query(User).filter(User.tenant_id == org.id).delete()
                self.db.query(Organization).filter(Organization.id == org.id).delete()
                self.db.commit()

        # Provision Tenant A: Alpha Corp (Technology)
        res_a = self.client.post(
            "/api/v1/platform/tenants",
            json={
                "name": "Alpha Corp",
                "slug": "alpha-corp-sec",
                "industry": "technology",
                "admin_email": "admin@alphacorp.io",
                "admin_username": "alpha_sec_admin",
                "admin_password": "AlphaPassword123!",
                "apply_industry_template": False,
            },
            headers={"Authorization": f"Bearer {self.platform_admin_token}"},
        )
        assert res_a.status_code == 201, f"Failed to provision Tenant A: {res_a.text}"
        self.tenant_a = res_a.json()

        # Provision Tenant B: Beta Health (Healthcare)
        res_b = self.client.post(
            "/api/v1/platform/tenants",
            json={
                "name": "Beta Health",
                "slug": "beta-health-sec",
                "industry": "healthcare",
                "admin_email": "admin@betahealth.org",
                "admin_username": "beta_sec_admin",
                "admin_password": "BetaPassword123!",
                "apply_industry_template": False,
            },
            headers={"Authorization": f"Bearer {self.platform_admin_token}"},
        )
        assert res_b.status_code == 201, f"Failed to provision Tenant B: {res_b.text}"
        self.tenant_b = res_b.json()

        # Ensure fresh, isolated vector collections for verification tenants
        c_clean = chromadb.PersistentClient("data/chroma_db")
        for tid in [self.tenant_a["id"], self.tenant_b["id"]]:
            try:
                c_clean.delete_collection(f"tenant_{tid}_kb")
            except Exception:
                pass

        # Create Regular Users in both tenants
        user_a = User(
            email="developer@alphacorp.io",
            username="alpha_developer",
            full_name="Alpha Developer",
            hashed_password=get_password_hash("DevPass123!"),
            role=UserRole.STUDENT,
            tenant_id=self.tenant_a["id"],
            is_active=True,
        )
        user_b = User(
            email="nurse@betahealth.org",
            username="beta_nurse",
            full_name="Beta Clinical Nurse",
            hashed_password=get_password_hash("NursePass123!"),
            role=UserRole.STUDENT,
            tenant_id=self.tenant_b["id"],
            is_active=True,
        )
        self.db.add_all([user_a, user_b])
        self.db.commit()

        self.user_a_token = create_access_token(user_a.username)
        self.admin_a_token = create_access_token("alpha_sec_admin")
        self.user_b_token = create_access_token(user_b.username)
        self.admin_b_token = create_access_token("beta_sec_admin")

        # Ingest Custom Distinguishable Document for Tenant A
        doc_a_content = (
            "ALPHA CORP CLOUD ARCHITECTURE 2026. "
            "Kubernetes clusters run Istio service mesh on VPC-Alpha. "
            "Microservice ZeroTrust authentication mandates mTLS 1.3 encryption. "
            "Terraform state files are stored in bucket alpha-corp-iac-vault."
        )
        cat_dir_a = Path(f"data/tenants/{self.tenant_a['id']}/documents/security")
        cat_dir_a.mkdir(parents=True, exist_ok=True)
        file_a_path = cat_dir_a / "alpha_cloud_arch.txt"
        file_a_path.write_text(doc_a_content, encoding="utf-8")

        doc_a_rec = Document(
            title="Alpha Cloud Infrastructure Architecture",
            category="security",
            filename="alpha_cloud_arch.txt",
            file_path=str(file_a_path),
            file_size=len(doc_a_content),
            mime_type="text/plain",
            uploader_id=admin.id,
            tenant_id=self.tenant_a["id"],
        )
        self.db.add(doc_a_rec)
        self.db.commit()
        self.db.refresh(doc_a_rec)
        ingest_document_to_rag(db=self.db, document_id=doc_a_rec.id, tenant_id=self.tenant_a["id"])
        self.doc_a = doc_a_rec

        # Ingest Custom Distinguishable Document for Tenant B
        doc_b_content = (
            "BETA HEALTH CLINICAL ICU TRIAGE PROTOCOLS 2026. "
            "Level 1 Critical Triage requires attending physician presence within 45 seconds. "
            "Pediatric Morphine dosage is restricted to 0.05 mg/kg IV with dual RN sign-off. "
            "HIPAA patient health records must never be exported outside Epic EHR sandbox."
        )
        cat_dir_b = Path(f"data/tenants/{self.tenant_b['id']}/documents/clinical_protocols")
        cat_dir_b.mkdir(parents=True, exist_ok=True)
        file_b_path = cat_dir_b / "beta_icu_protocols.txt"
        file_b_path.write_text(doc_b_content, encoding="utf-8")

        doc_b_rec = Document(
            title="Beta ICU Triage and Medication Protocols",
            category="clinical_protocols",
            filename="beta_icu_protocols.txt",
            file_path=str(file_b_path),
            file_size=len(doc_b_content),
            mime_type="text/plain",
            uploader_id=admin.id,
            tenant_id=self.tenant_b["id"],
        )
        self.db.add(doc_b_rec)
        self.db.commit()
        self.db.refresh(doc_b_rec)
        ingest_document_to_rag(db=self.db, document_id=doc_b_rec.id, tenant_id=self.tenant_b["id"])
        self.doc_b = doc_b_rec

        # Seed Ticket in Tenant B
        ticket_b_rec = Ticket(
            ticket_code=f"TICK-{self.tenant_b['id']}-7788",
            user_id=user_b.id,
            tenant_id=self.tenant_b["id"],
            title="Ventilator Telemetry Intermittent Disconnect",
            description="Room 402 ICU telemetry monitor dropped connection to centralized nurse station.",
            category="clinical_protocols",
            status=TicketStatus.OPEN,
        )
        self.db.add(ticket_b_rec)
        self.db.commit()
        self.db.refresh(ticket_b_rec)
        self.ticket_b = ticket_b_rec
        print("Setup completed successfully.")

    # 1. Database-Level Isolation
    def test_database_level_isolation(self):
        with engine.connect() as conn:
            docs = conn.execute(text("SELECT id, title, tenant_id FROM documents WHERE tenant_id IN (:ta, :tb)"),
                                {"ta": self.tenant_a["id"], "tb": self.tenant_b["id"]}).fetchall()
            ta_docs = [d for d in docs if d[2] == self.tenant_a["id"]]
            tb_docs = [d for d in docs if d[2] == self.tenant_b["id"]]

            passed = (len(ta_docs) >= 1 and len(tb_docs) >= 1 and
                      all(d[2] == self.tenant_a["id"] for d in ta_docs) and
                      all(d[2] == self.tenant_b["id"] for d in tb_docs))
            evidence = f"Tenant A DB docs: {len(ta_docs)}, Tenant B DB docs: {len(tb_docs)}"
            self.record("Database-Level Row Isolation", passed, evidence)

    # 2. API-Level Document Listing Isolation
    def test_api_document_listing_isolation(self):
        res_a = self.client.get("/api/v1/documents", headers={"Authorization": f"Bearer {self.user_a_token}"})
        res_b = self.client.get("/api/v1/documents", headers={"Authorization": f"Bearer {self.user_b_token}"})

        docs_a = [d["title"] for d in res_a.json()]
        docs_b = [d["title"] for d in res_b.json()]

        passed = (
            "Alpha Cloud Infrastructure Architecture" in docs_a and
            "Beta ICU Triage and Medication Protocols" not in docs_a and
            "Beta ICU Triage and Medication Protocols" in docs_b and
            "Alpha Cloud Infrastructure Architecture" not in docs_b
        )
        evidence = f"Tenant A list: {docs_a}; Tenant B list: {docs_b}"
        self.record("API Document Listing Boundary", passed, evidence)

    # 3. Document Access & Deletion Isolation (Negative Tests)
    def test_document_cross_access_denial(self):
        # Tenant A user attempting to GET Tenant B document
        res_get = self.client.get(
            f"/api/v1/documents/{self.doc_b.id}",
            headers={"Authorization": f"Bearer {self.user_a_token}"},
        )
        get_denied = res_get.status_code == 404

        # Tenant A admin attempting to DELETE Tenant B document
        res_del = self.client.delete(
            f"/api/v1/documents/{self.doc_b.id}",
            headers={"Authorization": f"Bearer {self.admin_a_token}"},
        )
        del_denied = res_del.status_code == 404

        passed = get_denied and del_denied
        evidence = f"GET cross-tenant doc: {res_get.status_code}; DELETE cross-tenant doc: {res_del.status_code}"
        self.record("Cross-Tenant Document Access & Delete Denial", passed, evidence)

    # 4. ChromaDB Collection Partitioning
    def test_chromadb_collection_partitioning(self):
        c = chromadb.PersistentClient("data/chroma_db")
        col_a_name = f"tenant_{self.tenant_a['id']}_kb"
        col_b_name = f"tenant_{self.tenant_b['id']}_kb"

        col_a = c.get_collection(col_a_name)
        col_b = c.get_collection(col_b_name)

        docs_in_a = col_a.get()["documents"]
        docs_in_b = col_b.get()["documents"]

        leak_in_a = any("ICU" in d or "Morphine" in d for d in docs_in_a)
        leak_in_b = any("Kubernetes" in d or "Terraform" in d for d in docs_in_b)

        passed = not leak_in_a and not leak_in_b and len(docs_in_a) > 0 and len(docs_in_b) > 0
        evidence = f"Col {col_a_name} count: {col_a.count()} (leak: {leak_in_a}); Col {col_b_name} count: {col_b.count()} (leak: {leak_in_b})"
        self.record("ChromaDB Dedicated Collection Partitioning", passed, evidence)

    # 5. BM25 Retrieval Isolation
    def test_bm25_retrieval_isolation(self):
        bm25_a = get_bm25_index(self.tenant_a["id"])
        bm25_b = get_bm25_index(self.tenant_b["id"])

        # Query A with B's distinct keywords
        hits_in_a = bm25_a.search("Morphine ICU triage dosage pediatric", top_k=5)
        # Query B with A's distinct keywords
        hits_in_b = bm25_b.search("Kubernetes Istio Terraform ZeroTrust mTLS", top_k=5)

        passed = len(hits_in_a) == 0 and len(hits_in_b) == 0
        evidence = f"Hits in Index A for medical terms: {len(hits_in_a)}; Hits in Index B for tech terms: {len(hits_in_b)}"
        self.record("BM25 Okapi Index Lexical Isolation", passed, evidence)

    # 6. Hybrid RAG Retrieval & Citation Isolation
    def test_hybrid_rag_and_citation_isolation(self):
        # Query Tenant A with medical prompt
        res_rag_a = self.client.post(
            "/api/v1/rag/query",
            json={"query": "What is the pediatric morphine dosage and triage policy?", "top_k": 4},
            headers={"Authorization": f"Bearer {self.user_a_token}"},
        )
        assert res_rag_a.status_code == 200
        results_a = res_rag_a.json()["results"]
        leak_a = any("Beta" in r["text"] or "Morphine" in r["text"] or "ICU" in r["text"] for r in results_a)

        # Query Tenant B with tech prompt
        res_rag_b = self.client.post(
            "/api/v1/rag/query",
            json={"query": "Where is the Terraform state file stored?", "top_k": 4},
            headers={"Authorization": f"Bearer {self.user_b_token}"},
        )
        assert res_rag_b.status_code == 200
        results_b = res_rag_b.json()["results"]
        leak_b = any("Alpha" in r["text"] or "Terraform" in r["text"] or "Istio" in r["text"] for r in results_b)

        passed = not leak_a and not leak_b
        evidence = f"Tenant A RAG leak: {leak_a} (results: {len(results_a)}); Tenant B RAG leak: {leak_b} (results: {len(results_b)})"
        self.record("Hybrid RAG & Citation Cross-Tenant Boundary", passed, evidence)

    # 7. Ticket & Conversation Isolation
    def test_ticket_and_conversation_isolation(self):
        # Tenant A user lists tickets
        res_tickets = self.client.get("/api/v1/tickets", headers={"Authorization": f"Bearer {self.user_a_token}"})
        assert res_tickets.status_code == 200
        tickets_seen = [t["ticket_code"] for t in res_tickets.json()]
        ticket_b_leaked = self.ticket_b.ticket_code in tickets_seen

        # Tenant A user attempts to update Tenant B ticket
        res_patch = self.client.patch(
            f"/api/v1/tickets/{self.ticket_b.id}",
            json={"status": "resolved", "priority": "high"},
            headers={"Authorization": f"Bearer {self.admin_a_token}"},
        )
        patch_denied = res_patch.status_code == 404

        passed = not ticket_b_leaked and patch_denied
        evidence = f"Ticket B leaked in A's queue: {ticket_b_leaked}; PATCH cross-tenant status: {res_patch.status_code}"
        self.record("Ticket Queue & Modification Isolation", passed, evidence)

    # 8. Agent Tool Execution & Memory Scoping
    def test_agent_tool_isolation(self):
        # Tenant A user runs agent tool to ask about ICU triage
        res_agent_a = self.client.post(
            "/api/v1/agent/run",
            json={"prompt": "Find documents regarding pediatric morphine dosage and ICU triage."},
            headers={"Authorization": f"Bearer {self.user_a_token}"},
        )
        assert res_agent_a.status_code == 200
        data_a = res_agent_a.json()
        agent_a_resp = data_a.get("agent_response", "")
        leak_agent = "Beta" in agent_a_resp or "Morphine" in agent_a_resp or "0.05 mg/kg" in agent_a_resp

        # Tenant A user creates ticket via agent
        res_agent_tick = self.client.post(
            "/api/v1/agent/run",
            json={"prompt": "Please report a critical database timeout issue on cluster Alpha."},
            headers={"Authorization": f"Bearer {self.user_a_token}"},
        )
        data_tick = res_agent_tick.json()
        tick_code = data_tick.get("tool_output", {}).get("ticket_code", "")
        # Verify the created ticket has tenant_id == Tenant A
        created_tick = self.db.query(Ticket).filter(Ticket.ticket_code == tick_code).first()
        proper_tenant = created_tick and created_tick.tenant_id == self.tenant_a["id"]

        passed = not leak_agent and proper_tenant
        evidence = f"Agent leaked Tenant B data: {leak_agent}; Agent ticket tenant_id correct: {proper_tenant} ({tick_code})"
        self.record("Agent Tool Execution & Ticket Creation Scoping", passed, evidence)

    # 9. Suspended Tenant Lockout & Reactivation
    def test_suspended_tenant_lifecycle(self):
        tid = self.tenant_b["id"]
        # 1. Suspend Tenant B
        res_sus = self.client.post(
            f"/api/v1/platform/tenants/{tid}/suspend",
            headers={"Authorization": f"Bearer {self.platform_admin_token}"},
        )
        assert res_sus.status_code == 200
        assert res_sus.json()["status"] == "SUSPENDED"

        # 2. Verify immediate lockout on Tenant B endpoints
        res_doc_b = self.client.get("/api/v1/documents", headers={"Authorization": f"Bearer {self.user_b_token}"})
        res_rag_b = self.client.post("/api/v1/rag/query", json={"query": "test"}, headers={"Authorization": f"Bearer {self.user_b_token}"})
        res_tick_b = self.client.get("/api/v1/tickets", headers={"Authorization": f"Bearer {self.user_b_token}"})

        b_locked = (res_doc_b.status_code == 403 and res_rag_b.status_code == 403 and res_tick_b.status_code == 403)

        # 3. Verify Tenant A is completely unaffected
        res_doc_a = self.client.get("/api/v1/documents", headers={"Authorization": f"Bearer {self.user_a_token}"})
        a_unaffected = res_doc_a.status_code == 200

        # 4. Reactivate Tenant B
        res_act = self.client.post(
            f"/api/v1/platform/tenants/{tid}/activate",
            headers={"Authorization": f"Bearer {self.platform_admin_token}"},
        )
        assert res_act.status_code == 200
        assert res_act.json()["status"] == "ACTIVE"

        res_doc_b_after = self.client.get("/api/v1/documents", headers={"Authorization": f"Bearer {self.user_b_token}"})
        b_restored = res_doc_b_after.status_code == 200

        passed = b_locked and a_unaffected and b_restored
        evidence = f"B suspended codes (doc:{res_doc_b.status_code}, rag:{res_rag_b.status_code}); A unaffected: {res_doc_a.status_code}; B restored: {res_doc_b_after.status_code}"
        self.record("Suspended Tenant Access Lockout & Recovery", passed, evidence)

    # 10. JWT Tampering & Tenant Spoofing Defense
    def test_jwt_tampering_and_spoofing(self):
        # 1. Attacker attempts to forge tenant context via HTTP header
        res_header_spoof = self.client.get(
            "/api/v1/documents",
            headers={
                "Authorization": f"Bearer {self.user_a_token}",
                "X-Tenant-ID": str(self.tenant_b["id"]),
                "Tenant-Id": str(self.tenant_b["id"]),
            },
        )
        # Hardened defense: spoofing foreign tenant ID is actively rejected with HTTP 403 Forbidden
        if res_header_spoof.status_code == 403:
            header_spoof_prevented = True
        elif res_header_spoof.status_code == 200 and isinstance(res_header_spoof.json(), list):
            docs = [d["title"] for d in res_header_spoof.json()]
            header_spoof_prevented = ("Beta ICU Triage and Medication Protocols" not in docs and
                                      "Alpha Cloud Infrastructure Architecture" in docs)
        else:
            header_spoof_prevented = False

        # 2. Attacker crafts JWT with forged subject or invalid signature
        invalid_token = self.user_a_token[:-5] + "XXXXX"
        res_bad_jwt = self.client.get(
            "/api/v1/documents",
            headers={"Authorization": f"Bearer {invalid_token}"},
        )
        bad_jwt_denied = res_bad_jwt.status_code == 401

        # 3. Forged token with non-existent username
        ghost_token = create_access_token(subject="ghost_infiltrator_9999")
        res_ghost = self.client.get(
            "/api/v1/documents",
            headers={"Authorization": f"Bearer {ghost_token}"},
        )
        ghost_denied = res_ghost.status_code == 404

        passed = header_spoof_prevented and bad_jwt_denied and ghost_denied
        evidence = f"Header spoof ignored: {header_spoof_prevented}; Tampered JWT code: {res_bad_jwt.status_code}; Ghost user code: {res_ghost.status_code}"
        self.record("JWT Cryptographic & Header Spoofing Defense", passed, evidence)

    # 11. Unauthorized Platform Administration Barrier
    def test_unauthorized_platform_admin_barrier(self):
        # Tenant A Admin attempts to provision new tenant
        res_prov = self.client.post(
            "/api/v1/platform/tenants",
            json={"name": "Hacked Tenant", "slug": "hacked-slug", "industry": "other", "admin_email": "h@h.com", "admin_username": "h", "admin_password": "p"},
            headers={"Authorization": f"Bearer {self.admin_a_token}"},
        )
        prov_denied = res_prov.status_code == 403

        # Tenant A Admin attempts to suspend Tenant B
        res_sus = self.client.post(
            f"/api/v1/platform/tenants/{self.tenant_b['id']}/suspend",
            headers={"Authorization": f"Bearer {self.admin_a_token}"},
        )
        sus_denied = res_sus.status_code == 403

        # Tenant A Admin attempts to read platform overview
        res_over = self.client.get(
            "/api/v1/platform/overview",
            headers={"Authorization": f"Bearer {self.admin_a_token}"},
        )
        over_denied = res_over.status_code == 403

        passed = prov_denied and sus_denied and over_denied
        evidence = f"Provisioning code: {res_prov.status_code}; Suspend code: {res_sus.status_code}; Overview code: {res_over.status_code}"
        self.record("Platform Administration Privilege Barrier", passed, evidence)

    # 12. Legacy University Knowledge Base Partitioning
    def test_legacy_university_kb_partitioning(self):
        # Tenant 1 (University) queries attendance regulations
        res_univ = self.client.post(
            "/api/v1/rag/query",
            json={"query": "What is the mandatory attendance requirement?", "top_k": 3},
            headers={"Authorization": f"Bearer {self.platform_admin_token}"},
        )
        assert res_univ.status_code == 200
        univ_results = res_univ.json()["results"]
        univ_accessible = any("75%" in r["text"] or "attendance" in r["text"].lower() for r in univ_results)

        # Tenant A queries attendance regulations
        res_a_univ = self.client.post(
            "/api/v1/rag/query",
            json={"query": "What is the mandatory attendance requirement?", "top_k": 3},
            headers={"Authorization": f"Bearer {self.user_a_token}"},
        )
        assert res_a_univ.status_code == 200
        a_results = res_a_univ.json()["results"]
        # Must NOT return University Institutional Regulations
        leak_univ_to_a = any("UniMind University" in r["text"] or "Dean of Academic Affairs" in r["text"] for r in a_results)

        passed = univ_accessible and not leak_univ_to_a
        evidence = f"Univ query found: {univ_accessible}; University leaked into Tenant A: {leak_univ_to_a}"
        self.record("Legacy University KB Partitioning & Accessibility", passed, evidence)

    # 13. Concurrent Cross-Tenant Retrieval Stress
    def test_concurrent_cross_tenant_retrieval(self):
        queries = [
            ("Alpha", self.user_a_token, "What is the Istio service mesh and VPC configuration?", "Alpha"),
            ("Beta", self.user_b_token, "What is the pediatric morphine dosage in ICU triage?", "Beta"),
            ("Univ", self.platform_admin_token, "What is the mandatory curfew time for hostels?", "Hostel"),
        ] * 4  # 12 concurrent requests across 3 distinct tenants

        errors = []
        def _exec(item):
            label, token, q, expected = item
            res = self.client.post(
                "/api/v1/rag/query",
                json={"query": q, "top_k": 3},
                headers={"Authorization": f"Bearer {token}"},
            )
            if res.status_code != 200:
                errors.append(f"{label} HTTP {res.status_code}")
                return
            texts = [r["text"] for r in res.json()["results"]]
            if label == "Alpha" and any("Morphine" in t or "curfew" in t.lower() for t in texts):
                errors.append("Alpha received foreign data!")
            if label == "Beta" and any("Kubernetes" in t or "curfew" in t.lower() for t in texts):
                errors.append("Beta received foreign data!")
            if label == "Univ" and any("Morphine" in t or "Kubernetes" in t for t in texts):
                errors.append("Univ received foreign data!")

        with ThreadPoolExecutor(max_workers=6) as ex:
            list(ex.map(_exec, queries))

        passed = len(errors) == 0
        evidence = f"12 concurrent requests completed. Violations: {errors if errors else 'None'}"
        self.record("Concurrent Multi-Tenant Retrieval Thread Safety", passed, evidence)

    # 14. Persistence, Client Reload & Isolation Stability
    def test_persistence_and_restart_isolation(self):
        # Simulate service restart by creating fresh ChromaStore & BM25 handles
        from rag.vector_store import chroma_service
        from rag.retrieval import bm25

        # Re-fetch stores
        fresh_store_a = chroma_service.ChromaStore(tenant_id=self.tenant_a["id"])
        fresh_store_b = chroma_service.ChromaStore(tenant_id=self.tenant_b["id"])

        res_a = fresh_store_a.query("Kubernetes", top_k=2)
        res_b = fresh_store_b.query("Morphine", top_k=2)

        leak_a = any("Beta" in r["text"] for r in res_a)
        leak_b = any("Alpha" in r["text"] for r in res_b)
        has_a = len(res_a) > 0
        has_b = len(res_b) > 0

        passed = has_a and has_b and not leak_a and not leak_b
        evidence = f"Fresh Store A retrieved: {len(res_a)} (leak: {leak_a}); Fresh Store B retrieved: {len(res_b)} (leak: {leak_b})"
        self.record("Cold Restart Persistence & Collection Separation", passed, evidence)

    # 15. Header-based Tenant Spoofing Denial & Context Switching
    def test_tenant_spoofing_via_header_blocked(self):
        # 1. User A (Alpha Corp) attempts to spoof Tenant B (Beta Health) via X-Tenant-ID header
        res_spoof = self.client.get(
            "/api/v1/documents",
            headers={
                "Authorization": f"Bearer {self.user_a_token}",
                "X-Tenant-ID": str(self.tenant_b["id"]),
            },
        )
        blocked_spoof = (res_spoof.status_code == 403)

        # 2. Invalid X-Tenant-ID header format (must be positive integer)
        res_invalid = self.client.get(
            "/api/v1/documents",
            headers={
                "Authorization": f"Bearer {self.user_a_token}",
                "X-Tenant-ID": "invalid_format",
            },
        )
        blocked_invalid = (res_invalid.status_code == 400)

        # 3. Non-existent X-Tenant-ID
        res_nonexistent = self.client.get(
            "/api/v1/documents",
            headers={
                "Authorization": f"Bearer {self.platform_admin_token}",
                "X-Tenant-ID": "99999",
            },
        )
        blocked_nonexistent = (res_nonexistent.status_code == 404)

        # 4. Super Admin authorized context switching via X-Tenant-ID
        res_admin_switch = self.client.get(
            "/api/v1/documents",
            headers={
                "Authorization": f"Bearer {self.platform_admin_token}",
                "X-Tenant-ID": str(self.tenant_a["id"]),
            },
        )
        admin_switch_ok = (res_admin_switch.status_code == 200)

        passed = blocked_spoof and blocked_invalid and blocked_nonexistent and admin_switch_ok
        evidence = (
            f"Spoof blocked (403): {blocked_spoof}; "
            f"Invalid header rejected (400): {blocked_invalid}; "
            f"Non-existent tenant 404: {blocked_nonexistent}; "
            f"Admin switch 200: {admin_switch_ok}"
        )
        self.record("Header-Based Tenant Spoofing Defense & Context Switching", passed, evidence)

    def test_audit_log_boundary_isolation(self):
        """Probe 16: Audit log boundary isolation across tenants."""
        import json
        # Ensure audit records for Tenant A and Tenant B
        log_a = AuditLog(
            tenant_id=self.tenant_a["id"],
            action="PROBE_16_ACTION_A",
            performed_by="user_a",
            target_resource="service/probe16-a",
            status="SUCCESS",
            details={"env": "prod"},
        )
        log_b = AuditLog(
            tenant_id=self.tenant_b["id"],
            action="PROBE_16_ACTION_B",
            performed_by="user_b",
            target_resource="service/probe16-b",
            status="SUCCESS",
            details={"env": "prod"},
        )
        self.db.add_all([log_a, log_b])
        self.db.commit()

        # Tenant A exports audit logs
        res_export_a = self.client.get(
            "/api/v1/governance/audit/export?format=jsonl",
            headers={"Authorization": f"Bearer {self.user_a_token}"},
        )
        export_a_ok = (res_export_a.status_code == 200)
        lines = [l for l in res_export_a.text.split("\n") if l.strip()]
        cross_leak = False
        for l in lines:
            rec = json.loads(l)
            if rec.get("tenant_id") == self.tenant_b["id"]:
                cross_leak = True

        # Tenant A attempts to verify Tenant B audit chain via header spoof
        res_verify_spoof = self.client.get(
            "/api/v1/governance/audit/verify-chain",
            headers={
                "Authorization": f"Bearer {self.user_a_token}",
                "X-Tenant-ID": str(self.tenant_b["id"]),
            },
        )
        spoof_blocked = (res_verify_spoof.status_code == 403)

        passed = export_a_ok and (not cross_leak) and spoof_blocked
        evidence = (
            f"Export 200: {export_a_ok}; "
            f"Cross-tenant leak in export: {cross_leak}; "
            f"Verify chain spoof blocked (403): {spoof_blocked}"
        )
        self.record("Audit Log Boundary Isolation & Tamper Chain Scoping", passed, evidence)

    def test_remediation_and_incident_scoping(self):
        """Probe 17: Remediation execution & chaos incident scoping."""
        # Create an incident for Tenant B
        inc_b = Incident(
            incident_code=f"INC-PROBE17-B-{int(time.time()*1000)}",
            tenant_id=self.tenant_b["id"],
            service_name="exam-service",
            title="ConnectionPoolExhausted in exam-service",
            severity=IncidentSeverity.HIGH,
            status=IncidentStatus.OPEN,
            logs_summary=["DB pool 100% full"],
        )
        self.db.add(inc_b)
        self.db.commit()
        self.db.refresh(inc_b)

        # User A attempts to transition Tenant B's incident
        res_trans_spoof = self.client.post(
            f"/api/v1/aegisops/incidents/{inc_b.id}/transition",
            json={"status": "INVESTIGATING", "notes": "Unauthorized transition attempt by Tenant A"},
            headers={"Authorization": f"Bearer {self.admin_a_token}"},
        )
        trans_blocked = (res_trans_spoof.status_code in (403, 404))

        # User A attempts to read Tenant B's incident by ID
        res_get_spoof = self.client.get(
            f"/api/v1/incidents/{inc_b.id}",
            headers={"Authorization": f"Bearer {self.user_a_token}"},
        )
        get_blocked = (res_get_spoof.status_code in (403, 404))

        passed = trans_blocked and get_blocked
        evidence = (
            f"Cross-tenant transition blocked ({res_trans_spoof.status_code}): {trans_blocked}; "
            f"Cross-tenant incident read blocked ({res_get_spoof.status_code}): {get_blocked}"
        )
        self.record("Remediation Execution & Incident Scoping Isolation", passed, evidence)

    def test_cache_namespace_isolation(self):
        """Probe 18: In-memory / cache key tenant namespace isolation."""
        cache = AdapterFactory.get_cache()
        key = "probe18_shared_config"
        tid_a = self.tenant_a["id"]
        tid_b = self.tenant_b["id"]

        cache.set(tid_a, key, "ALPHA_SECRET_PAYLOAD_991")
        cache.set(tid_b, key, "BETA_SECRET_PAYLOAD_992")

        val_a = cache.get(tid_a, key)
        val_b = cache.get(tid_b, key)

        vals_isolated = (val_a == "ALPHA_SECRET_PAYLOAD_991" and val_b == "BETA_SECRET_PAYLOAD_992")

        # Zero/negative tenant_id violation check
        zero_tid_blocked = False
        try:
            cache.get(0, key)
        except TenantIsolationViolationError:
            zero_tid_blocked = True
        except Exception:
            pass

        # Delete from A, confirm B unaffected
        cache.delete(tid_a, key)
        val_a_post = cache.get(tid_a, key)
        val_b_post = cache.get(tid_b, key)
        delete_isolated = (val_a_post is None and val_b_post == "BETA_SECRET_PAYLOAD_992")

        passed = vals_isolated and zero_tid_blocked and delete_isolated
        evidence = (
            f"Values partitioned: {vals_isolated}; "
            f"Non-positive tenant_id blocked: {zero_tid_blocked}; "
            f"Delete isolation verified: {delete_isolated}"
        )
        self.record("In-Memory & Cache Key Tenant Namespace Isolation", passed, evidence)

    def cleanup(self):
        c_clean = chromadb.PersistentClient("data/chroma_db")
        for slug in ["alpha-corp-sec", "beta-health-sec"]:
            org = self.db.query(Organization).filter(Organization.slug == slug).first()
            if org:
                try:
                    c_clean.delete_collection(f"tenant_{org.id}_kb")
                except Exception:
                    pass
                self.db.query(Ticket).filter(Ticket.tenant_id == org.id).delete()
                self.db.query(Incident).filter(Incident.tenant_id == org.id).delete()
                self.db.query(Document).filter(Document.tenant_id == org.id).delete()
                self.db.query(AuditLog).filter(AuditLog.tenant_id == org.id).delete()
                self.db.query(OrganizationMembership).filter(OrganizationMembership.tenant_id == org.id).delete()
                self.db.query(User).filter(User.tenant_id == org.id).delete()
                self.db.query(Organization).filter(Organization.id == org.id).delete()
                self.db.commit()

    def run_all(self):
        print("\n================================================================================")
        print("          STAGE F INDEPENDENT CROSS-TENANT SECURITY & ISOLATION SUITE          ")
        print("================================================================================")
        try:
            self.setup_tenants_and_users()
            print("\n--- Running Security Test Matrix ---")
            self.test_database_level_isolation()
            self.test_api_document_listing_isolation()
            self.test_document_cross_access_denial()
            self.test_chromadb_collection_partitioning()
            self.test_bm25_retrieval_isolation()
            self.test_hybrid_rag_and_citation_isolation()
            self.test_ticket_and_conversation_isolation()
            self.test_agent_tool_isolation()
            self.test_suspended_tenant_lifecycle()
            self.test_jwt_tampering_and_spoofing()
            self.test_unauthorized_platform_admin_barrier()
            self.test_legacy_university_kb_partitioning()
            self.test_concurrent_cross_tenant_retrieval()
            self.test_persistence_and_restart_isolation()
            self.test_tenant_spoofing_via_header_blocked()
            self.test_audit_log_boundary_isolation()
            self.test_remediation_and_incident_scoping()
            self.test_cache_namespace_isolation()
        finally:
            self.cleanup()

        total = len(self.results)
        passed_cnt = sum(1 for r in self.results if r["status"] == "PASS")
        print("\n================================================================================")
        print(f"                       FINAL SUMMARY: {passed_cnt}/{total} PASSED")
        print("================================================================================")
        for r in self.results:
            print(f"[{r['status']}] {r['test_name']}")
            print(f"       Evidence: {r['evidence']}")
            if r["limitation"] != "None":
                print(f"       Limitation: {r['limitation']}")
        return passed_cnt == total


if __name__ == "__main__":
    runner = SecurityVerificationRunner()
    success = runner.run_all()
    sys.exit(0 if success else 1)
