#!/usr/bin/env python3
"""Script to load the personalization survey into the database."""

import logging
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from healthcare.config.config import ConfigManager
from healthcare.storage.database import DatabaseService
from healthcare.survey.survey_service import SurveyService

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Load the personalization survey into the database."""
    try:
        # Initialize configuration
        config = ConfigManager.load_config()
        logger.info("Configuration loaded successfully")

        # Initialize services
        db_service = DatabaseService(config)
        db_service.create_tables()
        logger.info("Database initialized")

        survey_service = SurveyService(config, db_service)
        logger.info("Survey service initialized")

        # Path to personalization survey file
        survey_file = project_root / "docs" / "personalization-survey.json"

        if not survey_file.exists():
            logger.error(f"Personalization survey file not found: {survey_file}")
            sys.exit(1)

        # Load the survey
        logger.info(f"Loading personalization survey from: {survey_file}")
        survey = survey_service.load_survey_from_file(survey_file)

        logger.info(f"✓ Successfully loaded survey: {survey.code} (v{survey.version})")
        logger.info(f"  Title: {survey.title}")
        logger.info(f"  Type: {survey.type.value}")
        logger.info(f"  ID: {survey.id}")

        # Verify the survey was loaded correctly
        loaded_survey = survey_service.get_survey_by_code(survey.code)
        if loaded_survey:
            definition = survey_service.get_survey_definition(survey.code)
            if definition:
                question_count = len(definition.get("questions", []))
                logger.info(f"  Questions: {question_count}")
                logger.info("✓ Survey verification successful")
            else:
                logger.warning("Could not retrieve survey definition for verification")
        else:
            logger.error("Survey verification failed - could not retrieve survey")
            sys.exit(1)

        logger.info("Personalization survey loaded successfully!")

    except Exception as e:
        logger.error(f"Failed to load personalization survey: {e}")
        sys.exit(1)
    finally:
        if "db_service" in locals():
            db_service.close()


if __name__ == "__main__":
    main()
