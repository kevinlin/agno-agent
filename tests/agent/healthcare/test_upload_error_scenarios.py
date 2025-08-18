"""Error scenario tests for PDF upload functionality."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from agent.healthcare.config.config import Config
from agent.healthcare.storage.database import DatabaseService
from agent.healthcare.upload.service import PDFUploadService


class TestUploadErrorScenarios:
    """Test error scenarios and edge cases for PDF upload."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = Config(
            openai_api_key="test_key",
            base_data_dir=Path(self.temp_dir) / "data",
            uploads_dir=Path(self.temp_dir) / "data/uploads",
            reports_dir=Path(self.temp_dir) / "data/reports",
            chroma_dir=Path(self.temp_dir) / "data/chroma",
            medical_db_path=Path(self.temp_dir) / "data/medical.db",
            agent_db_path=Path(self.temp_dir) / "data/agent_sessions.db",
        )

        self.mock_db_service = MagicMock(spec=DatabaseService)
        self.service = PDFUploadService(self.config, self.mock_db_service)

    def test_validate_pdf_with_various_invalid_formats(self):
        """Test PDF validation with various invalid file formats."""
        invalid_formats = [
            b"",  # Empty file
            b"%PDF",  # Incomplete header
            b"<html><body>Fake PDF</body></html>",  # HTML
            b"\x89PNG\r\n\x1a\n",  # PNG header
            b"JFIF",  # JPEG header
            b"PK\x03\x04",  # ZIP header
            b"\x00\x00\x00\x00",  # Null bytes
            b"This is just plain text",  # Plain text
        ]

        for invalid_content in invalid_formats:
            assert self.service.validate_pdf(invalid_content) is False

    def test_validate_pdf_with_corrupted_pdf(self):
        """Test PDF validation with corrupted PDF content."""
        # Start with valid header but corrupt the rest
        corrupted_pdf = b"%PDF-1.4\n" + b"\x00" * 100 + b"corrupted data"

        # Should still pass basic validation (starts with %PDF-)
        # But might fail in actual processing
        result = self.service.validate_pdf(corrupted_pdf)
        # The result depends on the magic library's behavior
        assert isinstance(result, bool)

    def test_compute_hash_with_large_file(self):
        """Test hash computation with large file content."""
        # Create 10MB of test data
        large_content = b"test_data" * (10 * 1024 * 1024 // 9)

        hash_result = self.service.compute_hash(large_content)

        assert len(hash_result) == 64
        assert isinstance(hash_result, str)
        # Should be deterministic
        assert hash_result == self.service.compute_hash(large_content)

    def test_store_pdf_permission_error(self):
        """Test PDF storage when directory is not writable."""
        # Make upload directory read-only
        upload_dir = self.config.uploads_dir
        upload_dir.mkdir(parents=True, exist_ok=True)
        upload_dir.chmod(0o444)  # Read-only

        try:
            with pytest.raises(HTTPException) as exc_info:
                self.service.store_pdf(b"test content", "test.pdf", "testhash")

            assert exc_info.value.status_code == 500
            assert "Error storing uploaded file" in str(exc_info.value.detail)
        finally:
            # Restore permissions for cleanup
            upload_dir.chmod(0o755)

    def test_store_pdf_disk_full_simulation(self):
        """Test PDF storage when disk is full (simulated)."""
        # Mock the open function to raise OSError (disk full)
        with patch("builtins.open", side_effect=OSError("No space left on device")):
            with pytest.raises(HTTPException) as exc_info:
                self.service.store_pdf(b"test content", "test.pdf", "testhash")

            assert exc_info.value.status_code == 500

    def test_check_duplicate_database_error(self):
        """Test duplicate checking when database query fails."""
        # Mock database session to raise exception
        mock_session = MagicMock()
        mock_session.exec.side_effect = Exception("Database connection failed")
        self.mock_db_service.get_session.return_value.__enter__.return_value = (
            mock_session
        )

        with pytest.raises(HTTPException) as exc_info:
            self.service.check_duplicate(1, "test_hash")

        assert exc_info.value.status_code == 500
        assert "Error checking for duplicate files" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_upload_pdf_file_read_error(self):
        """Test upload when file reading fails."""
        mock_file = MagicMock()
        mock_file.filename = "test.pdf"
        mock_file.read.side_effect = Exception("Failed to read file")

        with pytest.raises(HTTPException) as exc_info:
            await self.service.upload_pdf("user123", mock_file)

        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_upload_pdf_user_creation_fails(self):
        """Test upload when user creation fails."""
        mock_file = MagicMock()
        mock_file.filename = "test.pdf"
        mock_file.read.return_value = b"%PDF-1.4\ntest content"

        # Mock user creation failure
        self.mock_db_service.get_or_create_user.side_effect = Exception(
            "Database error"
        )

        with pytest.raises(HTTPException) as exc_info:
            await self.service.upload_pdf("user123", mock_file)

        assert exc_info.value.status_code == 500

    def test_store_pdf_with_special_characters_in_filename(self):
        """Test PDF storage with special characters in filename."""
        special_filenames = [
            "test file with spaces.pdf",
            "test-file-with-dashes.pdf",
            "test_file_with_underscores.pdf",
            "test.file.with.dots.pdf",
            "test(file)with[brackets].pdf",
            "test&file&with&ampersands.pdf",
            "testфайл.pdf",  # Cyrillic characters
            "test文件.pdf",  # Chinese characters
        ]

        for filename in special_filenames:
            try:
                stored_path = self.service.store_pdf(
                    b"%PDF-1.4\ntest content", filename, "testhash123"
                )

                # Should create file with hash-based name regardless of original filename
                assert stored_path.exists()
                assert stored_path.name.startswith("testhash123")
                assert stored_path.suffix == ".pdf"

                # Clean up
                stored_path.unlink()
            except Exception as e:
                pytest.fail(f"Failed to store file with filename '{filename}': {e}")

    def test_store_pdf_filename_without_extension(self):
        """Test PDF storage with filename that has no extension."""
        stored_path = self.service.store_pdf(
            b"%PDF-1.4\ntest content", "filename_no_extension", "testhash123"
        )

        # Should add .pdf extension
        assert stored_path.suffix == ".pdf"
        assert stored_path.name == "testhash123.pdf"
        assert stored_path.exists()

    def test_store_pdf_filename_with_wrong_extension(self):
        """Test PDF storage with filename that has wrong extension."""
        stored_path = self.service.store_pdf(
            b"%PDF-1.4\ntest content", "document.doc", "testhash123"
        )

        # Should use original extension but still work
        assert stored_path.suffix == ".doc"
        assert stored_path.name == "testhash123.doc"
        assert stored_path.exists()

    def test_get_upload_stats_with_permission_error(self):
        """Test upload stats when directory access fails."""
        # Create upload directory first
        upload_dir = self.config.uploads_dir
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Create a file to test with
        test_file = upload_dir / "test.pdf"
        test_file.write_bytes(b"test content")

        # Make upload directory inaccessible
        upload_dir.chmod(0o000)  # No permissions

        try:
            stats = self.service.get_upload_stats()

            # Should handle error gracefully - either return error or empty stats
            assert "error" in stats or (
                stats["total_files"] == 0 and stats["total_size"] == 0
            )
        finally:
            # Restore permissions for cleanup
            upload_dir.chmod(0o755)

    def test_get_upload_stats_nonexistent_directory(self):
        """Test upload stats when directory doesn't exist."""
        # Create a temporary directory that we can safely test with
        temp_dir = tempfile.mkdtemp()
        nonexistent_dir = Path(temp_dir) / "nonexistent"

        # Use config with directory that doesn't exist yet
        config = Config(openai_api_key="test_key", uploads_dir=nonexistent_dir)

        # Mock the service initialization to avoid creating the directory
        with patch.object(PDFUploadService, "_ensure_upload_directory"):
            service = PDFUploadService(config, self.mock_db_service)

            stats = service.get_upload_stats()

            assert stats["total_files"] == 0
            assert stats["total_size"] == 0

    @pytest.mark.asyncio
    async def test_upload_pdf_boundary_file_sizes(self):
        """Test upload with files at size boundaries."""
        # Test file exactly at limit (50MB)
        max_size = 50 * 1024 * 1024

        mock_file = MagicMock()
        mock_file.filename = "test.pdf"

        # Make read() method async
        async def mock_read():
            return b"%PDF-1.4\n" + b"x" * (max_size - 9)

        mock_file.read = mock_read

        # Mock user creation
        from agent.healthcare.storage.models import User

        mock_user = User(id=1, external_id="user123")
        self.mock_db_service.get_or_create_user.return_value = mock_user
        self.service.check_duplicate = MagicMock(return_value=None)

        # Should succeed at exactly max size
        result = await self.service.upload_pdf("user123", mock_file)
        assert result["file_size"] == max_size

        # Test file over limit
        async def mock_read_large():
            return b"%PDF-1.4\n" + b"x" * max_size

        mock_file.read = mock_read_large

        with pytest.raises(HTTPException) as exc_info:
            await self.service.upload_pdf("user123", mock_file)

        assert exc_info.value.status_code == 413

    def test_upload_directory_creation_failure(self):
        """Test service initialization when directory creation fails."""
        # Mock Path.mkdir to raise exception
        with patch.object(
            Path, "mkdir", side_effect=PermissionError("Cannot create directory")
        ):
            with pytest.raises(PermissionError):
                PDFUploadService(self.config, self.mock_db_service)

    @pytest.mark.asyncio
    async def test_upload_pdf_with_empty_filename(self):
        """Test upload with empty filename."""
        mock_file = MagicMock()
        mock_file.filename = ""

        with pytest.raises(HTTPException) as exc_info:
            await self.service.upload_pdf("user123", mock_file)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_upload_pdf_with_none_filename(self):
        """Test upload with None filename."""
        mock_file = MagicMock()
        mock_file.filename = None

        with pytest.raises(HTTPException) as exc_info:
            await self.service.upload_pdf("user123", mock_file)

        assert exc_info.value.status_code == 400
