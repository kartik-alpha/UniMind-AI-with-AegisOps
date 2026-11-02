from typing import List, Optional
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


def create_ticket(db: Session, user_id: int, ticket_in: TicketCreate) -> Ticket:
    count = db.query(Ticket).count()
    code = f"TICK-{count + 1001}"

    priority_enum = TicketPriority.MEDIUM
    try:
        priority_enum = TicketPriority[ticket_in.priority.upper()]
    except (KeyError, AttributeError):
        pass

    ticket = Ticket(
        ticket_code=code,
        user_id=user_id,
        title=ticket_in.title,
        description=ticket_in.description,
        category=ticket_in.category,
        priority=priority_enum,
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
) -> List[Ticket]:
    query = db.query(Ticket)
    if user_id:
        query = query.filter(Ticket.user_id == user_id)
    if status_filter:
        try:
            s_enum = TicketStatus[status_filter.upper()]
            query = query.filter(Ticket.status == s_enum)
        except KeyError:
            pass
    return query.order_by(Ticket.created_at.desc()).offset(skip).limit(limit).all()


def update_ticket(db: Session, ticket_id: int, ticket_in: TicketUpdate) -> Optional[Ticket]:
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
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
    db: Session, status_filter: Optional[str] = None, skip: int = 0, limit: int = 100
) -> List[Incident]:
    query = db.query(Incident)
    if status_filter:
        try:
            i_enum = IncidentStatus[status_filter.upper()]
            query = query.filter(Incident.status == i_enum)
        except KeyError:
            pass
    return query.order_by(Incident.created_at.desc()).offset(skip).limit(limit).all()
