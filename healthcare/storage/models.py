"""Database models for healthcare agent using SQLModel."""

from datetime import UTC, datetime
from enum import Enum
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


# Survey-related enums
class SurveyType(str, Enum):
    """Survey type enumeration."""

    PERSONALIZATION = "PERSONALIZATION"
    DISEASE_RISK = "DISEASE_RISK"
    LIFE_STYLE = "LIFE_STYLE"


class SurveyResponseStatus(str, Enum):
    """Survey response status enumeration."""

    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# Survey database models
class Survey(SQLModel, table=True):
    """Survey definition model."""

    id: Optional[str] = Field(default=None, primary_key=True)
    code: str = Field(unique=True, index=True)
    title: str
    version: str
    type: SurveyType
    description: Optional[str] = None
    definition_json: str  # JSON-encoded survey definition
    created_at: datetime = Field(default_factory=utc_now)


class SurveyResponse(SQLModel, table=True):
    """Survey response tracking model."""

    id: Optional[str] = Field(default=None, primary_key=True)  # UUID
    survey_id: str = Field(foreign_key="survey.id")
    user_id: int = Field(foreign_key="user.id")
    status: SurveyResponseStatus = Field(default=SurveyResponseStatus.IN_PROGRESS)
    progress_pct: int = Field(default=0, ge=0, le=100)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    __table_args__ = (UniqueConstraint("user_id", "survey_id"),)


class SurveyAnswer(SQLModel, table=True):
    """Individual answer storage model."""

    id: Optional[int] = Field(default=None, primary_key=True)
    response_id: str = Field(foreign_key="surveyresponse.id")
    question_code: str
    value_json: str  # JSON-encoded answer value
    created_at: datetime = Field(default_factory=utc_now)

    __table_args__ = (UniqueConstraint("response_id", "question_code"),)


class SurveyResult(SQLModel, table=True):
    """Computed survey results model."""

    id: Optional[int] = Field(default=None, primary_key=True)
    response_id: str = Field(foreign_key="surveyresponse.id", unique=True)
    result_json: str  # JSON-encoded computed metrics
    created_at: datetime = Field(default_factory=utc_now)
