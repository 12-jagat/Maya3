"""
Pydantic Schemas for Multimodal Operations (Image, Document, Audio, Voice).
"""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field
from app.schemas.chat import CitationItem


class AttachmentMetadata(BaseModel):
    """Metadata for uploaded media stored securely on backend."""

    id: str = Field(description="Unique attachment UUID")
    filename: str = Field(description="Sanitized display filename")
    file_type: Literal["image", "pdf", "docx", "audio"] = Field(description="Categorized media type")
    size_bytes: int = Field(description="File size in bytes")
    mime_type: str = Field(description="Validated MIME type")
    storage_path: Optional[str] = Field(default=None, description="Internal storage path (scrubbed before sending to client)")
    download_url: Optional[str] = Field(default=None, description="URL to access or preview the file")
    duration_seconds: Optional[float] = Field(default=None, description="Audio duration in seconds if applicable")
    page_count: Optional[int] = Field(default=None, description="Document page count if applicable")


class ImageUnderstandingResult(BaseModel):
    """Structured response from Gemini Image Understanding."""

    extracted_text: str = Field(default="", description="Visible text extracted from image")
    explanation: str = Field(description="Detailed analysis answering the student's question")
    is_university_notice: bool = Field(default=False, description="Whether the image appears to be an official notice")
    identified_dates: List[str] = Field(default_factory=list, description="Key deadlines or dates identified")
    official_verification: Optional[str] = Field(default=None, description="Cross-verification against official notices in RAG")
    citations: List[CitationItem] = Field(default_factory=list, description="Validated official citations if verified")


class DocumentUnderstandingResult(BaseModel):
    """Structured response from Document Understanding (PDF/DOCX)."""

    document_id: str
    filename: str
    page_count: int
    summary: str
    answer: str
    relevant_pages: List[int] = Field(default_factory=list)
    citations: List[CitationItem] = Field(default_factory=list)


class AudioUnderstandingResult(BaseModel):
    """Structured response from Gemini Audio Understanding."""

    transcription: str = Field(description="Verbatim or near-verbatim speech transcription")
    summary: str = Field(description="Concise summary of the spoken audio")
    key_points: List[str] = Field(default_factory=list, description="Key takeaways or instructions")
    answer: Optional[str] = Field(default=None, description="Answer to student's specific question about the audio")
    official_verification: Optional[str] = Field(default=None, description="Cross-check against university notices")


class MultimodalResponse(BaseModel):
    """Unified API response for all multimodal interactions."""

    conversation_id: str
    message_id: str
    role: str = "assistant"
    content: str
    attachment: AttachmentMetadata
    citations: List[CitationItem] = Field(default_factory=list)
    confidence: str = "high"
    insufficient_evidence: bool = False
    created_at: str
    metadata: Optional[Dict[str, Any]] = None
