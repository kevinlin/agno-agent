"""Search module initialization."""

from .embeddings import EmbeddingService
from .routes import router
from .search_service import SearchResult, SearchService

__all__ = ["EmbeddingService", "SearchService", "SearchResult", "router"]
