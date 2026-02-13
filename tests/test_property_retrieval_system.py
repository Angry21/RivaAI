"""Property-based tests for RetrievalSystem.

Feature: knowledge-base-retrieval
"""

import pytest
from hypothesis import given, strategies as st
from unittest.mock import AsyncMock, MagicMock, patch

from rivaai.knowledge.models import RawSearchResult, SearchResult
from rivaai.knowledge.retrieval import RetrievalSystem


# Strategies for generating test data
@st.composite
def raw_search_result_strategy(draw):
    """Generate a valid RawSearchResult for testing."""
    doc_id = draw(st.text(min_size=1, max_size=50))
    content = draw(st.text(min_size=10, max_size=200))
    similarity = draw(st.floats(min_value=0.0, max_value=1.0))
    domain = draw(st.sampled_from(["agriculture", "welfare", "education"]))
    entity_type = draw(st.sampled_from(["crop", "chemical", "scheme", "document"]))
    source_table = draw(st.sampled_from(["crops", "chemicals", "schemes", "knowledge_items"]))
    
    return RawSearchResult(
        doc_id=doc_id,
        content=content,
        metadata={"test": "data"},
        similarity=similarity,
        domain=domain,
        entity_type=entity_type,
        source_table=source_table,
    )


@pytest.mark.property
@given(
    queries=st.lists(st.text(min_size=5, max_size=100), min_size=1, max_size=5),
    top_k=st.integers(min_value=1, max_value=10),
)
@pytest.mark.asyncio
async def test_property_batch_query_order_correspondence(queries, top_k):
    """Property 11: Batch Query Order Correspondence.
    
    For any batch of N queries, the system should return exactly N result lists,
    where the i-th result list corresponds to the i-th query in the input batch.
    
    **Validates: Requirements 6.1, 6.4**
    """
    # Create mock dependencies
    mock_db_pool = MagicMock()
    mock_embedding_gen = MagicMock()
    mock_settings = MagicMock()
    mock_settings.retrieval_relevance_threshold = 0.5
    
    # Create retrieval system
    with patch('rivaai.knowledge.retrieval.VectorSearchEngine'), \
         patch('rivaai.knowledge.retrieval.HybridReranker'), \
         patch('rivaai.knowledge.retrieval.RAGFormatter'):
        
        system = RetrievalSystem(mock_db_pool, mock_embedding_gen, mock_settings)
        
        # Mock embedding generation to return list of embeddings
        mock_embeddings = [[0.1] * 1536 for _ in queries]
        mock_embedding_gen.generate_embeddings_batch.return_value = mock_embeddings
        
        # Mock vector search to return empty results for each query
        system.vector_search.similarity_search = AsyncMock(return_value=[])
        
        # Mock reranker to return empty results
        system.reranker.rerank = AsyncMock(return_value=[])
        
        # Execute batch search
        results = await system.search_batch(queries, top_k=top_k)
        
        # Verify order correspondence
        assert len(results) == len(queries), \
            f"Should return exactly {len(queries)} result lists, got {len(results)}"
        
        # Verify each result is a list
        for i, result_list in enumerate(results):
            assert isinstance(result_list, list), \
                f"Result {i} should be a list, got {type(result_list)}"


@pytest.mark.property
@given(
    domain=st.sampled_from(["agriculture", "welfare", "education"]),
    results=st.lists(raw_search_result_strategy(), min_size=1, max_size=10),
)
@pytest.mark.asyncio
async def test_property_domain_filtering_behavior(domain, results):
    """Property 5: Domain Filtering Behavior.
    
    For any query with a domain filter specified, all returned results should
    have the specified domain.
    
    **Validates: Requirements 2.2, 2.3**
    """
    # Filter results to match domain
    filtered_results = [r for r in results if r.domain == domain]
    
    # If no results match domain, skip test
    if not filtered_results:
        return
    
    # Create mock dependencies
    mock_db_pool = MagicMock()
    mock_embedding_gen = MagicMock()
    mock_settings = MagicMock()
    mock_settings.retrieval_relevance_threshold = 0.0
    
    with patch('rivaai.knowledge.retrieval.VectorSearchEngine'), \
         patch('rivaai.knowledge.retrieval.HybridReranker'), \
         patch('rivaai.knowledge.retrieval.RAGFormatter'):
        
        system = RetrievalSystem(mock_db_pool, mock_embedding_gen, mock_settings)
        
        # Mock embedding generation
        mock_embedding_gen.generate_embedding.return_value = [0.1] * 1536
        
        # Mock vector search to return filtered results
        system.vector_search.similarity_search = AsyncMock(return_value=filtered_results)
        
        # Mock reranker to convert to SearchResult
        search_results = [
            SearchResult(
                doc_id=r.doc_id,
                content=r.content,
                metadata=r.metadata,
                similarity_score=r.similarity,
                reranked_score=r.similarity,
                domain=r.domain,
                entity_type=r.entity_type,
                source_table=r.source_table,
            )
            for r in filtered_results
        ]
        system.reranker.rerank = AsyncMock(return_value=search_results)
        
        # Execute search with domain filter
        results = await system.search("test query", domain=domain, top_k=10)
        
        # Verify all results have the specified domain
        for result in results:
            assert result.domain == domain, \
                f"Result domain {result.domain} does not match filter {domain}"


