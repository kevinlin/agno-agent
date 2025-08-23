"""Tests for survey database models."""

import json
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine

from healthcare.config.config import Config
from healthcare.storage.database import DatabaseService
from healthcare.storage.models import (
    Survey,
    SurveyResponse,
    SurveyResponseStatus,
    SurveyResult,
    SurveyType,
    User,
)


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
    """Create a database service with temporary database."""
    service = DatabaseService(temp_config)
    service.create_tables()
    return service


@pytest.fixture
def test_user(db_service):
    """Create a test user."""
    return db_service.get_or_create_user("test_user_123")


@pytest.fixture
def test_survey_data():
    """Create test survey data."""
    return {
        "code": "test_survey",
        "type": "PERSONALIZATION",
        "version": "1.0.0",
        "title": "Test Survey",
        "description": "A test survey",
        "questions": [
            {
                "type": "INPUT",
                "code": "height_cm",
                "title": "What's your height?",
                "required": True,
                "unit": "INTEGER_NUMBER",
                "unit_text": "cm",
                "constraints": {"min": 80, "max": 250},
            },
            {
                "type": "SINGLE_SELECT",
                "code": "smoke_status",
                "title": "Do you smoke?",
                "required": True,
                "answers": {
                    "answers": [
                        {"code": "current", "title": "Yes, I currently smoke"},
                        {"code": "quit", "title": "No, I quit smoking"},
                        {"code": "never", "title": "No, I don't smoke"},
                    ]
                },
            },
        ],
        "branching_rules": [],
    }


class TestSurveyEnums:
    """Test survey-related enums."""

    def test_survey_type_enum(self):
        """Test SurveyType enum values."""
        assert SurveyType.PERSONALIZATION == "PERSONALIZATION"
        assert SurveyType.DISEASE_RISK == "DISEASE_RISK"
        assert SurveyType.LIFE_STYLE == "LIFE_STYLE"

    def test_survey_response_status_enum(self):
        """Test SurveyResponseStatus enum values."""
        assert SurveyResponseStatus.IN_PROGRESS == "in_progress"
        assert SurveyResponseStatus.COMPLETED == "completed"
        assert SurveyResponseStatus.CANCELLED == "cancelled"


class TestSurveyModel:
    """Test Survey model."""

    def test_survey_creation(self, db_service, test_survey_data):
        """Test creating a survey record."""
        with db_service.get_session() as session:
            survey = Survey(
                id="test_survey_id",
                code=test_survey_data["code"],
                title=test_survey_data["title"],
                version=test_survey_data["version"],
                type=SurveyType(test_survey_data["type"]),
                description=test_survey_data["description"],
                definition_json=json.dumps(test_survey_data),
            )
            session.add(survey)
            session.commit()
            session.refresh(survey)

            assert survey.id == "test_survey_id"
            assert survey.code == "test_survey"
            assert survey.title == "Test Survey"
            assert survey.version == "1.0.0"
            assert survey.type == SurveyType.PERSONALIZATION
            assert survey.description == "A test survey"
            assert isinstance(survey.created_at, datetime)

            # Verify JSON schema storage
            stored_schema = json.loads(survey.definition_json)
            assert stored_schema["code"] == test_survey_data["code"]
            assert len(stored_schema["questions"]) == 2

    def test_survey_unique_code_constraint(self, db_service, test_survey_data):
        """Test that survey codes must be unique."""
        with db_service.get_session() as session:
            # Create first survey
            survey1 = Survey(
                id="survey_1",
                code="duplicate_code",
                title="Survey 1",
                version="1.0.0",
                type=SurveyType.PERSONALIZATION,
                definition_json=json.dumps(test_survey_data),
            )
            session.add(survey1)
            session.commit()

            # Try to create second survey with same code
            survey2 = Survey(
                id="survey_2",
                code="duplicate_code",
                title="Survey 2",
                version="2.0.0",
                type=SurveyType.DISEASE_RISK,
                definition_json=json.dumps(test_survey_data),
            )
            session.add(survey2)

            with pytest.raises(Exception):  # Should raise integrity error
                session.commit()


