"""Unit tests for image asset retrieval routes."""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from healthcare.images.routes import (
    _check_file_exists,
    _extract_filename_from_path,
    _validate_user_access,
    get_asset_details,
    list_report_assets,
)
from healthcare.storage.models import MedicalReport, ReportAsset, User


class TestAssetRoutes:
    """Test asset retrieval routes."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_db_service = Mock()
        self.test_user_id = "test_user_123"
        self.test_report_id = 456
        self.test_asset_id = 789

    @pytest.mark.asyncio
    async def test_list_report_assets_success(self):
        """Test successful asset listing."""
        # Mock assets
        mock_assets = [
            Mock(
                id=1,
                kind="image",
                path="/path/to/page-001-img-01.png",
                alt_text="Test image 1",
                created_at=datetime(2024, 1, 15, 10, 30, 0),
            ),
            Mock(
                id=2,
                kind="image",
                path="/path/to/page-002-img-01.png",
                alt_text="Test image 2",
                created_at=datetime(2024, 1, 15, 10, 31, 0),
            ),
        ]

        # Mock database responses
        self.mock_db_service.get_report_assets.return_value = mock_assets

        # Mock access validation
        with patch(
            "healthcare.images.routes._validate_user_access"
        ) as mock_validate:
            mock_validate.return_value = True

            response = await list_report_assets(
                report_id=self.test_report_id,
                user_external_id=self.test_user_id,
                db_service=self.mock_db_service,
            )

            # Verify response
            assert isinstance(response, JSONResponse)
            content = response.body.decode()
            import json

            data = json.loads(content)

            assert data["report_id"] == self.test_report_id
            assert data["total_assets"] == 2
            assert len(data["assets"]) == 2
            assert data["assets"][0]["id"] == 1
            assert data["assets"][0]["kind"] == "image"
            assert data["assets"][0]["filename"] == "page-001-img-01.png"
            assert data["assets"][0]["alt_text"] == "Test image 1"

    @pytest.mark.asyncio
    async def test_list_report_assets_access_denied(self):
        """Test asset listing with access denied."""
        # Mock access validation failure
        with patch(
            "healthcare.images.routes._validate_user_access"
        ) as mock_validate:
            mock_validate.return_value = False

            with pytest.raises(HTTPException) as exc_info:
                await list_report_assets(
                    report_id=self.test_report_id,
                    user_external_id=self.test_user_id,
                    db_service=self.mock_db_service,
                )

            assert exc_info.value.status_code == 403
            assert "Access denied" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_list_report_assets_no_assets(self):
        """Test asset listing when no assets exist."""
        # Mock empty assets list
        self.mock_db_service.get_report_assets.return_value = []

        # Mock access validation
        with patch(
            "healthcare.images.routes._validate_user_access"
        ) as mock_validate:
            mock_validate.return_value = True

            response = await list_report_assets(
                report_id=self.test_report_id,
                user_external_id=self.test_user_id,
                db_service=self.mock_db_service,
            )

            # Verify response
            assert isinstance(response, JSONResponse)
            content = response.body.decode()
            import json

            data = json.loads(content)

            assert data["report_id"] == self.test_report_id
            assert data["total_assets"] == 0
            assert len(data["assets"]) == 0
            assert "No assets found" in data["message"]

    @pytest.mark.asyncio
    async def test_list_report_assets_database_error(self):
        """Test asset listing with database error."""
        # Mock database error
        self.mock_db_service.get_report_assets.side_effect = Exception("Database error")

        # Mock access validation
        with patch(
            "healthcare.images.routes._validate_user_access"
        ) as mock_validate:
            mock_validate.return_value = True

            with pytest.raises(HTTPException) as exc_info:
                await list_report_assets(
                    report_id=self.test_report_id,
                    user_external_id=self.test_user_id,
                    db_service=self.mock_db_service,
                )

            assert exc_info.value.status_code == 500
            assert "error occurred" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_asset_details_success(self):
        """Test successful asset detail retrieval."""
        # Mock database session and query
        mock_session = MagicMock()
        mock_asset = Mock(
            id=self.test_asset_id,
            report_id=self.test_report_id,
            kind="image",
            path="/path/to/test-image.png",
            alt_text="Test image",
            created_at=datetime(2024, 1, 15, 10, 30, 0),
        )

        mock_session.exec.return_value.first.return_value = mock_asset
        self.mock_db_service.get_session.return_value = MagicMock()
        self.mock_db_service.get_session.return_value = MagicMock()
        self.mock_db_service.get_session.return_value.__enter__.return_value = (
            mock_session
        )
        self.mock_db_service.get_session.return_value.__exit__.return_value = None
        self.mock_db_service.get_session.return_value.__exit__.return_value = None

        # Mock access validation and file check
        with (
            patch(
                "healthcare.images.routes._validate_user_access"
            ) as mock_validate,
            patch(
                "healthcare.images.routes._check_file_exists"
            ) as mock_file_check,
        ):
            mock_validate.return_value = True
            mock_file_check.return_value = True

            response = await get_asset_details(
                report_id=self.test_report_id,
                asset_id=self.test_asset_id,
                user_external_id=self.test_user_id,
                db_service=self.mock_db_service,
            )

            # Verify response
            assert isinstance(response, JSONResponse)
            content = response.body.decode()
            import json

            data = json.loads(content)

            assert data["asset"]["id"] == self.test_asset_id
            assert data["asset"]["report_id"] == self.test_report_id
            assert data["asset"]["kind"] == "image"
            assert data["asset"]["filename"] == "test-image.png"
            assert data["asset"]["file_exists"] is True

    @pytest.mark.asyncio
    async def test_get_asset_details_not_found(self):
        """Test asset detail retrieval when asset not found."""
        # Mock database session with no result
        mock_session = MagicMock()
        mock_session.exec.return_value.first.return_value = None
        self.mock_db_service.get_session.return_value = MagicMock()
        self.mock_db_service.get_session.return_value.__enter__.return_value = (
            mock_session
        )
        self.mock_db_service.get_session.return_value.__exit__.return_value = None

        # Mock access validation
        with patch(
            "healthcare.images.routes._validate_user_access"
        ) as mock_validate:
            mock_validate.return_value = True

            with pytest.raises(HTTPException) as exc_info:
                await get_asset_details(
                    report_id=self.test_report_id,
                    asset_id=self.test_asset_id,
                    user_external_id=self.test_user_id,
                    db_service=self.mock_db_service,
                )

            assert exc_info.value.status_code == 404
            assert f"Asset {self.test_asset_id} not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_asset_details_access_denied(self):
        """Test asset detail retrieval with access denied."""
        # Mock access validation failure
        with patch(
            "healthcare.images.routes._validate_user_access"
        ) as mock_validate:
            mock_validate.return_value = False

            with pytest.raises(HTTPException) as exc_info:
                await get_asset_details(
                    report_id=self.test_report_id,
                    asset_id=self.test_asset_id,
                    user_external_id=self.test_user_id,
                    db_service=self.mock_db_service,
                )

            assert exc_info.value.status_code == 403
            assert "Access denied" in exc_info.value.detail


class TestAccessValidation:
    """Test access validation functions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_db_service = Mock()
        self.test_user_external_id = "test_user_123"
        self.test_report_id = 456

    def test_validate_user_access_success(self):
        """Test successful user access validation."""
        # Mock database session and queries
        mock_session = MagicMock()
        mock_user = Mock(id=123, external_id=self.test_user_external_id)
        mock_report = Mock(id=self.test_report_id, user_id=123)

        # Mock query results
        mock_session.exec.return_value.first.side_effect = [mock_user, mock_report]
        self.mock_db_service.get_session.return_value = MagicMock()
        self.mock_db_service.get_session.return_value.__enter__.return_value = (
            mock_session
        )
        self.mock_db_service.get_session.return_value.__exit__.return_value = None

        result = _validate_user_access(
            self.test_report_id, self.test_user_external_id, self.mock_db_service
        )

        assert result is True

    def test_validate_user_access_user_not_found(self):
        """Test access validation when user not found."""
        # Mock database session with no user
        mock_session = MagicMock()
        mock_session.exec.return_value.first.return_value = None
        self.mock_db_service.get_session.return_value = MagicMock()
        self.mock_db_service.get_session.return_value.__enter__.return_value = (
            mock_session
        )
        self.mock_db_service.get_session.return_value.__exit__.return_value = None

        result = _validate_user_access(
            self.test_report_id, self.test_user_external_id, self.mock_db_service
        )

        assert result is False

    def test_validate_user_access_report_not_found(self):
        """Test access validation when report not found for user."""
        # Mock database session
        mock_session = MagicMock()
        mock_user = Mock(id=123, external_id=self.test_user_external_id)

        # Mock query results - user found, report not found
        mock_session.exec.return_value.first.side_effect = [mock_user, None]
        self.mock_db_service.get_session.return_value = MagicMock()
        self.mock_db_service.get_session.return_value.__enter__.return_value = (
            mock_session
        )
        self.mock_db_service.get_session.return_value.__exit__.return_value = None

        result = _validate_user_access(
            self.test_report_id, self.test_user_external_id, self.mock_db_service
        )

        assert result is False

    def test_validate_user_access_database_error(self):
        """Test access validation with database error."""
        # Mock database error
        self.mock_db_service.get_session.side_effect = Exception(
            "Database connection failed"
        )

        result = _validate_user_access(
            self.test_report_id, self.test_user_external_id, self.mock_db_service
        )

        assert result is False


