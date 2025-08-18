"""Embedding service for vector database operations using Chroma."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from agent.healthcare.config.config import Config

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for managing embeddings and vector database operations."""

    def __init__(self, config: Config, openai_client: Optional[OpenAI] = None):
        """Initialize embedding service with configuration.

        Args:
            config: Configuration object
            openai_client: Optional OpenAI client (will create one if not provided)
        """
        self.config = config
        self.openai_client = openai_client or OpenAI(api_key=config.openai_api_key)
        self.chroma_client = None
        self.collection = None
        self._initialize_chroma()

    def _initialize_chroma(self) -> None:
        """Initialize Chroma client and collection."""
        try:
            # Ensure chroma directory exists
            self.config.chroma_dir.mkdir(parents=True, exist_ok=True)

            # Initialize persistent Chroma client
            self.chroma_client = chromadb.PersistentClient(
                path=str(self.config.chroma_dir),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                ),
            )

            # Get or create collection
            self.collection = self.chroma_client.get_or_create_collection(
                name="medical_reports",
                metadata={"description": "Medical report chunks with embeddings"},
            )

            logger.info(f"✓ Chroma initialized with collection: {self.collection.name}")
            logger.info(f"✓ Collection count: {self.collection.count()}")

        except Exception as e:
            logger.error(f"Failed to initialize Chroma: {e}")
            raise

    def chunk_markdown(self, markdown: str) -> List[str]:
        """Chunk Markdown content into semantic segments.

        Args:
            markdown: The markdown content to chunk

        Returns:
            List of text chunks
        """
        if not markdown or not markdown.strip():
            return []

        # Simple paragraph-based chunking for now
        # Split on double newlines (paragraph breaks)
        paragraphs = [p.strip() for p in markdown.split("\n\n") if p.strip()]

        chunks = []
        current_chunk = ""
        current_size = 0

        for paragraph in paragraphs:
            paragraph_size = len(paragraph)

            # If adding this paragraph would exceed chunk size, save current chunk
            if current_size + paragraph_size > self.config.chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = paragraph
                current_size = paragraph_size
            else:
                # Add paragraph to current chunk
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                    current_size += paragraph_size + 2  # +2 for the newlines
                else:
                    current_chunk = paragraph
                    current_size = paragraph_size

        # Add the last chunk if it exists
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        logger.info(f"Chunked markdown into {len(chunks)} segments")
        return chunks

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def generate_embeddings(self, chunks: List[str]) -> List[List[float]]:
        """Generate embeddings for text chunks using OpenAI.

        Args:
            chunks: List of text chunks to embed

        Returns:
            List of embedding vectors
        """
        if not chunks:
            return []

        try:
            response = self.openai_client.embeddings.create(
                model=self.config.embedding_model, input=chunks, encoding_format="float"
            )

            embeddings = [data.embedding for data in response.data]
            logger.info(
                f"Generated {len(embeddings)} embeddings using {self.config.embedding_model}"
            )
            return embeddings

        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise

    def store_chunks(
        self, chunks: List[str], embeddings: List[List[float]], metadata: Dict[str, Any]
    ) -> None:
        """Store chunks with embeddings in Chroma vector database.

        Args:
            chunks: List of text chunks
            embeddings: List of embedding vectors
            metadata: Base metadata to attach to all chunks
        """
        if len(chunks) != len(embeddings):
            raise ValueError("Number of chunks must match number of embeddings")

        if not chunks:
            logger.warning("No chunks to store")
            return

        try:
            # Generate unique IDs for each chunk
            chunk_ids = []
            chunk_metadatas = []

            for i, chunk in enumerate(chunks):
                chunk_id = f"{metadata.get('report_id', 'unknown')}_{i}"
                chunk_ids.append(chunk_id)

                # Create metadata for this chunk
                chunk_metadata = metadata.copy()
                chunk_metadata.update(
                    {
                        "chunk_index": i,
                        "content_type": "paragraph",  # Default content type
                        "chunk_size": len(chunk),
                    }
                )
                chunk_metadatas.append(chunk_metadata)

            # Store in Chroma
            self.collection.add(
                documents=chunks,
                embeddings=embeddings,
                metadatas=chunk_metadatas,
                ids=chunk_ids,
            )

            logger.info(f"Stored {len(chunks)} chunks in vector database")

        except Exception as e:
            logger.error(f"Failed to store chunks in vector database: {e}")
            raise

    def process_report_embeddings(
        self, markdown_content: str, report_metadata: Dict[str, Any]
    ) -> None:
        """Process a complete report for embeddings storage.

        Args:
            markdown_content: The markdown content of the report
            report_metadata: Metadata about the report (user_id, report_id, etc.)
        """
        try:
            # Chunk the markdown content
            chunks = self.chunk_markdown(markdown_content)

            if not chunks:
                logger.warning(
                    f"No chunks generated for report {report_metadata.get('report_id')}"
                )
                return

            # Generate embeddings
            embeddings = self.generate_embeddings(chunks)

            # Store chunks with embeddings
            self.store_chunks(chunks, embeddings, report_metadata)

            logger.info(
                f"Successfully processed embeddings for report {report_metadata.get('report_id')}"
            )

        except Exception as e:
            logger.error(f"Failed to process report embeddings: {e}")
            raise

    def search_similar(
        self, query: str, user_filter: Optional[str] = None, k: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for similar chunks in the vector database.

        Args:
            query: Search query text
            user_filter: Optional user external ID to filter results
            k: Number of results to return

        Returns:
            List of search results with content and metadata
        """
        try:
            # Generate embedding for query
            query_embeddings = self.generate_embeddings([query])
            if not query_embeddings:
                return []

            query_embedding = query_embeddings[0]

            # Prepare where clause for user filtering
            where_clause = {}
            if user_filter:
                where_clause["user_external_id"] = user_filter

            # Search in Chroma
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=k,
                where=where_clause if where_clause else None,
                include=["documents", "metadatas", "distances"],
            )

            # Format results
            search_results = []
            if results["documents"] and results["documents"][0]:
                for i in range(len(results["documents"][0])):
                    result = {
                        "content": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "distance": results["distances"][0][i],
                        "relevance_score": 1.0
                        - results["distances"][0][i],  # Convert distance to relevance
                    }
                    search_results.append(result)

            logger.info(f"Found {len(search_results)} similar chunks for query")
            return search_results

        except Exception as e:
            logger.error(f"Failed to search similar chunks: {e}")
            raise

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector database collection.

        Returns:
            Dictionary with collection statistics
        """
        try:
            count = self.collection.count()
            return {
                "collection_name": self.collection.name,
                "total_chunks": count,
                "storage_path": str(self.config.chroma_dir),
            }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {"error": str(e)}

    def delete_report_chunks(self, report_id: int) -> None:
        """Delete all chunks for a specific report.

        Args:
            report_id: The report ID to delete chunks for
        """
        try:
            # Find all chunk IDs for this report
            results = self.collection.get(
                where={"report_id": report_id}, include=["metadatas"]
            )

            if results["ids"]:
                self.collection.delete(ids=results["ids"])
                logger.info(
                    f"Deleted {len(results['ids'])} chunks for report {report_id}"
                )
            else:
                logger.info(f"No chunks found for report {report_id}")

        except Exception as e:
            logger.error(f"Failed to delete chunks for report {report_id}: {e}")
            raise
