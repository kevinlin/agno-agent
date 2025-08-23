"""Search service for semantic search functionality."""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from healthcare.config.config import Config
from healthcare.search.embeddings import EmbeddingService
from healthcare.storage.database import DatabaseService
from healthcare.storage.models import MedicalReport, User

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Search result with content and metadata."""

    content: str
    relevance_score: float
    report_id: int
    chunk_index: int
    filename: str
    created_at: datetime
    user_external_id: str
    metadata: Dict[str, Any]


class SearchService:
    """Service for semantic search across medical reports."""

    def __init__(
        self,
        config: Config,
        db_service: DatabaseService,
        embedding_service: EmbeddingService,
    ):
        """Initialize search service.

        Args:
            config: Application configuration
            db_service: Database service instance
            embedding_service: Embedding service instance
        """
        self.config = config
        self.db_service = db_service
        self.embedding_service = embedding_service

    def validate_query(self, query: str) -> bool:
        """Validate search query.

        Args:
            query: Search query text

        Returns:
            True if query is valid, False otherwise
        """
        if not query or not isinstance(query, str):
            return False

        query = query.strip()
        if len(query) == 0:
            return False

        if len(query) > 1000:  # Reasonable limit
            return False

        return True

    def semantic_search(
        self, user_external_id: str, query: str, k: int = 5
    ) -> List[SearchResult]:
        """Perform semantic search with user filtering.

        Args:
            user_external_id: User external ID to filter results
            query: Search query text
            k: Number of results to return

        Returns:
            List of search results with relevance scores and metadata

        Raises:
            ValueError: If query is invalid or user not found
            RuntimeError: If search operation fails
        """
        try:
            # Strip and validate text inputs
            user_external_id = user_external_id.strip() if user_external_id else ""
            query = query.strip() if query else ""

            if not self.validate_query(query):
                raise ValueError("Invalid search query")

            if k <= 0 or k > 50:  # Reasonable limits
                raise ValueError("k must be between 1 and 50")

            # Verify user exists
            with self.db_service.get_session() as session:
                user = session.exec(
                    select(User).where(User.external_id == user_external_id)
                ).first()
                if not user:
                    raise ValueError(f"User not found: {user_external_id}")

            logger.info(
                f"Performing semantic search for user {user_external_id}, query: {query[:50]}..."
            )

            # Perform vector search with user filtering
            raw_results = self.embedding_service.search_similar(
                query=query, user_filter=user_external_id, k=k
            )

            # Enrich results with metadata from database
            search_results = self._enrich_with_metadata(raw_results, user.id)

            logger.info(f"Found {len(search_results)} search results")
            return search_results

        except ValueError:
            # Re-raise validation errors
            raise
        except Exception as e:
            logger.error(f"Failed to perform semantic search: {e}")
            raise RuntimeError(f"Search operation failed: {str(e)}")

    def _enrich_with_metadata(
        self, raw_results: List[Dict[str, Any]], user_id: int
    ) -> List[SearchResult]:
        """Enrich search results with database metadata.

        Args:
            raw_results: Raw results from vector search
            user_id: Internal user ID

        Returns:
            List of enriched search results
        """
        search_results = []

        with self.db_service.get_session() as session:
            for result in raw_results:
                try:
                    metadata = result.get("metadata", {})
                    report_id = metadata.get("report_id")

                    if not report_id:
                        logger.warning("Search result missing report_id, skipping")
                        continue

                    # Get report metadata from database
                    report = session.get(MedicalReport, report_id)
                    if not report or report.user_id != user_id:
                        logger.warning(f"Report {report_id} not found or access denied")
                        continue

                    search_result = SearchResult(
                        content=result.get("content", ""),
                        relevance_score=result.get("relevance_score", 0.0),
                        report_id=report_id,
                        chunk_index=metadata.get("chunk_index", 0),
                        filename=report.filename,
                        created_at=report.created_at,
                        user_external_id=metadata.get("user_external_id", ""),
                        metadata=metadata,
                    )
                    search_results.append(search_result)

                except Exception as e:
                    logger.error(f"Failed to enrich search result: {e}")
                    continue

        # Sort by relevance score (highest first)
        search_results.sort(key=lambda x: x.relevance_score, reverse=True)
        return search_results

    def get_search_stats(self, user_external_id: str) -> Dict[str, Any]:
        """Get search statistics for a user.

        Args:
            user_external_id: User external ID

        Returns:
            Dictionary with search statistics
        """
        try:
            # Strip text input
            user_external_id = user_external_id.strip() if user_external_id else ""

            with self.db_service.get_session() as session:
                user = session.exec(
                    select(User).where(User.external_id == user_external_id)
                ).first()
                if not user:
                    return {"error": "User not found"}

                # Get user's reports count
                reports_count = len(
                    session.exec(
                        select(MedicalReport).where(MedicalReport.user_id == user.id)
                    ).all()
                )

                # Get collection stats from embedding service
                collection_stats = self.embedding_service.get_collection_stats()

                return {
                    "user_external_id": user_external_id,
                    "reports_count": reports_count,
                    "total_chunks": collection_stats.get("total_chunks", 0),
                    "embedding_model": self.config.embedding_model,
                }

        except Exception as e:
            logger.error(f"Failed to get search stats: {e}")
            return {"error": str(e)}

    def refresh_vector_database(self) -> Dict[str, Any]:
        """Refresh the vector database collection to handle external updates.

        This method should be called when ChromaDB has been updated externally
        and you need to refresh the collection state.

        Returns:
            Dictionary with refresh status and collection info
        """
        try:
            logger.info("Refreshing vector database collection...")

            # Refresh the embedding service collection
            self.embedding_service.refresh_collection()

            # Get updated collection stats
            collection_stats = self.embedding_service.get_collection_stats()

            return {
                "status": "success",
                "message": "Vector database collection refreshed successfully",
                "collection_stats": collection_stats,
            }

        except Exception as e:
            logger.error(f"Failed to refresh vector database: {e}")
            return {
                "status": "error",
                "message": f"Failed to refresh vector database: {str(e)}",
            }
