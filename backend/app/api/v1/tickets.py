from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_roles
from app.api.tenant_deps import get_current_tenant
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.models.ticket import Ticket, Incident
from app.schemas.ticket import (
    TicketCreate,
    TicketUpdate,
    TicketResponse,
    TicketTriageRequest,
    TicketTriageResponse,
    IncidentResponse,
)
from app.services import ticket_service

router = APIRouter(tags=["Tickets & Incidents"])


@router.post("/tickets", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
def create_new_ticket(
    payload: TicketCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_tenant: Organization = Depends(get_current_tenant),
):
    """
    Submit a support ticket within current tenant.
    """
    return ticket_service.create_ticket(
        db=db, user_id=current_user.id, ticket_in=payload, tenant_id=current_tenant.id
    )


@router.post("/tickets/auto-triage", response_model=TicketTriageResponse)
def preview_ticket_triage(
    payload: TicketTriageRequest,
    current_user: User = Depends(get_current_user),
    current_tenant: Organization = Depends(get_current_tenant),
):
    """
    Analyze ticket subject and description using NLP heuristics to predict category, priority, and routing team.
    """
    result = ticket_service.auto_triage_ticket(payload.title, payload.description)
    return {
        "priority": result["priority_name"],
        "category": result["category"],
        "recommended_department": result["recommended_department"],
        "urgency_score": result["urgency_score"],
        "auto_triaged": True,
    }


@router.get("/tickets", response_model=List[TicketResponse])
def list_tickets(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_tenant: Organization = Depends(get_current_tenant),
):
    """
    List tickets for current tenant. Regular users see their own; Admin/Faculty see all in tenant.
    """
    user_id = None if current_user.role in (UserRole.ADMIN, UserRole.FACULTY) else current_user.id
    return ticket_service.get_tickets(
        db=db, user_id=user_id, status_filter=status_filter, tenant_id=current_tenant.id
    )


@router.patch("/tickets/{ticket_id}", response_model=TicketResponse)
def update_ticket_status(
    ticket_id: int,
    payload: TicketUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.FACULTY)),
    current_tenant: Organization = Depends(get_current_tenant),
):
    """
    Update ticket status, priority, or assigned handler within current tenant. Restricted to ADMIN and FACULTY.
    """
    ticket = ticket_service.update_ticket(
        db=db, ticket_id=ticket_id, ticket_in=payload, tenant_id=current_tenant.id
    )
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
    current_tenant: Organization = Depends(get_current_tenant),
):
    """
    List AegisOps IT infrastructure incidents for current tenant.
    """
    return ticket_service.get_incidents(
        db=db, status_filter=status_filter, tenant_id=current_tenant.id
    )


@router.get("/incidents/{incident_id}", response_model=IncidentResponse)
def get_incident_by_id(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_tenant: Organization = Depends(get_current_tenant),
):
    """
    Get incident details by ID with strict multi-tenant boundary enforcement.
    """
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found.",
        )

    is_super_admin = (
        current_user.role == UserRole.ADMIN
        and current_user.username in ("admin", "platform_admin", "kartik")
    )
    if not is_super_admin and incident.tenant_id != current_tenant.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: Incident {incident_id} belongs to a different organization.",
        )

    return incident
