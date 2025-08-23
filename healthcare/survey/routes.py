"""FastAPI routes for survey endpoints."""

import json
import logging
from typing import Annotated, Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from healthcare.config.config import Config
from healthcare.storage.database import DatabaseService
from healthcare.storage.models import SurveyType, User
from healthcare.survey.survey_service import SurveyService

logger = logging.getLogger(__name__)

# Create router for survey endpoints
router = APIRouter(prefix="/api", tags=["survey"])


# Request/Response Models
class SurveyCreateRequest(BaseModel):
    """Request model for creating a new survey."""

    code: str = Field(..., min_length=1, description="Unique survey code")
    title: str = Field(..., min_length=1, description="Survey title")
    version: str = Field(..., min_length=1, description="Survey version")
    type: str = Field(
        ..., description="Survey type: PERSONALIZATION, DISEASE_RISK, LIFE_STYLE"
    )
    description: Optional[str] = Field(None, description="Optional survey description")
    definition: Dict = Field(..., description="Survey definition JSON")


class SurveyCatalogItem(BaseModel):
    """Response model for survey catalog item."""

    id: str = Field(..., description="Survey ID")
    code: str = Field(..., description="Survey code")
    title: str = Field(..., description="Survey title")
    type: str = Field(..., description="Survey type")
    active_version: str = Field(..., description="Active version")


class SurveyResponse(BaseModel):
    """Response model for survey operations."""

    ok: bool = Field(..., description="Operation success status")
    survey_id: Optional[str] = Field(None, description="Survey ID if created")
    message: Optional[str] = Field(None, description="Success message")


class SurveyResponseStatus(BaseModel):
    """Response model for survey response status."""

    ok: bool = Field(..., description="Operation success status")
    status: str = Field(
        ..., description="Response status: in_progress, completed, cancelled"
    )
    progress_pct: int = Field(..., description="Progress percentage (0-100)")
    last_question_id: Optional[str] = Field(
        None, description="Last answered question ID"
    )
    answers: List[Dict] = Field(..., description="List of question answers")


class SaveAnswerRequest(BaseModel):
    """Request model for saving survey answer."""

    question_id: str = Field(..., min_length=1, description="Question ID/code")
    value: Union[Dict, List, str, int, float, bool] = Field(..., description="Answer value - can be dict, list, string, number, or boolean depending on question type")


class SaveAnswerResponse(BaseModel):
    """Response model for saving survey answer."""

    ok: bool = Field(..., description="Operation success status")
    progress_pct: int = Field(..., description="Updated progress percentage")


class SurveyLinkRequest(BaseModel):
    """Request model for generating survey links."""

    user_id: str = Field(..., min_length=1, description="External user ID")
    survey_code: str = Field(..., min_length=1, description="Survey code")


class SurveyLinkResponse(BaseModel):
    """Response model for survey link generation."""

    ok: bool = Field(..., description="Operation success status")
    survey_url: str = Field(..., description="Generated survey URL")
    user_id: str = Field(..., description="User ID")
    survey_code: str = Field(..., description="Survey code")


class ErrorResponse(BaseModel):
    """Standard error response model."""

    ok: bool = Field(default=False, description="Always false for errors")
    error: Dict = Field(
        ..., description="Error details with code, message, and details"
    )


# Dependency injection functions
def get_config() -> Config:
    """Dependency to get configuration from app state."""
    # This will be replaced with proper dependency injection from app state
    from healthcare.config.config import ConfigManager

    return ConfigManager.load_config()


def get_database_service(request: Request) -> DatabaseService:
    """Dependency to get database service from app state."""
    if hasattr(request.app.state, "db_service") and request.app.state.db_service:
        return request.app.state.db_service
    raise HTTPException(
        status_code=503,
        detail={
            "ok": False,
            "error": {
                "code": "service_unavailable",
                "message": "Database service not available",
            },
        },
    )


def get_survey_service(
    request: Request,
    db_service: Annotated[DatabaseService, Depends(get_database_service)],
) -> SurveyService:
    """Dependency to get survey service."""
    if hasattr(request.app.state, "config") and request.app.state.config:
        config = request.app.state.config
    else:
        config = get_config()
    return SurveyService(config, db_service)


def get_or_create_user(db_service: DatabaseService, external_id: str) -> User:
    """Get or create user by external ID."""
    try:
        with db_service.get_session() as session:
            from sqlmodel import select

            statement = select(User).where(User.external_id == external_id)
            user = session.exec(statement).first()

            if not user:
                # Create new user
                user = User(external_id=external_id)
                session.add(user)
                session.commit()
                session.refresh(user)
                logger.info(f"Created new user with external_id: {external_id}")

            return user
    except Exception as e:
        logger.error(f"Failed to get/create user {external_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "ok": False,
                "error": {
                    "code": "user_error",
                    "message": "Failed to get or create user",
                },
            },
        )


