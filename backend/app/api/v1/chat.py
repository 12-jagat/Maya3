"""
Chat & Conversational RAG API Endpoints.
Provides student question answering, conversation thread management,
citation verification, and subsystem readiness checks.
"""

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.config import get_settings
from app.database.supabase_client import get_supabase_client
from app.database.zilliz_client import get_zilliz_client
from app.schemas.chat import (
    ChatHealthResponse,
    ChatMessageRequest,
    ChatMessageResponse,
    ConversationDetail,
    ConversationSummary,
)
from app.services.conversation_service import get_conversation_service
from app.services.embedding_service import get_embedding_service
from app.services.gemini_service import get_gemini_service
from app.services.rag_service import get_rag_service

router = APIRouter(prefix="/chat", tags=["Conversational RAG"])
logger = logging.getLogger("maya.api.chat")
settings = get_settings()


@router.post("/message", response_model=ChatMessageResponse, status_code=status.HTTP_200_OK)
async def post_chat_message(request: ChatMessageRequest):
    """
    Submit a student query to MAYA.
    Executes grounded RAG against indexed GGSIPU notices and returns answer with citations.
    """
    if not request.message or not request.message.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message content cannot be empty.",
        )

    rag_service = get_rag_service()
    try:
        response = await rag_service.answer_question(
            message=request.message,
            conversation_id=request.conversation_id,
            metadata=request.metadata,
        )
        return response
    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while generating the response. Please try again shortly.",
        )


@router.get("/conversations", response_model=List[ConversationSummary])
async def list_conversations(limit: int = Query(default=20, ge=1, le=50)):
    """Fetch recent conversation threads for the user."""
    conv_service = get_conversation_service()
    return await conv_service.list_conversations(limit=limit)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation_detail(conversation_id: str):
    """Fetch an individual conversation thread and its complete ordered messages."""
    conv_service = get_conversation_service()
    conv = await conv_service.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' not found.",
        )

    messages = await conv_service.get_messages(conversation_id)
    return ConversationDetail(
        id=conv["id"],
        title=conv.get("title", "Conversation"),
        created_at=conv.get("created_at", ""),
        updated_at=conv.get("updated_at", ""),
        messages=messages,
    )


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_200_OK)
async def delete_conversation(conversation_id: str):
    """Delete a conversation thread and all associated messages."""
    conv_service = get_conversation_service()
    success = await conv_service.delete_conversation(conversation_id)
    return {"id": conversation_id, "deleted": success}


@router.get("/health", response_model=ChatHealthResponse)
async def get_chat_health():
    """Report health and readiness across all conversational RAG components."""
    gemini = get_gemini_service()
    zilliz = get_zilliz_client()
    supabase = get_supabase_client()
    embedding = get_embedding_service()

    gemini_status = "ready" if gemini.is_configured else "not_configured"
    zilliz_status = "connected" if zilliz.has_credentials else "in_memory_fallback"
    supabase_status = "connected" if supabase.has_credentials else "in_memory_fallback"
    embedding_status = "ready" if embedding._is_loaded else "uninitialized"

    all_ready = bool(gemini.is_configured and embedding._is_loaded)

    return ChatHealthResponse(
        gemini=gemini_status,
        gemini_model=settings.GEMINI_MODEL,
        zilliz=zilliz_status,
        embedding_model=settings.EMBEDDING_MODEL,
        supabase=supabase_status,
        ready=all_ready,
    )


@router.get("/stream")
async def stream_chat_message(
    message: str = Query(..., min_length=1),
    conversation_id: Optional[str] = Query(default=None),
):
    """
    Stream answer tokens progressively via Server-Sent Events (SSE).
    """
    rag_service = get_rag_service()
    return StreamingResponse(
        rag_service.stream_question(message=message, conversation_id=conversation_id),
        media_type="text/event-stream",
    )
