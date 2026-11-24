from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.api.tenant_deps import get_current_tenant
from app.models.organization import Organization
from app.models.user import User
from app.schemas.assistant import ChatRequest, ChatResponse, ConversationSchema
from app.services import assistant_service

router = APIRouter(prefix="/assistant", tags=["UniMind AI Assistant"])


@router.post("/chat", response_model=ChatResponse)
def ask_assistant(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_tenant: Organization = Depends(get_current_tenant),
):
    """
    Ask AI Assistant a question. Grounded against official tenant documents.
    """
    result = assistant_service.process_chat_query(
        db=db,
        user_id=current_user.id,
        user_message=payload.message,
        conversation_id=payload.conversation_id,
        category_filter=payload.category_filter,
        mode=payload.mode or "hybrid",
        tenant_id=current_tenant.id,
    )
    return result


@router.post("/chat/stream")
def stream_assistant_chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_tenant: Organization = Depends(get_current_tenant),
):
    """
    Real-time Server-Sent Events (SSE) token streaming for UniMind AI Assistant.
    Yields data frames with token chunks and terminal metadata object.
    """
    generator = assistant_service.stream_chat_query(
        db=db,
        user_id=current_user.id,
        user_message=payload.message,
        conversation_id=payload.conversation_id,
        category_filter=payload.category_filter,
        mode=payload.mode or "hybrid",
        tenant_id=current_tenant.id,
    )
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/conversations", response_model=List[ConversationSchema])
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_tenant: Organization = Depends(get_current_tenant),
):
    """
    List user conversation history within current tenant.
    """
    return assistant_service.get_user_conversations(
        db=db, user_id=current_user.id, tenant_id=current_tenant.id
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationSchema)
def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_tenant: Organization = Depends(get_current_tenant),
):
    """
    Get full message details for a specific conversation within current tenant.
    """
    conv = assistant_service.get_conversation_history(
        db=db, conversation_id=conversation_id, user_id=current_user.id, tenant_id=current_tenant.id
    )
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return conv
