"""
Pydantic Schemas for Semantic Vector Search.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SemanticSearchRequest(BaseModel):
    query: str = Field(min_length=2, description="Natural-language question or search phrase")
    top_k: int = Field(default=5, ge=1, le=20, description="Maximum number of nearest chunks to return")
    threshold: float = Field(default=0.15, ge=0.0, le=1.0, description="Cosine similarity threshold filter")
    category: Optional[str] = Field(default=None, description="Optional category filter (Examinations, Admissions, etc.)")


class SemanticChunkResult(BaseModel):
    id: str
    notice_id: str
    chunk_index: int
    title: str
    content: str
    source_url: str
    pdf_url: Optional[str] = None
    page_number: Optional[int] = None
    category: Optional[str] = None
    published_date: Optional[str] = None
    score: float


class SemanticSearchResponse(BaseModel):
    query: str
    results_count: int
    top_k: int
    results: List[SemanticChunkResult]
