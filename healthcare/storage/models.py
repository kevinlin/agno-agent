"""Database models for healthcare agent using SQLModel."""

from datetime import UTC, datetime
from typing import Optional

from sqlmodel import Field, SQLModel, UniqueConstraint


def utc_now() -> datetime:
    """Get current UTC datetime using the recommended approach."""
    return datetime.now(UTC)


class User(SQLModel, table=True):
    """User model for external user identification."""

    id: Optional[int] = Field(default=None, primary_key=True)
    external_id: str = Field(unique=True, index=True)
    created_at: datetime = Field(default_factory=utc_now)


class MedicalReport(SQLModel, table=True):
    """Medical report model for storing report metadata."""

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    filename: str
    file_hash: str = Field(index=True)
    language: Optional[str] = "en"
    markdown_path: str
    images_dir: Optional[str] = None
    meta_json: str  # JSON-encoded manifest
    created_at: datetime = Field(default_factory=utc_now)

    __table_args__ = (UniqueConstraint("user_id", "file_hash"),)


class ReportAsset(SQLModel, table=True):
    """Model for tracking report assets like images and tables."""

    id: Optional[int] = Field(default=None, primary_key=True)
    report_id: int = Field(foreign_key="medicalreport.id")
    kind: str  # "image" | "table"
    path: str
    alt_text: Optional[str] = None
    page_number: Optional[int] = None
    created_at: datetime = Field(default_factory=utc_now)
