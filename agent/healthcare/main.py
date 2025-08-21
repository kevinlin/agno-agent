"""Main FastAPI application for Healthcare Agent MVP."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exception_handlers import http_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from agent.healthcare.agent.agent_service import HealthcareAgent
from agent.healthcare.config.config import Config, ConfigManager
from agent.healthcare.config.logging_config import (
    get_healthcare_logger,
    log_shutdown_info,
    log_startup_info,
    setup_healthcare_logging,
    setup_performance_monitoring,
    setup_security_logging,
)
from agent.healthcare.reports.service import ReportService
from agent.healthcare.search.search_service import SearchService
from agent.healthcare.storage.database import DatabaseService
from agent.healthcare.storage.embeddings import EmbeddingService

# Global variables for application state
config: Config = None
db_service: DatabaseService = None
embedding_service: EmbeddingService = None
search_service: SearchService = None
report_service: ReportService = None
healthcare_agent: HealthcareAgent = None

logger = get_healthcare_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown."""
    global config, db_service, embedding_service, search_service, report_service, healthcare_agent

    try:
        # Startup
        logger.info("Starting Healthcare Agent MVP...")

        # Load configuration
        config = ConfigManager.load_config()

        # Setup enhanced logging first
        setup_healthcare_logging(
            log_level=config.log_level,
            log_format=config.log_format,
            enable_file_logging=True,
            enable_structured_logging=False,
        )
        setup_performance_monitoring()
        setup_security_logging()

        # Log startup information
        log_startup_info(config)
        logger.info("✓ Configuration loaded")

        # Initialize directories
        ConfigManager.initialize_directories(config)
        logger.info("✓ Directories initialized")

        # Validate environment
        ConfigManager.validate_environment(config)
        logger.info("✓ Environment validated")

        # Check external dependencies
        dep_warnings = ConfigManager.check_external_dependencies()
        if dep_warnings:
            for warning in dep_warnings:
                logger.warning(f"Dependency warning: {warning}")

        # Check production readiness
        prod_warnings = ConfigManager.validate_production_readiness(config)
        if prod_warnings:
            for warning in prod_warnings:
                logger.warning(f"Production readiness: {warning}")

        # Log system information
        sys_info = ConfigManager.get_system_info()
        logger.info(f"System: {sys_info.get('platform', 'Unknown')}")
        logger.info(f"Python: {sys_info.get('python_version', 'Unknown')}")
        if "available_memory_gb" in sys_info:
            logger.info(f"Memory: {sys_info['available_memory_gb']}GB available")
        if "free_disk_gb" in sys_info:
            logger.info(f"Disk: {sys_info['free_disk_gb']}GB free")

        # Initialize database
        db_service = DatabaseService(config)
        db_service.create_tables()
        logger.info("✓ Database initialized")

        # Initialize embedding service
        embedding_service = EmbeddingService(config)
        logger.info("✓ Embedding service initialized")

        # Initialize search service
        search_service = SearchService(config, db_service, embedding_service)
        logger.info("✓ Search service initialized")

        # Initialize report service
        report_service = ReportService(config, db_service)
        logger.info("✓ Report service initialized")

        # Initialize healthcare agent service
        healthcare_agent = HealthcareAgent(
            config=config,
            db_service=db_service,
            search_service=search_service,
            report_service=report_service,
        )
        logger.info("✓ Healthcare agent service initialized")

        # Store services in app state for dependency injection
        app.state.config = config
        app.state.db_service = db_service
        app.state.embedding_service = embedding_service
        app.state.search_service = search_service
        app.state.report_service = report_service
        app.state.healthcare_agent = healthcare_agent
        logger.info("✓ Services stored in application state")

        logger.info("Healthcare Agent MVP started successfully!")

        yield

    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    finally:
        # Shutdown
        logger.info("Shutting down Healthcare Agent MVP...")
        if db_service:
            db_service.close()
            logger.info("✓ Database connections closed")
        log_shutdown_info()


