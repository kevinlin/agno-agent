"""Tests for enhanced health check endpoint."""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from agent.healthcare.config.config import Config
from agent.healthcare.main import add_routes, create_app
from agent.healthcare.search.search_service import SearchService
from agent.healthcare.storage.database import DatabaseService
from agent.healthcare.storage.embeddings import EmbeddingService


class TestHealthCheckEndpoint:
    """Test cases for the enhanced health check endpoint."""

    @pytest.fixture
    def app(self):
        """Create test FastAPI app."""
        app = create_app()
        add_routes(app)
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_config(self):
        """Mock configuration."""
        config = Mock(spec=Config)
        config.openai_model = "gpt-4o-mini"
        config.embedding_model = "text-embedding-3-large"
        config.base_data_dir.exists.return_value = True
        config.chunk_size = 1000
        config.chunk_overlap = 200
        return config

    @pytest.fixture
    def mock_db_service(self):
        """Mock database service."""
        from contextlib import contextmanager

        db_service = Mock(spec=DatabaseService)
        session_mock = Mock()
        session_mock.exec.return_value.first.return_value = True

        @contextmanager
        def mock_get_session():
            yield session_mock

        db_service.get_session = mock_get_session
        return db_service

    @pytest.fixture
    def mock_embedding_service(self, mock_config):
        """Mock embedding service."""
        embedding_service = Mock(spec=EmbeddingService)
        embedding_service.config = mock_config
        return embedding_service

    @pytest.fixture
    def mock_search_service(self, mock_config):
        """Mock search service."""
        search_service = Mock(spec=SearchService)
        search_service.config = mock_config
        return search_service

    def test_health_check_all_services_healthy(
        self,
        client,
        mock_config,
        mock_db_service,
        mock_embedding_service,
        mock_search_service,
    ):
        """Test health check when all services are healthy."""
        # Set up app state with all services
        client.app.state.config = mock_config
        client.app.state.db_service = mock_db_service
        client.app.state.embedding_service = mock_embedding_service
        client.app.state.search_service = mock_search_service

        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Check overall status
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["version"] == "0.1.0"
        assert "services" in data

        # Check individual service statuses
        services = data["services"]

        # Config service
        assert services["config"]["status"] == "healthy"
        assert services["config"]["openai_model"] == "gpt-4o-mini"
        assert services["config"]["embedding_model"] == "text-embedding-3-large"
        assert services["config"]["base_data_dir_exists"] is True

        # Database service
        assert services["database"]["status"] == "healthy"
        assert services["database"]["connection"] == "active"

        # Embedding service
        assert services["embedding"]["status"] == "healthy"
        assert services["embedding"]["model"] == "text-embedding-3-large"
        assert services["embedding"]["chunk_size"] == 1000
        assert services["embedding"]["chunk_overlap"] == 200

        # Search service
        assert services["search"]["status"] == "healthy"
        assert services["search"]["embedding_model"] == "text-embedding-3-large"
        assert services["search"]["vector_db"] == "chroma"

    def test_health_check_services_not_initialized(self, client):
        """Test health check when services are not initialized."""
        # Clear app state to simulate services not initialized
        if hasattr(client.app.state, "config"):
            delattr(client.app.state, "config")
        if hasattr(client.app.state, "db_service"):
            delattr(client.app.state, "db_service")
        if hasattr(client.app.state, "embedding_service"):
            delattr(client.app.state, "embedding_service")
        if hasattr(client.app.state, "search_service"):
            delattr(client.app.state, "search_service")

        response = client.get("/health")

        assert response.status_code == 503
        data = response.json()["detail"]

        # Check overall status
        assert data["status"] == "degraded"
        assert "timestamp" in data

        # Check individual service statuses
        services = data["services"]
        assert services["config"]["status"] == "not_initialized"
        assert services["database"]["status"] == "not_initialized"
        assert services["embedding"]["status"] == "not_initialized"
        assert services["search"]["status"] == "not_initialized"

    def test_health_check_database_connection_failure(
        self, client, mock_config, mock_embedding_service, mock_search_service
    ):
        """Test health check when database connection fails."""
        # Create a failing database service
        failing_db_service = Mock(spec=DatabaseService)
        failing_db_service.get_session.side_effect = Exception("Connection refused")

        # Set up app state with failing database
        client.app.state.config = mock_config
        client.app.state.db_service = failing_db_service
        client.app.state.embedding_service = mock_embedding_service
        client.app.state.search_service = mock_search_service

        response = client.get("/health")

        assert response.status_code == 503
        data = response.json()["detail"]

        # Check overall status
        assert data["status"] == "unhealthy"

        # Check individual service statuses
        services = data["services"]
        assert services["config"]["status"] == "healthy"
        assert services["database"]["status"] == "unhealthy"
        assert "Connection refused" in services["database"]["error"]
        assert services["embedding"]["status"] == "healthy"
        assert services["search"]["status"] == "healthy"

    def test_health_check_embedding_service_failure(
        self, client, mock_config, mock_db_service, mock_search_service
    ):
        """Test health check when embedding service fails."""
        # Create a failing embedding service
        failing_embedding_service = Mock(spec=EmbeddingService)
        failing_embedding_service.config = None  # This will cause an AttributeError

        # Set up app state with failing embedding service
        client.app.state.config = mock_config
        client.app.state.db_service = mock_db_service
        client.app.state.embedding_service = failing_embedding_service
        client.app.state.search_service = mock_search_service

        response = client.get("/health")

        assert response.status_code == 503
        data = response.json()["detail"]

        # Check overall status
        assert data["status"] == "unhealthy"

        # Check individual service statuses
        services = data["services"]
        assert services["config"]["status"] == "healthy"
        assert services["database"]["status"] == "healthy"
        assert services["embedding"]["status"] == "unhealthy"
        assert "error" in services["embedding"]
        assert services["search"]["status"] == "healthy"

    def test_health_check_search_service_failure(
        self, client, mock_config, mock_db_service, mock_embedding_service
    ):
        """Test health check when search service fails."""
        # Create a failing search service
        failing_search_service = Mock(spec=SearchService)
        failing_search_service.config = None  # This will cause an AttributeError

        # Set up app state with failing search service
        client.app.state.config = mock_config
        client.app.state.db_service = mock_db_service
        client.app.state.embedding_service = mock_embedding_service
        client.app.state.search_service = failing_search_service

        response = client.get("/health")

        assert response.status_code == 503
        data = response.json()["detail"]

        # Check overall status
        assert data["status"] == "unhealthy"

        # Check individual service statuses
        services = data["services"]
        assert services["config"]["status"] == "healthy"
        assert services["database"]["status"] == "healthy"
        assert services["embedding"]["status"] == "healthy"
        assert services["search"]["status"] == "unhealthy"
        assert "error" in services["search"]

    def test_health_check_mixed_service_states(
        self, client, mock_config, mock_db_service, mock_embedding_service
    ):
        """Test health check with mixed service states."""
        # Set up app state with some services initialized, some not
        client.app.state.config = mock_config
        client.app.state.db_service = mock_db_service
        client.app.state.embedding_service = mock_embedding_service
        # Don't set search_service to simulate it not being initialized
        if hasattr(client.app.state, "search_service"):
            delattr(client.app.state, "search_service")

        response = client.get("/health")

        assert response.status_code == 503
        data = response.json()["detail"]

        # Check overall status
        assert data["status"] == "degraded"

        # Check individual service statuses
        services = data["services"]
        assert services["config"]["status"] == "healthy"
        assert services["database"]["status"] == "healthy"
        assert services["embedding"]["status"] == "healthy"
        assert services["search"]["status"] == "not_initialized"

    def test_health_check_response_format(
        self,
        client,
        mock_config,
        mock_db_service,
        mock_embedding_service,
        mock_search_service,
    ):
        """Test that health check response has the correct format."""
        # Set up app state with all services
        client.app.state.config = mock_config
        client.app.state.db_service = mock_db_service
        client.app.state.embedding_service = mock_embedding_service
        client.app.state.search_service = mock_search_service

        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Check required top-level fields
        required_fields = ["status", "timestamp", "version", "services"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Check timestamp format (should be ISO format)
        timestamp = data["timestamp"]
        # This should not raise an exception if it's a valid ISO format
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

        # Check services structure
        services = data["services"]
        expected_services = ["config", "database", "embedding", "search"]
        for service in expected_services:
            assert service in services, f"Missing service: {service}"
            assert (
                "status" in services[service]
            ), f"Missing status for service: {service}"
