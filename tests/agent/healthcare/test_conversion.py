"""Tests for PDF conversion service."""

import json
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import openai
import pytest

from agent.healthcare.config.config import Config
from agent.healthcare.conversion.conversion_service import (
    ConversionResult,
    Figure,
    PDFConversionService,
    TableRef,
)


@pytest.fixture
def config():
    """Test configuration."""
    return Config(
        openai_api_key="test-key",
        openai_model="gpt-5-mini",
        max_retries=2,
        request_timeout=10,
    )


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client."""
    return Mock(spec=openai.OpenAI)


@pytest.fixture
def conversion_service(config, mock_openai_client):
    """PDF conversion service with mocked client."""
    return PDFConversionService(config, mock_openai_client)


@pytest.fixture
def sample_conversion_result():
    """Sample conversion result for testing."""
    return ConversionResult(
        markdown="# Test Report\n\nSample medical report content.",
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


class TestPDFConversionService:
    """Test suite for PDFConversionService."""

    def test_init_with_default_client(self, config):
        """Test initialization with default OpenAI client."""
        with patch(
            "agent.healthcare.conversion.conversion_service.OpenAI"
        ) as mock_openai:
            service = PDFConversionService(config)
            mock_openai.assert_called_once_with(api_key="test-key")
            assert service.config == config

    def test_init_with_custom_client(self, config, mock_openai_client):
        """Test initialization with custom OpenAI client."""
        service = PDFConversionService(config, mock_openai_client)
        assert service.client == mock_openai_client
        assert service.config == config

    def test_upload_to_openai_success(self, conversion_service, mock_openai_client):
        """Test successful PDF upload to OpenAI."""
        # Mock file upload response
        mock_file = Mock()
        mock_file.id = "file-12345"
        mock_openai_client.files.create.return_value = mock_file

        # Mock file reading
        with patch("builtins.open", mock_open(read_data=b"fake pdf content")):
            with patch("pathlib.Path.exists", return_value=True):
                file_id = conversion_service.upload_to_openai(Path("test.pdf"))

        assert file_id == "file-12345"
        mock_openai_client.files.create.assert_called_once()
        call_args = mock_openai_client.files.create.call_args
        assert call_args[1]["purpose"] == "assistants"

    def test_upload_to_openai_file_not_found(self, conversion_service):
        """Test upload with non-existent file."""
        with pytest.raises(FileNotFoundError, match="PDF file not found"):
            conversion_service.upload_to_openai(Path("nonexistent.pdf"))

    def test_upload_to_openai_api_error_retry(
        self, conversion_service, mock_openai_client
    ):
        """Test upload with API error and retry logic."""
        # Mock API error on first call, success on second
        mock_file = Mock()
        mock_file.id = "file-12345"
        mock_openai_client.files.create.side_effect = [
            openai.APIError("Rate limit exceeded", request=Mock(), body=None),
            mock_file,
        ]

        with patch("builtins.open", mock_open(read_data=b"fake pdf content")):
            with patch("pathlib.Path.exists", return_value=True):
                file_id = conversion_service.upload_to_openai(Path("test.pdf"))

        assert file_id == "file-12345"
        assert mock_openai_client.files.create.call_count == 2

    def test_convert_pdf_to_markdown_success(
        self, conversion_service, mock_openai_client, sample_conversion_result
    ):
        """Test successful PDF to Markdown conversion."""
        # Mock successful response
        mock_response = Mock()
        mock_response.output_text = json.dumps(
            {
                "markdown": sample_conversion_result.markdown,
                "manifest": sample_conversion_result.manifest,
            }
        )
        mock_openai_client.responses.create.return_value = mock_response

        result = conversion_service.convert_pdf_to_markdown("file-12345")

        assert isinstance(result, ConversionResult)
        assert result.markdown == "# Test Report\n\nSample medical report content."
        assert "figures" in result.manifest
        assert "tables" in result.manifest

        # Verify API call
        mock_openai_client.responses.create.assert_called_once()
        call_args = mock_openai_client.responses.create.call_args
        assert call_args[1]["model"] == "gpt-5-mini"
        assert "input" in call_args[1]

    def test_convert_pdf_to_markdown_failure(
        self, conversion_service, mock_openai_client
    ):
        """Test conversion failure with both methods."""
        # Mock both calls failing
        mock_openai_client.responses.create.side_effect = [
            Exception("First call failed")
        ]

        with pytest.raises(Exception, match="First call failed"):
            conversion_service.convert_pdf_to_markdown("file-12345")

    def test_save_markdown_success(self, conversion_service, tmp_path):
        """Test successful Markdown saving."""
        report_dir = tmp_path / "report"
        markdown_content = "# Test Report\n\nContent here."

        result_path = conversion_service.save_markdown(markdown_content, report_dir)

        assert result_path == report_dir / "report.md"
        assert result_path.exists()
        assert result_path.read_text(encoding="utf-8") == markdown_content

    def test_save_markdown_creates_directory(self, conversion_service, tmp_path):
        """Test that save_markdown creates directory if it doesn't exist."""
        report_dir = tmp_path / "nonexistent" / "report"
        markdown_content = "# Test Report"

        result_path = conversion_service.save_markdown(markdown_content, report_dir)

        assert report_dir.exists()
        assert result_path.exists()
        assert result_path.read_text(encoding="utf-8") == markdown_content

    @pytest.mark.asyncio
    async def test_process_pdf_complete_pipeline(
        self, conversion_service, mock_openai_client, sample_conversion_result, tmp_path
    ):
        """Test complete PDF processing pipeline."""
        # Mock successful upload
        mock_file = Mock()
        mock_file.id = "file-12345"
        mock_openai_client.files.create.return_value = mock_file

        # Mock successful conversion
        mock_response = Mock()
        mock_response.output_text = json.dumps(
            {
                "markdown": sample_conversion_result.markdown,
                "manifest": sample_conversion_result.manifest,
            }
        )
        mock_openai_client.responses.create.return_value = mock_response

        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"fake pdf content")
        report_dir = tmp_path / "report"

        result = await conversion_service.process_pdf(pdf_path, report_dir)

        # Verify result
        assert isinstance(result, ConversionResult)
        assert result.markdown == sample_conversion_result.markdown
        assert result.manifest == sample_conversion_result.manifest

        # Verify Markdown was saved
        markdown_path = report_dir / "report.md"
        assert markdown_path.exists()
        assert (
            markdown_path.read_text(encoding="utf-8")
            == sample_conversion_result.markdown
        )

    def test_cleanup_openai_file_success(self, conversion_service, mock_openai_client):
        """Test successful file cleanup."""
        conversion_service.cleanup_openai_file("file-12345")
        mock_openai_client.files.delete.assert_called_once_with("file-12345")

    def test_cleanup_openai_file_failure(self, conversion_service, mock_openai_client):
        """Test file cleanup failure (should not raise exception)."""
        mock_openai_client.files.delete.side_effect = Exception("Delete failed")

        # Should not raise exception
        conversion_service.cleanup_openai_file("file-12345")
        mock_openai_client.files.delete.assert_called_once_with("file-12345")


