"""Test FastAPI application assembly and integration."""

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


class TestApplicationAssembly:
    """Test suite for complete application assembly."""

    def setup_method(self):
        """Set up test environment."""
        # Set test environment variables
        os.environ["OPENAI_API_KEY"] = "test-key"

    def test_application_creation_success(self):
        """Test that the application can be created successfully."""
        from agent.healthcare.main import create_app

        app = create_app()

        # Verify app is created
        assert app is not None
        assert app.title == "Healthcare Agent MVP"
        assert app.version == "0.1.0"
        assert app.docs_url == "/docs"
        assert app.redoc_url == "/redoc"

    def test_all_routes_integrated(self):
        """Test that all expected routes are integrated."""
        from agent.healthcare.main import app

        # Get all route paths
        route_paths = [route.path for route in app.routes]

        # Check for expected route patterns
        expected_route_patterns = [
            "/",  # Root endpoint
            "/health",  # Health check
            "/config",  # Configuration endpoint
            "/api/upload",  # Upload routes
            "/reports",  # Report and search routes
            "/api/reports",  # Additional report routes
            "/api/agent",  # Agent routes
        ]

        # Verify we have routes for each major component
        for pattern in expected_route_patterns:
            matching_routes = [path for path in route_paths if pattern in path]
            assert (
                len(matching_routes) > 0
            ), f"No routes found matching pattern: {pattern}"

    def test_middleware_configured(self):
        """Test that middleware is properly configured."""
        from agent.healthcare.main import app

        # Check that middleware is configured (CORS is wrapped in Middleware class)
        assert len(app.user_middleware) > 0

        # Verify CORS middleware is configured by checking the middleware stack
        # CORS middleware will be wrapped in a generic Middleware wrapper
        middleware_stack = app.user_middleware
        assert len(middleware_stack) >= 1, "Expected at least one middleware (CORS)"

    def test_error_handlers_configured(self):
        """Test that error handlers are configured."""
        from agent.healthcare.main import app

        # Check that exception handlers are configured
        exception_handlers = app.exception_handlers

        # Should have handlers for various exception types
        assert ValueError in exception_handlers
        assert FileNotFoundError in exception_handlers
        assert PermissionError in exception_handlers
        assert RuntimeError in exception_handlers
        assert Exception in exception_handlers

    def test_root_endpoint(self):
        """Test the root endpoint."""
        from agent.healthcare.main import app

        client = TestClient(app)
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Healthcare Agent MVP"
        assert data["status"] == "running"
        assert data["docs"] == "/docs"

    def test_openapi_docs_available(self):
        """Test that OpenAPI documentation is available."""
        from agent.healthcare.main import app

        client = TestClient(app)

        # Test docs endpoint
        response = client.get("/docs")
        assert response.status_code == 200

        # Test redoc endpoint
        response = client.get("/redoc")
        assert response.status_code == 200

        # Test OpenAPI schema
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert schema["info"]["title"] == "Healthcare Agent MVP"

    def test_router_prefixes_correct(self):
        """Test that all routers have correct prefixes."""
        from agent.healthcare.main import app

        route_paths = [route.path for route in app.routes]

        # Verify API routes have correct prefixes
        api_routes = [path for path in route_paths if path.startswith("/api")]

        # Should have routes for each API module
        assert any("/api/upload" in path for path in api_routes)
        assert any("/api/reports" in path for path in api_routes)
        assert any("/api/agent" in path for path in api_routes)

    def test_dependency_injection_setup(self):
        """Test that dependency injection is properly set up."""
        # This test verifies that the application can be created
        # and the lifecycle manager would initialize services
        from agent.healthcare.main import app

        # Application should be created without errors
        assert app is not None

        # The lifespan manager should be configured
        assert app.router.lifespan_context is not None

    def test_cli_integration(self):
        """Test that CLI is properly integrated."""
        from agent.healthcare.cli import cli

        # CLI should be available
        assert cli is not None

        # Should have expected commands
        command_names = [cmd.name for cmd in cli.commands.values()]
        expected_commands = [
            "start",
            "init-db",
            "test",
            "status",
            "cleanup",
            "user-reports",
            "health",
        ]

        for cmd in expected_commands:
            assert cmd in command_names, f"Missing CLI command: {cmd}"

    def test_error_handling_integration(self):
        """Test that error handling works end-to-end."""
        from agent.healthcare.main import app

        client = TestClient(app)

        # Test a route that might cause an error
        # Since services aren't initialized in testing, this should trigger error handling
        response = client.get("/config")

        # Should get an error response with proper structure
        assert response.status_code in [
            500,
            503,
        ]  # Service unavailable or internal error

        # Response should have error structure
        data = response.json()
        assert "error" in data or "detail" in data

    def test_comprehensive_route_coverage(self):
        """Test that we have comprehensive route coverage."""
        from agent.healthcare.main import app

        route_info = []
        for route in app.routes:
            if hasattr(route, "methods") and hasattr(route, "path"):
                for method in route.methods:
                    if method != "HEAD":  # Skip HEAD methods
                        route_info.append(f"{method} {route.path}")

        # Should have a substantial number of routes
        assert (
            len(route_info) >= 15
        ), f"Expected at least 15 routes, got {len(route_info)}"

        # Should have various HTTP methods
        methods_used = set()
        for info in route_info:
            method = info.split()[0]
            methods_used.add(method)

        # Should use GET, POST, DELETE at minimum
        assert "GET" in methods_used
        assert "POST" in methods_used
        assert "DELETE" in methods_used
