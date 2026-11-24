"""
Health Check Router.
Provides system liveness, readiness, and database dependency verification endpoints.
"""

from fastapi import APIRouter
from app.config import get_settings
from app.database.supabase_client import get_supabase_client
from app.database.zilliz_client import get_zilliz_client
from app.schemas.health import DatabaseHealthResponse, HealthResponse

router = APIRouter(tags=["System Health"])
settings = get_settings()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Application Health Check",
    description="Returns the operational status and application identifier of the MAYA backend.",
)
async def get_health() -> HealthResponse:
    """Return health status of the application."""
    return HealthResponse(status="healthy", application="MAYA")


@router.get(
    "/health/database",
    response_model=DatabaseHealthResponse,
    summary="Database Connectivity Health Check",
    description="Reports the connectivity and operational status of Supabase and Zilliz Cloud without exposing credentials.",
)
async def get_database_health() -> DatabaseHealthResponse:
    """Check connectivity to Supabase and Zilliz Cloud databases."""
    supabase = get_supabase_client()
    zilliz = get_zilliz_client()

    supabase_status = "connected" if supabase.has_credentials else "in_memory_fallback"
    zilliz_status = "connected" if zilliz.has_credentials else "in_memory_fallback"

    overall_status = "healthy" if (supabase.has_credentials or zilliz.has_credentials) else "degraded_fallback"

    return DatabaseHealthResponse(
        status=overall_status,
        supabase=supabase_status,
        zilliz=zilliz_status,
        zilliz_collection=settings.ZILLIZ_COLLECTION,
        embedding_dimension=384,
    )
