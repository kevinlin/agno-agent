#!/usr/bin/env python3
"""Script to load all survey definitions from docs/survey-definition into the database."""

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
    """Load all survey definitions from docs/survey-definition into the database."""
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

        # Path to survey definition directory
        survey_definition_dir = project_root / "docs" / "survey-definition"

        if not survey_definition_dir.exists():
            logger.error(f"Survey definition directory not found: {survey_definition_dir}")
            sys.exit(1)

        # Find all JSON files in the survey definition directory
        survey_files = list(survey_definition_dir.glob("*.json"))
        
        if not survey_files:
            logger.warning(f"No JSON files found in: {survey_definition_dir}")
            return

        logger.info(f"Found {len(survey_files)} survey definition files")

        # Track loading results
        loaded_count = 0
        skipped_count = 0
        failed_count = 0

        # Load each survey file
        for survey_file in survey_files:
            try:
                logger.info(f"Processing: {survey_file.name}")
                survey = survey_service.load_survey_from_file(survey_file)

                if survey:
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
                        failed_count += 1
                        continue

                    loaded_count += 1
                else:
                    # Survey already exists and was skipped
                    skipped_count += 1

            except Exception as e:
                logger.error(f"Failed to load survey from {survey_file.name}: {e}")
                failed_count += 1
                continue

        # Summary
        logger.info("\n" + "="*50)
        logger.info("SURVEY LOADING SUMMARY:")
        logger.info(f"  Total files processed: {len(survey_files)}")
        logger.info(f"  Successfully loaded: {loaded_count}")
        logger.info(f"  Skipped (already exist): {skipped_count}")
        logger.info(f"  Failed: {failed_count}")
        logger.info("="*50)

        if failed_count > 0:
            logger.warning(f"{failed_count} surveys failed to load")
            sys.exit(1)
        else:
            logger.info("All survey definitions processed successfully!")

    except Exception as e:
        logger.error(f"Failed to load survey definitions: {e}")
        sys.exit(1)
    finally:
        if "db_service" in locals():
            db_service.close()


if __name__ == "__main__":
    main()
