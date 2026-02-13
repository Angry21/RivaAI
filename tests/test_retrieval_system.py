"""Unit tests for RetrievalSystem."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from rivaai.knowledge.models import (
    DatabaseError,
    EmbeddingError,
    RawSearchResult,
    SearchResult,
    ValidationError,
)
from rivaai.knowledge.retrieval import RetrievalSystem


@pytest.fixture
def mock_dependencies():
    """Create mock dependencies for RetrievalSystem."""
    mock_db_pool = MagicMock()
    mock_embedding_gen = MagicMock()
    mock_settings = MagicMock()
    mock_settings.retrieval_relevance_threshold = 0.7
    mock_settings.retrieval_top_k = 5
    
    return mock_db_pool, mock_embedding_gen, mock_settings


@pytest.mark.asyncio
async def test_search_basic_flow(mock_dependencies):
    """Test basic search flow with successful retrieval."""
    mock_db_pool, mock_embedding_gen, mock_settings = mock_dependencies
    
    with patch('rivaai.knowledge.retrieval.VectorSearchEngine'), \
         patch('rivaai.knowledge.retrieval.HybridReranker'), \
         patch('rivaai.knowledge.retrieval.RAGFormatter'):
        
        system = RetrievalSystem(mock_db_pool, mock_embedding_gen, mock_settings)
        
        # Mock embedding generation
        mock_embedding_gen.generate_embedding.return_value = [0.1] * 1536
        
        # Mock vector search
        raw_results = [
            RawSearchResult(
                doc_id="doc1",
                content="Test content",
                metadata={},
                similarity=0.9,
                domain="agriculture",
                entity_type="crop",
                source_table="crops",
            )
        ]
        system.vector_search.similarity_search = AsyncMock(return_value=raw_results)
        
        # Mock reranker
        search_results = [
            SearchResult(
                doc_id="doc1",
                content="Test content",
                metadata={},
                similarity_score=0.9,
                reranked_score=0.92,
                domain="agriculture",
                entity_type="crop",
                source_table="crops",
            )
        ]
        system.reranker.rerank = AsyncMock(return_value=search_results)
        
        # Execute search
        results = await system.search("test query", top_k=5)
        
        assert len(results) == 1
        assert results[0].doc_id == "doc1"
        assert results[0].similarity_score == 0.9


@pytest.mark.asyncio
async def test_search_with_empty_query_raises_error(mock_dependencies):
    """Test that empty query raises ValidationError."""
    mock_db_pool, mock_embedding_gen, mock_settings = mock_dependencies
    
    with patch('rivaai.knowledge.retrieval.VectorSearchEngine'), \
         patch('rivaai.knowledge.retrieval.HybridReranker'), \
         patch('rivaai.knowledge.retrieval.RAGFormatter'):
        
        system = RetrievalSystem(mock_db_pool, mock_embedding_gen, mock_settings)
        
        with pytest.raises(ValidationError, match="Query cannot be empty"):
            await system.search("", top_k=5)


@pytest.mark.asyncio
async def test_search_with_invalid_top_k_raises_error(mock_dependencies):
    """Test that invalid top_k raises ValidationError."""
    mock_db_pool, mock_embedding_gen, mock_settings = mock_dependencies
    
    with patch('rivaai.knowledge.retrieval.VectorSearchEngine'), \
         patch('rivaai.knowledge.retrieval.HybridReranker'), \
         patch('rivaai.knowledge.retrieval.RAGFormatter'):
        
        system = RetrievalSystem(mock_db_pool, mock_embedding_gen, mock_settings)
        
        with pytest.raises(ValidationError, match="top_k must be between 1 and 20"):
            await system.search("test query", top_k=0)
        
        with pytest.raises(ValidationError, match="top_k must be between 1 and 20"):
            await system.search("test query", top_k=25)


@pytest.mark.asyncio
async def test_search_with_invalid_threshold_raises_error(mock_dependencies):
    """Test that invalid threshold raises ValidationError."""
    mock_db_pool, mock_embedding_gen, mock_settings = mock_dependencies
    
    with patch('rivaai.knowledge.retrieval.VectorSearchEngine'), \
         patch('rivaai.knowledge.retrieval.HybridReranker'), \
         patch('rivaai.knowledge.retrieval.RAGFormatter'):
        
        system = RetrievalSystem(mock_db_pool, mock_embedding_gen, mock_settings)
        
        with pytest.raises(ValidationError, match="threshold must be between 0.0 and 1.0"):
            await system.search("test query", threshold=-0.1)
        
        with pytest.raises(ValidationError, match="threshold must be between 0.0 and 1.0"):
            await system.search("test query", threshold=1.5)


@pytest.mark.asyncio
async def test_search_embedding_failure_raises_error(mock_dependencies):
    """Test that embedding generation failure raises EmbeddingError."""
    mock_db_pool, mock_embedding_gen, mock_settings = mock_dependencies
    
    with patch('rivaai.knowledge.retrieval.VectorSearchEngine'), \
         patch('rivaai.knowledge.retrieval.HybridReranker'), \
         patch('rivaai.knowledge.retrieval.RAGFormatter'):
        
        system = RetrievalSystem(mock_db_pool, mock_embedding_gen, mock_settings)
        
        # Mock embedding generation to fail
        mock_embedding_gen.generate_embedding.side_effect = Exception("API error")
        
        with pytest.raises(EmbeddingError, match="Failed to generate query embedding"):
            await system.search("test query", top_k=5)


@pytest.mark.asyncio
async def test_search_applies_threshold_filtering(mock_dependencies):
    """Test that results below threshold are filtered out."""
    mock_db_pool, mock_embedding_gen, mock_settings = mock_dependencies
    
    with patch('rivaai.knowledge.retrieval.VectorSearchEngine'), \
         patch('rivaai.knowledge.retrieval.HybridReranker'), \
         patch('rivaai.knowledge.retrieval.RAGFormatter'):
        
        system = RetrievalSystem(mock_db_pool, mock_embedding_gen, mock_settings)
        
        # Mock embedding generation
        mock_embedding_gen.generate_embedding.return_value = [0.1] * 1536
        
        # Mock vector search
        raw_results = [
            RawSearchResult(
                doc_id="doc1",
                content="High score",
                metadata={},
                similarity=0.9,
                domain="agriculture",
                entity_type="crop",
                source_table="crops",
            ),
            RawSearchResult(
                doc_id="doc2",
                content="Low score",
                metadata={},
                similarity=0.5,
                domain="agriculture",
                entity_type="crop",
                source_table="crops",
            ),
        ]
        system.vector_search.similarity_search = AsyncMock(return_value=raw_results)
        
        # Mock reranker
        search_results = [
            SearchResult(
                doc_id="doc1",
                content="High score",
                metadata={},
                similarity_score=0.9,
                reranked_score=0.92,
                domain="agriculture",
                entity_type="crop",
                source_table="crops",
            ),
            SearchResult(
                doc_id="doc2",
                content="Low score",
                metadata={},
                similarity_score=0.5,
                reranked_score=0.52,
                domain="agriculture",
                entity_type="crop",
                source_table="crops",
            ),
        ]
        system.reranker.rerank = AsyncMock(return_value=search_results)
        
        # Execute search with threshold 0.7
        results = await system.search("test query", threshold=0.7, top_k=10)
        
        # Only high score result should be returned
        assert len(results) == 1
        assert results[0].doc_id == "doc1"


@pytest.mark.asyncio
async def test_search_batch_basic_flow(mock_dependencies):
    """Test basic batch search flow."""
    mock_db_pool, mock_embedding_gen, mock_settings = mock_dependencies
    
    with patch('rivaai.knowledge.retrieval.VectorSearchEngine'), \
         patch('rivaai.knowledge.retrieval.HybridReranker'), \
         patch('rivaai.knowledge.retrieval.RAGFormatter'):
        
        system = RetrievalSystem(mock_db_pool, mock_embedding_gen, mock_settings)
        
        # Mock batch embedding generation
        queries = ["query1", "query2"]
        mock_embedding_gen.generate_embeddings_batch.return_value = [
            [0.1] * 1536,
            [0.2] * 1536,
        ]
        
        # Mock vector search
        system.vector_search.similarity_search = AsyncMock(return_value=[])
        
        # Mock reranker
        system.reranker.rerank = AsyncMock(return_value=[])
        
        # Execute batch search
        results = await system.search_batch(queries, top_k=5)
        
        assert len(results) == 2
        assert all(isinstance(r, list) for r in results)


@pytest.mark.asyncio
async def test_search_batch_with_empty_queries(mock_dependencies):
    """Test batch search with empty query list."""
    mock_db_pool, mock_embedding_gen, mock_settings = mock_dependencies
    
    with patch('rivaai.knowledge.retrieval.VectorSearchEngine'), \
         patch('rivaai.knowledge.retrieval.HybridReranker'), \
         patch('rivaai.knowledge.retrieval.RAGFormatter'):
        
        system = RetrievalSystem(mock_db_pool, mock_embedding_gen, mock_settings)
        
        results = await system.search_batch([], top_k=5)
        
        assert results == []


@pytest.mark.asyncio
async def test_search_batch_partial_failure(mock_dependencies):
    """Test batch search with partial failures."""
    mock_db_pool, mock_embedding_gen, mock_settings = mock_dependencies
    
    with patch('rivaai.knowledge.retrieval.VectorSearchEngine'), \
         patch('rivaai.knowledge.retrieval.HybridReranker'), \
         patch('rivaai.knowledge.retrieval.RAGFormatter'):
        
        system = RetrievalSystem(mock_db_pool, mock_embedding_gen, mock_settings)
        
        # Mock batch embedding generation
        queries = ["query1", "query2", "query3"]
        mock_embedding_gen.generate_embeddings_batch.return_value = [
            [0.1] * 1536,
            [0.2] * 1536,
            [0.3] * 1536,
        ]
        
        # Mock vector search to fail for second query
        async def mock_search(query_embedding, top_k, domain, threshold):
            if query_embedding[0] == 0.2:
                raise Exception("Search failed")
            return []
        
        system.vector_search.similarity_search = mock_search
        
        # Mock reranker
        system.reranker.rerank = AsyncMock(return_value=[])
        
        # Execute batch search
        results = await system.search_batch(queries, top_k=5)
        
        # Should return 3 result lists, with second one empty due to failure
        assert len(results) == 3
        assert results[0] == []
        assert results[1] == []  # Failed query
        assert results[2] == []


@pytest.mark.asyncio
async def test_format_for_rag(mock_dependencies):
    """Test RAG formatting."""
    mock_db_pool, mock_embedding_gen, mock_settings = mock_dependencies
    
    with patch('rivaai.knowledge.retrieval.VectorSearchEngine'), \
         patch('rivaai.knowledge.retrieval.HybridReranker'), \
         patch('rivaai.knowledge.retrieval.RAGFormatter'):
        
        system = RetrievalSystem(mock_db_pool, mock_embedding_gen, mock_settings)
        
        # Mock formatter
        system.formatter.format_context = MagicMock(return_value="formatted context")
        
        results = [
            SearchResult(
                doc_id="doc1",
                content="Test",
                metadata={},
                similarity_score=0.9,
                reranked_score=0.92,
                domain="agriculture",
                entity_type="crop",
                source_table="crops",
            )
        ]
        
        context = await system.format_for_rag(results, max_tokens=2000)
        
        assert context == "formatted context"
        system.formatter.format_context.assert_called_once_with(results, max_tokens=2000)

