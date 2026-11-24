"""
Health check response schemas.
"""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check endpoint response schema."""

    status: str = Field(default="healthy", description="Service health status indicator")
    application: str = Field(default="MAYA", description="Application identity")


class DatabaseHealthResponse(BaseModel):
    """Database connectivity health check response schema."""

    status: str = Field(default="healthy", description="Overall database health status")
    supabase: str = Field(description="Supabase PostgreSQL connectivity status")
    zilliz: str = Field(description="Zilliz Cloud vector store status")
    zilliz_collection: str = Field(description="Configured vector collection name")
    embedding_dimension: int = Field(default=384, description="Dense vector dimensions")
