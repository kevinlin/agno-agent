"""Integration tests for PDF upload functionality."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture(scope="function")
def temp_config():
    """Create temporary configuration for testing."""
    temp_dir = tempfile.mkdtemp()
    return {
        "OPENAI_API_KEY": "test_key",
        "DATA_DIR": f"{temp_dir}/data",
        "UPLOADS_DIR": f"{temp_dir}/data/uploads",
        "REPORTS_DIR": f"{temp_dir}/data/reports",
        "CHROMA_DIR": f"{temp_dir}/data/chroma",
        "MEDICAL_DB_PATH": f"{temp_dir}/data/medical.db",
        "AGENT_DB_PATH": f"{temp_dir}/data/healthcare_agent.db",
    }


@pytest.fixture(scope="function")
def app_with_db(temp_config):
    """Create FastAPI app with database initialized."""
    with patch.dict("os.environ", temp_config, clear=True):
        # Create the app
        app = FastAPI(title="Test Healthcare Agent")

        # Import and include upload routes
        from healthcare.upload.routes import router as upload_router

        app.include_router(upload_router)

        # Initialize database tables for testing
        from healthcare.config.config import ConfigManager
        from healthcare.storage.database import DatabaseService

        config = ConfigManager.load_config()
        db_service = DatabaseService(config)
        db_service.create_tables()

        yield app


@pytest.fixture(scope="function")
def client(app_with_db):
    """Create test client."""
    return TestClient(app_with_db)


@pytest.fixture
def sample_pdf_content():
    """Sample PDF content for testing."""
    return b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000074 00000 n \n0000000120 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n179\n%%EOF"


class TestUploadIntegration:
    """Integration tests for PDF upload endpoints."""

    def test_upload_pdf_success(self, client, sample_pdf_content):
        """Test successful PDF upload."""
        files = {"file": ("test.pdf", sample_pdf_content, "application/pdf")}
        data = {"user_external_id": "test_user_123"}

        response = client.post("/api/upload", files=files, data=data)

        assert response.status_code == 200
        result = response.json()

        assert "report_id" in result
        assert result["filename"] == "test.pdf"
        assert result["duplicate"] is False
        assert "file_hash" in result
        assert result["file_size"] > 0

    def test_upload_pdf_invalid_file_type(self, client):
        """Test upload with invalid file type."""
        files = {"file": ("test.txt", b"not a pdf", "text/plain")}
        data = {"user_external_id": "test_user_123"}

        response = client.post("/api/upload", files=files, data=data)

        assert response.status_code == 400
        assert "Only PDF files are allowed" in response.json()["detail"]

    def test_upload_pdf_invalid_content(self, client):
        """Test upload with invalid PDF content."""
        files = {"file": ("test.pdf", b"not a valid pdf", "application/pdf")}
        data = {"user_external_id": "test_user_123"}

        response = client.post("/api/upload", files=files, data=data)

        assert response.status_code == 400
        assert "Invalid PDF file format" in response.json()["detail"]

    def test_upload_pdf_file_too_large(self, client):
        """Test upload with file exceeding size limit."""
        # Create large file content (51MB)
        large_content = b"%PDF-1.4\n" + b"x" * (51 * 1024 * 1024)
        files = {"file": ("large.pdf", large_content, "application/pdf")}
        data = {"user_external_id": "test_user_123"}

        response = client.post("/api/upload", files=files, data=data)

        assert response.status_code == 413
        assert "File too large" in response.json()["detail"]

    def test_upload_pdf_missing_user_id(self, client, sample_pdf_content):
        """Test upload without user_external_id."""
        files = {"file": ("test.pdf", sample_pdf_content, "application/pdf")}
        # Missing user_external_id

        response = client.post("/api/upload", files=files)

        assert response.status_code == 422
        # FastAPI validation error for missing required field

    def test_upload_pdf_missing_file(self, client):
        """Test upload without file."""
        data = {"user_external_id": "test_user_123"}
        # Missing file

        response = client.post("/api/upload", data=data)

        assert response.status_code == 422
        # FastAPI validation error for missing required field

    def test_upload_pdf_duplicate_file(self, client, sample_pdf_content):
        """Test uploading the same file twice."""
        files = {"file": ("test.pdf", sample_pdf_content, "application/pdf")}
        data = {"user_external_id": "test_user_123"}

        # First upload
        response1 = client.post("/api/upload", files=files, data=data)
        assert response1.status_code == 200
        first_result = response1.json()

        # Second upload (duplicate)
        response2 = client.post("/api/upload", files=files, data=data)
        assert response2.status_code == 200
        second_result = response2.json()

        # Should return same report_id and indicate duplicate
        assert second_result["report_id"] == first_result["report_id"]
        assert second_result["duplicate"] is True
        assert "already exists" in second_result["message"]

    def test_upload_stats_endpoint(self, client):
        """Test upload statistics endpoint."""
        response = client.get("/api/upload/stats")

        assert response.status_code == 200
        stats = response.json()

        assert "total_files" in stats
        assert "total_size" in stats
        assert "upload_directory" in stats
        assert isinstance(stats["total_files"], int)
        assert isinstance(stats["total_size"], int)

    @pytest.mark.slow
    def test_multiple_users_separate_files(self, client, sample_pdf_content):
        """Test that different users can upload the same file."""
        files = {"file": ("test.pdf", sample_pdf_content, "application/pdf")}

        # Upload for first user
        data1 = {"user_external_id": "user_1"}
        response1 = client.post("/api/upload", files=files, data=data1)
        assert response1.status_code == 200
        result1 = response1.json()

        # Upload same file for second user
        data2 = {"user_external_id": "user_2"}
        response2 = client.post("/api/upload", files=files, data=data2)
        assert response2.status_code == 200
        result2 = response2.json()

        # Should create separate reports for different users
        assert result1["report_id"] != result2["report_id"]
        assert result1["duplicate"] is False
        assert result2["duplicate"] is False

    def test_upload_pdf_different_extensions(self, client, sample_pdf_content):
        """Test upload with different valid PDF extensions."""
        # Test .PDF (uppercase)
        files = {"file": ("test.PDF", sample_pdf_content, "application/pdf")}
        data = {"user_external_id": "test_user_123"}

        response = client.post("/api/upload", files=files, data=data)
        assert response.status_code == 200

        # Test .pdf (lowercase)
        files = {"file": ("test2.pdf", sample_pdf_content, "application/pdf")}
        response = client.post("/api/upload", files=files, data=data)
        assert response.status_code == 200

    def test_upload_workflow_end_to_end(self, client, sample_pdf_content):
        """Test complete upload workflow from start to finish."""
        user_id = "integration_test_user"
        filename = "medical_report.pdf"

        # 1. Check initial upload stats
        stats_response = client.get("/api/upload/stats")
        initial_stats = stats_response.json()
        initial_count = initial_stats["total_files"]

        # 2. Upload PDF
        files = {"file": (filename, sample_pdf_content, "application/pdf")}
        data = {"user_external_id": user_id}

        upload_response = client.post("/api/upload", files=files, data=data)
        assert upload_response.status_code == 200

        upload_result = upload_response.json()
        report_id = upload_result["report_id"]

        # 3. Verify upload result structure
        assert isinstance(report_id, int)
        assert upload_result["filename"] == filename
        assert upload_result["duplicate"] is False
        assert len(upload_result["file_hash"]) == 64  # SHA-256
        assert upload_result["file_size"] == len(sample_pdf_content)

        # 4. Check updated upload stats
        updated_stats_response = client.get("/api/upload/stats")
        updated_stats = updated_stats_response.json()

        assert updated_stats["total_files"] == initial_count + 1
        assert updated_stats["total_size"] > initial_stats["total_size"]

        # 5. Verify duplicate detection works
        duplicate_response = client.post("/api/upload", files=files, data=data)
        assert duplicate_response.status_code == 200

        duplicate_result = duplicate_response.json()
        assert duplicate_result["report_id"] == report_id
        assert duplicate_result["duplicate"] is True

        # 6. Stats should not change for duplicate
        final_stats_response = client.get("/api/upload/stats")
        final_stats = final_stats_response.json()

        assert final_stats["total_files"] == updated_stats["total_files"]
        assert final_stats["total_size"] == updated_stats["total_size"]
