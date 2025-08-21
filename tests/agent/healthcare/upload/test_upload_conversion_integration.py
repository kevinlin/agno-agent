"""Integration tests for PDF upload with conversion pipeline."""

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from agent.healthcare.config.config import Config
from agent.healthcare.conversion.conversion_service import ConversionResult
from agent.healthcare.storage.database import DatabaseService


@pytest.fixture
def config():
    """Test configuration."""
    return Config(
        openai_api_key="test-key",
        openai_model="gpt-5-mini",
        max_retries=1,
        request_timeout=5,
    )


@pytest.fixture
def sample_pdf_content():
    """Sample PDF content for testing."""
    return b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n%%EOF"


@pytest.fixture
def sample_conversion_result():
    """Sample conversion result."""
    return ConversionResult(
        markdown="# Medical Report\n\n## Patient Information\n- Name: John Doe\n- DOB: 1980-01-15",
        manifest={
            "figures": [
                {
                    "page": 1,
                    "index": 1,
                    "caption": "Chest X-ray",
                    "filename": "page-001-img-01.png",
                }
            ],
            "tables": [
                {"page": 2, "index": 1, "title": "Lab Results", "format": "markdown"}
            ],
        },
    )


class MockUploadFile:
    """Mock FastAPI UploadFile for testing."""

    def __init__(self, filename: str, content: bytes):
        self.filename = filename
        self.content = content

    async def read(self) -> bytes:
        return self.content


