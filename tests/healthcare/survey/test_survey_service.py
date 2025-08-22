"""Tests for survey service functionality."""

import json
import tempfile
from pathlib import Path
from typing import Dict

import pytest
from fastapi import HTTPException

from healthcare.config.config import Config
from healthcare.storage.database import DatabaseService
from healthcare.storage.models import (
    Survey,
    SurveyResponse,
    SurveyResponseStatus,
    SurveyType,
    User,
)
from healthcare.survey.survey_service import SurveyService


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
    """Create a test database service."""
    service = DatabaseService(temp_config)
    service.create_tables()
    yield service
    service.close()


@pytest.fixture
def survey_service(temp_config, db_service):
    """Create a test survey service."""
    return SurveyService(temp_config, db_service)


@pytest.fixture
def sample_survey_definition() -> Dict:
    """Create a sample survey definition for testing."""
    return {
        "code": "test_survey",
        "type": "PERSONALIZATION",
        "version": "1.0.0",
        "title": "Test Survey",
        "description": "A test survey for unit testing",
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
                "code": "gender",
                "title": "What's your gender?",
                "required": True,
                "answers": {
                    "answers": [
                        {"code": "male", "title": "Male"},
                        {"code": "female", "title": "Female"},
                        {"code": "other", "title": "Other"},
                    ]
                },
            },
            {
                "type": "MULTIPLE_SELECT",
                "code": "conditions",
                "title": "Do you have any of these conditions?",
                "answers": {
                    "answers": [
                        {"code": "diabetes", "title": "Diabetes"},
                        {"code": "hypertension", "title": "High Blood Pressure"},
                        {
                            "code": "none",
                            "title": "None of the above",
                            "exclusive": True,
                        },
                    ]
                },
            },
        ],
        "branching_rules": [],
    }


@pytest.fixture
def invalid_survey_definition() -> Dict:
    """Create an invalid survey definition for testing validation."""
    return {
        "code": "invalid_survey",
        "type": "INVALID_TYPE",  # Invalid type
        "version": "1.0.0",
        "title": "Invalid Survey",
        "questions": [],  # Empty questions array
    }


