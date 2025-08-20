"""Reports module initialization."""

from .routes import router
from .service import ReportService

__all__ = ["ReportService", "router"]