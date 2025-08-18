"""Integration tests for PDF conversion workflow."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from agent.healthcare.config.config import Config
from agent.healthcare.conversion.conversion_service import (
    ConversionResult,
    PDFConversionService,
)


@pytest.fixture
def config():
    """Test configuration for integration tests."""
    return Config(
        openai_api_key="test-integration-key",
        openai_model="gpt-5-mini",
        max_retries=1,  # Reduced for faster tests
        request_timeout=5,
    )


@pytest.fixture
def sample_pdf_content():
    """Sample PDF content for testing."""
    # This would normally be actual PDF bytes, but for testing we use placeholder
    return b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n%%EOF"


@pytest.fixture
def expected_conversion_result():
    """Expected conversion result for integration tests."""
    return ConversionResult(
        markdown="""# Medical Report

<a id="page-001"></a>

## Patient Information
- Name: John Doe
- DOB: 1980-01-15
- MRN: 123456

## Lab Results

| Test | Value | Reference Range | Units |
|------|-------|-----------------|-------|
| Glucose | 95 | 70-100 | mg/dL |
| Cholesterol | 180 | <200 | mg/dL |

## Imaging

![Chest X-ray showing clear lungs](assets/page-002-img-01.png)

**Figure 1**: Chest X-ray from January 15, 2024 showing clear lung fields with no acute findings.