class TestSurveyService:
    """Test cases for SurveyService."""

    def test_create_survey_success(self, survey_service, sample_survey_definition):
        """Test successful survey creation."""
        survey = survey_service.create_survey(
            code="test_survey",
            title="Test Survey",
            version="1.0.0",
            survey_type=SurveyType.PERSONALIZATION,
            definition=sample_survey_definition,
            description="Test description",
        )

        assert survey.code == "test_survey"
        assert survey.title == "Test Survey"
        assert survey.version == "1.0.0"
        assert survey.type == SurveyType.PERSONALIZATION
        assert survey.description == "Test description"
        assert survey.id is not None

        # Verify definition is stored correctly
        stored_definition = json.loads(survey.definition_json)
        assert stored_definition["code"] == "test_survey"
        assert len(stored_definition["questions"]) == 3

    def test_create_survey_duplicate_code(
        self, survey_service, sample_survey_definition
    ):
        """Test creating survey with duplicate code fails."""
        # Create first survey
        survey_service.create_survey(
            code="duplicate_survey",
            title="First Survey",
            version="1.0.0",
            survey_type=SurveyType.PERSONALIZATION,
            definition=sample_survey_definition,
        )

        # Try to create second survey with same code
        with pytest.raises(HTTPException) as exc_info:
            survey_service.create_survey(
                code="duplicate_survey",
                title="Second Survey",
                version="2.0.0",
                survey_type=SurveyType.DISEASE_RISK,
                definition=sample_survey_definition,
            )

        assert exc_info.value.status_code == 409
        assert "already exists" in str(exc_info.value.detail)

    def test_create_survey_invalid_definition(
        self, survey_service, invalid_survey_definition
    ):
        """Test creating survey with invalid definition fails."""
        with pytest.raises(HTTPException) as exc_info:
            survey_service.create_survey(
                code="invalid_survey",
                title="Invalid Survey",
                version="1.0.0",
                survey_type=SurveyType.PERSONALIZATION,
                definition=invalid_survey_definition,
            )

        assert exc_info.value.status_code == 400

    def test_get_survey_by_code(self, survey_service, sample_survey_definition):
        """Test retrieving survey by code."""
        # Create survey
        created_survey = survey_service.create_survey(
            code="get_test_survey",
            title="Get Test Survey",
            version="1.0.0",
            survey_type=SurveyType.PERSONALIZATION,
            definition=sample_survey_definition,
        )

        # Retrieve survey
        retrieved_survey = survey_service.get_survey_by_code("get_test_survey")

        assert retrieved_survey is not None
        assert retrieved_survey.id == created_survey.id
        assert retrieved_survey.code == "get_test_survey"
        assert retrieved_survey.title == "Get Test Survey"

    def test_get_survey_by_code_not_found(self, survey_service):
        """Test retrieving non-existent survey returns None."""
        survey = survey_service.get_survey_by_code("nonexistent_survey")
        assert survey is None

    def test_get_survey_by_id(self, survey_service, sample_survey_definition):
        """Test retrieving survey by ID."""
        # Create survey
        created_survey = survey_service.create_survey(
            code="id_test_survey",
            title="ID Test Survey",
            version="1.0.0",
            survey_type=SurveyType.PERSONALIZATION,
            definition=sample_survey_definition,
        )

        # Retrieve survey by ID
        retrieved_survey = survey_service.get_survey_by_id(created_survey.id)

        assert retrieved_survey is not None
        assert retrieved_survey.id == created_survey.id
        assert retrieved_survey.code == "id_test_survey"

    def test_list_surveys(self, survey_service, sample_survey_definition):
        """Test listing all surveys."""
        # Create multiple surveys
        survey_service.create_survey(
            code="survey1",
            title="Survey 1",
            version="1.0.0",
            survey_type=SurveyType.PERSONALIZATION,
            definition=sample_survey_definition,
        )

        survey_service.create_survey(
            code="survey2",
            title="Survey 2",
            version="1.0.0",
            survey_type=SurveyType.DISEASE_RISK,
            definition=sample_survey_definition,
        )

        # List all surveys
        surveys = survey_service.list_surveys()

        assert len(surveys) == 2
        assert any(s["code"] == "survey1" for s in surveys)
        assert any(s["code"] == "survey2" for s in surveys)

        # Check survey structure
        survey = surveys[0]
        required_fields = ["id", "code", "title", "type", "version", "created_at"]
        for field in required_fields:
            assert field in survey

    def test_list_surveys_filtered_by_type(
        self, survey_service, sample_survey_definition
    ):
        """Test listing surveys filtered by type."""
        # Create surveys of different types
        survey_service.create_survey(
            code="personalization_survey",
            title="Personalization Survey",
            version="1.0.0",
            survey_type=SurveyType.PERSONALIZATION,
            definition=sample_survey_definition,
        )

        survey_service.create_survey(
            code="disease_risk_survey",
            title="Disease Risk Survey",
            version="1.0.0",
            survey_type=SurveyType.DISEASE_RISK,
            definition=sample_survey_definition,
        )

        # List only personalization surveys
        personalization_surveys = survey_service.list_surveys(
            SurveyType.PERSONALIZATION
        )

        assert len(personalization_surveys) == 1
        assert personalization_surveys[0]["code"] == "personalization_survey"
        assert personalization_surveys[0]["type"] == "PERSONALIZATION"

    def test_get_survey_definition(self, survey_service, sample_survey_definition):
        """Test retrieving survey definition."""
        # Create survey
        survey_service.create_survey(
            code="definition_test",
            title="Definition Test",
            version="1.0.0",
            survey_type=SurveyType.PERSONALIZATION,
            definition=sample_survey_definition,
        )

        # Get definition
        definition = survey_service.get_survey_definition("definition_test")

        assert definition is not None
        assert definition["code"] == "test_survey"  # From sample definition
        assert definition["type"] == "PERSONALIZATION"
        assert len(definition["questions"]) == 3

    def test_get_survey_definition_not_found(self, survey_service):
        """Test getting definition for non-existent survey."""
        definition = survey_service.get_survey_definition("nonexistent")
        assert definition is None

    def test_load_survey_from_file(
        self, survey_service, sample_survey_definition, temp_config
    ):
        """Test loading survey from JSON file."""
        # Create temporary survey file
        survey_file = temp_config.base_data_dir / "test_survey.json"
        with open(survey_file, "w", encoding="utf-8") as f:
            json.dump(sample_survey_definition, f, ensure_ascii=False, indent=2)

        # Load survey from file
        survey = survey_service.load_survey_from_file(survey_file)

        assert survey.code == "test_survey"
        assert survey.title == "Test Survey"
        assert survey.type == SurveyType.PERSONALIZATION

    def test_load_survey_from_nonexistent_file(self, survey_service, temp_config):
        """Test loading survey from non-existent file fails."""
        nonexistent_file = temp_config.base_data_dir / "nonexistent.json"

        with pytest.raises(HTTPException) as exc_info:
            survey_service.load_survey_from_file(nonexistent_file)

        assert exc_info.value.status_code == 404

    def test_load_survey_from_invalid_json(self, survey_service, temp_config):
        """Test loading survey from invalid JSON file fails."""
        # Create file with invalid JSON
        invalid_file = temp_config.base_data_dir / "invalid.json"
        with open(invalid_file, "w") as f:
            f.write("{ invalid json }")

        with pytest.raises(HTTPException) as exc_info:
            survey_service.load_survey_from_file(invalid_file)

        assert exc_info.value.status_code == 400


