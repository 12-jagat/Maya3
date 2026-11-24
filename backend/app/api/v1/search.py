"""
MAYA Semantic Vector Search Endpoints.
Performs dense vector retrieval against Zilliz Cloud using local embeddings.
"""

from fastapi import APIRouter, HTTPException, status

from app.database.zilliz_client import get_zilliz_client
from app.schemas.search import (
    SemanticChunkResult,
    SemanticSearchRequest,
    SemanticSearchResponse,
)
from app.services.embedding_service import get_embedding_service

router = APIRouter(prefix="/search", tags=["Semantic Vector Search"])


@router.post(
    "/semantic",
    response_model=SemanticSearchResponse,
    summary="Semantic Vector Search for University Notices",
)
async def semantic_search(request: SemanticSearchRequest):
    """
    Search official university circular chunks using natural language questions.
    Generates local 384-dimensional query embedding and runs cosine similarity search in Zilliz.
    """
    embedder = get_embedding_service()
    zilliz = get_zilliz_client()

    try:
        # 1. Generate local query embedding vector (dim=384, normalized)
        query_vector = embedder.generate_query_embedding(request.query)

        # 2. Build category filter if requested
        filter_expr = f"category == '{request.category}'" if request.category else None

        # 3. Query Zilliz Cloud collection
        raw_results = await zilliz.semantic_search(
            query_vector=query_vector,
            top_k=request.top_k,
            threshold=request.threshold,
            filter_expr=filter_expr,
        )

        typed_results = [SemanticChunkResult(**item) for item in raw_results]

        return SemanticSearchResponse(
            query=request.query,
            results_count=len(typed_results),
            top_k=request.top_k,
            results=typed_results,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Semantic search execution error: {str(e)}",
        )