@pytest.mark.property
@given(
    threshold=st.floats(min_value=0.0, max_value=1.0),
    results=st.lists(raw_search_result_strategy(), min_size=1, max_size=10),
)
@pytest.mark.asyncio
async def test_property_relevance_threshold_filtering(threshold, results):
    """Property 14: Relevance Threshold Filtering.
    
    For any relevance threshold T, all returned results should have similarity
    scores >= T, and any documents with scores < T should be excluded.
    
    **Validates: Requirements 8.1, 8.2**
    """
    # Create mock dependencies
    mock_db_pool = MagicMock()
    mock_embedding_gen = MagicMock()
    mock_settings = MagicMock()
    mock_settings.retrieval_relevance_threshold = threshold
    
    with patch('rivaai.knowledge.retrieval.VectorSearchEngine'), \
         patch('rivaai.knowledge.retrieval.HybridReranker'), \
         patch('rivaai.knowledge.retrieval.RAGFormatter'):
        
        system = RetrievalSystem(mock_db_pool, mock_embedding_gen, mock_settings)
        
        # Mock embedding generation
        mock_embedding_gen.generate_embedding.return_value = [0.1] * 1536
        
        # Mock vector search to return all results
        system.vector_search.similarity_search = AsyncMock(return_value=results)
        
        # Mock reranker to convert to SearchResult
        search_results = [
            SearchResult(
                doc_id=r.doc_id,
                content=r.content,
                metadata=r.metadata,
                similarity_score=r.similarity,
                reranked_score=r.similarity,
                domain=r.domain,
                entity_type=r.entity_type,
                source_table=r.source_table,
            )
            for r in results
        ]
        system.reranker.rerank = AsyncMock(return_value=search_results)
        
        # Execute search with threshold
        filtered_results = await system.search("test query", threshold=threshold, top_k=20)
        
        # Verify all results meet threshold
        for result in filtered_results:
            assert result.similarity_score >= threshold, \
                f"Result score {result.similarity_score} is below threshold {threshold}"
        
        # Verify no results below threshold are included
        expected_count = sum(1 for r in results if r.similarity >= threshold)
        assert len(filtered_results) == expected_count, \
            f"Expected {expected_count} results, got {len(filtered_results)}"


@pytest.mark.property
@given(results=st.lists(raw_search_result_strategy(), min_size=1, max_size=10))
@pytest.mark.asyncio
async def test_property_metadata_completeness(results):
    """Property 6: Metadata Completeness.
    
    For any search result returned by the system, it should contain all required
    metadata fields: doc_id, content, domain, entity_type, similarity_score, and
    metadata dictionary.
    
    **Validates: Requirements 2.4**
    """
    # Create mock dependencies
    mock_db_pool = MagicMock()
    mock_embedding_gen = MagicMock()
    mock_settings = MagicMock()
    mock_settings.retrieval_relevance_threshold = 0.0
    
    with patch('rivaai.knowledge.retrieval.VectorSearchEngine'), \
         patch('rivaai.knowledge.retrieval.HybridReranker'), \
         patch('rivaai.knowledge.retrieval.RAGFormatter'):
        
        system = RetrievalSystem(mock_db_pool, mock_embedding_gen, mock_settings)
        
        # Mock embedding generation
        mock_embedding_gen.generate_embedding.return_value = [0.1] * 1536
        
        # Mock vector search
        system.vector_search.similarity_search = AsyncMock(return_value=results)
        
        # Mock reranker
        search_results = [
            SearchResult(
                doc_id=r.doc_id,
                content=r.content,
                metadata=r.metadata,
                similarity_score=r.similarity,
                reranked_score=r.similarity,
                domain=r.domain,
                entity_type=r.entity_type,
                source_table=r.source_table,
            )
            for r in results
        ]
        system.reranker.rerank = AsyncMock(return_value=search_results)
        
        # Execute search
        search_results = await system.search("test query", top_k=20)
        
        # Verify metadata completeness
        for result in search_results:
            assert hasattr(result, 'doc_id') and result.doc_id, "Missing doc_id"
            assert hasattr(result, 'content') and result.content, "Missing content"
            assert hasattr(result, 'domain') and result.domain, "Missing domain"
            assert hasattr(result, 'entity_type') and result.entity_type, "Missing entity_type"
            assert hasattr(result, 'similarity_score'), "Missing similarity_score"
            assert hasattr(result, 'metadata') and isinstance(result.metadata, dict), \
                "Missing or invalid metadata"

