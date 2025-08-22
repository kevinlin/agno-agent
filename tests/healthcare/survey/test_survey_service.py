"""Tests for survey service functionality."""

import json
import tempfile
from pathlib import Path
from typing import Dict

import pytest
from fastapi import HTTPException

from healthcare.config.config import Config
from healthcare.storage.database import DatabaseService
from healthcare.storage.models import Survey, SurveyType
from healthcare.survey.service import SurveyService


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
