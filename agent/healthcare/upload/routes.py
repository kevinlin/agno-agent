"""FastAPI routes for PDF upload endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from agent.healthcare.config.config import Config, ConfigManager
from agent.healthcare.storage.database import DatabaseService
from agent.healthcare.upload.service import PDFUploadService

logger = logging.getLogger(__name__)

# Create router for upload endpoints
router = APIRouter(prefix="/api", tags=["upload"])


def get_config() -> Config:
    """Dependency to get configuration."""
    return ConfigManager.load_config()


def get_database_service(
    config: Annotated[Config, Depends(get_config)],
) -> DatabaseService:
    """Dependency to get database service."""
    return DatabaseService(config)


def get_upload_service(
    config: Annotated[Config, Depends(get_config)],
    db_service: Annotated[DatabaseService, Depends(get_database_service)],
) -> PDFUploadService:
    """Dependency to get PDF upload service."""
    return PDFUploadService(config, db_service)


@router.post("/ingest")
async def ingest_pdf(
    user_external_id: Annotated[str, Form(description="External user identifier")],
    file: Annotated[UploadFile, File(description="PDF file to upload")],
    upload_service: Annotated[PDFUploadService, Depends(get_upload_service)],
    db_service: Annotated[DatabaseService, Depends(get_database_service)],
) -> JSONResponse:
    """
    Ingest a PDF medical report.

    This endpoint accepts a PDF file upload and processes it for storage.
    It validates the file, computes a hash for deduplication, and stores
    the file along with metadata in the database.

    Args:
        user_external_id: External identifier for the user
        file: PDF file to upload
        upload_service: PDF upload service dependency
        db_service: Database service dependency

    Returns:
        JSON response with report_id and status information

    Raises:
        HTTPException: For various error conditions (400, 413, 422, 500)
    """
    try:
        logger.info(f"PDF upload started for user: {user_external_id}")

        # Process the upload
        upload_result = await upload_service.upload_pdf(user_external_id, file)

        # If it's a duplicate, return early
        if upload_result.get("duplicate", False):
            logger.info(f"Duplicate file detected for user {user_external_id}")
            return JSONResponse(
                status_code=200,
                content={
                    "report_id": upload_result["report_id"],
                    "message": "File already exists - no processing needed",
                    "duplicate": True,
                },
            )

        # Create medical report record in database
        report_data = {
            "filename": upload_result["filename"],
            "file_hash": upload_result["file_hash"],
            "language": "en",  # Default language
            "markdown_path": "",  # Will be set during conversion
            "images_dir": "",  # Will be set during image extraction
            "meta_json": "{}",  # Will be populated during conversion
        }

        medical_report = db_service.create_medical_report(
            user_id=upload_result["user_id"], report_data=report_data
        )

        logger.info(f"PDF upload completed successfully: report_id={medical_report.id}")

        return JSONResponse(
            status_code=200,
            content={
                "report_id": medical_report.id,
                "message": "PDF uploaded successfully",
                "filename": upload_result["filename"],
                "file_size": upload_result["file_size"],
                "file_hash": upload_result["file_hash"],
                "duplicate": False,
            },
        )

    except HTTPException:
        # Re-raise HTTP exceptions (they have proper status codes)
        raise

    except Exception as e:
        logger.error(f"Unexpected error in PDF ingest endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="An unexpected error occurred during PDF ingestion"
        )


@router.get("/upload/stats")
async def get_upload_stats(
    upload_service: Annotated[PDFUploadService, Depends(get_upload_service)],
) -> JSONResponse:
    """
    Get statistics about uploaded files.

    Args:
        upload_service: PDF upload service dependency

    Returns:
        JSON response with upload statistics
    """
    try:
        stats = upload_service.get_upload_stats()
        return JSONResponse(status_code=200, content=stats)

    except Exception as e:
        logger.error(f"Error getting upload stats: {e}")
        raise HTTPException(
            status_code=500, detail="Error retrieving upload statistics"
        )
