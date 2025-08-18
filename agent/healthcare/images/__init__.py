"""Image extraction and asset management package."""

from .routes import router
from .image_service import AssetMetadata, ImageExtractionService

__all__ = ["ImageExtractionService", "AssetMetadata", "router"]
