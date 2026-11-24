from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.api.tenant_deps import get_current_tenant
from app.models.organization import Organization
from app.models.user import User
from app.schemas.agent import AgentRunRequest, AgentRunResponse
from ai.agents.unimind_agent import UniMindAgent

router = APIRouter(prefix="/agent", tags=["AI Agent"])


@router.post("/run", response_model=AgentRunResponse)
def run_agent_task(
    payload: AgentRunRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_tenant: Organization = Depends(get_current_tenant),
):
    """
    Run UniMind AI Agent to evaluate prompt, select controlled backend tool, execute action, and return response.
    Scoped by active tenant context.
    """
    agent = UniMindAgent(db=db, user_id=current_user.id, tenant_id=current_tenant.id)
    result = agent.execute_task(prompt=payload.prompt)

    # Stage G1.5: Record Monthly Token Usage for Tenant
    try:
        from app.adapters.factory import AdapterFactory
        prompt_tokens = max(1, len(payload.prompt) // 4)
        resp_text = result.get("agent_response", "") if isinstance(result, dict) else getattr(result, "agent_response", "")
        comp_tokens = max(1, len(resp_text) // 4)
        AdapterFactory.get_cache().record_token_usage(
            tenant_id=current_tenant.id,
            prompt_tokens=prompt_tokens,
            completion_tokens=comp_tokens,
            model_name="unimind-agent",
        )
    except Exception:
        pass

    return result
