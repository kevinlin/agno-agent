"""Integration tests for report management API endpoints."""

import json
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from agent.healthcare.main import create_app
from agent.healthcare.reports.routes import get_report_service
from agent.healthcare.reports.service import ReportService


class TestReportsIntegration:
    """Integration tests for report management endpoints."""

    @pytest.fixture
    def mock_report_service(self):
        """Create mock report service."""
        return Mock(spec=ReportService)

    @pytest.fixture
    def app_with_reports(self, mock_report_service):
        """Create FastAPI app with mocked report service."""
        app = create_app()

        # Store the mock report service in app state
        app.state.report_service = mock_report_service

        # Add report routes
        from agent.healthcare.reports import router as reports_router

        app.include_router(reports_router)

        # Override the dependency
        app.dependency_overrides[get_report_service] = lambda: mock_report_service

        return app

    @pytest.fixture
    def client(self, app_with_reports):
        """Create test client."""
        return TestClient(app_with_reports)

    def test_list_reports_success(self, client, mock_report_service):
        """Test successful report listing endpoint."""
        # Setup mock response
        mock_report_service.list_user_reports.return_value = [
            {
                "id": 1,
                "filename": "report1.pdf",
                "created_at": "2024-01-01T00:00:00+00:00",
                "language": "en",
                "file_hash": "abcd12345678",
                "has_images": True,
                "manifest": {"figures": [], "tables": []},
            },
            {
                "id": 2,
                "filename": "report2.pdf",
                "created_at": "2024-01-02T00:00:00+00:00",
                "language": "en",
                "file_hash": "efgh87654321",
                "has_images": False,
                "manifest": {"figures": [], "tables": []},
            },
        ]

        # Make request
        response = client.get("/api/reports/test_user")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["user_external_id"] == "test_user"
        assert len(data["reports"]) == 2
        assert data["reports"][0]["id"] == 1
        assert data["reports"][0]["filename"] == "report1.pdf"
        assert data["reports"][0]["has_images"] is True
        assert data["reports"][1]["id"] == 2
        assert data["reports"][1]["has_images"] is False

        # Verify service call
        mock_report_service.list_user_reports.assert_called_once_with("test_user")

    def test_list_reports_user_not_found(self, client, mock_report_service):
        """Test report listing when user not found."""
        # Setup mock to raise ValueError
        mock_report_service.list_user_reports.side_effect = ValueError(
            "User not found: nonexistent_user"
        )

        # Make request
        response = client.get("/api/reports/nonexistent_user")

        # Assertions
        assert response.status_code == 404
        data = response.json()
        assert "User not found" in data["detail"]

    def test_list_reports_validation_error(self, client, mock_report_service):
        """Test report listing with validation error."""
        # Setup mock to raise ValueError
        mock_report_service.list_user_reports.side_effect = ValueError(
            "User external ID is required"
        )

        # Make request
        response = client.get("/api/reports/test_user")

        # Assertions
        assert response.status_code == 400
        data = response.json()
        assert "User external ID is required" in data["detail"]

    def test_list_reports_runtime_error(self, client, mock_report_service):
        """Test report listing with runtime error."""
        # Setup mock to raise RuntimeError
        mock_report_service.list_user_reports.side_effect = RuntimeError(
            "Report listing failed: database error"
        )

        # Make request
        response = client.get("/api/reports/test_user")

        # Assertions
        assert response.status_code == 500
        data = response.json()
        assert "Report listing failed" in data["detail"]

    def test_list_reports_unexpected_error(self, client, mock_report_service):
        """Test report listing with unexpected error."""
        # Setup mock to raise unexpected exception
        mock_report_service.list_user_reports.side_effect = Exception(
            "Unexpected error"
        )

        # Make request
        response = client.get("/api/reports/test_user")

        # Assertions
        assert response.status_code == 500
        data = response.json()
        assert "Internal report listing error" in data["detail"]

    def test_get_report_markdown_success(self, client, mock_report_service):
        """Test successful markdown retrieval endpoint."""
        # Setup mock responses
        markdown_content = "# Test Report\n\nThis is test content."
        mock_report_service.get_report_markdown.return_value = markdown_content
        mock_report_service.get_report_summary.return_value = {
            "filename": "test_report.pdf",
            "created_at": "2024-01-01T00:00:00+00:00",
        }

        # Make request
        response = client.get("/api/reports/123/markdown?user_external_id=test_user")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["report_id"] == 123
        assert data["filename"] == "test_report.pdf"
        assert data["content"] == markdown_content
        assert data["content_length"] == len(markdown_content)

        # Verify service calls
        mock_report_service.get_report_markdown.assert_called_once_with(
            123, "test_user"
        )
        mock_report_service.get_report_summary.assert_called_once_with(123, "test_user")

    def test_get_report_markdown_access_denied(self, client, mock_report_service):
        """Test markdown retrieval with access denied."""
        # Setup mock to raise access denied error
        mock_report_service.get_report_markdown.side_effect = ValueError(
            "Access denied to report 123 for user test_user"
        )

        # Make request
        response = client.get("/api/reports/123/markdown?user_external_id=test_user")

        # Assertions
        assert response.status_code == 403
        data = response.json()
        assert "Access denied" in data["detail"]

    def test_get_report_markdown_not_found(self, client, mock_report_service):
        """Test markdown retrieval when report not found."""
        # Setup mock to raise not found error
        mock_report_service.get_report_markdown.side_effect = ValueError(
            "Report not found: 999"
        )

        # Make request
        response = client.get("/api/reports/999/markdown?user_external_id=test_user")

        # Assertions
        assert response.status_code == 404
        data = response.json()
        assert "Report not found" in data["detail"]

    def test_get_report_markdown_file_not_found(self, client, mock_report_service):
        """Test markdown retrieval when file not found."""
        # Setup mock to raise FileNotFoundError
        mock_report_service.get_report_markdown.side_effect = FileNotFoundError(
            "Markdown file not found: /path/to/file.md"
        )

        # Make request
        response = client.get("/api/reports/123/markdown?user_external_id=test_user")

        # Assertions
        assert response.status_code == 404
        data = response.json()
        assert "Markdown file not found" in data["detail"]

    def test_get_report_markdown_missing_user_id(self, client, mock_report_service):
        """Test markdown retrieval without user_external_id parameter."""
        # Make request without user_external_id
        response = client.get("/api/reports/123/markdown")

        # Assertions
        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "field required" in str(data["detail"]).lower()

    def test_list_report_assets_success(self, client, mock_report_service):
        """Test successful asset listing endpoint."""
        # Setup mock response
        mock_report_service.list_report_assets.return_value = [
            {
                "id": 1,
                "kind": "image",
                "filename": "image1.png",
                "path": "/path/to/image1.png",
                "alt_text": "Test image 1",
                "page_number": 1,
                "created_at": "2024-01-01T00:00:00+00:00",
                "file_exists": True,
                "file_size": 1024,
            },
            {
                "id": 2,
                "kind": "table",
                "filename": "table1.csv",
                "path": "/path/to/table1.csv",
                "alt_text": None,
                "page_number": 2,
                "created_at": "2024-01-01T00:00:00+00:00",
                "file_exists": False,
                "file_size": 0,
            },
        ]

        # Make request
        response = client.get("/api/reports/123/assets?user_external_id=test_user")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["report_id"] == 123
        assert len(data["assets"]) == 2
        assert data["assets"][0]["id"] == 1
        assert data["assets"][0]["kind"] == "image"
        assert data["assets"][0]["file_exists"] is True
        assert data["assets"][1]["id"] == 2
        assert data["assets"][1]["kind"] == "table"
        assert data["assets"][1]["file_exists"] is False

        # Verify service call
        mock_report_service.list_report_assets.assert_called_once_with(123, "test_user")

    def test_list_report_assets_access_denied(self, client, mock_report_service):
        """Test asset listing with access denied."""
        # Setup mock to raise access denied error
        mock_report_service.list_report_assets.side_effect = ValueError(
            "Access denied to report 123 for user test_user"
        )

        # Make request
        response = client.get("/api/reports/123/assets?user_external_id=test_user")

        # Assertions
        assert response.status_code == 403
        data = response.json()
        assert "Access denied" in data["detail"]

    def test_get_report_summary_success(self, client, mock_report_service):
        """Test successful report summary endpoint."""
        # Setup mock response
        mock_report_service.get_report_summary.return_value = {
            "id": 123,
            "filename": "test_report.pdf",
            "file_hash": "abcd1234567890",
            "language": "en",
            "created_at": "2024-01-01T00:00:00+00:00",
            "markdown_path": "/path/to/report.md",
            "markdown_exists": True,
            "markdown_size": 2048,
            "images_dir": "/path/to/images",
            "asset_count": 3,
            "metadata": {"test": "data"},
        }

        # Make request
        response = client.get("/api/reports/123/summary?user_external_id=test_user")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 123
        assert data["filename"] == "test_report.pdf"
        assert data["markdown_exists"] is True
        assert data["markdown_size"] == 2048
        assert data["asset_count"] == 3
        assert data["metadata"] == {"test": "data"}

        # Verify service call
        mock_report_service.get_report_summary.assert_called_once_with(123, "test_user")

    def test_get_report_stats_success(self, client, mock_report_service):
        """Test successful report statistics endpoint."""
        # Setup mock response
        mock_report_service.get_report_stats.return_value = {
            "user_external_id": "test_user",
            "total_reports": 5,
            "total_assets": 12,
            "total_markdown_size": 10240,
            "languages": {"en": 4, "es": 1},
            "user_created_at": "2024-01-01T00:00:00+00:00",
        }

        # Make request
        response = client.get("/api/reports/test_user/stats")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["user_external_id"] == "test_user"
        assert data["total_reports"] == 5
        assert data["total_assets"] == 12
        assert data["total_markdown_size"] == 10240
        assert data["languages"] == {"en": 4, "es": 1}

        # Verify service call
        mock_report_service.get_report_stats.assert_called_once_with("test_user")

    def test_get_report_stats_user_not_found(self, client, mock_report_service):
        """Test report statistics when user not found."""
        # Setup mock to raise ValueError
        mock_report_service.get_report_stats.side_effect = ValueError(
            "User not found: nonexistent_user"
        )

        # Make request
        response = client.get("/api/reports/nonexistent_user/stats")

        # Assertions
        assert response.status_code == 404
        data = response.json()
        assert "User not found" in data["detail"]

    def test_service_not_initialized(self):
        """Test endpoints when report service is not initialized."""
        # Create app without report service in state
        app = create_app()

        # Add report routes but don't set up the service in app state
        from agent.healthcare.reports import router as reports_router

        app.include_router(reports_router)

        client_no_service = TestClient(app)

        # Make request
        response = client_no_service.get("/api/reports/test_user")

        # Assertions
        assert response.status_code == 503
        data = response.json()
        assert "Report service not initialized" in data["detail"]

    def test_pydantic_model_validation(self, client, mock_report_service):
        """Test that Pydantic models validate response data correctly."""
        # Setup mock with invalid data (missing required fields)
        mock_report_service.list_user_reports.return_value = [
            {
                "id": 1,
                "filename": "report1.pdf",
                "created_at": "2024-01-01T00:00:00+00:00",
                "language": "en",
                "file_hash": "abcd12345678",
                "has_images": True,
                "manifest": {"figures": [], "tables": []},
            }
        ]

        # Make request
        response = client.get("/api/reports/test_user")

        # Should succeed because all required fields are present
        assert response.status_code == 200
        data = response.json()
        assert "reports" in data
        assert "total" in data
        assert "user_external_id" in data

    def test_error_response_format(self, client, mock_report_service):
        """Test that error responses follow consistent format."""
        # Setup mock to raise ValueError
        mock_report_service.list_user_reports.side_effect = ValueError(
            "Test error message"
        )

        # Make request
        response = client.get("/api/reports/test_user")

        # Assertions
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert data["detail"] == "Test error message"

    def test_route_parameter_validation(self, client, mock_report_service):
        """Test route parameter validation."""
        # Test with invalid report_id (non-integer)
        response = client.get(
            "/api/reports/invalid_id/markdown?user_external_id=test_user"
        )

        # Should return validation error
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_query_parameter_validation(self, client, mock_report_service):
        """Test query parameter validation."""
        # Test endpoints that require user_external_id query parameter
        endpoints = [
            "/api/reports/123/markdown",
            "/api/reports/123/assets",
            "/api/reports/123/summary",
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 422  # Missing required query parameter