## Assessment
Patient presents with normal lab values and clear chest imaging.
""",
        manifest={
            "figures": [
                {
                    "page": 2,
                    "index": 1,
                    "caption": "Chest X-ray showing clear lungs",
                    "filename": "page-002-img-01.png",
                }
            ],
            "tables": [
                {"page": 1, "index": 1, "title": "Lab Results", "format": "markdown"}
            ],
        },
    )


class TestConversionIntegration:
    """Integration tests for PDF conversion workflow."""

    @pytest.mark.integration
    def test_end_to_end_conversion_workflow(
        self, config, sample_pdf_content, expected_conversion_result
    ):
        """Test complete end-to-end PDF conversion workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test PDF file
            pdf_path = temp_path / "test_report.pdf"
            pdf_path.write_bytes(sample_pdf_content)

            # Create report directory
            report_dir = temp_path / "converted_report"

            # Mock OpenAI client responses
            mock_client = Mock()

            # Mock file upload
            mock_file = Mock()
            mock_file.id = "file-integration-test-123"
            mock_client.files.create.return_value = mock_file

            # Mock conversion response
            mock_response = Mock()
            mock_response.output_text = json.dumps(
                {
                    "markdown": expected_conversion_result.markdown,
                    "manifest": expected_conversion_result.manifest,
                }
            )
            mock_client.responses.create.return_value = mock_response

            # Create service with mocked client
            service = PDFConversionService(config, mock_client)

            # Run the complete workflow (async method needs await)
            import asyncio

            result = asyncio.run(service.process_pdf(pdf_path, report_dir))

            # Verify the result
            assert isinstance(result, ConversionResult)
            assert result.markdown == expected_conversion_result.markdown
            assert result.manifest == expected_conversion_result.manifest

            # Verify file was saved
            markdown_file = report_dir / "report.md"
            assert markdown_file.exists()

            # Verify markdown content
            saved_content = markdown_file.read_text(encoding="utf-8")
            assert saved_content == expected_conversion_result.markdown

            # Verify API calls were made correctly
            mock_client.files.create.assert_called_once()
            mock_client.responses.create.assert_called_once()

            # Verify upload call arguments
            upload_call = mock_client.files.create.call_args
            assert upload_call[1]["purpose"] == "assistants"

            # Verify conversion call arguments
            conversion_call = mock_client.responses.create.call_args
            assert conversion_call[1]["model"] == "gpt-5-mini"
            assert "input" in conversion_call[1]

    @pytest.mark.integration
    async def test_async_process_pdf_workflow(
        self, config, sample_pdf_content, expected_conversion_result
    ):
        """Test async PDF processing workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test PDF file
            pdf_path = temp_path / "async_test_report.pdf"
            pdf_path.write_bytes(sample_pdf_content)

            # Create report directory
            report_dir = temp_path / "async_converted_report"

            # Mock OpenAI client
            mock_client = Mock()
            mock_file = Mock()
            mock_file.id = "file-async-test-456"
            mock_client.files.create.return_value = mock_file

            mock_response = Mock()
            mock_response.output_text = json.dumps(
                {
                    "markdown": expected_conversion_result.markdown,
                    "manifest": expected_conversion_result.manifest,
                }
            )
            mock_client.responses.create.return_value = mock_response

            # Create service and run async workflow
            service = PDFConversionService(config, mock_client)
            result = await service.process_pdf(pdf_path, report_dir)

            # Verify results
            assert isinstance(result, ConversionResult)
            assert result.markdown == expected_conversion_result.markdown

            # Verify markdown file was created
            markdown_file = report_dir / "report.md"
            assert markdown_file.exists()

    @pytest.mark.integration
    def test_conversion_with_retry_logic(self, config, sample_pdf_content):
        """Test conversion workflow with retry logic."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            pdf_path = temp_path / "retry_test.pdf"
            pdf_path.write_bytes(sample_pdf_content)

            # Mock client with temporary failure then success
            mock_client = Mock()

            # Mock upload with retry - use specific exception types that tenacity will retry
            mock_file = Mock()
            mock_file.id = "file-retry-101112"
            import openai

            mock_client.files.create.side_effect = [
                openai.APIError("Temporary failure", request=Mock(), body=None),
                mock_file,
            ]

            # Mock successful conversion
            conversion_result = ConversionResult(
                markdown="# Retry Test Report", manifest={"figures": [], "tables": []}
            )
            mock_response = Mock()
            mock_response.output_text = json.dumps(
                {
                    "markdown": conversion_result.markdown,
                    "manifest": conversion_result.manifest,
                }
            )
            mock_client.responses.create.return_value = mock_response

            # Test upload retry
            service = PDFConversionService(config, mock_client)
            file_id = service.upload_to_openai(pdf_path)

            # Verify retry worked
            assert file_id == "file-retry-101112"
            assert mock_client.files.create.call_count == 2

    @pytest.mark.integration
    def test_file_cleanup_workflow(self, config):
        """Test OpenAI file cleanup workflow."""
        mock_client = Mock()
        service = PDFConversionService(config, mock_client)

        # Test successful cleanup
        service.cleanup_openai_file("file-cleanup-test")
        mock_client.files.delete.assert_called_once_with("file-cleanup-test")

        # Test cleanup failure (should not raise exception)
        mock_client.files.delete.side_effect = Exception("Delete failed")
        service.cleanup_openai_file("file-cleanup-fail")  # Should not raise

    @pytest.mark.integration
    def test_directory_creation_during_save(self, config):
        """Test that save_markdown creates necessary directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create nested directory path that doesn't exist
            nested_report_dir = temp_path / "level1" / "level2" / "report"

            service = PDFConversionService(config)
            markdown_content = (
                "# Test Directory Creation\n\nThis tests directory creation."
            )

            # Save markdown to non-existent directory
            result_path = service.save_markdown(markdown_content, nested_report_dir)

            # Verify directory was created and file was saved
            assert nested_report_dir.exists()
            assert result_path.exists()
            assert result_path.read_text(encoding="utf-8") == markdown_content

    @pytest.mark.integration
    def test_large_markdown_handling(self, config):
        """Test handling of large markdown content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            report_dir = temp_path / "large_report"

            # Create large markdown content (simulate large medical report)
            large_content = "# Large Medical Report\n\n"
            large_content += "## Section 1\n\n" + "Large content block. " * 1000
            large_content += "\n\n## Section 2\n\n" + "More large content. " * 1000
            large_content += "\n\n## Lab Results\n\n"

            # Add large table
            for i in range(100):
                large_content += f"| Test {i} | Value {i} | Normal | mg/dL |\n"

            service = PDFConversionService(config)
            result_path = service.save_markdown(large_content, report_dir)

            # Verify large content was saved correctly
            assert result_path.exists()
            saved_content = result_path.read_text(encoding="utf-8")
            assert saved_content == large_content
            assert (
                len(saved_content) > 40000
            )  # Verify it's actually large (adjusted for actual size)

    @pytest.mark.integration
    def test_unicode_content_handling(self, config):
        """Test handling of unicode content in medical reports."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            report_dir = temp_path / "unicode_report"

            # Create content with medical unicode characters
            unicode_content = """# Rapport Médical

## Informations du Patient
- Nom: José García
- Âge: 45 ans
- Température: 37.2°C

## Résultats
- Pression artérielle: 120/80 mmHg
- Pouls: 72 bpm
- SpO₂: 98%

## Notes
Patient présente des symptômes légers. Aucune intervention nécessaire.
Recommandations: repos et hydratation.

## Signature
Dr. François Müller, MD
"""

            service = PDFConversionService(config)
            result_path = service.save_markdown(unicode_content, report_dir)

            # Verify unicode content was saved correctly
            assert result_path.exists()
            saved_content = result_path.read_text(encoding="utf-8")
            assert saved_content == unicode_content
            assert "José García" in saved_content
            assert "37.2°C" in saved_content
            assert "SpO₂" in saved_content
