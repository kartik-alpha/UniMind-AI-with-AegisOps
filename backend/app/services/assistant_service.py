from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.models.conversation import Conversation, Message
from rag.retrieval.retriever import search_knowledge_base
from ai.llm.llm_client import generate_llm_response

RELEVANCE_THRESHOLD = 0.40  # Minimum similarity threshold for grounded RAG matching


def process_chat_query(
    db: Session,
    user_id: int,
    user_message: str,
    conversation_id: Optional[int] = None,
    category_filter: Optional[str] = None,
    mode: str = "hybrid",
) -> Dict[str, Any]:
    # 1. Get or Create Conversation
    if conversation_id:
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id, Conversation.user_id == user_id
        ).first()
        if not conversation:
            conversation = Conversation(user_id=user_id, title=user_message[:40])
            db.add(conversation)
            db.commit()
            db.refresh(conversation)
    else:
        conversation = Conversation(user_id=user_id, title=user_message[:40])
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    # 2. Retrieve Relevant Context Chunks from RAG using selected retrieval mode
    retrieved_chunks = search_knowledge_base(
        query=user_message,
        top_k=4,
        category_filter=category_filter,
        mode=mode,
        use_expansion=True,
    )

    # 3. Filter by relevance threshold
    valid_chunks = [c for c in retrieved_chunks if c.get("similarity_score", 0.0) >= RELEVANCE_THRESHOLD]

    # 4. Generate LLM Grounded Answer
    llm_output = generate_llm_response(query=user_message, context_chunks=valid_chunks)

    # 5. Save User Message & Bot Response to Database
    msg_user = Message(
        conversation_id=conversation.id,
        sender="user",
        content=user_message,
    )
    msg_bot = Message(
        conversation_id=conversation.id,
        sender="assistant",
        content=llm_output["answer"],
        sources=llm_output["sources"],
    )
    db.add_all([msg_user, msg_bot])
    conversation.updated_at = datetime.utcnow()
    db.commit()

    return {
        "conversation_id": conversation.id,
        "user_message": user_message,
        "bot_answer": llm_output["answer"],
        "sources": llm_output["sources"],
        "grounded": llm_output["grounded"],
        "groundedness_score": llm_output.get("groundedness_score", 1.0),
        "retrieval_mode": mode,
        "timestamp": msg_bot.created_at,
    }


def get_user_conversations(db: Session, user_id: int) -> List[Conversation]:
    return (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )


def get_conversation_history(db: Session, conversation_id: int, user_id: int) -> Optional[Conversation]:
    return (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == user_id)
        .first()
    )
