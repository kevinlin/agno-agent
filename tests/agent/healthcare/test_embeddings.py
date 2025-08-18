"""Unit tests for embedding service."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from agent.healthcare.config.config import Config
from agent.healthcare.storage.embeddings import EmbeddingService


@pytest.fixture
def test_config():
    """Create test configuration."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        config = Config(
            openai_api_key="test-key",
            base_data_dir=temp_path,
            chroma_dir=temp_path / "chroma",
            chunk_size=500,
            chunk_overlap=50,
        )
        yield config


@pytest.fixture
def mock_openai_client():
    """Create mock OpenAI client."""
    client = Mock()

    def mock_create_embeddings(*args, **kwargs):
        # Return embeddings matching the number of input chunks
        input_chunks = kwargs.get("input", [])
        embedding_response = Mock()
        embedding_response.data = [
            Mock(embedding=[0.1, 0.2, 0.3]) for _ in input_chunks
        ]
        return embedding_response

    client.embeddings.create.side_effect = mock_create_embeddings

    return client


@pytest.fixture
def mock_chroma_client():
    """Create mock Chroma client."""
    with patch("chromadb.PersistentClient") as mock_client_class:
        mock_client = Mock()
        mock_collection = Mock()

        # Configure collection
        mock_collection.name = "medical_reports"
        mock_collection.count.return_value = 0
        mock_collection.add = Mock()
        mock_collection.query.return_value = {
            "documents": [["test document"]],
            "metadatas": [[{"report_id": 1}]],
            "distances": [[0.2]],
        }
        mock_collection.get.return_value = {"ids": ["1_0"]}
        mock_collection.delete = Mock()

        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client_class.return_value = mock_client

        yield mock_client, mock_collection


