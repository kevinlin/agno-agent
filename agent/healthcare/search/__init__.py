"""Search module initialization."""

from .routes import router
from .service import SearchResult, SearchService

__all__ = ["SearchService", "SearchResult", "router"]
