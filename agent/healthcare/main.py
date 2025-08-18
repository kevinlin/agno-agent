"""Main FastAPI application for Healthcare Agent MVP."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from agent.healthcare.config.config import Config, ConfigManager
from agent.healthcare.storage.database import DatabaseService

# Global variables for application state
config: Config = None
db_service: DatabaseService = None

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown."""
    global config, db_service

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

    @app.get("/")
    async def root():
        """Root endpoint with basic information."""
        return {"message": "Healthcare Agent MVP", "status": "running", "docs": "/docs"}

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        try:
            # Check database connection
            if db_service:
                with db_service.get_session() as session:
                    # Simple query to test connection
                    from sqlmodel import text

                    session.exec(text("SELECT 1")).first()

            return {
                "status": "healthy",
                "database": "connected",
                "timestamp": ConfigManager.load_config().base_data_dir.exists(),
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

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
