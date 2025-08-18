"""Search module initialization."""

from .routes import router
from .search_service import SearchResult, SearchService

__all__ = ["SearchService", "SearchResult", "router"]
