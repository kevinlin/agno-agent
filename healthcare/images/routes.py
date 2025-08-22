"""FastAPI routes for asset retrieval endpoints."""

import logging
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from healthcare.storage.database import DatabaseService
from healthcare.storage.models import MedicalReport, ReportAsset

logger = logging.getLogger(__name__)

# Create router for asset endpoints
router = APIRouter(prefix="/api", tags=["assets"])


def get_database_service(request: Request) -> DatabaseService:
    """Dependency function to get database service from app state."""
    if not hasattr(request.app.state, "db_service"):
        raise HTTPException(status_code=503, detail="Database service not initialized")
    return request.app.state.db_service


@router.get("/reports/{report_id}/assets")
async def list_report_assets(
    report_id: int,
    user_external_id: Annotated[
        str, Query(description="External user identifier for access control")
    ],
    db_service: Annotated[DatabaseService, Depends(get_database_service)],
) -> JSONResponse:
    """
    List all assets for a specific medical report.

    This endpoint returns metadata about all assets (images, tables, etc.)
    associated with a medical report. Access is restricted to the report owner.

    Args:
        report_id: ID of the medical report
        user_external_id: External identifier of the requesting user
        db_service: Database service dependency

    Returns:
        JSON response with list of asset metadata

    Raises:
        HTTPException: For access denied (403), not found (404), or server errors (500)
    """
    try:
        logger.info(
            f"Asset list request for report_id={report_id}, user={user_external_id}"
        )

        # Validate user access to the report
        if not _validate_user_access(report_id, user_external_id, db_service):
            logger.warning(
                f"Access denied for user {user_external_id} to report {report_id}"
            )
            raise HTTPException(
                status_code=403,
                detail="Access denied: You don't have permission to view this report's assets",
            )

        # Get report assets
        assets = db_service.get_report_assets(report_id)

        if not assets:
            logger.info(f"No assets found for report {report_id}")
            return JSONResponse(
                status_code=200,
                content={
                    "report_id": report_id,
                    "assets": [],
                    "total_assets": 0,
                    "message": "No assets found for this report",
                },
            )

        # Format asset data for response
        asset_data = []
        for asset in assets:
            asset_info = {
                "id": asset.id,
                "kind": asset.kind,
                "filename": _extract_filename_from_path(asset.path),
                "path": asset.path,
                "alt_text": asset.alt_text,
                "created_at": (
                    asset.created_at.isoformat()
                    if hasattr(asset, "created_at") and asset.created_at
                    else None
                ),
            }
            asset_data.append(asset_info)

        logger.info(f"Retrieved {len(assets)} assets for report {report_id}")

        return JSONResponse(
            status_code=200,
            content={
                "report_id": report_id,
                "assets": asset_data,
                "total_assets": len(assets),
                "user_external_id": user_external_id,
            },
        )

    except HTTPException:
        # Re-raise HTTP exceptions with proper status codes
        raise

    except Exception as e:
        logger.error(
            f"Error retrieving assets for report {report_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=500, detail="An error occurred while retrieving report assets"
        )


@router.get("/reports/{report_id}/assets/{asset_id}")
async def get_asset_details(
    report_id: int,
    asset_id: int,
    user_external_id: Annotated[
        str, Query(description="External user identifier for access control")
    ],
    db_service: Annotated[DatabaseService, Depends(get_database_service)],
) -> JSONResponse:
    """
    Get detailed information about a specific asset.

    Args:
        report_id: ID of the medical report
        asset_id: ID of the specific asset
        user_external_id: External identifier of the requesting user
        db_service: Database service dependency

    Returns:
        JSON response with detailed asset information

    Raises:
        HTTPException: For access denied (403), not found (404), or server errors (500)
    """
    try:
        logger.info(
            f"Asset details request for asset_id={asset_id}, report_id={report_id}, user={user_external_id}"
        )

        # Validate user access to the report
        if not _validate_user_access(report_id, user_external_id, db_service):
            logger.warning(
                f"Access denied for user {user_external_id} to report {report_id}"
            )
            raise HTTPException(
                status_code=403,
                detail="Access denied: You don't have permission to view this report's assets",
            )

        # Get specific asset
        with db_service.get_session() as session:
            from sqlmodel import select

            statement = select(ReportAsset).where(
                ReportAsset.id == asset_id, ReportAsset.report_id == report_id
            )
            asset = session.exec(statement).first()

            if not asset:
                logger.warning(f"Asset {asset_id} not found for report {report_id}")
                raise HTTPException(
                    status_code=404,
                    detail=f"Asset {asset_id} not found for report {report_id}",
                )

            # Format detailed asset information
            asset_details = {
                "id": asset.id,
                "report_id": asset.report_id,
                "kind": asset.kind,
                "filename": _extract_filename_from_path(asset.path),
                "path": asset.path,
                "alt_text": asset.alt_text,
                "created_at": (
                    asset.created_at.isoformat()
                    if hasattr(asset, "created_at") and asset.created_at
                    else None
                ),
                "file_exists": _check_file_exists(asset.path),
            }

            logger.info(f"Retrieved details for asset {asset_id}")

            return JSONResponse(
                status_code=200,
                content={"asset": asset_details, "user_external_id": user_external_id},
            )

    except HTTPException:
        # Re-raise HTTP exceptions with proper status codes
        raise

    except Exception as e:
        logger.error(
            f"Error retrieving asset {asset_id} for report {report_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="An error occurred while retrieving asset details"
        )


def _validate_user_access(
    report_id: int, user_external_id: str, db_service: DatabaseService
) -> bool:
    """
    Validate that the user has access to the specified report.

    Args:
        report_id: ID of the medical report
        user_external_id: External identifier of the user
        db_service: Database service instance

    Returns:
        True if user has access, False otherwise
    """
    try:
        with db_service.get_session() as session:
            from sqlmodel import select

            from healthcare.storage.models import User

            # Get user by external ID
            user_statement = select(User).where(User.external_id == user_external_id)
            user = session.exec(user_statement).first()

            if not user:
                logger.warning(f"User not found: {user_external_id}")
                return False

            # Check if report belongs to user
            report_statement = select(MedicalReport).where(
                MedicalReport.id == report_id, MedicalReport.user_id == user.id
            )
            report = session.exec(report_statement).first()

            return report is not None

    except Exception as e:
        logger.error(f"Error validating user access: {e}")
        return False


def _extract_filename_from_path(file_path: str) -> str:
    """
    Extract filename from full file path.

    Args:
        file_path: Full path to the file

    Returns:
        Just the filename portion of the path
    """
    from pathlib import Path

    return Path(file_path).name


def _check_file_exists(file_path: str) -> bool:
    """
    Check if a file exists on disk.

    Args:
        file_path: Path to the file to check

    Returns:
        True if file exists, False otherwise
    """
    try:
        from pathlib import Path

        return Path(file_path).exists()
    except Exception:
        return False
