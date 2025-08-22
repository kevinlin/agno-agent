"""Integration tests for search API endpoints."""

import json
from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from healthcare.main import create_app
from healthcare.search.routes import get_search_service
from healthcare.search.search_service import SearchResult, SearchService


class TestSearchIntegration:
    """Integration tests for search endpoints."""

    @pytest.fixture
    def mock_search_service(self):
        """Create mock search service."""
        return Mock(spec=SearchService)

    @pytest.fixture
    def app_with_search(self, mock_search_service):
        """Create FastAPI app with mocked search service."""
        app = create_app()

        # Store the mock search service in app state
        app.state.search_service = mock_search_service

        # Add search routes
        from healthcare.search import router as search_router

        app.include_router(search_router)

        return app

    @pytest.fixture
    def client(self, app_with_search):
        """Create test client."""
        return TestClient(app_with_search)

    def test_search_reports_success(self, client, mock_search_service):
        """Test successful search request."""
        # Mock search results
        search_results = [
            SearchResult(
                content="Patient has elevated blood pressure readings",
                relevance_score=0.85,
                report_id=1,
                chunk_index=0,
                filename="bp_report_2023.pdf",
                created_at=datetime(2023, 6, 15, 10, 30, 0),
                user_external_id="user123",
                metadata={"report_id": 1, "chunk_index": 0},
            ),
            SearchResult(
                content="Blood pressure medication prescribed",
                relevance_score=0.72,
                report_id=2,
                chunk_index=1,
                filename="prescription_2023.pdf",
                created_at=datetime(2023, 6, 20, 14, 15, 0),
                user_external_id="user123",
                metadata={"report_id": 2, "chunk_index": 1},
            ),
        ]

        mock_search_service.semantic_search.return_value = search_results

        # Make request
        response = client.get("/api/search/user123?q=blood%20pressure&k=5")

        # Verify response
        assert response.status_code == 200
        data = response.json()

        assert data["query"] == "blood pressure"
        assert data["total_results"] == 2
        assert data["user_external_id"] == "user123"
        assert len(data["results"]) == 2

        # Check first result
        result1 = data["results"][0]
        assert result1["content"] == "Patient has elevated blood pressure readings"
        assert result1["relevance_score"] == 0.85
        assert result1["report_id"] == 1
        assert result1["chunk_index"] == 0
        assert result1["filename"] == "bp_report_2023.pdf"
        assert result1["created_at"] == "2023-06-15T10:30:00"

        # Verify service was called correctly
        mock_search_service.semantic_search.assert_called_once_with(
            user_external_id="user123", query="blood pressure", k=5
        )

    def test_search_reports_empty_results(self, client, mock_search_service):
        """Test search with no results."""
        mock_search_service.semantic_search.return_value = []

        response = client.get("/api/search/user123?q=nonexistent")

        assert response.status_code == 200
        data = response.json()
        assert data["total_results"] == 0
        assert len(data["results"]) == 0

    def test_search_reports_missing_query(self, client):
        """Test search without query parameter."""
        response = client.get("/api/search/user123")
        assert response.status_code == 422  # Validation error

    def test_search_reports_empty_query(self, client):
        """Test search with empty query."""
        response = client.get("/api/search/user123?q=")
        assert response.status_code == 422  # Validation error

    def test_search_reports_query_too_long(self, client):
        """Test search with query too long."""
        long_query = "a" * 1001
        response = client.get(f"/api/search/user123?q={long_query}")
        assert response.status_code == 422  # Validation error

    def test_search_reports_invalid_k_parameter(self, client):
        """Test search with invalid k parameter."""
        # k too small
        response = client.get("/api/search/user123?q=test&k=0")
        assert response.status_code == 422

        # k too large
        response = client.get("/api/search/user123?q=test&k=21")
        assert response.status_code == 422

    def test_search_reports_default_k_parameter(self, client, mock_search_service):
        """Test search with default k parameter."""
        mock_search_service.semantic_search.return_value = []

        response = client.get("/api/search/user123?q=test")
        assert response.status_code == 200

        # Verify default k=5 was used
        mock_search_service.semantic_search.assert_called_once_with(
            user_external_id="user123", query="test", k=5
        )

    def test_search_reports_user_not_found(self, client, mock_search_service):
        """Test search with non-existent user."""
        mock_search_service.semantic_search.side_effect = ValueError(
            "User not found: nonexistent"
        )

        response = client.get("/api/search/nonexistent?q=test")
        assert response.status_code == 400
        assert "User not found" in response.json()["detail"]

    def test_search_reports_search_failure(self, client, mock_search_service):
        """Test search with service failure."""
        mock_search_service.semantic_search.side_effect = RuntimeError(
            "Search operation failed"
        )

        response = client.get("/api/search/user123?q=test")
        assert response.status_code == 500
        assert "Search operation failed" in response.json()["detail"]

    def test_search_reports_unexpected_error(self, client, mock_search_service):
        """Test search with unexpected error."""
        mock_search_service.semantic_search.side_effect = Exception("Unexpected error")

        response = client.get("/api/search/user123?q=test")
        assert response.status_code == 500
        assert "Internal search error" in response.json()["detail"]

    def test_get_search_stats_success(self, client, mock_search_service):
        """Test successful search stats request."""
        stats = {
            "user_external_id": "user123",
            "reports_count": 5,
            "total_chunks": 250,
            "embedding_model": "text-embedding-3-large",
        }
        mock_search_service.get_search_stats.return_value = stats

        response = client.get("/api/search/user123/stats")
        assert response.status_code == 200
        assert response.json() == stats

    def test_get_search_stats_user_not_found(self, client, mock_search_service):
        """Test search stats with non-existent user."""
        mock_search_service.get_search_stats.return_value = {"error": "User not found"}

        response = client.get("/api/search/nonexistent/stats")
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]

    def test_get_search_stats_service_error(self, client, mock_search_service):
        """Test search stats with service error."""
        mock_search_service.get_search_stats.return_value = {
            "error": "Database connection failed"
        }

        response = client.get("/api/search/user123/stats")
        assert response.status_code == 500
        assert "Database connection failed" in response.json()["detail"]

    def test_get_search_stats_exception(self, client, mock_search_service):
        """Test search stats with unexpected exception."""
        mock_search_service.get_search_stats.side_effect = Exception("Unexpected error")

        response = client.get("/api/search/user123/stats")
        assert response.status_code == 500
        assert "Failed to get search statistics" in response.json()["detail"]

    def test_search_response_format_validation(self, client, mock_search_service):
        """Test that search response matches expected format."""
        search_results = [
            SearchResult(
                content="Test content",
                relevance_score=0.95,
                report_id=123,
                chunk_index=2,
                filename="test.pdf",
                created_at=datetime(2023, 1, 1, 12, 0, 0),
                user_external_id="user123",
                metadata={"key": "value"},
            )
        ]
        mock_search_service.semantic_search.return_value = search_results

        response = client.get("/api/search/user123?q=test")
        assert response.status_code == 200

        data = response.json()

        # Verify response structure
        required_fields = ["results", "query", "total_results", "user_external_id"]
        for field in required_fields:
            assert field in data

        # Verify result structure
        result = data["results"][0]
        required_result_fields = [
            "content",
            "relevance_score",
            "report_id",
            "chunk_index",
            "filename",
            "created_at",
            "metadata",
        ]
        for field in required_result_fields:
            assert field in result

        # Verify data types
        assert isinstance(result["relevance_score"], float)
        assert 0.0 <= result["relevance_score"] <= 1.0
        assert isinstance(result["report_id"], int)
        assert isinstance(result["chunk_index"], int)
        assert isinstance(result["metadata"], dict)

    def test_search_url_encoding_handling(self, client, mock_search_service):
        """Test that search handles URL-encoded queries correctly."""
        mock_search_service.semantic_search.return_value = []

        # Test with URL-encoded query containing spaces and special characters
        encoded_query = "blood%20pressure%20%26%20diabetes"
        response = client.get(f"/api/search/user123?q={encoded_query}")

        assert response.status_code == 200

        # Verify the service received the decoded query
        mock_search_service.semantic_search.assert_called_once_with(
            user_external_id="user123", query="blood pressure & diabetes", k=5
        )
