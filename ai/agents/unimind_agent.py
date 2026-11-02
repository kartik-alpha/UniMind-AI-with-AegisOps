from typing import Dict, Any, List
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from ai.agents.agent_tools import (
    tool_search_documents,
    tool_create_ticket,
    tool_check_service_status,
)


class UniMindAgent:
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id

    def execute_task(self, prompt: str) -> Dict[str, Any]:
        p_lower = prompt.lower()
        tool_used = None
        result_payload = None

        # 1. Ticket creation intent
        if "ticket" in p_lower or "issue" in p_lower or "complain" in p_lower or "report problem" in p_lower:
            tool_used = "create_support_ticket"
            result_payload = tool_create_ticket(
                db=self.db,
                user_id=self.user_id,
                title=f"Support Request: {prompt[:30]}",
                description=prompt,
            )
            response_text = f"Support ticket successfully created! Ticket Code: {result_payload['ticket_code']}. Our operations team has been notified."

        # 2. Service status intent
        elif "status" in p_lower or "down" in p_lower or "lms" in p_lower or "portal" in p_lower or "exam service" in p_lower:
            tool_used = "check_service_status"
            service_name = "exam_service" if "exam" in p_lower else ("lms" if "lms" in p_lower else "student_portal")
            result_payload = tool_check_service_status(service_name)
            response_text = f"Service Status for {result_payload['service']}: {result_payload['status']}. Latency: {result_payload['latency_ms']}ms, Error Rate: {result_payload['error_rate']}%."

        # 3. Document knowledge search intent
        else:
            tool_used = "search_university_documents"
            retrieved = tool_search_documents(query=prompt)
            result_payload = retrieved
            if retrieved:
                lines = [r["text"] for r in retrieved]
                response_text = "Based on university document retrieval:\n\n" + "\n".join(lines)
            else:
                response_text = "Information not found in the university knowledge base."

        # Record Agent Execution Audit Log
        audit = AuditLog(
            action="AGENT_EXECUTION",
            performed_by=f"user:{self.user_id}",
            target_resource=f"tool/{tool_used}",
            status="SUCCESS",
            details={"prompt": prompt, "tool_used": tool_used},
        )
        self.db.add(audit)
        self.db.commit()

        return {
            "prompt": prompt,
            "tool_used": tool_used,
            "agent_response": response_text,
            "tool_output": result_payload,
        }
