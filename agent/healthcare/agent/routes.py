"""FastAPI routes for AI agent endpoints."""

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from agent.healthcare.agent.service import HealthcareAgent
from agent.healthcare.config.config import Config, ConfigManager
from agent.healthcare.reports.service import ReportService
from agent.healthcare.search.search_service import SearchService
from agent.healthcare.storage.database import DatabaseService

logger = logging.getLogger(__name__)

# Create router for agent endpoints
router = APIRouter(prefix="/api/agent", tags=["agent"])


# Request/Response Models
class ChatRequest(BaseModel):
    """Request model for agent chat."""

    user_external_id: str = Field(..., min_length=1, description="External user ID")
    query: str = Field(..., min_length=1, description="User query or message")
    session_id: Optional[str] = Field(
        None, description="Optional session ID for conversation continuity"
    )


class ChatResponse(BaseModel):
    """Response model for agent chat."""

    response: str = Field(..., description="Agent's response to the query")
    user_external_id: str = Field(..., description="User external ID")
    session_id: str = Field(..., description="Session ID used for the conversation")
    query: str = Field(..., description="Original user query")


class ConversationHistoryResponse(BaseModel):
    """Response model for conversation history."""

    user_external_id: str = Field(..., description="User external ID")
    session_id: str = Field(..., description="Session ID")
    history: list = Field(..., description="List of conversation messages")
    total_messages: int = Field(..., description="Total number of messages in history")


class AgentStatsResponse(BaseModel):
    """Response model for agent statistics."""

    agent_name: str = Field(..., description="Name of the AI agent")
    model: str = Field(..., description="OpenAI model being used")
    embedding_model: str = Field(..., description="Embedding model for knowledge base")
    vector_db: str = Field(..., description="Vector database type")
    storage: str = Field(..., description="Storage type for conversations")
    knowledge_base: str = Field(..., description="Knowledge base collection name")
    toolkit_functions: list = Field(..., description="Available toolkit functions")


# Dependency injection functions
def get_config() -> Config:
    """Dependency to get configuration."""
    return ConfigManager.load_config()


def get_database_service(
    config: Annotated[Config, Depends(get_config)],
) -> DatabaseService:
    """Dependency to get database service."""
    return DatabaseService(config)


def get_search_service(
    config: Annotated[Config, Depends(get_config)],
    db_service: Annotated[DatabaseService, Depends(get_database_service)],
) -> SearchService:
    """Dependency to get search service."""
    try:
        from agent.healthcare.storage.embeddings import EmbeddingService

        embedding_service = EmbeddingService(config)
        return SearchService(config, db_service, embedding_service)
    except Exception as e:
        logger.error(f"Failed to initialize search service: {e}")
        raise HTTPException(status_code=503, detail="Search service not available")


def get_report_service(
    config: Annotated[Config, Depends(get_config)],
    db_service: Annotated[DatabaseService, Depends(get_database_service)],
) -> ReportService:
    """Dependency to get report service."""
    return ReportService(config, db_service)


def get_healthcare_agent(
    config: Annotated[Config, Depends(get_config)],
    db_service: Annotated[DatabaseService, Depends(get_database_service)],
    search_service: Annotated[SearchService, Depends(get_search_service)],
    report_service: Annotated[ReportService, Depends(get_report_service)],
) -> HealthcareAgent:
    """Dependency to get healthcare agent."""
    try:
        return HealthcareAgent(
            config=config,
            db_service=db_service,
            search_service=search_service,
            report_service=report_service,
        )
    except Exception as e:
        logger.error(f"Failed to initialize healthcare agent: {e}")
        raise HTTPException(status_code=503, detail="Healthcare agent not available")


# Error handling utility
def handle_agent_error(
    error: Exception, operation: str, user_id: str = None
) -> JSONResponse:
    """Handle agent errors with appropriate HTTP responses."""
    error_msg = str(error)

    if isinstance(error, ValueError):
        # Input validation errors
        logger.warning(
            f"Agent {operation} validation error for user {user_id}: {error_msg}"
        )
        return JSONResponse(
            status_code=400,
            content={
                "error": "validation_error",
                "message": error_msg,
                "operation": operation,
                "user_id": user_id,
            },
        )
    elif isinstance(error, RuntimeError):
        # Service/processing errors
        logger.error(f"Agent {operation} runtime error for user {user_id}: {error_msg}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "processing_error",
                "message": "An error occurred while processing your request",
                "operation": operation,
                "user_id": user_id,
            },
        )
    else:
        # Unexpected errors
        logger.error(
            f"Agent {operation} unexpected error for user {user_id}: {error_msg}",
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_error",
                "message": "An unexpected error occurred",
                "operation": operation,
                "user_id": user_id,
            },
        )


