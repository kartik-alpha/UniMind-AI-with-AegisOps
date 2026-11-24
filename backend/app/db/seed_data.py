import os
from pathlib import Path
from sqlalchemy.orm import Session
from app.db.base_class import Base
from app.db.session import engine, SessionLocal
from app.core.security import get_password_hash
from app.models.organization import (
    Organization,
    OrganizationMembership,
    TenantStatus,
    TenantIndustry,
    TenantRole,
)
from app.models.user import User, UserRole
from app.models.document import Document
from app.models.ticket import Ticket, TicketPriority, TicketStatus, Incident, IncidentSeverity, IncidentStatus
from rag.ingestion.chunker import chunk_text
from rag.vector_store.chroma_service import get_chroma_store
from app.db.migrations.manager import apply_migrations


def _migrate_sqlite_schema(bind_engine):
    """Safely adds missing tenant_id column to existing SQLite tables if not present."""
    from sqlalchemy import text
    try:
        with bind_engine.connect() as conn:
            for table in ["users", "documents", "tickets", "conversations", "incidents", "audit_logs"]:
                try:
                    res = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
                    cols = [r[1] for r in res]
                    if cols and "tenant_id" not in cols:
                        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN tenant_id INTEGER DEFAULT 1 REFERENCES organizations(id)"))
                        conn.commit()
                except Exception:
                    pass

            # Ensure audit_logs has cryptographic hash chain columns
            try:
                res = conn.execute(text("PRAGMA table_info(audit_logs)")).fetchall()
                cols = [r[1] for r in res]
                if cols:
                    if "previous_hash" not in cols:
                        conn.execute(text("ALTER TABLE audit_logs ADD COLUMN previous_hash VARCHAR(64)"))
                    if "current_hash" not in cols:
                        conn.execute(text("ALTER TABLE audit_logs ADD COLUMN current_hash VARCHAR(64)"))
                    if "signature" not in cols:
                        conn.execute(text("ALTER TABLE audit_logs ADD COLUMN signature VARCHAR(128)"))
                    conn.commit()
            except Exception:
                pass
    except Exception:
        pass