class TestUtilityFunctions:
    """Test utility functions."""

    def test_extract_filename_from_path(self):
        """Test filename extraction from file paths."""
        # Test various path formats
        assert _extract_filename_from_path("/path/to/file.png") == "file.png"
        # Use a path that works on all platforms
        assert _extract_filename_from_path("path/to/image.jpg") == "image.jpg"
        assert (
            _extract_filename_from_path("page-001-img-01.png") == "page-001-img-01.png"
        )
        assert (
            _extract_filename_from_path("/complex/nested/path/report-figure-1.png")
            == "report-figure-1.png"
        )

    def test_check_file_exists(self):
        """Test file existence checking."""
        # Since the function does local import, let's test with real paths that we control
        import os
        import tempfile

        # Test with existing file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name
            assert _check_file_exists(temp_path) is True
            os.unlink(temp_path)  # Clean up

        # Test with non-existent file
        assert _check_file_exists("/definitely/does/not/exist.png") is False

    def test_check_file_exists_exception(self):
        """Test file existence checking with exception."""
        # Test that the function handles exceptions gracefully
        # We'll mock the Path constructor to raise an exception

        with patch("builtins.__import__") as mock_import:

            def side_effect(name, *args, **kwargs):
                if name == "pathlib":
                    raise ImportError("Mocked pathlib import error")
                return __import__(name, *args, **kwargs)

            mock_import.side_effect = side_effect
            result = _check_file_exists("/some/path")
            assert result is False
