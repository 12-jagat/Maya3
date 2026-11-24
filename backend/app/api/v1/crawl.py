"""
MAYA Crawl Operations API.
Provides endpoints to trigger, poll, resume, and view history of notice crawl jobs.
"""

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from app.schemas.crawl import (
    CrawlHistoryResponse,
    CrawlJobStatusResponse,
    CrawlStartRequest,
)
from app.services.crawl_manager import get_crawl_manager

router = APIRouter(prefix="/crawl", tags=["Notice Crawler"])


@router.post(
    "/start",
    response_model=CrawlJobStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start University Notice Crawl",
)
async def start_crawl(
    request: CrawlStartRequest,
    background_tasks: BackgroundTasks,
):
    """
    Trigger an asynchronous crawl of official GGSIPU portals.
    Executes discovery, document download, and 8-process worker execution in background.
    """
    manager = get_crawl_manager()
    try:
        job = await manager.start_crawl(
            sources=request.sources,
            max_pages_per_source=request.max_pages_per_source,
            download_pdfs=request.download_pdfs,
        )

        # Schedule execution in background
        background_tasks.add_task(
            manager.run_crawl_pipeline,
            job_id=job["id"],
            sources=request.sources,
            max_pages_per_source=request.max_pages_per_source,
            download_pdfs=request.download_pdfs,
        )

        return job
    except RuntimeError as err:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(err),
        )


@router.get(
    "/status/{job_id}",
    response_model=CrawlJobStatusResponse,
    summary="Get Crawl Job Status",
)
async def get_crawl_status(job_id: str):
    """Fetch live progress, metrics, and current stage of a crawl job."""
    manager = get_crawl_manager()
    job = await manager.db.get_crawl_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Crawl job '{job_id}' not found.",
        )
    return job


@router.get(
    "/history",
    response_model=CrawlHistoryResponse,
    summary="Get Crawl Job History",
)
async def get_crawl_history():
    """Retrieve historical crawl executions."""
    manager = get_crawl_manager()
    jobs = await manager.db.list_crawl_jobs(limit=15)
    return {"jobs": jobs}


@router.post(
    "/resume/{job_id}",
    response_model=CrawlJobStatusResponse,
    summary="Resume Interrupted Crawl Job",
)
async def resume_crawl(
    job_id: str,
    background_tasks: BackgroundTasks,
):
    """Resume an interrupted or failed crawl job."""
    manager = get_crawl_manager()
    try:
        job = await manager.resume_crawl(job_id)

        background_tasks.add_task(
            manager.run_crawl_pipeline,
            job_id=job["id"],
        )

        return job
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except RuntimeError as err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(err))
