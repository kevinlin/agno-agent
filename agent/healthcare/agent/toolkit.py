"""Medical toolkit for Agno agent integration."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from agno.agent import Agent
from agno.tools import Toolkit

from agent.healthcare.config.config import Config
from agent.healthcare.reports.service import ReportService
from agent.healthcare.search.search_service import SearchResult, SearchService
from agent.healthcare.storage.database import DatabaseService

logger = logging.getLogger(__name__)


class MedicalToolkit(Toolkit):
    """Toolkit providing medical data access tools for Agno agent."""

    def __init__(
        self,
        config: Config,
        db_service: DatabaseService,
        search_service: SearchService,
        report_service: ReportService,
    ):
        """Initialize medical toolkit with required services.

        Args:
            config: Application configuration
            db_service: Database service for medical data access
            search_service: Search service for semantic search
            report_service: Report service for report management
        """
        super().__init__()
        self.config = config
        self.db_service = db_service
        self.search_service = search_service
        self.report_service = report_service

    def ingest_pdf(self, user_external_id: str, pdf_path: str) -> str:
        """Upload and ingest a PDF medical report for processing.

        Args:
            user_external_id: External ID of the user
            pdf_path: Path to the PDF file to ingest

        Returns:
            Success message with report ID

        Raises:
            ValueError: If PDF path is invalid or user ID is missing
            RuntimeError: If ingestion fails
        """
        try:
            # Validate inputs
            if not user_external_id or not user_external_id.strip():
                raise ValueError("User external ID is required")

            if not pdf_path or not pdf_path.strip():
                raise ValueError("PDF path is required")

            pdf_file = Path(pdf_path.strip())
            if not pdf_file.exists():
                raise ValueError(f"PDF file not found: {pdf_path}")

            if not pdf_file.suffix.lower() == ".pdf":
                raise ValueError("File must be a PDF")

            # Note: This tool is designed to work with PDFs that have already been uploaded
            # through the main ingestion endpoint. In a production system, this would
            # trigger the full ingestion pipeline.
            # For now, we'll return a helpful message about using the upload endpoint.

            return (
                f"To ingest PDF '{pdf_file.name}', please use the upload endpoint:\n"
                f"POST /api/ingest with user_external_id='{user_external_id}' and the PDF file.\n"
                f"The PDF will be converted to Markdown, images extracted, and embeddings generated automatically."
            )

        except ValueError as e:
            # Re-raise validation errors
            raise e
        except Exception as e:
            logger.error(f"PDF ingestion failed: {e}")
            raise RuntimeError(f"Failed to ingest PDF: {e}")

    def list_reports(self, user_external_id: str) -> List[str]:
        """List all medical reports for a user.

        Args:
            user_external_id: External ID of the user

        Returns:
            List of report descriptions with ID, filename, and date

        Raises:
            ValueError: If user ID is missing
            RuntimeError: If report listing fails
        """
        try:
            # Validate input
            if not user_external_id or not user_external_id.strip():
                raise ValueError("User external ID is required")

            user_external_id = user_external_id.strip()

            # Get reports using the report service
            reports = self.report_service.list_user_reports(user_external_id)

            if not reports:
                return [f"No medical reports found for user '{user_external_id}'"]

            # Format report information
            report_list = []
            for report in reports:
                report_info = (
                    f"Report ID: {report['id']} | "
                    f"Filename: {report['filename']} | "
                    f"Uploaded: {report['created_at']}"
                )
                report_list.append(report_info)

            return report_list

        except ValueError as e:
            # Re-raise validation errors
            raise e
        except Exception as e:
            logger.error(f"Failed to list reports for user {user_external_id}: {e}")
            raise RuntimeError(f"Failed to list reports: {e}")

    def search_medical_data(
        self, user_external_id: str, query: str, k: int = 5
    ) -> List[Dict[str, any]]:
        """Search medical data using semantic search across user's reports.

        Args:
            user_external_id: External ID of the user
            query: Search query text
            k: Number of results to return (default: 5, max: 20)

        Returns:
            List of search results with content, scores, and metadata

        Raises:
            ValueError: If inputs are invalid
            RuntimeError: If search fails
        """
        try:
            # Validate inputs
            if not user_external_id or not user_external_id.strip():
                raise ValueError("User external ID is required")

            if not query or not query.strip():
                raise ValueError("Search query is required")

            # Limit k to reasonable bounds
            k = max(1, min(k, 20))

            user_external_id = user_external_id.strip()
            query = query.strip()

            # Perform semantic search
            search_results = self.search_service.semantic_search(
                user_external_id=user_external_id, query=query, k=k
            )

            if not search_results:
                return [
                    {
                        "message": f"No results found for query: '{query}'",
                        "user_id": user_external_id,
                        "query": query,
                    }
                ]

            # Format results for agent consumption
            formatted_results = []
            for result in search_results:
                formatted_result = {
                    "content": result.content,
                    "relevance_score": round(result.relevance_score, 3),
                    "source": {
                        "report_id": result.report_id,
                        "filename": result.filename,
                        "chunk_index": result.chunk_index,
                        "created_at": result.created_at.isoformat(),
                    },
                    "metadata": result.metadata,
                }
                formatted_results.append(formatted_result)

            return formatted_results

        except ValueError as e:
            # Re-raise validation errors
            raise e
        except Exception as e:
            logger.error(f"Medical data search failed for user {user_external_id}: {e}")
            raise RuntimeError(f"Search failed: {e}")

    def get_report_content(self, user_external_id: str, report_id: int) -> str:
        """Get the full Markdown content of a specific report.

        Args:
            user_external_id: External ID of the user
            report_id: ID of the report to retrieve

        Returns:
            Full Markdown content of the report

        Raises:
            ValueError: If inputs are invalid
            RuntimeError: If retrieval fails
        """
        try:
            # Validate inputs
            if not user_external_id or not user_external_id.strip():
                raise ValueError("User external ID is required")

            if not report_id or report_id <= 0:
                raise ValueError("Valid report ID is required")

            user_external_id = user_external_id.strip()

            # Get report content using the report service
            content = self.report_service.get_report_markdown(
                report_id=report_id, user_external_id=user_external_id
            )

            return content

        except ValueError as e:
            # Re-raise validation errors
            raise e
        except Exception as e:
            logger.error(
                f"Failed to get report content for user {user_external_id}, report {report_id}: {e}"
            )
            raise RuntimeError(f"Failed to retrieve report content: {e}")

    def get_report_summary(
        self, user_external_id: str, report_id: int
    ) -> Dict[str, any]:
        """Get a summary of a specific report including metadata and assets.

        Args:
            user_external_id: External ID of the user
            report_id: ID of the report to summarize

        Returns:
            Dictionary with report metadata, asset count, and content preview

        Raises:
            ValueError: If inputs are invalid
            RuntimeError: If summary generation fails
        """
        try:
            # Validate inputs
            if not user_external_id or not user_external_id.strip():
                raise ValueError("User external ID is required")

            if not report_id or report_id <= 0:
                raise ValueError("Valid report ID is required")

            user_external_id = user_external_id.strip()

            # Get report details from report service
            reports = self.report_service.list_user_reports(user_external_id)
            target_report = None

            for report in reports:
                if report["id"] == report_id:
                    target_report = report
                    break

            if not target_report:
                raise ValueError(
                    f"Report {report_id} not found for user {user_external_id}"
                )

            # Get assets information
            try:
                assets = self.report_service.list_report_assets(
                    report_id, user_external_id
                )
                asset_count = len(assets)
                image_count = len([a for a in assets if a.get("kind") == "image"])
            except Exception:
                asset_count = 0
                image_count = 0

            # Get content preview (first 500 characters)
            try:
                content = self.report_service.get_report_markdown(
                    report_id, user_external_id
                )
                content_preview = (
                    content[:500] + "..." if len(content) > 500 else content
                )
            except Exception:
                content_preview = "Content not available"

            summary = {
                "report_id": report_id,
                "filename": target_report["filename"],
                "created_at": target_report["created_at"],
                "asset_count": asset_count,
                "image_count": image_count,
                "content_preview": content_preview,
                "user_external_id": user_external_id,
            }

            return summary

        except ValueError as e:
            # Re-raise validation errors
            raise e
        except Exception as e:
            logger.error(
                f"Failed to generate report summary for user {user_external_id}, report {report_id}: {e}"
            )
            raise RuntimeError(f"Failed to generate report summary: {e}")
