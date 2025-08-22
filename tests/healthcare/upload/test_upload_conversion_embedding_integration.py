"""Integration tests for the complete PDF upload, conversion, and embedding pipeline."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from healthcare.config.config import Config
from healthcare.main import app
from healthcare.storage.database import DatabaseService


@pytest.fixture
def test_config():
    """Create test configuration."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        config = Config(
            openai_api_key="test-key",
            base_data_dir=temp_path,
            uploads_dir=temp_path / "uploads",
            reports_dir=temp_path / "reports",
            chroma_dir=temp_path / "chroma",
            medical_db_path=temp_path / "medical.db",
        )
        yield config


@pytest.fixture
def test_client():
    """Create test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def sample_pdf_content():
    """Create sample PDF content for testing."""
    # This is a minimal valid PDF header
    return b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n%%EOF"


@pytest.fixture
def mock_openai_services():
    """Mock OpenAI services for testing."""
    with (
        patch(
            "healthcare.conversion.conversion_service.OpenAI"
        ) as mock_openai_conversion,
        patch("healthcare.search.embeddings.OpenAI") as mock_openai_embedding,
        patch("chromadb.PersistentClient") as mock_chroma,
    ):

        # Mock conversion service
        mock_conversion_client = Mock()
        mock_conversion_client.files.create.return_value.id = "test-file-id"

        # Mock conversion response
        mock_response = Mock()
        mock_response.output_text = json.dumps(
            {
                "markdown": "# Test Medical Report\n\nPatient shows improvement.\n\nFollow-up recommended.",
                "manifest": {"figures": [], "tables": []},
            }
        )
        mock_conversion_client.responses.create.return_value = mock_response
        mock_openai_conversion.return_value = mock_conversion_client

        # Mock embedding service
        mock_embedding_client = Mock()

        def mock_create_embeddings(*args, **kwargs):
            input_chunks = kwargs.get("input", [])
            embedding_response = Mock()
            embedding_response.data = [
                Mock(embedding=[0.1, 0.2, 0.3]) for _ in input_chunks
            ]
            return embedding_response

        mock_embedding_client.embeddings.create.side_effect = mock_create_embeddings
        mock_openai_embedding.return_value = mock_embedding_client

        # Mock Chroma
        mock_chroma_client = Mock()
        mock_collection = Mock()
        mock_collection.name = "medical_reports"
        mock_collection.count.return_value = 0
        mock_chroma_client.get_or_create_collection.return_value = mock_collection
        mock_chroma.return_value = mock_chroma_client

        yield {
            "conversion_client": mock_conversion_client,
            "embedding_client": mock_embedding_client,
            "chroma_client": mock_chroma_client,
            "collection": mock_collection,
        }


class TestUploadConversionEmbeddingIntegration:
    """Integration tests for the complete pipeline."""

    @patch("healthcare.config.config.ConfigManager.load_config")
    def test_complete_pdf_ingestion_pipeline_success(
        self,
        mock_load_config,
        test_config,
        test_client,
        sample_pdf_content,
        mock_openai_services,
    ):
        """Test the complete PDF ingestion pipeline from upload to embeddings."""
        # Setup config mock
        mock_load_config.return_value = test_config

        # Ensure directories exist
        test_config.uploads_dir.mkdir(parents=True, exist_ok=True)
        test_config.reports_dir.mkdir(parents=True, exist_ok=True)
        test_config.chroma_dir.mkdir(parents=True, exist_ok=True)

        # Initialize database
        db_service = DatabaseService(test_config)
        db_service.create_tables()

        # Prepare test file
        files = {"file": ("test_report.pdf", sample_pdf_content, "application/pdf")}
        data = {"user_external_id": "test_user_123"}

        # Make the request
        response = test_client.post("/api/upload", files=files, data=data)

        # Verify response
        assert response.status_code == 200
        response_data = response.json()

        assert "report_id" in response_data
        assert response_data["message"] == "PDF uploaded and processed successfully"
        assert response_data["filename"] == "test_report.pdf"
        assert response_data["markdown_generated"] is True
        assert response_data["embeddings_generated"] is True
        assert response_data["duplicate"] is False

        # Verify OpenAI conversion was called
        mock_openai_services["conversion_client"].files.create.assert_called_once()
        mock_openai_services["conversion_client"].responses.create.assert_called_once()

        # Verify embeddings were generated
        mock_openai_services["embedding_client"].embeddings.create.assert_called_once()

        # Verify Chroma storage was called
        mock_openai_services["collection"].add.assert_called_once()

        # Verify file structure was created
        report_id = response_data["report_id"]
        user_reports_dir = test_config.reports_dir / "user_1"
        assert user_reports_dir.exists()

        # Find the report directory (hash-based)
        report_dirs = list(user_reports_dir.iterdir())
        assert len(report_dirs) == 1
        report_dir = report_dirs[0]

        # Verify markdown file was created
        markdown_file = report_dir / "report.md"
        assert markdown_file.exists()

        markdown_content = markdown_file.read_text()
        assert "# Test Medical Report" in markdown_content
        assert "Patient shows improvement" in markdown_content

    @patch("healthcare.config.config.ConfigManager.load_config")
    def test_pdf_ingestion_conversion_failure(
        self,
        mock_load_config,
        test_config,
        test_client,
        sample_pdf_content,
        mock_openai_services,
    ):
        """Test pipeline behavior when PDF conversion fails."""
        # Setup config mock
        mock_load_config.return_value = test_config

        # Make conversion fail
        mock_openai_services["conversion_client"].responses.create.side_effect = (
            Exception("API Error")
        )

        # Ensure directories exist
        test_config.uploads_dir.mkdir(parents=True, exist_ok=True)
        test_config.reports_dir.mkdir(parents=True, exist_ok=True)

        # Initialize database
        db_service = DatabaseService(test_config)
        db_service.create_tables()

        # Prepare test file
        files = {"file": ("test_report.pdf", sample_pdf_content, "application/pdf")}
        data = {"user_external_id": "test_user_456"}

        # Make the request
        response = test_client.post("/api/upload", files=files, data=data)

        # Verify response
        assert response.status_code == 200
        response_data = response.json()

        assert "report_id" in response_data
        assert "conversion failed" in response_data["message"]
        assert response_data["markdown_generated"] is False
        assert response_data["embeddings_generated"] is False
        assert "conversion_error" in response_data

        # Verify embeddings were not attempted
        mock_openai_services["embedding_client"].embeddings.create.assert_not_called()
        mock_openai_services["collection"].add.assert_not_called()

    @patch("healthcare.config.config.ConfigManager.load_config")
    def test_pdf_ingestion_embedding_failure(
        self,
        mock_load_config,
        test_config,
        test_client,
        sample_pdf_content,
        mock_openai_services,
    ):
        """Test pipeline behavior when embedding generation fails."""
        # Setup config mock
        mock_load_config.return_value = test_config

        # Make embedding generation fail
        mock_openai_services["embedding_client"].embeddings.create.side_effect = (
            Exception("Embedding API Error")
        )

        # Ensure directories exist
        test_config.uploads_dir.mkdir(parents=True, exist_ok=True)
        test_config.reports_dir.mkdir(parents=True, exist_ok=True)
        test_config.chroma_dir.mkdir(parents=True, exist_ok=True)

        # Initialize database
        db_service = DatabaseService(test_config)
        db_service.create_tables()

        # Prepare test file
        files = {"file": ("test_report.pdf", sample_pdf_content, "application/pdf")}
        data = {"user_external_id": "test_user_789"}

        # Make the request
        response = test_client.post("/api/upload", files=files, data=data)

        # Verify response - should still succeed with conversion but fail embeddings
        assert response.status_code == 200
        response_data = response.json()

        assert "report_id" in response_data
        assert response_data["message"] == "PDF uploaded and processed successfully"
        assert response_data["markdown_generated"] is True
        assert (
            response_data["embeddings_generated"] is False
        )  # This should be False due to embedding failure

        # Verify conversion succeeded
        mock_openai_services["conversion_client"].files.create.assert_called_once()
        mock_openai_services["conversion_client"].responses.create.assert_called_once()

        # Verify embedding was attempted but failed (retry logic means multiple calls)
        assert (
            mock_openai_services["embedding_client"].embeddings.create.call_count == 3
        )  # Max retries

        # Verify Chroma storage was not called due to embedding failure
        mock_openai_services["collection"].add.assert_not_called()

    @patch("healthcare.config.config.ConfigManager.load_config")
    def test_duplicate_file_handling(
        self,
        mock_load_config,
        test_config,
        test_client,
        sample_pdf_content,
        mock_openai_services,
    ):
        """Test that duplicate files are handled correctly without reprocessing."""
        # Setup config mock
        mock_load_config.return_value = test_config

        # Ensure directories exist
        test_config.uploads_dir.mkdir(parents=True, exist_ok=True)
        test_config.reports_dir.mkdir(parents=True, exist_ok=True)
        test_config.chroma_dir.mkdir(parents=True, exist_ok=True)

        # Initialize database
        db_service = DatabaseService(test_config)
        db_service.create_tables()

        # Prepare test file
        files = {
            "file": ("duplicate_report.pdf", sample_pdf_content, "application/pdf")
        }
        data = {"user_external_id": "test_user_duplicate"}

        # Upload first time
        response1 = test_client.post("/api/upload", files=files, data=data)
        assert response1.status_code == 200
        response1_data = response1.json()
        assert response1_data["duplicate"] is False

        # Reset mocks to track second upload
        mock_openai_services["conversion_client"].reset_mock()
        mock_openai_services["embedding_client"].reset_mock()
        mock_openai_services["collection"].reset_mock()

        # Upload same file again
        response2 = test_client.post("/api/upload", files=files, data=data)
        assert response2.status_code == 200
        response2_data = response2.json()

        # Verify duplicate detection
        assert response2_data["duplicate"] is True
        assert response2_data["message"] == "File already exists - no processing needed"
        assert response2_data["report_id"] == response1_data["report_id"]

        # Verify no reprocessing occurred
        mock_openai_services["conversion_client"].files.create.assert_not_called()
        mock_openai_services["conversion_client"].responses.create.assert_not_called()
        mock_openai_services["embedding_client"].embeddings.create.assert_not_called()
        mock_openai_services["collection"].add.assert_not_called()

    @patch("healthcare.config.config.ConfigManager.load_config")
    def test_embedding_metadata_structure(
        self,
        mock_load_config,
        test_config,
        test_client,
        sample_pdf_content,
        mock_openai_services,
    ):
        """Test that embedding metadata contains all required fields."""
        # Setup config mock
        mock_load_config.return_value = test_config

        # Ensure directories exist
        test_config.uploads_dir.mkdir(parents=True, exist_ok=True)
        test_config.reports_dir.mkdir(parents=True, exist_ok=True)
        test_config.chroma_dir.mkdir(parents=True, exist_ok=True)

        # Initialize database
        db_service = DatabaseService(test_config)
        db_service.create_tables()

        # Prepare test file
        files = {"file": ("metadata_test.pdf", sample_pdf_content, "application/pdf")}
        data = {"user_external_id": "metadata_test_user"}

        # Make the request
        response = test_client.post("/api/upload", files=files, data=data)
        assert response.status_code == 200

        # Verify Chroma add was called with correct metadata structure
        mock_openai_services["collection"].add.assert_called_once()
        call_args = mock_openai_services["collection"].add.call_args[1]

        # Check metadata structure
        metadatas = call_args["metadatas"]
        assert len(metadatas) > 0

        metadata = metadatas[0]
        assert metadata["user_external_id"] == "metadata_test_user"
        assert metadata["user_id"] == 1  # First user
        assert "report_id" in metadata
        assert metadata["filename"] == "metadata_test.pdf"
        assert "created_at" in metadata
        assert metadata["chunk_index"] == 0
        assert metadata["content_type"] == "paragraph"

        # Verify documents were chunked
        documents = call_args["documents"]
        assert len(documents) > 0
        assert all(isinstance(doc, str) for doc in documents)

        # Verify embeddings were generated
        embeddings = call_args["embeddings"]
        assert len(embeddings) == len(documents)
        assert all(isinstance(emb, list) for emb in embeddings)


@pytest.mark.integration
class TestFullPipelineIntegration:
    """End-to-end integration tests requiring real services (when available)."""

    def test_pipeline_components_integration(self):
        """Test that all pipeline components can be instantiated together."""
        # This test verifies that all components can work together
        # without mocking, useful for development environment testing

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config = Config(
                openai_api_key="test-key",
                base_data_dir=temp_path,
                uploads_dir=temp_path / "uploads",
                reports_dir=temp_path / "reports",
                chroma_dir=temp_path / "chroma",
                medical_db_path=temp_path / "medical.db",
            )

            # Test that all services can be instantiated
            from healthcare.conversion.conversion_service import (
                PDFConversionService,
            )
            from healthcare.storage.database import DatabaseService
            from healthcare.search.embeddings import EmbeddingService
            from healthcare.upload.upload_service import PDFUploadService

            db_service = DatabaseService(config)
            db_service.create_tables()

            # These should not fail to instantiate
            upload_service = PDFUploadService(config, db_service)
            conversion_service = PDFConversionService(config)
            embedding_service = EmbeddingService(config)

            # Verify services are properly configured
            assert upload_service.config == config
            assert conversion_service.config == config
            assert embedding_service.config == config

            # Verify database connection works
            stats = upload_service.get_upload_stats()
            assert "total_files" in stats

            # Verify embedding service has proper collection
            collection_stats = embedding_service.get_collection_stats()
            assert "collection_name" in collection_stats
            assert collection_stats["collection_name"] == "medical_reports"