@pytest.mark.integration
class TestUploadConversionIntegration:
    """Integration tests for complete upload and conversion pipeline."""

    @pytest.mark.asyncio
    async def test_complete_upload_conversion_pipeline(
        self, config, sample_pdf_content, sample_conversion_result
    ):
        """Test complete PDF upload and conversion pipeline."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Set up temporary directories
            temp_path = Path(temp_dir)
            config.base_data_dir = temp_path / "data"
            config.uploads_dir = temp_path / "data/uploads"
            config.reports_dir = temp_path / "data/reports"
            config.medical_db_path = temp_path / "data/medical.db"

            # Initialize database
            db_service = DatabaseService(config)
            db_service.create_tables()

            # Mock the conversion service
            with patch(
                "agent.healthcare.upload.routes.PDFConversionService"
            ) as mock_conversion_class:
                mock_conversion_service = Mock()

                # Create a custom async mock that also creates the markdown file
                async def mock_process_pdf(pdf_path, report_dir):
                    # Create the report directory and markdown file
                    report_dir.mkdir(parents=True, exist_ok=True)
                    markdown_path = report_dir / "report.md"
                    markdown_path.write_text(
                        sample_conversion_result.markdown, encoding="utf-8"
                    )
                    return sample_conversion_result

                mock_conversion_service.process_pdf = AsyncMock(
                    side_effect=mock_process_pdf
                )
                mock_conversion_class.return_value = mock_conversion_service

                # Import and test the upload route function
                from agent.healthcare.upload.routes import upload_pdf
                from agent.healthcare.upload.upload_service import PDFUploadService

                # Create services
                upload_service = PDFUploadService(config, db_service)

                # Mock embedding service
                with patch(
                    "agent.healthcare.storage.embeddings.EmbeddingService"
                ) as mock_embedding_class:
                    mock_embedding_service = Mock()
                    mock_embedding_service.process_report_embeddings = Mock()
                    mock_embedding_class.return_value = mock_embedding_service

                    # Create mock upload file
                    mock_file = MockUploadFile("test_report.pdf", sample_pdf_content)

                    # Call the ingest endpoint
                    result = await upload_pdf(
                        user_external_id="test_user",
                        file=mock_file,
                        upload_service=upload_service,
                        conversion_service=mock_conversion_service,
                        embedding_service=mock_embedding_service,
                        db_service=db_service,
                        config=config,
                    )

                    # Verify response
                    assert result.status_code == 200
                    response_data = json.loads(result.body)

                    assert (
                        response_data["message"]
                        == "PDF uploaded and processed successfully"
                    )
                    assert response_data["markdown_generated"] is True
                    assert response_data["embeddings_generated"] is True
                    assert "report_id" in response_data
                    assert (
                        response_data["manifest"] == sample_conversion_result.manifest
                    )
                    assert response_data["duplicate"] is False

                    # Verify conversion service was called
                    mock_conversion_service.process_pdf.assert_called_once()

                    # Verify database record was created with conversion data
                    report = db_service.get_report_by_id(response_data["report_id"])
                    assert report is not None
                    assert report.filename == "test_report.pdf"
                    assert report.markdown_path != ""
                    assert report.images_dir != ""

                    # Verify manifest was stored
                    stored_manifest = json.loads(report.meta_json)
                    assert stored_manifest == sample_conversion_result.manifest

    @pytest.mark.asyncio
    async def test_upload_with_conversion_failure(self, config, sample_pdf_content):
        """Test upload pipeline when conversion fails."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Set up temporary directories
            temp_path = Path(temp_dir)
            config.base_data_dir = temp_path / "data"
            config.uploads_dir = temp_path / "data/uploads"
            config.reports_dir = temp_path / "data/reports"
            config.medical_db_path = temp_path / "data/medical.db"

            # Initialize database
            db_service = DatabaseService(config)
            db_service.create_tables()

            # Mock the conversion service to fail
            with patch(
                "agent.healthcare.upload.routes.PDFConversionService"
            ) as mock_conversion_class:
                mock_conversion_service = Mock()
                mock_conversion_service.process_pdf.side_effect = Exception(
                    "Conversion failed"
                )
                mock_conversion_class.return_value = mock_conversion_service

                # Import and test the upload route function
                from agent.healthcare.upload.routes import upload_pdf
                from agent.healthcare.upload.upload_service import PDFUploadService

                # Create services
                upload_service = PDFUploadService(config, db_service)

                # Mock embedding service
                with patch(
                    "agent.healthcare.storage.embeddings.EmbeddingService"
                ) as mock_embedding_class:
                    mock_embedding_service = Mock()
                    mock_embedding_service.process_report_embeddings = Mock()
                    mock_embedding_class.return_value = mock_embedding_service

                    # Create mock upload file
                    mock_file = MockUploadFile("test_report.pdf", sample_pdf_content)

                    # Call the ingest endpoint
                    result = await upload_pdf(
                        user_external_id="test_user",
                        file=mock_file,
                        upload_service=upload_service,
                        conversion_service=mock_conversion_service,
                        embedding_service=mock_embedding_service,
                        db_service=db_service,
                        config=config,
                    )

                    # Verify response indicates conversion failure but upload success
                    assert result.status_code == 200
                    response_data = json.loads(result.body)

                    assert "conversion failed" in response_data["message"].lower()
                    assert response_data["markdown_generated"] is False
                    assert response_data["embeddings_generated"] is False
                    assert "report_id" in response_data
                    assert "conversion_error" in response_data
                    assert response_data["duplicate"] is False

                    # Verify database record was created without conversion data
                    report = db_service.get_report_by_id(response_data["report_id"])
                    assert report is not None
                    assert report.filename == "test_report.pdf"
                    assert report.markdown_path == ""  # Empty due to conversion failure
                    assert report.images_dir == ""  # Empty due to conversion failure

                    # Verify error manifest was stored
                    stored_manifest = json.loads(report.meta_json)
                    assert stored_manifest["error"] == "Conversion failed"

    @pytest.mark.asyncio
    async def test_duplicate_file_handling(self, config, sample_pdf_content):
        """Test that duplicate files are handled correctly without reprocessing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Set up temporary directories
            temp_path = Path(temp_dir)
            config.base_data_dir = temp_path / "data"
            config.uploads_dir = temp_path / "data/uploads"
            config.reports_dir = temp_path / "data/reports"
            config.medical_db_path = temp_path / "data/medical.db"

            # Initialize database
            db_service = DatabaseService(config)
            db_service.create_tables()

            # Import services
            from agent.healthcare.upload.routes import upload_pdf
            from agent.healthcare.upload.upload_service import PDFUploadService

            # Create services
            upload_service = PDFUploadService(config, db_service)
            mock_conversion_service = Mock()

            # Mock embedding service
            with patch(
                "agent.healthcare.storage.embeddings.EmbeddingService"
            ) as mock_embedding_class:
                mock_embedding_service = Mock()
                mock_embedding_service.process_report_embeddings = Mock()
                mock_embedding_class.return_value = mock_embedding_service

                # Create mock upload file
                mock_file1 = MockUploadFile("test_report.pdf", sample_pdf_content)
                mock_file2 = MockUploadFile("test_report.pdf", sample_pdf_content)

                # First upload
                result1 = await upload_pdf(
                    user_external_id="test_user",
                    file=mock_file1,
                    upload_service=upload_service,
                    conversion_service=mock_conversion_service,
                    embedding_service=mock_embedding_service,
                    db_service=db_service,
                    config=config,
                )

                # Second upload (duplicate)
                result2 = await upload_pdf(
                    user_external_id="test_user",
                    file=mock_file2,
                    upload_service=upload_service,
                    conversion_service=mock_conversion_service,
                    embedding_service=mock_embedding_service,
                    db_service=db_service,
                    config=config,
                )

                # Verify both responses
                assert result1.status_code == 200
                assert result2.status_code == 200

                response1_data = json.loads(result1.body)
                response2_data = json.loads(result2.body)

                # First upload should not be marked as duplicate
                assert response1_data["duplicate"] is False

                # Second upload should be marked as duplicate
                assert response2_data["duplicate"] is True
                assert (
                    response2_data["message"]
                    == "File already exists - no processing needed"
                )

                # Both should have same report_id
                assert response1_data["report_id"] == response2_data["report_id"]

    @pytest.mark.asyncio
    async def test_directory_structure_creation(
        self, config, sample_pdf_content, sample_conversion_result
    ):
        """Test that proper directory structure is created during conversion."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Set up temporary directories
            temp_path = Path(temp_dir)
            config.base_data_dir = temp_path / "data"
            config.uploads_dir = temp_path / "data/uploads"
            config.reports_dir = temp_path / "data/reports"
            config.medical_db_path = temp_path / "data/medical.db"

            # Initialize database
            db_service = DatabaseService(config)
            db_service.create_tables()

            # Mock the conversion service
            with patch(
                "agent.healthcare.upload.routes.PDFConversionService"
            ) as mock_conversion_class:
                mock_conversion_service = Mock()

                # Create a custom async mock that also creates the markdown file
                async def mock_process_pdf(pdf_path, report_dir):
                    # Create the report directory and markdown file
                    report_dir.mkdir(parents=True, exist_ok=True)
                    markdown_path = report_dir / "report.md"
                    markdown_path.write_text(
                        sample_conversion_result.markdown, encoding="utf-8"
                    )
                    return sample_conversion_result

                mock_conversion_service.process_pdf = AsyncMock(
                    side_effect=mock_process_pdf
                )
                mock_conversion_class.return_value = mock_conversion_service

                # Import and test the upload route function
                from agent.healthcare.upload.routes import upload_pdf
                from agent.healthcare.upload.upload_service import PDFUploadService

                # Create services
                upload_service = PDFUploadService(config, db_service)

                # Mock embedding service
                with patch(
                    "agent.healthcare.storage.embeddings.EmbeddingService"
                ) as mock_embedding_class:
                    mock_embedding_service = Mock()
                    mock_embedding_service.process_report_embeddings = Mock()
                    mock_embedding_class.return_value = mock_embedding_service

                    # Create mock upload file
                    mock_file = MockUploadFile("test_report.pdf", sample_pdf_content)

                    # Call the ingest endpoint
                    result = await upload_pdf(
                        user_external_id="test_user",
                        file=mock_file,
                        upload_service=upload_service,
                        conversion_service=mock_conversion_service,
                        embedding_service=mock_embedding_service,
                        db_service=db_service,
                        config=config,
                    )

                    # Verify directory structure was created
                    response_data = json.loads(result.body)
                    report = db_service.get_report_by_id(response_data["report_id"])

                    # Check that paths are correctly structured
                    assert "user_1" in report.markdown_path
                    assert "user_1" in report.images_dir
                    assert report.markdown_path.endswith("report.md")
                    assert report.images_dir.endswith("images")

                    # Verify conversion service was called with correct paths
                    call_args = mock_conversion_service.process_pdf.call_args
                    pdf_path, report_dir = call_args[0]

                    assert pdf_path.name.endswith(".pdf")
                    assert "user_1" in str(report_dir)
                    assert str(report_dir).startswith(str(config.reports_dir))
