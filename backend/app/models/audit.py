from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from app.db.base_class import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String(100), index=True, nullable=False)  # e.g., REMEDIATION_RESTART, USER_LOGIN, DOCUMENT_UPLOAD
    performed_by = Column(String(100), nullable=False)  # username or system agent
    target_resource = Column(String(200), nullable=False)  # e.g., pod/exam-service, doc/attendance_policy.pdf
    status = Column(String(50), default="SUCCESS")  # SUCCESS, FAILED, PENDING
    details = Column(JSON, default=dict)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