class TestEmbeddingService:
    """Test cases for EmbeddingService."""

    def test_initialization(self, test_config, mock_openai_client, mock_chroma_client):
        """Test service initialization."""
        mock_client, mock_collection = mock_chroma_client

        service = EmbeddingService(test_config, mock_openai_client)

        assert service.config == test_config
        assert service.openai_client == mock_openai_client
        assert service.chroma_client == mock_client
        assert service.collection == mock_collection

    def test_chunk_markdown_simple(
        self, test_config, mock_openai_client, mock_chroma_client
    ):
        """Test simple markdown chunking."""
        service = EmbeddingService(test_config, mock_openai_client)

        markdown = (
            "# Header\n\nFirst paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        )
        chunks = service.chunk_markdown(markdown)

        # The chunking algorithm combines content within chunk size limit
        # So we should expect fewer chunks than paragraphs when they're small
        assert len(chunks) > 0
        assert all(isinstance(chunk, str) for chunk in chunks)
        assert all(len(chunk.strip()) > 0 for chunk in chunks)

        # Verify all original content is preserved
        combined_content = "\n\n".join(chunks)
        assert "# Header" in combined_content
        assert "First paragraph." in combined_content
        assert "Second paragraph." in combined_content
        assert "Third paragraph." in combined_content

    def test_chunk_markdown_large_chunks(
        self, test_config, mock_openai_client, mock_chroma_client
    ):
        """Test chunking with size limits."""
        service = EmbeddingService(test_config, mock_openai_client)

        # Create content that exceeds chunk size
        large_paragraph = "This is a very long paragraph. " * 50  # ~1500 chars
        markdown = f"# Header\n\n{large_paragraph}\n\nSmall paragraph."

        chunks = service.chunk_markdown(markdown)

        # Should split into multiple chunks
        assert len(chunks) >= 2
        # Most chunks should respect the size limit, but allow for some flexibility
        # since we don't want to break paragraphs mid-sentence
        reasonable_chunks = [
            chunk for chunk in chunks if len(chunk) <= test_config.chunk_size * 1.5
        ]
        assert (
            len(reasonable_chunks) >= len(chunks) - 1
        )  # At most one chunk can exceed the flexible limit

    def test_chunk_markdown_empty(
        self, test_config, mock_openai_client, mock_chroma_client
    ):
        """Test chunking empty content."""
        service = EmbeddingService(test_config, mock_openai_client)

        assert service.chunk_markdown("") == []
        assert service.chunk_markdown("   ") == []
        assert service.chunk_markdown("\n\n\n") == []

    def test_generate_embeddings_success(
        self, test_config, mock_openai_client, mock_chroma_client
    ):
        """Test successful embedding generation."""
        service = EmbeddingService(test_config, mock_openai_client)

        chunks = ["First chunk", "Second chunk"]
        embeddings = service.generate_embeddings(chunks)

        assert len(embeddings) == 2
        assert embeddings[0] == [0.1, 0.2, 0.3]
        assert embeddings[1] == [
            0.1,
            0.2,
            0.3,
        ]  # Mock returns same embedding for all chunks

        mock_openai_client.embeddings.create.assert_called_once_with(
            model=test_config.embedding_model, input=chunks, encoding_format="float"
        )

    def test_generate_embeddings_empty(
        self, test_config, mock_openai_client, mock_chroma_client
    ):
        """Test embedding generation with empty input."""
        service = EmbeddingService(test_config, mock_openai_client)

        embeddings = service.generate_embeddings([])
        assert embeddings == []
        mock_openai_client.embeddings.create.assert_not_called()

    def test_generate_embeddings_api_error(
        self, test_config, mock_openai_client, mock_chroma_client
    ):
        """Test embedding generation with API error."""
        service = EmbeddingService(test_config, mock_openai_client)

        # Mock API error
        mock_openai_client.embeddings.create.side_effect = Exception("API Error")

        # The retry decorator will wrap the exception in a RetryError
        with pytest.raises(
            Exception
        ):  # Don't match specific message due to retry wrapper
            service.generate_embeddings(["test chunk"])

    def test_store_chunks_success(
        self, test_config, mock_openai_client, mock_chroma_client
    ):
        """Test successful chunk storage."""
        mock_client, mock_collection = mock_chroma_client
        service = EmbeddingService(test_config, mock_openai_client)

        chunks = ["First chunk", "Second chunk"]
        embeddings = [[0.1, 0.2], [0.3, 0.4]]
        metadata = {
            "user_external_id": "test_user",
            "report_id": 123,
            "filename": "test.pdf",
        }

        service.store_chunks(chunks, embeddings, metadata)

        # Verify collection.add was called with correct parameters
        mock_collection.add.assert_called_once()
        call_args = mock_collection.add.call_args

        assert call_args[1]["documents"] == chunks
        assert call_args[1]["embeddings"] == embeddings
        assert len(call_args[1]["ids"]) == 2
        assert len(call_args[1]["metadatas"]) == 2

        # Check metadata structure
        metadata_0 = call_args[1]["metadatas"][0]
        assert metadata_0["user_external_id"] == "test_user"
        assert metadata_0["report_id"] == 123
        assert metadata_0["chunk_index"] == 0
        assert metadata_0["content_type"] == "paragraph"

    def test_store_chunks_mismatch_error(
        self, test_config, mock_openai_client, mock_chroma_client
    ):
        """Test store chunks with mismatched lengths."""
        service = EmbeddingService(test_config, mock_openai_client)

        chunks = ["First chunk", "Second chunk"]
        embeddings = [[0.1, 0.2]]  # Only one embedding
        metadata = {"report_id": 123}

        with pytest.raises(ValueError, match="Number of chunks must match"):
            service.store_chunks(chunks, embeddings, metadata)

    def test_store_chunks_empty(
        self, test_config, mock_openai_client, mock_chroma_client
    ):
        """Test storing empty chunks."""
        mock_client, mock_collection = mock_chroma_client
        service = EmbeddingService(test_config, mock_openai_client)

        service.store_chunks([], [], {})
        mock_collection.add.assert_not_called()

    def test_process_report_embeddings_success(
        self, test_config, mock_openai_client, mock_chroma_client
    ):
        """Test complete report processing."""
        service = EmbeddingService(test_config, mock_openai_client)

        markdown = "# Medical Report\n\nPatient shows signs of improvement.\n\nFollow-up recommended."
        metadata = {
            "user_external_id": "test_user",
            "report_id": 456,
            "filename": "report.pdf",
        }

        service.process_report_embeddings(markdown, metadata)

        # Verify OpenAI was called
        mock_openai_client.embeddings.create.assert_called_once()

        # Verify Chroma was called
        mock_collection = mock_chroma_client[1]
        mock_collection.add.assert_called_once()

    def test_process_report_embeddings_empty_content(
        self, test_config, mock_openai_client, mock_chroma_client
    ):
        """Test processing empty report content."""
        service = EmbeddingService(test_config, mock_openai_client)

        # Should not raise error, just log warning
        service.process_report_embeddings("", {"report_id": 123})

        mock_openai_client.embeddings.create.assert_not_called()

    def test_search_similar_success(
        self, test_config, mock_openai_client, mock_chroma_client
    ):
        """Test successful similarity search."""
        mock_client, mock_collection = mock_chroma_client
        service = EmbeddingService(test_config, mock_openai_client)

        results = service.search_similar("test query", user_filter="test_user", k=5)

        assert len(results) == 1
        assert results[0]["content"] == "test document"
        assert results[0]["metadata"]["report_id"] == 1
        assert results[0]["distance"] == 0.2
        assert results[0]["relevance_score"] == 0.8  # 1.0 - 0.2

        # Verify query was called correctly
        mock_collection.query.assert_called_once_with(
            query_embeddings=[[0.1, 0.2, 0.3]],  # From mock
            n_results=5,
            where={"user_external_id": "test_user"},
            include=["documents", "metadatas", "distances"],
        )

    def test_search_similar_no_user_filter(
        self, test_config, mock_openai_client, mock_chroma_client
    ):
        """Test similarity search without user filter."""
        mock_client, mock_collection = mock_chroma_client
        service = EmbeddingService(test_config, mock_openai_client)

        service.search_similar("test query", k=3)

        mock_collection.query.assert_called_once_with(
            query_embeddings=[[0.1, 0.2, 0.3]],
            n_results=3,
            where=None,
            include=["documents", "metadatas", "distances"],
        )

    def test_search_similar_no_results(
        self, test_config, mock_openai_client, mock_chroma_client
    ):
        """Test similarity search with no results."""
        mock_client, mock_collection = mock_chroma_client
        service = EmbeddingService(test_config, mock_openai_client)

        # Mock empty results
        mock_collection.query.return_value = {
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }

        results = service.search_similar("test query")
        assert results == []

    def test_get_collection_stats(
        self, test_config, mock_openai_client, mock_chroma_client
    ):
        """Test getting collection statistics."""
        mock_client, mock_collection = mock_chroma_client
        service = EmbeddingService(test_config, mock_openai_client)

        mock_collection.count.return_value = 42

        stats = service.get_collection_stats()

        assert stats["collection_name"] == "medical_reports"
        assert stats["total_chunks"] == 42
        assert str(test_config.chroma_dir) in stats["storage_path"]

    def test_get_collection_stats_error(
        self, test_config, mock_openai_client, mock_chroma_client
    ):
        """Test collection stats with error."""
        mock_client, mock_collection = mock_chroma_client
        service = EmbeddingService(test_config, mock_openai_client)

        mock_collection.count.side_effect = Exception("Database error")

        stats = service.get_collection_stats()
        assert "error" in stats

    def test_delete_report_chunks_success(
        self, test_config, mock_openai_client, mock_chroma_client
    ):
        """Test successful deletion of report chunks."""
        mock_client, mock_collection = mock_chroma_client
        service = EmbeddingService(test_config, mock_openai_client)

        service.delete_report_chunks(123)

        mock_collection.get.assert_called_once_with(
            where={"report_id": 123}, include=["metadatas"]
        )
        mock_collection.delete.assert_called_once_with(ids=["1_0"])

    def test_delete_report_chunks_no_results(
        self, test_config, mock_openai_client, mock_chroma_client
    ):
        """Test deletion with no chunks found."""
        mock_client, mock_collection = mock_chroma_client
        service = EmbeddingService(test_config, mock_openai_client)

        mock_collection.get.return_value = {"ids": []}

        service.delete_report_chunks(123)

        mock_collection.get.assert_called_once()
        mock_collection.delete.assert_not_called()

    @patch("agent.healthcare.storage.embeddings.retry")
    def test_generate_embeddings_retry_decorator(
        self, mock_retry, test_config, mock_openai_client, mock_chroma_client
    ):
        """Test that retry decorator is applied to generate_embeddings."""
        service = EmbeddingService(test_config, mock_openai_client)

        # Verify retry decorator was applied
        assert hasattr(service.generate_embeddings, "retry")


class TestEmbeddingServiceIntegration:
    """Integration tests for embedding service."""

    @patch("chromadb.PersistentClient")
    def test_real_chunking_and_embedding_flow(self, mock_chroma_client, test_config):
        """Test realistic chunking and embedding workflow."""
        # Mock Chroma
        mock_client = Mock()
        mock_collection = Mock()
        mock_collection.name = "medical_reports"
        mock_collection.count.return_value = 0
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_chroma_client.return_value = mock_client

        # Mock OpenAI
        mock_openai = Mock()

        def mock_create_embeddings(*args, **kwargs):
            # Return embeddings matching the number of input chunks
            input_chunks = kwargs.get("input", [])
            embedding_response = Mock()
            embedding_response.data = [
                Mock(embedding=[0.1] * 1536)
                for _ in input_chunks  # Realistic embedding size
            ]
            return embedding_response

        mock_openai.embeddings.create.side_effect = mock_create_embeddings

        service = EmbeddingService(test_config, mock_openai)

        # Realistic medical report content
        markdown_content = """# Medical Report - Patient John Doe

## Chief Complaint
Patient presents with chest pain and shortness of breath.

## History of Present Illness
The patient is a 45-year-old male who developed acute onset chest pain approximately 2 hours prior to presentation. The pain is described as sharp, substernal, and radiating to the left arm.

## Physical Examination
Vital signs: BP 140/90, HR 95, RR 18, Temp 98.6°F
General appearance: Patient appears anxious and diaphoretic.

## Assessment and Plan
1. Rule out myocardial infarction
2. Obtain EKG and cardiac enzymes
3. Start aspirin and monitor closely"""

        metadata = {
            "user_external_id": "patient_123",
            "report_id": 456,
            "filename": "chest_pain_report.pdf",
            "created_at": "2024-01-15T10:30:00Z",
        }

        # Process the report
        service.process_report_embeddings(markdown_content, metadata)

        # Verify chunking occurred
        mock_openai.embeddings.create.assert_called_once()
        call_args = mock_openai.embeddings.create.call_args[1]
        chunks = call_args["input"]

        # Should have multiple chunks (at least 2 for this content)
        assert len(chunks) >= 2
        assert all(isinstance(chunk, str) for chunk in chunks)
        assert all(len(chunk.strip()) > 0 for chunk in chunks)

        # Verify storage
        mock_collection.add.assert_called_once()
        add_args = mock_collection.add.call_args[1]

        assert len(add_args["documents"]) == len(chunks)
        assert len(add_args["embeddings"]) == len(chunks)
        assert len(add_args["metadatas"]) == len(chunks)
        assert len(add_args["ids"]) == len(chunks)

        # Check metadata structure
        for i, chunk_metadata in enumerate(add_args["metadatas"]):
            assert chunk_metadata["user_external_id"] == "patient_123"
            assert chunk_metadata["report_id"] == 456
            assert chunk_metadata["chunk_index"] == i
            assert chunk_metadata["content_type"] == "paragraph"
