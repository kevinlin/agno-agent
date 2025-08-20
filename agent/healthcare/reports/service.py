"""Report management service for healthcare agent."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import HTTPException
from sqlmodel import select

from agent.healthcare.config.config import Config
from agent.healthcare.storage.database import DatabaseService
from agent.healthcare.storage.models import MedicalReport, ReportAsset, User

logger = logging.getLogger(__name__)


class ReportService:
    """Service for managing medical reports and providing access control."""

    def __init__(self, config: Config, db_service: DatabaseService):
        """Initialize report service.

        Args:
            config: Application configuration
            db_service: Database service instance
        """
        self.config = config
        self.db_service = db_service

    def validate_user_access(self, report_id: int, user_external_id: str) -> bool:
        """Validate that a user has access to a specific report.

        Args:
            report_id: Report ID to check access for
            user_external_id: User external ID to validate

        Returns:
            True if user has access, False otherwise

        Raises:
            ValueError: If user or report not found
        """
        try:
            with self.db_service.get_session() as session:
                # Get user by external ID
                user = session.exec(
                    select(User).where(User.external_id == user_external_id)
                ).first()
                if not user:
                    raise ValueError(f"User not found: {user_external_id}")

                # Get report and check ownership
                report = session.get(MedicalReport, report_id)
                if not report:
                    raise ValueError(f"Report not found: {report_id}")

                # Check if report belongs to user
                return report.user_id == user.id

        except ValueError:
            # Re-raise validation errors
            raise
        except Exception as e:
            logger.error(f"Error validating user access: {e}")
            raise RuntimeError(f"Access validation failed: {str(e)}")

    def list_user_reports(self, user_external_id: str) -> List[Dict]:
        """List all reports for a user.

        Args:
            user_external_id: User external ID

        Returns:
            List of report summaries with metadata

        Raises:
            ValueError: If user not found
            RuntimeError: If operation fails
        """
        try:
            # Strip whitespace from input
            user_external_id = user_external_id.strip() if user_external_id else ""

            if not user_external_id:
                raise ValueError("User external ID is required")

            with self.db_service.get_session() as session:
                # Get user by external ID
                user = session.exec(
                    select(User).where(User.external_id == user_external_id)
                ).first()
                if not user:
                    raise ValueError(f"User not found: {user_external_id}")

                # Get all reports for user
                reports = session.exec(
                    select(MedicalReport)
                    .where(MedicalReport.user_id == user.id)
                    .order_by(MedicalReport.created_at.desc())
                ).all()

                # Convert to summary format
                report_summaries = []
                for report in reports:
                    try:
                        # Parse metadata JSON
                        meta_data = (
                            json.loads(report.meta_json) if report.meta_json else {}
                        )

                        summary = {
                            "id": report.id,
                            "filename": report.filename,
                            "created_at": report.created_at.isoformat(),
                            "language": report.language,
                            "file_hash": report.file_hash[
                                :12
                            ],  # Shortened hash for display
                            "has_images": bool(report.images_dir),
                            "manifest": meta_data.get("manifest", {}),
                        }
                        report_summaries.append(summary)
                    except Exception as e:
                        logger.warning(f"Error processing report {report.id}: {e}")
                        # Include basic info even if metadata parsing fails
                        summary = {
                            "id": report.id,
                            "filename": report.filename,
                            "created_at": report.created_at.isoformat(),
                            "language": report.language,
                            "file_hash": report.file_hash[:12],
                            "has_images": bool(report.images_dir),
                            "manifest": {},
                        }
                        report_summaries.append(summary)

                logger.info(
                    f"Listed {len(report_summaries)} reports for user {user_external_id}"
                )
                return report_summaries

        except ValueError:
            # Re-raise validation errors
            raise
        except Exception as e:
            logger.error(f"Failed to list user reports: {e}")
            raise RuntimeError(f"Report listing failed: {str(e)}")

    def get_report_markdown(self, report_id: int, user_external_id: str) -> str:
        """Get the markdown content for a specific report.

        Args:
            report_id: Report ID to retrieve
            user_external_id: User external ID for access validation

        Returns:
            Markdown content as string

        Raises:
            ValueError: If user not found or access denied
            FileNotFoundError: If markdown file not found
            RuntimeError: If operation fails
        """
        try:
            # Strip whitespace from input
            user_external_id = user_external_id.strip() if user_external_id else ""

            if not user_external_id:
                raise ValueError("User external ID is required")

            # Validate access first
            if not self.validate_user_access(report_id, user_external_id):
                raise ValueError(
                    f"Access denied to report {report_id} for user {user_external_id}"
                )

            with self.db_service.get_session() as session:
                # Get report metadata
                report = session.get(MedicalReport, report_id)
                if not report:
                    raise ValueError(f"Report not found: {report_id}")

                # Check if markdown file exists
                markdown_path = Path(report.markdown_path)
                if not markdown_path.exists():
                    raise FileNotFoundError(f"Markdown file not found: {markdown_path}")

                # Read markdown content
                try:
                    with open(markdown_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    logger.info(
                        f"Retrieved markdown for report {report_id}, size: {len(content)} chars"
                    )
                    return content

                except UnicodeDecodeError as e:
                    logger.error(f"Encoding error reading markdown file: {e}")
                    raise RuntimeError(
                        f"Could not read markdown file due to encoding issues"
                    )

        except (ValueError, FileNotFoundError):
            # Re-raise validation and file not found errors
            raise
        except Exception as e:
            logger.error(f"Failed to get report markdown: {e}")
            raise RuntimeError(f"Markdown retrieval failed: {str(e)}")

    def list_report_assets(self, report_id: int, user_external_id: str) -> List[Dict]:
        """List all assets for a specific report.

        Args:
            report_id: Report ID to list assets for
            user_external_id: User external ID for access validation

        Returns:
            List of asset information dictionaries

        Raises:
            ValueError: If user not found or access denied
            RuntimeError: If operation fails
        """
        try:
            # Strip whitespace from input
            user_external_id = user_external_id.strip() if user_external_id else ""

            if not user_external_id:
                raise ValueError("User external ID is required")

            # Validate access first
            if not self.validate_user_access(report_id, user_external_id):
                raise ValueError(
                    f"Access denied to report {report_id} for user {user_external_id}"
                )

            with self.db_service.get_session() as session:
                # Get all assets for the report
                assets = session.exec(
                    select(ReportAsset)
                    .where(ReportAsset.report_id == report_id)
                    .order_by(ReportAsset.page_number, ReportAsset.kind)
                ).all()

                # Convert to info format
                asset_info = []
                for asset in assets:
                    try:
                        # Check if file exists on disk
                        asset_path = Path(asset.path)
                        file_exists = asset_path.exists()
                        file_size = asset_path.stat().st_size if file_exists else 0

                        info = {
                            "id": asset.id,
                            "kind": asset.kind,
                            "filename": asset_path.name,
                            "path": asset.path,
                            "alt_text": asset.alt_text,
                            "page_number": asset.page_number,
                            "created_at": asset.created_at.isoformat(),
                            "file_exists": file_exists,
                            "file_size": file_size,
                        }
                        asset_info.append(info)
                    except Exception as e:
                        logger.warning(f"Error processing asset {asset.id}: {e}")
                        # Include basic info even if file checking fails
                        info = {
                            "id": asset.id,
                            "kind": asset.kind,
                            "filename": Path(asset.path).name,
                            "path": asset.path,
                            "alt_text": asset.alt_text,
                            "page_number": asset.page_number,
                            "created_at": asset.created_at.isoformat(),
                            "file_exists": False,
                            "file_size": 0,
                        }
                        asset_info.append(info)

                logger.info(f"Listed {len(asset_info)} assets for report {report_id}")
                return asset_info

        except ValueError:
            # Re-raise validation errors
            raise
        except Exception as e:
            logger.error(f"Failed to list report assets: {e}")
            raise RuntimeError(f"Asset listing failed: {str(e)}")

    def get_report_summary(self, report_id: int, user_external_id: str) -> Dict:
        """Get detailed summary information for a specific report.

        Args:
            report_id: Report ID to get summary for
            user_external_id: User external ID for access validation

        Returns:
            Detailed report summary dictionary

        Raises:
            ValueError: If user not found or access denied
            RuntimeError: If operation fails
        """
        try:
            # Strip whitespace from input
            user_external_id = user_external_id.strip() if user_external_id else ""

            if not user_external_id:
                raise ValueError("User external ID is required")

            # Validate access first
            if not self.validate_user_access(report_id, user_external_id):
                raise ValueError(
                    f"Access denied to report {report_id} for user {user_external_id}"
                )

            with self.db_service.get_session() as session:
                # Get report
                report = session.get(MedicalReport, report_id)
                if not report:
                    raise ValueError(f"Report not found: {report_id}")

                # Get asset count
                asset_count = len(
                    session.exec(
                        select(ReportAsset).where(ReportAsset.report_id == report_id)
                    ).all()
                )

                # Check file sizes
                markdown_size = 0
                markdown_exists = False
                if report.markdown_path:
                    markdown_path = Path(report.markdown_path)
                    if markdown_path.exists():
                        markdown_exists = True
                        markdown_size = markdown_path.stat().st_size

                # Parse metadata
                try:
                    meta_data = json.loads(report.meta_json) if report.meta_json else {}
                except json.JSONDecodeError:
                    meta_data = {}

                summary = {
                    "id": report.id,
                    "filename": report.filename,
                    "file_hash": report.file_hash,
                    "language": report.language,
                    "created_at": report.created_at.isoformat(),
                    "markdown_path": report.markdown_path,
                    "markdown_exists": markdown_exists,
                    "markdown_size": markdown_size,
                    "images_dir": report.images_dir,
                    "asset_count": asset_count,
                    "metadata": meta_data,
                }

                logger.info(f"Generated summary for report {report_id}")
                return summary

        except ValueError:
            # Re-raise validation errors
            raise
        except Exception as e:
            logger.error(f"Failed to get report summary: {e}")
            raise RuntimeError(f"Report summary failed: {str(e)}")

    def get_report_stats(self, user_external_id: str) -> Dict:
        """Get statistics for all reports of a user.

        Args:
            user_external_id: User external ID

        Returns:
            Dictionary with user report statistics

        Raises:
            ValueError: If user not found
            RuntimeError: If operation fails
        """
        try:
            # Strip whitespace from input
            user_external_id = user_external_id.strip() if user_external_id else ""

            if not user_external_id:
                raise ValueError("User external ID is required")

            with self.db_service.get_session() as session:
                # Get user
                user = session.exec(
                    select(User).where(User.external_id == user_external_id)
                ).first()
                if not user:
                    raise ValueError(f"User not found: {user_external_id}")

                # Get all reports for user
                reports = session.exec(
                    select(MedicalReport).where(MedicalReport.user_id == user.id)
                ).all()

                # Calculate statistics
                total_reports = len(reports)
                total_assets = 0
                total_markdown_size = 0
                languages = {}

                for report in reports:
                    # Count assets
                    assets = session.exec(
                        select(ReportAsset).where(ReportAsset.report_id == report.id)
                    ).all()
                    total_assets += len(assets)

                    # Sum markdown sizes
                    if report.markdown_path:
                        markdown_path = Path(report.markdown_path)
                        if markdown_path.exists():
                            total_markdown_size += markdown_path.stat().st_size

                    # Count languages
                    lang = report.language or "unknown"
                    languages[lang] = languages.get(lang, 0) + 1

                stats = {
                    "user_external_id": user_external_id,
                    "total_reports": total_reports,
                    "total_assets": total_assets,
                    "total_markdown_size": total_markdown_size,
                    "languages": languages,
                    "user_created_at": user.created_at.isoformat(),
                }

                logger.info(
                    f"Generated stats for user {user_external_id}: {total_reports} reports"
                )
                return stats

        except ValueError:
            # Re-raise validation errors
            raise
        except Exception as e:
            logger.error(f"Failed to get report stats: {e}")
            raise RuntimeError(f"Report stats failed: {str(e)}")
