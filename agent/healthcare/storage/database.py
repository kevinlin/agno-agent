"""Database service for healthcare agent."""

import logging
from pathlib import Path
from typing import List, Optional

from sqlmodel import Session, SQLModel, create_engine, select

from agent.healthcare.config.config import Config
from agent.healthcare.storage.models import MedicalReport, ReportAsset, User

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service for managing database operations."""
    
    def __init__(self, config: Config):
        """Initialize database service with configuration."""
        self.config = config
        self.db_path = config.medical_db_path
        self.engine = None
        self._initialize_engine()
    
    def _initialize_engine(self) -> None:
        """Initialize SQLite database engine."""
        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create engine with SQLite
        database_url = f"sqlite:///{self.db_path}"
        self.engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            echo=False  # Set to True for SQL debugging
        )
        logger.info(f"Database engine initialized: {database_url}")
    
    def create_tables(self) -> None:
        """Create all database tables."""
        try:
            SQLModel.metadata.create_all(self.engine)
            logger.info("✓ Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise
    
    def get_session(self) -> Session:
        """Get a database session."""
        if not self.engine:
            raise RuntimeError("Database engine not initialized")
        return Session(self.engine)
    
    def get_or_create_user(self, external_id: str) -> User:
        """Get existing user or create new one."""
        with self.get_session() as session:
            # Try to find existing user
            statement = select(User).where(User.external_id == external_id)
            user = session.exec(statement).first()
            
            if user:
                logger.debug(f"Found existing user: {external_id}")
                return user
            
            # Create new user
            user = User(external_id=external_id)
            session.add(user)
            session.commit()
            session.refresh(user)
            logger.info(f"Created new user: {external_id}")
            return user
    
    def create_medical_report(self, user_id: int, report_data: dict) -> MedicalReport:
        """Create a new medical report record."""
        with self.get_session() as session:
            # Check for duplicate based on user_id and file_hash
            if "file_hash" in report_data:
                statement = select(MedicalReport).where(
                    MedicalReport.user_id == user_id,
                    MedicalReport.file_hash == report_data["file_hash"]
                )
                existing = session.exec(statement).first()
                if existing:
                    logger.warning(f"Duplicate report detected for user {user_id}, hash {report_data['file_hash']}")
                    return existing
            
            # Create new report
            report = MedicalReport(user_id=user_id, **report_data)
            session.add(report)
            session.commit()
            session.refresh(report)
            logger.info(f"Created medical report: {report.id}")
            return report
    
    def create_report_assets(self, report_id: int, assets: List[dict]) -> List[ReportAsset]:
        """Create report asset records."""
        created_assets = []
        with self.get_session() as session:
            for asset_data in assets:
                asset = ReportAsset(report_id=report_id, **asset_data)
                session.add(asset)
                created_assets.append(asset)
            
            session.commit()
            for asset in created_assets:
                session.refresh(asset)
            
            logger.info(f"Created {len(created_assets)} assets for report {report_id}")
            return created_assets
    
    def get_user_reports(self, user_id: int) -> List[MedicalReport]:
        """Get all reports for a user."""
        with self.get_session() as session:
            statement = select(MedicalReport).where(MedicalReport.user_id == user_id)
            reports = session.exec(statement).all()
            return list(reports)
    
    def get_report_by_id(self, report_id: int) -> Optional[MedicalReport]:
        """Get a report by its ID."""
        with self.get_session() as session:
            return session.get(MedicalReport, report_id)
    
    def get_report_assets(self, report_id: int) -> List[ReportAsset]:
        """Get all assets for a report."""
        with self.get_session() as session:
            statement = select(ReportAsset).where(ReportAsset.report_id == report_id)
            assets = session.exec(statement).all()
            return list(assets)
    
    def close(self) -> None:
        """Close database connections."""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connections closed")
