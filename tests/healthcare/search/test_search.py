"""Unit tests for search service functionality."""

from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch

import pytest

from healthcare.config.config import Config
from healthcare.search.embeddings import EmbeddingService
from healthcare.search.search_service import SearchResult, SearchService
from healthcare.storage.database import DatabaseService
from healthcare.storage.models import MedicalReport, User


class TestSearchService:
    """Test cases for SearchService."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return Config(
            openai_api_key="test-key", embedding_model="text-embedding-3-small"
        )

    @pytest.fixture
    def mock_db_service(self):
        """Create mock database service."""
        return Mock(spec=DatabaseService)

    @pytest.fixture
    def mock_embedding_service(self):
        """Create mock embedding service."""
        return Mock(spec=EmbeddingService)

    @pytest.fixture
    def search_service(self, config, mock_db_service, mock_embedding_service):
        """Create search service instance."""
        return SearchService(config, mock_db_service, mock_embedding_service)

    def _mock_session_context(self, mock_db_service, mock_session):
        """Helper to mock database session context manager."""
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_session)
        mock_context_manager.__exit__ = Mock(return_value=None)
        mock_db_service.get_session.return_value = mock_context_manager
        return mock_session

    def test_validate_query_valid(self, search_service):
        """Test query validation with valid queries."""
        assert search_service.validate_query("valid query") is True
        assert search_service.validate_query("  valid query  ") is True
        assert search_service.validate_query("a" * 100) is True

    def test_validate_query_invalid(self, search_service):
        """Test query validation with invalid queries."""
        assert search_service.validate_query("") is False
        assert search_service.validate_query("   ") is False
        assert search_service.validate_query(None) is False
        assert search_service.validate_query(123) is False
        assert search_service.validate_query("a" * 1001) is False

    def test_semantic_search_invalid_query(self, search_service):
        """Test semantic search with invalid query."""
        with pytest.raises(ValueError, match="Invalid search query"):
            search_service.semantic_search("user123", "")

    def test_semantic_search_invalid_k(self, search_service):
        """Test semantic search with invalid k parameter."""
        with pytest.raises(ValueError, match="k must be between 1 and 50"):
            search_service.semantic_search("user123", "valid query", k=0)

        with pytest.raises(ValueError, match="k must be between 1 and 50"):
            search_service.semantic_search("user123", "valid query", k=51)

    def test_semantic_search_user_not_found(self, search_service, mock_db_service):
        """Test semantic search with non-existent user."""
        # Mock database session
        mock_session = Mock()
        mock_session.exec.return_value.first.return_value = None
        self._mock_session_context(mock_db_service, mock_session)

        with pytest.raises(ValueError, match="User not found: nonexistent"):
            search_service.semantic_search("nonexistent", "valid query")

    def test_semantic_search_success(
        self, search_service, mock_db_service, mock_embedding_service
    ):
        """Test successful semantic search."""
        # Mock user
        mock_user = User(id=1, external_id="user123")

        # Mock database session for user lookup
        mock_session = Mock()
        mock_session.exec.return_value.first.return_value = mock_user
        self._mock_session_context(mock_db_service, mock_session)

        # Mock embedding service results
        raw_results = [
            {
                "content": "Patient has high blood pressure",
                "relevance_score": 0.85,
                "metadata": {
                    "report_id": 1,
                    "chunk_index": 0,
                    "user_external_id": "user123",
                },
            }
        ]
        mock_embedding_service.search_similar.return_value = raw_results

        # Mock report for enrichment - need to mock session again for enrichment
        mock_report = MedicalReport(
            id=1,
            user_id=1,
            filename="test_report.pdf",
            file_hash="hash123",
            markdown_path="/path/to/markdown",
            created_at=datetime(2023, 1, 1, 12, 0, 0),
        )
        mock_session.get.return_value = mock_report

        # Execute search
        results = search_service.semantic_search("user123", "blood pressure", k=5)

        # Verify results
        assert len(results) == 1
        result = results[0]
        assert isinstance(result, SearchResult)
        assert result.content == "Patient has high blood pressure"
        assert result.relevance_score == 0.85
        assert result.report_id == 1
        assert result.chunk_index == 0
        assert result.filename == "test_report.pdf"
        assert result.user_external_id == "user123"

        # Verify service calls
        mock_embedding_service.search_similar.assert_called_once_with(
            query="blood pressure", user_filter="user123", k=5
        )

    def test_semantic_search_empty_results(
        self, search_service, mock_db_service, mock_embedding_service
    ):
        """Test semantic search with no results."""
        # Mock user
        mock_user = User(id=1, external_id="user123")

        # Mock database session
        mock_session = Mock()
        mock_session.exec.return_value.first.return_value = mock_user
        self._mock_session_context(mock_db_service, mock_session)

        # Mock empty results
        mock_embedding_service.search_similar.return_value = []

        # Execute search
        results = search_service.semantic_search("user123", "nonexistent query", k=5)

        # Verify empty results
        assert len(results) == 0

    def test_enrich_with_metadata_missing_report_id(
        self, search_service, mock_db_service
    ):
        """Test enrichment with missing report_id in metadata."""
        raw_results = [
            {
                "content": "Some content",
                "relevance_score": 0.8,
                "metadata": {},  # Missing report_id
            }
        ]

        mock_session = Mock()
        self._mock_session_context(mock_db_service, mock_session)

        results = search_service._enrich_with_metadata(raw_results, user_id=1)
        assert len(results) == 0

    def test_enrich_with_metadata_report_not_found(
        self, search_service, mock_db_service
    ):
        """Test enrichment with non-existent report."""
        raw_results = [
            {
                "content": "Some content",
                "relevance_score": 0.8,
                "metadata": {"report_id": 999},
            }
        ]

        mock_session = Mock()
        mock_session.get.return_value = None  # Report not found
        self._mock_session_context(mock_db_service, mock_session)

        results = search_service._enrich_with_metadata(raw_results, user_id=1)
        assert len(results) == 0

    def test_enrich_with_metadata_access_denied(self, search_service, mock_db_service):
        """Test enrichment with access denied (wrong user)."""
        raw_results = [
            {
                "content": "Some content",
                "relevance_score": 0.8,
                "metadata": {"report_id": 1},
            }
        ]

        # Mock report belonging to different user
        mock_report = MedicalReport(
            id=1,
            user_id=999,  # Different user
            filename="test.pdf",
            file_hash="hash",
            markdown_path="/path",
            created_at=datetime.now(),
        )

        mock_session = Mock()
        mock_session.get.return_value = mock_report
        self._mock_session_context(mock_db_service, mock_session)

        results = search_service._enrich_with_metadata(raw_results, user_id=1)
        assert len(results) == 0

    def test_enrich_with_metadata_sorts_by_relevance(
        self, search_service, mock_db_service
    ):
        """Test that enrichment sorts results by relevance score."""
        raw_results = [
            {
                "content": "Content 1",
                "relevance_score": 0.6,
                "metadata": {
                    "report_id": 1,
                    "chunk_index": 0,
                    "user_external_id": "user123",
                },
            },
            {
                "content": "Content 2",
                "relevance_score": 0.9,
                "metadata": {
                    "report_id": 2,
                    "chunk_index": 0,
                    "user_external_id": "user123",
                },
            },
            {
                "content": "Content 3",
                "relevance_score": 0.7,
                "metadata": {
                    "report_id": 3,
                    "chunk_index": 0,
                    "user_external_id": "user123",
                },
            },
        ]

        mock_session = Mock()
        self._mock_session_context(mock_db_service, mock_session)

        # Mock reports
        def mock_get(model_class, report_id):
            return MedicalReport(
                id=report_id,
                user_id=1,
                filename=f"report_{report_id}.pdf",
                file_hash=f"hash_{report_id}",
                markdown_path="/path",
                created_at=datetime.now(),
            )

        mock_session.get.side_effect = mock_get

        results = search_service._enrich_with_metadata(raw_results, user_id=1)

        # Verify sorting (highest relevance first)
        assert len(results) == 3
        assert results[0].relevance_score == 0.9
        assert results[1].relevance_score == 0.7
        assert results[2].relevance_score == 0.6

    def test_get_search_stats_user_not_found(self, search_service, mock_db_service):
        """Test search stats with non-existent user."""
        mock_session = Mock()
        mock_session.exec.return_value.first.return_value = None
        self._mock_session_context(mock_db_service, mock_session)

        stats = search_service.get_search_stats("nonexistent")
        assert stats == {"error": "User not found"}

    def test_get_search_stats_success(
        self, search_service, mock_db_service, mock_embedding_service
    ):
        """Test successful search stats retrieval."""
        # Mock user and reports
        mock_user = User(id=1, external_id="user123")
        mock_reports = [Mock(), Mock(), Mock()]  # 3 reports

        mock_session = Mock()
        mock_session.exec.return_value.first.return_value = mock_user
        mock_session.exec.return_value.all.return_value = mock_reports
        self._mock_session_context(mock_db_service, mock_session)

        # Mock embedding service stats
        mock_embedding_service.get_collection_stats.return_value = {"total_chunks": 150}

        stats = search_service.get_search_stats("user123")

        expected = {
            "user_external_id": "user123",
            "reports_count": 3,
            "total_chunks": 150,
            "embedding_model": "text-embedding-3-small",
        }
        assert stats == expected

    def test_get_search_stats_exception_handling(self, search_service, mock_db_service):
        """Test search stats exception handling."""
        mock_db_service.get_session.side_effect = Exception("Database error")

        stats = search_service.get_search_stats("user123")
        assert "error" in stats
        assert stats["error"] == "Database error"

    def test_semantic_search_runtime_error_handling(
        self, search_service, mock_db_service, mock_embedding_service
    ):
        """Test semantic search runtime error handling."""
        # Mock user exists
        mock_user = User(id=1, external_id="user123")
        mock_session = Mock()
        mock_session.exec.return_value.first.return_value = mock_user
        self._mock_session_context(mock_db_service, mock_session)

        # Mock embedding service failure
        mock_embedding_service.search_similar.side_effect = Exception(
            "Vector search failed"
        )

        with pytest.raises(RuntimeError, match="Search operation failed"):
            search_service.semantic_search("user123", "valid query")

    def test_semantic_search_strips_whitespace(
        self, search_service, mock_db_service, mock_embedding_service
    ):
        """Test that semantic_search strips whitespace from inputs."""
        # Mock user
        mock_user = User(id=1, external_id="user123")

        # Mock database session for user lookup
        mock_session = Mock()
        mock_session.exec.return_value.first.return_value = mock_user
        self._mock_session_context(mock_db_service, mock_session)

        # Mock embedding service results
        raw_results = [
            {
                "content": "Patient has high blood pressure",
                "relevance_score": 0.85,
                "metadata": {
                    "report_id": 1,
                    "chunk_index": 0,
                    "user_external_id": "user123",
                },
            }
        ]
        mock_embedding_service.search_similar.return_value = raw_results

        # Mock report for enrichment
        mock_report = MedicalReport(
            id=1,
            user_id=1,
            filename="test.pdf",
            file_hash="hash123",
            markdown_path="/path/to/markdown",
            created_at=datetime.now(),
        )

        # Mock session.get for report enrichment
        mock_session.get.return_value = mock_report

        # Test with whitespace in inputs
        results = search_service.semantic_search("  user123  ", "  blood pressure  ", 5)

        # Verify embedding service was called with stripped values
        mock_embedding_service.search_similar.assert_called_once_with(
            query="blood pressure", user_filter="user123", k=5
        )

        # Verify results
        assert len(results) == 1
        assert results[0].content == "Patient has high blood pressure"

    def test_semantic_search_handles_none_inputs(self, search_service, mock_db_service):
        """Test that semantic_search handles None inputs gracefully."""
        # Mock database session to return no user found
        mock_session = Mock()
        mock_session.exec.return_value.first.return_value = None
        self._mock_session_context(mock_db_service, mock_session)

        # Test with None user_external_id - should strip to empty string and fail validation
        with pytest.raises(ValueError, match="User not found"):
            search_service.semantic_search(None, "valid query", 5)

        # Test with None query - should strip to empty string and fail validation
        with pytest.raises(ValueError, match="Invalid search query"):
            search_service.semantic_search("user123", None, 5)

    def test_get_search_stats_strips_whitespace(
        self, search_service, mock_db_service, mock_embedding_service
    ):
        """Test that get_search_stats strips whitespace from user_external_id."""
        # Mock user
        mock_user = User(id=1, external_id="user123")

        # Mock database session
        mock_session = Mock()
        mock_session.exec.return_value.first.return_value = mock_user
        mock_session.exec.return_value.all.return_value = []  # No reports
        self._mock_session_context(mock_db_service, mock_session)

        # Mock embedding service stats
        mock_embedding_service.get_collection_stats.return_value = {"total_chunks": 10}

        # Test with whitespace in user_external_id
        stats = search_service.get_search_stats("  user123  ")

        # Verify the user was found (whitespace stripped)
        assert stats["user_external_id"] == "user123"
        assert stats["reports_count"] == 0
        assert stats["total_chunks"] == 10

    def test_get_search_stats_handles_none_input(self, search_service, mock_db_service):
        """Test that get_search_stats handles None input gracefully."""
        # Mock database session to return no user found
        mock_session = Mock()
        mock_session.exec.return_value.first.return_value = None
        self._mock_session_context(mock_db_service, mock_session)

        # Test with None user_external_id - should strip to empty string
        stats = search_service.get_search_stats(None)

        # Should return user not found error
        assert stats == {"error": "User not found"}

    def test_validate_query_with_whitespace_only(self, search_service):
        """Test that validate_query returns False for whitespace-only strings."""
        # Test with only whitespace - should be stripped to empty and return False
        assert search_service.validate_query("   ") is False
        assert search_service.validate_query("\t\n  ") is False

        # Test with valid query with whitespace - should pass
        assert search_service.validate_query("  valid query  ") is True