# API Endpoints
@router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(
    request: ChatRequest,
    agent: Annotated[HealthcareAgent, Depends(get_healthcare_agent)],
) -> JSONResponse:
    """Chat with the healthcare AI agent.

    Process a user query through the healthcare agent and return the response.
    The agent has access to the user's medical data and can search, analyze,
    and provide insights based on uploaded reports.
    """
    try:
        # Strip whitespace from inputs
        user_external_id = request.user_external_id.strip()
        query = request.query.strip()
        session_id = request.session_id.strip() if request.session_id else None

        # Process query through agent
        response = agent.process_query(
            user_external_id=user_external_id,
            query=query,
            session_id=session_id,
        )

        # Prepare response
        chat_response = ChatResponse(
            response=response,
            user_external_id=user_external_id,
            session_id=session_id or user_external_id,
            query=query,
        )

        logger.info(f"Agent chat completed for user {user_external_id}")
        return JSONResponse(status_code=200, content=chat_response.model_dump())

    except Exception as e:
        return handle_agent_error(e, "chat", request.user_external_id)


@router.get("/history/{user_external_id}", response_model=ConversationHistoryResponse)
async def get_conversation_history(
    user_external_id: str,
    session_id: Optional[str] = None,
    agent: Annotated[HealthcareAgent, Depends(get_healthcare_agent)] = None,
) -> JSONResponse:
    """Get conversation history for a user.

    Retrieve the conversation history for a specific user and optional session.
    If no session_id is provided, uses the user_external_id as the session.
    """
    try:
        # Strip whitespace
        user_external_id = user_external_id.strip()
        session_id = session_id.strip() if session_id else None

        # Get conversation history
        history = agent.get_conversation_history(
            user_external_id=user_external_id,
            session_id=session_id,
        )

        # Prepare response
        history_response = ConversationHistoryResponse(
            user_external_id=user_external_id,
            session_id=session_id or user_external_id,
            history=history,
            total_messages=len(history),
        )

        logger.info(
            f"Retrieved conversation history for user {user_external_id}: {len(history)} messages"
        )
        return JSONResponse(status_code=200, content=history_response.model_dump())

    except Exception as e:
        return handle_agent_error(e, "get_history", user_external_id)


@router.delete("/history/{user_external_id}")
async def clear_conversation_history(
    user_external_id: str,
    session_id: Optional[str] = None,
    agent: Annotated[HealthcareAgent, Depends(get_healthcare_agent)] = None,
) -> JSONResponse:
    """Clear conversation history for a user.

    Delete the conversation history for a specific user and optional session.
    If no session_id is provided, clears history for the user_external_id session.
    """
    try:
        # Strip whitespace
        user_external_id = user_external_id.strip()
        session_id = session_id.strip() if session_id else None

        # Clear conversation history
        success = agent.clear_conversation_history(
            user_external_id=user_external_id,
            session_id=session_id,
        )

        # Prepare response
        response_content = {
            "success": success,
            "user_external_id": user_external_id,
            "session_id": session_id or user_external_id,
            "message": (
                "Conversation history cleared" if success else "No history to clear"
            ),
        }

        logger.info(
            f"Cleared conversation history for user {user_external_id}: {success}"
        )
        return JSONResponse(status_code=200, content=response_content)

    except Exception as e:
        return handle_agent_error(e, "clear_history", user_external_id)


@router.get("/stats", response_model=AgentStatsResponse)
async def get_agent_stats(
    agent: Annotated[HealthcareAgent, Depends(get_healthcare_agent)],
) -> JSONResponse:
    """Get statistics and information about the healthcare agent.

    Returns information about the agent configuration, available tools,
    and system status for monitoring and debugging purposes.
    """
    try:
        # Get agent statistics
        stats = agent.get_agent_stats()

        # Handle error case
        if "error" in stats:
            logger.warning(f"Agent stats returned error: {stats['error']}")
            return JSONResponse(
                status_code=503,
                content={
                    "error": "stats_error",
                    "message": "Unable to retrieve complete agent statistics",
                    "details": stats,
                },
            )

        # Prepare successful response
        stats_response = AgentStatsResponse(**stats)

        logger.info("Agent stats retrieved successfully")
        return JSONResponse(status_code=200, content=stats_response.model_dump())

    except Exception as e:
        return handle_agent_error(e, "get_stats")


@router.get("/health")
async def agent_health_check() -> JSONResponse:
    """Health check endpoint for the agent service.

    Returns the health status of the agent service and its dependencies.
    This is a lightweight check that doesn't require full agent initialization.
    """
    try:
        # Basic health check - verify configuration can be loaded
        config = ConfigManager.load_config()

        health_status = {
            "status": "healthy",
            "service": "healthcare_agent",
            "timestamp": "2024-01-15T10:30:00Z",  # In production, use datetime.utcnow().isoformat()
            "config": {
                "openai_model": config.openai_model,
                "embedding_model": config.embedding_model,
                "data_dir_exists": config.base_data_dir.exists(),
            },
        }

        logger.info("Agent health check passed")
        return JSONResponse(status_code=200, content=health_status)

    except Exception as e:
        logger.error(f"Agent health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "healthcare_agent",
                "error": str(e),
                "timestamp": "2024-01-15T10:30:00Z",
            },
        )
