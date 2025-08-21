"""Simplified unit tests for agent API routes."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent.healthcare.agent.routes import router
from agent.healthcare.config.config import Config


class TestAgentRoutesSimple:
    """Simplified test suite for agent API routes using dependency overrides."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create test FastAPI app with agent router
        self.app = FastAPI()
        self.app.include_router(router)
        self.client = TestClient(self.app)

        # Mock configuration
        self.mock_config = Config(
            openai_api_key="test-key",
            openai_model="gpt-4o-mini",
            embedding_model="text-embedding-3-large",
            base_data_dir=Path("test_data"),
        )

        # Create mock agent for tests
        self.mock_agent = Mock()

    def override_dependencies(self):
        """Override FastAPI dependencies with mocks."""
        from agent.healthcare.agent.routes import get_healthcare_agent

        def mock_get_healthcare_agent():
            return self.mock_agent

        self.app.dependency_overrides[get_healthcare_agent] = mock_get_healthcare_agent

    def teardown_method(self):
        """Clean up after each test."""
        # Clear dependency overrides
        self.app.dependency_overrides.clear()

    def test_chat_with_agent_success(self):
        """Test successful chat with agent."""
        # Configure mock agent
        self.mock_agent.process_query.return_value = (
            "This is the agent's response to your query."
        )

        # Override dependencies
        self.override_dependencies()

        # Test request
        request_data = {
            "user_external_id": "user123",
            "query": "What is my blood pressure?",
            "session_id": "session456",
        }

        response = self.client.post("/api/agent/chat", json=request_data)

        # Verify response
        assert response.status_code == 200
        response_data = response.json()

        assert (
            response_data["response"] == "This is the agent's response to your query."
        )
        assert response_data["user_external_id"] == "user123"
        assert response_data["session_id"] == "session456"
        assert response_data["query"] == "What is my blood pressure?"

        # Verify agent was called correctly
        self.mock_agent.process_query.assert_called_once_with(
            user_external_id="user123",
            query="What is my blood pressure?",
            session_id="session456",
        )

    def test_chat_with_agent_no_session_id(self):
        """Test chat with agent without session ID."""
        # Configure mock agent
        self.mock_agent.process_query.return_value = "Response without session ID."

        # Override dependencies
        self.override_dependencies()

        # Test request without session_id
        request_data = {"user_external_id": "user123", "query": "Test query"}

        response = self.client.post("/api/agent/chat", json=request_data)

        # Verify response
        assert response.status_code == 200
        response_data = response.json()

        assert (
            response_data["session_id"] == "user123"
        )  # Should default to user_external_id

        # Verify agent was called with None session_id
        self.mock_agent.process_query.assert_called_once_with(
            user_external_id="user123",
            query="Test query",
            session_id=None,
        )

    def test_chat_with_agent_validation_error(self):
        """Test chat with agent validation error."""
        # Configure mock agent to raise ValueError
        self.mock_agent.process_query.side_effect = ValueError(
            "User external ID is required"
        )

        # Override dependencies
        self.override_dependencies()

        request_data = {"user_external_id": "user123", "query": "Test query"}

        response = self.client.post("/api/agent/chat", json=request_data)

        # Verify error response
        assert response.status_code == 400
        response_data = response.json()

        assert response_data["error"] == "validation_error"
        assert "User external ID is required" in response_data["message"]
        assert response_data["operation"] == "chat"
        assert response_data["user_id"] == "user123"

    def test_chat_with_agent_runtime_error(self):
        """Test chat with agent runtime error."""
        # Configure mock agent to raise RuntimeError
        self.mock_agent.process_query.side_effect = RuntimeError(
            "Agent processing failed"
        )

        # Override dependencies
        self.override_dependencies()

        request_data = {"user_external_id": "user123", "query": "Test query"}

        response = self.client.post("/api/agent/chat", json=request_data)

        # Verify error response
        assert response.status_code == 500
        response_data = response.json()

        assert response_data["error"] == "processing_error"
        assert (
            response_data["message"]
            == "An error occurred while processing your request"
        )
        assert response_data["operation"] == "chat"

    def test_get_conversation_history_success(self):
        """Test successful conversation history retrieval."""
        # Configure mock agent
        mock_history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        self.mock_agent.get_conversation_history.return_value = mock_history

        # Override dependencies
        self.override_dependencies()

        response = self.client.get("/api/agent/history/user123?session_id=session456")

        # Verify response
        assert response.status_code == 200
        response_data = response.json()

        assert response_data["user_external_id"] == "user123"
        assert response_data["session_id"] == "session456"
        assert response_data["history"] == mock_history
        assert response_data["total_messages"] == 2

        # Verify agent was called correctly
        self.mock_agent.get_conversation_history.assert_called_once_with(
            user_external_id="user123",
            session_id="session456",
        )

    def test_clear_conversation_history_success(self):
        """Test successful conversation history clearing."""
        # Configure mock agent
        self.mock_agent.clear_conversation_history.return_value = True

        # Override dependencies
        self.override_dependencies()

        response = self.client.delete(
            "/api/agent/history/user123?session_id=session456"
        )

        # Verify response
        assert response.status_code == 200
        response_data = response.json()

        assert response_data["success"] is True
        assert response_data["user_external_id"] == "user123"
        assert response_data["session_id"] == "session456"
        assert "cleared" in response_data["message"]

        # Verify agent was called correctly
        self.mock_agent.clear_conversation_history.assert_called_once_with(
            user_external_id="user123",
            session_id="session456",
        )

    def test_get_agent_config_success(self):
        """Test successful agent config retrieval."""
        # Configure mock agent
        mock_config = {
            "agent_name": "Healthcare Assistant",
            "model": "gpt-4o-mini",
            "embedding_model": "text-embedding-3-large",
            "vector_db": "ChromaDB",
            "storage": "SQLite",
            "knowledge_base": "medical_reports",
            "toolkit_functions": ["ingest_pdf", "list_reports", "search_medical_data"],
        }
        self.mock_agent.get_agent_stats.return_value = mock_config

        # Override dependencies
        self.override_dependencies()

        response = self.client.get("/api/agent/config")

        # Verify response
        assert response.status_code == 200
        response_data = response.json()

        assert response_data["agent_name"] == "Healthcare Assistant"
        assert response_data["model"] == "gpt-4o-mini"
        assert response_data["embedding_model"] == "text-embedding-3-large"
        assert response_data["vector_db"] == "ChromaDB"
        assert response_data["storage"] == "SQLite"
        assert response_data["knowledge_base"] == "medical_reports"
        assert len(response_data["toolkit_functions"]) == 3

    def test_get_agent_config_error(self):
        """Test agent config retrieval with error."""
        # Configure mock agent to return error config
        mock_config = {"error": "Agent not initialized"}
        self.mock_agent.get_agent_stats.return_value = mock_config

        # Override dependencies
        self.override_dependencies()

        response = self.client.get("/api/agent/config")

        # Verify error response
        assert response.status_code == 503
        response_data = response.json()

        assert response_data["error"] == "config_error"
        assert (
            "Unable to retrieve complete agent configuration" in response_data["message"]
        )

    def test_chat_with_agent_invalid_request(self):
        """Test chat with invalid request data."""
        # Test missing user_external_id
        request_data = {"query": "Test query"}

        response = self.client.post("/api/agent/chat", json=request_data)
        assert response.status_code == 422  # Validation error

        # Test empty user_external_id
        request_data = {"user_external_id": "", "query": "Test query"}

        response = self.client.post("/api/agent/chat", json=request_data)
        assert response.status_code == 422  # Validation error

        # Test missing query
        request_data = {"user_external_id": "user123"}

        response = self.client.post("/api/agent/chat", json=request_data)
        assert response.status_code == 422  # Validation error

    def test_input_whitespace_stripping(self):
        """Test that input whitespace is properly stripped."""
        # Configure mock agent
        self.mock_agent.process_query.return_value = "Response"

        # Override dependencies
        self.override_dependencies()

        # Test request with whitespace
        request_data = {
            "user_external_id": "  user123  ",
            "query": "  Test query  ",
            "session_id": "  session456  ",
        }

        response = self.client.post("/api/agent/chat", json=request_data)

        # Verify agent was called with stripped values
        self.mock_agent.process_query.assert_called_once_with(
            user_external_id="user123",
            query="Test query",
            session_id="session456",
        )

        # Verify response contains stripped values
        if response.status_code == 200:
            response_data = response.json()
            assert response_data["user_external_id"] == "user123"
            assert response_data["query"] == "Test query"
            assert response_data["session_id"] == "session456"


