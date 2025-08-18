"""Search module initialization."""

from .routes import router, set_search_service
from .service import SearchResult, SearchService

__all__ = ["SearchService", "SearchResult", "router", "set_search_service"]
