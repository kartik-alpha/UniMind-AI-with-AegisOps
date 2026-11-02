from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_roles
from app.models.user import User, UserRole
from app.schemas.ticket import (
    TicketCreate,
    TicketUpdate,
    TicketResponse,
    IncidentResponse,
)
from app.services import ticket_service

router = APIRouter(tags=["Tickets & Incidents"])


@router.post("/tickets", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
def create_new_ticket(
    payload: TicketCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Submit a support ticket.
    """
    return ticket_service.create_ticket(db=db, user_id=current_user.id, ticket_in=payload)


@router.get("/tickets", response_model=List[TicketResponse])
def list_tickets(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List tickets. Students see their own tickets; Admin/Faculty see all tickets.
    """
    user_id = None if current_user.role in (UserRole.ADMIN, UserRole.FACULTY) else current_user.id
    return ticket_service.get_tickets(db=db, user_id=user_id, status_filter=status_filter)


@router.patch("/tickets/{ticket_id}", response_model=TicketResponse)
def update_ticket_status(
    ticket_id: int,
    payload: TicketUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.FACULTY)),
):
    """
    Update ticket status, priority, or assigned handler. Restricted to ADMIN and FACULTY.
    """
    ticket = ticket_service.update_ticket(db=db, ticket_id=ticket_id, ticket_in=payload)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} not found.",
        )
    return ticket


@router.get("/incidents", response_model=List[IncidentResponse])
def list_incidents(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List AegisOps IT infrastructure incidents.
    """
    return ticket_service.get_incidents(db=db, status_filter=status_filter)
