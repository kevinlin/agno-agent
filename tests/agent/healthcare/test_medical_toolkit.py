"""Unit tests for medical toolkit."""

from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from agent.healthcare.agent.toolkit import MedicalToolkit
from agent.healthcare.config.config import Config
from agent.healthcare.search.search_service import SearchResult


class TestMedicalToolkit:
    """Test suite for MedicalToolkit class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Mock configuration
        self.config = Config(openai_api_key="test-key", base_data_dir=Path("test_data"))

        # Mock services
        self.mock_db_service = Mock()
        self.mock_search_service = Mock()
        self.mock_report_service = Mock()

        # Create toolkit instance
        self.toolkit = MedicalToolkit(
            config=self.config,
            db_service=self.mock_db_service,
            search_service=self.mock_search_service,
            report_service=self.mock_report_service,
        )

    def test_init(self):
        """Test toolkit initialization."""
        assert self.toolkit.config == self.config
        assert self.toolkit.db_service == self.mock_db_service
        assert self.toolkit.search_service == self.mock_search_service
        assert self.toolkit.report_service == self.mock_report_service

    def test_ingest_pdf_valid_inputs(self):
        """Test PDF ingestion with valid inputs."""
        # Create a temporary test file
        test_pdf = Path("test_report.pdf")
        test_pdf.touch()

        try:
            result = self.toolkit.ingest_pdf("user123", str(test_pdf))

            # Should return helpful message about using upload endpoint
            assert "POST /api/ingest" in result
            assert "user123" in result
            assert "test_report.pdf" in result

        finally:
            # Clean up
            if test_pdf.exists():
                test_pdf.unlink()

    def test_ingest_pdf_missing_user_id(self):
        """Test PDF ingestion with missing user ID."""
        with pytest.raises(ValueError, match="User external ID is required"):
            self.toolkit.ingest_pdf("", "/path/to/test.pdf")

        with pytest.raises(ValueError, match="User external ID is required"):
            self.toolkit.ingest_pdf("   ", "/path/to/test.pdf")

    def test_ingest_pdf_missing_path(self):
        """Test PDF ingestion with missing path."""
        with pytest.raises(ValueError, match="PDF path is required"):
            self.toolkit.ingest_pdf("user123", "")

        with pytest.raises(ValueError, match="PDF path is required"):
            self.toolkit.ingest_pdf("user123", "   ")

    def test_ingest_pdf_file_not_found(self):
        """Test PDF ingestion with non-existent file."""
        with pytest.raises(ValueError, match="PDF file not found"):
            self.toolkit.ingest_pdf("user123", "/nonexistent/file.pdf")

    def test_ingest_pdf_invalid_file_type(self):
        """Test PDF ingestion with invalid file type."""
        # Create a temporary non-PDF file
        test_file = Path("test_report.txt")
        test_file.touch()

        try:
            with pytest.raises(ValueError, match="File must be a PDF"):
                self.toolkit.ingest_pdf("user123", str(test_file))
        finally:
            # Clean up
            if test_file.exists():
                test_file.unlink()

    def test_list_reports_success(self):
        """Test successful report listing."""
        # Mock report service response
        mock_reports = [
            {"id": 1, "filename": "report1.pdf", "created_at": "2024-01-15T10:30:00"},
            {"id": 2, "filename": "report2.pdf", "created_at": "2024-01-16T14:45:00"},
        ]
        self.mock_report_service.list_user_reports.return_value = mock_reports

        result = self.toolkit.list_reports("user123")

        assert len(result) == 2
        assert "Report ID: 1" in result[0]
        assert "report1.pdf" in result[0]
        assert "2024-01-15T10:30:00" in result[0]
        assert "Report ID: 2" in result[1]
        assert "report2.pdf" in result[1]

        self.mock_report_service.list_user_reports.assert_called_once_with("user123")

    def test_list_reports_no_reports(self):
        """Test report listing with no reports."""
        self.mock_report_service.list_user_reports.return_value = []

        result = self.toolkit.list_reports("user123")

        assert len(result) == 1
        assert "No medical reports found" in result[0]
        assert "user123" in result[0]

    def test_list_reports_missing_user_id(self):
        """Test report listing with missing user ID."""
        with pytest.raises(ValueError, match="User external ID is required"):
            self.toolkit.list_reports("")

        with pytest.raises(ValueError, match="User external ID is required"):
            self.toolkit.list_reports("   ")

    def test_list_reports_service_error(self):
        """Test report listing with service error."""
        self.mock_report_service.list_user_reports.side_effect = Exception(
            "Database error"
        )

        with pytest.raises(RuntimeError, match="Failed to list reports"):
            self.toolkit.list_reports("user123")

    def test_search_medical_data_success(self):
        """Test successful medical data search."""
        # Mock search results
        mock_results = [
            SearchResult(
                content="Blood pressure reading: 120/80 mmHg",
                relevance_score=0.95,
                report_id=1,
                chunk_index=0,
                filename="checkup.pdf",
                created_at=datetime(2024, 1, 15, 10, 30),
                user_external_id="user123",
                metadata={"page": 1},
            ),
            SearchResult(
                content="Cholesterol levels within normal range",
                relevance_score=0.87,
                report_id=2,
                chunk_index=1,
                filename="bloodwork.pdf",
                created_at=datetime(2024, 1, 16, 14, 45),
                user_external_id="user123",
                metadata={"page": 2},
            ),
        ]
        self.mock_search_service.semantic_search.return_value = mock_results

        result = self.toolkit.search_medical_data("user123", "blood pressure", 5)

        assert len(result) == 2

        # Check first result
        assert result[0]["content"] == "Blood pressure reading: 120/80 mmHg"
        assert result[0]["relevance_score"] == 0.95
        assert result[0]["source"]["report_id"] == 1
        assert result[0]["source"]["filename"] == "checkup.pdf"
        assert result[0]["metadata"]["page"] == 1

        # Check second result
        assert result[1]["content"] == "Cholesterol levels within normal range"
        assert result[1]["relevance_score"] == 0.87
        assert result[1]["source"]["report_id"] == 2

        self.mock_search_service.semantic_search.assert_called_once_with(
            user_external_id="user123", query="blood pressure", k=5
        )

    def test_search_medical_data_no_results(self):
        """Test medical data search with no results."""
        self.mock_search_service.semantic_search.return_value = []

        result = self.toolkit.search_medical_data("user123", "rare condition", 5)

        assert len(result) == 1
        assert "No results found" in result[0]["message"]
        assert result[0]["query"] == "rare condition"
        assert result[0]["user_id"] == "user123"

    def test_search_medical_data_invalid_inputs(self):
        """Test medical data search with invalid inputs."""
        # Missing user ID
        with pytest.raises(ValueError, match="User external ID is required"):
            self.toolkit.search_medical_data("", "query", 5)

        # Missing query
        with pytest.raises(ValueError, match="Search query is required"):
            self.toolkit.search_medical_data("user123", "", 5)

    def test_search_medical_data_k_bounds(self):
        """Test medical data search k parameter bounds."""
        self.mock_search_service.semantic_search.return_value = []

        # Test k too small (should be clamped to 1)
        self.toolkit.search_medical_data("user123", "query", 0)
        self.mock_search_service.semantic_search.assert_called_with(
            user_external_id="user123", query="query", k=1
        )

        # Test k too large (should be clamped to 20)
        self.toolkit.search_medical_data("user123", "query", 100)
        self.mock_search_service.semantic_search.assert_called_with(
            user_external_id="user123", query="query", k=20
        )

    def test_search_medical_data_service_error(self):
        """Test medical data search with service error."""
        self.mock_search_service.semantic_search.side_effect = Exception("Search error")

        with pytest.raises(RuntimeError, match="Search failed"):
            self.toolkit.search_medical_data("user123", "query", 5)

    def test_get_report_content_success(self):
        """Test successful report content retrieval."""
        mock_content = "# Medical Report\n\nPatient shows good health indicators..."
        self.mock_report_service.get_report_markdown.return_value = mock_content

        result = self.toolkit.get_report_content("user123", 1)

        assert result == mock_content
        self.mock_report_service.get_report_markdown.assert_called_once_with(
            report_id=1, user_external_id="user123"
        )

    def test_get_report_content_invalid_inputs(self):
        """Test report content retrieval with invalid inputs."""
        # Missing user ID
        with pytest.raises(ValueError, match="User external ID is required"):
            self.toolkit.get_report_content("", 1)

        # Invalid report ID
        with pytest.raises(ValueError, match="Valid report ID is required"):
            self.toolkit.get_report_content("user123", 0)

        with pytest.raises(ValueError, match="Valid report ID is required"):
            self.toolkit.get_report_content("user123", -1)

    def test_get_report_content_service_error(self):
        """Test report content retrieval with service error."""
        self.mock_report_service.get_report_markdown.side_effect = Exception(
            "Access error"
        )

        with pytest.raises(RuntimeError, match="Failed to retrieve report content"):
            self.toolkit.get_report_content("user123", 1)

    def test_get_report_summary_success(self):
        """Test successful report summary generation."""
        # Mock report listing
        mock_reports = [
            {"id": 1, "filename": "report1.pdf", "created_at": "2024-01-15T10:30:00"}
        ]
        self.mock_report_service.list_user_reports.return_value = mock_reports

        # Mock assets
        mock_assets = [
            {"kind": "image", "filename": "image1.png"},
            {"kind": "image", "filename": "image2.png"},
            {"kind": "table", "filename": "table1.csv"},
        ]
        self.mock_report_service.list_report_assets.return_value = mock_assets

        # Mock content
        mock_content = (
            "# Medical Report\n\n" + "A" * 600
        )  # Long content for preview test
        self.mock_report_service.get_report_markdown.return_value = mock_content

        result = self.toolkit.get_report_summary("user123", 1)

        assert result["report_id"] == 1
        assert result["filename"] == "report1.pdf"
        assert result["created_at"] == "2024-01-15T10:30:00"
        assert result["asset_count"] == 3
        assert result["image_count"] == 2
        assert result["user_external_id"] == "user123"
        assert len(result["content_preview"]) == 503  # 500 chars + "..."
        assert result["content_preview"].endswith("...")

    def test_get_report_summary_report_not_found(self):
        """Test report summary for non-existent report."""
        self.mock_report_service.list_user_reports.return_value = []

        with pytest.raises(ValueError, match="Report 1 not found"):
            self.toolkit.get_report_summary("user123", 1)

    def test_get_report_summary_invalid_inputs(self):
        """Test report summary with invalid inputs."""
        # Missing user ID
        with pytest.raises(ValueError, match="User external ID is required"):
            self.toolkit.get_report_summary("", 1)

        # Invalid report ID
        with pytest.raises(ValueError, match="Valid report ID is required"):
            self.toolkit.get_report_summary("user123", 0)

    def test_get_report_summary_service_errors(self):
        """Test report summary with service errors handled gracefully."""
        # Mock report listing
        mock_reports = [
            {"id": 1, "filename": "report1.pdf", "created_at": "2024-01-15T10:30:00"}
        ]
        self.mock_report_service.list_user_reports.return_value = mock_reports

        # Mock assets error (should not break summary)
        self.mock_report_service.list_report_assets.side_effect = Exception(
            "Asset error"
        )

        # Mock content error (should not break summary)
        self.mock_report_service.get_report_markdown.side_effect = Exception(
            "Content error"
        )

        result = self.toolkit.get_report_summary("user123", 1)

        assert result["report_id"] == 1
        assert result["filename"] == "report1.pdf"
        assert result["asset_count"] == 0
        assert result["image_count"] == 0
        assert result["content_preview"] == "Content not available"
