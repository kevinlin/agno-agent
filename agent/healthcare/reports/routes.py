"""FastAPI routes for report management endpoints."""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from agent.healthcare.reports.service import ReportService

logger = logging.getLogger(__name__)

# Create router for report management endpoints
router = APIRouter(prefix="/reports", tags=["reports"])


def get_report_service(request: Request) -> ReportService:
    """Dependency function to get report service from app state."""
    if not hasattr(request.app.state, "report_service"):
        raise HTTPException(status_code=503, detail="Report service not initialized")
    return request.app.state.report_service


class ReportSummary(BaseModel):
    """API response model for report summary."""

    id: int
    filename: str
    created_at: str  # ISO format datetime
    language: str
    file_hash: str  # Shortened hash for display
    has_images: bool
    manifest: Dict[str, Any] = Field(default_factory=dict)


class ReportListResponse(BaseModel):
    """API response model for report listing."""

    reports: List[ReportSummary]
    total: int
    user_external_id: str


class MarkdownResponse(BaseModel):
    """API response model for markdown content."""

    report_id: int
    filename: str
    content: str
    content_length: int
    created_at: str


class AssetInfo(BaseModel):
    """API response model for asset information."""

    id: int
    kind: str
    filename: str
    path: str
    alt_text: Optional[str] = None
    page_number: Optional[int] = None
    created_at: str
    file_exists: bool
    file_size: int


class AssetListResponse(BaseModel):
    """API response model for asset listing."""

    assets: List[AssetInfo]
    total: int
    report_id: int


class ErrorResponse(BaseModel):
    """API response model for errors."""

    error: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


@router.get(
    "/{user_external_id}",
    response_model=ReportListResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid user ID"},
        404: {"model": ErrorResponse, "description": "User not found"},
        500: {"model": ErrorResponse, "description": "Report listing failed"},
    },
)
async def list_reports(
    user_external_id: str,
    report_service: ReportService = Depends(get_report_service),
) -> ReportListResponse:
    """List all medical reports for a user.

    Returns a list of all medical reports belonging to the specified user,
    with summary information including metadata and creation dates.

    Args:
        user_external_id: External user identifier

    Returns:
        ReportListResponse with list of report summaries

    Raises:
        HTTPException: For validation errors, user not found, or operation failures
    """
    try:
        logger.info(f"Listing reports for user: {user_external_id}")

        # Get user reports
        report_summaries = report_service.list_user_reports(user_external_id)

        # Convert to API response format
        api_reports = []
        for summary in report_summaries:
            api_report = ReportSummary(
                id=summary["id"],
                filename=summary["filename"],
                created_at=summary["created_at"],
                language=summary["language"],
                file_hash=summary["file_hash"],
                has_images=summary["has_images"],
                manifest=summary["manifest"],
            )
            api_reports.append(api_report)

        response = ReportListResponse(
            reports=api_reports,
            total=len(api_reports),
            user_external_id=user_external_id,
        )

        logger.info(f"Listed {len(api_reports)} reports for user {user_external_id}")
        return response

    except ValueError as e:
        logger.warning(f"Report listing validation error: {e}")
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        logger.error(f"Report listing operation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected report listing error: {e}")
        raise HTTPException(status_code=500, detail="Internal report listing error")


