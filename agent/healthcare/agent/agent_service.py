"""Healthcare agent service for Agno integration."""

import logging
from typing import Optional

from agno.agent import Agent
from agno.embedder.openai import OpenAIEmbedder
from agno.knowledge import AgentKnowledge
from agno.memory.v2.db.sqlite import SqliteMemoryDb
from agno.memory.v2.memory import Memory
from agno.models.openai import OpenAIChat
from agno.storage.sqlite import SqliteStorage
from agno.vectordb.chroma import ChromaDb

from agent.healthcare.agent.toolkit import MedicalToolkit
from agent.healthcare.config.config import Config
from agent.healthcare.reports.service import ReportService
from agent.healthcare.search.search_service import SearchService
from agent.healthcare.storage.database import DatabaseService

logger = logging.getLogger(__name__)


class HealthcareAgent:
    """Service for managing the healthcare AI agent with medical toolkit."""

    def __init__(
        self,
        config: Config,
        db_service: DatabaseService,
        search_service: SearchService,
        report_service: ReportService,
    ):
        """Initialize healthcare agent service.

        Args:
            config: Application configuration
            db_service: Database service for medical data access
            search_service: Search service for semantic search
            report_service: Report service for report management
        """
        self.config = config
        self.db_service = db_service
        self.search_service = search_service
        self.report_service = report_service
        self._agent: Optional[Agent] = None

    def get_agent(self) -> Agent:
        """Get or create the healthcare agent instance.

        Returns:
            Configured Agno agent with medical toolkit

        Raises:
            RuntimeError: If agent initialization fails
        """
        if self._agent is None:
            self._agent = self._create_healthcare_agent()
        return self._agent

    def _create_healthcare_agent(self) -> Agent:
        """Create and configure the healthcare agent.

        Returns:
            Configured Agno agent instance

        Raises:
            RuntimeError: If agent creation fails
        """
        try:
            # Initialize memory.v2
            memory = Memory(
                # Use any model for creating memories
                model=OpenAIChat(id="gpt-5-mini"),
                db=SqliteMemoryDb(
                    table_name="user_memories", db_file=str(self.config.agent_db_path)
                ),
            )

            # Initialize storage
            storage = SqliteStorage(
                table_name="agent_sessions", db_file=str(self.config.agent_db_path)
            )

            # Create knowledge base with Chroma vector database
            knowledge = AgentKnowledge(
                vector_db=ChromaDb(
                    collection="medical_reports",
                    path=str(self.config.chroma_dir),
                    persistent_client=True,
                ),
                embedder=OpenAIEmbedder(
                    id=self.config.embedding_model,
                    dimensions=3072,  # text-embedding-3-large dimensions
                ),
            )

            # Create medical toolkit with all required services
            medical_toolkit = MedicalToolkit(
                config=self.config,
                db_service=self.db_service,
                search_service=self.search_service,
                report_service=self.report_service,
            )

            # Create the agent with healthcare-specific configuration
            agent = Agent(
                name="Healthcare Assistant",
                model=OpenAIChat(id=self.config.openai_model),
                memory=memory,
                enable_agentic_memory=True,
                enable_user_memories=True,
                storage=storage,
                knowledge=knowledge,
                tools=[
                    medical_toolkit.ingest_pdf,
                    medical_toolkit.list_reports,
                    medical_toolkit.get_report_summary,
                    medical_toolkit.get_report_content,
                    medical_toolkit.search_medical_data,
                ],
                instructions=[
                    "You are a healthcare AI assistant specialized in analyzing medical reports and patient data.",
                    "Always search your knowledge base before answering questions about medical data.",
                    "Use the medical toolkit tools to access patient reports and search medical information.",
                    "Provide clear, accurate information with proper source attribution and citations.",
                    "If you don't have enough information to answer a question, ask clarifying questions.",
                    "Maintain strict patient privacy and never share data across different users.",
                    "When referencing medical data, always include the source report ID and filename.",
                    "Focus on being helpful while being appropriately cautious about medical advice.",
                    "Remember that you are an assistant to help organize and understand medical information, not provide medical diagnosis or treatment advice.",
                ],
                add_history_to_messages=True,
                num_history_runs=5,  # Keep recent conversation context
                markdown=True,
                show_tool_calls=True,  # Show tool usage for transparency
                # Add datetime for context
                add_datetime_to_instructions=True,
            )

            logger.info("Healthcare agent created successfully")
            return agent

        except Exception as e:
            logger.error(f"Failed to create healthcare agent: {e}")
            raise RuntimeError(f"Agent initialization failed: {e}")

    def process_query(
        self, user_external_id: str, query: str, session_id: Optional[str] = None
    ) -> str:
        """Process a user query through the healthcare agent.

        Args:
            user_external_id: External ID of the user
            query: User's query text
            session_id: Optional session ID for conversation continuity

        Returns:
            Agent's response to the query

        Raises:
            ValueError: If inputs are invalid
            RuntimeError: If query processing fails
        """
        try:
            # Validate inputs
            if not user_external_id or not user_external_id.strip():
                raise ValueError("User external ID is required")

            if not query or not query.strip():
                raise ValueError("Query is required")

            user_external_id = user_external_id.strip()
            query = query.strip()

            # Get the agent instance
            agent = self.get_agent()

            # Add user context to the query for security
            contextualized_query = f"[User: {user_external_id}] {query}"

            # Process the query through the agent
            response = agent.run(
                message=contextualized_query,
                session_id=session_id or user_external_id,
                stream=False,
            )

            logger.info(
                f"Processed query for user {user_external_id}: {len(query)} chars -> {len(response.content)} chars"
            )
            return response.content

        except ValueError as e:
            # Re-raise validation errors
            raise e
        except Exception as e:
            logger.error(f"Failed to process query for user {user_external_id}: {e}")
            raise RuntimeError(f"Query processing failed: {e}")

    def get_conversation_history(
        self, user_external_id: str, session_id: Optional[str] = None
    ) -> list:
        """Get conversation history for a user.

        Args:
            user_external_id: External ID of the user
            session_id: Optional session ID (defaults to user_external_id)

        Returns:
            List of conversation messages

        Raises:
            ValueError: If user ID is invalid
            RuntimeError: If history retrieval fails
        """
        try:
            # Validate input
            if not user_external_id or not user_external_id.strip():
                raise ValueError("User external ID is required")

            user_external_id = user_external_id.strip()
            session_id = session_id or user_external_id

            # Get the agent instance
            agent = self.get_agent()

            # Retrieve session from storage
            if agent.storage:
                try:
                    sessions = agent.storage.get_all_sessions(user_id=session_id)
                    if sessions and len(sessions) > 0:
                        # Get the most recent session
                        latest_session = max(sessions, key=lambda s: s.created_at)
                        return latest_session.memory or []
                except Exception as e:
                    logger.debug(f"Error retrieving sessions: {e}")
                    return []

            return []

        except ValueError as e:
            # Re-raise validation errors
            raise e
        except Exception as e:
            logger.error(
                f"Failed to get conversation history for user {user_external_id}: {e}"
            )
            raise RuntimeError(f"History retrieval failed: {e}")

    def clear_conversation_history(
        self, user_external_id: str, session_id: Optional[str] = None
    ) -> bool:
        """Clear conversation history for a user.

        Args:
            user_external_id: External ID of the user
            session_id: Optional session ID (defaults to user_external_id)

        Returns:
            True if history was cleared successfully

        Raises:
            ValueError: If user ID is invalid
            RuntimeError: If history clearing fails
        """
        try:
            # Validate input
            if not user_external_id or not user_external_id.strip():
                raise ValueError("User external ID is required")

            user_external_id = user_external_id.strip()
            session_id = session_id or user_external_id

            # Get the agent instance
            agent = self.get_agent()

            # Clear session history if storage is available
            if agent.storage:
                # Delete sessions for this session ID
                agent.storage.delete_session(session_id=session_id)
                logger.info(f"Cleared conversation history for user {user_external_id}")
                return True

            return False

        except ValueError as e:
            # Re-raise validation errors
            raise e
        except Exception as e:
            logger.error(
                f"Failed to clear conversation history for user {user_external_id}: {e}"
            )
            raise RuntimeError(f"History clearing failed: {e}")

    def get_agent_stats(self) -> dict:
        """Get statistics about the agent and its usage.

        Returns:
            Dictionary with agent statistics
        """
        try:
            stats = {
                "agent_name": "Healthcare Assistant",
                "model": self.config.openai_model,
                "embedding_model": self.config.embedding_model,
                "vector_db": "ChromaDB",
                "storage": "SQLite",
                "knowledge_base": "medical_reports",
                "toolkit_functions": [],
            }

            # Get toolkit function names if agent is initialized
            if self._agent:
                medical_toolkit = None
                for tool in self._agent.tools:
                    if isinstance(tool, MedicalToolkit):
                        medical_toolkit = tool
                        break

                if medical_toolkit and isinstance(medical_toolkit, MedicalToolkit):
                    # Get function names from the toolkit
                    stats["toolkit_functions"] = [
                        "ingest_pdf",
                        "list_reports",
                        "search_medical_data",
                        "get_report_content",
                        "get_report_summary",
                    ]

            return stats

        except Exception as e:
            logger.error(f"Failed to get agent stats: {e}")
            return {"error": str(e)}


def create_healthcare_agent_service(
    config: Config,
    db_service: DatabaseService,
    search_service: SearchService,
    report_service: ReportService,
) -> HealthcareAgent:
    """Factory function to create a healthcare agent service.

    Args:
        config: Application configuration
        db_service: Database service instance
        search_service: Search service instance
        report_service: Report service instance

    Returns:
        Configured HealthcareAgent instance
    """
    return HealthcareAgent(
        config=config,
        db_service=db_service,
        search_service=search_service,
        report_service=report_service,
    )
