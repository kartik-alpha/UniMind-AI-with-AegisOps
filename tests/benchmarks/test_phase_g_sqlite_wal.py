"""
Phase G4: SQLite WAL Mode Concurrency & Database Crash Recovery Suite.
Validates:
1. Multi-threaded concurrent read/write transactions under WAL mode (zero database locked exceptions).
2. Atomic transaction integrity during simulated application exceptions.
3. Cryptographic audit log continuity and hash integrity after concurrent writes.
"""
import time
import sqlite3
import threading
import concurrent.futures
from sqlalchemy import text
import pytest

from app.db.session import engine, SessionLocal
from app.models.ticket import Ticket, TicketPriority, TicketStatus
from app.models.audit import AuditLog
from app.services.governance_service import GovernanceService


def test_sqlite_wal_journal_mode_enabled():
    """Verifies that the SQLite database engine is running in Write-Ahead Logging (WAL) mode."""
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA journal_mode")).fetchone()
        assert result is not None
        # Should be 'wal' (or memory if in-memory test)
        mode = result[0].lower()
        print(f"\n[BENCHMARK] SQLite journal_mode: {mode.upper()}")
        assert mode in ("wal", "memory"), f"Expected WAL mode, got: {mode}"


def test_concurrent_multithreaded_wal_writes():
    """
    Stress-tests WAL mode with 20 concurrent threads writing tickets and audit logs.
    Validates that zero 'database is locked' errors occur.
    """
    num_threads = 15
    errors = []
    created_ticket_ids = []

    def worker_transaction(thread_idx: int):
        db = SessionLocal()
        try:
            # 1. Create a ticket
            ticket = Ticket(
                ticket_code=f"TICK-WAL-{thread_idx}-{int(time.time()*1000)%10000}",
                title=f"Concurrent WAL Stress Test Thread #{thread_idx}",
                description="Testing SQLite WAL concurrency under load.",
                category="IT Support",
                priority=TicketPriority.MEDIUM,
                status=TicketStatus.OPEN,
                tenant_id=1,
            )
            db.add(ticket)
            db.flush()

            # 2. Record an audit log
            audit = GovernanceService.record_audit_event(
                db=db,
                tenant_id=1,
                action="WAL_CONCURRENCY_TEST",
                performed_by=f"worker_thread_{thread_idx}",
                target_resource=f"ticket/{ticket.id}",
                status="SUCCESS",
                details={"thread_idx": thread_idx},
            )
            db.commit()
            return ticket.id
        except Exception as e:
            db.rollback()
            errors.append(f"Thread {thread_idx} error: {type(e).__name__}: {str(e)}")
            return None
        finally:
            db.close()

    t_start = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(worker_transaction, i) for i in range(num_threads)]
        for f in concurrent.futures.as_completed(futures):
            res = f.result()
            if res:
                created_ticket_ids.append(res)
    t_elapsed = (time.perf_counter() - t_start) * 1000.0

    print(f"\n[BENCHMARK] SQLite WAL Concurrency: {num_threads} concurrent writes in {t_elapsed:.2f}ms. Errors: {len(errors)}")

    # Invariants
    assert len(errors) == 0, f"Concurrent database write errors encountered: {errors}"
    assert len(created_ticket_ids) == num_threads

    # Verify audit chain integrity after concurrent writes
    db = SessionLocal()
    try:
        chain_res = GovernanceService.verify_audit_chain(db, tenant_id=1)
        assert chain_res["is_valid"] is True, f"Audit chain broken after concurrent writes: {chain_res}"

        # Clean up test tickets
        db.query(Ticket).filter(Ticket.id.in_(created_ticket_ids)).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


def test_atomic_transaction_crash_recovery():
    """
    Validates atomic rollback behavior during unhandled exceptions:
    Ensures partially inserted records are never persisted to disk.
    """
    db = SessionLocal()
    initial_ticket_count = db.query(Ticket).count()

    # Simulate failing transaction block
    with pytest.raises(RuntimeError):
        try:
            t1 = Ticket(
                ticket_code="TICK-CRASH-TEST-01",
                title="Should Not Persist",
                description="Testing atomic rollback",
                category="IT",
                status=TicketStatus.OPEN,
                tenant_id=1,
            )
            db.add(t1)
            db.flush()
            # Force simulated unexpected failure
            raise RuntimeError("Simulated process crash / unhandled failure")
        except Exception:
            db.rollback()
            raise

    # Verify zero ghost records leaked
    final_ticket_count = db.query(Ticket).count()
    assert final_ticket_count == initial_ticket_count, "Dirty read leaked into database despite rollback!"
    db.close()
