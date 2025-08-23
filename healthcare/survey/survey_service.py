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
from healthcare.storage.models import (
    Survey,
    SurveyResponse,
    SurveyResponseStatus,
    SurveyResult,
    SurveyType,
    User,
)

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

    # Survey Response Management Methods

    def get_or_create_survey_response(
        self, user_id: int, survey_code: str
    ) -> Optional[Dict]:
        """Get existing survey response or create new one.

        Args:
            user_id: User ID
            survey_code: Survey code

        Returns:
            Response data with status, progress, and answers, or None if survey not found
        """
        try:
            with self.db_service.get_session() as session:
                # Get survey by code
                survey_statement = select(Survey).where(Survey.code == survey_code)
                survey = session.exec(survey_statement).first()
                if not survey:
                    logger.warning(f"Survey not found: {survey_code}")
                    return None

                # Look for existing response
                response_statement = (
                    select(SurveyResponse)
                    .where(SurveyResponse.user_id == user_id)
                    .where(SurveyResponse.survey_id == survey.id)
                )
                response = session.exec(response_statement).first()

                if response:
                    # Parse user_response JSON data
                    user_response_data = {}
                    if response.user_response:
                        try:
                            user_response_data = json.loads(response.user_response)
                        except json.JSONDecodeError:
                            logger.warning(
                                f"Invalid JSON in user_response for response {response.id}"
                            )
                            user_response_data = {}

                    return {
                        "id": response.id,
                        "status": response.status.value,
                        "progress_pct": response.progress_pct,
                        "user_response": user_response_data,
                        "created_at": response.created_at.isoformat(),
                        "updated_at": response.updated_at.isoformat(),
                    }
                else:
                    # Create new response
                    response_id = str(uuid.uuid4())
                    new_response = SurveyResponse(
                        id=response_id,
                        survey_id=survey.id,
                        user_id=user_id,
                        status=SurveyResponseStatus.IN_PROGRESS,
                        progress_pct=0,
                    )

                    session.add(new_response)
                    session.commit()
                    session.refresh(new_response)

                    logger.info(
                        f"Created new survey response: {response_id} for user {user_id}"
                    )
                    return {
                        "id": new_response.id,
                        "status": new_response.status.value,
                        "progress_pct": new_response.progress_pct,
                        "user_response": {},
                        "created_at": new_response.created_at.isoformat(),
                        "updated_at": new_response.updated_at.isoformat(),
                    }

        except Exception as e:
            logger.error(
                f"Failed to get/create survey response for user {user_id}, survey {survey_code}: {e}"
            )
            return None

    def save_survey_response(
        self,
        user_id: int,
        survey_code: str,
        user_response: Dict,
        status: Optional[SurveyResponseStatus] = None,
    ) -> Optional[Dict]:
        """Save complete survey response with user_response JSON field.

        Args:
            user_id: User ID
            survey_code: Survey code
            user_response: Complete answer data as dict (e.g., {"height_cm": "173", "smoke_status": "never"})
            status: Optional status override (defaults to in_progress, or completed if all questions answered)

        Returns:
            Updated response data with progress, or None if failed
        """
        try:
            with self.db_service.get_session() as session:
                # Get survey by code
                survey_statement = select(Survey).where(Survey.code == survey_code)
                survey = session.exec(survey_statement).first()
                if not survey:
                    logger.warning(f"Survey not found: {survey_code}")
                    return None

                # Get or create survey response
                response_statement = (
                    select(SurveyResponse)
                    .where(SurveyResponse.user_id == user_id)
                    .where(SurveyResponse.survey_id == survey.id)
                )
                response = session.exec(response_statement).first()

                if not response:
                    # Create new response
                    response = SurveyResponse(
                        id=str(uuid.uuid4()),
                        survey_id=survey.id,
                        user_id=user_id,
                        status=status or SurveyResponseStatus.IN_PROGRESS,
                        user_response=json.dumps(user_response, ensure_ascii=False),
                    )
                else:
                    # Update existing response
                    response.user_response = json.dumps(
                        user_response, ensure_ascii=False
                    )
                    response.updated_at = datetime.now()
                    if status:
                        response.status = status

                # Calculate progress based on answered questions
                progress_pct = self._calculate_progress_from_user_response(
                    survey.id, user_response
                )
                response.progress_pct = progress_pct

                session.add(response)
                session.commit()

                logger.info(
                    f"Saved survey response for user {user_id}, survey {survey_code} with {len(user_response)} answers"
                )
                return {
                    "ok": True,
                    "progress_pct": progress_pct,
                    "response_id": response.id,
                    "status": response.status,
                }

        except Exception as e:
            logger.error(
                f"Failed to save survey response for user {user_id}, survey {survey_code}: {e}"
            )
            return None

    def complete_survey_response(
        self, user_id: int, survey_code: str, derived_metrics: Optional[Dict] = None
    ) -> Optional[Dict]:
        """Complete a survey response and calculate derived metrics.

        Args:
            user_id: User ID
            survey_code: Survey code
            derived_metrics: Optional derived metrics (BMI, etc.)

        Returns:
            Completion result with metrics, or None if failed
        """
        try:
            with self.db_service.get_session() as session:
                # Get survey by code
                survey_statement = select(Survey).where(Survey.code == survey_code)
                survey = session.exec(survey_statement).first()
                if not survey:
                    logger.warning(f"Survey not found: {survey_code}")
                    return None

                # Get survey response
                response_statement = (
                    select(SurveyResponse)
                    .where(SurveyResponse.user_id == user_id)
                    .where(SurveyResponse.survey_id == survey.id)
                )
                response = session.exec(response_statement).first()
                if not response:
                    logger.warning(
                        f"Survey response not found for user {user_id}, survey {survey_code}"
                    )
                    return None

                # Update response status to completed
                response.status = SurveyResponseStatus.COMPLETED
                response.progress_pct = 100
                response.updated_at = datetime.now()
                session.add(response)

                # Calculate derived metrics if not provided
                if derived_metrics is None:
                    derived_metrics = self._calculate_derived_metrics(
                        session, response.id, survey_code
                    )

                # Save survey results
                if derived_metrics:
                    # Check if result already exists
                    result_statement = select(SurveyResult).where(
                        SurveyResult.response_id == response.id
                    )
                    existing_result = session.exec(result_statement).first()

                    result_json = json.dumps(derived_metrics, ensure_ascii=False)

                    if existing_result:
                        existing_result.result_json = result_json
                        session.add(existing_result)
                    else:
                        new_result = SurveyResult(
                            response_id=response.id, result_json=result_json
                        )
                        session.add(new_result)

                session.commit()

                logger.info(
                    f"Completed survey response {response.id} for user {user_id}"
                )
                return {
                    "ok": True,
                    "response_id": response.id,
                    "status": "completed",
                    "derived_metrics": derived_metrics,
                }

        except Exception as e:
            logger.error(
                f"Failed to complete survey response for user {user_id}, survey {survey_code}: {e}"
            )
            return None

    def _calculate_progress(self, session, response_id: str, survey_id: str) -> int:
        """Calculate progress percentage based on answered questions.

        Args:
            session: Database session
            response_id: Survey response ID
            survey_id: Survey ID

        Returns:
            Progress percentage (0-100)
        """
        try:
            # Get total questions in survey
            survey = session.get(Survey, survey_id)
            if not survey:
                return 0

            definition = json.loads(survey.definition_json)
            total_questions = len(definition.get("questions", []))

            if total_questions == 0:
                return 0

            # Get response to access user_response
            response = session.get(SurveyResponse, response_id)
            if not response or not response.user_response:
                return 0

            # Count answered questions from user_response JSON
            try:
                user_response_data = json.loads(response.user_response)
                answered_count = len(
                    [
                        v
                        for v in user_response_data.values()
                        if v is not None and v != ""
                    ]
                )
            except json.JSONDecodeError:
                return 0

            # Calculate percentage
            progress = min(100, int((answered_count / total_questions) * 100))
            return progress

        except Exception as e:
            logger.error(
                f"Failed to calculate progress for response {response_id}: {e}"
            )
            return 0

    def _calculate_progress_from_user_response(
        self, survey_id: str, user_response: Dict
    ) -> int:
        """Calculate progress percentage based on user_response JSON data.

        Args:
            survey_id: Survey ID
            user_response: User response data as dict

        Returns:
            Progress percentage (0-100)
        """
        try:
            with self.db_service.get_session() as session:
                # Get total questions in survey
                survey = session.get(Survey, survey_id)
                if not survey:
                    return 0

                definition = json.loads(survey.definition_json)
                total_questions = len(definition.get("questions", []))

                if total_questions == 0:
                    return 0

                # Count answered questions from user_response
                answered_count = len(
                    [v for v in user_response.values() if v is not None and v != ""]
                )

                # Calculate percentage
                progress = min(100, int((answered_count / total_questions) * 100))
                return progress

        except Exception as e:
            logger.error(
                f"Failed to calculate progress from user_response for survey {survey_id}: {e}"
            )
            return 0

    def _calculate_derived_metrics(
        self, session, response_id: str, survey_code: str
    ) -> Dict:
        """Calculate derived metrics based on survey answers.

        Args:
            session: Database session
            response_id: Survey response ID
            survey_code: Survey code

        Returns:
            Dictionary of derived metrics
        """
        try:
            # Get survey response to access user_response JSON field
            response = session.get(SurveyResponse, response_id)
            if not response or not response.user_response:
                return {}

            # Parse user_response JSON
            try:
                answer_dict = json.loads(response.user_response)
            except json.JSONDecodeError:
                logger.warning(
                    f"Invalid JSON in user_response for response {response_id}"
                )
                return {}

            metrics = {}

            # Calculate BMI if height and weight are available (check multiple possible field names)
            height_value = None
            weight_value = None

            # Check for height in different possible field names
            for height_key in ["height", "height_cm", "height_in"]:
                if height_key in answer_dict:
                    height_value = answer_dict[height_key]
                    break

            # Check for weight in different possible field names
            for weight_key in ["weight", "weight_kg", "weight_lbs"]:
                if weight_key in answer_dict:
                    weight_value = answer_dict[weight_key]
                    break

            if height_value is not None and weight_value is not None:
                try:
                    height_m = float(height_value) / 100  # Convert cm to m
                    weight_kg = float(weight_value)
                    bmi = weight_kg / (height_m**2)
                    metrics["bmi"] = round(bmi, 2)

                    # BMI categories
                    if bmi < 18.5:
                        metrics["bmi_category"] = "underweight"
                    elif bmi < 25:
                        metrics["bmi_category"] = "normal"
                    elif bmi < 30:
                        metrics["bmi_category"] = "overweight"
                    else:
                        metrics["bmi_category"] = "obese"

                except (ValueError, ZeroDivisionError):
                    pass

            # Calculate age if birth_year is available
            if "birth_year" in answer_dict:
                try:
                    birth_year = int(answer_dict["birth_year"])
                    current_year = datetime.now().year
                    metrics["age"] = current_year - birth_year
                except ValueError:
                    pass

            # Add survey-specific metrics based on survey code
            if survey_code == "personalization-survey":
                metrics["survey_type"] = "personalization"
                metrics["completion_date"] = datetime.now().isoformat()

            return metrics

        except Exception as e:
            logger.error(
                f"Failed to calculate derived metrics for response {response_id}: {e}"
            )
            return {}