class TestSurveyValidation:
    """Test cases for survey validation."""

    def test_validate_missing_required_fields(self, survey_service):
        """Test validation fails for missing required fields."""
        invalid_definition = {"code": "test"}  # Missing other required fields

        with pytest.raises(HTTPException) as exc_info:
            survey_service.create_survey(
                code="test",
                title="Test",
                version="1.0.0",
                survey_type=SurveyType.PERSONALIZATION,
                definition=invalid_definition,
            )

        assert exc_info.value.status_code == 400
        assert "Missing required field" in str(exc_info.value.detail)

    def test_validate_invalid_survey_type(
        self, survey_service, sample_survey_definition
    ):
        """Test validation fails for invalid survey type."""
        invalid_definition = sample_survey_definition.copy()
        invalid_definition["type"] = "INVALID_TYPE"

        with pytest.raises(HTTPException) as exc_info:
            survey_service.create_survey(
                code="test",
                title="Test",
                version="1.0.0",
                survey_type=SurveyType.PERSONALIZATION,
                definition=invalid_definition,
            )

        assert exc_info.value.status_code == 400
        assert "Invalid survey type" in str(exc_info.value.detail)

    def test_validate_empty_questions(self, survey_service, sample_survey_definition):
        """Test validation fails for empty questions array."""
        invalid_definition = sample_survey_definition.copy()
        invalid_definition["questions"] = []

        with pytest.raises(HTTPException) as exc_info:
            survey_service.create_survey(
                code="test",
                title="Test",
                version="1.0.0",
                survey_type=SurveyType.PERSONALIZATION,
                definition=invalid_definition,
            )

        assert exc_info.value.status_code == 400
        assert "at least one question" in str(exc_info.value.detail)

    def test_validate_question_missing_fields(
        self, survey_service, sample_survey_definition
    ):
        """Test validation fails for questions missing required fields."""
        invalid_definition = sample_survey_definition.copy()
        invalid_definition["questions"] = [{"type": "INPUT"}]  # Missing code and title

        with pytest.raises(HTTPException) as exc_info:
            survey_service.create_survey(
                code="test",
                title="Test",
                version="1.0.0",
                survey_type=SurveyType.PERSONALIZATION,
                definition=invalid_definition,
            )

        assert exc_info.value.status_code == 400
        assert "Missing required field" in str(exc_info.value.detail)

    def test_validate_invalid_question_type(
        self, survey_service, sample_survey_definition
    ):
        """Test validation fails for invalid question type."""
        invalid_definition = sample_survey_definition.copy()
        invalid_definition["questions"] = [
            {"type": "INVALID_TYPE", "code": "test", "title": "Test Question"}
        ]

        with pytest.raises(HTTPException) as exc_info:
            survey_service.create_survey(
                code="test",
                title="Test",
                version="1.0.0",
                survey_type=SurveyType.PERSONALIZATION,
                definition=invalid_definition,
            )

        assert exc_info.value.status_code == 400
        assert "Invalid question type" in str(exc_info.value.detail)

    def test_validate_input_question_missing_unit(
        self, survey_service, sample_survey_definition
    ):
        """Test validation fails for INPUT questions missing unit."""
        invalid_definition = sample_survey_definition.copy()
        invalid_definition["questions"] = [
            {
                "type": "INPUT",
                "code": "test_input",
                "title": "Test Input",
                # Missing unit field
            }
        ]

        with pytest.raises(HTTPException) as exc_info:
            survey_service.create_survey(
                code="test",
                title="Test",
                version="1.0.0",
                survey_type=SurveyType.PERSONALIZATION,
                definition=invalid_definition,
            )

        assert exc_info.value.status_code == 400
        assert "must have 'unit' field" in str(exc_info.value.detail)

    def test_validate_select_question_missing_answers(
        self, survey_service, sample_survey_definition
    ):
        """Test validation fails for select questions missing answers."""
        invalid_definition = sample_survey_definition.copy()
        invalid_definition["questions"] = [
            {
                "type": "SINGLE_SELECT",
                "code": "test_select",
                "title": "Test Select",
                # Missing answers field
            }
        ]

        with pytest.raises(HTTPException) as exc_info:
            survey_service.create_survey(
                code="test",
                title="Test",
                version="1.0.0",
                survey_type=SurveyType.PERSONALIZATION,
                definition=invalid_definition,
            )

        assert exc_info.value.status_code == 400
        assert "must have 'answers' field" in str(exc_info.value.detail)

    def test_validate_branching_rules_invalid_question_reference(
        self, survey_service, sample_survey_definition
    ):
        """Test validation fails for branching rules referencing invalid questions."""
        invalid_definition = sample_survey_definition.copy()
        invalid_definition["branching_rules"] = [
            {
                "id": "rule1",
                "condition": {
                    "operator": "equals",
                    "question_code": "nonexistent_question",
                    "value": "test",
                },
                "action": {"type": "skip_questions", "target": ["height_cm"]},
            }
        ]

        with pytest.raises(HTTPException) as exc_info:
            survey_service.create_survey(
                code="test",
                title="Test",
                version="1.0.0",
                survey_type=SurveyType.PERSONALIZATION,
                definition=invalid_definition,
            )

        assert exc_info.value.status_code == 400
        assert "References unknown question" in str(exc_info.value.detail)