class TestConversionModels:
    """Test Pydantic models for conversion."""

    def test_figure_model(self):
        """Test Figure model validation."""
        figure = Figure(
            page=1, index=1, caption="Test image", filename="page-001-img-01.png"
        )
        assert figure.page == 1
        assert figure.index == 1
        assert figure.caption == "Test image"
        assert figure.filename == "page-001-img-01.png"

    def test_table_ref_model(self):
        """Test TableRef model validation."""
        table = TableRef(page=2, index=1, title="Lab Results", format="markdown")
        assert table.page == 2
        assert table.index == 1
        assert table.title == "Lab Results"
        assert table.format == "markdown"

    def test_conversion_result_model(self):
        """Test ConversionResult model validation."""
        result = ConversionResult(
            markdown="# Test", manifest={"figures": [], "tables": []}
        )
        assert result.markdown == "# Test"
        assert result.manifest == {"figures": [], "tables": []}

    def test_conversion_result_with_complex_manifest(self):
        """Test ConversionResult with complex manifest."""
        manifest = {
            "figures": [
                {
                    "page": 1,
                    "index": 1,
                    "caption": "X-ray",
                    "filename": "page-001-img-01.png",
                }
            ],
            "tables": [{"page": 2, "index": 1, "title": "Labs", "format": "markdown"}],
        }
        result = ConversionResult(
            markdown="# Medical Report\n\nContent...", manifest=manifest
        )
        assert result.manifest["figures"][0]["caption"] == "X-ray"
        assert result.manifest["tables"][0]["title"] == "Labs"
