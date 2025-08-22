"""Unit tests for survey API routes."""

import json
import uuid
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from healthcare.config.config import Config
from healthcare.storage.models import SurveyType, User
from healthcare.survey.routes import router
from healthcare.survey.survey_service import SurveyService


class TestSurveyRoutes:
    """Test suite for survey API routes using dependency overrides."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create test FastAPI app with survey router
        self.app = FastAPI()
        self.app.include_router(router)
        self.client = TestClient(self.app)

        # Mock configuration
        self.mock_config = Config(
            openai_api_key="test-key",
            openai_model="gpt-4-mini",
            embedding_model="text-embedding-3-large",
            base_data_dir=Path("test_data"),
        )

        # Mock services
        self.mock_db_service = Mock()
        self.mock_survey_service = Mock()
        self.mock_user = User(id=1, external_id="test-user-123")

        # Sample survey data
        self.sample_survey_definition = {
            "code": "test-survey",
            "type": "PERSONALIZATION",
            "version": "1.0.0",
            "title": "Test Survey",
            "description": "A test survey",
            "questions": [
                {
                    "type": "INPUT",
                    "code": "age",
                    "title": "What is your age?",
                    "unit": "INTEGER_NUMBER",
                    "required": True,
                },
                {
                    "type": "SINGLE_SELECT",
                    "code": "gender",
                    "title": "What is your gender?",
                    "required": True,
                    "answers": [
                        {"code": "M", "text": "Male"},
                        {"code": "F", "text": "Female"},
                        {"code": "O", "text": "Other"},
                    ],
                },
            ],
            "branching_rules": [],
        }

    def override_dependencies(self):
        """Override FastAPI dependencies with mocks."""
        from healthcare.survey.routes import get_database_service, get_survey_service

        def mock_get_database_service():
            return self.mock_db_service

        def mock_get_survey_service():
            return self.mock_survey_service

        self.app.dependency_overrides[get_database_service] = mock_get_database_service
        self.app.dependency_overrides[get_survey_service] = mock_get_survey_service

    def teardown_method(self):
        """Clean up after each test."""
        # Clear dependency overrides
        self.app.dependency_overrides.clear()

    def test_create_survey_success(self):
        """Test successful survey creation."""
        self.override_dependencies()

        # Mock survey service response
        mock_survey = Mock()
        mock_survey.id = str(uuid.uuid4())
        mock_survey.code = "test-survey"
        self.mock_survey_service.create_survey.return_value = mock_survey

        # Test data
        create_request = {
            "code": "test-survey",
            "title": "Test Survey",
            "version": "1.0.0",
            "type": "PERSONALIZATION",
            "description": "A test survey",
            "definition": self.sample_survey_definition,
        }

        # Make request
        response = self.client.post("/api/survey", json=create_request)

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["survey_id"] == mock_survey.id
        assert "created successfully" in data["message"]

        # Verify service was called correctly
        self.mock_survey_service.create_survey.assert_called_once_with(
            code="test-survey",
            title="Test Survey",
            version="1.0.0",
            survey_type=SurveyType.PERSONALIZATION,
            definition=self.sample_survey_definition,
            description="A test survey",
        )

    def test_create_survey_invalid_type(self):
        """Test survey creation with invalid type."""
        self.override_dependencies()

        # Test data with invalid type
        create_request = {
            "code": "test-survey",
            "title": "Test Survey",
            "version": "1.0.0",
            "type": "INVALID_TYPE",
            "definition": self.sample_survey_definition,
        }

        # Make request
        response = self.client.post("/api/survey", json=create_request)

        # Assertions
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["ok"] is False
        assert data["detail"]["error"]["code"] == "invalid_survey_type"
        assert "INVALID_TYPE" in data["detail"]["error"]["message"]

    def test_create_survey_service_error(self):
        """Test survey creation with service error."""
        self.override_dependencies()

        # Mock service to raise exception
        self.mock_survey_service.create_survey.side_effect = Exception("Service error")

        # Test data
        create_request = {
            "code": "test-survey",
            "title": "Test Survey",
            "version": "1.0.0",
            "type": "PERSONALIZATION",
            "definition": self.sample_survey_definition,
        }

        # Make request
        response = self.client.post("/api/survey", json=create_request)

        # Assertions
        assert response.status_code == 500
        data = response.json()
        assert data["detail"]["ok"] is False
        assert data["detail"]["error"]["code"] == "creation_failed"

    def test_list_surveys_success(self):
        """Test successful survey listing."""
        self.override_dependencies()

        # Mock survey service response
        mock_surveys = [
            {
                "id": str(uuid.uuid4()),
                "code": "survey-1",
                "title": "Survey 1",
                "type": "PERSONALIZATION",
                "version": "1.0.0",
            },
            {
                "id": str(uuid.uuid4()),
                "code": "survey-2",
                "title": "Survey 2",
                "type": "DISEASE_RISK",
                "version": "2.0.0",
            },
        ]
        self.mock_survey_service.list_surveys.return_value = mock_surveys

        # Make request
        response = self.client.get("/api/survey")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["code"] == "survey-1"
        assert data[0]["active_version"] == "1.0.0"
        assert data[1]["code"] == "survey-2"
        assert data[1]["active_version"] == "2.0.0"

        # Verify service was called correctly
        self.mock_survey_service.list_surveys.assert_called_once_with(None)

    def test_list_surveys_with_type_filter(self):
        """Test survey listing with type filter."""
        self.override_dependencies()

        # Mock survey service response
        mock_surveys = [
            {
                "id": str(uuid.uuid4()),
                "code": "survey-1",
                "title": "Survey 1",
                "type": "PERSONALIZATION",
                "version": "1.0.0",
            }
        ]
        self.mock_survey_service.list_surveys.return_value = mock_surveys

        # Make request with type filter
        response = self.client.get("/api/survey?type=PERSONALIZATION")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["type"] == "PERSONALIZATION"

        # Verify service was called correctly
        self.mock_survey_service.list_surveys.assert_called_once_with(
            SurveyType.PERSONALIZATION
        )

    def test_list_surveys_invalid_type_filter(self):
        """Test survey listing with invalid type filter."""
        self.override_dependencies()

        # Make request with invalid type filter
        response = self.client.get("/api/survey?type=INVALID_TYPE")

        # Assertions
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["ok"] is False
        assert data["detail"]["error"]["code"] == "invalid_survey_type"

    def test_get_survey_definition_success(self):
        """Test successful survey definition retrieval."""
        self.override_dependencies()

        # Mock survey service response
        self.mock_survey_service.get_survey_definition.return_value = (
            self.sample_survey_definition
        )

        # Make request
        response = self.client.get("/api/survey/test-survey")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "test-survey"
        assert data["title"] == "Test Survey"
        assert len(data["questions"]) == 2

        # Verify service was called correctly
        self.mock_survey_service.get_survey_definition.assert_called_once_with(
            "test-survey"
        )

    def test_get_survey_definition_not_found(self):
        """Test survey definition retrieval for non-existent survey."""
        self.override_dependencies()

        # Mock survey service response
        self.mock_survey_service.get_survey_definition.return_value = None

        # Make request
        response = self.client.get("/api/survey/non-existent")

        # Assertions
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["ok"] is False
        assert data["detail"]["error"]["code"] == "survey_not_found"

    @patch("healthcare.survey.routes.get_or_create_user")
    def test_get_survey_response_success(self, mock_get_user):
        """Test successful survey response retrieval."""
        self.override_dependencies()

        # Mock user creation
        mock_get_user.return_value = self.mock_user

        # Mock survey service responses
        mock_response_data = {
            "id": str(uuid.uuid4()),
            "status": "in_progress",
            "progress_pct": 50,
            "answers": [
                {"question_code": "age", "value": 25},
                {"question_code": "gender", "value": "M"},
            ],
        }
        self.mock_survey_service.get_or_create_survey_response.return_value = (
            mock_response_data
        )
        self.mock_survey_service.get_survey_definition.return_value = (
            self.sample_survey_definition
        )

        # Make request
        response = self.client.get(
            "/api/survey-response?user_id=test-user-123&survey_code=test-survey"
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["status"] == "in_progress"
        assert data["progress_pct"] == 50
        assert len(data["answers"]) == 2
        assert data["last_question_id"] == "gender"

    @patch("healthcare.survey.routes.get_or_create_user")
    def test_get_survey_response_survey_not_found(self, mock_get_user):
        """Test survey response retrieval for non-existent survey."""
        self.override_dependencies()

        # Mock user creation
        mock_get_user.return_value = self.mock_user

        # Mock survey service response
        self.mock_survey_service.get_or_create_survey_response.return_value = None

        # Make request
        response = self.client.get(
            "/api/survey-response?user_id=test-user-123&survey_code=non-existent"
        )

        # Assertions
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["ok"] is False
        assert data["detail"]["error"]["code"] == "survey_not_found"

    @patch("healthcare.survey.routes.get_or_create_user")
    def test_save_survey_answer_success(self, mock_get_user):
        """Test successful survey answer saving."""
        self.override_dependencies()

        # Mock user creation
        mock_get_user.return_value = self.mock_user

        # Mock survey service response
        mock_result = {"ok": True, "progress_pct": 75, "response_id": str(uuid.uuid4())}
        self.mock_survey_service.save_survey_answer.return_value = mock_result

        # Test data
        answer_request = {"question_id": "age", "value": {"answer": 25}}

        # Make request
        response = self.client.post(
            "/api/survey-response/answer?user_id=test-user-123&survey_code=test-survey",
            json=answer_request,
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["progress_pct"] == 75

        # Verify service was called correctly
        self.mock_survey_service.save_survey_answer.assert_called_once_with(
            1, "test-survey", "age", {"answer": 25}
        )

    @patch("healthcare.survey.routes.get_or_create_user")
    def test_save_survey_answer_failed(self, mock_get_user):
        """Test failed survey answer saving."""
        self.override_dependencies()

        # Mock user creation
        mock_get_user.return_value = self.mock_user

        # Mock survey service response
        self.mock_survey_service.save_survey_answer.return_value = None

        # Test data
        answer_request = {"question_id": "age", "value": {"answer": 25}}

        # Make request
        response = self.client.post(
            "/api/survey-response/answer?user_id=test-user-123&survey_code=test-survey",
            json=answer_request,
        )

        # Assertions
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["ok"] is False
        assert data["detail"]["error"]["code"] == "save_failed"

    @patch("healthcare.survey.routes.get_or_create_user")
    def test_complete_survey_response_success(self, mock_get_user):
        """Test successful survey response completion."""
        self.override_dependencies()

        # Mock user creation
        mock_get_user.return_value = self.mock_user

        # Mock survey service response
        mock_result = {
            "ok": True,
            "response_id": str(uuid.uuid4()),
            "status": "completed",
            "derived_metrics": {"bmi": 22.5, "age": 25},
        }
        self.mock_survey_service.complete_survey_response.return_value = mock_result

        # Make request
        response = self.client.post(
            "/api/survey-response?user_id=test-user-123&survey_code=test-survey"
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["status"] == "completed"
        assert "derived_metrics" in data
        assert data["derived_metrics"]["bmi"] == 22.5

        # Verify service was called correctly
        self.mock_survey_service.complete_survey_response.assert_called_once_with(
            1, "test-survey"
        )

    @patch("healthcare.survey.routes.get_or_create_user")
    def test_complete_survey_response_failed(self, mock_get_user):
        """Test failed survey response completion."""
        self.override_dependencies()

        # Mock user creation
        mock_get_user.return_value = self.mock_user

        # Mock survey service response
        self.mock_survey_service.complete_survey_response.return_value = None

        # Make request
        response = self.client.post(
            "/api/survey-response?user_id=test-user-123&survey_code=test-survey"
        )

        # Assertions
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["ok"] is False
        assert data["detail"]["error"]["code"] == "completion_failed"

    def test_generate_survey_link_success(self):
        """Test successful survey link generation."""
        self.override_dependencies()

        # Mock survey service response
        mock_survey = Mock()
        mock_survey.id = str(uuid.uuid4())
        mock_survey.code = "test-survey"
        self.mock_survey_service.get_survey_by_code.return_value = mock_survey

        # Test data
        link_request = {"user_id": "test-user-123", "survey_code": "test-survey"}

        # Make request
        response = self.client.post("/api/survey-links", json=link_request)

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "survey_url" in data
        assert "test-user-123" in data["survey_url"]
        assert "test-survey" in data["survey_url"]
        assert data["user_id"] == "test-user-123"
        assert data["survey_code"] == "test-survey"

        # Verify service was called correctly
        self.mock_survey_service.get_survey_by_code.assert_called_once_with(
            "test-survey"
        )

    def test_generate_survey_link_survey_not_found(self):
        """Test survey link generation for non-existent survey."""
        self.override_dependencies()

        # Mock survey service response
        self.mock_survey_service.get_survey_by_code.return_value = None

        # Test data
        link_request = {"user_id": "test-user-123", "survey_code": "non-existent"}

        # Make request
        response = self.client.post("/api/survey-links", json=link_request)

        # Assertions
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["ok"] is False
        assert data["detail"]["error"]["code"] == "survey_not_found"

    def test_get_or_create_user_function_exists(self):
        """Test that get_or_create_user function exists and is importable."""
        from healthcare.survey.routes import get_or_create_user

        # Just verify the function exists
        assert callable(get_or_create_user)


class TestSurveyRoutesIntegration:
    """Integration tests for survey routes with real dependencies."""

    @pytest.fixture
    def app_with_state(self):
        """Create FastAPI app with mock state for integration testing."""
        app = FastAPI()
        app.include_router(router)

        # Mock app state
        app.state.config = Config(
            openai_api_key="test-key", base_data_dir=Path("test_data")
        )
        app.state.db_service = Mock()

        return app

    def test_dependency_injection_from_app_state(self, app_with_state):
        """Test that dependencies are correctly injected from app state."""
        client = TestClient(app_with_state)

        # Mock the database service to raise a specific error we can catch
        app_with_state.state.db_service.get_session.side_effect = Exception(
            "DB connection failed"
        )

        # Make a request that would use the database
        response = client.get("/api/survey-response?user_id=test&survey_code=test")

        # Should get a 500 error due to our mocked exception
        assert response.status_code == 500

    def test_error_handling_service_unavailable(self):
        """Test error handling when services are unavailable."""
        app = FastAPI()
        app.include_router(router)
        # Don't set app.state - this should trigger service unavailable

        client = TestClient(app)

        # Make request
        response = client.get("/api/survey-response?user_id=test&survey_code=test")

        # Should get service unavailable error
        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["ok"] is False
        assert data["detail"]["error"]["code"] == "service_unavailable"
