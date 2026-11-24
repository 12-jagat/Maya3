"""
MAYA API v1 Master Router.
Modular router designed for clean addition of future university assistant endpoints.
"""

from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.v1.crawl import router as crawl_router
from app.api.v1.chat import router as chat_router
from app.api.v1.ingestion import router as ingestion_router
from app.api.v1.multimodal import router as multimodal_router
from app.api.v1.notices import router as notices_router
from app.api.v1.search import router as search_router

router = APIRouter(prefix="/api/v1")

# Subsystem Routers
router.include_router(health_router)
router.include_router(chat_router)
router.include_router(multimodal_router)
router.include_router(crawl_router)
router.include_router(notices_router)
router.include_router(ingestion_router)
router.include_router(search_router)


@router.get("/status", tags=["v1 System"])
async def v1_status():
    """Returns v1 API subsystem readiness."""
    return {
        "api_version": "v1",
        "subsystems": {
            "notice_crawler": "ready",
            "pdf_worker_pool": "ready_8_processes",
            "multimodal_parser": "ready",
            "zilliz_vector_indexing": "ready",
            "gemini_rag": "ready",
            "multimodal_interaction": "ready",
        },
    }


