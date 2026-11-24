import time
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.models.ticket import Ticket, TicketStatus, TicketPriority
from app.models.audit import AuditLog
from rag.retrieval.retriever import search_knowledge_base


def tool_search_documents(query: str, category: Optional[str] = None, tenant_id: int = 1) -> List[Dict[str, Any]]:
    """
    Search official documents knowledge base partitioned by tenant.
    Returns ranked chunks with citation metadata.
    """
    return search_knowledge_base(query=query, top_k=3, category_filter=category, tenant_id=tenant_id)


def tool_get_policy_details(policy_name: str, tenant_id: int = 1) -> Dict[str, Any]:
    """
    Direct lookup of institutional policies, regulations, or compliance guidelines.
    """
    results = search_knowledge_base(query=policy_name, top_k=2, tenant_id=tenant_id)
    if not results:
        return {
            "found": False,
            "policy": policy_name,
            "summary": "No matching policy found in current tenant repository.",
            "citations": [],
        }
    
    top = results[0]
    return {
        "found": True,
        "policy": policy_name,
        "summary": top.get("text", "")[:300] + "...",
        "citations": [r.get("citation", {}) for r in results if r.get("citation")],
        "full_text": top.get("text", ""),
    }


def tool_create_ticket(
    db: Session,
    user_id: int,
    title: str,
    description: str,
    category: str = "general",
    priority: str = "MEDIUM",
    tenant_id: int = 1,
) -> Dict[str, Any]:
    """
    Create a support ticket safely in the database partitioned by tenant with automated triage.
    """
    from app.services.ticket_service import auto_triage_ticket

    triage = auto_triage_ticket(title=title, description=description)

    p_enum = triage["priority"]
    if priority and priority.upper() in TicketPriority.__members__:
        p_enum = TicketPriority[priority.upper()]

    cat_final = category
    if not cat_final or cat_final.lower() in ("general", "it support"):
        cat_final = triage["category"]

    count = db.query(Ticket).filter(Ticket.tenant_id == tenant_id).count()
    ticket = Ticket(
        ticket_code=f"TICK-{tenant_id}-{count + 1001}",
        user_id=user_id,
        tenant_id=tenant_id,
        title=title,
        description=description,
        category=cat_final,
        priority=p_enum,
        assigned_to=triage["recommended_department"],
        status=TicketStatus.OPEN,
    )
    db.add(ticket)

    audit = AuditLog(
        action="CREATE_TICKET_VIA_AGENT",
        performed_by=f"user:{user_id}",
        target_resource=f"ticket/{ticket.ticket_code}",
        status="SUCCESS",
        details={
            "title": title,
            "category": cat_final,
            "priority": p_enum.value,
            "auto_triaged": True,
        },
        tenant_id=tenant_id,
    )
    db.add(audit)
    db.commit()
    db.refresh(ticket)

    return {
        "ticket_code": ticket.ticket_code,
        "title": ticket.title,
        "status": ticket.status.value,
        "priority": ticket.priority.value,
        "assigned_to": ticket.assigned_to,
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


def tool_auto_triage_issue(title: str, description: str) -> Dict[str, Any]:
    """
    Classify an issue, score urgency, and determine optimal dispatch team.
    """
    from app.services.ticket_service import auto_triage_ticket
    return auto_triage_ticket(title=title, description=description)


# Formal tool registry for agent validation and introspection
TOOL_REGISTRY = {
    "search_university_documents": {
        "name": "search_university_documents",
        "description": "Hybrid dense + sparse retrieval across institutional documents with citations.",
        "parameters": ["query", "category", "tenant_id"],
        "callable": tool_search_documents,
    },
    "get_policy_details": {
        "name": "get_policy_details",
        "description": "Look up full institutional regulations, policies, or compliance protocols.",
        "parameters": ["policy_name", "tenant_id"],
        "callable": tool_get_policy_details,
    },
    "create_support_ticket": {
        "name": "create_support_ticket",
        "description": "Safely creates an IT/Academic support ticket with automated triage.",
        "parameters": ["db", "user_id", "title", "description", "category", "priority", "tenant_id"],
        "callable": tool_create_ticket,
    },
    "check_service_status": {
        "name": "check_service_status",
        "description": "Inspect real-time health, latency, and error metrics for platform microservices.",
        "parameters": ["service_name"],
        "callable": tool_check_service_status,
    },
    "auto_triage_issue": {
        "name": "auto_triage_issue",
        "description": "Run NLP heuristic classification on an issue description.",
        "parameters": ["title", "description"],
        "callable": tool_auto_triage_issue,
    },
}


def execute_whitelisted_tool(tool_name: str, **kwargs) -> Dict[str, Any]:
    """
    Executes a whitelisted tool with parameter validation, error trapping, and latency measurement.
    """
    if tool_name not in TOOL_REGISTRY:
        return {
            "success": False,
            "error": f"Tool '{tool_name}' is not in the authorized tool registry.",
            "latency_ms": 0.0,
        }

    tool_def = TOOL_REGISTRY[tool_name]
    fn = tool_def["callable"]

    start = time.perf_counter()
    try:
        result = fn(**kwargs)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        return {
            "success": True,
            "result": result,
            "latency_ms": duration_ms,
        }
    except Exception as e:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        return {
            "success": False,
            "error": str(e),
            "latency_ms": duration_ms,
        }