class TestSurveyResponseManagement:
    """Test cases for survey response management functionality."""

    @pytest.fixture
    def test_user(self, db_service):
        """Create a test user."""
        with db_service.get_session() as session:
            user = User(external_id="test_user_123")
            session.add(user)
            session.commit()
            session.refresh(user)
            return user

    @pytest.fixture
    def test_survey(self, survey_service, sample_survey_definition):
        """Create a test survey."""
        return survey_service.create_survey(
            code="test_survey",
            title="Test Survey",
            version="1.0.0",
            survey_type=SurveyType.PERSONALIZATION,
            definition=sample_survey_definition,
            description="Test survey for response management",
        )

    def test_get_or_create_survey_response_new(
        self, survey_service, test_user, test_survey
    ):
        """Test creating a new survey response."""
        result = survey_service.get_or_create_survey_response(
            user_id=test_user.id, survey_code=test_survey.code
        )

        assert result is not None
        assert result["status"] == "in_progress"
        assert result["progress_pct"] == 0
        assert result["answers"] == []
        assert "id" in result
        assert "created_at" in result
        assert "updated_at" in result

    def test_get_or_create_survey_response_existing(
        self, survey_service, test_user, test_survey
    ):
        """Test getting an existing survey response."""
        # Create initial response
        first_result = survey_service.get_or_create_survey_response(
            user_id=test_user.id, survey_code=test_survey.code
        )

        # Save an answer to make it different
        survey_service.save_survey_answer(
            user_id=test_user.id,
            survey_code=test_survey.code,
            question_code="height_cm",
            value=175,
        )

        # Get the response again
        second_result = survey_service.get_or_create_survey_response(
            user_id=test_user.id, survey_code=test_survey.code
        )

        assert second_result is not None
        assert second_result["id"] == first_result["id"]  # Same response
        assert second_result["status"] == "in_progress"
        assert len(second_result["answers"]) == 1
        assert second_result["answers"][0]["question_code"] == "height_cm"
        assert second_result["answers"][0]["value"] == 175

    def test_get_or_create_survey_response_invalid_survey(
        self, survey_service, test_user
    ):
        """Test getting response for non-existent survey."""
        result = survey_service.get_or_create_survey_response(
            user_id=test_user.id, survey_code="nonexistent_survey"
        )

        assert result is None

    def test_save_survey_answer_success(self, survey_service, test_user, test_survey):
        """Test successfully saving a survey answer."""
        # Create response first
        survey_service.get_or_create_survey_response(
            user_id=test_user.id, survey_code=test_survey.code
        )

        # Save answer
        result = survey_service.save_survey_answer(
            user_id=test_user.id,
            survey_code=test_survey.code,
            question_code="height_cm",
            value=180,
        )

        assert result is not None
        assert result["ok"] is True
        assert result["progress_pct"] > 0  # Should calculate progress
        assert "response_id" in result

    def test_save_survey_answer_update_existing(
        self, survey_service, test_user, test_survey
    ):
        """Test updating an existing survey answer."""
        # Create response and save initial answer
        survey_service.get_or_create_survey_response(
            user_id=test_user.id, survey_code=test_survey.code
        )

        # Save initial answer
        survey_service.save_survey_answer(
            user_id=test_user.id,
            survey_code=test_survey.code,
            question_code="height_cm",
            value=180,
        )

        # Update the answer
        result = survey_service.save_survey_answer(
            user_id=test_user.id,
            survey_code=test_survey.code,
            question_code="height_cm",
            value=185,
        )

        assert result is not None
        assert result["ok"] is True

        # Verify the answer was updated
        response = survey_service.get_or_create_survey_response(
            user_id=test_user.id, survey_code=test_survey.code
        )
        assert len(response["answers"]) == 1
        assert response["answers"][0]["value"] == 185

    def test_save_survey_answer_invalid_survey(self, survey_service, test_user):
        """Test saving answer for non-existent survey."""
        result = survey_service.save_survey_answer(
            user_id=test_user.id,
            survey_code="nonexistent_survey",
            question_code="height_cm",
            value=180,
        )

        assert result is None

    def test_save_survey_answer_no_response(
        self, survey_service, test_user, test_survey
    ):
        """Test saving answer when no response exists."""
        # Don't create response first
        result = survey_service.save_survey_answer(
            user_id=test_user.id,
            survey_code=test_survey.code,
            question_code="height_cm",
            value=180,
        )

        assert result is None

    def test_complete_survey_response_success(
        self, survey_service, test_user, test_survey
    ):
        """Test successfully completing a survey response."""
        # Create response and save some answers
        survey_service.get_or_create_survey_response(
            user_id=test_user.id, survey_code=test_survey.code
        )

        # Save answers for BMI calculation
        survey_service.save_survey_answer(
            user_id=test_user.id,
            survey_code=test_survey.code,
            question_code="height_cm",
            value=175,
        )

        survey_service.save_survey_answer(
            user_id=test_user.id,
            survey_code=test_survey.code,
            question_code="weight",
            value=70,
        )

        # Complete the survey
        result = survey_service.complete_survey_response(
            user_id=test_user.id, survey_code=test_survey.code
        )

        assert result is not None
        assert result["ok"] is True
        assert result["status"] == "completed"
        assert "response_id" in result
        assert "derived_metrics" in result

        # Check if BMI was calculated
        metrics = result["derived_metrics"]
        assert "bmi" in metrics
        assert metrics["bmi"] == 22.86  # 70 / (1.75^2)
        assert "bmi_category" in metrics
        assert metrics["bmi_category"] == "normal"

    def test_complete_survey_response_with_custom_metrics(
        self, survey_service, test_user, test_survey
    ):
        """Test completing survey with custom derived metrics."""
        # Create response
        survey_service.get_or_create_survey_response(
            user_id=test_user.id, survey_code=test_survey.code
        )

        custom_metrics = {"custom_score": 85, "risk_level": "low"}

        # Complete with custom metrics
        result = survey_service.complete_survey_response(
            user_id=test_user.id,
            survey_code=test_survey.code,
            derived_metrics=custom_metrics,
        )

        assert result is not None
        assert result["ok"] is True
        assert result["derived_metrics"] == custom_metrics

    def test_complete_survey_response_invalid_survey(self, survey_service, test_user):
        """Test completing response for non-existent survey."""
        result = survey_service.complete_survey_response(
            user_id=test_user.id, survey_code="nonexistent_survey"
        )

        assert result is None

    def test_progress_calculation(self, survey_service, test_user, test_survey):
        """Test progress percentage calculation."""
        # Create response
        survey_service.get_or_create_survey_response(
            user_id=test_user.id, survey_code=test_survey.code
        )

        # Save first answer (1/3 questions = 33%)
        result1 = survey_service.save_survey_answer(
            user_id=test_user.id,
            survey_code=test_survey.code,
            question_code="height_cm",
            value=175,
        )
        assert result1["progress_pct"] == 33

        # Save second answer (2/3 questions = 66%)
        result2 = survey_service.save_survey_answer(
            user_id=test_user.id,
            survey_code=test_survey.code,
            question_code="gender",
            value="male",
        )
        assert result2["progress_pct"] == 66

        # Save third answer (3/3 questions = 100%)
        result3 = survey_service.save_survey_answer(
            user_id=test_user.id,
            survey_code=test_survey.code,
            question_code="conditions",
            value=["none"],
        )
        assert result3["progress_pct"] == 100

    def test_derived_metrics_bmi_calculation(
        self, survey_service, test_user, test_survey
    ):
        """Test BMI calculation in derived metrics."""
        # Create response and save height/weight
        survey_service.get_or_create_survey_response(
            user_id=test_user.id, survey_code=test_survey.code
        )

        survey_service.save_survey_answer(
            user_id=test_user.id,
            survey_code=test_survey.code,
            question_code="height",  # height in cm
            value=170,
        )

        survey_service.save_survey_answer(
            user_id=test_user.id,
            survey_code=test_survey.code,
            question_code="weight",  # weight in kg
            value=65,
        )

        # Complete survey to trigger metrics calculation
        result = survey_service.complete_survey_response(
            user_id=test_user.id, survey_code=test_survey.code
        )

        metrics = result["derived_metrics"]
        assert "bmi" in metrics
        assert metrics["bmi"] == 22.49  # 65 / (1.70^2)
        assert metrics["bmi_category"] == "normal"

    def test_derived_metrics_age_calculation(
        self, survey_service, test_user, test_survey
    ):
        """Test age calculation in derived metrics."""
        from datetime import datetime

        # Create response and save birth year
        survey_service.get_or_create_survey_response(
            user_id=test_user.id, survey_code=test_survey.code
        )

        current_year = datetime.now().year
        birth_year = current_year - 30

        survey_service.save_survey_answer(
            user_id=test_user.id,
            survey_code=test_survey.code,
            question_code="birth_year",
            value=birth_year,
        )

        # Complete survey
        result = survey_service.complete_survey_response(
            user_id=test_user.id, survey_code=test_survey.code
        )

        metrics = result["derived_metrics"]
        assert "age" in metrics
        assert metrics["age"] == 30

    def test_derived_metrics_personalization_survey(
        self, survey_service, test_user, test_survey
    ):
        """Test survey-specific metrics for personalization survey."""
        # Create personalization survey
        personalization_survey = survey_service.create_survey(
            code="personalization-survey",
            title="Personalization Survey",
            version="1.0.0",
            survey_type=SurveyType.PERSONALIZATION,
            definition={
                "code": "personalization-survey",
                "type": "PERSONALIZATION",
                "version": "1.0.0",
                "title": "Personalization Survey",
                "questions": [
                    {
                        "type": "INPUT",
                        "code": "age",
                        "title": "Age",
                        "unit": "INTEGER_NUMBER",
                    }
                ],
                "branching_rules": [],
            },
        )

        # Create response and complete
        survey_service.get_or_create_survey_response(
            user_id=test_user.id, survey_code="personalization-survey"
        )

        result = survey_service.complete_survey_response(
            user_id=test_user.id, survey_code="personalization-survey"
        )

        metrics = result["derived_metrics"]
        assert "survey_type" in metrics
        assert metrics["survey_type"] == "personalization"
        assert "completion_date" in metrics
