"""Command-line interface for Healthcare Agent MVP."""

import logging
import sys
from pathlib import Path

import click
import uvicorn

from agent.healthcare.config.config import ConfigManager
from agent.healthcare.storage.database import DatabaseService

logger = logging.getLogger(__name__)


@click.group()
def cli():
    """Healthcare Agent MVP - Personal health data management system."""
    pass


@cli.command()
@click.option("--host", default="0.0.0.0", help="Host to bind to")
@click.option("--port", default=8000, help="Port to bind to")
@click.option("--reload", is_flag=True, help="Enable auto-reload for development")
@click.option("--log-level", default="info", help="Log level")
def start(host: str, port: int, reload: bool, log_level: str):
    """Start the FastAPI server."""
    try:
        # Validate configuration before starting
        config = ConfigManager.load_config()
        ConfigManager.validate_environment(config)
        click.echo(f"✓ Configuration validated")

        # Initialize directories
        ConfigManager.initialize_directories(config)
        click.echo(f"✓ Directories initialized")

        click.echo(f"Starting Healthcare Agent MVP on {host}:{port}")
        click.echo(f"Documentation available at: http://{host}:{port}/docs")

        uvicorn.run(
            "agent.healthcare.main:app",
            host=host,
            port=port,
            reload=reload,
            log_level=log_level,
        )

    except Exception as e:
        click.echo(f"Error starting server: {e}", err=True)
        sys.exit(1)


@cli.command()
def init_db():
    """Initialize the database and create tables."""
    try:
        config = ConfigManager.load_config()
        ConfigManager.initialize_directories(config)

        db_service = DatabaseService(config)
        db_service.create_tables()

        click.echo(f"✓ Database initialized at: {config.medical_db_path}")
        click.echo(f"✓ Tables created successfully")

        db_service.close()

    except Exception as e:
        click.echo(f"Error initializing database: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--pattern", default="test_*.py", help="Test pattern to run")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def test(pattern: str, verbose: bool):
    """Run tests."""
    try:
        import subprocess

        cmd = ["python", "-m", "pytest"]
        if verbose:
            cmd.append("-v")

        # Add test pattern
        cmd.append(f"tests/agent/healthcare/{pattern}")

        click.echo(f"Running tests: {' '.join(cmd)}")
        result = subprocess.run(cmd, env={"PYTHONPATH": "."})
        sys.exit(result.returncode)

    except Exception as e:
        click.echo(f"Error running tests: {e}", err=True)
        sys.exit(1)


@cli.command()
def status():
    """Check application status and configuration."""
    try:
        config = ConfigManager.load_config()

        click.echo("Healthcare Agent MVP Status")
        click.echo("=" * 30)
        click.echo(f"OpenAI Model: {config.openai_model}")
        click.echo(f"Embedding Model: {config.embedding_model}")
        click.echo(f"Data Directory: {config.base_data_dir}")
        click.echo(f"Database Path: {config.medical_db_path}")
        click.echo(f"Log Level: {config.log_level}")

        # Check directory existence
        click.echo("\nDirectories:")
        for name, path in [
            ("Base Data", config.base_data_dir),
            ("Uploads", config.uploads_dir),
            ("Reports", config.reports_dir),
            ("Chroma", config.chroma_dir),
        ]:
            status = "✓" if path.exists() else "✗"
            click.echo(f"  {status} {name}: {path}")

        # Check database
        db_status = "✓" if config.medical_db_path.exists() else "✗"
        click.echo(f"  {db_status} Database: {config.medical_db_path}")

    except Exception as e:
        click.echo(f"Error checking status: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
