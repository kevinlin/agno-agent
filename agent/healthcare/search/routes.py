"""Search API routes."""

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from agent.healthcare.search.service import SearchResult, SearchService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["search"])


def get_search_service(request: Request) -> SearchService:
    """Dependency function to get search service from app state."""
    if not hasattr(request.app.state, "search_service"):
        raise HTTPException(status_code=503, detail="Search service not initialized")
    return request.app.state.search_service


class SearchResultResponse(BaseModel):
    """API response model for search results."""

    content: str
    relevance_score: float = Field(ge=0.0, le=1.0)
    report_id: int
    chunk_index: int
    filename: str
    created_at: str  # ISO format datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    """API response model for search endpoint."""

    results: List[SearchResultResponse]
    query: str
    total_results: int
    user_external_id: str


class ErrorResponse(BaseModel):
    """API response model for errors."""

    error: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


@router.get(
    "/{user_external_id}/search",
    response_model=SearchResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid query parameters"},
        404: {"model": ErrorResponse, "description": "User not found"},
        500: {"model": ErrorResponse, "description": "Search operation failed"},
    },
)
async def search_reports(
    user_external_id: str,
    q: str = Query(..., min_length=1, max_length=1000, description="Search query"),
    k: int = Query(5, ge=1, le=20, description="Number of results to return"),
    search_service: SearchService = Depends(get_search_service),
) -> SearchResponse:
    """Search medical reports using semantic search.

    Performs semantic search across all medical reports for the specified user,
    returning relevant chunks with relevance scores and provenance information.

    Args:
        user_external_id: External user identifier
        q: Search query text (1-1000 characters)
        k: Number of results to return (1-20)

    Returns:
        SearchResponse with results, query info, and metadata

    Raises:
        HTTPException: For validation errors, user not found, or search failures
    """
    try:
        logger.info(
            f"Search request: user={user_external_id}, query='{q[:50]}...', k={k}"
        )

        # Perform semantic search
        search_results = search_service.semantic_search(
            user_external_id=user_external_id, query=q, k=k
        )

        # Convert to API response format
        response_results = []
        for result in search_results:
            response_result = SearchResultResponse(
                content=result.content,
                relevance_score=result.relevance_score,
                report_id=result.report_id,
                chunk_index=result.chunk_index,
                filename=result.filename,
                created_at=result.created_at.isoformat(),
                metadata=result.metadata,
            )
            response_results.append(response_result)

        response = SearchResponse(
            results=response_results,
            query=q,
            total_results=len(response_results),
            user_external_id=user_external_id,
        )

        logger.info(f"Search completed: {len(response_results)} results found")
        return response

    except ValueError as e:
        logger.warning(f"Search validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        logger.error(f"Search operation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected search error: {e}")
        raise HTTPException(status_code=500, detail="Internal search error")


@router.get(
    "/{user_external_id}/search/stats",
    responses={
        404: {"model": ErrorResponse, "description": "User not found"},
        500: {"model": ErrorResponse, "description": "Failed to get stats"},
    },
)
async def get_search_stats(
    user_external_id: str,
    search_service: SearchService = Depends(get_search_service),
) -> Dict[str, Any]:
    """Get search statistics for a user.

    Returns information about the user's searchable content,
    including number of reports and chunks.

    Args:
        user_external_id: External user identifier

    Returns:
        Dictionary with search statistics

    Raises:
        HTTPException: If user not found or operation fails
    """
    try:
        stats = search_service.get_search_stats(user_external_id)

        if "error" in stats:
            if stats["error"] == "User not found":
                raise HTTPException(status_code=404, detail="User not found")
            else:
                raise HTTPException(status_code=500, detail=stats["error"])

        return stats

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Failed to get search stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get search statistics")


# Health check endpoint for search service
@router.get("/search/health")
async def search_health_check(
    search_service: SearchService = Depends(get_search_service),
) -> Dict[str, Any]:
    """Health check for search service."""
    try:
        # Basic health check - verify service is initialized
        return {
            "status": "healthy",
            "service": "search",
            "embedding_model": search_service.config.embedding_model,
        }
    except Exception as e:
        logger.error(f"Search health check failed: {e}")
        raise HTTPException(status_code=503, detail="Search service unhealthy")