class TestSurveyResponseModel:
    """Test SurveyResponse model."""

    def test_survey_response_creation(self, db_service, test_user, test_survey_data):
        """Test creating a survey response record."""
        with db_service.get_session() as session:
            # Create survey first
            survey = Survey(
                id="test_survey_id",
                code="test_survey",
                title="Test Survey",
                version="1.0.0",
                type=SurveyType.PERSONALIZATION,
                definition_json=json.dumps(test_survey_data),
            )
            session.add(survey)
            session.commit()

            # Create survey response
            response_id = str(uuid.uuid4())
            response = SurveyResponse(
                id=response_id,
                survey_id=survey.id,
                user_id=test_user.id,
                status=SurveyResponseStatus.IN_PROGRESS,
                progress_pct=25,
            )
            session.add(response)
            session.commit()
            session.refresh(response)

            assert response.id == response_id
            assert response.survey_id == "test_survey_id"
            assert response.user_id == test_user.id
            assert response.status == SurveyResponseStatus.IN_PROGRESS
            assert response.progress_pct == 25
            assert isinstance(response.created_at, datetime)
            assert isinstance(response.updated_at, datetime)

    def test_survey_response_default_values(
        self, db_service, test_user, test_survey_data
    ):
        """Test default values for survey response."""
        with db_service.get_session() as session:
            # Create survey first
            survey = Survey(
                id="test_survey_id",
                code="test_survey",
                title="Test Survey",
                version="1.0.0",
                type=SurveyType.PERSONALIZATION,
                definition_json=json.dumps(test_survey_data),
            )
            session.add(survey)
            session.commit()

            # Create response with minimal data
            response = SurveyResponse(
                id=str(uuid.uuid4()), survey_id=survey.id, user_id=test_user.id
            )
            session.add(response)
            session.commit()
            session.refresh(response)

            assert response.status == SurveyResponseStatus.IN_PROGRESS
            assert response.progress_pct == 0

    def test_survey_response_unique_user_survey_constraint(
        self, db_service, test_user, test_survey_data
    ):
        """Test that user can have only one response per survey."""
        with db_service.get_session() as session:
            # Create survey
            survey = Survey(
                id="test_survey_id",
                code="test_survey",
                title="Test Survey",
                version="1.0.0",
                type=SurveyType.PERSONALIZATION,
                definition_json=json.dumps(test_survey_data),
            )
            session.add(survey)
            session.commit()

            # Create first response
            response1 = SurveyResponse(
                id=str(uuid.uuid4()), survey_id=survey.id, user_id=test_user.id
            )
            session.add(response1)
            session.commit()

            # Try to create second response for same user-survey
            response2 = SurveyResponse(
                id=str(uuid.uuid4()), survey_id=survey.id, user_id=test_user.id
            )
            session.add(response2)

            with pytest.raises(Exception):  # Should raise integrity error
                session.commit()


class TestSurveyResultModel:
    """Test SurveyResult model."""

    def test_survey_result_creation(self, db_service, test_user, test_survey_data):
        """Test creating survey result records."""
        with db_service.get_session() as session:
            # Create survey and response
            survey = Survey(
                id="test_survey_id",
                code="test_survey",
                title="Test Survey",
                version="1.0.0",
                type=SurveyType.PERSONALIZATION,
                definition_json=json.dumps(test_survey_data),
            )
            session.add(survey)

            response = SurveyResponse(
                id=str(uuid.uuid4()),
                survey_id=survey.id,
                user_id=test_user.id,
                status=SurveyResponseStatus.COMPLETED,
            )
            session.add(response)
            session.commit()

            # Create result
            result_data = {
                "bmi": 22.5,
                "risk_score": 0.3,
                "recommendations": ["Exercise regularly", "Maintain healthy diet"],
            }

            result = SurveyResult(
                response_id=response.id, result_json=json.dumps(result_data)
            )
            session.add(result)
            session.commit()
            session.refresh(result)

            assert result.response_id == response.id
            assert isinstance(result.created_at, datetime)

            # Verify JSON result storage
            stored_result = json.loads(result.result_json)
            assert stored_result["bmi"] == 22.5
            assert stored_result["risk_score"] == 0.3
            assert len(stored_result["recommendations"]) == 2

    def test_survey_result_unique_response_constraint(
        self, db_service, test_user, test_survey_data
    ):
        """Test that each response can have only one result."""
        with db_service.get_session() as session:
            # Create survey and response
            survey = Survey(
                id="test_survey_id",
                code="test_survey",
                title="Test Survey",
                version="1.0.0",
                type=SurveyType.PERSONALIZATION,
                definition_json=json.dumps(test_survey_data),
            )
            session.add(survey)

            response = SurveyResponse(
                id=str(uuid.uuid4()), survey_id=survey.id, user_id=test_user.id
            )
            session.add(response)
            session.commit()

            # Create first result
            result1 = SurveyResult(
                response_id=response.id, result_json=json.dumps({"score": 1})
            )
            session.add(result1)
            session.commit()

            # Try to create second result for same response
            result2 = SurveyResult(
                response_id=response.id, result_json=json.dumps({"score": 2})
            )
            session.add(result2)

            with pytest.raises(Exception):  # Should raise integrity error
                session.commit()


class TestDatabaseIntegration:
    """Test database integration with survey models."""

    def test_tables_creation(self, db_service):
        """Test that all survey tables are created successfully."""
        # Tables should be created by the fixture
        with db_service.get_session() as session:
            # Test that we can perform basic operations on all tables

            # Create a user
            user = User(external_id="test_integration_user")
            session.add(user)
            session.commit()

            # Create a survey
            survey = Survey(
                id="integration_survey",
                code="integration_test",
                title="Integration Test Survey",
                version="1.0.0",
                type=SurveyType.PERSONALIZATION,
                definition_json=json.dumps({"questions": []}),
            )
            session.add(survey)
            session.commit()

            # Create a response
            response = SurveyResponse(
                id=str(uuid.uuid4()), survey_id=survey.id, user_id=user.id
            )
            session.add(response)
            session.commit()

            # Create a result
            result = SurveyResult(
                response_id=response.id, result_json=json.dumps({"test": "result"})
            )
            session.add(result)
            session.commit()

            # Verify all records were created
            assert session.get(User, user.id) is not None
            assert session.get(Survey, survey.id) is not None
            assert session.get(SurveyResponse, response.id) is not None
            assert session.get(SurveyResult, result.id) is not None
