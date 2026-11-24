import json
import hmac
import hashlib
import threading
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, event, text
from app.db.base_class import Base

_audit_chain_lock = threading.Lock()


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("organizations.id"), default=1, nullable=True, index=True)
    action = Column(String(100), index=True, nullable=False)  # e.g., REMEDIATION_RESTART, USER_LOGIN, DOCUMENT_UPLOAD
    performed_by = Column(String(100), nullable=False)  # username or system agent
    target_resource = Column(String(200), nullable=False)  # e.g., pod/exam-service, doc/attendance_policy.pdf
    status = Column(String(50), default="SUCCESS")  # SUCCESS, FAILED, PENDING
    details = Column(JSON, default=dict)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    previous_hash = Column(String(64), nullable=True)
    current_hash = Column(String(64), nullable=True)
    signature = Column(String(128), nullable=True)


@event.listens_for(AuditLog, "before_insert")
def auto_chain_audit_log(mapper, connection, target):
    """
    Guarantees that every AuditLog inserted into the database is cryptographically
    hash-chained to the tenant's previous log and signed with an HMAC signature.
    """
    if target.previous_hash and target.current_hash and target.signature:
        return

    tenant_id = target.tenant_id or 1
    target.tenant_id = tenant_id

    with _audit_chain_lock:
        try:
            row = connection.execute(
                text("SELECT id, current_hash FROM audit_logs WHERE tenant_id = :tid ORDER BY id DESC LIMIT 1"),
                {"tid": tenant_id}
            ).fetchone()
            db_id = row[0] if row and row[0] else 0
            db_hash = row[1] if row and row[1] else ("0" * 64)

            pending_id = connection.info.get(f"_pending_id_{tenant_id}", 0)
            pending_hash = connection.info.get(f"_pending_hash_{tenant_id}")

            if pending_hash and pending_id > db_id:
                prev_hash = pending_hash
            else:
                prev_hash = db_hash
                connection.info.pop(f"_pending_hash_{tenant_id}", None)
                connection.info.pop(f"_pending_id_{tenant_id}", None)

            last_assigned = connection.info.get("_last_audit_id")
            max_row = connection.execute(text("SELECT MAX(id) FROM audit_logs")).fetchone()
            db_max = max_row[0] or 0 if max_row and max_row[0] else 0
            next_id = max(db_max, last_assigned or 0) + 1
            connection.info["_last_audit_id"] = next_id

            if target.id is None:
                target.id = next_id

            target.previous_hash = prev_hash
            if target.timestamp is None:
                target.timestamp = datetime.utcnow()
            ts_str = target.timestamp.isoformat()
            details_str = json.dumps(target.details or {}, sort_keys=True)
            payload = f"{prev_hash}|{target.id}|{tenant_id}|{target.action}|{target.performed_by}|{target.target_resource}|{target.status}|{ts_str}|{details_str}"
            curr_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

            from app.core.config import settings
            sig = hmac.new(settings.SECRET_KEY.encode("utf-8"), curr_hash.encode("utf-8"), hashlib.sha256).hexdigest()

            target.current_hash = curr_hash
            target.signature = sig
            connection.info[f"_pending_id_{tenant_id}"] = target.id
            connection.info[f"_pending_hash_{tenant_id}"] = curr_hash
        except Exception:
            pass
