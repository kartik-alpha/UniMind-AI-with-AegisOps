from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.ticket import (
    Ticket,
    TicketStatus,
    TicketPriority,
    Incident,
    IncidentSeverity,
    IncidentStatus,
)
from app.models.audit import AuditLog
from app.schemas.ticket import TicketCreate, TicketUpdate


def auto_triage_ticket(title: str, description: str) -> Dict[str, Any]:
    """
    Intelligent NLP-based ticket classifier and triage engine.
    Infers priority, category, sentiment urgency, and recommended routing team.
    """
    combined = f"{title} {description}".lower()

    # 1. Priority scoring
    critical_terms = ["critical", "crash", "outage", "emergency", "fatal", "data loss", "security breach", "ventilator", "down"]
    high_terms = ["urgent", "broken", "blocked", "immediate", "cannot access", "failure", "cannot submit", "unable to login", "error 500"]
    low_terms = ["minor", "typo", "suggestion", "cosmetic", "feature request", "feedback", "question"]

    if any(w in combined for w in critical_terms):
        priority = TicketPriority.CRITICAL
        urgency_score = 0.95
    elif any(w in combined for w in high_terms):
        priority = TicketPriority.HIGH
        urgency_score = 0.75
    elif any(w in combined for w in low_terms):
        priority = TicketPriority.LOW
        urgency_score = 0.25
    else:
        priority = TicketPriority.MEDIUM
        urgency_score = 0.50

    # 2. Category & Department Routing (Domain-Specific First)
    if any(w in combined for w in ["icu", "triage", "morphine", "dosage", "clinical", "patient", "nurse", "ventilator", "vital signs"]):
        category = "Clinical Operations"
        department = "Clinical Informatics"
    elif any(w in combined for w in ["exam", "grade", "marks", "evaluation", "hall ticket", "re-evaluation"]):
        category = "Examinations"
        department = "Examination Cell"
    elif any(w in combined for w in ["wifi", "network", "internet", "lms", "portal", "login", "credentials", "server", "cluster", "telemetry"]):
        category = "IT Infrastructure"
        department = "IT Operations Team"
    elif any(w in combined for w in ["library", "book", "catalogue", "fine", "card"]):
        category = "Library"
        department = "Library Services"
    elif any(w in combined for w in ["hostel", "mess", "warden", "curfew", "gate", "room allotment"]):
        category = "Hostel & Facilities"
        department = "Hostel Administration"
    else:
        category = "General Inquiry"
        department = "Student Helpdesk"

    return {
        "priority": priority,
        "priority_name": priority.value,
        "category": category,
        "recommended_department": department,
        "urgency_score": urgency_score,
        "auto_triaged": True,
    }


def create_ticket(
    db: Session,
    user_id: int,
    ticket_in: TicketCreate,
    tenant_id: int = 1,
    enable_auto_triage: bool = True,
) -> Ticket:
    count = db.query(Ticket).filter(Ticket.tenant_id == tenant_id).count()
    code = f"TICK-{tenant_id}-{count + 1001}"

    # Auto-triage if priority or category is default/generic
    triage_info = auto_triage_ticket(ticket_in.title, ticket_in.description)

    priority_enum = triage_info["priority"] if enable_auto_triage else TicketPriority.MEDIUM
    if ticket_in.priority:
        try:
            priority_enum = TicketPriority[ticket_in.priority.upper()]
        except (KeyError, AttributeError):
            pass

    category_final = ticket_in.category
    if not category_final or category_final.lower() in ("it support", "general"):
        category_final = triage_info["category"]

    ticket = Ticket(
        ticket_code=code,
        user_id=user_id,
        tenant_id=tenant_id,
        title=ticket_in.title,
        description=ticket_in.description,
        category=category_final,
        priority=priority_enum,
        assigned_to=triage_info["recommended_department"],
        status=TicketStatus.OPEN,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def get_tickets(
    db: Session,
    user_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    tenant_id: Optional[int] = None,
) -> List[Ticket]:
    query = db.query(Ticket)
    if tenant_id is not None:
        query = query.filter(Ticket.tenant_id == tenant_id)
    if user_id:
        query = query.filter(Ticket.user_id == user_id)
    if status_filter:
        try:
            s_enum = TicketStatus[status_filter.upper()]
            query = query.filter(Ticket.status == s_enum)
        except KeyError:
            pass
    return query.order_by(Ticket.created_at.desc()).offset(skip).limit(limit).all()


def update_ticket(
    db: Session, ticket_id: int, ticket_in: TicketUpdate, tenant_id: Optional[int] = None
) -> Optional[Ticket]:
    query = db.query(Ticket).filter(Ticket.id == ticket_id)
    if tenant_id is not None:
        query = query.filter(Ticket.tenant_id == tenant_id)
    ticket = query.first()
    if not ticket:
        return None

    if ticket_in.status:
        try:
            ticket.status = TicketStatus[ticket_in.status.upper()]
        except KeyError:
            pass
    if ticket_in.priority:
        try:
            ticket.priority = TicketPriority[ticket_in.priority.upper()]
        except KeyError:
            pass
    if ticket_in.assigned_to is not None:
        ticket.assigned_to = ticket_in.assigned_to

    db.commit()
    db.refresh(ticket)
    return ticket


def get_incidents(
    db: Session,
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    tenant_id: Optional[int] = None,
) -> List[Incident]:
    query = db.query(Incident)
    if tenant_id is not None:
        if tenant_id == 1:
            query = query.filter((Incident.tenant_id == 1) | (Incident.tenant_id == None))
        else:
            query = query.filter(Incident.tenant_id == tenant_id)
    if status_filter:
        try:
            i_enum = IncidentStatus[status_filter.upper()]
            query = query.filter(Incident.status == i_enum)
        except KeyError:
            pass
    return query.order_by(Incident.created_at.desc()).offset(skip).limit(limit).all()
