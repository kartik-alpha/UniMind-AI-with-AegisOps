from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.assistant import ChatRequest, ChatResponse, ConversationSchema
from app.services import assistant_service

router = APIRouter(prefix="/assistant", tags=["UniMind AI Assistant"])


@router.post("/chat", response_model=ChatResponse)
def ask_assistant(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Ask UniMind AI Assistant a question. Grounded against official university documents.
    """
    result = assistant_service.process_chat_query(
        db=db,
        user_id=current_user.id,
        user_message=payload.message,
        conversation_id=payload.conversation_id,
        category_filter=payload.category_filter,
        mode=payload.mode or "hybrid",
    )
    return result


@router.get("/conversations", response_model=List[ConversationSchema])
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List user conversation history.
    """
    return assistant_service.get_user_conversations(db=db, user_id=current_user.id)


@router.get("/conversations/{conversation_id}", response_model=ConversationSchema)
def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get full message details for a specific conversation.
    """
    conv = assistant_service.get_conversation_history(
        db=db, conversation_id=conversation_id, user_id=current_user.id
    )
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return conv
