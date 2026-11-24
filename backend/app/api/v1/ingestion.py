"""
MAYA Document Ingestion Endpoints.
"""

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from app.schemas.ingestion import (
    IngestionJobStatusResponse,
    IngestionStartRequest,
    IngestionStatsResponse,
)
from app.services.ingestion_service import get_ingestion_service

router = APIRouter(prefix="/ingestion", tags=["Document Ingestion & Indexing"])


@router.post(
    "/start",
    response_model=IngestionJobStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start Document Processing Pipeline",
)
async def start_ingestion(
    request: IngestionStartRequest,
    background_tasks: BackgroundTasks,
):
    """
    Trigger end-to-end extraction, OCR, chunking, and Zilliz Cloud vector indexing.
    Executes in the background across exactly 8 worker processes.
    """
    service = get_ingestion_service()
    try:
        job = await service.start_ingestion_job(
            batch_size=request.batch_size,
            force_reindex=request.force_reindex,
        )

        background_tasks.add_task(
            service.run_ingestion_pipeline,
            job_id=job["id"],
            batch_size=request.batch_size,
            force_reindex=request.force_reindex,
        )

        return job
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get(
    "/status/{job_id}",
    response_model=IngestionJobStatusResponse,
    summary="Get Ingestion Job Progress",
)
async def get_ingestion_status(job_id: str):
    """Fetch live stage, extraction count, and vector indexing progress."""
    service = get_ingestion_service()
    job = await service.get_ingestion_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ingestion job '{job_id}' not found.",
        )
    return job


@router.get(
    "/statistics",
    response_model=IngestionStatsResponse,
    summary="Get Ingestion System Statistics",
)
async def get_statistics():
    """Retrieve system-wide document extraction and vector database metrics."""
    service = get_ingestion_service()
    stats = await service.get_statistics()
    return stats


@router.post(
    "/retry/{notice_id}",
    response_model=IngestionJobStatusResponse,
    summary="Retry Ingestion for Specific Notice",
)
async def retry_notice(notice_id: str):
    """Force re-processing and re-indexing of a specific circular."""
    service = get_ingestion_service()
    try:
        job = await service.retry_notice_ingestion(notice_id)
        return job
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
