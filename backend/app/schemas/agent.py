from typing import Dict, Any, Optional
from pydantic import BaseModel


class AgentRunRequest(BaseModel):
    prompt: str


class AgentRunResponse(BaseModel):
    prompt: str
    tool_used: str
    agent_response: str
    tool_output: Optional[Any] = None
