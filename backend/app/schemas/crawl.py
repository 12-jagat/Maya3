"""
Pydantic Schemas for Crawl Operations.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CrawlStartRequest(BaseModel):
    sources: Optional[List[str]] = Field(default=None, description="Custom list of official sources")
    max_pages_per_source: int = Field(default=20, ge=1, le=100, description="Page limit per source")
    download_pdfs: bool = Field(default=True, description="Whether to download discovered PDFs")


class CrawlJobStatusResponse(BaseModel):
    id: str
    status: str
    current_stage: Optional[str] = None
    current_source: Optional[str] = None
    pages_discovered: int = 0
    pages_processed: int = 0
    notices_discovered: int = 0
    new_notices: int = 0
    updated_notices: int = 0
    skipped_notices: int = 0
    pdfs_downloaded: int = 0
    pdfs_failed: int = 0
    last_processed_url: Optional[str] = None
    errors: List[str] = Field(default_factory=list)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class CrawlHistoryResponse(BaseModel):
    jobs: List[CrawlJobStatusResponse]
