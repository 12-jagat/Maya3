"""
Pydantic Schemas for Notice Operations.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class NoticeResponse(BaseModel):
    id: str = Field(description="Unique notice identifier")
    title: str = Field(description="Official notice headline")
    content: Optional[str] = Field(default="", description="Notice body text context")
    source_url: str = Field(description="Primary university URL")
    pdf_url: Optional[str] = Field(default=None, description="Direct URL to official PDF document")
    category: str = Field(default="General", description="Academic or administrative category")
    published_date: Optional[str] = Field(default=None, description="Extracted circular date")
    processing_status: str = Field(default="pending", description="Processing lifecycle state")
    content_hash: Optional[str] = Field(default=None, description="SHA-256 fingerprint")
    scraped_at: Optional[str] = Field(default=None, description="Timestamp of ingestion")
    indexed_at: Optional[str] = Field(default=None, description="Timestamp of vector indexing")


class NoticeListResponse(BaseModel):
    items: List[NoticeResponse]
    total: int
    skip: int
    limit: int
