"""
MAYA Notice Retrieval Endpoints.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.database.supabase_client import get_supabase_client
from app.schemas.notice import NoticeListResponse, NoticeResponse

router = APIRouter(prefix="/notices", tags=["University Notices"])


@router.get("", response_model=NoticeListResponse, summary="List Notices")
async def list_notices(
    skip: int = Query(0, ge=0, description="Offset records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Page size limit"),
    category: Optional[str] = Query(None, description="Filter by category (Examinations, Admissions, etc.)"),
    search: Optional[str] = Query(None, description="Search term for title or text"),
):
    """Retrieve paginated university notices with optional search and category filters."""
    db = get_supabase_client()
    result = await db.list_notices(skip=skip, limit=limit, category=category, search=search)
    return result


@router.get("/latest", response_model=NoticeListResponse, summary="Get Latest University Notices")
async def get_latest_notices(
    limit: int = Query(10, ge=1, le=50, description="Number of recent notices"),
):
    """Retrieve the most recently published official circulars."""
    db = get_supabase_client()
    result = await db.list_notices(skip=0, limit=limit)
    return result


@router.get("/{notice_id}", response_model=NoticeResponse, summary="Get Notice Details")
async def get_notice_by_id(notice_id: str):
    """Retrieve single notice by its unique ID or source URL hash."""
    db = get_supabase_client()
    # Search in memory or DB
    all_notices = await db.list_notices(limit=500)
    for n in all_notices["items"]:
        if n.get("id") == notice_id or n.get("source_url") == notice_id:
            return n

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Notice with ID '{notice_id}' not found.",
    )
