import os
from pathlib import Path

from agno.playground import Playground, serve_playground_app

# Import healthcare agent components
from healthcare.agent.agent_service import HealthcareAgent
from healthcare.config.config import Config, ConfigManager
from healthcare.reports.service import ReportService
from healthcare.search.embeddings import EmbeddingService
from healthcare.search.search_service import SearchService
from healthcare.storage.database import DatabaseService


def initialize_healthcare_services():
    """Initialize minimal healthcare services for playground."""
    config = ConfigManager.load_config()

    # Create directories
    ConfigManager.initialize_directories(config)

    # Initialize services
    db_service = DatabaseService(config)
    db_service.create_tables()

    embedding_service = EmbeddingService(config)
    search_service = SearchService(config, db_service, embedding_service)
    report_service = ReportService(config, db_service)

    # Create healthcare agent
    healthcare_agent_service = HealthcareAgent(
        config=config,
        db_service=db_service,
        search_service=search_service,
        report_service=report_service,
    )

    # Get the actual Agno agent instance
    healthcare_agent = healthcare_agent_service.get_agent()

    return healthcare_agent, {
        "db_service": db_service,
        "embedding_service": embedding_service,
        "search_service": search_service,
        "report_service": report_service,
    }


# Healthcare agent (new)
healthcare_agent, services = initialize_healthcare_services()

# Create playground app
agents = [healthcare_agent]
app = Playground(agents=agents).get_app()

if __name__ == "__main__":
    serve_playground_app("healthcare_agent:app", reload=True)
