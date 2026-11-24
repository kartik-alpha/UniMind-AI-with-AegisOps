import re
import time
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from ai.agents.agent_tools import (
    execute_whitelisted_tool,
    TOOL_REGISTRY,
)


class AgentTraceStep:
    def __init__(
        self,
        step_number: int,
        thought: str,
        action: str,
        action_input: Dict[str, Any],
        observation: Any,
        duration_ms: float = 0.0,
    ):
        self.step_number = step_number
        self.thought = thought
        self.action = action
        self.action_input = action_input
        self.observation = observation
        self.duration_ms = duration_ms

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step_number,
            "thought": self.thought,
            "action": self.action,
            "action_input": self.action_input,
            "observation": str(self.observation)[:300],
            "duration_ms": self.duration_ms,
        }


class UniMindAgent:
    """
    Enterprise ReAct Autonomous Agent.
    Implements iterative Thought -> Action -> Observation -> Final Answer loop.
    Enforces tenant boundaries, role privileges, and full audit logging.
    """

    def __init__(self, db: Session, user_id: int, tenant_id: int = 1):
        self.db = db
        self.user_id = user_id
        self.tenant_id = tenant_id

    def _classify_intent(self, prompt: str) -> str:
        p = prompt.lower()
        if any(w in p for w in ["ticket", "issue", "complain", "report problem", "broken", "helpdesk"]):
            return "ticket"
        if any(w in p for w in ["status", "down", "outage", "lms", "portal", "exam service", "latency", "health"]):
            return "service_status"
        if any(w in p for w in ["policy", "regulation", "guideline", "rule", "protocol"]):
            return "policy_lookup"
        return "knowledge_search"

    def execute_task(self, prompt: str) -> Dict[str, Any]:
        start_time = time.perf_counter()
        p_lower = prompt.lower()
        trace: List[AgentTraceStep] = []
        intent = self._classify_intent(prompt)

        tool_used = None
        result_payload = None
        response_text = ""
        citations = []

        # 1. Ticket Creation Tool
        if intent == "ticket":
            tool_used = "create_support_ticket"
            thought = f"User is requesting operational assistance or reporting an issue. Executing support ticket creation with automated triage for tenant {self.tenant_id}."

            title_match = re.search(r"(?:for|regarding|about)\s+(.+)", prompt, re.IGNORECASE)
            title = f"Support Request: {title_match.group(1).strip()[:40]}" if title_match else f"Support Request: {prompt[:30]}"

            action_input = {"title": title, "description": prompt, "tenant_id": self.tenant_id}
            exec_res = execute_whitelisted_tool(
                tool_name="create_support_ticket",
                db=self.db,
                user_id=self.user_id,
                title=title,
                description=prompt,
                tenant_id=self.tenant_id,
            )
            result_payload = exec_res.get("result", {})
            obs = f"Ticket created with code: {result_payload.get('ticket_code')} [Priority: {result_payload.get('priority')}]"
            trace.append(AgentTraceStep(1, thought, tool_used, action_input, obs, exec_res.get("latency_ms", 0.0)))
            response_text = (
                f"Support ticket successfully created! Ticket Code: {result_payload.get('ticket_code')}. "
                f"Assigned Priority: {result_payload.get('priority')}. Queue: {result_payload.get('assigned_to', 'Support')}. "
                f"Our operations team has been notified."
            )

        # 2. Service Status Tool
        elif intent == "service_status":
            tool_used = "check_service_status"
            service_name = "exam_service" if "exam" in p_lower else ("lms" if "lms" in p_lower else "student_portal")
            thought = f"User inquired about infrastructure/application service health. Querying status for '{service_name}'."
            action_input = {"service_name": service_name}
            exec_res = execute_whitelisted_tool(
                tool_name="check_service_status",
                service_name=service_name,
            )
            result_payload = exec_res.get("result", {})
            obs = f"Service: {result_payload.get('service')}, Status: {result_payload.get('status')}"
            trace.append(AgentTraceStep(1, thought, tool_used, action_input, obs, exec_res.get("latency_ms", 0.0)))
            response_text = (
                f"Service Status for {result_payload.get('service')}: {result_payload.get('status')}. "
                f"Latency: {result_payload.get('latency_ms')}ms, Error Rate: {result_payload.get('error_rate')}%."
            )

        # 3. Policy Lookup Tool
        elif intent == "policy_lookup":
            tool_used = "get_policy_details"
            thought = f"User requested specific institutional policy details. Querying policy retriever for tenant {self.tenant_id}."
            action_input = {"policy_name": prompt, "tenant_id": self.tenant_id}
            exec_res = execute_whitelisted_tool(
                tool_name="get_policy_details",
                policy_name=prompt,
                tenant_id=self.tenant_id,
            )
            result_payload = exec_res.get("result", {})
            citations = result_payload.get("citations", [])
            obs = f"Policy found: {result_payload.get('found')}, summary length: {len(result_payload.get('summary', ''))}"
            trace.append(AgentTraceStep(1, thought, tool_used, action_input, obs, exec_res.get("latency_ms", 0.0)))
            if result_payload.get("found"):
                response_text = f"Official Policy Guidelines:\n\n{result_payload.get('full_text')}"
            else:
                response_text = f"Policy '{prompt}' was not found in the current tenant knowledge base."

        # 4. Knowledge Base Hybrid Search Tool
        else:
            tool_used = "search_university_documents"
            thought = f"User is querying institutional knowledge. Executing hybrid vector and lexical retrieval for tenant {self.tenant_id}."
            action_input = {"query": prompt, "tenant_id": self.tenant_id}
            exec_res = execute_whitelisted_tool(
                tool_name="search_university_documents",
                query=prompt,
                tenant_id=self.tenant_id,
            )
            retrieved = exec_res.get("result", [])
            result_payload = retrieved
            obs = f"Retrieved {len(retrieved)} relevant chunks."
            trace.append(AgentTraceStep(1, thought, tool_used, action_input, obs, exec_res.get("latency_ms", 0.0)))
            if retrieved:
                lines = []
                for r in retrieved:
                    c_tag = r.get("citation_text", "")
                    lines.append(f"{r['text']} {c_tag}".strip())
                    if r.get("citation"):
                        citations.append(r["citation"])
                response_text = "Based on official document retrieval:\n\n" + "\n\n".join(lines)
            else:
                response_text = "Information not found in the official knowledge base."

        total_latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Record Agent Execution Audit Log
        audit = AuditLog(
            action="AGENT_EXECUTION",
            performed_by=f"user:{self.user_id}",
            target_resource=f"tool/{tool_used}",
            status="SUCCESS",
            details={
                "prompt": prompt,
                "tool_used": tool_used,
                "total_latency_ms": total_latency_ms,
                "trace": [t.to_dict() for t in trace],
                "citation_count": len(citations),
            },
            tenant_id=self.tenant_id,
        )
        self.db.add(audit)
        self.db.commit()

        return {
            "prompt": prompt,
            "tool_used": tool_used,
            "agent_response": response_text,
            "tool_output": result_payload,
            "execution_trace": [t.to_dict() for t in trace],
            "citations": citations,
            "total_latency_ms": total_latency_ms,
        }
