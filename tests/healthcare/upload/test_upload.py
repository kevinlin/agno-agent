"""Tests for PDF upload service."""

import hashlib
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException, UploadFile

from healthcare.config.config import Config
from healthcare.storage.database import DatabaseService
from healthcare.storage.models import User
from healthcare.upload.upload_service import PDFUploadService


class TestPDFUploadService:
    """Test cases for PDFUploadService."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        self.config = Config(
            openai_api_key="test_key",
            base_data_dir=Path(self.temp_dir) / "data",
            uploads_dir=Path(self.temp_dir) / "data/uploads",
            reports_dir=Path(self.temp_dir) / "data/reports",
            chroma_dir=Path(self.temp_dir) / "data/chroma",
            medical_db_path=Path(self.temp_dir) / "data/medical.db",
            agent_db_path=Path(self.temp_dir) / "data/healthcare_agent.db",
        )

        # Mock database service
        self.mock_db_service = MagicMock(spec=DatabaseService)
        self.service = PDFUploadService(self.config, self.mock_db_service)

    def test_validate_pdf_valid_file(self):
        """Test PDF validation with valid PDF content."""
        # Valid PDF header
        valid_pdf_content = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
        assert self.service.validate_pdf(valid_pdf_content) is True

    def test_validate_pdf_invalid_file(self):
        """Test PDF validation with invalid content."""
        invalid_content = b"Not a PDF file"
        assert self.service.validate_pdf(invalid_content) is False

    def test_validate_pdf_empty_file(self):
        """Test PDF validation with empty content."""
        empty_content = b""
        assert self.service.validate_pdf(empty_content) is False

    def test_compute_hash_consistency(self):
        """Test that hash computation is consistent."""
        content = b"test content"
        hash1 = self.service.compute_hash(content)
        hash2 = self.service.compute_hash(content)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 length
        assert isinstance(hash1, str)

    def test_compute_hash_different_content(self):
        """Test that different content produces different hashes."""
        content1 = b"content one"
        content2 = b"content two"

        hash1 = self.service.compute_hash(content1)
        hash2 = self.service.compute_hash(content2)

        assert hash1 != hash2

    def test_compute_hash_matches_hashlib(self):
        """Test that computed hash matches direct hashlib usage."""
        content = b"test content for hashing"
        service_hash = self.service.compute_hash(content)

        # Compare with direct hashlib computation
        expected_hash = hashlib.sha256(content).hexdigest()
        assert service_hash == expected_hash

    def test_check_duplicate_found(self):
        """Test duplicate detection when file exists."""
        # Mock database session and query
        mock_session = MagicMock()
        self.mock_db_service.get_session.return_value.__enter__.return_value = (
            mock_session
        )

        # Mock existing report
        mock_report = MagicMock()
        mock_report.id = 123
        mock_session.exec.return_value.first.return_value = mock_report

        result = self.service.check_duplicate(1, "test_hash")
        assert result == 123

    def test_check_duplicate_not_found(self):
        """Test duplicate detection when file doesn't exist."""
        # Mock database session and query
        mock_session = MagicMock()
        self.mock_db_service.get_session.return_value.__enter__.return_value = (
            mock_session
        )

        # Mock no existing report
        mock_session.exec.return_value.first.return_value = None

        result = self.service.check_duplicate(1, "test_hash")
        assert result is None

    def test_store_pdf_success(self):
        """Test successful PDF storage."""
        content = b"%PDF-1.4\ntest content"
        filename = "test.pdf"
        file_hash = "testhash123"

        stored_path = self.service.store_pdf(content, filename, file_hash)

        # Check file was created
        assert stored_path.exists()
        assert stored_path.name == f"{file_hash[:12]}.pdf"

        # Check content matches
        with open(stored_path, "rb") as f:
            stored_content = f.read()
        assert stored_content == content

    def test_store_pdf_no_extension(self):
        """Test PDF storage when filename has no extension."""
        content = b"%PDF-1.4\ntest content"
        filename = "test_file"
        file_hash = "testhash123"

        stored_path = self.service.store_pdf(content, filename, file_hash)

        # Should add .pdf extension
        assert stored_path.name == f"{file_hash[:12]}.pdf"
        assert stored_path.exists()

    @pytest.mark.asyncio
    async def test_upload_pdf_invalid_extension(self):
        """Test upload with invalid file extension."""
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "test.txt"

        with pytest.raises(HTTPException) as exc_info:
            await self.service.upload_pdf("user123", mock_file)

        assert exc_info.value.status_code == 400
        assert "Only PDF files are allowed" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_upload_pdf_no_filename(self):
        """Test upload with no filename."""
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = None

        with pytest.raises(HTTPException) as exc_info:
            await self.service.upload_pdf("user123", mock_file)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_upload_pdf_file_too_large(self):
        """Test upload with file exceeding size limit."""
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "test.pdf"
        # Mock file content larger than 50MB
        large_content = b"x" * (51 * 1024 * 1024)
        mock_file.read.return_value = large_content

        with pytest.raises(HTTPException) as exc_info:
            await self.service.upload_pdf("user123", mock_file)

        assert exc_info.value.status_code == 413
        assert "File too large" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_upload_pdf_invalid_format(self):
        """Test upload with invalid PDF format."""
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "test.pdf"
        mock_file.read.return_value = b"not a pdf"

        with pytest.raises(HTTPException) as exc_info:
            await self.service.upload_pdf("user123", mock_file)

        assert exc_info.value.status_code == 400
        assert "Invalid PDF file format" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_upload_pdf_duplicate_file(self):
        """Test upload of duplicate file."""
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "test.pdf"
        mock_file.read.return_value = b"%PDF-1.4\ntest content"

        # Mock user creation
        mock_user = User(id=1, external_id="user123")
        self.mock_db_service.get_or_create_user.return_value = mock_user

        # Mock duplicate check returning existing report ID
        self.service.check_duplicate = MagicMock(return_value=456)

        result = await self.service.upload_pdf("user123", mock_file)

        assert result["report_id"] == 456
        assert result["duplicate"] is True
        assert "already exists" in result["message"]

    @pytest.mark.asyncio
    async def test_upload_pdf_success(self):
        """Test successful PDF upload."""
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "test.pdf"
        content = b"%PDF-1.4\ntest content"
        mock_file.read.return_value = content

        # Mock user creation
        mock_user = User(id=1, external_id="user123")
        self.mock_db_service.get_or_create_user.return_value = mock_user

        # Mock no duplicate found
        self.service.check_duplicate = MagicMock(return_value=None)

        result = await self.service.upload_pdf("user123", mock_file)

        assert result["user_id"] == 1
        assert result["filename"] == "test.pdf"
        assert result["duplicate"] is False
        assert "file_hash" in result
        assert "stored_path" in result
        assert result["file_size"] == len(content)

    def test_get_upload_stats_empty_directory(self):
        """Test upload statistics with empty directory."""
        stats = self.service.get_upload_stats()

        assert stats["total_files"] == 0
        assert stats["total_size"] == 0
        assert "upload_directory" in stats

    def test_get_upload_stats_with_files(self):
        """Test upload statistics with existing files."""
        # Create test files
        upload_dir = self.config.uploads_dir
        upload_dir.mkdir(parents=True, exist_ok=True)

        test_file1 = upload_dir / "test1.pdf"
        test_file2 = upload_dir / "test2.pdf"

        test_file1.write_bytes(b"content1")
        test_file2.write_bytes(b"content2")

        stats = self.service.get_upload_stats()

        assert stats["total_files"] == 2
        assert stats["total_size"] == 16  # 8 + 8 bytes
        assert str(upload_dir) in stats["upload_directory"]

    def test_ensure_upload_directory(self):
        """Test that upload directory is created."""
        # Remove directory if it exists
        if self.config.uploads_dir.exists():
            self.config.uploads_dir.rmdir()

        # Create new service instance
        service = PDFUploadService(self.config, self.mock_db_service)

        # Directory should be created
        assert self.config.uploads_dir.exists()