# Survey Catalog Endpoints
@router.post("/survey", response_model=SurveyResponse)
async def create_survey(
    request: SurveyCreateRequest,
    survey_service: Annotated[SurveyService, Depends(get_survey_service)],
):
    """Create a new survey definition."""
    try:
        # Validate survey type
        try:
            survey_type = SurveyType(request.type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail={
                    "ok": False,
                    "error": {
                        "code": "invalid_survey_type",
                        "message": f"Invalid survey type: {request.type}",
                        "details": "Valid types: PERSONALIZATION, DISEASE_RISK, LIFE_STYLE",
                    },
                },
            )

        # Create survey
        survey = survey_service.create_survey(
            code=request.code,
            title=request.title,
            version=request.version,
            survey_type=survey_type,
            definition=request.definition,
            description=request.description,
        )

        return SurveyResponse(
            ok=True,
            survey_id=survey.id,
            message=f"Survey '{request.code}' created successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create survey: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "ok": False,
                "error": {
                    "code": "creation_failed",
                    "message": "Failed to create survey",
                    "details": str(e),
                },
            },
        )


@router.get("/survey", response_model=List[SurveyCatalogItem])
async def list_surveys(
    survey_service: Annotated[SurveyService, Depends(get_survey_service)],
    type: Optional[str] = Query(None, description="Filter by survey type"),
):
    """List all surveys with basic information."""
    try:
        # Validate type filter if provided
        survey_type = None
        if type:
            try:
                survey_type = SurveyType(type)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "ok": False,
                        "error": {
                            "code": "invalid_survey_type",
                            "message": f"Invalid survey type filter: {type}",
                            "details": "Valid types: PERSONALIZATION, DISEASE_RISK, LIFE_STYLE",
                        },
                    },
                )

        surveys = survey_service.list_surveys(survey_type)

        return [
            SurveyCatalogItem(
                id=survey["id"],
                code=survey["code"],
                title=survey["title"],
                type=survey["type"],
                active_version=survey["version"],
            )
            for survey in surveys
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list surveys: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "ok": False,
                "error": {
                    "code": "listing_failed",
                    "message": "Failed to list surveys",
                    "details": str(e),
                },
            },
        )


@router.get("/survey/{code}")
async def get_survey_definition(
    code: str,
    survey_service: Annotated[SurveyService, Depends(get_survey_service)],
):
    """Get full survey definition by code."""
    try:
        definition = survey_service.get_survey_definition(code)

        if not definition:
            raise HTTPException(
                status_code=404,
                detail={
                    "ok": False,
                    "error": {
                        "code": "survey_not_found",
                        "message": f"Survey with code '{code}' not found",
                        "details": "The requested survey does not exist",
                    },
                },
            )

        return definition

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get survey definition for {code}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "ok": False,
                "error": {
                    "code": "retrieval_failed",
                    "message": "Failed to retrieve survey definition",
                    "details": str(e),
                },
            },
        )


# Survey Response Management Endpoints
@router.get("/survey-response", response_model=SurveyResponseStatus)
async def get_survey_response(
    user_id: str = Query(..., description="External user ID"),
    survey_code: str = Query(..., description="Survey code"),
    survey_service: Annotated[SurveyService, Depends(get_survey_service)] = ...,
    db_service: Annotated[DatabaseService, Depends(get_database_service)] = ...,
):
    """Get existing survey response with status and answers."""
    try:
        # Get or create user
        user = get_or_create_user(db_service, user_id)

        # Get or create survey response
        response_data = survey_service.get_or_create_survey_response(
            user.id, survey_code
        )

        if not response_data:
            raise HTTPException(
                status_code=404,
                detail={
                    "ok": False,
                    "error": {
                        "code": "survey_not_found",
                        "message": f"Survey '{survey_code}' not found",
                        "details": "The requested survey does not exist",
                    },
                },
            )

        # Format answers for response
        formatted_answers = []
        for answer in response_data.get("answers", []):
            # Get question title from survey definition
            survey_def = survey_service.get_survey_definition(survey_code)
            question_title = answer["question_code"]  # Default to code

            if survey_def and "questions" in survey_def:
                for q in survey_def["questions"]:
                    if q.get("code") == answer["question_code"]:
                        question_title = q.get("title", answer["question_code"])
                        break

            formatted_answers.append(
                {
                    "question_id": answer["question_code"],
                    "title": question_title,
                    "value": answer["value"],
                }
            )

        # Get last question ID (most recent answer)
        last_question_id = None
        if formatted_answers:
            last_question_id = formatted_answers[-1]["question_id"]

        return SurveyResponseStatus(
            ok=True,
            status=response_data["status"],
            progress_pct=response_data["progress_pct"],
            last_question_id=last_question_id,
            answers=formatted_answers,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to get survey response for user {user_id}, survey {survey_code}: {e}"
        )
        raise HTTPException(
            status_code=500,
            detail={
                "ok": False,
                "error": {
                    "code": "response_retrieval_failed",
                    "message": "Failed to retrieve survey response",
                    "details": str(e),
                },
            },
        )


