"""Demonstration script for PDF upload functionality."""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from agent.healthcare.config.config import Config
from agent.healthcare.storage.database import DatabaseService
from agent.healthcare.upload.upload_service import PDFUploadService


async def create_sample_pdf() -> bytes:
    """Create a sample PDF content for demonstration."""
    return b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000074 00000 n \n0000000120 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n179\n%%EOF"


class MockUploadFile:
    """Mock UploadFile for demonstration."""

    def __init__(self, filename: str, content: bytes):
        self.filename = filename
        self.content = content

    async def read(self) -> bytes:
        return self.content


async def demo_upload_service():
    """Demonstrate the PDF upload service functionality."""
    print("Healthcare Agent - PDF Upload Service Demo")
    print("=" * 50)

    # Create temporary directory for demo
    temp_dir = tempfile.mkdtemp()
    print(f"Using temporary directory: {temp_dir}")

    try:
        # Create configuration
        config = Config(
            openai_api_key="demo_key",
            base_data_dir=Path(temp_dir) / "data",
            uploads_dir=Path(temp_dir) / "data/uploads",
            reports_dir=Path(temp_dir) / "data/reports",
            chroma_dir=Path(temp_dir) / "data/chroma",
            medical_db_path=Path(temp_dir) / "data/medical.db",
            agent_db_path=Path(temp_dir) / "data/agent_sessions.db",
        )

        # Create database service
        db_service = DatabaseService(config)
        db_service.create_tables()
        print("✓ Database initialized")

        # Create upload service
        upload_service = PDFUploadService(config, db_service)
        print("✓ Upload service created")

        # Create sample PDF
        pdf_content = await create_sample_pdf()
        print(f"✓ Sample PDF created ({len(pdf_content)} bytes)")

        # Test PDF validation
        is_valid = upload_service.validate_pdf(pdf_content)
        print(f"✓ PDF validation: {'VALID' if is_valid else 'INVALID'}")

        # Test hash computation
        file_hash = upload_service.compute_hash(pdf_content)
        print(f"✓ File hash: {file_hash}")

        # Test file upload
        mock_file = MockUploadFile("demo_report.pdf", pdf_content)
        upload_result = await upload_service.upload_pdf("demo_user", mock_file)
        print(f"✓ Upload result: {upload_result}")

        # Test duplicate detection
        duplicate_result = await upload_service.upload_pdf("demo_user", mock_file)
        print(f"✓ Duplicate detection: {duplicate_result}")

        # Test upload stats
        stats = upload_service.get_upload_stats()
        print(f"✓ Upload stats: {stats}")

        print("\n" + "=" * 50)
        print("🎉 Demo completed successfully!")
        print(f"Files created in: {config.uploads_dir}")

        # List created files
        if config.uploads_dir.exists():
            files = list(config.uploads_dir.glob("*"))
            print(f"Created files: {[f.name for f in files]}")

    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # Cleanup
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)
        print(f"✓ Cleaned up temporary directory: {temp_dir}")


def demo_validation_scenarios():
    """Demonstrate various validation scenarios."""
    print("\nPDF Validation Scenarios Demo")
    print("-" * 30)

    # Create a basic service for validation testing
    temp_dir = tempfile.mkdtemp()
    config = Config(openai_api_key="demo_key", uploads_dir=Path(temp_dir) / "uploads")

    mock_db_service = MagicMock()
    service = PDFUploadService(config, mock_db_service)

    test_cases = [
        ("Valid PDF", b"%PDF-1.4\nvalid content"),
        ("Invalid - Plain text", b"This is just text"),
        ("Invalid - Empty file", b""),
        ("Invalid - HTML", b"<html><body>Not a PDF</body></html>"),
        ("Invalid - Incomplete header", b"%PDF"),
        ("Valid - Different version", b"%PDF-1.7\nother valid content"),
    ]

    for description, content in test_cases:
        is_valid = service.validate_pdf(content)
        status = "✓ VALID" if is_valid else "✗ INVALID"
        print(f"{description:25} : {status}")

    # Cleanup
    import shutil

    shutil.rmtree(temp_dir, ignore_errors=True)


async def main():
    """Run the demonstration."""
    await demo_upload_service()
    demo_validation_scenarios()


if __name__ == "__main__":
    asyncio.run(main())
