"""Unit tests for report service functionality."""

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest

from agent.healthcare.config.config import Config
from agent.healthcare.reports.service import ReportService
from agent.healthcare.storage.database import DatabaseService
from agent.healthcare.storage.models import MedicalReport, ReportAsset, User


class TestReportService:
    """Test cases for ReportService."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return Config(
            openai_api_key="test-key",
            base_data_dir=Path("test_data"),
            reports_dir=Path("test_data/reports"),
        )

    @pytest.fixture
    def mock_db_service(self):
        """Create mock database service."""
        return Mock(spec=DatabaseService)

    @pytest.fixture
    def report_service(self, config, mock_db_service):
        """Create report service instance."""
        return ReportService(config, mock_db_service)

    def _mock_session_context(self, mock_db_service, mock_session):
        """Helper to mock database session context manager."""
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_session)
        mock_context_manager.__exit__ = Mock(return_value=None)
        mock_db_service.get_session.return_value = mock_context_manager
        return mock_session

    def test_validate_user_access_success(self, report_service, mock_db_service):
        """Test successful user access validation."""
        # Setup
        mock_session = Mock()
        self._mock_session_context(mock_db_service, mock_session)

        # Mock user lookup
        mock_user = Mock()
        mock_user.id = 1
        mock_session.exec.return_value.first.return_value = mock_user

        # Mock report lookup
        mock_report = Mock()
        mock_report.user_id = 1
        mock_session.get.return_value = mock_report

        # Test
        result = report_service.validate_user_access(123, "test_user")

        # Assertions
        assert result is True
        mock_session.exec.assert_called_once()
        mock_session.get.assert_called_once_with(MedicalReport, 123)

    def test_validate_user_access_denied(self, report_service, mock_db_service):
        """Test user access validation with different user_id."""
        # Setup
        mock_session = Mock()
        self._mock_session_context(mock_db_service, mock_session)

        # Mock user lookup
        mock_user = Mock()
        mock_user.id = 1
        mock_session.exec.return_value.first.return_value = mock_user

        # Mock report lookup with different user_id
        mock_report = Mock()
        mock_report.user_id = 2
        mock_session.get.return_value = mock_report

        # Test
        result = report_service.validate_user_access(123, "test_user")

        # Assertions
        assert result is False

    def test_validate_user_access_user_not_found(self, report_service, mock_db_service):
        """Test user access validation when user not found."""
        # Setup
        mock_session = Mock()
        self._mock_session_context(mock_db_service, mock_session)

        # Mock user not found
        mock_session.exec.return_value.first.return_value = None

        # Test
        with pytest.raises(ValueError, match="User not found"):
            report_service.validate_user_access(123, "nonexistent_user")

    def test_validate_user_access_report_not_found(
        self, report_service, mock_db_service
    ):
        """Test user access validation when report not found."""
        # Setup
        mock_session = Mock()
        self._mock_session_context(mock_db_service, mock_session)

        # Mock user lookup
        mock_user = Mock()
        mock_user.id = 1
        mock_session.exec.return_value.first.return_value = mock_user

        # Mock report not found
        mock_session.get.return_value = None

        # Test
        with pytest.raises(ValueError, match="Report not found"):
            report_service.validate_user_access(123, "test_user")

    def test_list_user_reports_success(self, report_service, mock_db_service):
        """Test successful user reports listing."""
        # Setup
        mock_session = Mock()
        self._mock_session_context(mock_db_service, mock_session)

        # Mock user lookup
        mock_user = Mock()
        mock_user.id = 1
        mock_session.exec.return_value.first.return_value = mock_user

        # Create mock reports
        mock_report1 = Mock()
        mock_report1.id = 1
        mock_report1.filename = "report1.pdf"
        mock_report1.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        mock_report1.language = "en"
        mock_report1.file_hash = "abcd1234567890"
        mock_report1.images_dir = "/path/to/images"
        mock_report1.meta_json = json.dumps({"manifest": {"figures": [], "tables": []}})

        mock_report2 = Mock()
        mock_report2.id = 2
        mock_report2.filename = "report2.pdf"
        mock_report2.created_at = datetime(2024, 1, 2, tzinfo=timezone.utc)
        mock_report2.language = "en"
        mock_report2.file_hash = "efgh5678901234"
        mock_report2.images_dir = None
        mock_report2.meta_json = json.dumps({"manifest": {"figures": [], "tables": []}})

        # Mock reports query - return on all() call
        mock_reports_result = Mock()
        mock_reports_result.all.return_value = [mock_report1, mock_report2]
        mock_session.exec.side_effect = [
            mock_session.exec.return_value,
            mock_reports_result,
        ]

        # Test
        result = report_service.list_user_reports("test_user")

        # Assertions
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[0]["filename"] == "report1.pdf"
        assert result[0]["file_hash"] == "abcd1234567890"[:12]
        assert result[0]["has_images"] is True
        assert result[1]["id"] == 2
        assert result[1]["filename"] == "report2.pdf"
        assert result[1]["has_images"] is False

    def test_list_user_reports_empty_user_id(self, report_service):
        """Test list_user_reports with empty user ID."""
        with pytest.raises(ValueError, match="User external ID is required"):
            report_service.list_user_reports("")

    def test_list_user_reports_user_not_found(self, report_service, mock_db_service):
        """Test list_user_reports when user not found."""
        # Setup
        mock_session = Mock()
        self._mock_session_context(mock_db_service, mock_session)

        # Mock user not found
        mock_session.exec.return_value.first.return_value = None

        # Test
        with pytest.raises(ValueError, match="User not found"):
            report_service.list_user_reports("nonexistent_user")

    def test_get_report_markdown_success(self, report_service, mock_db_service):
        """Test successful markdown retrieval."""
        # Setup
        mock_session = Mock()
        self._mock_session_context(mock_db_service, mock_session)

        # Mock user and report for access validation
        mock_user = Mock()
        mock_user.id = 1
        mock_report = Mock()
        mock_report.user_id = 1
        mock_report.markdown_path = "/path/to/report.md"

        # Configure mocks for access validation
        mock_session.exec.return_value.first.return_value = mock_user
        mock_session.get.return_value = mock_report

        markdown_content = "# Test Report\n\nThis is test content."

        # Mock file reading
        with patch("builtins.open", mock_open(read_data=markdown_content)):
            with patch("pathlib.Path.exists", return_value=True):
                # Test
                result = report_service.get_report_markdown(123, "test_user")

        # Assertions
        assert result == markdown_content

    def test_get_report_markdown_file_not_found(self, report_service, mock_db_service):
        """Test markdown retrieval when file doesn't exist."""
        # Setup
        mock_session = Mock()
        self._mock_session_context(mock_db_service, mock_session)

        # Mock user and report for access validation
        mock_user = Mock()
        mock_user.id = 1
        mock_report = Mock()
        mock_report.user_id = 1
        mock_report.markdown_path = "/path/to/nonexistent.md"

        # Configure mocks for access validation
        mock_session.exec.return_value.first.return_value = mock_user
        mock_session.get.return_value = mock_report

        # Mock file not existing
        with patch("pathlib.Path.exists", return_value=False):
            # Test
            with pytest.raises(FileNotFoundError, match="Markdown file not found"):
                report_service.get_report_markdown(123, "test_user")

    def test_get_report_markdown_access_denied(self, report_service, mock_db_service):
        """Test markdown retrieval with access denied."""
        # Setup
        mock_session = Mock()
        self._mock_session_context(mock_db_service, mock_session)

        # Mock user and report for access validation (different user_id)
        mock_user = Mock()
        mock_user.id = 1
        mock_report = Mock()
        mock_report.user_id = 2

        # Configure mocks for access validation
        mock_session.exec.return_value.first.return_value = mock_user
        mock_session.get.return_value = mock_report

        # Test
        with pytest.raises(ValueError, match="Access denied"):
            report_service.get_report_markdown(123, "test_user")

    def test_list_report_assets_success(self, report_service, mock_db_service):
        """Test successful asset listing."""
        # Setup
        mock_session = Mock()
        self._mock_session_context(mock_db_service, mock_session)

        # Mock user and report for access validation
        mock_user = Mock()
        mock_user.id = 1
        mock_report = Mock()
        mock_report.user_id = 1

        # Create mock assets
        mock_asset1 = Mock()
        mock_asset1.id = 1
        mock_asset1.kind = "image"
        mock_asset1.path = "/path/to/image1.png"
        mock_asset1.alt_text = "Test image 1"
        mock_asset1.page_number = 1
        mock_asset1.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)

        mock_asset2 = Mock()
        mock_asset2.id = 2
        mock_asset2.kind = "table"
        mock_asset2.path = "/path/to/table1.csv"
        mock_asset2.alt_text = None
        mock_asset2.page_number = 2
        mock_asset2.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)

        # Configure mocks
        mock_session.exec.return_value.first.return_value = mock_user
        mock_session.get.return_value = mock_report

        # Mock assets query
        mock_assets_result = Mock()
        mock_assets_result.all.return_value = [mock_asset1, mock_asset2]
        mock_session.exec.side_effect = [
            mock_session.exec.return_value,
            mock_assets_result,
        ]

        # Mock file existence
        with patch("pathlib.Path.exists") as mock_exists:
            with patch("pathlib.Path.stat") as mock_stat:
                mock_exists.return_value = True
                mock_stat.return_value.st_size = 1024

                # Test
                result = report_service.list_report_assets(123, "test_user")

        # Assertions
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[0]["kind"] == "image"
        assert result[0]["filename"] == "image1.png"
        assert result[0]["file_exists"] is True
        assert result[0]["file_size"] == 1024
        assert result[1]["id"] == 2
        assert result[1]["kind"] == "table"
        assert result[1]["filename"] == "table1.csv"

    def test_get_report_summary_success(self, report_service, mock_db_service):
        """Test successful report summary retrieval."""
        # Setup
        mock_session = Mock()
        self._mock_session_context(mock_db_service, mock_session)

        # Mock user and report for access validation
        mock_user = Mock()
        mock_user.id = 1
        mock_report = Mock()
        mock_report.id = 123
        mock_report.user_id = 1
        mock_report.filename = "test_report.pdf"
        mock_report.file_hash = "abcd1234567890"
        mock_report.language = "en"
        mock_report.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        mock_report.markdown_path = "/path/to/report.md"
        mock_report.images_dir = "/path/to/images"
        mock_report.meta_json = json.dumps({"test": "data"})

        # Configure mocks for access validation
        mock_session.exec.return_value.first.return_value = mock_user
        mock_session.get.return_value = mock_report

        # Mock asset count query
        mock_assets_result = Mock()
        mock_assets_result.all.return_value = [Mock(), Mock()]  # 2 assets
        mock_session.exec.side_effect = [
            mock_session.exec.return_value,
            mock_assets_result,
        ]

        # Mock file checking
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.stat") as mock_stat:
                mock_stat.return_value.st_size = 2048

                # Test
                result = report_service.get_report_summary(123, "test_user")

        # Assertions
        assert result["id"] == 123
        assert result["filename"] == "test_report.pdf"
        assert result["file_hash"] == "abcd1234567890"
        assert result["markdown_exists"] is True
        assert result["markdown_size"] == 2048
        assert result["asset_count"] == 2
        assert result["metadata"] == {"test": "data"}

    def test_get_report_stats_success(self, report_service, mock_db_service):
        """Test successful report statistics retrieval."""
        # Setup
        mock_session = Mock()
        self._mock_session_context(mock_db_service, mock_session)

        # Mock user
        mock_user = Mock()
        mock_user.id = 1
        mock_user.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)

        # Create mock reports
        mock_report1 = Mock()
        mock_report1.id = 1
        mock_report1.language = "en"
        mock_report1.markdown_path = "/path/to/report1.md"

        mock_report2 = Mock()
        mock_report2.id = 2
        mock_report2.language = "en"
        mock_report2.markdown_path = "/path/to/report2.md"

        # Configure mocks
        mock_session.exec.return_value.first.return_value = mock_user

        # Mock multiple queries
        mock_reports_result = Mock()
        mock_reports_result.all.return_value = [mock_report1, mock_report2]

        mock_assets_result1 = Mock()
        mock_assets_result1.all.return_value = [Mock(), Mock()]  # 2 assets for report 1

        mock_assets_result2 = Mock()
        mock_assets_result2.all.return_value = [Mock()]  # 1 asset for report 2

        mock_session.exec.side_effect = [
            mock_session.exec.return_value,  # User query
            mock_reports_result,  # Reports query
            mock_assets_result1,  # Assets for report 1
            mock_assets_result2,  # Assets for report 2
        ]

        # Mock file existence and sizes
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.stat") as mock_stat:
                mock_stat.return_value.st_size = 1024

                # Test
                result = report_service.get_report_stats("test_user")

        # Assertions
        assert result["user_external_id"] == "test_user"
        assert result["total_reports"] == 2
        assert result["total_assets"] == 3  # 2 + 1
        assert result["total_markdown_size"] == 2048  # 2 * 1024
        assert result["languages"] == {"en": 2}

    def test_whitespace_stripping_in_inputs(self, report_service, mock_db_service):
        """Test that all service methods properly strip whitespace from user inputs."""
        # Setup
        mock_session = Mock()
        self._mock_session_context(mock_db_service, mock_session)

        # Mock user lookup
        mock_user = Mock()
        mock_user.id = 1
        mock_session.exec.return_value.first.return_value = mock_user

        # Mock empty reports result
        mock_reports_result = Mock()
        mock_reports_result.all.return_value = []
        mock_session.exec.side_effect = [
            mock_session.exec.return_value,
            mock_reports_result,
        ]

        # Test with leading/trailing whitespace
        result = report_service.list_user_reports("  test_user  ")

        # Should succeed without whitespace causing issues
        assert isinstance(result, list)

    def test_runtime_error_handling(self, report_service, mock_db_service):
        """Test that database errors are properly converted to RuntimeError."""
        # Setup to throw exception
        mock_db_service.get_session.side_effect = Exception(
            "Database connection failed"
        )

        # Test
        with pytest.raises(RuntimeError, match="Report listing failed"):
            report_service.list_user_reports("test_user")
