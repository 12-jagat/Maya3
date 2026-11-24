"""
Pydantic Schemas for Conversational RAG Operations.
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class CitationItem(BaseModel):
    """Structured verifiable citation linking directly to official university circular."""

    source_id: str = Field(description="Internal source tag, e.g. SOURCE_1")
    notice_id: str = Field(description="Unique notice identifier")
    title: str = Field(description="Official title of the circular or document")
    source_url: str = Field(description="Official university portal URL")
    pdf_url: Optional[str] = Field(default=None, description="Direct download URL for document PDF")
    page_number: Optional[int] = Field(default=1, description="Page number containing the supporting evidence")
    relevant_excerpt: str = Field(default="", description="Verbatim or summarized supporting evidence from document")


class RAGGenerationOutput(BaseModel):
    """Raw structured output schema enforced on Gemini response generation."""

    answer: str = Field(description="Factual, student-friendly answer grounded strictly in retrieved sources")
    citations: List[CitationItem] = Field(default_factory=list, description="List of validated supporting citations")
    confidence: Literal["high", "medium", "low"] = Field(default="high", description="Estimated confidence level")
    insufficient_evidence: bool = Field(
        default=False,
        description="True if available sources lack sufficient evidence to fully verify the answer",
    )


class ChatMessageRequest(BaseModel):
    """Request payload sent by student when submitting a question."""

    message: str = Field(min_length=1, max_length=4000, description="Natural-language question or follow-up prompt")
    conversation_id: Optional[str] = Field(default=None, description="Active conversation UUID, or None for new thread")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional user/session metadata")


class ChatMessageResponse(BaseModel):
    """Complete assistant response payload returned to frontend."""

    conversation_id: str
    message_id: str
    role: str = "assistant"
    content: str
    citations: List[CitationItem] = Field(default_factory=list)
    confidence: str = "high"
    insufficient_evidence: bool = False
    created_at: str


class ConversationSummary(BaseModel):
    """Summary record for conversation list in sidebar."""

    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int = 0


class ConversationDetail(BaseModel):
    """Detailed conversation object including ordered messages."""

    id: str
    title: str
    created_at: str
    updated_at: str
    messages: List[Dict[str, Any]] = Field(default_factory=list)


class ChatHealthResponse(BaseModel):
    """Status report of all RAG subsystems."""

    gemini: str
    gemini_model: str
    zilliz: str
    embedding_model: str
    supabase: str
    ready: bool
