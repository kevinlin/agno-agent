"""Main FastAPI application for Healthcare Agent MVP."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from agent.healthcare.config.config import Config, ConfigManager
from agent.healthcare.search.search_service import SearchService
from agent.healthcare.storage.database import DatabaseService
from agent.healthcare.storage.embeddings import EmbeddingService

# Global variables for application state
config: Config = None
db_service: DatabaseService = None
embedding_service: EmbeddingService = None
search_service: SearchService = None

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown."""
    global config, db_service, embedding_service, search_service

    try:
        # Startup
        logger.info("Starting Healthcare Agent MVP...")

        # Load configuration
        config = ConfigManager.load_config()
        logger.info("✓ Configuration loaded")

        # Initialize directories
        ConfigManager.initialize_directories(config)
        logger.info("✓ Directories initialized")

        # Validate environment
        ConfigManager.validate_environment(config)
        logger.info("✓ Environment validated")

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

        # Store services in app state for dependency injection
        app.state.config = config
        app.state.db_service = db_service
        app.state.embedding_service = embedding_service
        app.state.search_service = search_service
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
        logger.info("Healthcare Agent MVP shutdown complete")


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

    return app


def add_routes(app: FastAPI) -> None:
    """Add all routes to the FastAPI app."""

    # Include upload routes
    from agent.healthcare.upload.routes import router as upload_router

    app.include_router(upload_router)

    # Include search routes
    from agent.healthcare.search import router as search_router

    app.include_router(search_router)

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
            "timestamp": datetime.utcnow().isoformat(),
            "version": "0.1.0",
            "services": {}
        }
        
        try:
            # Check configuration service
            if hasattr(app.state, 'config') and app.state.config:
                health_status["services"]["config"] = {
                    "status": "healthy",
                    "openai_model": app.state.config.openai_model,
                    "embedding_model": app.state.config.embedding_model,
                    "base_data_dir_exists": app.state.config.base_data_dir.exists()
                }
            else:
                health_status["services"]["config"] = {"status": "not_initialized"}
                health_status["status"] = "degraded"

            # Check database service
            if hasattr(app.state, 'db_service') and app.state.db_service:
                try:
                    with app.state.db_service.get_session() as session:
                        session.exec(text("SELECT 1")).first()
                    health_status["services"]["database"] = {"status": "healthy", "connection": "active"}
                except Exception as e:
                    health_status["services"]["database"] = {"status": "unhealthy", "error": str(e)}
                    health_status["status"] = "unhealthy"
            else:
                health_status["services"]["database"] = {"status": "not_initialized"}
                health_status["status"] = "degraded"

            # Check embedding service
            if hasattr(app.state, 'embedding_service') and app.state.embedding_service:
                try:
                    # Basic health check - verify service is initialized with config
                    embedding_config = app.state.embedding_service.config
                    health_status["services"]["embedding"] = {
                        "status": "healthy",
                        "model": embedding_config.embedding_model,
                        "chunk_size": embedding_config.chunk_size,
                        "chunk_overlap": embedding_config.chunk_overlap
                    }
                except Exception as e:
                    health_status["services"]["embedding"] = {"status": "unhealthy", "error": str(e)}
                    health_status["status"] = "unhealthy"
            else:
                health_status["services"]["embedding"] = {"status": "not_initialized"}
                health_status["status"] = "degraded"

            # Check search service
            if hasattr(app.state, 'search_service') and app.state.search_service:
                try:
                    # Verify search service has required dependencies
                    search_config = app.state.search_service.config
                    health_status["services"]["search"] = {
                        "status": "healthy",
                        "embedding_model": search_config.embedding_model,
                        "vector_db": "chroma"
                    }
                except Exception as e:
                    health_status["services"]["search"] = {"status": "unhealthy", "error": str(e)}
                    health_status["status"] = "unhealthy"
            else:
                health_status["services"]["search"] = {"status": "not_initialized"}
                health_status["status"] = "degraded"

            # Set overall status based on service health
            service_statuses = [service.get("status") for service in health_status["services"].values()]
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
            raise HTTPException(status_code=503, detail={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "error": "health_check_failed",
                "message": "An unexpected error occurred during health check",
                "detail": str(e)
            })

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

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        """Handle unexpected exceptions."""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return {
            "error": "internal_server_error",
            "message": "An unexpected error occurred",
            "detail": str(exc) if app.debug else "Internal server error",
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
