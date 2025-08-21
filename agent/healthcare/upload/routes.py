"""FastAPI routes for PDF upload endpoints."""

import json
import logging
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from agent.healthcare.config.config import Config, ConfigManager
from agent.healthcare.conversion.conversion_service import PDFConversionService
from agent.healthcare.storage.database import DatabaseService
from agent.healthcare.storage.embeddings import EmbeddingService
from agent.healthcare.upload.upload_service import PDFUploadService

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


def get_conversion_service(
    config: Annotated[Config, Depends(get_config)],
) -> PDFConversionService:
    """Dependency to get PDF conversion service."""
    return PDFConversionService(config)


def get_embedding_service(
    config: Annotated[Config, Depends(get_config)],
) -> EmbeddingService:
    """Dependency to get embedding service."""
    return EmbeddingService(config)


@router.post("/upload")
async def upload_pdf(
    user_external_id: Annotated[str, Form(description="External user identifier")],
    file: Annotated[UploadFile, File(description="PDF file to upload")],
    upload_service: Annotated[PDFUploadService, Depends(get_upload_service)],
    conversion_service: Annotated[
        PDFConversionService, Depends(get_conversion_service)
    ],
    embedding_service: Annotated[EmbeddingService, Depends(get_embedding_service)],
    db_service: Annotated[DatabaseService, Depends(get_database_service)],
    config: Annotated[Config, Depends(get_config)],
) -> JSONResponse:
    """
    Upload a PDF medical report.

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

        # Process PDF through conversion pipeline
        logger.info(f"Starting PDF conversion for file: {upload_result['filename']}")

        try:
            # Set up report directory structure
            user_id = upload_result["user_id"]
            file_hash = upload_result["file_hash"]
            report_dir = config.reports_dir / f"user_{user_id}" / file_hash[:12]

            # Convert PDF to Markdown
            pdf_path = Path(upload_result["stored_path"])
            conversion_result = await conversion_service.process_pdf(
                pdf_path, report_dir
            )

            # Create medical report record in database with conversion results
            markdown_path = report_dir / "report.md"
            images_dir = report_dir / "images"

            report_data = {
                "filename": upload_result["filename"],
                "file_hash": file_hash,
                "language": "en",  # Default language
                "markdown_path": str(markdown_path),
                "images_dir": str(images_dir),
                "meta_json": json.dumps(conversion_result.manifest),
            }

            medical_report = db_service.create_medical_report(
                user_id=user_id, report_data=report_data
            )

            # Create asset records for extracted images
            if conversion_result.extracted_images:
                logger.info(
                    f"Creating asset records for {len(conversion_result.extracted_images)} images"
                )
                try:
                    asset_data_list = []
                    for img_metadata in conversion_result.extracted_images:
                        asset_data = {
                            "kind": img_metadata.kind,
                            "path": str(img_metadata.stored_path),
                            "alt_text": img_metadata.alt_text,
                        }
                        asset_data_list.append(asset_data)

                    db_service.create_report_assets(medical_report.id, asset_data_list)
                    logger.info(
                        f"Created {len(asset_data_list)} asset records for report {medical_report.id}"
                    )

                except Exception as asset_error:
                    logger.error(f"Failed to create asset records: {asset_error}")
                    # Continue processing - asset creation failure shouldn't fail the whole upload

            # Generate and store embeddings for the converted markdown
            logger.info(f"Generating embeddings for report_id={medical_report.id}")
            try:
                # Read the markdown content
                markdown_content = markdown_path.read_text(encoding="utf-8")

                # Prepare metadata for embedding storage
                embedding_metadata = {
                    "user_external_id": user_external_id,
                    "user_id": user_id,
                    "report_id": medical_report.id,
                    "filename": upload_result["filename"],
                    "created_at": medical_report.created_at.isoformat(),
                }

                # Process embeddings
                embedding_service.process_report_embeddings(
                    markdown_content, embedding_metadata
                )

                logger.info(
                    f"Embeddings generated successfully for report_id={medical_report.id}"
                )
                embeddings_generated = True

            except Exception as embedding_error:
                logger.error(
                    f"Failed to generate embeddings for report {medical_report.id}: {embedding_error}"
                )
                embeddings_generated = False

            logger.info(
                f"PDF processing completed successfully: report_id={medical_report.id}"
            )

            return JSONResponse(
                status_code=200,
                content={
                    "report_id": medical_report.id,
                    "message": "PDF uploaded and processed successfully",
                    "filename": upload_result["filename"],
                    "file_size": upload_result["file_size"],
                    "file_hash": file_hash,
                    "markdown_generated": True,
                    "embeddings_generated": embeddings_generated,
                    "images_extracted": len(conversion_result.extracted_images),
                    "manifest": conversion_result.manifest,
                    "duplicate": False,
                },
            )

        except Exception as conversion_error:
            logger.error(f"PDF conversion failed: {conversion_error}", exc_info=True)

            # Create report record without conversion data as fallback
            report_data = {
                "filename": upload_result["filename"],
                "file_hash": upload_result["file_hash"],
                "language": "en",
                "markdown_path": "",  # Empty - conversion failed
                "images_dir": "",  # Empty - conversion failed
                "meta_json": json.dumps(
                    {"error": "Conversion failed", "figures": [], "tables": []}
                ),
            }

            medical_report = db_service.create_medical_report(
                user_id=upload_result["user_id"], report_data=report_data
            )

            logger.warning(
                f"PDF uploaded but conversion failed: report_id={medical_report.id}"
            )

            return JSONResponse(
                status_code=200,
                content={
                    "report_id": medical_report.id,
                    "message": "PDF uploaded but conversion failed - file stored for manual processing",
                    "filename": upload_result["filename"],
                    "file_size": upload_result["file_size"],
                    "file_hash": upload_result["file_hash"],
                    "markdown_generated": False,
                    "embeddings_generated": False,  # No embeddings without markdown
                    "conversion_error": str(conversion_error),
                    "duplicate": False,
                },
            )

    except HTTPException:
        # Re-raise HTTP exceptions (they have proper status codes)
        raise

    except Exception as e:
        logger.error(f"Unexpected error in PDF upload endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="An unexpected error occurred during PDF upload"
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
