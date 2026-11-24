"""
Stage F Database Migration & Data Integrity Validation Script.
Validates schema integrity, foreign keys, orphaned record absence, and migration idempotency.
"""

import sys
import os
import tempfile
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.db.base_class import Base
from app.db.session import engine as main_engine
from app.db.seed_data import _migrate_sqlite_schema, seed_initial_data
from app.models.organization import Organization, TenantIndustry, TenantStatus
from app.models.user import User
from app.models.document import Document
from app.models.ticket import Ticket, Incident
from app.models.conversation import Conversation
from app.models.audit import AuditLog


def validate_existing_database():
    print("\n--- 1. Validating Existing Database Schema & Records ---")
    db_path = ROOT / "unimind.db"
    if not db_path.exists():
        print(f"Database file not found at {db_path}. Initializing database schema and seeding enterprise data...")
        seed_initial_data()
    assert db_path.exists(), f"Database file not found at {db_path}"

    con = sqlite3.connect(str(db_path))
    cur = con.cursor()

    tables = ["users", "documents", "conversations", "tickets", "incidents", "audit_logs"]
    for tbl in tables:
        cols = [r[1] for r in cur.execute(f"PRAGMA table_info({tbl})").fetchall()]
        has_tid = "tenant_id" in cols
        print(f"Table '{tbl}': tenant_id column present? {has_tid}")
        assert has_tid, f"Table '{tbl}' is missing tenant_id column!"

    # Check for NULL tenant_id
    for tbl in tables:
        null_count = cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE tenant_id IS NULL").fetchone()[0]
        print(f"Table '{tbl}': NULL tenant_id count = {null_count}")
        assert null_count == 0, f"Table '{tbl}' has {null_count} orphaned records with NULL tenant_id!"

    # Check for foreign key integrity
    org_ids = set(r[0] for r in cur.execute("SELECT id FROM organizations").fetchall())
    print(f"Active Organization IDs: {org_ids}")
    assert 1 in org_ids, "Default University Organization (ID=1) missing!"

    for tbl in tables:
        orphans = [r[0] for r in cur.execute(f"SELECT DISTINCT tenant_id FROM {tbl}").fetchall() if r[0] not in org_ids]
        print(f"Table '{tbl}': Orphaned tenant_id values: {orphans}")
        assert len(orphans) == 0, f"Table '{tbl}' references non-existent tenant_id {orphans}!"

    # Verify Default University Data
    univ_org = cur.execute("SELECT id, slug, name, industry, status FROM organizations WHERE id=1").fetchone()
    print(f"University Org: {univ_org}")
    assert univ_org[1] == "unimind-edu" and univ_org[2] == "UniMind University"

    univ_docs = cur.execute("SELECT COUNT(*) FROM documents WHERE tenant_id=1").fetchone()[0]
    print(f"University Documents Count: {univ_docs}")
    assert univ_docs >= 4, f"Expected at least 4 university documents, found {univ_docs}"

    univ_users = cur.execute("SELECT username, role FROM users WHERE tenant_id=1").fetchall()
    print(f"University Users: {univ_users}")
    usernames = [u[0] for u in univ_users]
    assert "admin" in usernames and "student" in usernames

    con.close()
    print("Existing database validation: PASSED")


def validate_migration_idempotency():
    print("\n--- 2. Validating Migration Idempotency on Existing DB ---")
    # Running _migrate_sqlite_schema again should not alter columns or throw errors
    _migrate_sqlite_schema(main_engine)
    print("Migration re-run completed without errors.")


def validate_fresh_database_initialization():
    print("\n--- 3. Validating Fresh Database Creation & Seeding ---")
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_db_path = tmp.name

    try:
        tmp_engine = create_engine(f"sqlite:///{tmp_db_path}")
        Base.metadata.create_all(bind=tmp_engine)
        _migrate_sqlite_schema(tmp_engine)

        TmpSession = sessionmaker(bind=tmp_engine)
        session = TmpSession()

        # Seed data in fresh DB
        org = Organization(
            id=1,
            slug="unimind-edu",
            name="UniMind University",
            industry=TenantIndustry.EDUCATION,
            status=TenantStatus.ACTIVE,
            config={"display_name": "UniMind University"},
        )
        session.add(org)
        session.commit()

        user = User(
            email="test_fresh@univ.edu",
            username="fresh_user",
            full_name="Fresh User",
            hashed_password="hash",
            tenant_id=1,
        )
        session.add(user)
        session.commit()

        # Verify
        assert session.query(Organization).count() == 1
        assert session.query(User).count() == 1
        fresh_user = session.query(User).first()
        assert fresh_user.tenant_id == 1
        assert fresh_user.organization.name == "UniMind University"

        session.close()
        tmp_engine.dispose()
        print("Fresh database creation and foreign key verification: PASSED")
    finally:
        if os.path.exists(tmp_db_path):
            try:
                os.remove(tmp_db_path)
            except Exception:
                pass


if __name__ == "__main__":
    print("================================================================================")
    print("          STAGE F DATABASE MIGRATION & DATA INTEGRITY VALIDATION                ")
    print("================================================================================")
    validate_existing_database()
    validate_migration_idempotency()
    validate_fresh_database_initialization()
    print("\nALL DATABASE MIGRATION CHECKS PASSED SUCCESSFULLY.")