def setup_logging(config: Config) -> None:
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, config.log_level.upper()),
        format=config.log_format,
        handlers=[
            logging.StreamHandler(),
        ],
    )

    # Reduce noise from some third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    # Load config early for logging setup
    try:
        temp_config = ConfigManager.load_config()
        setup_logging(temp_config)
    except Exception as e:
        # Fallback logging if config fails
        logging.basicConfig(level=logging.INFO)
        logger.warning(f"Failed to load config for logging setup: {e}")

    app = FastAPI(
        title="Healthcare Agent MVP",
        description="Personal health data management system with AI-powered analysis",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add custom error handling
    add_error_handlers(app)

    return app


def add_error_handlers(app: FastAPI) -> None:
    """Add comprehensive error handlers to the FastAPI app."""

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        """Handle ValueError exceptions."""
        logger.warning(f"Validation error on {request.url}: {exc}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "validation_error",
                "message": str(exc),
                "detail": "The provided input is invalid",
                "path": str(request.url),
            },
        )

    @app.exception_handler(FileNotFoundError)
    async def file_not_found_handler(request: Request, exc: FileNotFoundError):
        """Handle FileNotFoundError exceptions."""
        logger.warning(f"File not found on {request.url}: {exc}")
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": "file_not_found",
                "message": "The requested resource was not found",
                "detail": str(exc),
                "path": str(request.url),
            },
        )

    @app.exception_handler(PermissionError)
    async def permission_error_handler(request: Request, exc: PermissionError):
        """Handle PermissionError exceptions."""
        logger.error(f"Permission error on {request.url}: {exc}")
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "error": "permission_denied",
                "message": "Access denied to the requested resource",
                "detail": "Insufficient permissions",
                "path": str(request.url),
            },
        )

    @app.exception_handler(RuntimeError)
    async def runtime_error_handler(request: Request, exc: RuntimeError):
        """Handle RuntimeError exceptions."""
        logger.error(f"Runtime error on {request.url}: {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "processing_error",
                "message": "An error occurred while processing your request",
                "detail": str(exc),
                "path": str(request.url),
            },
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Handle all other unexpected exceptions."""
        logger.error(f"Unhandled exception on {request.url}: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "internal_server_error",
                "message": "An unexpected error occurred",
                "detail": (
                    str(exc)
                    if hasattr(app, "debug") and app.debug
                    else "Internal server error"
                ),
                "path": str(request.url),
            },
        )


def add_routes(app: FastAPI) -> None:
    """Add all routes to the FastAPI app."""

    # Include upload routes
    from agent.healthcare.upload.routes import router as upload_router

    app.include_router(upload_router)

    # Include search routes
    from agent.healthcare.search.routes import router as search_router

    app.include_router(search_router)

    # Include report management routes
    from agent.healthcare.reports.routes import router as reports_router

    app.include_router(reports_router)

    # Include image routes
    from agent.healthcare.images.routes import router as images_router

    app.include_router(images_router)

    # Include AI agent routes
    from agent.healthcare.agent.routes import router as agent_router

    app.include_router(agent_router)

    @app.get("/")
    async def root():
        """Root endpoint with basic information."""
        return {"message": "Healthcare Agent MVP", "status": "running", "docs": "/docs"}

    @app.get("/health")
    async def health_check():
        """Health check endpoint for all services."""
        from datetime import datetime

        from sqlmodel import text

        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "0.1.0",
            "services": {},
        }

        try:
            # Check configuration service
            if hasattr(app.state, "config") and app.state.config:
                health_status["services"]["config"] = {
                    "status": "healthy",
                    "openai_model": app.state.config.openai_model,
                    "embedding_model": app.state.config.embedding_model,
                    "base_data_dir_exists": app.state.config.base_data_dir.exists(),
                }
            else:
                health_status["services"]["config"] = {"status": "not_initialized"}
                health_status["status"] = "degraded"

            # Check database service
            if hasattr(app.state, "db_service") and app.state.db_service:
                try:
                    with app.state.db_service.get_session() as session:
                        session.exec(text("SELECT 1")).first()
                    health_status["services"]["database"] = {
                        "status": "healthy",
                        "connection": "active",
                    }
                except Exception as e:
                    health_status["services"]["database"] = {
                        "status": "unhealthy",
                        "error": str(e),
                    }
                    health_status["status"] = "unhealthy"
            else:
                health_status["services"]["database"] = {"status": "not_initialized"}
                health_status["status"] = "degraded"

            # Check embedding service
            if hasattr(app.state, "embedding_service") and app.state.embedding_service:
                try:
                    # Basic health check - verify service is initialized with config
                    embedding_config = app.state.embedding_service.config
                    health_status["services"]["embedding"] = {
                        "status": "healthy",
                        "model": embedding_config.embedding_model,
                        "chunk_size": embedding_config.chunk_size,
                        "chunk_overlap": embedding_config.chunk_overlap,
                    }
                except Exception as e:
                    health_status["services"]["embedding"] = {
                        "status": "unhealthy",
                        "error": str(e),
                    }
                    health_status["status"] = "unhealthy"
            else:
                health_status["services"]["embedding"] = {"status": "not_initialized"}
                health_status["status"] = "degraded"

            # Check search service
            if hasattr(app.state, "search_service") and app.state.search_service:
                try:
                    # Verify search service has required dependencies
                    search_config = app.state.search_service.config
                    health_status["services"]["search"] = {
                        "status": "healthy",
                        "embedding_model": search_config.embedding_model,
                        "vector_db": "chroma",
                    }
                except Exception as e:
                    health_status["services"]["search"] = {
                        "status": "unhealthy",
                        "error": str(e),
                    }
                    health_status["status"] = "unhealthy"
            else:
                health_status["services"]["search"] = {"status": "not_initialized"}
                health_status["status"] = "degraded"

            # Check report service
            if hasattr(app.state, "report_service") and app.state.report_service:
                try:
                    # Verify report service has required dependencies
                    report_config = app.state.report_service.config
                    health_status["services"]["reports"] = {
                        "status": "healthy",
                        "base_data_dir": str(report_config.base_data_dir),
                        "reports_dir": str(report_config.reports_dir),
                    }
                except Exception as e:
                    health_status["services"]["reports"] = {
                        "status": "unhealthy",
                        "error": str(e),
                    }
                    health_status["status"] = "unhealthy"
            else:
                health_status["services"]["reports"] = {"status": "not_initialized"}
                health_status["status"] = "degraded"

            # Set overall status based on service health
            service_statuses = [
                service.get("status") for service in health_status["services"].values()
            ]
            if "unhealthy" in service_statuses:
                health_status["status"] = "unhealthy"
            elif "not_initialized" in service_statuses:
                health_status["status"] = "degraded"

            # Return appropriate HTTP status code
            if health_status["status"] == "unhealthy":
                raise HTTPException(status_code=503, detail=health_status)
            elif health_status["status"] == "degraded":
                raise HTTPException(status_code=503, detail=health_status)

            return health_status

        except HTTPException:
            # Re-raise HTTP exceptions with their status
            raise
        except Exception as e:
            logger.error(f"Health check failed: {e}", exc_info=True)
            raise HTTPException(
                status_code=503,
                detail={
                    "status": "unhealthy",
                    "timestamp": datetime.utcnow().isoformat(),
                    "error": "health_check_failed",
                    "message": "An unexpected error occurred during health check",
                    "detail": str(e),
                },
            )

    @app.get("/config")
    async def get_config():
        """Get application configuration (non-sensitive parts)."""
        if not config:
            raise HTTPException(status_code=503, detail="Application not initialized")

        return {
            "openai_model": config.openai_model,
            "embedding_model": config.embedding_model,
            "chunk_size": config.chunk_size,
            "chunk_overlap": config.chunk_overlap,
            "max_retries": config.max_retries,
            "request_timeout": config.request_timeout,
            "log_level": config.log_level,
            "data_directories": {
                "base_data_dir": str(config.base_data_dir),
                "uploads_dir": str(config.uploads_dir),
                "reports_dir": str(config.reports_dir),
                "chroma_dir": str(config.chroma_dir),
            },
        }


# Create the FastAPI app
app = create_app()
add_routes(app)


if __name__ == "__main__":
    import uvicorn

    # Run with uvicorn for development
    uvicorn.run(
        "agent.healthcare.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