@router.get(
    "/{report_id}/markdown",
    response_model=MarkdownResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid parameters"},
        403: {"model": ErrorResponse, "description": "Access denied"},
        404: {"model": ErrorResponse, "description": "Report or file not found"},
        500: {"model": ErrorResponse, "description": "Markdown retrieval failed"},
    },
)
async def get_report_markdown(
    report_id: int,
    user_external_id: str = Query(
        ..., description="External user identifier for access validation"
    ),
    report_service: ReportService = Depends(get_report_service),
) -> MarkdownResponse:
    """Get the markdown content for a specific report.

    Returns the full markdown content of the specified report after validating
    that the user has access to it.

    Args:
        report_id: Report ID to retrieve markdown for
        user_external_id: External user identifier for access validation

    Returns:
        MarkdownResponse with markdown content and metadata

    Raises:
        HTTPException: For validation errors, access denied, file not found, or operation failures
    """
    try:
        logger.info(
            f"Retrieving markdown for report {report_id}, user {user_external_id}"
        )

        # Get markdown content (includes access validation)
        content = report_service.get_report_markdown(report_id, user_external_id)

        # Get report summary for additional metadata
        report_summary = report_service.get_report_summary(report_id, user_external_id)

        response = MarkdownResponse(
            report_id=report_id,
            filename=report_summary["filename"],
            content=content,
            content_length=len(content),
            created_at=report_summary["created_at"],
        )

        logger.info(
            f"Retrieved markdown for report {report_id}, size: {len(content)} chars"
        )
        return response

    except ValueError as e:
        logger.warning(f"Markdown retrieval validation error: {e}")
        error_msg = str(e).lower()
        if "access denied" in error_msg:
            raise HTTPException(status_code=403, detail=str(e))
        elif "not found" in error_msg:
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        logger.warning(f"Markdown file not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        logger.error(f"Markdown retrieval operation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected markdown retrieval error: {e}")
        raise HTTPException(status_code=500, detail="Internal markdown retrieval error")


@router.get(
    "/{report_id}/assets",
    response_model=AssetListResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid parameters"},
        403: {"model": ErrorResponse, "description": "Access denied"},
        404: {"model": ErrorResponse, "description": "Report not found"},
        500: {"model": ErrorResponse, "description": "Asset listing failed"},
    },
)
async def list_report_assets(
    report_id: int,
    user_external_id: str = Query(
        ..., description="External user identifier for access validation"
    ),
    report_service: ReportService = Depends(get_report_service),
) -> AssetListResponse:
    """List all assets for a specific report.

    Returns a list of all assets (images, tables, etc.) associated with the
    specified report after validating user access.

    Args:
        report_id: Report ID to list assets for
        user_external_id: External user identifier for access validation

    Returns:
        AssetListResponse with list of asset information

    Raises:
        HTTPException: For validation errors, access denied, report not found, or operation failures
    """
    try:
        logger.info(f"Listing assets for report {report_id}, user {user_external_id}")

        # Get report assets (includes access validation)
        asset_info = report_service.list_report_assets(report_id, user_external_id)

        # Convert to API response format
        api_assets = []
        for asset in asset_info:
            api_asset = AssetInfo(
                id=asset["id"],
                kind=asset["kind"],
                filename=asset["filename"],
                path=asset["path"],
                alt_text=asset["alt_text"],
                page_number=asset["page_number"],
                created_at=asset["created_at"],
                file_exists=asset["file_exists"],
                file_size=asset["file_size"],
            )
            api_assets.append(api_asset)

        response = AssetListResponse(
            assets=api_assets,
            total=len(api_assets),
            report_id=report_id,
        )

        logger.info(f"Listed {len(api_assets)} assets for report {report_id}")
        return response

    except ValueError as e:
        logger.warning(f"Asset listing validation error: {e}")
        error_msg = str(e).lower()
        if "access denied" in error_msg:
            raise HTTPException(status_code=403, detail=str(e))
        elif "not found" in error_msg:
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        logger.error(f"Asset listing operation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected asset listing error: {e}")
        raise HTTPException(status_code=500, detail="Internal asset listing error")


@router.get(
    "/{report_id}/summary",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid parameters"},
        403: {"model": ErrorResponse, "description": "Access denied"},
        404: {"model": ErrorResponse, "description": "Report not found"},
        500: {"model": ErrorResponse, "description": "Summary retrieval failed"},
    },
)
async def get_report_summary(
    report_id: int,
    user_external_id: str = Query(
        ..., description="External user identifier for access validation"
    ),
    report_service: ReportService = Depends(get_report_service),
) -> Dict[str, Any]:
    """Get detailed summary information for a specific report.

    Returns comprehensive information about the specified report including
    file sizes, asset counts, and metadata after validating user access.

    Args:
        report_id: Report ID to get summary for
        user_external_id: External user identifier for access validation

    Returns:
        Dictionary with detailed report summary

    Raises:
        HTTPException: For validation errors, access denied, report not found, or operation failures
    """
    try:
        logger.info(f"Getting summary for report {report_id}, user {user_external_id}")

        # Get report summary (includes access validation)
        summary = report_service.get_report_summary(report_id, user_external_id)

        logger.info(f"Retrieved summary for report {report_id}")
        return summary

    except ValueError as e:
        logger.warning(f"Summary retrieval validation error: {e}")
        error_msg = str(e).lower()
        if "access denied" in error_msg:
            raise HTTPException(status_code=403, detail=str(e))
        elif "not found" in error_msg:
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        logger.error(f"Summary retrieval operation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected summary retrieval error: {e}")
        raise HTTPException(status_code=500, detail="Internal summary retrieval error")


@router.get(
    "/{user_external_id}/stats",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid user ID"},
        404: {"model": ErrorResponse, "description": "User not found"},
        500: {"model": ErrorResponse, "description": "Stats retrieval failed"},
    },
)
async def get_report_stats(
    user_external_id: str,
    report_service: ReportService = Depends(get_report_service),
) -> Dict[str, Any]:
    """Get statistics for all reports of a user.

    Returns aggregate statistics about all reports belonging to the specified user,
    including counts, sizes, and language distribution.

    Args:
        user_external_id: External user identifier

    Returns:
        Dictionary with user report statistics

    Raises:
        HTTPException: For validation errors, user not found, or operation failures
    """
    try:
        logger.info(f"Getting report stats for user: {user_external_id}")

        # Get report statistics
        stats = report_service.get_report_stats(user_external_id)

        logger.info(
            f"Retrieved stats for user {user_external_id}: {stats.get('total_reports', 0)} reports"
        )
        return stats

    except ValueError as e:
        logger.warning(f"Stats retrieval validation error: {e}")
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        logger.error(f"Stats retrieval operation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected stats retrieval error: {e}")
        raise HTTPException(status_code=500, detail="Internal stats retrieval error")
