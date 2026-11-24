"""
MAYA Backend Entrypoint.
Initializes FastAPI application, middleware, centralized error handlers, and routers.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.health import router as health_router
from app.api.v1.router import router as v1_router
from app.config import get_settings
from app.services.pdf_worker_pool import get_pdf_worker_pool
from app.utils.errors import (
    MayaBaseException,
    http_exception_handler,
    maya_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.utils.logger import logger

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown lifecycle events."""
    logger.info(f"Starting {settings.APP_NAME} backend in '{settings.APP_ENV}' mode...")
    logger.info(f"Configured CORS origins: {settings.cors_origins}")
    logger.info(f"Configured PDF Worker Processes: {settings.PDF_WORKERS}")
    yield
    logger.info(f"Shutting down {settings.APP_NAME} backend...")
    get_pdf_worker_pool().shutdown(wait=False)



def create_application() -> FastAPI:
    """Application factory for MAYA."""
    app = FastAPI(
        title="MAYA Backend API",
        description="Multimodal AI-Powered University Assistant for GGSIPU",
        version="0.1.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # Configure Cross-Origin Resource Sharing (CORS) with Vercel preview and local dev support
    origins = settings.cors_origins
    allow_all = "*" in origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if allow_all else origins,
        allow_origin_regex=r"^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$|^https:\/\/.*\.vercel\.app$" if not allow_all else None,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    # Register centralized exception handlers
    app.add_exception_handler(MayaBaseException, maya_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # Register API routers
    # Root level health endpoint matching exact specification: GET /health
    app.include_router(health_router)
    app.include_router(v1_router)

    return app


app = create_application()
