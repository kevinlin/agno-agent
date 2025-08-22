"""Survey management service for healthcare agent."""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import HTTPException
from sqlmodel import select

from healthcare.config.config import Config
from healthcare.storage.database import DatabaseService
from healthcare.storage.models import Survey, SurveyType, User

logger = logging.getLogger(__name__)


class SurveyService:
    """Service for managing surveys and survey definitions."""

    def __init__(self, config: Config, db_service: DatabaseService):
        """Initialize survey service.

        Args:
            config: Application configuration
            db_service: Database service instance
        """
        self.config = config
        self.db_service = db_service

    def create_survey(
        self,
        code: str,
        title: str,
        version: str,
        survey_type: SurveyType,
        definition: Dict,
        description: Optional[str] = None,
    ) -> Survey:
        """Create a new survey definition.

        Args:
            code: Unique survey code
            title: Survey title
            version: Survey version
            survey_type: Survey type enum
            definition: Survey definition JSON
            description: Optional description

        Returns:
            Created survey instance

        Raises:
            HTTPException: If survey creation fails or code already exists
        """
        try:
            with self.db_service.get_session() as session:
                # Check if survey code already exists
                statement = select(Survey).where(Survey.code == code)
                existing = session.exec(statement).first()
                if existing:
                    raise HTTPException(
                        status_code=409,
                        detail=f"Survey with code '{code}' already exists",
                    )

                # Validate survey definition structure
                self._validate_survey_definition(definition)

                # Create survey with UUID
                survey_id = str(uuid.uuid4())
                survey = Survey(
                    id=survey_id,
                    code=code,
                    title=title,
                    version=version,
                    type=survey_type,
                    description=description,
                    definition_json=json.dumps(definition, ensure_ascii=False),
                )

                session.add(survey)
                session.commit()
                session.refresh(survey)

                logger.info(f"Created survey: {code} (v{version})")
                return survey

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to create survey {code}: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to create survey: {str(e)}"
            )

    def get_survey_by_code(self, code: str) -> Optional[Survey]:
        """Get survey by code.

        Args:
            code: Survey code

        Returns:
            Survey instance if found, None otherwise
        """
        try:
            with self.db_service.get_session() as session:
                statement = select(Survey).where(Survey.code == code)
                survey = session.exec(statement).first()
                return survey
        except Exception as e:
            logger.error(f"Failed to get survey {code}: {e}")
            return None

    def get_survey_by_id(self, survey_id: str) -> Optional[Survey]:
        """Get survey by ID.

        Args:
            survey_id: Survey ID

        Returns:
            Survey instance if found, None otherwise
        """
        try:
            with self.db_service.get_session() as session:
                return session.get(Survey, survey_id)
        except Exception as e:
            logger.error(f"Failed to get survey {survey_id}: {e}")
            return None

    def list_surveys(self, survey_type: Optional[SurveyType] = None) -> List[Dict]:
        """List all surveys with basic information.

        Args:
            survey_type: Optional filter by survey type

        Returns:
            List of survey summaries
        """
        try:
            with self.db_service.get_session() as session:
                statement = select(Survey)
                if survey_type:
                    statement = statement.where(Survey.type == survey_type)

                surveys = session.exec(statement).all()

                return [
                    {
                        "id": survey.id,
                        "code": survey.code,
                        "title": survey.title,
                        "type": survey.type.value,
                        "version": survey.version,
                        "description": survey.description,
                        "created_at": survey.created_at.isoformat(),
                    }
                    for survey in surveys
                ]
        except Exception as e:
            logger.error(f"Failed to list surveys: {e}")
            return []

    def get_survey_definition(self, code: str) -> Optional[Dict]:
        """Get full survey definition by code.

        Args:
            code: Survey code

        Returns:
            Survey definition dictionary if found, None otherwise
        """
        survey = self.get_survey_by_code(code)
        if not survey:
            return None

        try:
            definition = json.loads(survey.definition_json)
            return definition
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse survey definition for {code}: {e}")
            return None

    def _validate_survey_definition(self, definition: Dict) -> None:
        """Validate survey definition structure.

        Args:
            definition: Survey definition to validate

        Raises:
            HTTPException: If validation fails
        """
        required_fields = ["code", "type", "version", "title", "questions"]

        for field in required_fields:
            if field not in definition:
                raise HTTPException(
                    status_code=400, detail=f"Missing required field: {field}"
                )

        # Validate survey type
        if definition["type"] not in [t.value for t in SurveyType]:
            raise HTTPException(
                status_code=400, detail=f"Invalid survey type: {definition['type']}"
            )

        # Validate questions array
        questions = definition.get("questions", [])
        if not isinstance(questions, list) or len(questions) == 0:
            raise HTTPException(
                status_code=400, detail="Survey must have at least one question"
            )

        # Validate each question
        for i, question in enumerate(questions):
            self._validate_question(question, i)

        # Validate branching rules if present
        if "branching_rules" in definition:
            self._validate_branching_rules(definition["branching_rules"], questions)

        logger.debug(f"Survey definition validation passed for {definition['code']}")

    def _validate_question(self, question: Dict, index: int) -> None:
        """Validate individual question structure.

        Args:
            question: Question dictionary to validate
            index: Question index for error messages

        Raises:
            HTTPException: If validation fails
        """
        required_fields = ["type", "code", "title"]

        for field in required_fields:
            if field not in question:
                raise HTTPException(
                    status_code=400,
                    detail=f"Question {index}: Missing required field '{field}'",
                )

        # Validate question type
        valid_types = ["INPUT", "SINGLE_SELECT", "MULTIPLE_SELECT", "DROPDOWN", "TIME"]
        if question["type"] not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Question {index}: Invalid question type '{question['type']}'",
            )

        # Validate INPUT questions have unit
        if question["type"] == "INPUT" and "unit" not in question:
            raise HTTPException(
                status_code=400,
                detail=f"Question {index}: INPUT questions must have 'unit' field",
            )

        # Validate select-type questions have answers
        select_types = ["SINGLE_SELECT", "MULTIPLE_SELECT", "DROPDOWN"]
        if question["type"] in select_types and "answers" not in question:
            raise HTTPException(
                status_code=400,
                detail=f"Question {index}: {question['type']} questions must have 'answers' field",
            )

    def _validate_branching_rules(
        self, rules: List[Dict], questions: List[Dict]
    ) -> None:
        """Validate branching rules structure.

        Args:
            rules: List of branching rules to validate
            questions: List of questions for reference validation

        Raises:
            HTTPException: If validation fails
        """
        if not isinstance(rules, list):
            raise HTTPException(
                status_code=400, detail="branching_rules must be an array"
            )

        question_codes = {q["code"] for q in questions}

        for i, rule in enumerate(rules):
            if not isinstance(rule, dict):
                raise HTTPException(
                    status_code=400, detail=f"Branching rule {i}: Must be an object"
                )

            # Validate required fields
            required_fields = ["id", "condition", "action"]
            for field in required_fields:
                if field not in rule:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Branching rule {i}: Missing required field '{field}'",
                    )

            # Validate condition references valid questions
            condition = rule["condition"]
            if "question_code" in condition:
                if condition["question_code"] not in question_codes:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Branching rule {i}: References unknown question '{condition['question_code']}'",
                    )

    def load_survey_from_file(self, file_path: Path) -> Survey:
        """Load survey definition from JSON file.

        Args:
            file_path: Path to survey JSON file

        Returns:
            Created survey instance

        Raises:
            HTTPException: If file loading or survey creation fails
        """
        try:
            if not file_path.exists():
                raise HTTPException(
                    status_code=404, detail=f"Survey file not found: {file_path}"
                )

            with open(file_path, "r", encoding="utf-8") as f:
                definition = json.load(f)

            # Extract survey metadata from definition
            code = definition.get("code")
            title = definition.get("title")
            version = definition.get("version")
            survey_type = SurveyType(definition.get("type"))
            description = definition.get("description")

            return self.create_survey(
                code=code,
                title=title,
                version=version,
                survey_type=survey_type,
                definition=definition,
                description=description,
            )

        except HTTPException:
            # Re-raise HTTPExceptions without wrapping
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in survey file {file_path}: {e}")
            raise HTTPException(
                status_code=400, detail=f"Invalid JSON in survey file: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Failed to load survey from file {file_path}: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to load survey: {str(e)}"
            )