@router.post("/survey-response/answer", response_model=SaveAnswerResponse)
async def save_survey_answer(
    user_id: str = Query(..., description="External user ID"),
    survey_code: str = Query(..., description="Survey code"),
    request: SaveAnswerRequest = ...,
    survey_service: Annotated[SurveyService, Depends(get_survey_service)] = ...,
    db_service: Annotated[DatabaseService, Depends(get_database_service)] = ...,
):
    """Save an individual survey answer."""
    try:
        # Get or create user
        user = get_or_create_user(db_service, user_id)

        # Save answer
        result = survey_service.save_survey_answer(
            user.id, survey_code, request.question_id, request.value
        )

        if not result:
            raise HTTPException(
                status_code=404,
                detail={
                    "ok": False,
                    "error": {
                        "code": "save_failed",
                        "message": "Failed to save answer",
                        "details": "Survey or response not found",
                    },
                },
            )

        return SaveAnswerResponse(ok=result["ok"], progress_pct=result["progress_pct"])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to save answer for user {user_id}, survey {survey_code}: {e}"
        )
        raise HTTPException(
            status_code=500,
            detail={
                "ok": False,
                "error": {
                    "code": "answer_save_failed",
                    "message": "Failed to save survey answer",
                    "details": str(e),
                },
            },
        )


@router.post("/survey-response", response_model=Dict)
async def complete_survey_response(
    user_id: str = Query(..., description="External user ID"),
    survey_code: str = Query(..., description="Survey code"),
    survey_service: Annotated[SurveyService, Depends(get_survey_service)] = ...,
    db_service: Annotated[DatabaseService, Depends(get_database_service)] = ...,
):
    """Complete a survey response and calculate derived metrics."""
    try:
        # Get or create user
        user = get_or_create_user(db_service, user_id)

        # Complete survey
        result = survey_service.complete_survey_response(user.id, survey_code)

        if not result:
            raise HTTPException(
                status_code=404,
                detail={
                    "ok": False,
                    "error": {
                        "code": "completion_failed",
                        "message": "Failed to complete survey",
                        "details": "Survey or response not found",
                    },
                },
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to complete survey for user {user_id}, survey {survey_code}: {e}"
        )
        raise HTTPException(
            status_code=500,
            detail={
                "ok": False,
                "error": {
                    "code": "completion_failed",
                    "message": "Failed to complete survey response",
                    "details": str(e),
                },
            },
        )


# Agent Integration Endpoints
@router.post("/survey-links", response_model=SurveyLinkResponse)
async def generate_survey_link(
    request: SurveyLinkRequest,
    survey_service: Annotated[SurveyService, Depends(get_survey_service)],
):
    """Generate signed survey URLs for agent integration."""
    try:
        # Validate survey exists
        survey = survey_service.get_survey_by_code(request.survey_code)
        if not survey:
            raise HTTPException(
                status_code=404,
                detail={
                    "ok": False,
                    "error": {
                        "code": "survey_not_found",
                        "message": f"Survey '{request.survey_code}' not found",
                        "details": "The requested survey does not exist",
                    },
                },
            )

        # Generate survey URL (for now, simple URL construction)
        # In production, this might include signed tokens or other security measures
        base_url = "http://localhost:3000"  # This should come from config
        survey_url = (
            f"{base_url}/survey/{request.survey_code}?user_id={request.user_id}"
        )

        return SurveyLinkResponse(
            ok=True,
            survey_url=survey_url,
            user_id=request.user_id,
            survey_code=request.survey_code,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to generate survey link for {request.user_id}, {request.survey_code}: {e}"
        )
        raise HTTPException(
            status_code=500,
            detail={
                "ok": False,
                "error": {
                    "code": "link_generation_failed",
                    "message": "Failed to generate survey link",
                    "details": str(e),
                },
            },
        )
