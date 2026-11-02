from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict


class SourceCitation(BaseModel):
    source_number: int
    title: str
    category: str
    filename: str
    chunk_id: str
    similarity_score: float
    section_heading: Optional[str] = None
    matched_keywords: Optional[List[str]] = None
    rrf_score: Optional[float] = None


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[int] = None
    category_filter: Optional[str] = None
    mode: Optional[str] = "hybrid"


class ChatResponse(BaseModel):
    conversation_id: int
    user_message: str
    bot_answer: str
    sources: List[SourceCitation]
    grounded: bool
    groundedness_score: Optional[float] = 1.0
    retrieval_mode: Optional[str] = "hybrid"
    timestamp: datetime


class MessageSchema(BaseModel):
    id: int
    sender: str
    content: str
    sources: Optional[List[Dict[str, Any]]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationSchema(BaseModel):
    id: int
    session_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[MessageSchema] = []

    model_config = ConfigDict(from_attributes=True)
