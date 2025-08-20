"""PDF upload service for healthcare agent."""

import hashlib
import logging
from pathlib import Path
from typing import Optional, Tuple

from fastapi import HTTPException, UploadFile

from agent.healthcare.config.config import Config
from agent.healthcare.storage.database import DatabaseService

logger = logging.getLogger(__name__)


class PDFUploadService:
    """Service for handling PDF file uploads and validation."""

    def __init__(self, config: Config, db_service: DatabaseService):
        """Initialize PDF upload service."""
        self.config = config
        self.db_service = db_service
        self._ensure_upload_directory()

    def _ensure_upload_directory(self) -> None:
        """Ensure upload directory exists."""
        self.config.uploads_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Upload directory ensured: {self.config.uploads_dir}")

    def validate_pdf(self, file_content: bytes) -> bool:
        """
        Validate that the file content is a valid PDF.

        Args:
            file_content: Raw file content bytes

        Returns:
            True if valid PDF, False otherwise
        """
        try:
            # Check if file is empty
            if not file_content:
                return False

            # Check PDF magic number - most reliable method
            if file_content.startswith(b"%PDF-"):
                # For basic validation, if it starts with %PDF- we consider it valid
                # This covers most real-world scenarios without requiring complex parsing
                return True

            return False

        except Exception as e:
            logger.warning(f"PDF validation failed: {e}")
            return False

    def compute_hash(self, file_content: bytes) -> str:
        """
        Compute SHA-256 hash of file content.

        Args:
            file_content: Raw file content bytes

        Returns:
            Hexadecimal string representation of SHA-256 hash
        """
        sha256_hash = hashlib.sha256()
        sha256_hash.update(file_content)
        return sha256_hash.hexdigest()

    def check_duplicate(self, user_id: int, file_hash: str) -> Optional[int]:
        """
        Check if a file with the same hash already exists for the user.

        Args:
            user_id: User ID to check for duplicates
            file_hash: SHA-256 hash of the file

        Returns:
            Report ID if duplicate found, None otherwise
        """
        try:
            with self.db_service.get_session() as session:
                from sqlmodel import select

                from agent.healthcare.storage.models import MedicalReport

                statement = select(MedicalReport).where(
                    MedicalReport.user_id == user_id,
                    MedicalReport.file_hash == file_hash,
                )
                existing_report = session.exec(statement).first()

                if existing_report:
                    logger.info(
                        f"Duplicate file detected: hash={file_hash}, user_id={user_id}"
                    )
                    return existing_report.id

                return None

        except Exception as e:
            logger.error(f"Error checking for duplicates: {e}")
            raise HTTPException(
                status_code=500, detail="Error checking for duplicate files"
            )

    def store_pdf(self, file_content: bytes, filename: str, file_hash: str) -> Path:
        """
        Store PDF file to disk with hash-based naming.

        Args:
            file_content: Raw file content bytes
            filename: Original filename
            file_hash: SHA-256 hash of the file

        Returns:
            Path where the file was stored
        """
        try:
            # Create filename with hash prefix for uniqueness
            file_extension = Path(filename).suffix.lower()
            if not file_extension:
                file_extension = ".pdf"

            stored_filename = f"{file_hash[:12]}{file_extension}"
            stored_path = self.config.uploads_dir / stored_filename

            # Write file to disk
            with open(stored_path, "wb") as f:
                f.write(file_content)

            logger.info(f"PDF stored: {stored_path}")
            return stored_path

        except Exception as e:
            logger.error(f"Error storing PDF file: {e}")
            raise HTTPException(status_code=500, detail="Error storing uploaded file")

    async def upload_pdf(self, user_external_id: str, file: UploadFile) -> dict:
        """
        Handle complete PDF upload process.

        Args:
            user_external_id: External user identifier
            file: Uploaded file object

        Returns:
            Dictionary with upload result information
        """
        try:
            # Validate file type
            if not file.filename or not file.filename.lower().endswith(".pdf"):
                raise HTTPException(
                    status_code=400, detail="Only PDF files are allowed"
                )

            # Read file content
            file_content = await file.read()

            # Validate file size (max 50MB)
            max_size = 50 * 1024 * 1024  # 50MB
            if len(file_content) > max_size:
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Maximum size is {max_size // (1024*1024)}MB",
                )

            # Validate PDF format
            if not self.validate_pdf(file_content):
                raise HTTPException(status_code=400, detail="Invalid PDF file format")

            # Compute hash
            file_hash = self.compute_hash(file_content)

            # Get or create user
            user = self.db_service.get_or_create_user(user_external_id)

            # Check for duplicates
            existing_report_id = self.check_duplicate(user.id, file_hash)
            if existing_report_id:
                return {
                    "report_id": existing_report_id,
                    "message": "File already exists",
                    "duplicate": True,
                }

            # Store PDF file
            stored_path = self.store_pdf(file_content, file.filename, file_hash)

            return {
                "user_id": user.id,
                "filename": file.filename,
                "file_hash": file_hash,
                "stored_path": str(stored_path),
                "file_size": len(file_content),
                "duplicate": False,
            }

        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except Exception as e:
            logger.error(f"Unexpected error in PDF upload: {e}")
            raise HTTPException(
                status_code=500,
                detail="An unexpected error occurred during file upload",
            )

    def get_upload_stats(self) -> dict:
        """
        Get statistics about uploaded files.

        Returns:
            Dictionary with upload statistics
        """
        try:
            upload_dir = self.config.uploads_dir
            if not upload_dir.exists():
                return {"total_uploads": 0, "total_files": 0, "total_size": 0}

            files = list(upload_dir.glob("*.pdf"))
            total_size = sum(f.stat().st_size for f in files if f.is_file())

            return {
                "total_uploads": len(files),
                "total_files": len(files),  # Keep for backward compatibility
                "total_size": total_size,
                "upload_directory": str(upload_dir),
            }

        except Exception as e:
            logger.error(f"Error getting upload stats: {e}")
            return {"error": str(e)}
