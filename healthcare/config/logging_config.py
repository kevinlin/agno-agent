"""Enhanced logging configuration for Healthcare Agent MVP."""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Dict, Optional


class HealthcareLogFormatter(logging.Formatter):
    """Custom formatter for healthcare agent logs."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with healthcare-specific context."""
        # Add healthcare-specific context if available
        if hasattr(record, "user_id"):
            record.msg = f"[User: {record.user_id}] {record.msg}"

        if hasattr(record, "report_id"):
            record.msg = f"[Report: {record.report_id}] {record.msg}"

        if hasattr(record, "session_id"):
            record.msg = f"[Session: {record.session_id}] {record.msg}"

        return super().format(record)


def setup_healthcare_logging(
    log_level: str = "INFO",
    log_format: Optional[str] = None,
    log_file: Optional[Path] = None,
    enable_file_logging: bool = True,
    enable_structured_logging: bool = False,
    max_log_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> None:
    """Set up comprehensive logging for the healthcare agent.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Custom log format string
        log_file: Path to log file (if None, uses default location)
        enable_file_logging: Whether to log to file
        enable_structured_logging: Whether to use structured JSON logging
        max_log_size: Maximum size of log file before rotation
        backup_count: Number of backup log files to keep
    """

    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Clear existing handlers
    root_logger.handlers.clear()

    # Default log format
    if log_format is None:
        if enable_structured_logging:
            log_format = '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s", "module": "%(module)s", "function": "%(funcName)s", "line": %(lineno)d}'
        else:
            log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Create formatter
    if enable_structured_logging:
        formatter = logging.Formatter(log_format)
    else:
        formatter = HealthcareLogFormatter(log_format)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler (if enabled)
    if enable_file_logging:
        if log_file is None:
            log_file = Path("logs/healthcare_agent.log")

        # Ensure log directory exists
        log_file.parent.mkdir(parents=True, exist_ok=True)

        # Rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=max_log_size, backupCount=backup_count, encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)  # File logs more detail
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Configure specific loggers
    configure_logger_levels()

    # Log setup completion
    logging.info(
        f"Healthcare Agent logging configured - Level: {log_level}, File: {log_file}"
    )


def configure_logger_levels() -> None:
    """Configure specific logger levels for different components."""

    # Application loggers - more verbose
    logging.getLogger("healthcare").setLevel(logging.INFO)

    # Database and storage - moderate verbosity
    logging.getLogger("healthcare.storage").setLevel(logging.INFO)
    logging.getLogger("healthcare.search").setLevel(logging.INFO)

    # Agent and AI - detailed for debugging
    logging.getLogger("healthcare.agent").setLevel(logging.DEBUG)
    logging.getLogger("healthcare.conversion").setLevel(logging.INFO)

    # External libraries - less verbose
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("agno").setLevel(logging.INFO)

    # Database libraries
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    # Vector database
    logging.getLogger("chromadb").setLevel(logging.WARNING)

    # PDF processing
    logging.getLogger("pikepdf").setLevel(logging.WARNING)


def get_healthcare_logger(name: str) -> logging.Logger:
    """Get a logger with healthcare-specific configuration.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Add healthcare-specific methods
    def log_user_action(message: str, user_id: str, level: int = logging.INFO) -> None:
        """Log a user action with user context."""
        extra = {"user_id": user_id}
        logger.log(level, message, extra=extra)

    def log_report_action(
        message: str, report_id: int, user_id: str = None, level: int = logging.INFO
    ) -> None:
        """Log a report action with report context."""
        extra = {"report_id": report_id}
        if user_id:
            extra["user_id"] = user_id
        logger.log(level, message, extra=extra)

    def log_agent_action(
        message: str, session_id: str, user_id: str = None, level: int = logging.INFO
    ) -> None:
        """Log an agent action with session context."""
        extra = {"session_id": session_id}
        if user_id:
            extra["user_id"] = user_id
        logger.log(level, message, extra=extra)

    # Monkey patch the logger with healthcare methods
    logger.log_user_action = log_user_action
    logger.log_report_action = log_report_action
    logger.log_agent_action = log_agent_action

    return logger


def setup_performance_monitoring() -> None:
    """Set up performance monitoring and metrics logging."""

    perf_logger = logging.getLogger("healthcare.performance")
    perf_logger.setLevel(logging.INFO)

    # Performance log file
    perf_file = Path("logs/performance.log")
    perf_file.parent.mkdir(parents=True, exist_ok=True)

    perf_handler = logging.handlers.RotatingFileHandler(
        perf_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"  # 5MB
    )

    perf_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    perf_handler.setFormatter(perf_formatter)
    perf_logger.addHandler(perf_handler)

    # Don't propagate to root logger
    perf_logger.propagate = False


def setup_security_logging() -> None:
    """Set up security-focused logging."""

    security_logger = logging.getLogger("healthcare.security")
    security_logger.setLevel(logging.WARNING)

    # Security log file
    security_file = Path("logs/security.log")
    security_file.parent.mkdir(parents=True, exist_ok=True)

    security_handler = logging.handlers.RotatingFileHandler(
        security_file,
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=10,  # Keep more security logs
        encoding="utf-8",
    )

    security_formatter = logging.Formatter(
        "%(asctime)s - SECURITY - %(levelname)s - %(message)s - [%(pathname)s:%(lineno)d]"
    )
    security_handler.setFormatter(security_formatter)
    security_logger.addHandler(security_handler)

    # Don't propagate to root logger to avoid duplication
    security_logger.propagate = False


def log_startup_info(config) -> None:
    """Log important startup information."""
    logger = get_healthcare_logger("healthcare.startup")

    logger.info("=== Healthcare Agent MVP Starting ===")
    logger.info(f"OpenAI Model: {config.openai_model}")
    logger.info(f"Embedding Model: {config.embedding_model}")
    logger.info(f"Data Directory: {config.base_data_dir}")
    logger.info(f"Database: {config.medical_db_path}")
    logger.info(f"Agent DB: {config.agent_db_path}")
    logger.info(f"Chroma DB: {config.chroma_dir}")
    logger.info(f"Log Level: {config.log_level}")
    logger.info("=== Configuration Complete ===")


def log_shutdown_info() -> None:
    """Log shutdown information."""
    logger = get_healthcare_logger("healthcare.shutdown")

    logger.info("=== Healthcare Agent MVP Shutting Down ===")
    logger.info("All services stopped gracefully")
    logger.info("=== Shutdown Complete ===")


# Performance monitoring decorators
def log_performance(operation_name: str):
    """Decorator to log performance metrics for operations."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            import time

            perf_logger = logging.getLogger("healthcare.performance")
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                perf_logger.info(f"{operation_name} completed in {duration:.3f}s")
                return result
            except Exception as e:
                duration = time.time() - start_time
                perf_logger.error(f"{operation_name} failed after {duration:.3f}s: {e}")
                raise

        return wrapper

    return decorator


def log_security_event(
    event_type: str, details: Dict, severity: str = "WARNING"
) -> None:
    """Log security-related events."""
    security_logger = logging.getLogger("healthcare.security")

    message = f"Security Event: {event_type}"
    if details:
        detail_str = ", ".join([f"{k}={v}" for k, v in details.items()])
        message += f" - {detail_str}"

    level = getattr(logging, severity.upper(), logging.WARNING)
    security_logger.log(level, message)