def seed_initial_data():
    """Seeds default demo users, documents, incident, tickets, and RAG knowledge base."""
    Base.metadata.create_all(bind=engine)
    apply_migrations(engine)
    _migrate_sqlite_schema(engine)
    db: Session = SessionLocal()

    try:
        # 0. Seed Default Organization (UniMind University)
        default_org = db.query(Organization).filter(Organization.slug == "unimind-edu").first()
        if not default_org:
            default_org = Organization(
                slug="unimind-edu",
                name="UniMind University",
                industry=TenantIndustry.EDUCATION,
                status=TenantStatus.ACTIVE,
                config={
                    "display_name": "UniMind University",
                    "categories": ["attendance", "examinations", "hostel", "library", "academics", "policies"],
                    "primary_color": "#2563eb",
                    "welcome_message": "Welcome to UniMind AI Institutional Support.",
                    "ai_instructions": "You are UniMind AI, the official student and faculty academic assistant.",
                },
            )
            db.add(default_org)
            db.commit()
            db.refresh(default_org)

        # 1. Seed Users
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin = User(
                email="admin@unimind.edu",
                username="admin",
                full_name="Kartik Lakhera",
                hashed_password=get_password_hash("admin123"),
                role=UserRole.ADMIN,
                tenant_id=default_org.id,
                is_active=True,
            )
            db.add(admin)
        elif not admin.tenant_id:
            admin.tenant_id = default_org.id

        student = db.query(User).filter(User.username == "student").first()
        if not student:
            student = User(
                email="student@unimind.edu",
                username="student",
                full_name="Alice Student",
                hashed_password=get_password_hash("student123"),
                role=UserRole.STUDENT,
                tenant_id=default_org.id,
                is_active=True,
            )
            db.add(student)
        elif not student.tenant_id:
            student.tenant_id = default_org.id

        db.commit()
        if admin:
            db.refresh(admin)
            admin_mem = db.query(OrganizationMembership).filter(
                OrganizationMembership.user_id == admin.id,
                OrganizationMembership.tenant_id == default_org.id
            ).first()
            if not admin_mem:
                db.add(OrganizationMembership(
                    tenant_id=default_org.id,
                    user_id=admin.id,
                    role=TenantRole.TENANT_ADMIN,
                ))

        if student:
            db.refresh(student)
            stu_mem = db.query(OrganizationMembership).filter(
                OrganizationMembership.user_id == student.id,
                OrganizationMembership.tenant_id == default_org.id
            ).first()
            if not stu_mem:
                db.add(OrganizationMembership(
                    tenant_id=default_org.id,
                    user_id=student.id,
                    role=TenantRole.TENANT_MEMBER,
                ))

        db.commit()

        # Backfill any existing records without tenant_id to default_org
        db.query(Document).filter(Document.tenant_id == None).update({Document.tenant_id: default_org.id})
        db.query(Ticket).filter(Ticket.tenant_id == None).update({Ticket.tenant_id: default_org.id})
        db.query(Incident).filter(Incident.tenant_id == None).update({Incident.tenant_id: default_org.id})
        db.commit()

        # 2. Seed University Documents
        data_docs_dir = Path("./data/documents").resolve()
        data_docs_dir.mkdir(parents=True, exist_ok=True)

        sample_docs = [
            {
                "title": "Hostel Policy & Curfew Guidelines 2026",
                "category": "hostel",
                "filename": "hostel_curfew_policy_2026.txt",
                "content": (
                    "HOSTEL POLICY 2026 - CAMPUS RESIDENCE REGULATIONS\n"
                    "Mandatory hostel curfew is 10:00 PM for all undergraduate resident students.\n"
                    "Late entries require prior digital approval from the hostel warden submitted at least 2 hours in advance via the student portal.\n"
                    "Quiet hours begin strictly at 11:00 PM on weekdays and 12:00 AM on weekends.\n"
                    "External visitors are permitted in designated ground-floor visitor lounges between 4:00 PM and 8:00 PM daily.\n"
                    "Possession of prohibited electrical heating appliances or hazardous materials is strictly forbidden."
                ),
            },
            {
                "title": "Academic Attendance & Examination Regulations 2026",
                "category": "attendance",
                "filename": "attendance_exam_rules_2026.txt",
                "content": (
                    "ACADEMIC REGULATIONS 2026 - ATTENDANCE REQUIREMENTS\n"
                    "A minimum of 75% aggregate attendance across lectures, practical laboratory sessions, and tutorial hours is mandatory to be eligible for semester final examinations.\n"
                    "Students with attendance between 65% and 74% due to verified medical emergencies must file an appeal with medical documentation to the Dean of Academic Affairs within 7 working days.\n"
                    "Students falling below 65% attendance are automatically barred from end-term examinations and must repeat the course in summer term."
                ),
            },
            {
                "title": "Grading System & GPA Calculation Guidelines 2026",
                "category": "academic",
                "filename": "grading_gpa_guidelines_2026.txt",
                "content": (
                    "EXAMINATION GRADING SYSTEM 2026\n"
                    "The university utilizes a 10-point cumulative grade point average (CGPA) system based on relative grading:\n"
                    "A+ = 10.0 (Outstanding), A = 9.0 (Excellent), B+ = 8.0 (Very Good), B = 7.0 (Good), C = 6.0 (Average), D = 5.0 (Pass), F = 0.0 (Fail).\n"
                    "A minimum cumulative CGPA of 5.0 is required for undergraduate degree conferral.\n"
                    "Grade dispute appeals must be formally lodged through the Examination Portal within 10 days of results publication."
                ),
            },
            {
                "title": "IT Lab Access & Cloud Computing Regulations 2026",
                "category": "it",
                "filename": "it_lab_cloud_policy_2026.txt",
                "content": (
                    "IT INFRASTRUCTURE & LAB POLICIES 2026\n"
                    "Computing laboratories and AI research clusters are open 24/7 for authenticated engineering students.\n"
                    "VPN and cloud sandbox credentials are provisioned through university SSO and reset every 90 days.\n"
                    "Unauthorized network sniffing, port scanning, or cryptocurrency mining on university compute nodes is strictly prohibited and results in immediate account suspension."
                ),
            },
        ]

        admin_user = db.query(User).filter(User.username == "admin").first()
        uploader_id = admin_user.id if admin_user else 1

        for d in sample_docs:
            existing = db.query(Document).filter(Document.title == d["title"]).first()
            if not existing:
                doc_path = data_docs_dir / d["filename"]
                doc_path.write_text(d["content"], encoding="utf-8")

                new_doc = Document(
                    title=d["title"],
                    category=d["category"],
                    filename=d["filename"],
                    file_path=str(doc_path),
                    uploader_id=uploader_id,
                    tenant_id=default_org.id,
                )
                db.add(new_doc)
                db.commit()
                db.refresh(new_doc)

                # Ingest into ChromaDB
                try:
                    chunks = chunk_text(
                        d["content"],
                        chunk_size=300,
                        chunk_overlap=40,
                        metadata={
                            "doc_id": new_doc.id,
                            "tenant_id": default_org.id,
                            "title": new_doc.title,
                            "category": new_doc.category,
                            "filename": new_doc.filename,
                            "source": new_doc.filename,
                        },
                    )
                    store = get_chroma_store()
                    store.add_chunks(chunks)
                    new_doc.chunk_count = len(chunks)
                    db.commit()
                except Exception as ex:
                    print(f"Warning: RAG auto-ingest error for {d['title']}: {ex}")

        # 3. Seed Active Infrastructure Incident
        active_inc = db.query(Incident).filter(Incident.incident_code == "INC-2026-0842").first()
        if not active_inc:
            active_inc = Incident(
                incident_code="INC-2026-0842",
                service_name="Exam Service",
                tenant_id=default_org.id,
                title="Database Connection Pool Exhaustion & Spike in 503 Errors",
                severity=IncidentSeverity.CRITICAL,
                status=IncidentStatus.OPEN,
                anomaly_score=0.91,
                root_cause="High concurrent submission load during exam window leading to DB connection pool timeout (>5000ms).",
                recommendation="Restart Exam Service Pod & Scale Replicas to 4",
            )
            db.add(active_inc)
            db.commit()

        # 4. Seed Support Tickets
        existing_tickets = db.query(Ticket).count()
        if existing_tickets == 0:
            student_user = db.query(User).filter(User.username == "student").first()
            student_id = student_user.id if student_user else 1

            t1 = Ticket(
                ticket_code="TCK-1001",
                user_id=student_id,
                tenant_id=default_org.id,
                title="Hostel Wi-Fi access point in Block C dropping connections",
                description="The 5GHz access point on the second floor keeps disconnecting during evening study hours.",
                category="IT Support",
                priority=TicketPriority.HIGH,
                status=TicketStatus.IN_PROGRESS,
            )
            t2 = Ticket(
                ticket_code="TCK-1002",
                user_id=student_id,
                tenant_id=default_org.id,
                title="Request for grade verification in CS402 Cloud & AIOps",
                description="Submitted mid-term assignment on LMS before deadline, request grade audit verification.",
                category="Academic",
                priority=TicketPriority.MEDIUM,
                status=TicketStatus.OPEN,
            )
            t3 = Ticket(
                ticket_code="TCK-1003",
                user_id=student_id,
                tenant_id=default_org.id,
                title="Library RFID turnstile card scan error at main entrance",
                description="RFID card scanner displays read error for newly issued student ID cards.",
                category="Library",
                priority=TicketPriority.LOW,
                status=TicketStatus.RESOLVED,
            )
            db.add_all([t1, t2, t3])
            db.commit()

        # Backfill and cryptographically chain any pending audit logs
        try:
            from app.services.governance_service import GovernanceService
            GovernanceService.backfill_hash_chain(db)
        except Exception:
            pass

        print("[UniMind AI] Seeded default database state: users, documents, incident & tickets verified.")

    except Exception as e:
        print(f"[UniMind AI] Seed error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_initial_data()
