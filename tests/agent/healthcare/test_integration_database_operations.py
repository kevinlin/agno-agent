"""Integration tests for database operations."""

import os
import tempfile
from datetime import datetime
from pathlib import Path

import pytest
from sqlmodel import select

from agent.healthcare.config.config import Config
from agent.healthcare.reports.service import ReportService
from agent.healthcare.search.search_service import SearchService
from agent.healthcare.storage.database import DatabaseService
from agent.healthcare.storage.embeddings import EmbeddingService
from agent.healthcare.storage.models import MedicalReport, ReportAsset, User


class TestDatabaseOperationsIntegration:
    """Integration test suite for database operations."""

    def setup_method(self):
        """Set up test fixtures for each test."""
        # Create temporary directory for test data
        self.temp_dir = tempfile.mkdtemp()
        self.test_data_dir = Path(self.temp_dir)

        # Create test configuration
        self.config = Config(
            openai_api_key="test-key",
            openai_model="gpt-5-mini",
            embedding_model="text-embedding-3-large",
            base_data_dir=self.test_data_dir,
            medical_db_path=self.test_data_dir / "test_medical.db",
            agent_db_path=self.test_data_dir / "test_agent.db",
            chroma_dir=self.test_data_dir / "chroma",
        )

        # Initialize database service
        self.db_service = DatabaseService(self.config)
        self.db_service.create_tables()

    def teardown_method(self):
        """Clean up after each test."""
        self.db_service.close()
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_user_operations(self):
        """Test user creation and retrieval operations."""

        # Test creating a new user
        user = self.db_service.get_or_create_user("test_user_123")
        assert user is not None
        assert user.external_id == "test_user_123"
        assert user.id is not None
        assert user.created_at is not None

        # Test retrieving existing user
        user2 = self.db_service.get_or_create_user("test_user_123")
        assert user2.id == user.id
        assert user2.external_id == user.external_id

        # Test creating different user
        user3 = self.db_service.get_or_create_user("different_user")
        assert user3.id != user.id
        assert user3.external_id == "different_user"

    def test_medical_report_operations(self):
        """Test medical report creation and retrieval."""

        # Create user first
        user = self.db_service.get_or_create_user("report_test_user")

        # Test creating medical report
        report_data = {
            "filename": "test_report.pdf",
            "file_hash": "abc123def456",
            "language": "en",
            "markdown_path": str(self.test_data_dir / "test_report.md"),
            "images_dir": str(self.test_data_dir / "images"),
            "meta_json": '{"manifest": {"figures": [], "tables": []}}',
        }

        report = self.db_service.create_medical_report(user.id, report_data)
        assert report is not None
        assert report.user_id == user.id
        assert report.filename == "test_report.pdf"
        assert report.file_hash == "abc123def456"
        assert report.id is not None

        # Test retrieving report
        with self.db_service.get_session() as session:
            retrieved_report = session.get(MedicalReport, report.id)
            assert retrieved_report is not None
            assert retrieved_report.filename == "test_report.pdf"
            assert retrieved_report.user_id == user.id

    def test_duplicate_report_prevention(self):
        """Test that duplicate reports are prevented."""

        user = self.db_service.get_or_create_user("duplicate_test_user")

        report_data = {
            "filename": "duplicate_test.pdf",
            "file_hash": "duplicate_hash_123",
            "language": "en",
            "markdown_path": str(self.test_data_dir / "duplicate.md"),
            "images_dir": None,
            "meta_json": "{}",
        }

        # Create first report
        report1 = self.db_service.create_medical_report(user.id, report_data)
        assert report1 is not None

        # Try to create duplicate (same user + same hash)
        # Should return existing report instead of creating new one
        report2 = self.db_service.create_medical_report(user.id, report_data)
        assert report2.id == report1.id  # Should return the same report

        # But different user with same hash should work
        user2 = self.db_service.get_or_create_user("different_user_duplicate")
        report3 = self.db_service.create_medical_report(user2.id, report_data)
        assert report3 is not None
        assert report3.id != report1.id

    def test_report_asset_operations(self):
        """Test report asset creation and retrieval."""

        user = self.db_service.get_or_create_user("asset_test_user")

        # Create report
        report_data = {
            "filename": "asset_test.pdf",
            "file_hash": "asset_hash_123",
            "language": "en",
            "markdown_path": str(self.test_data_dir / "asset_test.md"),
            "images_dir": str(self.test_data_dir / "images"),
            "meta_json": "{}",
        }
        report = self.db_service.create_medical_report(user.id, report_data)

        # Create test assets
        assets_data = [
            {
                "kind": "image",
                "path": str(self.test_data_dir / "image1.png"),
                "alt_text": "Medical chart image",
            },
            {
                "kind": "image",
                "path": str(self.test_data_dir / "image2.png"),
                "alt_text": "X-ray image",
            },
            {
                "kind": "table",
                "path": str(self.test_data_dir / "table1.csv"),
                "alt_text": "Lab results table",
            },
        ]

        # Create assets
        self.db_service.create_report_assets(report.id, assets_data)

        # Verify assets were created
        with self.db_service.get_session() as session:
            assets = session.exec(
                select(ReportAsset).where(ReportAsset.report_id == report.id)
            ).all()

            assert len(assets) == 3

            # Check image assets
            image_assets = [a for a in assets if a.kind == "image"]
            assert len(image_assets) == 2

            # Check table asset
            table_assets = [a for a in assets if a.kind == "table"]
            assert len(table_assets) == 1
            assert "table1.csv" in table_assets[0].path

    def test_user_report_isolation(self):
        """Test that reports are properly isolated between users."""

        # Create two users
        user1 = self.db_service.get_or_create_user("isolation_user1")
        user2 = self.db_service.get_or_create_user("isolation_user2")

        # Create reports for each user
        report_data1 = {
            "filename": "user1_report.pdf",
            "file_hash": "user1_hash",
            "language": "en",
            "markdown_path": str(self.test_data_dir / "user1.md"),
            "images_dir": None,
            "meta_json": "{}",
        }

        report_data2 = {
            "filename": "user2_report.pdf",
            "file_hash": "user2_hash",
            "language": "en",
            "markdown_path": str(self.test_data_dir / "user2.md"),
            "images_dir": None,
            "meta_json": "{}",
        }

        report1 = self.db_service.create_medical_report(user1.id, report_data1)
        report2 = self.db_service.create_medical_report(user2.id, report_data2)

        # Verify each user only sees their own reports
        with self.db_service.get_session() as session:
            user1_reports = session.exec(
                select(MedicalReport).where(MedicalReport.user_id == user1.id)
            ).all()
            assert len(user1_reports) == 1
            assert user1_reports[0].id == report1.id

            user2_reports = session.exec(
                select(MedicalReport).where(MedicalReport.user_id == user2.id)
            ).all()
            assert len(user2_reports) == 1
            assert user2_reports[0].id == report2.id

    def test_database_service_integration_with_report_service(self):
        """Test database service integration with report service."""

        # Create report service
        report_service = ReportService(self.config, self.db_service)

        # Create user and report via database service
        user = self.db_service.get_or_create_user("integration_user")

        # Create markdown file
        markdown_content = "# Test Report\n\nThis is a test medical report."
        markdown_path = self.test_data_dir / "integration_test.md"
        markdown_path.write_text(markdown_content)

        report_data = {
            "filename": "integration_test.pdf",
            "file_hash": "integration_hash",
            "language": "en",
            "markdown_path": str(markdown_path),
            "images_dir": None,
            "meta_json": "{}",
        }

        report = self.db_service.create_medical_report(user.id, report_data)

        # Test report service can access the data
        reports = report_service.list_user_reports("integration_user")
        assert len(reports) == 1
        assert reports[0]["id"] == report.id
        assert reports[0]["filename"] == "integration_test.pdf"

        # Test getting markdown content
        content = report_service.get_report_markdown(report.id, "integration_user")
        assert "Test Report" in content
        assert "test medical report" in content

    def test_database_transaction_handling(self):
        """Test proper transaction handling and rollback."""

        user = self.db_service.get_or_create_user("transaction_user")

        # Test successful transaction
        with self.db_service.get_session() as session:
            report_data = {
                "filename": "transaction_test.pdf",
                "file_hash": "transaction_hash",
                "language": "en",
                "markdown_path": str(self.test_data_dir / "transaction.md"),
                "images_dir": None,
                "meta_json": "{}",
            }

            report = self.db_service.create_medical_report(user.id, report_data)

            # Verify report exists
            assert report.id is not None

        # Verify report persisted after session
        with self.db_service.get_session() as session:
            persisted_report = session.get(MedicalReport, report.id)
            assert persisted_report is not None
            assert persisted_report.filename == "transaction_test.pdf"

    def test_database_connection_management(self):
        """Test proper database connection management."""

        # Test multiple sessions
        user_ids = []
        for i in range(5):
            user = self.db_service.get_or_create_user(f"connection_user_{i}")
            user_ids.append(user.id)

        # Verify all users were created
        with self.db_service.get_session() as session:
            users = session.exec(select(User).where(User.id.in_(user_ids))).all()
            assert len(users) == 5

        # Test concurrent-like access
        reports = []
        for i, user_id in enumerate(user_ids):
            report_data = {
                "filename": f"concurrent_test_{i}.pdf",
                "file_hash": f"concurrent_hash_{i}",
                "language": "en",
                "markdown_path": str(self.test_data_dir / f"concurrent_{i}.md"),
                "images_dir": None,
                "meta_json": "{}",
            }
            report = self.db_service.create_medical_report(user_id, report_data)
            reports.append(report)

        # Verify all reports were created
        assert len(reports) == 5
        assert len(set(r.id for r in reports)) == 5  # All unique IDs

    def test_database_schema_validation(self):
        """Test database schema validation and constraints."""

        user = self.db_service.get_or_create_user("schema_test_user")

        # Test required fields
        with pytest.raises(Exception):
            # Missing required filename
            invalid_data = {
                "file_hash": "schema_hash",
                "language": "en",
                "markdown_path": str(self.test_data_dir / "schema.md"),
                "meta_json": "{}",
            }
            self.db_service.create_medical_report(user.id, invalid_data)

        # Test valid data
        valid_data = {
            "filename": "schema_valid.pdf",
            "file_hash": "schema_valid_hash",
            "language": "en",
            "markdown_path": str(self.test_data_dir / "schema_valid.md"),
            "images_dir": None,
            "meta_json": "{}",
        }

        report = self.db_service.create_medical_report(user.id, valid_data)
        assert report is not None

    def test_database_performance_basic(self):
        """Test basic database performance characteristics."""

        import time

        # Time user creation
        start_time = time.time()
        users = []
        for i in range(10):
            user = self.db_service.get_or_create_user(f"perf_user_{i}")
            users.append(user)
        user_creation_time = time.time() - start_time

        # Should be reasonably fast (less than 1 second for 10 users)
        assert user_creation_time < 1.0

        # Time report creation
        start_time = time.time()
        reports = []
        for i, user in enumerate(users):
            report_data = {
                "filename": f"perf_report_{i}.pdf",
                "file_hash": f"perf_hash_{i}",
                "language": "en",
                "markdown_path": str(self.test_data_dir / f"perf_{i}.md"),
                "images_dir": None,
                "meta_json": "{}",
            }
            report = self.db_service.create_medical_report(user.id, report_data)
            reports.append(report)
        report_creation_time = time.time() - start_time

        # Should be reasonably fast (less than 2 seconds for 10 reports)
        assert report_creation_time < 2.0

        # Time bulk retrieval
        start_time = time.time()
        with self.db_service.get_session() as session:
            all_reports = session.exec(select(MedicalReport)).all()
        retrieval_time = time.time() - start_time

        assert len(all_reports) >= 10
        # Should be very fast (less than 0.1 seconds)
        assert retrieval_time < 0.1

    def test_database_cleanup_and_consistency(self):
        """Test database cleanup and data consistency."""

        user = self.db_service.get_or_create_user("cleanup_user")

        # Create report with assets
        report_data = {
            "filename": "cleanup_test.pdf",
            "file_hash": "cleanup_hash",
            "language": "en",
            "markdown_path": str(self.test_data_dir / "cleanup.md"),
            "images_dir": str(self.test_data_dir / "images"),
            "meta_json": "{}",
        }

        report = self.db_service.create_medical_report(user.id, report_data)

        # Add assets
        assets_data = [
            {
                "kind": "image",
                "path": str(self.test_data_dir / "cleanup_image.png"),
                "alt_text": "Cleanup test image",
            }
        ]
        self.db_service.create_report_assets(report.id, assets_data)

        # Verify data consistency
        with self.db_service.get_session() as session:
            # Check report exists
            db_report = session.get(MedicalReport, report.id)
            assert db_report is not None

            # Check assets exist
            assets = session.exec(
                select(ReportAsset).where(ReportAsset.report_id == report.id)
            ).all()
            assert len(assets) == 1

            # Check foreign key relationship
            assert assets[0].report_id == report.id

            # Verify user relationship
            db_user = session.get(User, user.id)
            assert db_user is not None
            assert db_report.user_id == db_user.id
