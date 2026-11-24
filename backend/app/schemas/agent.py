from typing import Dict, Any, Optional, List
from pydantic import BaseModel


class AgentRunRequest(BaseModel):
    prompt: str


class AgentRunResponse(BaseModel):
    prompt: str
    tool_used: str
    agent_response: str
    tool_output: Optional[Any] = None
    execution_trace: Optional[List[Dict[str, Any]]] = None
    citations: Optional[List[Dict[str, Any]]] = None
    total_latency_ms: Optional[float] = None
