"""Tests for storage models and database service."""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine

from agent.healthcare.config.config import Config
from agent.healthcare.storage.database import DatabaseService
from agent.healthcare.storage.models import MedicalReport, ReportAsset, User


@pytest.fixture
def temp_config():
    """Create a temporary config for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        config = Config(
            openai_api_key="test_key",
            base_data_dir=temp_path,
            uploads_dir=temp_path / "uploads",
            reports_dir=temp_path / "reports",
            chroma_dir=temp_path / "chroma",
            medical_db_path=temp_path / "test_medical.db",
            agent_db_path=temp_path / "test_agent.db",
        )
        yield config


@pytest.fixture
def db_service(temp_config):
    """Create a database service for testing."""
    service = DatabaseService(temp_config)
    service.create_tables()
    yield service
    service.close()


class TestUser:
    """Test User model."""

    def test_user_creation(self):
        """Test creating a user instance."""
        user = User(external_id="test_user")
        assert user.external_id == "test_user"
        assert user.id is None  # Not set until saved
        assert isinstance(user.created_at, datetime)


class TestMedicalReport:
    """Test MedicalReport model."""

    def test_medical_report_creation(self):
        """Test creating a medical report instance."""
        report = MedicalReport(
            user_id=1,
            filename="test_report.pdf",
            file_hash="abc123",
            markdown_path="/path/to/report.md",
            meta_json=json.dumps({"test": "data"}),
        )
        assert report.user_id == 1
        assert report.filename == "test_report.pdf"
        assert report.file_hash == "abc123"
        assert report.language == "en"  # default value
        assert isinstance(report.created_at, datetime)


class TestReportAsset:
    """Test ReportAsset model."""

    def test_report_asset_creation(self):
        """Test creating a report asset instance."""
        asset = ReportAsset(
            report_id=1, kind="image", path="/path/to/image.png", alt_text="Test image"
        )
        assert asset.report_id == 1
        assert asset.kind == "image"
        assert asset.path == "/path/to/image.png"
        assert asset.alt_text == "Test image"
        assert isinstance(asset.created_at, datetime)


class TestDatabaseService:
    """Test DatabaseService functionality."""

    def test_database_initialization(self, temp_config):
        """Test database service initialization."""
        service = DatabaseService(temp_config)
        assert service.config == temp_config
        assert service.db_path == temp_config.medical_db_path
        assert service.engine is not None
        service.close()

    def test_create_tables(self, db_service):
        """Test table creation."""
        # Tables should be created in fixture
        # Test that we can get a session
        with db_service.get_session() as session:
            assert isinstance(session, Session)

    def test_get_or_create_user_new(self, db_service):
        """Test creating a new user."""
        user = db_service.get_or_create_user("new_user")
        assert user.external_id == "new_user"
        assert user.id is not None
        assert isinstance(user.created_at, datetime)

    def test_get_or_create_user_existing(self, db_service):
        """Test getting an existing user."""
        # Create user first
        user1 = db_service.get_or_create_user("existing_user")
        original_id = user1.id

        # Get same user again
        user2 = db_service.get_or_create_user("existing_user")
        assert user2.id == original_id
        assert user2.external_id == "existing_user"

    def test_create_medical_report(self, db_service):
        """Test creating a medical report."""
        # Create user first
        user = db_service.get_or_create_user("test_user")

        # Create report
        report_data = {
            "filename": "test.pdf",
            "file_hash": "abc123def456",
            "markdown_path": "/path/to/test.md",
            "meta_json": json.dumps({"manifest": {"figures": [], "tables": []}}),
        }

        report = db_service.create_medical_report(user.id, report_data)
        assert report.user_id == user.id
        assert report.filename == "test.pdf"
        assert report.file_hash == "abc123def456"
        assert report.id is not None

    def test_create_duplicate_report(self, db_service):
        """Test handling duplicate report creation."""
        # Create user first
        user = db_service.get_or_create_user("test_user")

        # Create report
        report_data = {
            "filename": "test.pdf",
            "file_hash": "duplicate_hash",
            "markdown_path": "/path/to/test.md",
            "meta_json": json.dumps({}),
        }

        # Create first report
        report1 = db_service.create_medical_report(user.id, report_data)
        original_id = report1.id

        # Try to create duplicate
        report2 = db_service.create_medical_report(user.id, report_data)
        assert report2.id == original_id  # Should return existing report

    def test_create_report_assets(self, db_service):
        """Test creating report assets."""
        # Create user and report first
        user = db_service.get_or_create_user("test_user")
        report_data = {
            "filename": "test.pdf",
            "file_hash": "abc123",
            "markdown_path": "/path/to/test.md",
            "meta_json": json.dumps({}),
        }
        report = db_service.create_medical_report(user.id, report_data)

        # Create assets
        assets_data = [
            {
                "kind": "image",
                "path": "/path/to/image1.png",
                "alt_text": "Image 1",
                "page_number": 1,
            },
            {
                "kind": "image",
                "path": "/path/to/image2.png",
                "alt_text": "Image 2",
                "page_number": 2,
            },
        ]

        assets = db_service.create_report_assets(report.id, assets_data)
        assert len(assets) == 2
        assert assets[0].report_id == report.id
        assert assets[0].kind == "image"
        assert assets[1].report_id == report.id
        assert assets[1].kind == "image"

    def test_get_user_reports(self, db_service):
        """Test getting all reports for a user."""
        # Create user
        user = db_service.get_or_create_user("test_user")

        # Create multiple reports
        for i in range(3):
            report_data = {
                "filename": f"test{i}.pdf",
                "file_hash": f"hash{i}",
                "markdown_path": f"/path/to/test{i}.md",
                "meta_json": json.dumps({}),
            }
            db_service.create_medical_report(user.id, report_data)

        # Get all reports
        reports = db_service.get_user_reports(user.id)
        assert len(reports) == 3
        assert all(report.user_id == user.id for report in reports)

    def test_get_report_by_id(self, db_service):
        """Test getting a report by ID."""
        # Create user and report
        user = db_service.get_or_create_user("test_user")
        report_data = {
            "filename": "test.pdf",
            "file_hash": "abc123",
            "markdown_path": "/path/to/test.md",
            "meta_json": json.dumps({}),
        }
        report = db_service.create_medical_report(user.id, report_data)

        # Get report by ID
        retrieved_report = db_service.get_report_by_id(report.id)
        assert retrieved_report is not None
        assert retrieved_report.id == report.id
        assert retrieved_report.filename == "test.pdf"

        # Test non-existent ID
        non_existent = db_service.get_report_by_id(99999)
        assert non_existent is None

    def test_get_report_assets(self, db_service):
        """Test getting assets for a report."""
        # Create user and report
        user = db_service.get_or_create_user("test_user")
        report_data = {
            "filename": "test.pdf",
            "file_hash": "abc123",
            "markdown_path": "/path/to/test.md",
            "meta_json": json.dumps({}),
        }
        report = db_service.create_medical_report(user.id, report_data)

        # Create assets
        assets_data = [
            {"kind": "image", "path": "/path/to/image.png"},
            {"kind": "table", "path": "/path/to/table.csv"},
        ]
        db_service.create_report_assets(report.id, assets_data)

        # Get assets
        assets = db_service.get_report_assets(report.id)
        assert len(assets) == 2
        assert assets[0].report_id == report.id
        assert assets[1].report_id == report.id
