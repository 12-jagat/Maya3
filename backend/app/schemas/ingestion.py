"""
Pydantic Schemas for Document Ingestion Operations.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class IngestionStartRequest(BaseModel):
    batch_size: int = Field(default=10, ge=1, le=100, description="Max documents to process in this run")
    force_reindex: bool = Field(default=False, description="Re-process even if previously indexed")
    force_reprocess: Optional[bool] = Field(default=None, description="Alias for force_reindex")

    def model_post_init(self, __context):
        if self.force_reprocess is not None:
            self.force_reindex = self.force_reprocess


class IngestionJobStatusResponse(BaseModel):
    id: str
    status: str
    current_stage: str
    total_documents: int
    processed_documents: int
    extracted_documents: int
    ocr_pages_processed: int
    chunks_created: int
    vectors_indexed: int
    failed_documents: int
    errors: List[str] = Field(default_factory=list)
    started_at: str
    completed_at: Optional[str] = None


class IngestionStatsResponse(BaseModel):
    total_notices: int
    downloaded: int
    extracted: int
    ocr_processed: int
    indexed: int
    failed: int
    pending: int
    worker_count: int = 8
    total_indexed_chunks: int = 0
