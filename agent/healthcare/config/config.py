"""Configuration management for healthcare agent."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class Config:
    """Configuration settings for Healthcare Agent MVP."""

    # API Configuration
    openai_api_key: str
    openai_model: str = "gpt-5-mini"
    embedding_model: str = "text-embedding-3-large"

    # Storage Paths
    base_data_dir: Path = Path("data")
    uploads_dir: Path = Path("data/uploads")
    reports_dir: Path = Path("data/reports")
    chroma_dir: Path = Path("data/chroma")

    # Database Configuration
    medical_db_path: Path = Path("data/medical.db")
    agent_db_path: Path = Path("data/agent_sessions.db")

    # Processing Configuration
    chunk_size: int = 1000
    chunk_overlap: int = 200
    max_retries: int = 3
    request_timeout: int = 300

    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


class ConfigManager:
    """Manages configuration loading and environment setup."""

    @staticmethod
    def load_config() -> Config:
        """Load configuration from environment variables and defaults."""
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        return Config(
            openai_api_key=openai_api_key,
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-large"),
            base_data_dir=Path(os.getenv("DATA_DIR", "data")),
            uploads_dir=Path(os.getenv("UPLOADS_DIR", "data/uploads")),
            reports_dir=Path(os.getenv("REPORTS_DIR", "data/reports")),
            chroma_dir=Path(os.getenv("CHROMA_DIR", "data/chroma")),
            medical_db_path=Path(os.getenv("MEDICAL_DB_PATH", "data/medical.db")),
            agent_db_path=Path(os.getenv("AGENT_DB_PATH", "data/agent_sessions.db")),
            chunk_size=int(os.getenv("CHUNK_SIZE", "1000")),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "200")),
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
            request_timeout=int(os.getenv("REQUEST_TIMEOUT", "120")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_format=os.getenv(
                "LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            ),
        )

    @staticmethod
    def initialize_directories(config: Config) -> None:
        """Create necessary directories if they don't exist."""
        directories = [
            config.base_data_dir,
            config.uploads_dir,
            config.reports_dir,
            config.chroma_dir,
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            print(f"✓ Directory ensured: {directory}")

    @staticmethod
    def validate_environment(config: Config) -> None:
        """Validate configuration and environment requirements."""
        # Check required API key
        if not config.openai_api_key or config.openai_api_key.strip() == "":
            raise ValueError("OpenAI API key cannot be empty")

        # Validate model names
        valid_models = ["gpt-5", "gpt-5-mini", "gpt-5-nano"]
        if config.openai_model not in valid_models:
            print(f"Warning: OpenAI model '{config.openai_model}' may not be supported")

        # Validate paths are writable
        try:
            config.base_data_dir.mkdir(parents=True, exist_ok=True)
            test_file = config.base_data_dir / ".test_write"
            test_file.write_text("test")
            test_file.unlink()
        except Exception as e:
            raise ValueError(
                f"Cannot write to data directory {config.base_data_dir}: {e}"
            )

        # Validate numeric configuration
        if config.chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if config.chunk_overlap < 0:
            raise ValueError("chunk_overlap cannot be negative")
        if config.max_retries < 0:
            raise ValueError("max_retries cannot be negative")
        if config.request_timeout <= 0:
            raise ValueError("request_timeout must be positive")

    @staticmethod
    def check_external_dependencies() -> List[str]:
        """Check external dependencies and services.

        Returns:
            List of dependency warnings
        """
        warnings = []

        # Check required Python packages
        required_packages = [
            "fastapi",
            "uvicorn",
            "sqlmodel",
            "pydantic",
            "chromadb",
            "pikepdf",
            "click",
            "pytest",
        ]

        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                warnings.append(f"Required package not available: {package}")

        return warnings

    @staticmethod
    def get_system_info() -> dict:
        """Get system information for diagnostics.

        Returns:
            Dictionary with system information
        """
        import platform
        import sys

        info = {
            "python_version": sys.version,
            "platform": platform.platform(),
            "architecture": platform.architecture(),
            "processor": platform.processor(),
            "hostname": platform.node(),
        }

        # Memory information
        try:
            import psutil

            memory = psutil.virtual_memory()
            info["total_memory_gb"] = round(memory.total / (1024**3), 2)
            info["available_memory_gb"] = round(memory.available / (1024**3), 2)
            info["memory_percent"] = memory.percent
        except ImportError:
            info["memory_info"] = "psutil not available"

        # Disk information
        try:
            import shutil

            disk_usage = shutil.disk_usage("/")
            info["total_disk_gb"] = round(disk_usage.total / (1024**3), 2)
            info["free_disk_gb"] = round(disk_usage.free / (1024**3), 2)
            info["disk_usage_percent"] = round(
                (disk_usage.used / disk_usage.total) * 100, 2
            )
        except Exception:
            info["disk_info"] = "Not available"

        return info

    @staticmethod
    def validate_production_readiness(config: Config) -> List[str]:
        """Check if configuration is ready for production use.

        Args:
            config: Configuration to validate

        Returns:
            List of production readiness warnings
        """
        warnings = []

        # Check for test/development settings
        if config.openai_api_key.startswith("test-"):
            warnings.append("Using test API key - not suitable for production")

        if config.log_level.upper() == "DEBUG":
            warnings.append("Debug logging enabled - may impact performance")

        # Check security settings
        if not hasattr(config, "secret_key") or not config.openai_api_key:
            warnings.append("API key validation should be more robust for production")

        # Check resource limits
        if config.chunk_size > 2000:
            warnings.append("Large chunk_size may increase API costs")

        if config.max_retries > 5:
            warnings.append("High max_retries may cause long response times")

        return warnings
