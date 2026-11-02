from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.models.ticket import Ticket, TicketStatus, TicketPriority
from app.models.audit import AuditLog
from rag.retrieval.retriever import search_knowledge_base


def tool_search_documents(query: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Search university official documents knowledge base.
    """
    return search_knowledge_base(query=query, top_k=3, category_filter=category)


def tool_create_ticket(
    db: Session,
    user_id: int,
    title: str,
    description: str,
    category: str = "general",
    priority: str = "MEDIUM",
) -> Dict[str, Any]:
    """
    Create a student support ticket safely in the database.
    """
    p_enum = TicketPriority.MEDIUM
    try:
        p_enum = TicketPriority[priority.upper()]
    except KeyError:
        pass

    ticket = Ticket(
        ticket_code=f"TICK-{db.query(Ticket).count() + 1001}",
        user_id=user_id,
        title=title,
        description=description,
        category=category,
        priority=p_enum,
        status=TicketStatus.OPEN,
    )
    db.add(ticket)

    audit = AuditLog(
        action="CREATE_TICKET_VIA_AGENT",
        performed_by=f"user:{user_id}",
        target_resource=f"ticket/{ticket.ticket_code}",
        status="SUCCESS",
        details={"title": title, "category": category},
    )
    db.add(audit)
    db.commit()
    db.refresh(ticket)

    return {
        "ticket_code": ticket.ticket_code,
        "title": ticket.title,
        "status": ticket.status.value,
        "priority": ticket.priority.value,
        "created_at": ticket.created_at.isoformat(),
    }


def tool_check_service_status(service_name: str) -> Dict[str, Any]:
    """
    Check the operational status of university IT demo services.
    """
    valid_services = {"lms", "student_portal", "exam_service", "library_service"}
    clean_name = service_name.lower().strip().replace(" ", "_")

    if clean_name not in valid_services:
        return {"service": service_name, "status": "UNKNOWN", "message": "Service not found"}

    if clean_name == "exam_service":
        return {
            "service": "Exam Service",
            "status": "DEGRADED",
            "cpu_usage": 92.0,
            "latency_ms": 1800,
            "error_rate": 14.0,
            "active_incident": "INC-2026-001",
        }
    else:
        return {
            "service": service_name.title(),
            "status": "HEALTHY",
            "cpu_usage": 25.0,
            "latency_ms": 120,
            "error_rate": 0.1,
            "active_incident": None,
        }
