import os
from pathlib import Path

from agno.playground import Playground, serve_playground_app

# Import healthcare agent components
from agent.healthcare.agent.agent_service import HealthcareAgent
from agent.healthcare.config.config import Config, ConfigManager
from agent.healthcare.reports.service import ReportService
from agent.healthcare.search.search_service import SearchService
from agent.healthcare.storage.database import DatabaseService
from agent.healthcare.storage.embeddings import EmbeddingService


# Configuration for playground (using environment variables or defaults)
def create_minimal_config():
    """Create a minimal configuration for playground use."""
    return Config(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
        embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-large"),
        base_data_dir=Path("data"),
        uploads_dir=Path("data/uploads"),
        reports_dir=Path("data/reports"),
        chroma_dir=Path("data/chroma"),
        medical_db_path=Path("data/medical.db"),
        agent_db_path=Path("data/healthcare_agent.db"),
        chunk_size=1000,
        chunk_overlap=200,
        max_retries=3,
        request_timeout=120,
        log_level="INFO",
    )


def initialize_healthcare_services():
    """Initialize minimal healthcare services for playground."""
    config = create_minimal_config()

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
    serve_playground_app("healthcare_agent_playground:app", reload=True)
