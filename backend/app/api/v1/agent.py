from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.agent import AgentRunRequest, AgentRunResponse
from ai.agents.unimind_agent import UniMindAgent

router = APIRouter(prefix="/agent", tags=["AI Agent"])


@router.post("/run", response_model=AgentRunResponse)
def run_agent_task(
    payload: AgentRunRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Run UniMind AI Agent to evaluate prompt, select controlled backend tool, execute action, and return response.
    """
    agent = UniMindAgent(db=db, user_id=current_user.id)
    result = agent.execute_task(prompt=payload.prompt)
    return result
